"""
FF example output:

[...]

ff: found legal plan as follows

step    0: UP F0 F1
        1: BOARD F1 P0
        2: DOWN F1 F0
        3: DEPART F0 P0


time spent:    0.00 seconds instantiating 4 easy, 0 hard action templates
               0.00 seconds reachability analysis, yielding 4 facts and 4 actions
               0.00 seconds creating final representation with 4 relevant facts
               0.00 seconds building connectivity graph
               0.00 seconds searching, evaluating 5 states, to a max depth of 2
               0.00 seconds total time
"""

import re

from lab.parser import Parser


def error(content, props):
    if props["planner_exit_code"] == 0:
        props["error"] = "plan-found"
    else:
        props["error"] = "unsolvable-or-error"


def coverage(content, props):
    props["coverage"] = int(props["planner_exit_code"] == 0)


def get_plan(content, props):
    # All patterns are parsed before functions are called.
    if props.get("evaluations") is not None:
        props["plan"] = re.findall(r"^(?:step)?\s*\d+: (.+)$", content, re.M)


def get_times(content, props):
    props["times"] = re.findall(r"(\d+\.\d+) seconds", content)


def trivially_unsolvable(content, props):
    props["trivially_unsolvable"] = int(
        "ff: goal can be simplified to FALSE. No plan will solve it" in content
    )


class FFParser(Parser):
    def __init__(self):
        super().__init__()
        self.add_pattern(
            "node", r"node: (.+)\n", type=str, file="driver.log", required=True
        )
        self.add_pattern(
            "planner_exit_code",
            r"run-planner exit code: (.+)\n",
            type=int,
            file="driver.log",
        )
        self.add_pattern("evaluations", r"evaluating (\d+) states")
        self.add_function(error)
        self.add_function(coverage)
        self.add_function(get_plan)
        self.add_function(get_times)
        self.add_function(trivially_unsolvable)
