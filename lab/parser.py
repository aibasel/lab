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

import os
import sys
import re
from collections import defaultdict
import logging

# TODO: Remove debug code
print 'SYSPATH PARSER', sys.path
print 'CWD:', os.getcwd()
from lab import tools
print 'TOOLS FILE', tools.__file__


class _MultiPattern(object):
    """
    Parses a file for a pattern containing multiple match groups.
    Each group_number has an associated attribute name and a type.
    """
    def __init__(self, groups, regex, required, flags):
        """
        groups is a list of (group_number, attribute_name, type) tuples
        """
        self.groups = groups
        self.required = required

        flag = 0

        for char in flags:
            if   char == 'M':
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

        self.regex = re.compile(regex, flag)

    def search(self, content, filename):
        found_props = {}
        match = self.regex.search(content)
        if match:
            for group_number, attribute_name, typ in self.groups:
                try:
                    value = match.group(group_number)
                    value = typ(value)
                    found_props[attribute_name] = value
                except IndexError:
                    msg = 'Atrribute %s not found for pattern %s in file %s'
                    msg %= (attribute_name, self, filename)
                    logging.error(msg)
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
        try:
            with open(filename, 'rb') as file:
                self.content = file.read()
        except IOError:
            self.content = ''
            return False
        else:
            return True

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
    Parses files and writes found results into the run's properties file.
    """
    def __init__(self):
        self.file_parsers = defaultdict(_FileParser)

    def add_pattern(self, name, regex, group=1, file='run.log', required=True,
                    type=int, flags=''):
        """
        Look for *regex* in *file* and add what is found in *group* to the
        properties dictionary under *name*, i.e. ::

            properties[name] = type(re.compile(regex).search(open(file).read()).group(group))

        If *required* is True and the pattern is not found in file, an error
        message is printed.
        """
        groups = [(group, name, type)]
        self.add_multipattern(groups, regex, file, required, flags)

    def add_multipattern(self, groups, regex, file='run.log', required=True,
                         flags=''):
        """Look for multi-group *regex* in file.

        This function is useful if *regex* contains multiple attributes.

        *groups* is a list of (group_number, attribute_name, type) tuples. For
        each such tuple add the results for *group_number* to the properties
        under *attribute_name* after casting it to *type*.

        If *required* is True and the pattern is not found in file, an error
        message is printed.
        """
        self.file_parsers[file].add_pattern(
                                _MultiPattern(groups, regex, required, flags))

    def add_function(self, function, file='run.log'):
        """
        After all patterns have been evaluated and the found values have been
        inserted into ``props``, call ``function(file_content, props)`` for each
        added function. The function must directly manipulate the properties
        dictionary *props*.
        """
        self.file_parsers[file].add_function(function)

    def parse(self, run_dir='.'):
        prop_file = os.path.join(run_dir, 'properties')
        props = tools.Properties(filename=prop_file)

        for filename, file_parser in self.file_parsers.items():
            # If filename is absolute it will not be changed here
            path = os.path.join(run_dir, filename)
            success = file_parser.load_file(path)
            if success:
                # Subclasses directly modify the properties during parsing
                file_parser.parse(props)
            else:
                logging.error('File "%s" could not be read' % path)

        props.write()
