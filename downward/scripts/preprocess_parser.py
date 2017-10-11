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
Regular expressions and functions for parsing preprocessing results.
"""

from __future__ import division

import ast
import re

from lab.parser import Parser


def parse_translator_timestamps(content, props):
    """Parse all translator output of the following forms:

        Computing fact groups: [0.000s CPU, 0.004s wall-clock]
        Writing output... [0.000s CPU, 0.001s wall-clock]

    The last line reads:

        Done! [6.860s CPU, 6.923s wall-clock]
    """
    pattern = re.compile(r'^(.+)(\.\.\.|:|!) \[(.+)s CPU, .+s wall-clock\]$')
    for line in content.splitlines():
        match = pattern.match(line)
        if match:
            section = match.group(1).lower().replace(' ', '_')
            props['translator_time_' + section] = float(match.group(3))
        if line.startswith('Done!'):
            break


def parse_statistics(content, props):
    """Parse all output of the following forms:

        Translator xxx: yyy
        Preprocessor xxx: yyy
    """
    pattern = re.compile(r'^(Translator|Preprocessor) (.+): (.+?)( KB|)$')
    for line in content.splitlines():
        match = pattern.match(line)
        if match:
            part = match.group(1).lower()
            attr = match.group(2).lower().replace(' ', '_')
            # Support strings, numbers, tuples, lists, dicts, booleans, and None.
            props['%s_%s' % (part, attr)] = ast.literal_eval(match.group(3))
        if line.startswith('done'):
            break


def parse_translator_exitcode(content, props):
    """
    If there was an error, add its source to the error list at props['error'].

    For unexplained errors please check the files run.log, run.err,
    driver.log and driver.err to find the reason for the error.
    """

    exitcode = props['fast-downward_returncode']
    props['translator_out_of_time'] = False
    if exitcode == 0:
        props.add_error('none')
    elif exitcode == 232: # -24 means timeout
        props['translator_out_of_time'] = True
        props.add_error('translator-timeout')
    elif exitcode == 1 and props['translator_out_of_memory'] == True:
        # translator exits with code 1 if python threw a MemoryError.
        props.add_error('translator-out-of-memory')
    else:
        props.add_error('unexplained-translator-exitcode-{}'.format(exitcode))


def parse_translator_memory_error(content, props):
    """ Parse output for "MemoryError" of python."""
    translator_out_of_memory = False
    lines = content.split('\n')
    for line in lines:
        if line == 'MemoryError':
            translator_out_of_memory = True
    props['translator_out_of_memory'] = translator_out_of_memory


class PreprocessParser(Parser):
    def __init__(self):
        Parser.__init__(self)
        self.add_preprocess_parsing()
        self.add_preprocess_functions()

    def add_preprocess_parsing(self):
        # These logs were part of the preprocessor. The latter two are
        # now printed by the translator. We keep them for backwards
        # compatibility.
        self.add_pattern(
            'preprocessor_variables',
            r'(\d+) variables of \d+ necessary',
            required=False)
        self.add_pattern('preprocessor_operators', r'(\d+) of \d+ operators necessary')
        self.add_pattern('preprocessor_axioms', r'(\d+) of \d+ axiom rules necessary')

        # Parse the numbers from the following lines of translator output:
        #    170 relevant atoms
        #    141 auxiliary atoms
        #    311 final queue length
        #    364 total queue pushes
        #    13 uncovered facts
        #    0 effect conditions simplified
        #    0 implied preconditions added
        #    0 operators removed
        #    0 axioms removed
        #    38 propositions removed
        for value in [
                'relevant atoms', 'auxiliary atoms', 'final queue length',
                'total queue pushes', 'uncovered facts',
                'effect conditions simplified', 'implied preconditions added',
                'operators removed', 'axioms_removed', 'propositions removed']:
            attribute = 'translator_' + value.lower().replace(' ', '_')
            # These lines are not required, because they were not always printed.
            self.add_pattern(attribute, r'(.+) %s' % value, type=int,
                             required=False)

    def add_preprocess_functions(self):
        self.add_function(parse_translator_exitcode)
        self.add_function(parse_translator_memory_error, file='run.err')
        self.add_function(parse_translator_timestamps)
        self.add_function(parse_statistics)


if __name__ == '__main__':
    parser = PreprocessParser()
    parser.parse()
