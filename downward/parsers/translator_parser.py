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
    pattern = re.compile(
        r"^(.+)(?:\.\.\.|:|!) \[(.+)s CPU, .+s wall-clock\]$", flags=re.M
    )
    for section, time in pattern.findall(content):
        section = section.lower().replace(" ", "_")
        props[f"translator_time_{section}"] = float(time)


def parse_old_statistics(content, props):
    """Parse translator output of the following form:

    170 relevant atoms

    """
    names = {
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
    }
    for count, name in re.findall(r"^(\d+) (.+)$", content, flags=re.M):
        if name in names:
            attribute = f"translator_{name.replace(' ', '_')}"
            props[attribute] = int(count)


def parse_statistics(content, props):
    """Parse all translator output of the following form:

    Translator xxx: yyy

    """
    pattern = re.compile(r"^Translator (.+): (\d+)(?: KB|)$", flags=re.M)
    for name, count in pattern.findall(content):
        attr = name.lower().replace(" ", "_")
        # Support strings, numbers, tuples, lists, dicts, Booleans, and None.
        props[f"translator_{attr}"] = ast.literal_eval(count)


class TranslatorParser(Parser):
    def __init__(self):
        Parser.__init__(self)
        self.add_function(parse_translator_timestamps)
        self.add_function(parse_old_statistics)
        self.add_function(parse_statistics)


if __name__ == "__main__":
    parser = TranslatorParser()
    parser.parse()
