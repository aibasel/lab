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
BENCHMARKS_DIR = os.path.join(REPO, 'benchmarks')
CACHE_DIR = os.path.expanduser('~/lab')

exp = FastDownwardExperiment(cache_dir=CACHE_DIR)

exp.add_suite(BENCHMARKS_DIR, ['gripper:prob01.pddl', 'zenotravel:pfile2'])
exp.add_algorithm('ff', REPO, 'tip', ['--search', 'lazy_greedy(ff())'])
exp.add_algorithm('add', REPO, 'tip', ['--search', 'lazy_greedy(add())'])

exp.add_report(AbsoluteReport(), outfile='report-abs.html')
exp.add_report(ScatterPlotReport(attributes='expansions'))

exp.run_steps()
