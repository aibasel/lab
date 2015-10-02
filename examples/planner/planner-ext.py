#! /usr/bin/env python

"""
Example downward experiment that runs FF on two tasks.

Please adapt EXPPATH and REPO to be the path where the experiment shall be put
and the location of your Fast Downward repository.

The file planner.py contains the "basic" version of this experiment.
"""

import os

from downward.checkouts import Translator, Preprocessor, Planner
from downward.experiment import DownwardExperiment
from downward.reports.absolute import AbsoluteReport
from downward.reports.suite import SuiteReport
from downward.reports.scatter import ScatterPlotReport
from lab.steps import Step


EXPPATH = 'data/exp-planner'
REPO = '/home/jendrik/projects/Downward/downward'

REV = 'default'
COMBOS = [
    (Translator(REPO, rev=REV), Preprocessor(REPO, rev=REV), Planner(REPO, rev=REV)),
]

exp = DownwardExperiment(
    EXPPATH, REPO, combinations=COMBOS, limits={'search_time': 60})

exp.add_suite(['gripper:prob01.pddl'])
exp.add_suite('zenotravel:pfile2')
exp.add_config('ff', ['--search', 'lazy(single(ff()))'])
exp.add_config('add', ['--search', 'lazy(single(add()))'])

exp.add_report(AbsoluteReport('problem'), name='make-report', outfile='report-abs-p.html')


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
