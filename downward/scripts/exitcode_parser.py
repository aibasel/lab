#! /usr/bin/env python2
# -*- coding: utf-8 -*-
#
# downward uses the lab package to conduct experiments with the
# Fast Downward planning system.
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

"""
Functions for parsing Fast Downward exit codes.
"""

from lab.parser import Parser

# Search exit codes. For the moment, all translator errors result in exit code
# 1 and are thus treated as critical errors.
EXIT_PLAN_FOUND = 0
EXIT_CRITICAL_ERROR = 1
EXIT_INPUT_ERROR = 2
EXIT_UNSUPPORTED = 3
EXIT_UNSOLVABLE = 4
EXIT_UNSOLVED_INCOMPLETE = 5
EXIT_OUT_OF_MEMORY = 6
EXIT_TIMEOUT = 7
EXIT_TIMEOUT_AND_MEMORY = 8

EXIT_PYTHON_SIGKILL = 256 - 9
EXIT_PYTHON_SIGSEGV = 256 - 11
EXIT_PYTHON_SIGXCPU = 256 - 24


def unsolvable(content, props):
    props['unsolvable'] = int(props['fast-downward_returncode'] == EXIT_UNSOLVABLE)


def get_search_error(content, props):
    """
    If there was an error, add its source to the error list at props['error'].

    For unexplained errors please check the files run.log, run.err,
    driver.log and driver.err to find the reason for the error.
    """

    # TODO: Set coverage=1 only if EXIT_PLAN_FOUND is returned.
    # TODO: Check that a plan file exists if coverage=1.

    exitcode_to_error = {
        EXIT_PLAN_FOUND: 'none',
        EXIT_CRITICAL_ERROR: 'unexplained-critical-error',
        EXIT_INPUT_ERROR: 'unexplained-input-error',
        EXIT_UNSUPPORTED: 'unexplained-unsupported-feature-requested',
        EXIT_UNSOLVABLE: 'unsolvable',
        EXIT_UNSOLVED_INCOMPLETE: 'incomplete-search-found-no-plan',
        EXIT_OUT_OF_MEMORY: 'out-of-memory',
        EXIT_TIMEOUT: 'timeout',  # Currently only for portfolios.
        EXIT_TIMEOUT_AND_MEMORY: 'timeout-and-out-of-memory',
        EXIT_PYTHON_SIGKILL: 'unexplained-sigkill',
        EXIT_PYTHON_SIGSEGV: 'unexplained-segfault',
        EXIT_PYTHON_SIGXCPU: 'timeout',
    }

    exitcode = props['fast-downward_returncode']
    if exitcode in exitcode_to_error:
        props.add_error(exitcode_to_error[exitcode])
    else:
        props.add_error('unexplained-exitcode-{}'.format(exitcode))


class ExitCodeParser(Parser):
    def __init__(self):
        Parser.__init__(self)
        self.add_function(get_search_error)
        self.add_function(unsolvable)


def main():
    parser = ExitCodeParser()
    parser.parse()


main()
