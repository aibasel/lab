#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# downward uses the lab package to conduct experiments with the
# Fast Downward planning system.
#
# Copyright (C) 2012  Jendrik Seipp (jendrikseipp@web.de)
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
Regular expressions and functions for parsing planning experiments
"""

from __future__ import division

import re
import math
from collections import defaultdict

# The lab directory is added automatically in the Experiment constructor
from lab.parser import Parser


def _get_states_pattern(attribute, name):
    return (attribute, re.compile(r'%s (\d+) state\(s\)\.' % name), int)


PORTFOLIO_PATTERNS = [
    ('cost', re.compile(r'Plan cost: (.+)'), int),
    ('plan_length', re.compile(r'Plan length: (\d+)'), int),
]


ITERATIVE_PATTERNS = PORTFOLIO_PATTERNS + [
    _get_states_pattern('dead_ends', 'Dead ends:'),
    _get_states_pattern('evaluations', 'Evaluated'),
    _get_states_pattern('expansions', 'Expanded'),
    _get_states_pattern('generated', 'Generated'),
    # We exclude lines like "Initial state h value: 1147184/1703241." that stem
    # from multi-heuristic search.
    ('initial_h_value', re.compile(r'Initial state h value: (\d+)\.'), int),
    # We cannot include " \[t=.+s\]" in the regex, because older versions don't
    # have this information in the log.
    ('search_time', re.compile(r'Actual search time: (.+?)s'), float)
]


CUMULATIVE_PATTERNS = [
    # This time we parse the cumulative values
    _get_states_pattern('dead_ends', 'Dead ends:'),
    _get_states_pattern('evaluations', 'Evaluated'),
    _get_states_pattern('expansions', 'Expanded'),
    _get_states_pattern('generated', 'Generated'),
    _get_states_pattern('reopened', 'Reopened'),
    _get_states_pattern('expansions_until_last_jump', 'Expanded until last jump:'),
    ('search_time', re.compile(r'^Search time: (.+)s$'), float),
    ('total_time', re.compile(r'^Total time: (.+)s$'), float),
    ('memory', re.compile(r'Peak memory: (.+) KB'), int),
    # For iterated searches we discard any h values. Here we will not find
    # anything before the "cumulative" line and stop the search. For single
    # searches we will find the h value if it isn't a multi-heuristic search.
    ('initial_h_value', re.compile(r'Initial state h value: (\d+)\.'), int),
]


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

    # Check that some lists have the same length
    def same_length(group):
        return len(set(len(x) for x in group)) == 1

    group1 = ('cost', 'plan_length')
    assert same_length(values[x] for x in group1), values

    for name, items in values.items():
        props[name + '_all'] = items

    for attr in ['cost', 'plan_length']:
        if values[attr]:
            props[attr] = min(values[attr])


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

    # Check that some lists have the same length
    def same_length(group):
        return len(set(len(x) for x in group)) == 1

    group1 = ('cost', 'plan_length')
    group2 = ('expansions', 'generated', 'search_time')
    assert same_length(values[x] for x in group1), values
    assert same_length(values[x] for x in group2), values

    for name, items in values.items():
        props[name + '_all'] = items

    for attr in ['cost', 'plan_length']:
        if values[attr]:
            props[attr] = min(values[attr])


def get_cumulative_results(content, props):
    """
    Some cumulative results are printed at the end of the logfile. We revert
    the content to make a search for those values much faster. We would have to
    convert the content anyways, because there's no real telling if those
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
    # Iterative searches like lama might report the problem as unsolvable even
    # after they found a solution.
    logged_unsolvable = ('unsolvable' in content or
            'Completely explored state space -- no solution!' in content)
    props['unsolvable'] = int(not props['coverage'] and logged_unsolvable)


def parse_error(content, props):
    props['parse_error'] = 'Parse Error:' in content


def unsupported(content, props):
    props['unsupported'] = 'does not support' in content


def coverage(content, props):
    props['coverage'] = int(('plan_length' in props or 'cost' in props) and
                            not props.get('validate_error'))


def check_memory(content, props):
    """
    Set "memory" to the max value if it was exceeded and "-1 KB" was reported
    """
    memory = props.get('memory')
    memory_limit = props.get('limit_search_memory', None)
    if memory == -1:
        if memory_limit is not None:
            # Turn into KB
            memory_limit *= 1024
        props['memory'] = memory_limit


def scores(content, props):
    """
    Some reported results are measured via scores from the
    range 0-1, where best possible performance in a task is
    counted as 1, while failure to solve a task and worst
    performance are counted as 0
    """
    def log_score(value, min_bound, max_bound, min_score):
        if value is None:
            return 0
        if value < min_bound:
            value = min_bound
        if value > max_bound:
            value = max_bound
        raw_score = math.log(value) - math.log(max_bound)
        best_raw_score = math.log(min_bound) - math.log(max_bound)
        score = min_score + (1 - min_score) * (raw_score / best_raw_score)
        return round(score * 100, 2)

    # Maximum memory in KB
    max_memory = (props.get('limit_search_memory') or 2048) * 1024

    props.update({'score_expansions': log_score(props.get('expansions'),
                    min_bound=100, max_bound=1000000, min_score=0.0),
            'score_evaluations': log_score(props.get('evaluations'),
                    min_bound=100, max_bound=1000000, min_score=0.0),
            'score_memory': log_score(props.get('memory'),
                    min_bound=2000, max_bound=max_memory, min_score=0.0),
            'score_total_time': log_score(props.get('total_time'),
                    min_bound=1.0, max_bound=1800.0, min_score=0.0),
            'score_search_time': log_score(props.get('search_time'),
                    min_bound=1.0, max_bound=1800.0, min_score=0.0)})


def check_min_values(content, props):
    """
    Ensure that times are at least 0.1s if they are present in log
    """
    for time in ['search_time', 'total_time']:
        sec = props.get(time, None)
        if sec is not None:
            sec = max(sec, 0.1)
            props[time] = sec


def parse_last_loggings(content, props):
    patterns = [('last_logged_time', re.compile(r'total_time: (.+)s')),
                ('last_logged_wall_clock_time', re.compile(r'wall-clock time: (.+)')),
                ('last_logged_memory', re.compile(r'total_vsize: (.+) MB'))]
    new_props = {}
    for line in reversed(content.splitlines()):
        for attr, regex in patterns:
            match = regex.search(line)
            if match and attr not in new_props:
                new_props[attr] = float(match.group(1))
        # We can stop once we have found the last value for each attribute.
        if len(new_props) == 3:
            break
    props.update(new_props)


def get_error(content, props):
    """
    If there was an error, its source will be stored in props['error'].
    Possible values are
      * none: No error, coverage = 1
      * unsolvable: No error, planner reported that problem is unsolvable
      * timeout: planner exceeded time limit (recognized by signal SIGXCPU)
      * mem-limit-exceeded: planner exceeded memory limit
        (recognized by bad_alloc exception)

    The following reasons should never occur. If they do, this is an indication that
    something went completely wrong, either in the lab framework or on the executing
    computer. Check the files run.log, run.err, driver.log and driver.err for further
    details.

      * unexplained-timeout: lab stopped the planner due to a timeout.
      * unexplained-wall-clock-timeout: lab stopped the planner due to a
        wall clock timeout.
      * unexplained-mem-limit-exceeded: lab stopped the planner due to
        exceeded memory.
      * unexplained-probably-timeout: The planner was stopped with
        return code 128+9 (SIGKILL).
        The last logged entries for time and memory point to an unrecognized timeout.
      * unexplained-probably-mem-limit-exceeded: The planner was stopped with
        return code 128+9 (SIGKILL).
        The last logged entries for time and memory point to an unrecognized memory out.
      * unexplained-sigkill: The planner was stopped with return code 128+9 (SIGKILL)
        before reaching its time or memory limits or reaching both roughly at the same
        time.
      * unexplained: The planner did not produce a plan but was not killed with SIGKILL.
    """
    # Ignore search_error attribute. It only tells us whether returncode != 0.
    if 'search_error' in props:
        del props['search_error']
    # If there is any error, do no count this task as solved.
    if props.get('error') is not None:
        props['coverage'] = 0

    # If coverage is 0, try to explain this
    if props.get('coverage') == 0:
        # First see if we already know the type of error.
        if props.get('unsolvable', None) == 1:
            props['error'] = 'unsolvable'
        elif props.get('validate_error', None) == 1:
            props['error'] = 'invalid-solution'
        # If we don't know the error type already, look at the error log.
        elif 'bad_alloc' in content:
            props['error'] = 'mem-limit-exceeded'
            props['search_mem_limit_exceeded'] = 1
        # If the run was killed with SIGXCPU (return code: 128 + 24 (SIGXCPU) = 152),
        # we know it hit its CPU limit.
        elif props.get('search_returncode', None) == 152:
            props['error'] = 'timeout'
            props['search_timeout'] = 1
        # Maybe the run was stopped by lab
        elif props.get('error') in ['unexplained-timeout',
                                    'unexplained-wall-clock-timeout',
                                    'unexplained-mem-limit-exceeded']:
            # Error reason is already set by lab.
            pass
        # If the run was killed with SIGKILL (return code: 128 + 9 (SIGKILL) = 137),
        # we can assume it was because it hit its resource limits.
        # For other or unknown return values we don't want to hide potential problems.
        elif props.get('search_returncode', None) == 137:
            remaining_time = (props['limit_search_time'] -
                              props.get('last_logged_time', 0))
            remaining_memory = (props['limit_search_memory'] -
                                props.get('last_logged_memory', 0))
            remaining_time_rel = remaining_time / float(props['limit_search_time'])
            remaining_memory_rel = remaining_memory / float(props['limit_search_memory'])
            fraction = 0.05
            if remaining_time_rel < fraction and remaining_memory_rel > fraction:
                props['error'] = 'unexplained-probably-timeout'
            elif remaining_memory_rel < fraction and remaining_time_rel > fraction:
                props['error'] = 'unexplained-probably-mem-limit-exceeded'
            else:
                props['error'] = 'unexplained-sigkill'
        elif props.get('search_returncode') == 1:
            # TODO: Currently, this may hide potential errors on single searches.
            props['error'] = 'no-plan'
            props['no_plan'] = 1
        else:
            props['error'] = 'unexplained'

    pos_outcomes = ['coverage', 'unsolvable']
    neg_outcomes = ['search_timeout', 'search_mem_limit_exceeded',
                    'no_plan', 'unexplained_error']
    outcomes = pos_outcomes + neg_outcomes

    # Set all outcomes that did not occur to 0, so it is possible to sum over
    # all outcomes.
    for outcome in outcomes:
        if props.get(outcome) is None:
            props[outcome] = 0

    props['unexplained_error'] = not any(props.get(outcome) for outcome in outcomes)

    # Check that all errors that occured are handled in exactly one of the categories.
    assert (sum(props[outcome] for outcome in outcomes) == 1), props


class SearchParser(Parser):
    def __init__(self):
        Parser.__init__(self)

        # TODO: search run.err once parse errors are printed there
        self.add_function(parse_error)
        self.add_function(parse_last_loggings, file='driver.log')
        self.add_function(get_iterative_results)
        self.add_function(coverage)
        self.add_function(unsupported, 'run.err')
        self.add_function(unsolvable)
        self.add_function(get_error, 'run.err')


class SingleSearchParser(SearchParser):
    def __init__(self):
        SearchParser.__init__(self)

        self.add_pattern('landmarks', r'Discovered (\d+?) landmarks', type=int,
                         required=False)
        self.add_pattern('landmarks_generation_time',
                         r'Landmarks generation time: (.+)s', type=float,
                         required=False)

        self.add_function(get_cumulative_results)
        self.add_function(check_memory)
        self.add_function(set_search_time)
        self.add_function(scores)
        self.add_function(check_min_values)


class PortfolioParser(SearchParser):
    def __init__(self):
        SearchParser.__init__(self)
        self.add_function(get_iterative_portfolio_results)


if __name__ == '__main__':
    parser = SingleSearchParser()

    # Change parser type if we are parsing a portfolio.
    planner_type = parser.props['planner_type']
    if planner_type == 'single':
        print 'Running single search parser'
    else:
        assert planner_type == 'portfolio', planner_type
        parser = PortfolioParser()
        print 'Running portfolio parser'

    parser.parse()
