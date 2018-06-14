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
            'The exit code parser needs the {} attribute. Did you forget to add the'
            ' Lab driver parser and the exit code parser in that order?'.format(attr))
    return exitcode


def parse_exit_code(content, props):
    """
    Convert the exitcode of the planner to a human-readable message and store
    it in props['error']. Additionally, if there was an unexplained error, add
    its source to the list at props['unexplained_errors'].

    For unexplained errors please check the files run.log, run.err,
    driver.log and driver.err to find the reason for the error.

    """
    assert 'error' not in props

    # Check if Fast Downward uses the latest exit codes.
    use_legacy_exit_codes = True
    for line in content.splitlines():
        if (line.startswith('translate exit code:') or
                line.startswith('search exit code:')):
            use_legacy_exit_codes = False
            break

    exitcode = _get_planner_exitcode(props)
    outcome = outcomes.get_outcome(exitcode, use_legacy_exit_codes)
    props['error'] = outcome.msg
    props['coverage'] = int(outcome.msg == 'success')
    if use_legacy_exit_codes:
        props['unsolvable'] = int(outcome.msg == 'unsolvable')
    else:
        props['unsolvable'] = int(
            outcome.msg in ['translate-unsolvable', 'search-unsolvable'])
    if not outcome.explained:
        props.add_unexplained_error(outcome.msg)


class ExitCodeParser(Parser):
    def __init__(self):
        Parser.__init__(self)
        self.add_function(parse_exit_code)


def main():
    print 'Running exit code parser'
    parser = ExitCodeParser()
    parser.parse()


main()
