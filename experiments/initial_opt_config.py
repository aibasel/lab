#! /usr/bin/env python

"""
Questions:

How do we add values like "quality"?
"""

import os
import platform
import shutil
import sys

from lab.downward.downward_experiment import DownwardExperiment
from lab.downward.checkouts import Translator, Preprocessor, Planner
from lab.downward.reports.absolute import AbsoluteReport
from lab.environments import LocalEnvironment, GkiGridEnvironment
from lab.downward import configs
from lab.experiment import Step
from lab import tools


EXPNAME = 'js-' + os.path.splitext(os.path.basename(__file__))[0]
if platform.node() == 'habakuk':
    EXPPATH = os.path.join('/home/downward/jendrik/experiments/', EXPNAME)
    REPORTS = '/home/downward/jendrik/reports'
    REPO = '/home/downward/jendrik/downward'
    SUITE = 'LMCUT_DOMAINS'
    ENV = GkiGridEnvironment()
else:
    EXPPATH = os.path.join(tools.DEFAULT_EXP_DIR, EXPNAME)
    REPORTS = tools.DEFAULT_REPORTS_DIR
    REPO = '/home/jendrik/projects/Downward/downward'
    SUITE = 'gripper:prob01.pddl'
    ENV = LocalEnvironment()

ATTRIBUTES = None  # Include all attributes
LIMITS = {'search_time': 1800}
COMBINATIONS = [(Translator(repo=REPO), Preprocessor(repo=REPO), Planner(repo=REPO))]

CONFIG = ["--landmarks", "lmg=lm_rhw(only_causal_landmarks=false,"
                         "disjunctive_landmarks=true,"
                         "conjunctive_landmarks=true,no_orders=false)",
          "--heuristic", "hLMCut=lmcut()",
          "--heuristic", "hLM=lmcount(lmg,admissible=true)",
          "--heuristic", "hCombinedMax=max([hLM,hLMCut])",
          "--search", "astar(hCombinedMax,mpd=true,pathmax=false,cost_type=0)"]

exp = DownwardExperiment(path=EXPPATH, env=ENV, repo=REPO,
                         combinations=COMBINATIONS, limits=LIMITS)

exp.add_suite(SUITE)

exp.add_config('opt-initial', CONFIG)

#exp.steps.insert(5, Step('clear-results', shutil.rmtree, exp.eval_dir))

abs_domain_report_file = os.path.join(REPORTS, '%s-abs-d.html' % EXPNAME)
abs_problem_report_file = os.path.join(REPORTS, '%s-abs-p.html' % EXPNAME)
exp.add_step(Step('report-abs-d', AbsoluteReport('domain', attributes=ATTRIBUTES), exp.eval_dir, abs_domain_report_file))
exp.add_step(Step('report-abs-p', AbsoluteReport('problem', attributes=ATTRIBUTES), exp.eval_dir, abs_problem_report_file))

# exp.steps is a list that can be manipulated:
# steps can be removed, appended, replaced and inserted
#exp.steps.insert(6, Step('report-abs', AbsoluteReport('domain', attributes=['coverage']), exp.eval_dir, 'report-abs.html'))
#del exp.steps[7]

# Compress the experiment directory
#exp.add_step(Step('zip-exp-dir', Call, ['tar', '-cvzf', exp.path + '.tar.gz', exp.path]))

def copy_results():
    dest = os.path.join(os.path.expanduser('~'), '.public_html/',
                        os.path.basename(abs_domain_report_file))
    shutil.copy2(abs_domain_report_file, dest)

# Copy the results
exp.add_step(Step('copy-results', copy_results))

# Remove the experiment directory
#exp.add_step(Step('remove-exp-dir', shutil.rmtree, exp.path))

# This method parses the commandline. We assume this file is called exp.py.
# Supported styles:
# ./exp.py 1
# ./exp.py 4 5 6
# ./exp.py next
# ./exp.py rest      # runs all remaining steps
exp()
