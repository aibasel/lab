#! /usr/bin/env python
"""
This experiment demonstrates most of the available options.
"""

import os
import shutil
from subprocess import call

from lab.environments import LocalEnvironment, GkiGridEnvironment
from lab.steps import Step

from downward.experiment import DownwardExperiment
from downward.checkouts import Translator, Preprocessor, Planner
from downward.reports.absolute import AbsoluteReport
from downward.reports.suite import SuiteReport
from downward.reports.scatter import ScatterPlotReport
from downward.reports.ipc import IpcReport
from downward.reports.relative import RelativeReport

import standard_exp


EXPNAME = 'showcase-options'
if standard_exp.REMOTE:
    EXPPATH = os.path.join(standard_exp.REMOTE_EXPS, EXPNAME)
    REPO = standard_exp.REMOTE_REPO
    ENV = GkiGridEnvironment()
else:
    EXPPATH = os.path.join('/home/jendrik/lab/experiments', EXPNAME)
    REPO = '/home/jendrik/projects/Downward/downward'
    ENV = LocalEnvironment()

ATTRIBUTES = ['coverage']
LIMITS = {'search_time': 900}
COMBINATIONS = [(Translator(repo=REPO), Preprocessor(repo=REPO), Planner(repo=REPO))]

exp = DownwardExperiment(EXPPATH, repo=REPO, environment=ENV, combinations=COMBINATIONS, limits=LIMITS)

multiple_plans = [
    "--heuristic", "hlm,hff=lm_ff_syn(lm_rhw(reasonable_orders=false,lm_cost_type=2,cost_type=2))",
    "--heuristic", "hadd=add()",
    "--search", "iterated([lazy_greedy([hadd]),lazy_wastar([hff,hlm],preferred=[hff,hlm],w=2)],"
    "repeat_last=false)"]

iterated_search = [
    "--heuristic", "hadd=add()",
    "--search", "iterated([lazy_greedy([hadd]),lazy_wastar([hadd])],repeat_last=true)"]

def ipdbi(imp):
    return ("ipdbi%d" % imp, ["--search", "astar(ipdb(min_improvement=%d))" % imp])

exp.add_suite('gripper:prob01.pddl')
exp.add_suite('zenotravel:pfile1')
exp.add_config('many-plans', multiple_plans)
exp.add_config('iter-search', iterated_search)
exp.add_config(*ipdbi(10))
# Use original LAMA 2011 configuration
exp.add_config('lama11', ['ipc', 'seq-sat-lama-2011', '--plan-file', 'sas_plan'])
exp.add_portfolio(os.path.join(REPO, 'src', 'search', 'downward-seq-opt-fdss-1.py'))

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
    return run['config_nick'] in ['many-plans', 'iter-search']

def filter_and_transform(run):
    """Remove "WORK" from the configs and only include certain configurations"""
    if not only_two_configs(run):
        return False
    config = run['config']
    run['config'] = config[5:] if config.startswith('WORK-') else config
    return run

# Add report steps
abs_domain_report_file = os.path.join(exp.eval_dir, '%s-abs-d.html' % EXPNAME)
abs_problem_report_file = os.path.join(exp.eval_dir, '%s-abs-p.html' % EXPNAME)
exp.add_step(Step('report-abs-d', AbsoluteReport('domain', attributes=ATTRIBUTES),
                  exp.eval_dir, abs_domain_report_file))

exp.add_step(Step('report-abs-p-filter', AbsoluteReport('problem', attributes=ATTRIBUTES,
                  filter=filter_and_transform), exp.eval_dir, abs_problem_report_file))

def get_domain(run1, run2):
    return run1['domain']

exp.add_step(Step('report-scatter',
                  ScatterPlotReport(attributes=['expansions'], filter=only_two_configs,
                                    get_category=get_domain),
                  exp.eval_dir, os.path.join(exp.eval_dir, 'scatter.png')))
exp.add_step(Step('report-ipc', IpcReport(attributes=['quality']),
                  exp.eval_dir, os.path.join(exp.eval_dir, 'ipc.tex')))
exp.add_step(Step('report-relative-d',
                  RelativeReport('domain', attributes=['expansions'],
                                 filter_config=['WORK-many-plans', 'WORK-iter-search'],
                                 rel_change=0.1, abs_change=20),
                  exp.eval_dir, os.path.join(exp.eval_dir, 'relative.html')))
exp.add_step(Step('report-relative-p',
                  RelativeReport('problem', attributes=['quality', 'coverage', 'expansions'],
                                 filter_config_nick=['many-plans', 'iter-search']),
                  exp.eval_dir, os.path.join(exp.eval_dir, 'relative.html')))

# Write suite of solved problems
suite_file = os.path.join(exp.eval_dir, '%s_solved_suite.py' % EXPNAME)
exp.add_step(Step('report-suite', SuiteReport(filter=solved), exp.eval_dir, suite_file))

# Copy the results
exp.add_step(Step.publish_reports(abs_domain_report_file, abs_problem_report_file))

# Compress the experiment directory
#exp.add_step(Step.zip_exp_dir(exp))

exp.add_step(Step('report-abs-p', AbsoluteReport('problem',
                    attributes=['coverage', 'search_time', 'cost', 'error']),
                  exp.eval_dir, abs_problem_report_file))

# Remove the experiment directory
#exp.add_step(Step.remove_exp_dir(exp))

exp.add_step(Step('finished', call, ['echo', 'Experiment', 'finished.']))


if __name__ == '__main__':
    # This method parses the commandline. We assume this file is called exp.py.
    # Supported styles:
    # ./exp.py 1
    # ./exp.py 4 5 6
    exp()
