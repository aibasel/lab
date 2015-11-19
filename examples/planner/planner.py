#! /usr/bin/env python

"""
Example downward experiment that runs FF on a single problem.

Please adapt EXPPATH and REPO to be the path where the experiment shall be put
and the location of your Fast Downward repository.

The file planner-ext.py contains an "advanced" version of this basic experiment.
"""

import os.path

from lab import tools

from downward.experiment import FastDownwardExperiment
from downward.reports.absolute import AbsoluteReport


REPO = os.path.expanduser('~/projects/Downward/downward')
BENCHMARKS_DIR = os.path.join(REPO, 'benchmarks')

exp = FastDownwardExperiment(cache_dir=tools.DEFAULT_USER_DIR)

exp.add_suite(BENCHMARKS_DIR, 'gripper:prob01.pddl')
exp.add_algorithm('ff', REPO, 'tip', ['--search', 'lazy_greedy(ff())'])

exp.add_report(AbsoluteReport())

exp()
