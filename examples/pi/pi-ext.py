#! /usr/bin/env python

import os

from lab.experiment import Experiment
from lab.steps import Step
from lab.reports import Report


EXPNAME = 'pi'
EXPPATH = os.path.join(os.path.expanduser('~'), 'workshop', EXPNAME)

exp = Experiment(EXPPATH)
exp.add_resource('PARSER', 'pi-parser-ext.py', 'pi-parser.py')
exp.add_resource('CALC', 'calculate.py', 'calculate.py')

for rounds in [1, 5, 10, 50, 100, 500, 1000, 5000, 10000]:
    run = exp.add_run()
    run.require_resource('PARSER')
    run.require_resource('CALC')
    run.add_command('calc-pi', ['CALC', rounds], time_limit=10, mem_limit=1024)
    run.add_command('parse-pi', ['PARSER'])
    run.set_property('id', ['calc-%d' % rounds])

def good(run):
    return run['diff'] <= 0.01

exp.add_step(Step('report', Report(format='html', attributes=['pi', 'diff'], filter=good),
                  exp.eval_dir, os.path.join(exp.eval_dir, 'report.html')))

exp()
