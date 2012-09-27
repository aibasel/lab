#! /usr/bin/env python

import os

from downward.experiment import DownwardExperiment
from downward.reports.absolute import AbsoluteReport
from downward.reports.relative import RelativeReport
from downward.reports.suite import SuiteReport
from lab.steps import Step
from downward import suites
from downward.checkouts import Translator, Preprocessor, Planner


EXPNAME = 'planner'
WORKSHOP = os.path.join(os.path.expanduser('~'), 'workshop')
EXPPATH = os.path.join(WORKSHOP, EXPNAME)
REPO = '/home/jendrik/projects/Downward/downward'

combos = [
    (Translator(REPO, rev='WORK'), Preprocessor(REPO, rev=56734, dest='mypreprocessor'),
     Planner(REPO)),
     (Translator(REPO, rev='WORK'), Preprocessor(REPO, rev=56734, dest='mypreprocessor'),
     Planner(MYOTHER_REPO)),
]

exp = DownwardExperiment(EXPPATH, REPO, combinations=combos,
                         limits={'search_time': 60})

exp.add_suite(['gripper:prob01.pddl'])#, 'zenotravel'])
exp.add_config('ff', ["--search", "lazy(single(ff()))"])
exp.add_config('add', ["--search", "lazy(single(add()))"])
exp.add_portfolio('/home/')

exp.add_step(Step('report-abs-p', AbsoluteReport('problem'),
                  exp.eval_dir,
                  os.path.join(exp.eval_dir, '%s-abs-p.html' % EXPNAME)))

exp.add_step(Step('report-rel', RelativeReport('problem', rel_change=0.05),
                  exp.eval_dir,
                  os.path.join(exp.eval_dir, '%s-rel.html' % EXPNAME)))

def solved(run):
    return run['coverage'] == 1

exp.add_step(Step('suite', SuiteReport(filter=solved),
                  exp.eval_dir,
                  os.path.join(exp.eval_dir, 'suite.py')))

exp()
