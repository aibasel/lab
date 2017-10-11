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


# Exit codes.
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


def solved(run):
    return run['coverage'] or run['unsolvable']


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


CUMULATIVE_PATTERNS = COMMON_PATTERNS + [
    # Keep old names for backwards compatibility.
    _get_states_pattern('evaluations_until_last_jump', 'Evaluated until last jump:'),
    _get_states_pattern('expansions_until_last_jump', 'Expanded until last jump:'),
    _get_states_pattern('generated_until_last_jump', 'Generated until last jump:'),
    _get_states_pattern('reopened_until_last_jump', 'Reopened until last jump:'),
    ('search_time', re.compile(r'^Search time: (.+)s$'), float),
    ('total_time', re.compile(r'^Total time: (.+)s$'), float),
    ('raw_memory', re.compile(r'Peak memory: (.+) KB'), int),
]


def _same_length(groups):
    return len(set(len(x) for x in groups)) == 1


def _update_props_with_iterative_values(props, values, attr_groups):
    for group in attr_groups:
        if not _same_length(values[attr] for attr in group):
            print 'Error: malformed log:', values
            props.add_error('unexplained-malformed-log')

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


def get_cumulative_results(content, props):
    """
    Some cumulative results are printed at the end of the logfile. We revert
    the content to make a search for those values much faster. We would have to
    reverse the content anyways, because there's no real telling if those
    values talk about a single or a cumulative result. If we start parsing at
    the bottom of the file we know that the values are the cumulative ones.
    """
    reverse_content = list(reversed(content.splitlines()))
    for name, pattern, cast in CUMULATIVE_PATTERNS:
        for line in reverse_content:
            # There will be no cumulative values above this line
            if line == 'Cumulative statistics:':
                break
            match = pattern.search(line)
            if not match:
                continue
            props[name] = cast(match.group(1))


def set_search_time(content, props):
    """
    If iterative search has accumulated single search times, but the total
    search time was not written (due to a possible timeout for example), we
    set search_time to be the sum of the single search times.
    """
    if 'search_time' in props:
        return
    search_time_all = props.get('search_time_all', [])
    # Do not write search_time if no iterative search_time has been found.
    if search_time_all:
        props['search_time'] = math.fsum(search_time_all)


def unsolvable(content, props):
    props['unsolvable'] = int(props['fast-downward_returncode'] == EXIT_UNSOLVABLE)


def coverage(content, props):
    props['coverage'] = int('plan_length' in props and 'cost' in props)


def get_initial_h_values(content, props):
    """
    For each heuristic, collect the reported initial heuristic values in
    a list. For iterative searches this list may contain more than one
    value. Add a dictionary mapping from heuristics to initial heuristic
    values to the properties. If exactly one initial heuristic value was
    reported, add it to the properties under the name "initial_h_value".
    """
    heuristic_to_values = defaultdict(list)
    matches = re.findall(
        r'^Initial heuristic value for (.+): ([-]?\d+|infinity)$',
        content, flags=re.M)
    for heuristic, init_h in matches:
        if init_h == "infinity":
            init_h = sys.maxint
        else:
            init_h = int(init_h)
        heuristic_to_values[heuristic].append(init_h)

    props['initial_h_values'] = heuristic_to_values

    if len(heuristic_to_values) == 1:
        for heuristic, values in heuristic_to_values.items():
            if len(values) == 1:
                props['initial_h_value'] = values[0]


def check_memory(content, props):
    """Add "memory" attribute if the problem was solved."""
    raw_memory = props.get('raw_memory')

    if raw_memory is None or raw_memory < 0:
        propsprops.add_error('unexplained-could-not-determine-peak-memory')
        return

    if solved(props):
        props['memory'] = raw_memory


def scores(content, props):
    """
    Some reported results are measured via scores from the
    range 0-1, where best possible performance in a task is
    counted as 1, while failure to solve a task and worst
    performance are counted as 0.
    """
    def log_score(value, min_bound, max_bound):
        if value is None:
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
        print "search time limit missing -> can't compute time scores"
    else:
        props['score_total_time'] = log_score(
            props.get('total_time'), min_bound=1.0, max_bound=max_time)
        props['score_search_time'] = log_score(
            props.get('search_time'), min_bound=1.0, max_bound=max_time)

    try:
        max_memory_kb = props['limit_search_memory'] * 1024
    except KeyError:
        print "search memory limit missing -> can't compute score_memory"
    else:
        props['score_memory'] = log_score(
            props.get('memory'), min_bound=2000, max_bound=max_memory_kb)


def check_min_values(content, props):
    """
    Ensure that times are not 0 if they are present in log.
    """
    for attr in ['search_time', 'total_time']:
        time = props.get(attr, None)
        if time is not None:
            props[attr] = max(time, 0.01)


def get_error(content, props):
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


class SearchParser(Parser):
    def __init__(self):
        Parser.__init__(self)

        self.add_function(get_error)
        self.add_function(get_iterative_results)
        self.add_function(coverage)
        self.add_function(unsolvable)


class SingleSearchParser(SearchParser):
    def __init__(self):
        SearchParser.__init__(self)

        self.add_pattern(
            'landmarks', 'Discovered (\d+?) landmarks',
            type=int, required=False)
        self.add_pattern(
            'landmarks_generation_time', 'Landmarks generation time: (.+)s',
            type=float, required=False)
        self.add_pattern(
            'limit_search_time', 'search time limit: (\d+)s',
            type=int, required=False)
        self.add_pattern(
            'limit_search_memory', 'search memory limit: (\d+) MB',
            type=int, required=False)

        self.add_function(get_cumulative_results)
        self.add_function(check_memory)
        self.add_function(get_initial_h_values)
        self.add_function(set_search_time)
        self.add_function(scores)
        self.add_function(check_min_values)


class PortfolioParser(SearchParser):
    def __init__(self):
        SearchParser.__init__(self)
        self.add_function(get_iterative_portfolio_results)


def parse_planner_type(content, props):
    match = re.search(r'^INFO     search portfolio:', content, re.M)
    if match:
        props['planner_type'] = 'portfolio'
    else:
        props['planner_type'] = 'single'


def get_planner_type():
    planner_type_parser = Parser()
    planner_type_parser.add_function(parse_planner_type)
    planner_type_parser.parse()
    return planner_type_parser.props['planner_type']


def main():
    planner_type = get_planner_type()
    if planner_type == 'single':
        print 'Running single search parser'
        parser = SingleSearchParser()
    else:
        assert planner_type == 'portfolio', planner_type
        print 'Running portfolio parser'
        parser = PortfolioParser()

    parser.parse()


main()
