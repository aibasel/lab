#! /usr/bin/env python

"""
Example downward experiment that runs FF on a single problem.

Please adapt EXPPATH and REPO to be the path where the experiment shall be put
and the location of your Fast Downward repository.

The file planner-ext.py contains an "advanced" version of this basic experiment.
"""

import os

from downward.experiment import DownwardExperiment
from downward.reports.absolute import AbsoluteReport
from lab.steps import Step


EXPNAME = 'planner'
EXPPATH = os.path.join(os.path.expanduser('~'), 'lab', 'experiments', EXPNAME)
REPO = '/home/jendrik/projects/Downward/downward'

exp = DownwardExperiment(EXPPATH, REPO)

exp.add_suite('gripper:prob01.pddl')
exp.add_config('ff', ['--search', 'lazy(single(ff()))'])

exp.add_step(Step('report-abs-p', AbsoluteReport('problem'),
                  exp.eval_dir,
                  os.path.join(exp.eval_dir, '%s-abs-p.html' % EXPNAME)))

exp()
