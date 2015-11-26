#! /usr/bin/env python

"""
Basic example showing how to use lab.

This experiment consists of a single run that just prints all files
contained in the run's directory. A simple parser parses the output
and counts the number of files.

This experiment shows how to
* add a command to a run
* add a run to an experiment
* add a custom result parser
* add a report
"""

import os

from lab.experiment import Experiment
from lab.environments import LocalEnvironment
from lab.reports import Report


EXPNAME = 'simple-exp'
EXPPATH = os.path.join('data', EXPNAME)
ENV = LocalEnvironment()

# Create a new experiment.
exp = Experiment(path=EXPPATH, environment=ENV)
exp.add_resource(
    'SIMPLE_PARSER', 'simple-parser.py', 'simple-parser.py')
reportfile = os.path.join(exp.eval_dir, EXPNAME + '.html')

run = exp.add_run()
run.add_command('list-dir', ['ls', '-l'])
# Every run has to have an id in the form of a list.
run.set_property('id', ['current-dir'])
run.add_command('parse', ['SIMPLE_PARSER'])

# Make a default report.
exp.add_report(
    Report(attributes=['number_of_files', 'first_number']),
    outfile=reportfile)

# Parse the commandline and run the specified steps.
exp()
