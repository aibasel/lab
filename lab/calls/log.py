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


class LazyFile(object):
    def __init__(self, path):
        self._path = path
        self._file = None

    def _ensure_file_opened(self):
        if not self._file:
            self._file = open(self._path, 'w')

    def write(self, s):
        self._ensure_file_opened()
        self._file.write(s)

    def fileno(self):
        self._ensure_file_opened()
        return self._file.fileno()

    def flush(self):
        if self._file:
            self._file.flush()

    def close(self):
        if self._file:
            self._file.close()
            self._file = None
            if os.path.getsize(self._path) == 0:
                os.remove(self._path)


redirects = {'stdout': LazyFile('run.log'), 'stderr': LazyFile('run.err')}
driver_log = LazyFile('driver.log')
driver_err = LazyFile('driver.err')


def print_(stream, text):
    stream.write('%s\n' % text)
    stream.flush()


def set_property(name, value):
    # Read properties again before each write to ensure consistency.
    # Otherwise we might overwrite results added by parsers.
    properties = Properties(filename='properties')
    properties[name] = value
    properties.write()


def save_returncode(command_name, value):
    set_property('%s_returncode' % command_name.lower(), value)
    error = 0 if value == 0 else 1
    # TODO: Remove once we judge only by Fast Downward's exit code.
    set_property('%s_error' % command_name.lower(), error)
