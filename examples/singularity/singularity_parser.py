import re
import sys

from lab.parser import Parser


def coverage(content, props):
    props["coverage"] = int("cost" in props)


def unsolvable(content, props):
    # Note that this naive test may easily generate false positives.
    props["unsolvable"] = int(
        not props["coverage"]
        and "Completely explored state space -- no solution!" in content
    )


def parse_g_value_over_time(content, props):
    """Example line: "[g=6, 16 evaluated, 15 expanded, t=0.00328561s, 22300 KB]" """
    matches = re.findall(
        r"\[g=(\d+), \d+ evaluated, \d+ expanded, t=(.+)s, \d+ KB\]\n", content
    )
    props["g_values_over_time"] = [(float(t), int(g)) for g, t in matches]


def set_outcome(content, props):
    lines = content.splitlines()
    solved = props["coverage"]
    unsolvable = props["unsolvable"]
    out_of_time = int("TIMEOUT=true" in lines)
    out_of_memory = int("MEMOUT=true" in lines)
    # runsolver decides "out of time" based on CPU rather than (cumulated)
    # WCTIME.
    if (
        not solved
        and not unsolvable
        and not out_of_time
        and not out_of_memory
        and props["runtime"] > props["time_limit"]
    ):
        out_of_time = 1
    # In cases where CPU time is very slightly above the threshold so that
    # runsolver didn't kill the planner yet and the planner solved a task
    # just within the limit, runsolver will still record an "out of time".
    # We remove this record. This case also applies to iterative planners.
    # If such planners solve the task, we don't treat them as running out
    # of time.
    if (solved or unsolvable) and (out_of_time or out_of_memory):
        print("task solved however runsolver recorded an out_of_*")
        print(props)
        out_of_time = 0
        out_of_memory = 0

    if not solved and not unsolvable:
        props["runtime"] = None

    if solved ^ unsolvable ^ out_of_time ^ out_of_memory:
        if solved:
            props["error"] = "solved"
        elif unsolvable:
            props["error"] = "unsolvable"
        elif out_of_time:
            props["error"] = "out_of_time"
        elif out_of_memory:
            props["error"] = "out_of_memory"
    else:
        print(f"unexpected error: {props}", file=sys.stderr)
        props["error"] = "unexpected-error"


def get_parser():
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
    parser.add_pattern("runtime", r"Singularity runtime: (.+?)s", type=float)
    parser.add_pattern(
        "time_limit",
        r"Enforcing CPUTime limit \(soft limit, will send "
        r"SIGTERM then SIGKILL\): (\d+) seconds",
        type=int,
        file="watch.log",
        required=True,
    )
    # Cumulative runtime and virtual memory of the solver and all child processes.
    parser.add_pattern(
        "runtime", r"WCTIME=(.+)", type=float, file="values.log", required=True
    )
    parser.add_pattern(
        "virtual_memory", r"MAXVM=(\d+)", type=int, file="values.log", required=True
    )
    parser.add_pattern("raw_memory", r"Peak memory: (\d+) KB", type=int)
    parser.add_pattern("cost", r"\nFinal value: (.+)\n", type=int)
    parser.add_function(coverage)
    parser.add_function(unsolvable)
    parser.add_function(parse_g_value_over_time)
    parser.add_function(set_outcome, file="values.log")
    return parser
