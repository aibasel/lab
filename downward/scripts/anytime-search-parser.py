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


def add_memory(content, props):
    """Add "memory" attribute if the run was not aborted.

    Peak memory usage is printed even for runs that are terminated
    abnormally. For these runs we do not take the reported value into
    account since the value is censored: it only takes into account the
    memory usage until termination.

    """
    raw_memory = props.get("raw_memory")
    if raw_memory is not None:
        if raw_memory < 0:
            props.add_unexplained_error("planner failed to log peak memory")
        elif props["coverage"]:
            props["memory"] = raw_memory


def main():
    parser = Parser()
    parser.add_pattern("raw_memory", r"Peak memory: (.+) KB", type=int),
    parser.add_function(find_all_matches("cost:all", r"Plan cost: (.+)\n", type=float))
    parser.add_function(
        find_all_matches("steps:all", r"Plan length: (.+) step\(s\).\n", type=float)
    )
    parser.add_function(reduce_to_min("cost:all", "cost"))
    parser.add_function(reduce_to_min("steps:all", "steps"))
    parser.add_function(coverage)
    parser.add_function(add_memory)
    parser.parse()


main()
