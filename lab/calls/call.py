# -*- coding: utf-8 -*-
#
# Lab is a Python package for evaluating algorithms.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import errno
import logging
import os
import resource
import select
import subprocess
import sys
import time

from lab import tools


def set_limit(kind, soft_limit, hard_limit=None):
    if hard_limit is None:
        hard_limit = soft_limit
    try:
        resource.setrlimit(kind, (soft_limit, hard_limit))
    except (OSError, ValueError) as err:
        sys.stderr.write(
            'Resource limit for %s could not be set to %s (%s)\n' %
            (kind, (soft_limit, hard_limit), err))


class Call(object):
    def __init__(self, args, name, time_limit=None, memory_limit=None,
                 soft_stdout_limit=None, hard_stdout_limit=None,
                 soft_stderr_limit=None, hard_stderr_limit=None,
                 **kwargs):
        """Make system calls with time and memory constraints.

        *args* and *kwargs* are passed to `subprocess.Popen
        <http://docs.python.org/library/subprocess.html>`_.

        See also the documentation for
        ``lab.experiment._Buildable.add_command()``.

        """
        assert 'stdin' not in kwargs, 'redirecting stdin is not supported'
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
        for stream_name in ['stdout', 'stderr']:
            stream = kwargs.get(stream_name)
            if isinstance(stream, tools.string_type):
                file = open(stream, mode='w')
                kwargs[stream_name] = file
                self.opened_files.append(file)

        # Allow redirecting and limiting the output to streams.
        self.redirected_streams_and_limits = {}
        for stream_name, soft_limit, hard_limit in [
                ('stdout', get_bytes(soft_stdout_limit), get_bytes(hard_stdout_limit)),
                ('stderr', get_bytes(soft_stderr_limit), get_bytes(hard_stderr_limit))]:
            stream = kwargs.pop(stream_name, None)
            if stream:
                self.redirected_streams_and_limits[stream_name] = (
                    stream, (soft_limit, hard_limit))
                kwargs[stream_name] = subprocess.PIPE

        def prepare_call():
            # When the soft time limit is reached, SIGXCPU is emitted. Once we
            # reach the higher hard time limit, SIGKILL is sent. Having some
            # padding between the two limits allows programs to handle SIGXCPU.
            if time_limit is not None:
                set_limit(resource.RLIMIT_CPU, time_limit, time_limit + 5)
            if memory_limit is not None:
                # Convert memory from MiB to Bytes.
                set_limit(resource.RLIMIT_AS, memory_limit * 1024 * 1024)
            set_limit(resource.RLIMIT_CORE, 0)

        try:
            self.process = subprocess.Popen(
                args, preexec_fn=prepare_call, **kwargs)
        except OSError as err:
            if err.errno == errno.ENOENT:
                sys.exit('Error: Call {name} failed. "{path}" not found'.format(
                    path=args[0], **locals()))
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

        for stream_name, (new_stream, limits) in (
                self.redirected_streams_and_limits.items()):
            old_stream = getattr(self.process, stream_name)
            register_and_append(old_stream, select_POLLIN_POLLPRI)
            fd = old_stream.fileno()
            fd_to_outfile[fd] = new_stream
            fd_to_limits[fd] = limits

        while fd_to_infile:
            try:
                ready = poller.poll()
            except select.error as e:
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
                        if (hard_limit is not None and
                                fd_to_bytes[fd] + len(data) > hard_limit):
                            # Don't write to this outfile in subsequent rounds.
                            fd_to_outfile[fd] = None
                            logging.error(
                                '{} wrote {} KiB (hard limit) to {} ->'
                                ' abort command'.format(
                                    self.name, hard_limit / 1024, outfile.name))
                            self.process.terminate()
                            # Strip extra bytes.
                            data = data[:hard_limit - fd_to_bytes[fd]]
                        outfile.write(tools.get_string(data))
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
                if (soft_limit is not None and bytes_written > soft_limit):
                    logging.error(
                        '{} finished and wrote {} KiB to {} (soft limit: {} KiB)'.format(
                            self.name, bytes_written / 1024, outfile.name,
                            soft_limit / 1024))

    def wait(self):
        wall_clock_start_time = time.time()
        self._redirect_streams()
        retcode = self.process.wait()
        for stream, (soft_limit, _) in self.redirected_streams_and_limits.values():
            # Write output to disk before the next Call starts.
            stream.flush()
            os.fsync(stream.fileno())

        # Close files that were opened in the constructor.
        for file in self.opened_files:
            file.close()
        wall_clock_time = time.time() - wall_clock_start_time
        logging.info('{} wall-clock time: {:.2f}s'.format(self.name, wall_clock_time))
        if (self.wall_clock_time_limit is not None and
                wall_clock_time > self.wall_clock_time_limit):
            logging.error(
                'wall-clock time for %s too high: %.2f > %d\n' %
                (self.name, wall_clock_time, self.wall_clock_time_limit))
        logging.info('{} exit code: {}'.format(self.name, retcode))
        return retcode
