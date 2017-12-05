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

"""
Module for parsing logs and files.

A parser can be any program that analyzes files in the run's
directory (e.g. ``run.log``) and manipulates the ``properties``
file in the same directory.

To make parsing easier, however, you can use the ``Parser`` class.
The parser ``examples/simple/simple-parser.py`` serves as an
example:

.. literalinclude:: ../examples/simple/simple-parser.py

You can add your parser to a run by using :py:func:`add_command
<lab.experiment.Run.add_command>`::

    run.add_command('solve', ['path/to/my-solver', 'path/to/benchmark'])
    run.add_command('parse-output', ['path/to/my-parser.py'])

This calls ``my-parser.py`` in the run's directory after running the
solver.

A single run can have multiple parsing commands.

Instead of adding a parser to individual runs, you can use
:py:func:`add_command <lab.experiment.Experiment.add_command>` to
append your parser to the list of commands of each run.

"""

import os.path
import re
from collections import defaultdict
import logging

from lab import tools


class _Pattern(object):
    def __init__(self, attribute, regex, required, type_, flags):
        self.attribute = attribute
        self.type_ = type_
        self.required = required
        self.group = 1

        flag = 0

        for char in flags:
            if char == 'M':
                flag |= re.M
            elif char == 'L':
                flag |= re.L
            elif char == 'S':
                flag |= re.S
            elif char == 'I':
                flag |= re.I
            elif char == 'U':
                flag |= re.U
            elif char == 'X':
                flag |= re.X
            else:
                logging.critical('Unknown regex flag: {}'.format(char))

        self.regex = re.compile(regex, flag)

    def search(self, content, filename):
        found_props = {}
        match = self.regex.search(content)
        if match:
            try:
                value = match.group(self.group)
            except IndexError:
                logging.error('Attribute %s not found for pattern %s in '
                              'file %s' % (self.attribute, self, filename))
            else:
                value = self.type_(value)
                found_props[self.attribute] = value
        elif self.required:
            logging.error('Pattern %s not found in %s' % (self, filename))
        return found_props

    def __str__(self):
        return self.regex.pattern


class _FileParser(object):
    """
    Private class that parses a given file according to the added patterns
    and functions.
    """
    def __init__(self):
        self.filename = None
        self.content = None
        self.patterns = []
        self.functions = []

    def load_file(self, filename):
        self.filename = filename
        with open(filename, 'rb') as f:
            self.content = f.read()

    def add_pattern(self, pattern):
        self.patterns.append(pattern)

    def add_function(self, function):
        self.functions.append(function)

    def parse(self, props):
        assert self.filename
        props.update(self._search_patterns())
        self._apply_functions(props)

    def _search_patterns(self):
        found_props = {}
        for pattern in self.patterns:
            found_props.update(pattern.search(self.content, self.filename))
        return found_props

    def _apply_functions(self, props):
        for function in self.functions:
            function(self.content, props)


class Parser(object):
    """
    Parse files in the current directory and write results into the
    run's ``properties`` file.
    """
    def __init__(self):
        self.file_parsers = defaultdict(_FileParser)
        self.run_dir = os.path.abspath('.')
        prop_file = os.path.join(self.run_dir, 'properties')
        if not os.path.exists(prop_file):
            logging.critical('No properties file found at "%s"' % prop_file)
        self.props = tools.Properties(filename=prop_file)

    def add_pattern(
            self, attribute, regex, file='run.log', type=int, flags='',
            required=True):
        """
        Look for *regex* in *file*, cast what is found in brackets to
        *type* and store it in the properties dictionary under
        *attribute*. During parsing roughly the following code will be
        executed::

            contents = open(file).read()
            match = re.compile(regex).search(contents)
            properties[attribute] = type(match.group(1))

        If given, *flags* must be a string of Python regular expression
        flags (e.g. ``flags='UM'``).

        If *required* is True and the pattern is not found in *file*,
        an error message is printed.

        >>> parser = Parser()
        >>> parser.add_pattern('facts', r'^Facts: (\d+)$', type=int, flags='M')

        """
        if type == bool:
            logging.warning('Casting any non-empty string to boolean will always '
                            'evaluate to true. Are you sure you want to use type=bool?')
        self.file_parsers[file].add_pattern(
            _Pattern(attribute, regex, required, type, flags))

    def add_function(self, function, file='run.log'):
        """Call ``function(open(file), properties)`` during parsing.

        Functions are applied **after** all patterns have been
        evaluated.

        The function is passed the file contents and the properties
        dictionary. It must manipulate the passed properties
        dictionary. The return value is ignored.

        Example:

        >>> import re
        >>> from lab.parser import Parser
        >>> # Example content: f=14, f=12, f=10
        >>> def find_f_values(content, props):
        ...     props['f_values'] = re.findall(r'f=(\d+)', content)
        ...
        >>> parser = Parser()
        >>> parser.add_function(find_f_values)

        You can use `props.add_unexplained_error(msg)` when your parsing
        function detects that something went wrong during the run.

        """
        self.file_parsers[file].add_function(function)

    def parse(self):
        """Search all patterns and apply all functions.

        The found values are written to the run's ``properties`` file.

        """
        for filename, file_parser in self.file_parsers.items():
            # If filename is absolute it will not be changed here.
            path = os.path.join(self.run_dir, filename)
            try:
                file_parser.load_file(path)
            except (IOError, MemoryError) as err:
                logging.error('File "%s" could not be read: %s' % (path, err))
                self.props.add_unexplained_error('parser-failed-to-read-file')
            else:
                # Subclasses directly modify the properties during parsing.
                file_parser.parse(self.props)

        self.props.write()
