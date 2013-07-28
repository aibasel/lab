#! /usr/bin/env python

"""This experiment runs the "lmcut" configuration on some problems."""

import os

from lab.steps import Step
from lab import tools

from downward.experiment import DownwardExperiment
from downward.reports.absolute import AbsoluteReport


EXPNAME = 'custom-attributes'
EXPPATH = os.path.join('/home/jendrik/lab/experiments', EXPNAME)
REPO = '/home/jendrik/projects/Downward/downward'
SUITE = ['gripper:prob01.pddl', 'zenotravel:pfile1']
PARSER = os.path.join(tools.BASE_DIR, 'examples', 'simple', 'simple-parser.py')


class CustomDownwardExperiment(DownwardExperiment):
    def _make_search_runs(self):
        DownwardExperiment._make_search_runs(self)
        self.add_resource(PARSER, dest='myparser.py', name='MYPARSER')
        for run in self.runs:
            run.require_resource('MYPARSER')
            run.add_command('custom-parse', ['MYPARSER'])


exp = CustomDownwardExperiment(path=EXPPATH, repo=REPO)

exp.add_suite(SUITE)
exp.add_config('lmcut', ["--search", "astar(lmcut())"])

# Make a problem-wise report.
exp.add_step(Step('report-abs-p',
                  AbsoluteReport('problem', attributes=['expansions', 'first_number']),
                  exp.eval_dir,
                  os.path.join(exp.eval_dir, '%s-abs-p.html' % EXPNAME)))

# Remove the experiment directory.
exp.add_step(Step.remove_exp_dir(exp))

# This method parses the commandline. Invoke the script to see all steps.
exp()
