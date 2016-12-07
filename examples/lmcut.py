#! /usr/bin/env python

"""Solve some tasks with A* and the LM-Cut heuristic."""

import os.path
import platform

from lab.environments import LocalEnvironment, MaiaEnvironment

from downward.experiment import FastDownwardExperiment
from downward.reports.absolute import AbsoluteReport
from downward.reports.scatter import ScatterPlotReport


SUITE = ['gripper:prob01.pddl', 'depot:p01.pddl']
ATTRIBUTES = ['coverage', 'expansions']

if 'cluster' in platform.node():
    REPO = os.path.expanduser('~/projects/downward')
    BENCHMARKS_DIR = os.path.expanduser('~/projects/benchmarks')
    ENV = MaiaEnvironment(priority=0)
else:
    REPO = os.path.expanduser('~/projects/Downward/downward')
    BENCHMARKS_DIR = os.path.expanduser('~/projects/Downward/benchmarks')
    ENV = LocalEnvironment(processes=2)
REVISION_CACHE = os.path.expanduser('~/lab/revision-cache')

exp = FastDownwardExperiment(environment=ENV, revision_cache=REVISION_CACHE)
exp.add_suite(BENCHMARKS_DIR, SUITE)
exp.add_algorithm(
    'blind', REPO, 'default', ['--search', 'astar(blind())'])
exp.add_algorithm(
    'lmcut', REPO, 'default', ['--search', 'astar(lmcut())'])

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
