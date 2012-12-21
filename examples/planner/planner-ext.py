#! /usr/bin/env python

import os

from downward.experiment import DownwardExperiment
from downward.reports.absolute import AbsoluteReport
from downward.reports.suite import SuiteReport
from downward.reports.scatter import ScatterPlotReport
from lab.steps import Step
from downward import suites
from downward.checkouts import Translator, Preprocessor, Planner


EXPNAME = 'planner'
WORKSHOP = os.path.join(os.path.expanduser('~'), 'workshop')
EXPPATH = os.path.join(WORKSHOP, EXPNAME)
REPO = os.path.join(WORKSHOP, 'fast-downward')

#combos = [
#    (Translator(REPO, rev='WORK'), Preprocessor(REPO, rev=3097, dest='mypreprocessor'),
#     Planner(REPO)),
#     (Translator(REPO, rev='WORK'), Preprocessor(REPO, rev=3097, dest='mypreprocessor'),
#     Planner(MYOTHER_REPO)),
#]

exp = DownwardExperiment(EXPPATH, REPO, #combinations=combos,
                         limits={'search_time': 60})

exp.add_suite(['gripper:prob01.pddl'])
#exp.add_suite('zenotravel')
exp.add_config('ff', ['--search', 'lazy(single(ff()))'])
exp.add_config('add', ['--search', 'lazy(single(add()))'])
exp.add_portfolio(os.path.join(REPO, 'src', 'search', 'downward-seq-sat-fdss-1.py'))

exp.add_step(Step('report-abs-p', AbsoluteReport('problem'),
                  exp.eval_dir,
                  os.path.join(exp.eval_dir, '%s-abs-p.html' % EXPNAME)))

def solved(run):
    return run['coverage'] == 1

exp.add_step(Step('suite', SuiteReport(filter=solved),
                  exp.eval_dir,
                  os.path.join(exp.eval_dir, 'suite.py')))

exp.add_step(Step('scatter', ScatterPlotReport(filter_config_nick=['ff', 'add'],
                                               attributes='expansions', format='png'),
                  exp.eval_dir,
                  os.path.join(exp.eval_dir, 'scatter')))

exp()
