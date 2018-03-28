#! /usr/bin/env python
"""
This experiment demonstrates most of the available options.
"""

import os
import os.path
import platform
import shutil
from subprocess import call

from lab.environments import LocalEnvironment, MaiaEnvironment
from lab.steps import Step
from lab.reports.filter import FilterReport

from downward.experiment import FastDownwardExperiment
from downward.reports.absolute import AbsoluteReport
from downward.reports.compare import ComparativeReport
from downward.reports.scatter import ScatterPlotReport
from downward.reports.taskwise import TaskwiseReport


DIR = os.path.dirname(os.path.abspath(__file__))
REMOTE = 'cluster' in platform.node()
if REMOTE:
    ENV = MaiaEnvironment()
else:
    ENV = LocalEnvironment(processes=4)
REPO = os.environ["DOWNWARD_REPO"]
BENCHMARKS_DIR = os.environ["DOWNWARD_BENCHMARKS"]
REV_CACHE = os.path.expanduser('~/lab/revision-cache')
REV = 'tip'
ATTRIBUTES = ['coverage']
EXPNAME = 'showcase-options'

exp = FastDownwardExperiment(environment=ENV, revision_cache=REV_CACHE)

exp.add_parser('lab_driver_parser', exp.LAB_DRIVER_PARSER)
exp.add_parser('exitcode_parser', exp.EXITCODE_PARSER)
exp.add_parser('translator_parser', exp.TRANSLATOR_PARSER)
exp.add_parser('single_search_parser', exp.SINGLE_SEARCH_PARSER)

exp.add_suite(BENCHMARKS_DIR, ['gripper:prob01.pddl', 'miconic:s1-0.pddl'])
exp.add_algorithm('iter-hadd', REPO, REV, [
    '--heuristic', 'hadd=add()',
    '--search', 'iterated([lazy_greedy([hadd]),lazy_wastar([hadd])],repeat_last=true)'])
exp.add_algorithm(
    'ipdb', REPO, REV, ["--search", "astar(ipdb())"],
    driver_options=['--search-time-limit', 10])
exp.add_algorithm(
    'lama11', REPO, REV, [],
    driver_options=['--alias', 'seq-sat-lama-2011', '--plan-file', 'sas_plan'])
exp.add_algorithm(
    'sat-fdss-1', REPO, REV, [], driver_options=['--alias', 'seq-sat-fdss-1'])
exp.add_algorithm(
    'opt-fdss-1', REPO, REV, [], driver_options=[
        '--portfolio',
        os.path.join(REPO, 'driver', 'portfolios', 'seq_opt_fdss_1.py')])

# Before we fetch the new results, delete the old ones
exp.steps.insert(0, Step(
    'delete-old-results', shutil.rmtree, exp.eval_dir, ignore_errors=True))


# Showcase add_parse_again_step option.

exp.add_parse_again_step()


# Define some filters

def solved(run):
    """Only include solved problems."""
    return run['coverage'] == 1


def only_two_algorithms(run):
    return run['algorithm'] in ['lama11', 'iter-hadd']


# Showcase some fetcher options.

def eval_dir(num):
    return os.path.join(exp.eval_dir, 'test%d' % num)


exp.add_fetcher(
    dest=eval_dir(1), name='fetcher-test1', filter=only_two_algorithms)
exp.add_fetcher(
    dest=eval_dir(2), name='fetcher-test2', filter_algorithm='lama11')


# Add report steps
exp.add_report(
    AbsoluteReport(attributes=ATTRIBUTES + ['expansions', 'cost']),
    name='report-abs-d')
exp.add_report(
    AbsoluteReport(attributes=ATTRIBUTES, filter=only_two_algorithms),
    name='report-abs-p-filter')
exp.add_report(
    AbsoluteReport(attributes=['coverage', 'error'], format='tex'),
    outfile='report-abs-combined.tex')
exp.add_report(
    AbsoluteReport(attributes=['coverage', 'error'], format='html'),
    outfile='report-abs-combined.html')
exp.add_report(
    FilterReport(),
    outfile=os.path.join(exp.eval_dir, 'filter-eval', 'properties'))


def get_domain(run1, run2):
    return run1['domain']


exp.add_report(
    ScatterPlotReport(
        attributes=['expansions'],
        filter_algorithm=['iter-hadd', 'lama11']),
    name='report-scatter',
    outfile=os.path.join('plots', 'scatter.png'))

matplotlib_options = {
    'font.family': 'serif',
    'font.weight': 'normal',
    'font.size': 20,  # Only used if the more specific sizes are not set.
    'axes.labelsize': 20,
    'axes.titlesize': 30,
    'legend.fontsize': 22,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'lines.markersize': 10,
    'lines.markeredgewidth': 0.25,
    'lines.linewidth': 1,
    'figure.figsize': [8, 8],  # Width and height in inches.
    'savefig.dpi': 100,
}

for format in ["png", "tex"]:
    exp.add_report(
        ScatterPlotReport(
            attributes=['expansions'],
            format=format,
            filter=only_two_algorithms,
            get_category=get_domain,
            xscale='linear',
            yscale='linear',
            matplotlib_options=matplotlib_options),
        outfile=os.path.join('plots', 'scatter-domain.' + format))
exp.add_report(
    ComparativeReport(
        [('lama11', 'iter-hadd')],
        attributes=['quality', 'coverage', 'expansions']),
    name='report-compare',
    outfile='compare.html')

exp.add_report(
    TaskwiseReport(
        attributes=['coverage', 'expansions'],
        filter_algorithm=['ipdb']),
    name='report-taskwise',
    outfile='taskwise.html')

exp.add_report(
    AbsoluteReport(attributes=[
        'coverage', 'evaluated', 'evaluations', 'search_time',
        'cost', 'memory', 'error', 'cost_all', 'limit_search_time',
        'initial_h_value', 'initial_h_values', 'run_dir']),
    name='report-abs-p')

exp.add_step('finished', call, ['echo', 'Experiment', 'finished.'])


if __name__ == '__main__':
    exp.run_steps()
