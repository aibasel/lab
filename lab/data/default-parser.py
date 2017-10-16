#! /usr/bin/env python2

from lab.parser import Parser


def check_stderr_output(content, props):
    if content:
        props.add_unexplained_error('output-to-run-err')


def check_driver_stderr_output(content, props):
    if content:
        props.add_unexplained_error('output-to-driver-err')


def check_driver_failures(content, props):
    pass


def main():
    print "Running Lab default parser"
    p = Parser()
    p.add_function(check_stderr_output, file='run.err')
    p.add_function(check_driver_stderr_output, file='driver.err')
    p.add_function(check_driver_failures)
    p.parse()


main()
