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

from lab.parser import Parser


def add_planner_memory(content, props):
    try:
        props['planner_memory'] = max(props['translator_peak_memory'], props['memory'])
    except KeyError:
        pass


def add_planner_time(content, props):
    try:
        props['planner_time'] = props['translator_time_done'] + props['total_time']
    except KeyError:
        pass


class PlannerParser(Parser):
    def __init__(self):
        Parser.__init__(self)
        self.add_function(add_planner_memory)
        self.add_function(add_planner_time)

        self.add_pattern(
            'node',
            r'node: (.+)\n',
            type=str,
            file='driver.log',
            required=True)
        self.add_pattern(
            'planner_wall_clock_time',
            r'planner wall-clock time: (.+)s',
            type=float,
            file='driver.log',
            required=True)


def main():
    parser = PlannerParser()
    parser.parse()


main()
