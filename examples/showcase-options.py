#! /usr/bin/env python
"""
This experiment demonstrates most of the available options.
"""

import os.path
import platform
import shutil
from subprocess import call

from lab.environments import LocalEnvironment, MaiaEnvironment
from lab.steps import Step
from lab.reports.filter import FilterReport

from downward.experiment import FastDownwardExperiment
from downward.reports.absolute import AbsoluteReport
from downward.reports.compare import CompareConfigsReport
from downward.reports.ipc import IpcReport
from downward.reports.plot import ProblemPlotReport
from downward.reports.relative import RelativeReport
from downward.reports.scatter import ScatterPlotReport
from downward.reports.suite import SuiteReport
from downward.reports.taskwise import TaskwiseReport


DIR = os.path.dirname(os.path.abspath(__file__))
REMOTE = 'cluster' in platform.node()
if REMOTE:
    REPO = '/infai/seipp/projects/downward'
    ENV = MaiaEnvironment()
else:
    REPO = '/home/jendrik/projects/Downward/downward'
    ENV = LocalEnvironment(processes=4)
CACHE_DIR = os.path.expanduser('~/lab')
BENCHMARKS_DIR = os.path.join(REPO, 'benchmarks')
REV = 'tip'
ATTRIBUTES = ['coverage']
EXPNAME = 'showcase-options'

exp = FastDownwardExperiment(environment=ENV, cache_dir=CACHE_DIR)

exp.add_suite(BENCHMARKS_DIR, ['gripper:prob01.pddl', 'mystery:prob07.pddl'])
exp.add_suite(BENCHMARKS_DIR, 'zenotravel:pfile1')
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
exp.add_fetcher(
    dest=eval_dir(3), name='fetcher-test3',
    parsers=os.path.join(DIR, 'simple', 'simple-parser.py'))


# Add report steps
exp.add_report(
    AbsoluteReport('domain', attributes=ATTRIBUTES + ['expansions', 'cost']),
    name='report-abs-d')
exp.add_report(
    AbsoluteReport('problem', attributes=ATTRIBUTES, filter=only_two_algorithms),
    name='report-abs-p-filter')
exp.add_report(
    AbsoluteReport(attributes=None, format='tex'),
    name='report-abs-combined')
exp.add_report(
    FilterReport(),
    outfile=os.path.join(exp.eval_dir, 'filter-eval', 'properties'))


def get_domain(run1, run2):
    return run1['domain']


def sat_vs_opt(run):
    algo = run['algorithm']
    categories = {
        'lama11': 'sat', 'iter-hadd': 'sat', 'sat-fdss-1': 'sat',
        'ipdb': 'opt', 'opt-fdss-1': 'opt'
    }
    return {categories[algo]: [(algo, run.get('expansions'))]}


exp.add_report(
    ScatterPlotReport(
        attributes=['expansions'],
        filter_algorithm=['iter-hadd', 'lama11']),
    name='report-scatter',
    outfile=os.path.join('plots', 'scatter.png'))

params = {
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

exp.add_report(
    ScatterPlotReport(
        attributes=['expansions'],
        filter=only_two_algorithms,
        get_category=get_domain,
        xscale='linear',
        yscale='linear',
        category_styles={'gripper': {'c': 'b', 'marker': '+'}},
        params=params,
        legend_location=None),
    name='report-scatter-domain',
    outfile=os.path.join('plots', 'scatter-domain.png'))
exp.add_report(
    ProblemPlotReport(
        attributes=['expansions'], yscale='symlog', params=params),
    name='report-plot-prob',
    outfile='plots')
exp.add_report(
    ProblemPlotReport(get_points=sat_vs_opt),
    name='report-plot-cat',
    outfile='plots')
exp.add_report(
    IpcReport(attributes=['quality']),
    name='report-ipc',
    outfile='ipc.tex')
exp.add_report(
    RelativeReport(
        'domain',
        attributes=['expansions'],
        filter_algorithm=['lama11', 'iter-hadd'],
        rel_change=0.1,
        abs_change=20),
    name='report-relative-d',)
exp.add_report(
    RelativeReport(
        'problem',
        attributes=['quality', 'coverage', 'expansions'],
        filter_algorithm=['lama11', 'iter-hadd']),
    name='report-relative-p')
exp.add_report(
    CompareConfigsReport(
        [('lama11', 'iter-hadd')],
        attributes=['quality', 'coverage', 'expansions']),
    name='report-compare',
    outfile='compare.html')

# Write suite of solved problems
exp.add_report(
    SuiteReport(filter=solved), name='report-suite', outfile='solved.py')

exp.add_report(
    TaskwiseReport(
        attributes=['coverage', 'expansions'],
        filter_algorithm=['ipdb']),
    name='report-taskwise',
    outfile='taskwise.html')

exp.add_report(
    AbsoluteReport(
        'problem', colored=True, attributes=[
            'coverage', 'evaluated', 'evaluations', 'search_time',
            'cost', 'memory', 'error', 'cost_all', 'limit_search_time',
            'initial_h_value', 'initial_h_values', 'run_dir']),
    name='report-abs-p')

exp.add_step('finished', call, ['echo', 'Experiment', 'finished.'])


if __name__ == '__main__':
    # This method parses the commandline. We assume this file is called exp.py.
    # Supported styles:
    # ./exp.py 1
    # ./exp.py 4 5 6
    exp()
