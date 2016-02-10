#! /usr/bin/env python

"""
Simple experiment showing how to make reports for data obtained without
lab.

To use custom results, create the file <EXP_DIR>-eval/properties. It
must be a json file mapping planner runs to results (see below). The
keys must be unique, but otherwise they are irrelevant. Each mapped
value must itself be a dictionary with at least the keys "domain",
"problem" and "algorithm". In addition you need the attribute names and
values that you want to make reports for, e.g. "coverage",
"expansions", "time".

"""

import json
import os.path

from lab.experiment import Experiment
from lab import tools

from downward.reports.absolute import AbsoluteReport
from downward.reports.plot import ProblemPlotReport


EXP_DIR = "data/custom"


PROPERTIES = {
    "ff-gripper-prob01.pddl": {
        "domain": "gripper",
        "problem": "prob01.pddl",
        "algorithm": "ff",
        "coverage": 1,
        "expansions": 1234
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
    tools.makedirs(eval_dir)
    with open(os.path.join(eval_dir, 'properties'), 'w') as f:
        json.dump(PROPERTIES, f)


# Create new experiment. The file <EXP_DIR>-eval/properties must exist.
exp = Experiment(EXP_DIR)
# Remove all existing experiment steps.
exp.steps = []
exp.add_report(AbsoluteReport(attributes=['coverage', 'expansions']))
exp.add_report(ProblemPlotReport(attributes=['expansions']))

write_properties(exp.eval_dir)
exp.run_steps()
