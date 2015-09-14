#! /usr/bin/env python
"""
This experiment demonstrates most of the available options.
"""

import os
import platform
import shutil
from subprocess import call

from lab.environments import LocalEnvironment, MaiaEnvironment
from lab.steps import Step
from lab.fetcher import Fetcher
from lab.reports.filter import FilterReport

from downward.experiment import DownwardExperiment
from downward.checkouts import Translator, Preprocessor, Planner
from downward.reports.absolute import AbsoluteReport
from downward.reports.suite import SuiteReport
from downward.reports.scatter import ScatterPlotReport
from downward.reports.plot import ProblemPlotReport
from downward.reports.ipc import IpcReport
from downward.reports.relative import RelativeReport
from downward.reports.compare import CompareConfigsReport
from downward.reports.timeout import TimeoutReport
from downward.reports.taskwise import TaskwiseReport


DIR = os.path.dirname(os.path.abspath(__file__))
EXPNAME = 'showcase-options'
EXPPATH = os.path.join(DIR, 'data', EXPNAME)
REMOTE = 'cluster' in platform.node()
if REMOTE:
    REPO = '/infai/seipp/projects/downward'
    ENV = MaiaEnvironment()
else:
    REPO = '/home/jendrik/projects/Downward/downward'
    ENV = LocalEnvironment(processes=4)
CACHE_DIR = os.path.expanduser('~/lab/')
PYTHON = 'python'

ATTRIBUTES = ['coverage']
LIMITS = {'search_time': 900}
COMBINATIONS = [(Translator(repo=REPO), Preprocessor(repo=REPO), Planner(repo=REPO))]

exp = DownwardExperiment(EXPPATH, repo=REPO, environment=ENV, combinations=COMBINATIONS,
                         limits=LIMITS, cache_dir=CACHE_DIR)
exp.set_path_to_python(PYTHON)

exp.add_suite('gripper:prob01.pddl')
exp.add_suite('mystery:prob07.pddl')
exp.add_suite('zenotravel:pfile1', benchmark_dir=os.path.join(REPO, 'benchmarks'))
exp.add_config('iter-hadd', [
    '--heuristic', 'hadd=add()',
    '--search', 'iterated([lazy_greedy([hadd]),lazy_wastar([hadd])],repeat_last=true)'])
exp.add_config('ipdb', ["--search", "astar(ipdb())"], timeout=10)
# Use original LAMA 2011 configuration
exp.add_config('lama11', ['ipc', 'seq-sat-lama-2011', '--plan-file', 'sas_plan'])
exp.add_config('fdss-1', ['ipc', 'seq-sat-fdss-1', '--plan-file', 'sas_plan'])
old_portfolio_path = os.path.join(REPO, 'src', 'search', 'downward-seq-opt-fdss-1.py')
new_portfolio_path = os.path.join(REPO, 'src', 'driver', 'portfolios', 'seq_opt_fdss_1.py')
if os.path.exists(old_portfolio_path):
    exp.add_portfolio(old_portfolio_path)
elif os.path.exists(new_portfolio_path):
    exp.add_portfolio(new_portfolio_path)
else:
    raise SystemExit('portfolio not found')

# Before we fetch the new results, delete the old ones
exp.steps.insert(5, Step('delete-old-results', shutil.rmtree, exp.eval_dir, ignore_errors=True))

# Before we build the experiment, delete the old experiment directory
# and the preprocess directory
exp.steps.insert(0, Step('delete-exp-dir', shutil.rmtree, exp.path, ignore_errors=True))
exp.steps.insert(0, Step('delete-preprocess-dir', shutil.rmtree, exp.preprocess_exp_path,
                         ignore_errors=True))


# Define some filters

def solved(run):
    """Only include solved problems."""
    return run['coverage'] == 1


def only_two_configs(run):
    return run['config_nick'] in ['lama11', 'iter-hadd']


def remove_work_tag(run):
    """Remove "WORK-" from the configs."""
    config = run['config']
    config = config[5:] if config.startswith('WORK-') else config
    # Shorten long config name.
    config = config.replace('downward-', '')
    run['config'] = config
    return run


def filter_and_transform(run):
    """Remove "WORK-" from the configs and only include certain configurations.

    This also demonstrates a nested filter (one that calls another filter)."""
    if not only_two_configs(run):
        return False
    return remove_work_tag(run)


# Check that the various fetcher options work.
def eval_dir(num):
    return os.path.join(exp.eval_dir, 'test%d' % num)


exp.add_step(Step('fetcher-test1', Fetcher(), exp.path, eval_dir(1), copy_all=True))
exp.add_step(Step('fetcher-test2', Fetcher(), exp.path, eval_dir(2), copy_all=True, write_combined_props=True))
exp.add_step(Step('fetcher-test3', Fetcher(), exp.path, eval_dir(3), filter_config_nick='lama11'))
exp.add_step(Step('fetcher-test4', Fetcher(), exp.path, eval_dir(4),
                  parsers=os.path.join(DIR, 'simple', 'simple-parser.py')))


# Add report steps
abs_domain_report_file = os.path.join(exp.eval_dir, '%s-abs-d.html' % EXPNAME)
abs_problem_report_file = os.path.join(exp.eval_dir, '%s-abs-p.html' % EXPNAME)
abs_combined_report_file = os.path.join(exp.eval_dir, '%s-abs-c.tex' % EXPNAME)
exp.add_step(Step('report-abs-d', AbsoluteReport('domain', attributes=ATTRIBUTES + ['expansions', 'cost']),
                  exp.eval_dir, abs_domain_report_file))
exp.add_step(Step('report-abs-p-filter', AbsoluteReport('problem', attributes=ATTRIBUTES,
                  filter=filter_and_transform), exp.eval_dir, abs_problem_report_file))
exp.add_step(Step('report-abs-combined', AbsoluteReport(attributes=None, format='tex'),
                  exp.eval_dir, abs_combined_report_file))
exp.add_report(TimeoutReport([1, 2, 3]), outfile=os.path.join(exp.eval_dir, 'timeout-eval', 'properties'))
exp.add_report(FilterReport(), outfile=os.path.join(exp.eval_dir, 'filter-eval', 'properties'))


def get_domain(run1, run2):
    return run1['domain']


def sat_vs_opt(run):
    category = {'lama11': 'sat', 'iter-hadd': 'sat', 'ipdb': 'opt',
                'fdss': 'opt'}
    for nick, cat in category.items():
        if nick in run['config_nick']:
            return {cat: [(run['config'], run.get('expansions'))]}


exp.add_report(ScatterPlotReport(attributes=['expansions'],
                                 filter_config_nick=['iter-hadd', 'lama11']),
               name='report-scatter', outfile=os.path.join('plots', 'scatter.png'))

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

exp.add_step(Step('report-scatter-domain',
                  ScatterPlotReport(attributes=['expansions'], filter=only_two_configs,
                                    get_category=get_domain, xscale='linear', yscale='linear',
                                    category_styles={'gripper': {'c': 'b', 'marker': '+'}},
                                    params=params,
                                    legend_location=None),
                  exp.eval_dir, os.path.join(exp.eval_dir, 'plots', 'scatter-domain.png')))
exp.add_report(ProblemPlotReport(attributes=['expansions'], filter=remove_work_tag,
                                 yscale='symlog', params=params),
               name='report-plot-prob', outfile='plots')
exp.add_step(Step('report-plot-cat',
                  ProblemPlotReport(filter=remove_work_tag, get_points=sat_vs_opt),
                  exp.eval_dir, os.path.join(exp.eval_dir, 'plots')))
exp.add_step(Step('report-ipc', IpcReport(attributes=['quality']),
                  exp.eval_dir, os.path.join(exp.eval_dir, 'ipc.tex')))
exp.add_step(Step('report-relative-d',
                  RelativeReport('domain', attributes=['expansions'],
                                 filter_config=['WORK-lama11', 'WORK-iter-hadd'],
                                 rel_change=0.1, abs_change=20),
                  exp.eval_dir, os.path.join(exp.eval_dir, 'relative.html')))
exp.add_report(RelativeReport('problem', attributes=['quality', 'coverage', 'expansions'],
                              filter_config_nick=['lama11', 'iter-hadd']),
               name='report-relative-p',
               outfile='relative.html')
exp.add_report(CompareConfigsReport([('WORK-lama11', 'WORK-iter-hadd')],
                                    attributes=['quality', 'coverage', 'expansions']),
               name='report-compare',
               outfile='compare.html')

# Write suite of solved problems
suite_file = os.path.join(exp.eval_dir, '%s_solved_suite.py' % EXPNAME)
exp.add_step(Step('report-suite', SuiteReport(filter=solved), exp.eval_dir, suite_file))

exp.add_report(TaskwiseReport(attributes=['coverage', 'expansions'],
                              filter_config_nick=['ipdb']),
               name='report-taskwise',
               outfile='taskwise.html')

exp.add_report(
    AbsoluteReport(
        'problem', colored=True, attributes=[
            'coverage', 'evaluated', 'evaluations', 'search_time',
            'cost', 'memory', 'error', 'cost_all', 'limit_search_time',
            'initial_h_value', 'initial_h_values', 'run_dir']),
    name='report-abs-p', outfile=abs_problem_report_file)

exp.add_step(Step('finished', call, ['echo', 'Experiment', 'finished.']))


if __name__ == '__main__':
    # This method parses the commandline. We assume this file is called exp.py.
    # Supported styles:
    # ./exp.py 1
    # ./exp.py 4 5 6
    exp()
