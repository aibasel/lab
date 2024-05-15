import errno
import logging
import os
import resource
import select
import subprocess
import sys
import time


def set_limit(kind, soft_limit, hard_limit):
    try:
        resource.setrlimit(kind, (soft_limit, hard_limit))
    except (OSError, ValueError) as err:
        logging.error(
            f"Resource limit for {kind} could not be set to "
            f"[{soft_limit}, {hard_limit}] ({err})"
        )


class Call:
    def __init__(
        self,
        args,
        name,
        time_limit=None,
        memory_limit=None,
        soft_stdout_limit=None,
        hard_stdout_limit=None,
        soft_stderr_limit=None,
        hard_stderr_limit=None,
        **kwargs,
    ):
        """Make system calls with time and memory constraints.

        *args* and *kwargs* are passed to `subprocess.Popen
        <http://docs.python.org/library/subprocess.html>`_.

        See also the documentation for
        ``lab.experiment._Buildable.add_command()``.

        """
        assert "stdin" not in kwargs, "redirecting stdin is not supported"
        self.name = name

        if time_limit is None:
            self.wall_clock_time_limit = None
        else:
            # Enforce miminum on wall-clock limit to account for disk latencies.
            self.wall_clock_time_limit = max(30, time_limit * 1.5)

        def get_bytes(limit):
            return None if limit is None else int(limit * 1024)

        # Allow passing filenames instead of file handles.
        self.opened_files = []
        for stream_name in ["stdout", "stderr"]:
            stream = kwargs.get(stream_name)
            if isinstance(stream, str):
                file = open(stream, mode="wb")
                kwargs[stream_name] = file
                self.opened_files.append(file)

        # Allow redirecting and limiting the output to streams.
        self.redirected_streams_and_limits = {}
        for stream_name, soft_limit, hard_limit in [
            ("stdout", get_bytes(soft_stdout_limit), get_bytes(hard_stdout_limit)),
            ("stderr", get_bytes(soft_stderr_limit), get_bytes(hard_stderr_limit)),
        ]:
            stream = kwargs.pop(stream_name, None)
            if stream:
                self.redirected_streams_and_limits[stream_name] = (
                    stream,
                    (soft_limit, hard_limit),
                )
                kwargs[stream_name] = subprocess.PIPE

        def prepare_call():
            # When the soft time limit is reached, SIGXCPU is emitted. Once we
            # reach the higher hard time limit, SIGKILL is sent. Having some
            # padding between the two limits allows programs to handle SIGXCPU.
            if time_limit is not None:
                set_limit(resource.RLIMIT_CPU, time_limit, time_limit + 5)
            if memory_limit is not None:
                _, hard_mem_limit = resource.getrlimit(resource.RLIMIT_AS)
                # Convert memory from MiB to Bytes.
                set_limit(
                    resource.RLIMIT_AS, memory_limit * 1024 * 1024, hard_mem_limit
                )
            set_limit(resource.RLIMIT_CORE, 0, 0)

        try:
            self.process = subprocess.Popen(args, preexec_fn=prepare_call, **kwargs)
        except OSError as err:
            if err.errno == errno.ENOENT:
                sys.exit(f'Error: Call {name} failed. "{args[0]}" not found.')
            else:
                raise

    def _redirect_streams(self):
        """
        Redirect output from original stdout and stderr streams to new
        streams if redirection is requested in the constructor and limit
        the output written to the new streams.

        Redirection could also be achieved py passing suitable
        parameters to Popen, but neither Popen.wait() nor
        Popen.communicate() allow limiting the redirected output.

        Code adapted from the Python 2 version of subprocess.py.
        """
        fd_to_infile = {}
        fd_to_outfile = {}
        fd_to_limits = {}
        fd_to_bytes = {}

        poller = select.poll()

        def register_and_append(file_obj, eventmask):
            poller.register(file_obj.fileno(), eventmask)
            fd_to_infile[file_obj.fileno()] = file_obj
            fd_to_bytes[file_obj.fileno()] = 0

        def close_unregister_and_remove(fd):
            poller.unregister(fd)
            fd_to_infile[fd].close()
            fd_to_infile.pop(fd)

        select_POLLIN_POLLPRI = select.POLLIN | select.POLLPRI

        for (
            stream_name,
            (new_stream, limits),
        ) in self.redirected_streams_and_limits.items():
            old_stream = getattr(self.process, stream_name)
            register_and_append(old_stream, select_POLLIN_POLLPRI)
            fd = old_stream.fileno()
            fd_to_outfile[fd] = new_stream
            fd_to_limits[fd] = limits

        while fd_to_infile:
            try:
                ready = poller.poll()
            except OSError as e:
                if e.args[0] == errno.EINTR:
                    continue
                raise

            for fd, mode in ready:
                if mode & select_POLLIN_POLLPRI:
                    data = os.read(fd, 4096)
                    if not data:
                        close_unregister_and_remove(fd)
                    if fd_to_outfile[fd]:
                        outfile = fd_to_outfile[fd]
                        _, hard_limit = fd_to_limits[fd]
                        if (
                            hard_limit is not None
                            and fd_to_bytes[fd] + len(data) > hard_limit
                        ):
                            # Don't write to this outfile in subsequent rounds.
                            fd_to_outfile[fd] = None
                            logging.error(
                                f"{self.name} wrote {hard_limit / 1024} KiB "
                                f"(hard limit) to {outfile.name} -> abort command"
                            )
                            self.process.terminate()
                            # Strip extra bytes.
                            data = data[: hard_limit - fd_to_bytes[fd]]
                        outfile.write(data)
                        fd_to_bytes[fd] += len(data)
                else:
                    # Ignore hang up or errors.
                    close_unregister_and_remove(fd)

        # Check soft limit.
        for fd, outfile in fd_to_outfile.items():
            # Ignore streams that exceeded the hard limit.
            if outfile is not None:
                soft_limit, _ = fd_to_limits[fd]
                bytes_written = fd_to_bytes[fd]
                if soft_limit is not None and bytes_written > soft_limit:
                    logging.error(
                        f"{self.name} finished and wrote "
                        f"{bytes_written / 1024:.2f} KiB to {outfile.name} "
                        f"(soft limit: {soft_limit / 1024:.2f} KiB)"
                    )

    def wait(self):
        wall_clock_start_time = time.time()
        self._redirect_streams()
        retcode = self.process.wait()
        for stream, _ in self.redirected_streams_and_limits.values():
            # Write output to disk before the next Call starts.
            stream.flush()
            os.fsync(stream.fileno())

        # Close files that were opened in the constructor.
        for file in self.opened_files:
            file.close()
        wall_clock_time = time.time() - wall_clock_start_time
        logging.info(f"{self.name} wall-clock time: {wall_clock_time:.2f}s")
        if (
            self.wall_clock_time_limit is not None
            and wall_clock_time > self.wall_clock_time_limit
        ):
            logging.error(
                f"wall-clock time for {self.name} too high: "
                f"{wall_clock_time:.2f} > {self.wall_clock_time_limit}"
            )
        logging.info(f"{self.name} exit code: {retcode}")
        return retcode
