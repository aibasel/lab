# -*- coding: utf-8 -*-
#
# lab is a Python API for running and evaluating algorithms.
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

from lab.tools import Properties

redirects = {'stdout': open('run.log', 'a'), 'stderr': open('run.err', 'a')}
driver_log = open('driver.log', 'a')
driver_err = open('driver.err', 'a')


def print_(stream, text):
    stream.write('%s\n' % text)
    stream.flush()

def set_property(name, value):
    properties = Properties(filename='properties')
    properties[name] = value
    properties.write()

def save_returncode(command_name, value):
    set_property('%s_returncode' % command_name.lower(), str(value))
    error = 0 if value == 0 else 1
    set_property('%s_error' % command_name.lower(), error)
