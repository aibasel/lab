#! /usr/bin/env python

import os

from lab.steps import Step

from downward.experiment import DownwardExperiment
from downward import checkouts
from downward.checkouts import Translator, Preprocessor, Planner
from downward.suites import suite_optimal_with_ipc11
from downward.configs import default_configs_optimal
from downward.reports.compare import CompareRevisionsReport
from downward.reports.scatter import ScatterPlotReport


EXPNAME = os.path.splitext(os.path.basename(__file__))[0]
REV = EXPNAME
DIR = os.path.abspath(os.path.dirname(__file__))
EXPPATH = os.path.join(DIR, EXPNAME)
REPO = '/home/jendrik/projects/Downward/downward'
SUITE = 'gripper:prob01.pddl'  # suite_optimal_with_ipc11()
CONFIGS = default_configs_optimal()
ATTRIBUTES = [
    'coverage', 'search_time', 'score_search_time', 'total_time',
    'score_total_time', 'expansions', 'score_expansions',
    'expansions_until_last_jump', 'evaluations', 'score_evaluations',
    'generated', 'score_generated', 'memory', 'score_memory',
    'run_dir', 'cost']
SCATTER_PLOT_ATTRIBUTES = [
    'total_time', 'search_time', 'memory', 'expansions_until_last_jump']

base_rev = checkouts.get_common_ancestor(REPO, REV)
combos = [(Translator(REPO, rev=r), Preprocessor(REPO, rev=r), Planner(REPO, rev=r))
          for r in (base_rev, REV)]

exp = DownwardExperiment(path=EXPPATH, repo=REPO, combinations=combos)

exp.add_suite(SUITE)
for nick, config in CONFIGS.items():
    exp.add_config(nick, config)

exp.add_report(CompareRevisionsReport(base_rev, REV, attributes=ATTRIBUTES),
               outfile='compare.html')


def make_scatter_plots():
    for nick in CONFIGS.keys():
        config_before = '%s-%s' % (base_rev, nick)
        config_after = '%s-%s' % (REV, nick)
        for attribute in SCATTER_PLOT_ATTRIBUTES:
            name = 'scatter-%s-%s' % (attribute, nick)
            report = ScatterPlotReport(
                filter_config=[config_before, config_after],
                attributes=[attribute],
                get_category=lambda run1, run2: run1['domain'])
            report(exp.eval_dir, os.path.join(exp.eval_dir, name))

exp.add_step(Step('make-scatter-plots', make_scatter_plots))

exp()
