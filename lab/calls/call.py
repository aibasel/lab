import os
import resource
import signal
import subprocess
import time

from lab.calls.processgroup import ProcessGroup
from lab.calls.log import set_property


def kill_pgrp(pgrp, sig, show_error=True):
    try:
        os.killpg(pgrp, sig)
    except OSError:
        if not show_error:
            return
        print ("Process group %s could not be killed with signal %s" %
               (pgrp, sig))


def set_limit(kind, amount):
    try:
        resource.setrlimit(kind, (amount, amount))
    except (OSError, ValueError), err:
        print ("Resource limit for %s could not be set to %s (%s)" %
               (kind, amount, err))


class Call(subprocess.Popen):
    def __init__(self, args, time_limit=1800, wall_clock_time_limit=None,
                 mem_limit=2048, kill_delay=5, check_interval=0.1, **kwargs):
        """
        mem_limit =      Memory in MiB
        kill_delay =     How long we wait between SIGTERM and SIGKILL
        check_interval = How often we query the process group status
        """
        self.time_limit = time_limit
        self.wall_clock_time_limit = wall_clock_time_limit or time_limit * 1.5
        self.mem_limit = mem_limit

        self.kill_delay = kill_delay
        self.check_interval = check_interval

        self.log_interval = 5

        stdin = kwargs.get('stdin')
        if type(stdin) is str:
            kwargs['stdin'] = open(stdin)

        for stream_name in ['stdout', 'stderr']:
            stream = kwargs.get(stream_name)
            if type(stream) is str:
                kwargs[stream_name] = open(stream, 'w')

        def prepare_call():
            os.setpgrp()
            set_limit(resource.RLIMIT_CPU, self.time_limit)
            # Memory in Bytes
            set_limit(resource.RLIMIT_AS, self.mem_limit * 1024 * 1024)
            set_limit(resource.RLIMIT_CORE, 0)

        subprocess.Popen.__init__(self, args, preexec_fn=prepare_call, **kwargs)

    def terminate(self):
        print "aborting children with SIGTERM..."
        kill_pgrp(self.pid, signal.SIGTERM)

    def kill(self):
        print "aborting children with SIGKILL..."
        kill_pgrp(self.pid, signal.SIGKILL)

    def log(self, real_time, total_time, total_vsize):
        print "wall-clock time: %.2f" % (time.time() - self.wall_clock_start_time)
        print "[real-time %d] total_time: %.2fs" % (real_time, total_time)
        print "[real-time %d] total_vsize: %.2f MB" % (real_time, total_vsize)
        print

    def wait(self):
        """Wait for child process to terminate.

        If the process' processgroup exceeds any limit it is killed.
        Returns returncode attribute.
        """
        term_attempted = False
        real_time = 0
        last_log_time = 0
        self.wall_clock_start_time = time.time()
        while True:
            try:
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                print 'Keyboard interrupt received'
                self.terminate()

            real_time += self.check_interval

            group = ProcessGroup(self.pid)
            ## Generate the children information before the waitpid call to
            ## avoid a race condition. This way, we know that the pid
            ## is a descendant.

            pid, status = os.waitpid(self.pid, os.WNOHANG)
            if (pid, status) != (0, 0):
                self._handle_exitstatus(status)
                break

            total_time = group.total_time()
            total_vsize = group.total_vsize()

            if real_time >= last_log_time + self.log_interval:
                self.log(real_time, total_time, total_vsize)
                last_log_time = real_time

            try_term = (total_time >= self.time_limit or
                        real_time >= self.wall_clock_time_limit or
                        total_vsize > self.mem_limit)
            try_kill = (total_time >= self.time_limit + self.kill_delay or
                        real_time >= 1.5 * self.wall_clock_time_limit +
                                     self.kill_delay or
                        total_vsize > 1.5 * self.mem_limit)

            if try_term and not term_attempted:
                self.log(real_time, total_time, total_vsize)
                self.terminate()
                term_attempted = True
            elif term_attempted and try_kill:
                self.kill()

        # Even if we got here, there may be orphaned children or something
        # we may have missed due to a race condition. Check for that and kill.

        group = ProcessGroup(self.pid)
        if group:
            # If we have reason to suspect someone still lives, first try to
            # kill them nicely and wait a bit.
            print "Orphaned children found: %s" % group.pids()
            self.terminate()
            time.sleep(1)

        # Either way, kill properly for good measure. Note that it's not clear
        # if checking the ProcessGroup for emptiness is reliable, because
        # reading the process table may not be atomic, so for this last blow,
        # we don't do an emptiness test.
        kill_pgrp(self.pid, signal.SIGKILL, show_error=False)

        return self.returncode
