#! /usr/bin/env python

from lab.parser import Parser


def add_planner_memory(content, props):
    try:
        props["planner_memory"] = max(props["translator_peak_memory"], props["memory"])
    except KeyError:
        pass


def add_planner_time(content, props):
    try:
        props["planner_time"] = props["translator_time_done"] + props["total_time"]
    except KeyError:
        pass


class PlannerParser(Parser):
    def __init__(self):
        Parser.__init__(self)
        self.add_function(add_planner_memory)
        self.add_function(add_planner_time)

        self.add_pattern(
            "node", r"node: (.+)\n", type=str, file="driver.log", required=True
        )
        self.add_pattern(
            "planner_wall_clock_time",
            r"planner wall-clock time: (.+)s",
            type=float,
            file="driver.log",
            required=True,
        )


def main():
    parser = PlannerParser()
    parser.parse()


main()
