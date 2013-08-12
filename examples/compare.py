#! /usr/bin/env python

import os

from downward.experiments.comparerevisions import CompareRevisionsExperiment


EXPNAME = os.path.splitext(os.path.basename(__file__))[0]
DIR = os.path.abspath(os.path.dirname(__file__))
EXPPATH = os.path.join(DIR, EXPNAME)
REPO = '/home/jendrik/projects/Downward/downward'
SUITE = ['gripper:prob01.pddl', 'zenotravel:pfile1']

exp = CompareRevisionsExperiment(EXPPATH, REPO, 'opt', rev='issue344')
exp.suites = SUITE

exp()
