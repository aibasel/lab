# -*- coding: utf-8 -*-
#
# lab is a Python API for running and evaluating algorithms.
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

import os

from lab.tools import Properties

DRIVER_PROPERTIES_FILENAME = 'driver-properties'


def print_(stream, text):
    stream.write('%s\n' % text)
    stream.flush()


def delete_file_if_empty(filename):
    if os.path.getsize(filename) == 0:
        os.remove(filename)


def set_property(name, value):
    # Read properties again before each write to ensure consistency.
    # Otherwise we might overwrite results added by parsers.
    properties = Properties(filename=DRIVER_PROPERTIES_FILENAME)
    properties[name] = value
    properties.write()


def add_unexplained_error(error, filename=DRIVER_PROPERTIES_FILENAME):
    # See comment for set_property.
    properties = Properties(filename=filename)
    properties.add_unexplained_error(error)
    properties.write()


def save_returncode(command_name, value):
    set_property('%s_returncode' % command_name.lower(), value)
