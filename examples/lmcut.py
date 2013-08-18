#! /usr/bin/env python

"""Solve some tasks with A* and the LM-Cut heuristic."""

import os
import subprocess

from downward.experiment import DownwardExperiment
from downward.reports.absolute import AbsoluteReport
from lab.steps import Step


EXPNAME = 'lmcut-exp'
REPO = '/home/jendrik/projects/Downward/downward'
SUITE = ['gripper:prob01.pddl', 'zenotravel:pfile1']

exp = DownwardExperiment(path=EXPNAME, repo=REPO)
exp.add_suite(SUITE)
exp.add_config('lmcut', ['--search', 'astar(lmcut())'])

# Make a report containing absolute numbers (this is the most common report).
report = os.path.join(exp.eval_dir, 'report.html')
exp.add_report(AbsoluteReport(attributes=['coverage', 'expansions']),
               outfile=report)

# "Publish" the results with "cat" for demonstration purposes.
exp.add_step(Step('publish-report', subprocess.call, ['cat', report]))

# Compress the experiment directory.
exp.add_step(Step.zip_exp_dir(exp))

# Remove the experiment directory.
exp.add_step(Step.remove_exp_dir(exp))

# Parse the commandline and show or run experiment steps.
exp()
