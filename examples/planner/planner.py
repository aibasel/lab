#! /usr/bin/env python

"""
Example downward experiment that runs h^FF and h^add on two tasks.

Please adapt REPO to point to your Fast Downward repository.
"""

import os.path

from downward.experiment import FastDownwardExperiment
from downward.reports.absolute import AbsoluteReport
from downward.reports.scatter import ScatterPlotReport


REPO = os.path.expanduser('~/projects/Downward/downward')
OLD_BENCHMARKS_DIR = os.path.join(REPO, 'benchmarks')
NEW_BENCHMARKS_DIR = os.path.join(REPO, 'misc', 'tests', 'benchmarks')
if os.path.exists(NEW_BENCHMARKS_DIR):
    BENCHMARKS_DIR = NEW_BENCHMARKS_DIR
else:
    BENCHMARKS_DIR = OLD_BENCHMARKS_DIR
REVISION_CACHE = os.path.expanduser('~/lab/revision-cache')

exp = FastDownwardExperiment(revision_cache=REVISION_CACHE)

exp.add_suite(BENCHMARKS_DIR, ['gripper:prob01.pddl'])
exp.add_algorithm('ff', REPO, 'tip', ['--search', 'lazy_greedy(ff())'])
exp.add_algorithm('add', REPO, 'tip', ['--search', 'lazy_greedy(add())'])

exp.add_report(AbsoluteReport(), outfile='report-abs.html')
exp.add_report(ScatterPlotReport(attributes='expansions'))

exp.run_steps()
