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

import logging
import resource
import subprocess
import time

from lab.calls.log import set_property


def set_limit(kind, soft_limit, hard_limit=None):
    hard_limit = hard_limit or soft_limit
    try:
        resource.setrlimit(kind, (soft_limit, hard_limit))
    except (OSError, ValueError), err:
        print ("Resource limit for %s could not be set to %s (%s)" %
               (kind, (soft_limit, hard_limit), err))


class Call(subprocess.Popen):
    def __init__(self, args, name='call', time_limit=1800, mem_limit=2048, **kwargs):
        """Make system calls with time and memory constraints.

        *args* and *kwargs* are passed to the base class
        `subprocess.Popen <http://docs.python.org/library/subprocess.html>`_.

        *time_limit* and *mem_limit* are the time and memory contraints in
        seconds and MiB.

        Previously, not only the main process, but also all spawned
        child processes were watched. This functionality has been removed
        to simplify the code and reduce wait times in between checking
        whether the process has finished. As a result the options
        *kill_delay* and *check_interval* are now ignored.
        """
        for deprecated_arg in ['kill_delay', 'check_interval']:
            if deprecated_arg in kwargs:
                logging.warning('The "%s" argument is obsolete and will be ignored.' %
                                deprecated_arg)
                del kwargs[deprecated_arg]

        self.name = name
        # Use wall-clock limit of 30 seconds for very small time limits.
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
            # padding between the two limits allows us to distinguish between
            # SIGKILL signals sent by this class and the ones sent by the
            # system.
            set_limit(resource.RLIMIT_CPU, time_limit, time_limit + 5)
            # Memory in Bytes.
            set_limit(resource.RLIMIT_AS, mem_limit * 1024 * 1024)
            set_limit(resource.RLIMIT_CORE, 0)

        self.wall_clock_start_time = time.time()
        subprocess.Popen.__init__(self, args, preexec_fn=prepare_call, **kwargs)

    def wait(self):
        retcode = subprocess.Popen.wait(self)
        wall_clock_time = time.time() - self.wall_clock_start_time
        # TODO: Put directly into properties.
        print '%s wall-clock time: %.2fs' % (self.name, wall_clock_time)
        if wall_clock_time > self.wall_clock_time_limit:
            set_property('error', 'unexplained-wall-clock-timeout')
        return retcode
