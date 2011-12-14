import os

JIFFIES_PER_SECOND = 100


class Process(object):
    def __init__(self, pid):
        stat = open("/proc/%d/stat" % pid).read()
        cmdline = open("/proc/%d/cmdline" % pid).read()

        # Don't use stat.split(): the command can contain spaces.
        # Be careful which "()" to match: the command name can contain
        # parentheses.
        prefix, lparen, rest = stat.partition("(")
        command, rparen, suffix = rest.rpartition(")")
        parts = suffix.split()

        self.pid = pid
        self.ppid = int(parts[1])
        self.pgrp = int(parts[2])
        self.utime = int(parts[11])
        self.stime = int(parts[12])
        self.cutime = int(parts[13])
        self.cstime = int(parts[14])
        self.vsize = int(parts[20])
        self.cmdline = cmdline.rstrip("\0\n").replace("\0", " ")

    def total_time(self):
        return self.utime + self.stime + self.cutime + self.cstime


def read_processes():
    for filename in os.listdir("/proc"):
        if filename.isdigit():
            pid = int(filename)
            # Be careful about a race conditions here: The process
            # may have disappeared after the os.listdir call.
            try:
                yield Process(pid)
            except EnvironmentError:
                pass


class ProcessGroup(object):
    def __init__(self, pgrp):
        self.processes = [process for process in read_processes()
                          if process.pgrp == pgrp]

    def __nonzero__(self):
        return bool(self.processes)

    def pids(self):
        return [p.pid for p in self.processes]

    def total_time(self):
        # Cumulated time for this process group, in seconds
        total_jiffies = sum([p.total_time() for p in self.processes])
        return total_jiffies / float(JIFFIES_PER_SECOND)

    def total_vsize(self):
        # Cumulated virtual memory for this process group, in MB
        total_bytes = sum([p.vsize for p in self.processes])
        return total_bytes / float(2 ** 20)
