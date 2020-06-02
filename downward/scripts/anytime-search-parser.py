#! /usr/bin/env python
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
Parse anytime-search runs of Fast Downward. This includes iterated
searches and portfolios.
"""

from lab.parser import Parser


def reduce_to_min(list_name, single_name):
    def reduce_to_minimum(content, props):
        values = props.get(list_name, [])
        if values:
            props[single_name] = min(values)

    return reduce_to_minimum


def coverage(content, props):
    props["coverage"] = int("cost" in props)


def main():
    parser = Parser()
    parser.add_repeated_pattern("cost:all", r"Plan cost: (.+)\n", type=float, flags="M")
    parser.add_function(reduce_to_min("cost:all", "cost"))
    parser.add_function(coverage)
    parser.parse()


main()
