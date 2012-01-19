#! /usr/bin/env python

"""
Basic example for the use of the lab package.

This experiment shows how you
- add a command to a run
- add a run to an experiment
- add a custom result parser
- use the default report
- use additional standard steps
"""

import os
import platform

from lab.experiment import Experiment
from lab.environments import LocalEnvironment, GkiGridEnvironment
from lab.experiment import Step
from lab.reports import Report
from lab import tools


EXPNAME = 'simple-exp'
if platform.node() == 'habakuk':
    EXPPATH = os.path.join('/home/downward/jendrik/experiments/', EXPNAME)
    ENV = GkiGridEnvironment()
else:
    EXPPATH = os.path.join(tools.DEFAULT_EXP_DIR, EXPNAME)
    ENV = LocalEnvironment()

# Create a new experiment.
exp = Experiment(path=EXPPATH, env=ENV)
exp.add_resource('SIMPLE_PARSER', 'simple-parser.py', 'simple-parser.py')
reportfile = os.path.join(exp.eval_dir, EXPNAME + '.html')

run = exp.add_run()
run.add_command('list-dir', ['ls'])
# Every run has to have an id in the form of a list.
run.set_property('id', ['current-dir'])
run.require_resource('SIMPLE_PARSER')
run.add_command('parse', ['SIMPLE_PARSER'])

# Make a default report.
exp.add_step(Step('report', Report(), exp.eval_dir, reportfile))

# Compress the experiment directory.
exp.add_step(Step.zip_exp_dir(exp))

# Copy the reports to the html directory.
exp.add_step(Step.publish_reports(reportfile))

# Remove the experiment directory.
exp.add_step(Step.remove_exp_dir(exp))

# This method parses the commandline.
# Supported styles:
# ./simple-exp.py 1
# ./simple-exp.py report
# ./simple-exp.py 1 2 3
# ./simple-exp.py all
exp()
