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

from lab.parser import Parser


def solved(props):
    return props['coverage'] or props['unsolvable']


def add_planner_memory(content, props):
    translate_memory = props['translator_peak_memory']
    search_memory = props.get('memory')
    if search_memory is not None:
        assert solved(props)
        props['planner_peak_memory'] = max(translate_memory, search_memory)


def add_planner_time(content, props):
    translate_time = props['translator_time_done']
    search_time = props.get('total_time')
    if search_time is not None and solved(props):
        props['planner_time'] = translate_time + search_time


class PlannerParser(Parser):
    def __init__(self):
        Parser.__init__(self)
        self.add_function(add_planner_memory)
        self.add_function(add_planner_time)


def main():
    print 'Running planner parser'
    parser = PlannerParser()
    parser.parse()


main()
