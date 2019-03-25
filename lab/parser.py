# -*- coding: utf-8 -*-
#
# Lab is a Python package for evaluating algorithms.
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
Parse logs and output files.

A parser can be any program that analyzes files in the run's
directory (e.g. ``run.log``) and manipulates the ``properties``
file in the same directory.

To make parsing easier, however, you can use the ``Parser`` class. The
parser ``examples/ff/ff-parser.py`` serves as an example:

.. literalinclude:: ../examples/ff/ff-parser.py

You can add this parser to alls runs by using
:meth:`add_parser() <lab.experiment.Experiment.add_parser>`:

>>> import os.path
>>> from lab import experiment
>>> exp = experiment.Experiment()
>>> # The path can be absolute or relative to the working directory
>>> # at build time.
>>> parser = os.path.abspath(
...     os.path.join(__file__, '../../examples/ff/ff-parser.py'))
>>> exp.add_parser(parser)

All added parsers will be run in the order in which they were added
after executing the run's commands.

If you need to change your parsers and execute them again, use the
:meth:`~lab.experiment.Experiment.add_parse_again_step` method to
re-parse your results.

"""

import errno
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
            try:
                flag |= getattr(re, char)
            except AttributeError:
                logging.critical('Unknown pattern flag: {}'.format(char))

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
            logging.error('Pattern "%s" not found in %s' % (self, filename))
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
        with open(filename, 'r') as f:
            self.content = f.read()

    def add_pattern(self, pattern):
        self.patterns.append(pattern)

    def add_function(self, function):
        self.functions.append(function)

    def search_patterns(self):
        assert self.content is not None
        found_props = {}
        for pattern in self.patterns:
            found_props.update(pattern.search(self.content, self.filename))
        return found_props

    def apply_functions(self, props):
        assert self.content is not None
        for function in self.functions:
            function(self.content, props)


class Parser(object):
    """
    Parse files in the current directory and write results into the
    run's ``properties`` file.
    """
    def __init__(self):
        tools.configure_logging()
        self.file_parsers = defaultdict(_FileParser)

    def add_pattern(
            self, attribute, regex, file='run.log', type=int, flags='',
            required=False):
        r"""
        Look for *regex* in *file*, cast what is found in brackets to
        *type* and store it in the properties dictionary under
        *attribute*. During parsing roughly the following code will be
        executed::

            contents = open(file).read()
            match = re.compile(regex).search(contents)
            properties[attribute] = type(match.group(1))

        *flags* must be a string of Python regular expression flags (see
        https://docs.python.org/2/library/re.html). E.g., ``flags='M'``
        lets "^" and "$" match at the beginning and end of each line,
        respectively.

        If *required* is True and the pattern is not found in *file*,
        an error message is printed to stderr.

        >>> parser = Parser()
        >>> parser.add_pattern('facts', r'Facts: (\d+)', type=int)

        """
        if type == bool:
            logging.warning('Casting any non-empty string to boolean will always '
                            'evaluate to true. Are you sure you want to use type=bool?')
        self.file_parsers[file].add_pattern(
            _Pattern(attribute, regex, required, type, flags))

    def add_function(self, function, file='run.log'):
        r"""Call ``function(open(file).read(), properties)`` during parsing.

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

        You can use ``props.add_unexplained_error("message")`` when your
        parsing function detects that something went wrong during the
        run.

        """
        self.file_parsers[file].add_function(function)

    def parse(self):
        """Search all patterns and apply all functions.

        The found values are written to the run's ``properties`` file.

        """
        run_dir = os.path.abspath('.')
        prop_file = os.path.join(run_dir, 'properties')
        self.props = tools.Properties(filename=prop_file)

        for filename, file_parser in self.file_parsers.items():
            # If filename is absolute it will not be changed here.
            path = os.path.join(run_dir, filename)
            try:
                file_parser.load_file(path)
            except IOError as err:
                if err.errno == errno.ENOENT:
                    logging.info('File "{path}" is missing and thus not parsed.'.format(
                        **locals()))
                    del self.file_parsers[filename]
                else:
                    logging.error('Failed to read "{path}": {err}'.format(**locals()))

        for file_parser in self.file_parsers.values():
            self.props.update(file_parser.search_patterns())

        for file_parser in self.file_parsers.values():
            file_parser.apply_functions(self.props)

        self.props.write()
