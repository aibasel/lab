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
import re
from collections import defaultdict
import logging

from lab import tools


class _Pattern(object):
    def __init__(self, attribute, regex, group, required, typ, flags):
        self.attribute = attribute
        self.group = group
        self.typ = typ
        self.required = required

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

        self.regex = re.compile(regex, flag)

    def search(self, content, filename):
        found_props = {}
        match = self.regex.search(content)
        if match:
            try:
                value = match.group(self.group)
                value = self.typ(value)
                found_props[self.attribute] = value
            except IndexError:
                logging.error('Atrribute %s not found for pattern %s in '
                              'file %s' % (self.attribute, self, filename))
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


def parse_key_value_patterns(content, props):
    regex = re.compile(r'^(\D+): (\d+)$')
    for line in content.splitlines():
        match = regex.match(line)
        if match:
            props[match.group(1).replace(' ', '_').lower()] = int(match.group(2))


class Parser(object):
    """
    Parse files in the current directory and write results into the run's
    properties file.

    Parsing is done as just another run command. After the main command has been
    added to the run, we can add the parsing command::

        run.add_command('parse-output', ['path/to/myparser.py'])

    This calls *myparser.py* in the run directory. Principally a parser can be any
    program that analyzes any of the files in the run dir (e.g. ``run.log``) and
    manipulates the ``properties`` file in the same directory.

    To make parsing easier however, you should use the ``Parser`` class like in
    the simple-parser.py example (``examples/simple/simple-parser.py``):

    .. literalinclude:: ../examples/simple/simple-parser.py

    A single run can have multiple parsing commands.

    If *key_value_patterns* is True, the parser will parse all lines with the
    following format automatically (underlying regex: r'^(.+): (\d+)$')::

        My attribute: 89            --> props['my_attribute'] = 89
        other attribute name: 1234  --> props['other_attribute_name'] = 1234

    """
    def __init__(self, key_value_patterns=False):
        self.file_parsers = defaultdict(_FileParser)
        self.run_dir = os.path.abspath('.')
        prop_file = os.path.join(self.run_dir, 'properties')
        if not os.path.exists(prop_file):
            logging.critical('No properties file found at "%s"' % prop_file)
        self.props = tools.Properties(filename=prop_file)
        if key_value_patterns:
            self.add_function(parse_key_value_patterns)

    def add_pattern(self, name, regex, group=1, file='run.log', required=True,
                    type=int, flags=''):
        """
        Look for *regex* in *file* and add what is found in *group* to the
        properties dictionary under *name*, i.e. ::

            contents = open(file).read()
            match = re.compile(regex).search(contents)
            properties[name] = type(match.group(group))

        If *required* is True and the pattern is not found in file, an error
        message is printed.

        >>> parser = Parser()
        >>> parser.add_pattern('variables', r'Variables: (\d+)')
        """
        if type == bool:
            logging.warning('Casting any non-empty string to boolean will always '
                            'evaluate to true. Are you sure you want to use type=bool?')
        self.file_parsers[file].add_pattern(_Pattern(name, regex, group,
                                                     required, type, flags))

    def add_function(self, function, file='run.log'):
        """
        After all patterns have been evaluated and the found values have been
        inserted into ``props``, call ``function(content, props)`` for each
        added function where content is the content in *file*. The function must
        directly manipulate the properties dictionary *props*.

        >>> # Define a function and check that it works correctly.
        >>> import re
        >>> def find_f_values(content, props):
        ...     props['f_values'] = re.findall(r'f: (\d+)', content)
        ...
        >>> properties = {}
        >>> find_f_values('f: 14, f: 12, f: 10', properties)
        >>> print properties
        {'f_values': ['14', '12', '10']}

        >>> # Add the function to the parser.
        >>> parser = Parser()
        >>> parser.add_function(find_f_values)
        """
        self.file_parsers[file].add_function(function)

    def parse(self):
        """Search all patterns and apply all functions.

        The found values are written to the properties file at
        ``<run_dir>/properties``.
        """
        for filename, file_parser in self.file_parsers.items():
            # If filename is absolute it will not be changed here
            path = os.path.join(self.run_dir, filename)
            success = file_parser.load_file(path)
            if success:
                # Subclasses directly modify the properties during parsing
                file_parser.parse(self.props)
            else:
                logging.error('File "%s" could not be read' % path)

        self.props.write()
