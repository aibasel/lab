#! /usr/bin/env python

"""This experiment shows how to add a custom parser to your experiment."""

import os

from lab import tools

from downward.experiment import DownwardExperiment
from downward.reports.absolute import AbsoluteReport


EXPPATH = 'exp-custom-attributes'
REPO = '/home/jendrik/projects/Downward/downward'
SUITE = ['gripper:prob01.pddl', 'zenotravel:pfile1']
PARSER = os.path.join(tools.BASE_DIR, 'examples', 'simple', 'simple-parser.py')


class CustomDownwardExperiment(DownwardExperiment):
    def _make_search_runs(self):
        DownwardExperiment._make_search_runs(self)
        self.add_resource('MYPARSER', PARSER, 'myparser.py')
        for run in self.runs:
            run.require_resource('MYPARSER')
            run.add_command('custom-parse', ['MYPARSER'])


exp = CustomDownwardExperiment(path=EXPPATH, repo=REPO)

exp.add_suite(SUITE)
exp.add_config('lmcut', ["--search", "astar(lmcut())"])

# Make a problem-wise report.
exp.add_report(AbsoluteReport('problem', attributes=['expansions', 'first_number']))

# This method parses the commandline. Invoke the script to see all steps.
exp()
