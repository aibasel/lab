#! /usr/bin/env python

import re

from lab.parser import Parser


def coverage(content, props):
    props["coverage"] = int("cost" in props)
    if not props["coverage"] and "runtime" in props:
        del props["runtime"]


def unsolvable(content, props):
    # Note that this may easily generate false positives.
    props["unsolvable"] = int("unsolvable" in content.lower())


def parse_g_value_over_time(content, props):
    """Example line: "[g=6, 16 evaluated, 15 expanded, t=0.00328561s, 22300 KB]" """
    matches = re.findall(
        r"\[g=(\d+), \d+ evaluated, \d+ expanded, t=(.+)s, \d+ KB\]\n", content
    )
    props["g_values_over_time"] = [(float(t), int(g)) for g, t in matches]


def error(content, props):
    if props.get("planner_exit_code") == 0:
        props["error"] = "none"
    else:
        props["error"] = "some-error-occured"


def main():
    print("Running singularity parser")
    parser = Parser()
    parser.add_pattern(
        "planner_exit_code",
        r"run-planner exit code: (.+)\n",
        type=int,
        file="driver.log",
        required=True,
    )
    parser.add_pattern(
        "node", r"node: (.+)\n", type=str, file="driver.log", required=True
    )
    parser.add_pattern(
        "planner_wall_clock_time",
        r"run-planner wall-clock time: (.+)s",
        type=float,
        file="driver.log",
        required=True,
    )
    parser.add_pattern("search_time", r"Search time: (.+)s", type=float)
    parser.add_pattern("total_time", r"Total time: (.+)s\n", type=float)
    # The Singularity runtime only has a granularity of seconds.
    parser.add_pattern("singularity_runtime", r"Singularity runtime: (.+)s", type=int)
    parser.add_pattern("raw_memory", r"Peak memory: (\d+) KB", type=int)
    parser.add_pattern("cost", r"\nFinal value: (.+)\n", type=int)
    parser.add_function(coverage)
    parser.add_function(unsolvable)
    parser.add_function(error)
    parser.add_function(parse_g_value_over_time)
    parser.parse()


if __name__ == "__main__":
    main()
