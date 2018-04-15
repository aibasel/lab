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
Parse Fast Downward exit code and store a message describing the outcome
in the "error" attribute.
"""

import sys

from lab.parser import Parser

from downward import outcomes


def _get_planner_exitcode(props):
    attr = 'fast-downward_returncode'
    exitcode = props.get(attr)
    if exitcode is None:
        sys.exit(
            'Attribute {} is missing. Did you forget to call'
            ' exp.add_parser("lab_driver_parser", exp.LAB_DRIVER_PARSER)?'.format(attr))
    return exitcode


def get_search_error(content, props):
    """
    Convert the exitcode of the planner to a human-readable message and store
    it in props['error']. Additionally, if there was an unexplained error, add
    its source to the list at props['unexplained_errors'].

    For unexplained errors please check the files run.log, run.err,
    driver.log and driver.err to find the reason for the error.

    """
    assert 'error' not in props

    exitcode = _get_planner_exitcode(props)
    outcome = outcomes.get_outcome(exitcode)
    props['error'] = outcome.msg
    if not outcome.explained:
        props.add_unexplained_error(outcome.msg)


def unsolvable(content, props):
    outcome = outcomes.get_outcome(_get_planner_exitcode(props))
    props['unsolvable'] = int(outcome and outcome.msg == 'unsolvable')


class ExitCodeParser(Parser):
    def __init__(self):
        Parser.__init__(self)
        self.add_function(get_search_error)
        self.add_function(unsolvable)


def main():
    print 'Running exit code parser'
    parser = ExitCodeParser()
    parser.parse()


main()
