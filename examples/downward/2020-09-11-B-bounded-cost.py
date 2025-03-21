#! /usr/bin/env python

import os

import custom_parser
import project

from downward import suites
from downward.cached_revision import CachedFastDownwardRevision
from downward.experiment import FastDownwardAlgorithm, FastDownwardRun
from lab.experiment import Experiment

REPO = project.get_repo_base()
BENCHMARKS_DIR = os.environ["DOWNWARD_BENCHMARKS"]
SCP_LOGIN = "myname@myserver.com"
REMOTE_REPOS_DIR = "/infai/username/projects"
SUITE = ["depot:p01.pddl", "grid:prob01.pddl", "gripper:prob01.pddl"]
REVISION_CACHE = (
    os.environ.get("DOWNWARD_REVISION_CACHE") or project.DIR / "data" / "revision-cache"
)
if project.REMOTE:
    # ENV = project.BaselSlurmEnvironment(email="my.name@myhost.ch")
    ENV = project.TetralithEnvironment(
        memory_per_cpu="9G",  # leave some space for the scripts
        email="first.last@liu.se",
        extra_options="#SBATCH --account=naiss2024-5-421",
    )
    SUITE = project.SUITE_OPTIMAL_STRIPS
else:
    ENV = project.LocalEnvironment(processes=2)

CONFIGS = [
    ("ff", ["--search", "lazy_greedy([ff()], bound=100)"]),
]
BUILD_OPTIONS = []
DRIVER_OPTIONS = [
    "--validate",
    "--overall-time-limit",
    "5m",
    "--overall-memory-limit",
    "8G",
]
# Pairs of revision identifier and optional revision nick.
REV_NICKS = [
    ("main", ""),
]
ATTRIBUTES = [
    "error",
    "run_dir",
    "search_start_time",
    "search_start_memory",
    "total_time",
    "h_values",
    "coverage",
    "expansions",
    "memory",
    project.EVALUATIONS_PER_TIME,
]

exp = Experiment(environment=ENV)
for rev, rev_nick in REV_NICKS:
    cached_rev = CachedFastDownwardRevision(REVISION_CACHE, REPO, rev, BUILD_OPTIONS)
    cached_rev.cache()
    exp.add_resource("", cached_rev.path, cached_rev.get_relative_exp_path())
    for config_nick, config in CONFIGS:
        algo_name = f"{rev_nick}-{config_nick}" if rev_nick else config_nick

        for task in suites.build_suite(BENCHMARKS_DIR, SUITE):
            algo = FastDownwardAlgorithm(
                algo_name,
                cached_rev,
                DRIVER_OPTIONS,
                config,
            )
            run = FastDownwardRun(exp, algo, task)
            exp.add_run(run)

exp.add_parser(project.FastDownwardExperiment.EXITCODE_PARSER)
exp.add_parser(project.FastDownwardExperiment.TRANSLATOR_PARSER)
exp.add_parser(project.FastDownwardExperiment.SINGLE_SEARCH_PARSER)
exp.add_parser(custom_parser.get_parser())
exp.add_parser(project.FastDownwardExperiment.PLANNER_PARSER)

exp.add_step("build", exp.build)
exp.add_step("start", exp.start_runs)
exp.add_step("parse", exp.parse)
exp.add_fetcher(name="fetch")

project.add_absolute_report(
    exp,
    attributes=ATTRIBUTES,
    filter=[project.add_evaluations_per_time, project.group_domains],
)
if not project.REMOTE:
    project.add_scp_step(exp, SCP_LOGIN, REMOTE_REPOS_DIR)
project.add_compress_exp_dir_step(exp)

exp.run_steps()
