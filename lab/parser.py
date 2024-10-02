"""
To parse logs or generated files, you can use the ``Parser`` class. Here is an
example parser for the FF planner:

.. literalinclude:: ../examples/ff/ff_parser.py
   :caption:

You can add a parser to all runs with :meth:`add_parser()
<lab.experiment.Experiment.add_parser>`:

>>> from pathlib import Path
>>> from lab.experiment import Experiment
>>> parser = Parser()
>>> parser.add_pattern("exitcode", "retcode: (.+)\\n", type=int, file="run.log")
>>> exp = Experiment()
>>> exp.add_parser(parser)

Parsers are run in the order in which they were added.

"""

import logging
import os
import re
from collections import defaultdict
from pathlib import Path

from lab import tools


def _get_pattern_flags(s):
    flags = 0
    for char in s:
        try:
            flags |= getattr(re, char)
        except AttributeError:
            raise ValueError(f"Unknown pattern flag: {char}") from None
    return flags


class _Function:
    def __init__(self, function, filename):
        self.function = function
        self.filename = filename


class _Pattern:
    def __init__(self, attribute, regex, required, type_, flags):
        self.attribute = attribute
        self.type_ = type_
        self.required = required
        self.group = 1

        flags = _get_pattern_flags(flags)
        self.regex = re.compile(regex, flags)

    def search(self, filename, content, props):
        found_props = {}
        match = self.regex.search(content)
        if match:
            try:
                value = match.group(self.group)
            except IndexError:
                tools.add_unexplained_error(
                    props,
                    f"Attribute {self.attribute} not found for pattern {self} in "
                    f"file {filename}.",
                )
            else:
                value = self.type_(value)
                found_props[self.attribute] = value
        elif self.required:
            tools.add_unexplained_error(
                props, f'Pattern "{self}" not found in {filename}'
            )
        return found_props

    def __str__(self):
        return self.regex.pattern


class _FileParser:
    """
    Private class that searches a given file for the added patterns.
    """

    def __init__(self):
        self.patterns = []

    def add_pattern(self, pattern):
        self.patterns.append(pattern)

    def search_patterns(self, filename, content, props):
        for pattern in self.patterns:
            props.update(pattern.search(filename, content, props))


class Parser:
    """
    Parse logs or files in a given directory and write results into the
    ``properties`` file.
    """

    def __init__(self):
        self.file_parsers = defaultdict(_FileParser)
        self.functions = []

    def add_pattern(
        self, attribute, regex, file="run.log", type=int, flags="", required=False
    ):
        r"""
        Look for *regex* in *file*, cast what is found in brackets to
        *type* and store it in the properties dictionary under
        *attribute*. During parsing roughly the following code will be
        executed::

            contents = open(file).read()
            match = re.compile(regex).search(contents)
            properties[attribute] = type(match.group(1))

        *flags* must be a string of Python regular expression flags (see
        https://docs.python.org/3/library/re.html). E.g., ``flags="M"``
        lets "^" and "$" match at the beginning and end of each line,
        respectively.

        If *required* is True and the pattern is not found in *file*,
        an error message is printed to stderr.

        >>> parser = Parser()
        >>> parser.add_pattern("facts", r"Facts: (\d+)", type=int)

        """
        if type == bool:
            logging.warning(
                "Casting any non-empty string to boolean will always "
                "evaluate to true. Are you sure you want to use type=bool?"
            )
        self.file_parsers[file].add_pattern(
            _Pattern(attribute, regex, required, type, flags)
        )

    def add_function(self, function, file="run.log"):
        r"""Call ``function(open(file).read(), properties)`` during parsing.

        Functions are applied **after** all patterns have been
        evaluated and in the order in which they are added to the parser.

        The function is passed the file contents and the properties
        dictionary. It must manipulate the passed properties
        dictionary. The return value is ignored.

        Example:

        >>> import re
        >>> from lab.parser import Parser
        >>> def parse_states_over_time(content, props):
        ...     matches = re.findall(r"(.+)s: (\d+) states\n", content)
        ...     props["states_over_time"] = [(float(t), int(s)) for t, s in matches]
        ...
        >>> parser = Parser()
        >>> parser.add_function(parse_states_over_time)

        You can use ``props.add_unexplained_error("message")`` when your
        parsing function detects that something went wrong during the
        run.

        """
        self.functions.append(_Function(function, file))

    def parse(self, run_dir, props):
        """Search all patterns and apply all functions.

        Add the found values to *props*.

        """
        run_dir = Path(run_dir).resolve()

        content_cache = {}

        def get_content(path):
            if path not in content_cache:
                try:
                    content_cache[path] = path.read_text()
                except FileNotFoundError:
                    content_cache[path] = None
            return content_cache[path]

        for filename, file_parser in self.file_parsers.items():
            # If filename is absolute, path is set to filename.
            path = run_dir / filename
            content = get_content(path)
            if content is None:
                if any(pattern.required for pattern in file_parser.patterns):
                    tools.add_unexplained_error(
                        props, f'Required file "{path}" is missing.'
                    )
            else:
                file_parser.search_patterns(str(path), content, props)

        for function in self.functions:
            path = run_dir / function.filename
            # Call function with empty string if file is missing.
            content = get_content(path) or ""

            # Run function in the run directory.
            old_cwd = Path.cwd()
            os.chdir(run_dir)
            function.function(content, props)
            os.chdir(old_cwd)
