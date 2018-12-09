#! /usr/bin/env python

"""
Example experiment using a simple vertex cover solver.
"""

import glob
import os
import platform

from lab.environments import LocalEnvironment, BaselSlurmEnvironment
from lab.experiment import Experiment
from lab.reports import Attribute

# This report should ideally live the Lab package.
from downward.reports.absolute import AbsoluteReport

NODE = platform.node()
REMOTE = NODE.endswith(".scicore.unibas.ch") or NODE.endswith(".cluster.bc2.ch")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BENCHMARKS_DIR = os.path.join(SCRIPT_DIR, "benchmarks")
BHOSLIB_GRAPHS = sorted(glob.glob(os.path.join(BENCHMARKS_DIR, 'bhoslib', '*.mis')))
RANDOM_GRAPHS = sorted(glob.glob(os.path.join(BENCHMARKS_DIR, 'random', '*.txt')))
ALGORITHMS = ["2approx", "greedy"]
SEED = 2018

if REMOTE:
    ENV = BaselSlurmEnvironment(email="my.name@unibas.ch")
    SUITE = BHOSLIB_GRAPHS + RANDOM_GRAPHS
else:
    ENV = LocalEnvironment(processes=4)
    # Use smaller suite for local tests.
    SUITE = BHOSLIB_GRAPHS[:1] + RANDOM_GRAPHS[:1]
ATTRIBUTES = [
    'cover', 'cover_size', 'error', 'solve_time', 'solver_exit_code',
    Attribute('solved', absolute=True)]

# Create a new experiment.
exp = Experiment(environment=ENV)
# Add solver to experiment and make it available to all runs.
exp.add_resource('solver', os.path.join(SCRIPT_DIR, 'solver.py'))
# Add custom parser.
exp.add_parser('parser.py')

for algo in ALGORITHMS:
    for task in SUITE:
        run = exp.add_run()
        # Create a symbolic link and an alias. This is optional. We
        # could also use absolute paths in add_command().
        run.add_resource('task', task, symlink=True)
        run.add_command(
            'solve',
            ['{solver}', '--seed', str(SEED), '{task}', algo],
            time_limit=1800,
            memory_limit=2048)
        # AbsoluteReport needs the following attributes:
        # 'domain', 'problem' and 'algorithm'.
        domain = os.path.basename(os.path.dirname(task))
        task_name = os.path.basename(task)
        run.set_property('domain', domain)
        run.set_property('problem', task_name)
        run.set_property('algorithm', algo)
        # Every run has to have a unique id in the form of a list.
        run.set_property('id', [algo, domain, task_name])

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

# Parse the commandline and run the given steps.
exp.run_steps()
