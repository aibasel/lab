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
Regular expressions and functions for parsing Fast Downward experiments.
"""

from __future__ import division

from collections import defaultdict
import math
import re
import sys

from lab.parser import Parser


def _get_states_pattern(attribute, name):
    return (attribute, re.compile(r'%s (\d+) state\(s\)\.' % name), int)


PORTFOLIO_PATTERNS = [
    ('cost', re.compile(r'Plan cost: (.+)'), float),
    ('plan_length', re.compile(r'Plan length: (\d+)'), int),
]


COMMON_PATTERNS = [
    _get_states_pattern('dead_ends', 'Dead ends:'),
    _get_states_pattern('evaluated', 'Evaluated'),
    ('evaluations', re.compile(r'^Evaluations: (.+)$'), int),
    _get_states_pattern('expansions', 'Expanded'),
    _get_states_pattern('generated', 'Generated'),
    _get_states_pattern('reopened', 'Reopened'),
]


ITERATIVE_PATTERNS = COMMON_PATTERNS + PORTFOLIO_PATTERNS + [
    # We cannot include " \[t=.+s\]" (global timer) in the regex, because
    # older versions don't print it.
    ('search_time', re.compile(r'Actual search time: (.+?)s'), float)
]


def _same_length(groups):
    return len(set(len(x) for x in groups)) == 1


def _update_props_with_iterative_values(props, values, attr_groups):
    for group in attr_groups:
        if not _same_length(values[attr] for attr in group):
            print 'Error: malformed log:', values
            props.add_unexplained_error('malformed-log')

    for name, items in values.items():
        props[name + '_all'] = items

    for attr in ['cost', 'plan_length']:
        if values[attr]:
            props[attr] = min(values[attr])


def get_iterative_portfolio_results(content, props):
    values = defaultdict(list)

    for line in content.splitlines():
        for name, pattern, cast in PORTFOLIO_PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            values[name].append(cast(match.group(1)))
            # We can break here, because each line contains only one value
            break

    _update_props_with_iterative_values(props, values, [('cost', 'plan_length')])


def get_iterative_results(content, props):
    """
    In iterative search some attributes like plan cost can have multiple
    values, i.e. one value for each iterative search. We save those values in
    lists.
    """
    values = defaultdict(list)

    for line in content.splitlines():
        # At the end of iterative search some statistics are printed and we do
        # not want to parse those here.
        if line == 'Cumulative statistics:':
            break
        for name, pattern, cast in ITERATIVE_PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            values[name].append(cast(match.group(1)))
            # We can break here, because each line contains only one value
            break

    # After iterative search completes there is another line starting with
    # "Actual search time" that just states the cumulative search time.
    # In order to let all lists have the same length, we omit that value here.
    if len(values['search_time']) > len(values['expansions']):
        values['search_time'].pop()

    _update_props_with_iterative_values(
        props, values, [
            ('cost', 'plan_length'),
            ('expansions', 'generated', 'search_time')])


def coverage(content, props):
    props['coverage'] = int('plan_length' in props and 'cost' in props)


class PortfolioParser(Parser):
    def __init__(self):
        Parser.__init__(self)

        self.add_function(get_iterative_results)
        self.add_function(coverage)
        self.add_function(get_iterative_portfolio_results)


def main():
    print 'Running portfolio parser'
    parser = PortfolioParser()
    parser.parse()


main()
