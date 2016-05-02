#! /usr/bin/env python

"""Solve some tasks with A* and the LM-Cut heuristic."""

import os.path
import platform

from lab.environments import LocalEnvironment, MaiaEnvironment

from downward.experiment import FastDownwardExperiment
from downward.reports.absolute import AbsoluteReport


SUITE = ['gripper:prob01.pddl']
ATTRIBUTES = ['coverage', 'expansions']

if 'cluster' in platform.node():
    REPO = os.path.expanduser('~/projects/downward')
    ENV = MaiaEnvironment(priority=0)
else:
    REPO = os.path.expanduser('~/projects/Downward/downward')
    ENV = LocalEnvironment(processes=2)
OLD_BENCHMARKS_DIR = os.path.join(REPO, 'benchmarks')
NEW_BENCHMARKS_DIR = os.path.join(REPO, 'misc', 'tests', 'benchmarks')
if os.path.exists(NEW_BENCHMARKS_DIR):
    BENCHMARKS_DIR = NEW_BENCHMARKS_DIR
else:
    BENCHMARKS_DIR = OLD_BENCHMARKS_DIR
REVISION_CACHE = os.path.expanduser('~/lab/revision-cache')

exp = FastDownwardExperiment(environment=ENV, revision_cache=REVISION_CACHE)
exp.add_suite(BENCHMARKS_DIR, SUITE)
exp.add_algorithm(
    'lmcut', REPO, 'tip', ['--search', 'astar(lmcut())'])

# Make a report (AbsoluteReport is the standard report).
exp.add_report(
    AbsoluteReport(attributes=ATTRIBUTES), outfile='report.html')

# Parse the commandline and show or run experiment steps.
exp.run_steps()
