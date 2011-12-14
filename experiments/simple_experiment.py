#! /usr/bin/env python

import os
import shutil
import sys
from subprocess import call

sys.path.insert(0, '/home/jendrik/projects/Downward/lab/')

# Use the full paths here to demonstrate the layout
# Later we could use __init__.py files to simplify things a bit
from lab.fetcher import Fetcher
#from lab.downward_parser import DownwardParser
from lab.experiment import Experiment, Run
from lab.environments import LocalEnvironment, GkiGridEnvironment
from lab.experiment import Step

env = LocalEnvironment()
exp = Experiment(path='/home/jendrik/my-simple-exp', env=env)
exp.add_resource('SIMPLE_PARSER_PY', '/home/jendrik/projects/Downward/lab/lab/simple_parser.py', 'simple_parser.py')

run = exp.add_run()
run.add_command('list-dir', ['ls'])
run.set_property('id', ['toplevel'])
run.require_resource('SIMPLE_PARSER_PY')
run.add_command('parse', ['SIMPLE_PARSER_PY'])

#exp.add_report()

# Compress the experiment directory
exp.add_step(Step('zip-exp-dir', call, ['tar', '-czf', exp.path + '.tar.gz', exp.path]))

def copy_results():
    dest = os.path.join(os.path.expanduser('~'), '.public_html/',
                        os.path.basename(abs_report_file))
    shutil.copy2(abs_report_file, dest)

# Copy the results
#exp.add_step(Step('copy-results', copy_results))

# Remove the experiment directory
#exp.add_step(Step('remove-exp-dir', shutil.rmtree, exp.path))

# This method parses the commandline. We assume this file is called exp.py.
# Supported styles:
# ./exp.py 1
# ./exp.py 4 5 6
# ./exp.py next
# ./exp.py rest      # runs all remaining steps
exp()

# Thoughts:
# The only difference between the Call and Step classes is that a call is
# executed when it is created, but a step has a run() method. They should
# probably be unified.

