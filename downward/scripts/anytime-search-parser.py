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
Parse cost, coverage and plan_length attributes for Fast Downward runs.
"""

from __future__ import division

import re

from lab.parser import Parser


def _get_flags(flags_string):
    flags = 0
    for char in flags_string:
        flags |= getattr(re, char)
    return flags


class AnytimeParser(Parser):
    def add_repeated_pattern(self, name, regex, file='run.log', type=int, flags='M'):
        """
        *regex* must contain at most one group.
        """
        flags = _get_flags(flags)

        def find_all_occurences(content, props):
            matches = re.findall(regex, content, flags=flags)
            props[name] = [type(m) for m in matches]

        self.add_function(find_all_occurences, file=file)


def reduce_to_min(list_name, single_name):
    def reduce_to_minimum(content, props):
        values = props.get(list_name, [])
        if values:
            min_value = min(values)
            assert min_value == values[-1]
            props[single_name] = min_value

    return reduce_to_minimum


def coverage(content, props):
    props['coverage'] = int('cost' in props)


def main():
    print 'Running anytime parser'
    parser = AnytimeParser()
    parser.add_repeated_pattern('cost:all', r'^Plan cost: (.+)$', type=float)
    parser.add_function(reduce_to_min('cost:all', 'cost'))
    parser.add_function(coverage)
    parser.parse()


main()
