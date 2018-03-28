#! /usr/bin/env python

"""Solve some tasks with A* and the LM-Cut heuristic."""

import os
import os.path
import platform

from lab.environments import LocalEnvironment, BaselSlurmEnvironment

from downward.experiment import FastDownwardExperiment
from downward.reports.absolute import AbsoluteReport
from downward.reports.scatter import ScatterPlotReport


ATTRIBUTES = ['coverage', 'error', 'quality', 'cost']

if 'cluster' in platform.node():
    # Create bigger suites with suites.py from the downward-benchmarks repo.
    SUITE = ['depot', 'freecell', 'gripper', 'zenotravel']
    ENV = BaselSlurmEnvironment(email="my.name@unibas.ch")
else:
    SUITE = ['depot:p01.pddl', 'gripper:prob01.pddl']
    ENV = LocalEnvironment(processes=2)
# Change to path to your Fast Downward repository.
REPO = os.environ["DOWNWARD_REPO"]
BENCHMARKS_DIR = os.environ["DOWNWARD_BENCHMARKS"]
REVISION_CACHE = os.path.expanduser('~/lab/revision-cache')

exp = FastDownwardExperiment(environment=ENV, revision_cache=REVISION_CACHE)

# Add default parsers to the experiment.
exp.add_parser('lab_driver_parser', exp.LAB_DRIVER_PARSER)
exp.add_parser('exitcode_parser', exp.EXITCODE_PARSER)
exp.add_parser('translator_parser', exp.TRANSLATOR_PARSER)
exp.add_parser('portfolio_parser', exp.PORTFOLIO_PARSER)

exp.add_suite(BENCHMARKS_DIR, SUITE)
exp.add_algorithm(
    'lama', REPO, 'default', [], driver_options=['--alias', 'seq-sat-lama-2011'])

# Make a report (AbsoluteReport is the standard report).
exp.add_report(
    AbsoluteReport(attributes=ATTRIBUTES), outfile='report.html')

# Compare the number of expansions in a scatter plot.
exp.add_report(
    ScatterPlotReport(
        attributes=["expansions"], filter_algorithm=["blind", "lmcut"]),
    outfile='scatterplot.png')

# Parse the commandline and show or run experiment steps.
exp.run_steps()
