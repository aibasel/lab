#! /usr/bin/env python

"""
Parse anytime-search runs of Fast Downward. This includes iterated
searches and portfolios.
"""

import re

from lab.parser import Parser


def find_all_matches(attribute, regex, type=int):
    """
    Look for all occurences of *regex*, cast what is found in brackets to
    *type* and store the list of found items in the properties dictionary
    under *attribute*. *regex* must contain exactly one bracket group.
    """

    def store_all_occurences(content, props):
        matches = re.findall(regex, content)
        props[attribute] = [type(m) for m in matches]

    return store_all_occurences


def reduce_to_min(list_name, single_name):
    def reduce_to_minimum(content, props):
        values = props.get(list_name, [])
        if values:
            props[single_name] = min(values)

    return reduce_to_minimum


def coverage(content, props):
    props["coverage"] = int("cost" in props)


def main():
    parser = Parser()
    parser.add_function(find_all_matches("cost:all", r"Plan cost: (.+)\n", type=float))
    parser.add_function(
        find_all_matches("steps:all", r"Plan length: (.+) step\(s\).\n", type=float)
    )
    parser.add_function(reduce_to_min("cost:all", "cost"))
    parser.add_function(reduce_to_min("steps:all", "steps"))
    parser.add_function(coverage)
    parser.parse()


main()
