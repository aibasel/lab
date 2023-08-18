#! /usr/bin/env python

"""
Simple experiment showing how to make reports for data obtained without
Lab.

To use custom results, create the file <EXP_DIR>-eval/properties. It
must be a JSON file mapping planner run names to results (see below).
The run names must obviously be unique, but they're not used for the
reports. Each value in the dictionary must itself be a dictionary with
at least the keys "domain", "problem", "algorithm". In addition you need
the attribute names and values that you want to make reports for, e.g.
"coverage", "expansions", "time".

"""

import json
from pathlib import Path

from downward.reports.absolute import AbsoluteReport
from lab.experiment import Experiment


PROPERTIES = {
    "ff-gripper-prob01.pddl": {
        "domain": "gripper",
        "problem": "prob01.pddl",
        "algorithm": "ff",
        "coverage": 1,
        "expansions": 1234,
    },
    "blind-gripper-prob01.pddl": {
        "domain": "gripper",
        "problem": "prob01.pddl",
        "algorithm": "blind",
        "coverage": 1,
        "expansions": 6543,
    },
}


def write_properties(eval_dir):
    eval_dir = Path(eval_dir)
    eval_dir.mkdir(parents=True, exist_ok=True)
    with open(eval_dir / "properties", "w") as f:
        json.dump(PROPERTIES, f)


exp = Experiment()
exp.add_report(AbsoluteReport(attributes=["coverage", "expansions"]))

write_properties(exp.eval_dir)
exp.run_steps()
