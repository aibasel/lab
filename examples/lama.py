#! /usr/bin/env python

"""Solve some example tasks with LAMA-2011."""

import os.path
import platform

from lab.environments import LocalEnvironment, MaiaEnvironment

from downward.experiments.fast_downward_experiment import FastDownwardExperiment
from downward.reports.absolute import AbsoluteReport


SUITE = ['gripper:prob01.pddl', 'zenotravel:pfile1']
ATTRIBUTES = ['coverage']

if 'cluster' in platform.node():
    REPO = os.path.expanduser('~/projects/downward')
    ENV = MaiaEnvironment(priority=-10)
else:
    REPO = os.path.expanduser('~/projects/Downward/downward')
    ENV = LocalEnvironment(processes=2)
BENCHMARKS = os.path.join(REPO, 'benchmarks')
CACHE_DIR = os.path.expanduser('~/lab')

exp = FastDownwardExperiment(environment=ENV, cache_dir=CACHE_DIR)
exp.add_suite(BENCHMARKS, SUITE)
exp.add_algorithm(
    'lama', REPO, 'issue67', [],
    driver_options=['--alias', 'seq-sat-lama-2011'])

# Make a report containing absolute numbers (this is the most common report).
exp.add_report(AbsoluteReport(attributes=ATTRIBUTES), outfile='report.html')

# Parse the commandline and show or run experiment steps.
exp()
