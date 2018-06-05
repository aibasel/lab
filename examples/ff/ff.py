#! /usr/bin/env python

"""
Example experiment for the FF planner
(http://fai.cs.uni-saarland.de/hoffmann/ff.html).
"""

import os
import platform

from lab.environments import LocalEnvironment, BaselSlurmEnvironment
from lab.experiment import Experiment

# In the future, these modules should live in a separate
# "planning" or "solver" package.
from downward import suites
from downward.reports.absolute import AbsoluteReport


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
    'coverage', 'evaluations', 'plan', 'times',
    'trivially_unsolvable']


# Create a new experiment.
exp = Experiment(environment=ENV)
# Add built-in parsers.
exp.add_parser(exp.LAB_STATIC_PROPERTIES_PARSER)
exp.add_parser(exp.LAB_DRIVER_PARSER)
# Add custom ff-parser.
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
        time_limit=1800,
        memory_limit=2048)
    # AbsoluteReport needs the following properties:
    # 'domain', 'problem', 'algorithm', 'coverage'.
    run.set_property('domain', task.domain)
    run.set_property('problem', task.problem)
    run.set_property('algorithm', 'ff')
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
    AbsoluteReport(attributes=ATTRIBUTES),
    outfile='report.html')

# Parse the commandline and run the specified steps.
exp.run_steps()
