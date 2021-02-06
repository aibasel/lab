#! /usr/bin/env python

"""
Regular expressions and functions for parsing translator logs.
"""

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
    pattern = re.compile(r"^(.+)(\.\.\.|:|!) \[(.+)s CPU, .+s wall-clock\]$")
    for line in content.splitlines():
        match = pattern.match(line)
        if match:
            section = match.group(1).lower().replace(" ", "_")
            props["translator_time_" + section] = float(match.group(3))
        if line.startswith("Done!"):
            return


def parse_statistics(content, props):
    """Parse all translator output of the following form:

    Translator xxx: yyy
    """
    pattern = re.compile(r"^Translator (.+): (.+?)(?: KB|)$")
    for line in content.splitlines():
        match = pattern.match(line)
        if match:
            attr = match.group(1).lower().replace(" ", "_")
            # Support strings, numbers, tuples, lists, dicts, booleans, and None.
            props[f"translator_{attr}"] = ast.literal_eval(match.group(2))
        if line.startswith("Done!"):
            return


class TranslatorParser(Parser):
    def __init__(self):
        Parser.__init__(self)
        self.add_patterns()
        self.add_function(parse_translator_timestamps)
        self.add_function(parse_statistics)

    def add_patterns(self):
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
            "relevant atoms",
            "auxiliary atoms",
            "final queue length",
            "total queue pushes",
            "uncovered facts",
            "effect conditions simplified",
            "implied preconditions added",
            "operators removed",
            "axioms removed",
            "propositions removed",
        ]:
            attribute = "translator_" + value.lower().replace(" ", "_")
            self.add_pattern(attribute, f"\n(.+) {value}\n", type=int)


if __name__ == "__main__":
    parser = TranslatorParser()
    parser.parse()
