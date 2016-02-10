#! /usr/bin/env python

"""
Example downward experiment that runs h^FF and h^add on two tasks.

The file planner.py contains the "basic" version of this experiment.
"""

import os.path

from downward.experiment import FastDownwardExperiment
from downward.reports.absolute import AbsoluteReport
from downward.reports.scatter import ScatterPlotReport


REPO = '/home/jendrik/projects/Downward/downward'
BENCHMARKS_DIR = os.path.join(REPO, 'benchmarks')
CACHE_DIR = os.path.expanduser('~/lab')

exp = FastDownwardExperiment(cache_dir=CACHE_DIR)

exp.add_suite(BENCHMARKS_DIR, ['gripper:prob01.pddl'])
exp.add_suite(BENCHMARKS_DIR, ['zenotravel:pfile2'])
exp.add_algorithm('ff', REPO, 'tip', ['--search', 'lazy_greedy(ff())'])
exp.add_algorithm('add', REPO, 'tip', ['--search', 'lazy_greedy(add())'])

exp.add_report(AbsoluteReport('problem'), outfile='report-abs-p.html')
exp.add_report(ScatterPlotReport(attributes='expansions'))

exp.run_steps()
