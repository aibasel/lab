#! /usr/bin/env python
"""
Example lab experiment that approximates the number pi.

This file contains the simplest version of the experiment where a basic
approximation is not calculated, but simply printed.

You can find a more advanced experiment in pi-ext.py .
"""

from lab.experiment import Experiment


EXPPATH = 'exp-pi'

exp = Experiment(EXPPATH)

run = exp.add_run()
run.add_command('calc-pi', ['echo', 'Pi:', '3.14'])
run.set_property('id', ['echo-1'])

exp()
