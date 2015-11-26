#! /usr/bin/env python

"""
Example lab experiment that approximates the number pi.

This file contains the advanced version of the experiment where pi is
calculated with increasing precision.

This experiment builds on the basic pi.py experiment.
"""

from lab.experiment import Experiment
from lab.reports import Report


EXPPATH = 'data/exp-pi'


class PiReport(Report):
    def get_text(self):
        lines = []
        for run_id, run in self.props.items():
            lines.append('%s %s' % (run['time'], run['diff']))
        return '\n'.join(lines)

exp = Experiment(EXPPATH)
exp.add_resource('PARSER', 'pi-parser-ext.py', 'pi-parser.py')
exp.add_resource('CALC', 'calculate.py', 'calculate.py')

for rounds in [1, 5, 10, 50, 100, 500, 1000, 5000, 10000]:
    run = exp.add_run()
    run.add_command('calc-pi', ['CALC', rounds], time_limit=10, mem_limit=1024)
    run.add_command('parse-pi', ['PARSER'])
    run.set_property('id', ['calc-%d' % rounds])


def good(run):
    return run['diff'] <= 0.01


exp.add_report(
    Report(format='html', attributes=['pi', 'diff'], filter=good))

exp.add_report(PiReport(), outfile='plot.dat')

exp()
