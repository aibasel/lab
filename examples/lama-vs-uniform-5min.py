#! /usr/bin/env python

"""
This experiment uses outdated lab API.
"""

import os
import platform
import shutil
import sys

from lab.downward.downward_experiment import DownwardExperiment
from lab.downward.checkouts import Translator, Preprocessor, Planner
from lab.downward.reports.absolute import AbsoluteReport
from lab.environments import LocalEnvironment, GkiGridEnvironment
from lab.downward import configs
from lab.experiment import Step
from lab import tools


EXPNAME = 'js-' + os.path.splitext(os.path.basename(__file__))[0]
if platform.node() == 'habakuk':
    EXPPATH = os.path.join('/home/downward/jendrik/experiments/', EXPNAME)
    REPORTS = '/home/downward/jendrik/reports'
    REPO = '/home/downward/jendrik/fastr'
    SUITE = 'IPC11'
    ENV = GkiGridEnvironment()
    PORTFOLIOS = '/home/downward/jendrik/fastr/new-scripts/portfolios'
else:
    EXPPATH = os.path.join(tools.DEFAULT_EXP_DIR, EXPNAME)
    REPORTS = tools.DEFAULT_REPORTS_DIR
    REPO = '/home/jendrik/projects/Downward/fastr'
    SUITE = 'gripper:prob01.pddl'
    ENV = LocalEnvironment()
    PORTFOLIOS = '/home/jendrik/projects/Downward/fastr/new-scripts/portfolios'

ATTRIBUTES = ['cost', 'coverage']
LIMITS = {'search_time': 300}
COMBINATIONS = [(Translator(repo=REPO), Preprocessor(repo=REPO), Planner(repo=REPO))]

exp = DownwardExperiment(path=EXPPATH, env=ENV, repo=REPO,
                         combinations=COMBINATIONS, limits=LIMITS)

exp.add_suite(SUITE)

exp.add_config('lama11', configs.lama11)
exp.add_portfolio(os.path.join(PORTFOLIOS, 'uniform-5min.py'))

abs_domain_report_file = os.path.join(REPORTS, '%s-abs-d.html' % EXPNAME)
abs_problem_report_file = os.path.join(REPORTS, '%s-abs-p.html' % EXPNAME)
exp.add_step(Step('report-abs-d', AbsoluteReport('domain', attributes=ATTRIBUTES), exp.eval_dir, abs_domain_report_file))
exp.add_step(Step('report-abs-p', AbsoluteReport('problem', attributes=ATTRIBUTES), exp.eval_dir, abs_problem_report_file))

# Remove the experiment directory
#exp.add_step(Step('remove-exp-dir', shutil.rmtree, exp.path))

# This method parses the commandline. We assume this file is called exp.py.
# Supported styles:
# ./exp.py 1
# ./exp.py 4 5 6
# ./exp.py next
# ./exp.py rest      # runs all remaining steps
exp()
