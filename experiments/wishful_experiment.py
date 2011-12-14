#! /usr/bin/env python

"""
Questions:

How do we want to do reports?
How do we add values like "quality"?
Split generic and downward experiment code?
"""

import os
import shutil
import sys

sys.path.insert(0, '/home/jendrik/projects/Downward/lab/')

# Use the full paths here to demonstrate the layout
# Later we could use __init__.py files to simplify things a bit
from lab.downward.downward_experiment import DownwardExperiment
from lab.downward.checkouts import Translator, Preprocessor, Planner
from lab.downward.reports.absolute import AbsoluteReport
from lab.downward.reports.ipc import IpcReport
from lab.downward.reports.scatter import ScatterPlotReport
from lab.downward.reports.suite import SuiteReport
from lab.environments import LocalEnvironment
from lab.downward import configs
from lab.experiment import Step
from lab import tools

EXPNAME = 'myexp'
REPORTS = os.path.join(tools.USER_DIR, 'reports')
REPO = '/home/jendrik/projects/Downward/downward'

combinations = [(Translator(repo=REPO), Preprocessor(repo=REPO), Planner(repo=REPO))]

exp = DownwardExperiment(path='/home/jendrik/%s' % EXPNAME, env=LocalEnvironment(),
                         repo=REPO, combinations=combinations)

def pdb_max_states(max_states):
    return ('pdb-max-states-%i' % max_states,
            ['--search', 'astar(pdb(max_states=%i))' % max_states])

#exp.add_suite(downward_suites.suite_ipc08_common())
exp.add_suite('gripper:prob01.pddl')
exp.add_suite('depot:pfile1')
exp.add_config(*pdb_max_states(1000))
exp.add_config('yY', configs.yY)
exp.add_config('lama', configs.lama)
for config in configs.ipc_optimal_subset():
    exp.add_config(*config)

# The next step should be done explicitly
abs_domain_report_file = os.path.join(REPORTS, '%s-abs-d.html' % EXPNAME)
abs_problem_report_file = os.path.join(REPORTS, '%s-abs-p.html' % EXPNAME)
#exp.add_report(AbsoluteReport, outfile=abs_report_file)
exp.add_step(Step('report-abs-d', AbsoluteReport('domain'), exp.eval_dir, abs_domain_report_file))
exp.add_step(Step('report-abs-p', AbsoluteReport('problem'), exp.eval_dir, abs_problem_report_file))
exp.add_step(Step('report-ipc', IpcReport('coverage'), exp.eval_dir, os.path.join(REPORTS, 'ipc.tex')))
exp.add_step(Step('report-scatter', ScatterPlotReport(), exp.eval_dir, os.path.join(REPORTS, 'scatter.tex')))
exp.add_step(Step('report-scatter', ScatterPlotReport(), exp.eval_dir, os.path.join(REPORTS, 'scatter.tex')))
exp.add_step(Step('report-suite', SuiteReport(), exp.eval_dir, os.path.join(REPORTS, 'suite.py')))

# exp.steps is a list that can be manipulated:
# steps can be removed, appended, replaced and inserted
#exp.steps.insert(6, Step('scatter-report', ScatterReport(), dir=exp.eval_dir))
#del exp.steps[7]

# Compress the experiment directory
#exp.add_step(Step('zip-exp-dir', Call, ['tar', '-cvzf', exp.path + '.tar.gz', exp.path]))

def copy_results():
    dest = os.path.join(os.path.expanduser('~'), '.public_html/',
                        os.path.basename(abs_domain_report_file))
    shutil.copy2(abs_report_file, dest)

# Copy the results
exp.add_step(Step('copy-results', copy_results))

# Remove the experiment directory
exp.add_step(Step('remove-exp-dir', shutil.rmtree, exp.path))

# This method parses the commandline. We assume this file is called exp.py.
# Supported styles:
# ./exp.py 1
# ./exp.py 4 5 6
# ./exp.py next
# ./exp.py rest      # runs all remaining steps
exp()
