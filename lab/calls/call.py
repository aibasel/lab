import errno
import logging
import math
import os
import resource
import select
import subprocess
import sys
import threading
import time


def set_limit(kind, soft_limit, hard_limit):
    try:
        resource.setrlimit(kind, (soft_limit, hard_limit))
    except (OSError, ValueError) as err:
        logging.error(
            f"Resource limit for {kind} could not be set to "
            f"[{soft_limit}, {hard_limit}] ({err})"
        )


def get_process_cpu_time(pid):
    """
    Get the cumulative CPU time (user + system) for a process.
    Return None if the process doesn't exist or cannot be accessed.
    """
    try:
        with open(f"/proc/{pid}/stat") as f:
            stat = f.read().split()
            # Fields 14 and 15 are utime and stime in clock ticks
            utime = int(stat[13])
            stime = int(stat[14])
            # Convert clock ticks to seconds (typically 100 ticks per second)
            clock_ticks_per_sec = os.sysconf("SC_CLK_TCK")
            return (utime + stime) / clock_ticks_per_sec
    except (OSError, IndexError, ValueError):
        return None


def get_direct_children(pid):
    """
    Get list of direct child PIDs from /proc/{pid}/task/{pid}/children.

    This is much more efficient than scanning all /proc entries.
    Available since Linux 3.5.
    """
    try:
        # Read the children file which contains space-separated PIDs.
        with open(f"/proc/{pid}/task/{pid}/children") as f:
            children = f.read().strip().split()
            return [int(child) for child in children if child]
    except (OSError, ValueError):
        return []


def get_process_tree_cpu_time(pid):
    """
    Get the cumulative CPU time for a process and all its descendants.
    """
    total_cpu_time = 0.0

    # Get CPU time of main process.
    main_cpu_time = get_process_cpu_time(pid)
    if main_cpu_time is not None:
        total_cpu_time += main_cpu_time

    # Recursively get CPU time of direct children.
    try:
        for child_pid in get_direct_children(pid):
            child_cpu_time = get_process_tree_cpu_time(child_pid)
            total_cpu_time += child_cpu_time
    except OSError:
        pass

    return total_cpu_time


def get_process_tree_pids_and_times(pid):
    """
    Get a dictionary mapping each PID in the process tree to its CPU time.
    """
    pid_times = {}

    # Get CPU time of this process.
    cpu_time = get_process_cpu_time(pid)
    if cpu_time is not None:
        pid_times[pid] = cpu_time

    # Recursively get CPU times of children.
    try:
        for child_pid in get_direct_children(pid):
            child_times = get_process_tree_pids_and_times(child_pid)
            pid_times.update(child_times)
    except OSError:
        pass

    return pid_times


class Call:
    # CPU time monitoring check interval in seconds.
    CPU_TIME_CHECK_INTERVAL = 1.0

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

        The *time_limit* parameter enforces CPU time limits in two ways:
        1. Using RLIMIT_CPU to limit the main process (enforced by the kernel).
        2. Monitoring the cumulative CPU time of the process and all its child
           processes, terminating the process tree if the total exceeds the limit.

        See also the documentation for
        ``lab.experiment._Buildable.add_command()``.

        """
        assert "stdin" not in kwargs, "redirecting stdin is not supported"
        self.name = name
        self.time_limit = time_limit
        self.cpu_time = None
        # Track CPU time per PID to handle sequential children.
        self.pid_cpu_times = {}  # {pid: last_observed_cpu_time}
        self.finalized_cpu_time = 0.0  # Accumulated CPU time from terminated processes

        if time_limit is None:
            self.wall_clock_time_limit = None
        else:
            # Enforce minimum on wall-clock limit to account for disk latencies.
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
                cpu_soft_limit = max(1, math.ceil(time_limit))
                set_limit(resource.RLIMIT_CPU, cpu_soft_limit, cpu_soft_limit + 5)
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

    def _update_cpu_time(self):
        """
        Update CPU time tracking by measuring current process tree.

        Tracks each PID individually and accumulates CPU time from terminated
        processes to handle sequential children correctly.

        Returns the total CPU time or None if measurement fails.
        """
        try:
            # Get current PIDs and their CPU times.
            current_pids_times = get_process_tree_pids_and_times(self.process.pid)

            # Find PIDs that have terminated since last check.
            previous_pids = set(self.pid_cpu_times.keys())
            current_pids = set(current_pids_times.keys())
            terminated_pids = previous_pids - current_pids

            # Accumulate CPU time from terminated PIDs.
            for pid in terminated_pids:
                self.finalized_cpu_time += self.pid_cpu_times[pid]

            # Update tracking with current PIDs.
            self.pid_cpu_times = current_pids_times

            # Calculate total: finalized + current
            current_total = sum(current_pids_times.values())
            total_cpu_time = self.finalized_cpu_time + current_total
            self.cpu_time = total_cpu_time

            return total_cpu_time
        except (OSError, AttributeError):
            return None

    def _monitor_cpu_time(self):
        """
        Monitor the CPU time of the process and all its children.
        Terminate the process if it exceeds the time limit.
        """
        while self.process.poll() is None:
            total_cpu_time = self._update_cpu_time()

            if total_cpu_time is None:
                # Process may have terminated.
                break

            # Check if CPU time limit is exceeded.
            if self.time_limit is not None and total_cpu_time > self.time_limit:
                logging.info(
                    f"{self.name} exceeded CPU time limit: "
                    f"{total_cpu_time:.2f}s > {self.time_limit}s"
                )
                self.process.terminate()
                # Give it a moment to terminate gracefully.
                time.sleep(1)
                if self.process.poll() is None:
                    self.process.kill()
                break

            time.sleep(self.CPU_TIME_CHECK_INTERVAL)

    def cpu_time_limit_exceeded(self, use_slack=False):
        """
        Check if the CPU time limit was exceeded.

        If use_slack is True, add check interval as slack to account for
        measurement granularity.

        """
        if self.time_limit is None or self.cpu_time is None:
            return False
        limit = self.time_limit
        if use_slack:
            limit += self.CPU_TIME_CHECK_INTERVAL
        return self.cpu_time > limit

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
        wall_clock_start_time = time.monotonic()

        # Start CPU time monitoring thread if time limit is set.
        monitor_thread = None
        if self.time_limit is not None:
            monitor_thread = threading.Thread(
                target=self._monitor_cpu_time, daemon=True
            )
            monitor_thread.start()

        self._redirect_streams()
        retcode = self.process.wait()

        # Wait for monitor thread to finish
        if monitor_thread is not None:
            monitor_thread.join(timeout=1)

            # Do a final CPU time measurement to capture any time accumulated
            # between the last monitoring check and process termination.
            self._update_cpu_time()

        for stream, _ in self.redirected_streams_and_limits.values():
            # Write output to disk before the next Call starts.
            stream.flush()
            os.fsync(stream.fileno())

        # Close files that were opened in the constructor.
        for file in self.opened_files:
            file.close()

        wall_clock_time = time.monotonic() - wall_clock_start_time
        logging.info(f"{self.name} wall-clock time: {wall_clock_time:.2f}s")

        # Report CPU time including children.
        if self.cpu_time is not None:
            logging.info(f"{self.name} CPU time: {self.cpu_time:.2f}s")

        if (
            self.wall_clock_time_limit is not None
            and wall_clock_time > self.wall_clock_time_limit
        ):
            logging.error(
                f"wall-clock time for {self.name} too high: "
                f"{wall_clock_time:.2f}s > {self.time_limit}s"
            )
        logging.info(f"{self.name} exit code: {retcode}")
        return retcode
