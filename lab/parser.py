import os
import sys
import re
from collections import defaultdict
import logging

print 'SYSPATH PARSER', sys.path
from lab import tools
print 'TOOLS FILE', tools.__file__


class _MultiPattern(object):
    """
    Parses a file for a pattern containing multiple match groups.
    Each group_number has an associated attribute name and a type.
    """
    def __init__(self, groups, regex, file, required, flags):
        """
        groups is a list of (group_number, attribute_name, type) tuples
        """
        self.groups = groups
        self.file = file
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
            for group_number, attribute_name, type in self.groups:
                try:
                    value = match.group(group_number)
                    value = type(value)
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
    If copy-all is True, copies files from run dirs into a new tree under
    <eval-dir> according to the value "id" in the run's properties file.

    Parses files and writes found results into the run's properties file or
    into a global properties file.
    """
    def __init__(self):
        self.file_parsers = defaultdict(_FileParser)
        self.check = None

    def add_pattern(self, name, regex, group=1, file='run.log', required=True,
                    type=int, flags=''):
        """
        During evaluate() look for pattern in file and add what is found in
        group to the properties dictionary under "name":

        properties[name] = re.compile(regex).search(file_content).group(group)

        If required is True and the pattern is not found in file, an error
        message is printed
        """
        groups = [(group, name, type)]
        self.add_multipattern(groups, regex, file, required, flags)

    def add_multipattern(self, groups, regex, file='run.log', required=True,
                         flags=''):
        """
        During evaluate() look for "regex" in file. For each tuple of
        (group_number, attribute_name, type) add the results for "group_number"
        to the properties file under "attribute_name" after casting it to
        "type".

        If required is True and the pattern is not found in file, an error
        message is printed
        """
        self.file_parsers[file].add_pattern(
                        _MultiPattern(groups, regex, file, required, flags))

    def add_function(self, function, file='run.log'):
        """
        After all the patterns have been evaluated and the found values have
        been inserted into the properties files, call
        function(file_content, props) for each added function.
        The function can directly manipulate the properties dictionary "props".
        Functions can use the fact that all patterns have been parsed before
        any function is run on the file content. The found values are present
        in "props".
        """
        self.file_parsers[file].add_function(function)

    def set_check(self, function):
        """
        After all properties have been parsed or calculated, run "function"
        on them to assert some things.
        """
        self.check = function

    def parse(self, run_dir='.', copy_all=False):
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

        if self.check:
            try:
                self.check(props)
            except AssertionError, e:
                msg = 'Parsed properties not valid in %s: %s'
                logging.error(msg % (prop_file, e))
                print '*' * 60
                props.write(sys.stdout)
                print '*' * 60
        props.write()
