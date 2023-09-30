#! /usr/bin/env python

import json
import os
import shutil

from downward import suites
from downward.cached_revision import CachedFastDownwardRevision
from downward.experiment import FastDownwardAlgorithm, FastDownwardRun
from lab.experiment import Experiment

import project


REPO = project.get_repo_base()
BENCHMARKS_DIR = os.environ["DOWNWARD_BENCHMARKS"]
SCP_LOGIN = "myname@myserver.com"
REMOTE_REPOS_DIR = "/infai/seipp/projects"
BOUNDS_FILE = "bounds.json"
SUITE = ["depot:p01.pddl", "grid:prob01.pddl", "gripper:prob01.pddl"]
REVISION_CACHE = (
    os.environ.get("DOWNWARD_REVISION_CACHE") or project.DIR / "data" / "revision-cache"
)
if project.REMOTE:
    # ENV = project.BaselSlurmEnvironment(email="my.name@myhost.ch")
    ENV = project.TetralithEnvironment(
        email="first.last@liu.se", extra_options="#SBATCH --account=snic2022-5-341"
    )
    SUITE = project.SUITE_OPTIMAL_STRIPS
else:
    ENV = project.LocalEnvironment(processes=2)

CONFIGS = [
    ("ff", ["--search", "lazy_greedy([ff()], bound=BOUND)"]),
]
BUILD_OPTIONS = []
DRIVER_OPTIONS = [
    "--validate",
    "--overall-time-limit",
    "5m",
    "--overall-memory-limit",
    "3584M",
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

        bounds = {}
        with open(BOUNDS_FILE) as f:
            bounds = json.load(f)
        for task in suites.build_suite(BENCHMARKS_DIR, SUITE):
            upper_bound = bounds[f"{task.domain}:{task.problem}"]
            if upper_bound is None:
                upper_bound = "infinity"
            config_with_bound = config.copy()
            config_with_bound[-1] = config_with_bound[-1].replace(
                "bound=BOUND", f"bound={upper_bound}"
            )
            algo = FastDownwardAlgorithm(
                algo_name,
                cached_rev,
                DRIVER_OPTIONS,
                config_with_bound,
            )
            run = FastDownwardRun(exp, algo, task)
            exp.add_run(run)

exp.add_parser(project.FastDownwardExperiment.EXITCODE_PARSER)
exp.add_parser(project.FastDownwardExperiment.TRANSLATOR_PARSER)
exp.add_parser(project.FastDownwardExperiment.SINGLE_SEARCH_PARSER)
exp.add_parser(project.DIR / "parser.py")
exp.add_parser(project.FastDownwardExperiment.PLANNER_PARSER)

exp.add_step("build", exp.build)
exp.add_step("start", exp.start_runs)
exp.add_fetcher(name="fetch")

if not project.REMOTE:
    exp.add_step("remove-eval-dir", shutil.rmtree, exp.eval_dir, ignore_errors=True)
    project.add_scp_step(exp, SCP_LOGIN, REMOTE_REPOS_DIR)

project.add_absolute_report(
    exp,
    attributes=ATTRIBUTES,
    filter=[project.add_evaluations_per_time, project.group_domains],
)

exp.run_steps()
