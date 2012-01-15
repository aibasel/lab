#! /usr/bin/env python

import os
import shutil
import platform
from subprocess import call

from lab.experiment import Experiment
from lab.environments import LocalEnvironment, GkiGridEnvironment
from lab.experiment import Step
from lab.reports import Report
from lab import tools

EXPNAME = 'simple-exp'
if platform.node() == 'habakuk':
    EXPPATH = os.path.join('/home/downward/jendrik/experiments/', EXPNAME)
    REPORT = os.path.join('/home/downward/jendrik/reports', EXPNAME + '.html')
    ENV = GkiGridEnvironment()
else:
    EXPPATH = os.path.join(tools.DEFAULT_EXP_DIR, EXPNAME)
    REPORT = os.path.join(tools.DEFAULT_REPORTS_DIR, 'simple-report.html')
    ENV = LocalEnvironment()

exp = Experiment(path=EXPPATH, env=ENV)
exp.add_resource('SIMPLE_PARSER', 'simple-parser.py', 'simple-parser.py')

run = exp.add_run()
run.add_command('list-dir', ['ls'])
run.set_property('id', ['current-dir'])
run.require_resource('SIMPLE_PARSER')
run.add_command('parse', ['SIMPLE_PARSER'])

# Make a default report
exp.add_step(Step('report', Report(), exp.eval_dir, REPORT))

# Compress the experiment directory
exp.add_step(Step.zip_exp_dir(exp))

exp.add_step(Step.publish_reports(REPORT))

# Remove the experiment directory
exp.add_step(Step.remove_exp_dir(exp))

# This method parses the commandline. We assume this file is called exp.py.
# Supported styles:
# ./exp.py 1
# ./exp.py 4 5 6
# ./exp.py all
exp()
