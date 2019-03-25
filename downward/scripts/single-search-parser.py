#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Downward Lab uses the Lab package to conduct experiments with the
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
Regular expressions and functions for parsing single-search runs of Fast Downward.
"""

from __future__ import print_function

import math
import re
import sys

from lab.parser import Parser


def _get_states_pattern(attribute, name):
    return (attribute, r'{name} (\d+) state\(s\)\.'.format(**locals()), int)


PATTERNS = [
    ('limit_search_time', r'search time limit: (.+)s', float),
    ('limit_search_memory', r'search memory limit: (\d+) MB', int),
    ('raw_memory', r'Peak memory: (.+) KB', int),
    ('cost', r'Plan cost: (.+)\n', float),
    ('plan_length', r'Plan length: (\d+) step\(s\)\.', int),
    ('evaluations', r'Evaluations: (.+)\n', int),
    _get_states_pattern('dead_ends', 'Dead ends:'),
    _get_states_pattern('evaluated', 'Evaluated'),
    _get_states_pattern('expansions', 'Expanded'),
    _get_states_pattern('generated', 'Generated'),
    _get_states_pattern('reopened', 'Reopened'),
    _get_states_pattern('evaluations_until_last_jump', 'Evaluated until last jump:'),
    _get_states_pattern('expansions_until_last_jump', 'Expanded until last jump:'),
    _get_states_pattern('generated_until_last_jump', 'Generated until last jump:'),
    _get_states_pattern('reopened_until_last_jump', 'Reopened until last jump:'),
    ('search_time', r'Search time: (.+)s', float),
    ('total_time', r'Total time: (.+)s', float),
]


def check_single_search(content, props):
    if 'Cumulative statistics:' in content:
        props.add_unexplained_error(
            'single-search parser can\'t be used for iterated search')
    for name, pattern, _ in PATTERNS:
        results = re.findall(pattern, content)
        if len(results) > 1:
            props.add_unexplained_error(
                'single-search parser can\'t be used for anytime planner')


def add_coverage(content, props):
    props['coverage'] = int('cost' in props)


def add_initial_h_values(content, props):
    """
    Add a mapping from heuristic names to initial h values.

    If exactly one initial heuristic value was reported, add it to the
    properties under the name "initial_h_value".

    """
    initial_h_values = {}
    matches = re.findall(
        r'Initial heuristic value for (.+): ([-]?\d+|infinity)$',
        content, flags=re.M)
    for heuristic, init_h in matches:
        if init_h == "infinity":
            init_h = sys.maxsize
        else:
            init_h = int(init_h)
        if heuristic in initial_h_values:
            props.add_unexplained_error(
                'multiple initial h values found for {}'.format(heuristic))
        initial_h_values[heuristic] = init_h

    props['initial_h_values'] = initial_h_values

    if len(initial_h_values) == 1:
        props['initial_h_value'] = list(initial_h_values.values())[0]


def add_memory(content, props):
    """Add "memory" attribute if the run was not aborted.

    Peak memory usage is printed even for runs that are terminated
    abnormally. For these runs we do not take the reported value into
    account since the value is censored: it only takes into account the
    memory usage until termination.

    """
    raw_memory = props.get('raw_memory')
    if raw_memory is not None:
        if raw_memory < 0:
            props.add_unexplained_error('planner failed to log peak memory')
        elif 'total_time' in props:
            props['memory'] = raw_memory


def add_scores(content, props):
    """
    Convert some properties into scores in the range [0, 1].

    Best possible performance in a task is counted as 1, while failure
    to solve a task and worst performance are counted as 0.

    """
    def log_score(value, min_bound, max_bound):
        if value is None or not props['coverage']:
            return 0
        value = max(value, min_bound)
        value = min(value, max_bound)
        raw_score = math.log(value) - math.log(max_bound)
        best_raw_score = math.log(min_bound) - math.log(max_bound)
        return raw_score / best_raw_score

    for attr in ('expansions', 'evaluations', 'generated'):
        props['score_' + attr] = log_score(
            props.get(attr), min_bound=100, max_bound=1e6)

    try:
        max_time = props['limit_search_time']
    except KeyError:
        print("search time limit missing -> can't compute time scores")
    else:
        props['score_total_time'] = log_score(
            props.get('total_time'), min_bound=1.0, max_bound=max_time)
        props['score_search_time'] = log_score(
            props.get('search_time'), min_bound=1.0, max_bound=max_time)

    try:
        max_memory_kb = props['limit_search_memory'] * 1024
    except KeyError:
        print("search memory limit missing -> can't compute memory score")
    else:
        props['score_memory'] = log_score(
            props.get('memory'), min_bound=2000, max_bound=max_memory_kb)


def ensure_minimum_times(content, props):
    """
    Ensure that times are not 0 if they are present in log.
    """
    for attr in ['search_time', 'total_time']:
        time = props.get(attr, None)
        if time is not None:
            props[attr] = max(time, 0.01)


class SingleSearchParser(Parser):
    def __init__(self):
        Parser.__init__(self)

        for name, pattern, typ in PATTERNS:
            self.add_pattern(name, pattern, type=typ)

        self.add_function(check_single_search)
        self.add_function(add_coverage)
        self.add_function(add_memory)
        self.add_function(add_initial_h_values)
        self.add_function(ensure_minimum_times)
        self.add_function(add_scores)


def main():
    parser = SingleSearchParser()
    parser.parse()


main()
