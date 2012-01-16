#! /usr/bin/env python
"""
This experiment preprocesses all problems.
"""

import os
import platform
import shutil
from subprocess import call

from downward.experiment import DownwardExperiment
from lab.environments import LocalEnvironment, GkiGridEnvironment
from lab.steps import Step
from lab import tools


EXPNAME = 'js-' + os.path.splitext(os.path.basename(__file__))[0]
SUITE = 'ALL'

if platform.node() == 'habakuk':
    EXPPATH = os.path.join('/home/downward/jendrik/experiments/', EXPNAME)
    REPO = '/home/downward/jendrik/downward'
    ENV = GkiGridEnvironment()
else:
    EXPPATH = os.path.join(tools.DEFAULT_EXP_DIR, EXPNAME)
    REPO = '/home/jendrik/projects/Downward/downward'
    ENV = LocalEnvironment()

exp = DownwardExperiment(path=EXPPATH, env=ENV, repo=REPO)
exp.add_suite(SUITE)

# Remove search steps
del exp.steps[3:6]


if __name__ == '__main__':
    # This method parses the commandline. We assume this file is called exp.py.
    # Supported styles:
    # ./exp.py 1
    # ./exp.py 4 5 6
    # ./exp.py all
    exp()
