#! /usr/bin/env python

import sys

from lab.parser import Parser


MAX_LOG_SIZE_IN_KB = 100 * 1024


def check_log_size(content, props):
    log_size_in_kb = sys.getsizeof(content) / 1024
    props['log_size_in_kb'] = log_size_in_kb
    if log_size_in_kb > MAX_LOG_SIZE_IN_KB:
        props['error'] = 'unexplained-error:logfile-too-big ({} KB > {} KB)'.format(
            log_size_in_kb, MAX_LOG_SIZE_IN_KB)


def check_driver_failures(content, props):
    pass


def main():
    p = Parser()
    p.add_function(check_log_size)
    p.add_function(check_driver_failures)
    p.parse()


main()
