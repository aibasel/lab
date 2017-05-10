#! /usr/bin/env python

"""
Example experiment for the FF planner
(http://fai.cs.uni-saarland.de/hoffmann/ff.html).
"""

import os
import platform

from lab.environments import LocalEnvironment, MaiaEnvironment
from lab.experiment import Experiment

# In the future, these modules should live in a separate
# "planning" or "solver" package.
from downward import suites
from downward.reports.absolute import AbsoluteReport


REMOTE = 'cluster' in platform.node()
BENCHMARKS_DIR = os.environ["DOWNWARD_BENCHMARKS"]
if REMOTE:
    ENV = MaiaEnvironment()
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
# Copy parser into experiment dir and make it available as
# "PARSER". Parsers have to be executable.
exp.add_resource('parser', 'ff-parser.py')

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
    # Schedule parser.
    run.add_command('parse', ['{parser}'])

# Make a report.
exp.add_report(
    AbsoluteReport(attributes=ATTRIBUTES),
    outfile='report.html')

# Parse the commandline and run the specified steps.
exp.run_steps()
