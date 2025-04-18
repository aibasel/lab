#! /usr/bin/env python

"""
Example experiment using a simple vertex cover solver.
"""

import glob
import os

from downward.reports.absolute import AbsoluteReport
from lab.environments import BaselSlurmEnvironment, LocalEnvironment
from lab.experiment import Experiment
from lab.parser import Parser
from lab.reports import Attribute


# Create custom report class with suitable info and error attributes.
class BaseReport(AbsoluteReport):
    INFO_ATTRIBUTES = ["time_limit", "memory_limit", "seed"]
    ERROR_ATTRIBUTES = [
        "domain",
        "problem",
        "algorithm",
        "unexplained_errors",
        "error",
        "node",
    ]


REMOTE = BaselSlurmEnvironment.is_present()
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BENCHMARKS_DIR = os.path.join(SCRIPT_DIR, "benchmarks")
BHOSLIB_GRAPHS = sorted(glob.glob(os.path.join(BENCHMARKS_DIR, "bhoslib", "*.mis")))
RANDOM_GRAPHS = sorted(glob.glob(os.path.join(BENCHMARKS_DIR, "random", "*.txt")))
ALGORITHMS = ["2approx", "greedy"]
SEED = 2018
TIME_LIMIT = 1800
MEMORY_LIMIT = 2048

if REMOTE:
    ENV = BaselSlurmEnvironment(email="my.name@unibas.ch")
    SUITE = BHOSLIB_GRAPHS + RANDOM_GRAPHS
else:
    ENV = LocalEnvironment(processes=2)
    # Use smaller suite for local tests.
    SUITE = BHOSLIB_GRAPHS[:1] + RANDOM_GRAPHS[:1]
ATTRIBUTES = [
    "cover",
    "cover_size",
    "error",
    "solve_time",
    "solver_exit_code",
    Attribute("solved", absolute=True),
]

"""
Create parser for the following example solver output:

Algorithm: 2approx
Cover: set([1, 3, 5, 6, 7, 8, 9])
Cover size: 7
Solve time: 0.000771s
"""


def make_parser():
    def solved(content, props):
        props["solved"] = int("cover" in props)

    def error(content, props):
        if props["solved"]:
            props["error"] = "cover-found"
        else:
            props["error"] = "unsolved"

    vc_parser = Parser()
    vc_parser.add_pattern(
        "node", r"node: (.+)\n", type=str, file="driver.log", required=True
    )
    vc_parser.add_pattern(
        "solver_exit_code", r"solve exit code: (.+)\n", type=int, file="driver.log"
    )
    vc_parser.add_pattern("cover", r"Cover: (\{.*\})", type=str)
    vc_parser.add_pattern("cover_size", r"Cover size: (\d+)\n", type=int)
    vc_parser.add_pattern("solve_time", r"Solve time: (.+)s", type=float)
    vc_parser.add_function(solved)
    vc_parser.add_function(error)
    return vc_parser


# Create a new experiment.
exp = Experiment(environment=ENV)
# Add solver to experiment and make it available to all runs.
exp.add_resource("solver", os.path.join(SCRIPT_DIR, "solver.py"))
# Add custom parser.
exp.add_parser(make_parser())

for algo in ALGORITHMS:
    for task in SUITE:
        run = exp.add_run()
        # Create a symbolic link and an alias. This is optional. We
        # could also use absolute paths in add_command().
        run.add_resource("task", task, symlink=True)
        run.add_command(
            "solve",
            ["{solver}", "--seed", str(SEED), "{task}", algo],
            time_limit=TIME_LIMIT,
            memory_limit=MEMORY_LIMIT,
        )
        # AbsoluteReport needs the following attributes:
        # 'domain', 'problem' and 'algorithm'.
        domain = os.path.basename(os.path.dirname(task))
        task_name = os.path.basename(task)
        run.set_property("domain", domain)
        run.set_property("problem", task_name)
        run.set_property("algorithm", algo)
        # BaseReport needs the following properties:
        # 'time_limit', 'memory_limit', 'seed'.
        run.set_property("time_limit", TIME_LIMIT)
        run.set_property("memory_limit", MEMORY_LIMIT)
        run.set_property("seed", SEED)
        # Every run has to have a unique id in the form of a list.
        run.set_property("id", [algo, domain, task_name])

# Add step that writes experiment files to disk.
exp.add_step("build", exp.build)

# Add step that executes all runs.
exp.add_step("start", exp.start_runs)

# Add step that parses the logs.
exp.add_step("parse", exp.parse)

# Add step that collects properties from run directories and
# writes them to *-eval/properties.
exp.add_fetcher(name="fetch")

# Make a report.
exp.add_report(BaseReport(attributes=ATTRIBUTES), outfile="report.html")

# Parse the commandline and run the given steps.
exp.run_steps()
