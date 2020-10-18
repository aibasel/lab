#! /usr/bin/env python

import os

import project


REPO = project.get_repo_base()
BENCHMARKS_DIR = os.environ["DOWNWARD_BENCHMARKS"]
if project.REMOTE:
    SUITE = project.SUITE_SATISFICING
    ENV = project.BaselSlurmEnvironment(email="my.name@unibas.ch")
else:
    SUITE = ["depot:p01.pddl", "grid:prob01.pddl", "gripper:prob01.pddl"]
    ENV = project.LocalEnvironment(processes=2)

CONFIGS = [
    (f"{index:02d}-{h_nick}", ["--search", f"eager_greedy([{h}])"])
    for index, (h_nick, h) in enumerate([
        ("cg", "cg(transform=adapt_costs(one))"),
        ("ff", "ff(transform=adapt_costs(one))"),
    ], start=1)
]
BUILD_OPTIONS = []
DRIVER_OPTIONS = ["--overall-time-limit", "5m"]
REVS = [
    ("release-20.06.0", "20.06"),
]
ATTRIBUTES = [
    "error", "run_dir", "search_start_time", "search_start_memory",
    "total_time", "initial_h_value", "coverage",
    "expansions", "memory", project.EVALUATIONS_PER_TIME,
]

exp = project.CommonExperiment(environment=ENV)
for config_nick, config in CONFIGS:
    for rev, rev_nick in REVS:
        algo_name = f"{rev_nick}:{config_nick}" if rev_nick else config_nick
        exp.add_algorithm(
            algo_name,
            REPO,
            rev,
            config,
            build_options=BUILD_OPTIONS,
            driver_options=DRIVER_OPTIONS,
        )
exp.add_suite(BENCHMARKS_DIR, SUITE)

project.add_absolute_report(
    exp,
    attributes=ATTRIBUTES,
    filter=[project.add_evaluations_per_time])

attributes = ["expansions"]
pairs = [
    ("20.06:01-cg", "20.06:02-ff"),
]
for algo1, algo2 in pairs:
    for attr in attributes:
        exp.add_report(project.ScatterPlotReport(
                relative=project.RELATIVE,
                get_category=None if project.TEX else lambda run1, run2: run1["domain"],
                attributes=[attr],
                filter_algorithm=[algo1, algo2],
                filter=[project.add_evaluations_per_time],
                format="tex" if project.TEX else "png",
            ),
            name=f'{exp.name}-{algo1}-vs-{algo2}-{attr}{"-rel" if project.RELATIVE else ""}')

exp.run_steps()
