#! /usr/bin/env python

"""This experiment runs the "lmcut" configuration on some problems."""

import os

from downward.experiment import DownwardExperiment
from downward.reports.absolute import AbsoluteReport
from lab.steps import Step


EXPNAME = 'lmcut'
EXPPATH = os.path.join('/home/jendrik/lab/experiments', EXPNAME)
REPO = '/home/jendrik/projects/Downward/downward'
SUITE = ['gripper:prob01.pddl', 'zenotravel:pfile1']

exp = DownwardExperiment(path=EXPPATH, repo=REPO)

exp.add_suite(SUITE)
exp.add_config('lmcut', ["--search", "astar(lmcut())"])

# Make a report containing absolute numbers (this is the normal report).
exp.add_step(Step('report-abs',
                  AbsoluteReport(attributes=['coverage', 'expansions'],
                                 resolution='problem'),
                  exp.eval_dir,
                  os.path.join(exp.eval_dir, '%s-abs.html' % EXPNAME)))

# Compress the experiment directory.
exp.add_step(Step.zip_exp_dir(exp))

# Remove the experiment directory.
exp.add_step(Step.remove_exp_dir(exp))

# This method parses the commandline. Invoke the script to see all steps.
exp()
