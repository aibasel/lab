#! /usr/bin/env python

"""
Example downward experiment that runs h^FF and h^add.

Please adapt REPO and BENCHMARKS_DIR.
"""

import os.path

from downward.experiment import FastDownwardExperiment
from downward.reports.absolute import AbsoluteReport
from downward.reports.scatter import ScatterPlotReport


REPO = os.path.expanduser('~/projects/Downward/downward')
BENCHMARKS_DIR = os.path.expanduser('~/projects/Downward/benchmarks')
REVISION_CACHE = os.path.expanduser('~/lab/revision-cache')

exp = FastDownwardExperiment(revision_cache=REVISION_CACHE)

exp.add_suite(BENCHMARKS_DIR, ['gripper:prob01.pddl'])
exp.add_algorithm('ff', REPO, 'tip', ['--search', 'lazy_greedy(ff())'])
exp.add_algorithm('add', REPO, 'tip', ['--search', 'lazy_greedy(add())'])

exp.add_report(AbsoluteReport(), outfile='report-abs.html')
exp.add_report(ScatterPlotReport(attributes='expansions'))

exp.run_steps()
