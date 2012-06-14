#! /usr/bin/env python

import os

from lab.experiment import Experiment


EXPNAME = 'pi'
EXPPATH = os.path.join(os.path.expanduser('~'), 'workshop', EXPNAME)

exp = Experiment(EXPPATH)

run = exp.add_run()
run.add_command('calc-pi', ['echo', 'Pi:', '3.14'])
run.set_property('id', ['echo-1'])

exp()
