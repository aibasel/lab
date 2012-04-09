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
from collections import defaultdict

# The lab directory is added automatically in the Experiment constructor
from lab.parser import Parser


# Search functions ------------------------------------------------------------

def _get_states_pattern(attribute, name):
    return (attribute, re.compile(r'%s (\d+) state\(s\)\.' % name), int)

ITERATIVE_PATTERNS = [
    # This time we parse the cumulative values
    #_get_states_pattern('dead_ends', 'Dead ends:'),
    #_get_states_pattern('evaluations', 'Evaluated'),
    #_get_states_pattern('expansions', 'Expanded'),
    #_get_states_pattern('generated', 'Generated'),
    #('search_time', re.compile(r'^Search time: (.+)s$'), float),
    #('total_time', re.compile(r'^Total time: (.+)s$'), float),
    #('memory', re.compile(r'Peak memory: (.+) KB'), int),
    ('cost', re.compile(r'Plan cost: (.+)'), int),
    ('plan_length', re.compile(r'Plan length: (\d+)'), int),
    ]


def get_iterative_results(content, props):
    """
    In iterative search some attributes like plan cost can have multiple
    values, i.e. one value for each iterative search. We save those values in
    lists.
    """
    values = defaultdict(list)

    for line in content.splitlines():
        for name, pattern, cast in ITERATIVE_PATTERNS:
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


def parse_error(content, props):
    props['parse_error'] = 'Parse Error:' in content


def unsupported(content, props):
    props['unsupported'] = 'does not support' in content


def coverage(content, props):
    props['coverage'] = int('plan_length' in props or 'cost' in props)

# -----------------------------------------------------------------------------


def get_error(content, props):
    if not content.strip():
        props["error"] = "none"
    elif "bad_alloc" in content:
        props["error"] = "memory"
    else:
        props["error"] = "unknown"


class PortfolioParser(Parser):
    def __init__(self):
        Parser.__init__(self)
        self.add_search_functions()

    def add_search_functions(self):
        self.add_function(parse_error)  # TODO: search run.err once parse errors are printed there
        self.add_function(unsupported, 'run.err')
        self.add_function(get_iterative_results)
        self.add_function(coverage)
        self.add_function(get_error, "run.err")


if __name__ == '__main__':
    print 'Running portfolio parser'
    parser = PortfolioParser()
    parser.parse()
