# -*- coding: utf-8 -*-
#
# lab is a Python API for running and evaluating algorithms.
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

import resource
import subprocess
import sys
import time

from lab.calls.log import set_property


def set_limit(kind, soft_limit, hard_limit=None):
    if hard_limit is None:
        hard_limit = soft_limit
    try:
        resource.setrlimit(kind, (soft_limit, hard_limit))
    except (OSError, ValueError), err:
        sys.stderr.write(
            'Resource limit for %s could not be set to %s (%s)\n' %
            (kind, (soft_limit, hard_limit), err))


class Call(subprocess.Popen):
    def __init__(self, args, name='call', time_limit=None, mem_limit=None, **kwargs):
        """Make system calls with time and memory constraints.

        *args* and *kwargs* are passed to the base class
        `subprocess.Popen <http://docs.python.org/library/subprocess.html>`_.

        *time_limit* and *mem_limit* are the time and memory contraints in
        seconds and MiB. Pass None to enforce no limit.

        Previously, not only the main process, but also all spawned
        child processes were watched. This functionality has been removed
        to simplify the code and reduce wait times in between checking
        whether the process has finished. As a result the options
        *kill_delay* and *check_interval* are now ignored.
        """
        self.name = name
        if time_limit is None:
            self.wall_clock_time_limit = None
        else:
            # Enforce miminum on wall-clock limit to account for disk latencies.
            self.wall_clock_time_limit = max(30, time_limit * 1.5)

        stdin = kwargs.get('stdin')
        if isinstance(stdin, basestring):
            kwargs['stdin'] = open(stdin)

        for stream_name in ['stdout', 'stderr']:
            stream = kwargs.get(stream_name)
            if isinstance(stream, basestring):
                kwargs[stream_name] = open(stream, 'w')

        def prepare_call():
            # When the soft time limit is reached, SIGXCPU is emitted. Once we
            # reach the higher hard time limit, SIGKILL is sent. Having some
            # padding between the two limits allows programs to handle SIGXCPU.
            if time_limit is not None:
                set_limit(resource.RLIMIT_CPU, time_limit, time_limit + 5)
            if mem_limit is not None:
                # Convert memory from MiB to Bytes.
                set_limit(resource.RLIMIT_AS, mem_limit * 1024 * 1024)
            set_limit(resource.RLIMIT_CORE, 0)

        subprocess.Popen.__init__(self, args, preexec_fn=prepare_call, **kwargs)

    def wait(self):
        wall_clock_start_time = time.time()
        retcode = subprocess.Popen.wait(self)
        wall_clock_time = time.time() - wall_clock_start_time
        set_property('%s_wall_clock_time' % self.name, wall_clock_time)
        if (self.wall_clock_time_limit is not None and
                wall_clock_time > self.wall_clock_time_limit):
            set_property('error', 'unexplained-warning-wall-clock-time-very-high')
            sys.stderr.write(
                'Error: wall-clock time for %s too high: %.2f > %d\n' %
                (self.name, wall_clock_time, self.wall_clock_time_limit))
        return retcode
