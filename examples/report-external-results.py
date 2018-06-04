#! /usr/bin/env python

"""
Simple experiment showing how to make reports for data obtained without
Lab.

To use custom results, create the file <EXP_DIR>-eval/properties. It
must be a JSON file mapping planner run names to results (see below).
The run names must obviously be unique, but they're not used for the
reports. Each value in the dictionary must itself be a dictionary with
at least the keys "domain", "problem", "algorithm" and "error". In
addition you need the attribute names and values that you want to make
reports for, e.g. "coverage", "expansions", "time".

"""

import json
import os.path

from lab.experiment import Experiment
from lab import tools

from downward.reports.absolute import AbsoluteReport


EXP_DIR = "data/custom"


PROPERTIES = {
    "ff-gripper-prob01.pddl": {
        "domain": "gripper",
        "problem": "prob01.pddl",
        "algorithm": "ff",
        "coverage": 1,
        "expansions": 1234,
        "error": "plan-found",
    },
    "blind-gripper-prob01.pddl": {
        "domain": "gripper",
        "problem": "prob01.pddl",
        "algorithm": "blind",
        "coverage": 1,
        "expansions": 6543,
        "error": "plan-found",
    },
}


def write_properties(eval_dir):
    tools.makedirs(eval_dir)
    with open(os.path.join(eval_dir, 'properties'), 'w') as f:
        json.dump(PROPERTIES, f)


# Create new experiment. The file <EXP_DIR>-eval/properties must exist.
exp = Experiment(EXP_DIR)
exp.add_report(AbsoluteReport(attributes=['coverage', 'expansions']))

write_properties(exp.eval_dir)
exp.run_steps()
