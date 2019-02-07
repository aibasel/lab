#! /usr/bin/env python

"""
Example experiment for the FF planner
(http://fai.cs.uni-saarland.de/hoffmann/ff.html).
"""

import os
import platform

from lab.environments import LocalEnvironment, BaselSlurmEnvironment
from lab.experiment import Experiment

from downward import suites
from downward.reports.absolute import AbsoluteReport


# Create custom report class with suitable info and error attributes.
class BaseReport(AbsoluteReport):
    INFO_ATTRIBUTES = ['time_limit', 'memory_limit']
    ERROR_ATTRIBUTES = [
        'domain', 'problem', 'algorithm', 'unexplained_errors', 'error', 'node']


NODE = platform.node()
REMOTE = NODE.endswith(".scicore.unibas.ch") or NODE.endswith(".cluster.bc2.ch")
BENCHMARKS_DIR = os.environ["DOWNWARD_BENCHMARKS"]
if REMOTE:
    ENV = BaselSlurmEnvironment(email="my.name@unibas.ch")
else:
    ENV = LocalEnvironment(processes=4)
SUITE = [
    'grid', 'gripper:prob01.pddl',
    'miconic:s1-0.pddl', 'mystery:prob07.pddl']
ATTRIBUTES = [
    'coverage', 'error', 'evaluations', 'plan', 'times',
    'trivially_unsolvable']
TIME_LIMIT = 1800
MEMORY_LIMIT = 2048


# Create a new experiment.
exp = Experiment(environment=ENV)
# Add custom parser for FF.
exp.add_parser('ff-parser.py')

for task in suites.build_suite(BENCHMARKS_DIR, SUITE):
    run = exp.add_run()
    # Create symbolic links and aliases. This is optional. We
    # could also use absolute paths in add_command().
    run.add_resource('domain', task.domain_file, symlink=True)
    run.add_resource('problem', task.problem_file, symlink=True)
    # 'ff' binary has to be on the PATH.
    # We could also use exp.add_resource().
    run.add_command(
        'run-planner',
        ['ff', '-o', '{domain}', '-f', '{problem}'],
        time_limit=TIME_LIMIT,
        memory_limit=MEMORY_LIMIT)
    # AbsoluteReport needs the following properties:
    # 'domain', 'problem', 'algorithm', 'coverage'.
    run.set_property('domain', task.domain)
    run.set_property('problem', task.problem)
    run.set_property('algorithm', 'ff')
    # BaseReport needs the following properties:
    # 'time_limit', 'memory_limit'.
    run.set_property('time_limit', TIME_LIMIT)
    run.set_property('memory_limit', MEMORY_LIMIT)
    # Every run has to have a unique id in the form of a list.
    # The algorithm name is only really needed when there are
    # multiple algorithms.
    run.set_property('id', ['ff', task.domain, task.problem])

# Add step that writes experiment files to disk.
exp.add_step('build', exp.build)

# Add step that executes all runs.
exp.add_step('start', exp.start_runs)

# Add step that collects properties from run directories and
# writes them to *-eval/properties.
exp.add_fetcher(name='fetch')

# Make a report.
exp.add_report(
    BaseReport(attributes=ATTRIBUTES),
    outfile='report.html')

# Parse the commandline and run the specified steps.
exp.run_steps()
