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
OLD_BENCHMARKS_DIR = os.path.join(REPO, 'benchmarks')
NEW_BENCHMARKS_DIR = os.path.join(REPO, 'misc', 'tests', 'benchmarks')
if os.path.exists(NEW_BENCHMARKS_DIR):
    BENCHMARKS_DIR = NEW_BENCHMARKS_DIR
else:
    BENCHMARKS_DIR = OLD_BENCHMARKS_DIR

exp = FastDownwardExperiment(cache_dir=tools.DEFAULT_USER_DIR)

exp.add_suite(BENCHMARKS_DIR, ['gripper:prob01.pddl'])
exp.add_algorithm('ff', REPO, 'tip', ['--search', 'lazy_greedy(ff())'])

exp.add_report(AbsoluteReport())

exp()
