#! /usr/bin/env python

"""Solve some tasks with A* and the LM-Cut heuristic."""

import os
import platform
import subprocess

from lab.steps import Step
from lab.environments import LocalEnvironment, MaiaEnvironment
from downward.experiment import DownwardExperiment
from downward.reports.absolute import AbsoluteReport


EXPPATH = 'data/exp-lmcut'
REPO = os.path.expanduser('~/projects/Downward/downward')
SUITE = ['gripper:prob01.pddl', 'zenotravel:pfile1']
CONFIGS = [('lmcut', ['--search', 'astar(lmcut())'])]
ATTRIBUTES = ['coverage', 'expansions']

if 'cluster' in platform.node():
    ENV = MaiaEnvironment(priority=-10)
else:
    ENV = LocalEnvironment(processes=2)

exp = DownwardExperiment(path=EXPPATH, repo=REPO, environment=ENV)
exp.add_suite(SUITE)
for nick, config in CONFIGS:
    exp.add_config(nick, config)

# Make a report containing absolute numbers (this is the most common report).
report = os.path.join(exp.eval_dir, 'report.html')
exp.add_report(AbsoluteReport(attributes=ATTRIBUTES), outfile=report)

# "Publish" the results with "cat" for demonstration purposes.
exp.add_step(Step('publish-report', subprocess.call, ['cat', report]))

# Compress the experiment directory.
exp.add_step(Step.zip_exp_dir(exp))

# Parse the commandline and show or run experiment steps.
exp()
