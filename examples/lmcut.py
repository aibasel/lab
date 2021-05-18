#! /usr/bin/env python

"""Solve some tasks with A* and the LM-Cut heuristic."""

import os
import os.path
import platform
import re

from downward.experiment import FastDownwardExperiment
from downward.reports.absolute import AbsoluteReport
from downward.reports.scatter import ScatterPlotReport
from lab import cached_revision
from lab.environments import BaselSlurmEnvironment, LocalEnvironment, SlurmEnvironment


class TetralithEnvironment(SlurmEnvironment):
    """Environment for NSC Tetralith cluster in Linköping."""

    DEFAULT_PARTITION = "tetralith"
    DEFAULT_QOS = "normal"
    # The maximum wall-clock time limit for a job is 7 days. The default
    # is 2 hours. In certain situations, the scheduler prefers to schedule
    # jobs shorter than 24 hours.
    DEFAULT_TIME_LIMIT_PER_JOB = "24:00:00"
    # There are 1908 nodes. 1844 nodes have 93.1 GiB (97637616 KiB) of
    # memory and 64 nodes have 384 GB of memory. All nodes have 32 cores.
    # So for the vast majority of nodes, we have 2979 MiB per core. The
    # slurm.conf file sets DefMemPerCPU=2904. Since this is rather low, we
    # use the default value from the BaselSlurmEnvironment. This also
    # allows us to keep the default memory limit in the
    # FastDownwardExperiment class.
    DEFAULT_MEMORY_PER_CPU = "3872M"
    MAX_TASKS = 1000

    def __init__(self, runs_per_job=100, **kwargs):
        super().__init__(runs_per_job=runs_per_job, **kwargs)

    # def _submit_job(self, job_name, job_file, job_dir, dependency=None):
    #    pass  # TODO: use base class implementation.

    @classmethod
    def is_present(cls):
        node = platform.node()
        return node == "tetralith2.nsc.liu.se" or re.match(r"n\d+", node)


ATTRIBUTES = ["coverage", "error", "expansions", "total_time"]

NODE = platform.node()
if TetralithEnvironment.is_present():
    # Create bigger suites with suites.py from the downward-benchmarks repo.
    SUITE = ["depot", "freecell", "gripper", "zenotravel"]
    assert BaselSlurmEnvironment
    ENV = TetralithEnvironment(email="jendrik.seipp@liu.se")
else:
    SUITE = ["depot:p01.pddl", "gripper:prob01.pddl", "mystery:prob07.pddl"]
    ENV = LocalEnvironment(processes=2)
# Use path to your Fast Downward repository.
REPO = os.environ["DOWNWARD_REPO"]
BENCHMARKS_DIR = os.environ["DOWNWARD_BENCHMARKS"]
# If REVISION_CACHE is None, the default ./data/revision-cache is used.
REVISION_CACHE = os.environ.get("DOWNWARD_REVISION_CACHE")
VCS = cached_revision.get_version_control_system(REPO)
REV = "default" if VCS == cached_revision.MERCURIAL else "main"

exp = FastDownwardExperiment(environment=ENV, revision_cache=REVISION_CACHE)

# Add built-in parsers to the experiment.
exp.add_parser(exp.EXITCODE_PARSER)
exp.add_parser(exp.TRANSLATOR_PARSER)
exp.add_parser(exp.SINGLE_SEARCH_PARSER)
exp.add_parser(exp.PLANNER_PARSER)

exp.add_suite(BENCHMARKS_DIR, SUITE)
exp.add_algorithm("blind", REPO, REV, ["--search", "astar(blind())"])
exp.add_algorithm("lmcut", REPO, REV, ["--search", "astar(lmcut())"])

# Add step that writes experiment files to disk.
exp.add_step("build", exp.build)

# Add step that executes all runs.
exp.add_step("start", exp.start_runs)

# Add step that collects properties from run directories and
# writes them to *-eval/properties.
exp.add_fetcher(name="fetch")

# Add report step (AbsoluteReport is the standard report).
exp.add_report(AbsoluteReport(attributes=ATTRIBUTES), outfile="report.html")

# Add scatter plot report step.
exp.add_report(
    ScatterPlotReport(attributes=["expansions"], filter_algorithm=["blind", "lmcut"]),
    outfile="scatterplot.png",
)

# Parse the commandline and show or run experiment steps.
exp.run_steps()
