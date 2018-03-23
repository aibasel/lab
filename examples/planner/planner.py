#! /usr/bin/env python

"""
Example downward experiment that runs h^FF and h^add.

Please adapt REPO and set DOWNWARD_BENCHMARKS environment variable.
"""

import os.path

from downward.experiment import FastDownwardExperiment
from downward.reports.absolute import AbsoluteReport
from downward.reports.scatter import ScatterPlotReport


REPO = os.environ["DOWNWARD_REPO"]
BENCHMARKS_DIR = os.environ['DOWNWARD_BENCHMARKS']
REVISION_CACHE = os.path.expanduser('~/lab/revision-cache')

exp = FastDownwardExperiment(revision_cache=REVISION_CACHE)
# Add default parsers to the experiment.
exp.add_parser('driver_parser', exp.DRIVER_PARSER)
exp.add_parser('exitcode_parser', exp.EXITCODE_PARSER)
exp.add_parser('translator_parser', exp.TRANSLATOR_PARSER)
exp.add_parser('single_search_parser', exp.SINGLE_SEARCH_PARSER)

exp.add_suite(BENCHMARKS_DIR, ['gripper:prob01.pddl'])
exp.add_algorithm('ff', REPO, 'tip', ['--search', 'lazy_greedy([ff()])'])
exp.add_algorithm('add', REPO, 'tip', ['--search', 'lazy_greedy([add()])'])

exp.add_report(AbsoluteReport(), outfile='report-abs.html')
exp.add_report(ScatterPlotReport(attributes='expansions'))

exp.run_steps()
