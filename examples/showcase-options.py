#! /usr/bin/env python
"""
This experiment demonstrates most of the available options.
"""

import os.path
import platform
import shutil
from subprocess import call

from lab.environments import LocalEnvironment, MaiaEnvironment
from lab.fetcher import Fetcher
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
from downward.reports.timeout import TimeoutReport


DIR = os.path.dirname(os.path.abspath(__file__))
REMOTE = 'cluster' in platform.node()
if REMOTE:
    REPO = os.path.expanduser('~/projects/downward')
    BENCHMARKS_DIR = os.path.expanduser('~/projects/benchmarks')
    ENV = MaiaEnvironment()
else:
    REPO = os.path.expanduser('~/projects/Downward/downward')
    BENCHMARKS_DIR = os.path.expanduser('~/projects/Downward/benchmarks')
    ENV = LocalEnvironment(processes=4)
CACHE_DIR = os.path.expanduser('~/lab/')
REV = 'tip'
ATTRIBUTES = ['coverage']
EXPNAME = 'showcase-options'

exp = FastDownwardExperiment(environment=ENV, cache_dir=CACHE_DIR)

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

portfolio_paths = [
    os.path.join(REPO, 'src', 'search', 'downward-seq-opt-fdss-1.py'),
    os.path.join(REPO, 'src', 'driver', 'portfolios', 'seq_opt_fdss_1.py'),
    os.path.join(REPO, 'driver', 'portfolios', 'seq_opt_fdss_1.py'),
]
portfolio_found = False
for path in portfolio_paths:
    if os.path.exists(path):
        exp.add_algorithm(
            'opt-fdss-1', REPO, REV, [], driver_options=['--portfolio', path])
        portfolio_found = True
if not portfolio_found:
    raise SystemExit('Error: portfolio not found')

# Before we fetch the new results, delete the old ones.
exp.steps.insert(0, Step(
    'delete-eval-dir', shutil.rmtree, exp.eval_dir, ignore_errors=True))

# Before we build the experiment, delete the old experiment directory.
exp.steps.insert(0, Step('delete-exp-dir', shutil.rmtree, exp.path, ignore_errors=True))


# Define some filters

def solved(run):
    """Only include solved problems."""
    return run['coverage'] == 1


def only_two_configs(run):
    return run['config'] in ['lama11', 'iter-hadd']


# Showcase some fetcher options.

def eval_dir(num):
    return os.path.join(exp.eval_dir, 'test%d' % num)


exp.add_step(Step('fetcher-test1', Fetcher(), exp.path, eval_dir(1), copy_all=True))
exp.add_step(Step(
    'fetcher-test2', Fetcher(), exp.path, eval_dir(2),
    copy_all=True, write_combined_props=True))
exp.add_step(Step(
    'fetcher-test3', Fetcher(), exp.path, eval_dir(3),
    filter_config='lama11'))
exp.add_step(Step('fetcher-test4', Fetcher(), exp.path, eval_dir(4),
                  parsers=os.path.join(DIR, 'simple', 'simple-parser.py')))


# Add report steps
abs_domain_report_file = os.path.join(exp.eval_dir, '%s-abs-d.html' % EXPNAME)
abs_problem_report_file = os.path.join(exp.eval_dir, '%s-abs-p.html' % EXPNAME)
abs_combined_report_file = os.path.join(exp.eval_dir, '%s-abs-c.tex' % EXPNAME)
exp.add_step(Step(
    'report-abs-d',
    AbsoluteReport('domain', attributes=ATTRIBUTES + ['expansions', 'cost']),
    exp.eval_dir,
    abs_domain_report_file))
exp.add_step(Step(
    'report-abs-p-filter',
    AbsoluteReport(
        'problem',
        attributes=ATTRIBUTES,
        filter=only_two_configs),
    exp.eval_dir,
    abs_problem_report_file))
exp.add_step(Step(
    'report-abs-combined',
    AbsoluteReport(attributes=None, format='tex'),
    exp.eval_dir,
    abs_combined_report_file))
exp.add_report(
    TimeoutReport([1, 2, 3]),
    outfile=os.path.join(exp.eval_dir, 'timeout-eval', 'properties'))
exp.add_report(
    FilterReport(),
    outfile=os.path.join(exp.eval_dir, 'filter-eval', 'properties'))


def get_domain(run1, run2):
    return run1['domain']


def sat_vs_opt(run):
    config = run['config']
    categories = {
        'lama11': 'sat', 'iter-hadd': 'sat', 'sat-fdss-1': 'sat',
        'ipdb': 'opt', 'opt-fdss-1': 'opt'
    }
    return {categories[config]: [(config, run.get('expansions'))]}


exp.add_report(
    ScatterPlotReport(
        attributes=['expansions'],
        filter_config=['iter-hadd', 'lama11']),
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

exp.add_step(Step(
    'report-scatter-domain',
    ScatterPlotReport(
        attributes=['expansions'],
        filter=only_two_configs,
        get_category=get_domain, xscale='linear', yscale='linear',
        category_styles={'gripper': {'c': 'b', 'marker': '+'}},
        params=params,
        legend_location=None),
    exp.eval_dir,
    os.path.join(exp.eval_dir, 'plots', 'scatter-domain.png')))
exp.add_report(
    ProblemPlotReport(
        attributes=['expansions'], yscale='symlog', params=params),
    name='report-plot-prob',
    outfile='plots')
exp.add_step(Step(
    'report-plot-cat',
    ProblemPlotReport(get_points=sat_vs_opt),
    exp.eval_dir,
    os.path.join(exp.eval_dir, 'plots')))
exp.add_step(Step(
    'report-ipc',
    IpcReport(attributes=['quality']),
    exp.eval_dir,
    os.path.join(exp.eval_dir, 'ipc.tex')))
exp.add_step(Step(
    'report-relative-d',
    RelativeReport(
        'domain',
        attributes=['expansions'],
        filter_config=['lama11', 'iter-hadd'],
        rel_change=0.1,
        abs_change=20),
    exp.eval_dir,
    os.path.join(exp.eval_dir, 'relative.html')))
exp.add_report(
    RelativeReport(
        'problem',
        attributes=['quality', 'coverage', 'expansions'],
        filter_config=['lama11', 'iter-hadd']),
    name='report-relative-p',
    outfile='relative.html')
exp.add_report(
    CompareConfigsReport(
        [('lama11', 'iter-hadd')],
        attributes=['quality', 'coverage', 'expansions']),
    name='report-compare',
    outfile='compare.html')

# Write suite of solved problems
suite_file = os.path.join(exp.eval_dir, '%s_solved_suite.py' % EXPNAME)
exp.add_step(Step('report-suite', SuiteReport(filter=solved), exp.eval_dir, suite_file))

exp.add_report(
    TaskwiseReport(
        attributes=['coverage', 'expansions'],
        filter_config=['ipdb']),
    name='report-taskwise',
    outfile='taskwise.html')

exp.add_report(
    AbsoluteReport(
        'problem', colored=True, attributes=[
            'coverage', 'evaluated', 'evaluations', 'search_time',
            'cost', 'memory', 'error', 'cost_all', 'limit_search_time',
            'initial_h_value', 'initial_h_values', 'run_dir']),
    name='report-abs-p',
    outfile=abs_problem_report_file)

exp.add_step(Step('finished', call, ['echo', 'Experiment', 'finished.']))


if __name__ == '__main__':
    # This method parses the commandline. We assume this file is called exp.py.
    # Supported styles:
    # ./exp.py 1
    # ./exp.py 4 5 6
    exp()
