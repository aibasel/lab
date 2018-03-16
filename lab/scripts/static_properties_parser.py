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
Read a json dict from the file 'static_run.properties' and write it to 'properties'
"""

from lab.tools import Properties

import logging
import os


# TODO: this should read from the run script itself, where the static information should live.
def main():
    read_from = "static_run.properties"
    write_to = "properties"
    if not os.path.exists(read_from):
        logging.critical("{} does not exist!".format(read_from))
    props = Properties(filename=write_to)
    props.load(read_from)
    print("Adding properties from {} to properties".format(read_from))
    props.write()


main()
