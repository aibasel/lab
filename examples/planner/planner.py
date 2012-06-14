#! /usr/bin/env python

import os

from downward.experiment import DownwardExperiment
from downward.reports.absolute import AbsoluteReport
from lab.steps import Step


EXPNAME = 'planner'
WORKSHOP = os.path.join(os.path.expanduser('~'), 'workshop')
EXPPATH = os.path.join(WORKSHOP, EXPNAME)
REPO = os.path.join(WORKSHOP, 'fast-downward')

exp = DownwardExperiment(EXPPATH, REPO)

exp.add_suite('gripper:prob01.pddl')
exp.add_config('ff', ["--search", "lazy(single(ff()))"])

exp.add_step(Step('report-abs-p', AbsoluteReport('problem'),
                  exp.eval_dir,
                  os.path.join(exp.eval_dir, '%s-abs-p.html' % EXPNAME)))

exp()
