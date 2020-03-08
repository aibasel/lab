#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Example experiment for running Singularity planner images.

Note that Downward Lab assumes that the evaluated algorithms are written
in good faith. It is not equipped to handle malicious code. For example,
it would be easy to write planner code that bypasses the time and memory
limits set within Downward Lab. If you're running untrusted code, we
recommend using cgroups to enforce resource limits.

A note on running Singularity on clusters: reading large Singularity
files over the network is not optimal, so we recommend copying the
images to a local filesystem (e.g., /tmp/) before running experiments.
"""

import os
import platform
import subprocess

from downward import suites
from downward.reports.absolute import AbsoluteReport
from lab.environments import BaselSlurmEnvironment, LocalEnvironment
from lab.experiment import Experiment


# Create custom report class with suitable info and error attributes.
class BaseReport(AbsoluteReport):
    INFO_ATTRIBUTES = []
    ERROR_ATTRIBUTES = [
        "domain",
        "problem",
        "algorithm",
        "unexplained_errors",
        "error",
        "node",
    ]


NODE = platform.node()
RUNNING_ON_CLUSTER = NODE.endswith((".scicore.unibas.ch", ".cluster.bc2.ch"))
DIR = os.path.abspath(os.path.dirname(__file__))
REPO = os.path.dirname(DIR)
IMAGES_DIR = os.environ["SINGULARITY_IMAGES"]
assert os.path.isdir(IMAGES_DIR), IMAGES_DIR
BENCHMARKS_DIR = os.environ["DOWNWARD_BENCHMARKS"]
if RUNNING_ON_CLUSTER:
    SUITE = ["depot", "freecell", "gripper", "zenotravel"]
    ENVIRONMENT = BaselSlurmEnvironment(
        partition="infai_1",
        email="my.name@unibas.ch",
        memory_per_cpu="3872M",
        export=["PATH"],
        setup=BaselSlurmEnvironment.DEFAULT_SETUP
        + "\nmodule load Singularity/2.6.1 2> /dev/null",
    )
    TIME_LIMIT = 1800
else:
    SUITE = ["depot:p01.pddl", "gripper:prob01.pddl", "mystery:prob07.pddl"]
    ENVIRONMENT = LocalEnvironment(processes=2)
    TIME_LIMIT = 5

ATTRIBUTES = [
    "cost",
    "coverage",
    "run_dir",
    "total_time",
    "singularity_runtime",
    "error",
]

exp = Experiment(environment=ENVIRONMENT)
exp.add_step("build", exp.build)
exp.add_step("start", exp.start_runs)
exp.add_fetcher(name="fetch")
exp.add_parser(os.path.join(DIR, "singularity-parser.py"))


def get_image(name):
    planner = name.replace("-", "_")
    image = os.path.join(IMAGES_DIR, name + ".img")
    assert os.path.exists(image), image
    return planner, image


IMAGES = [get_image("lama-first")]

for planner, image in IMAGES:
    exp.add_resource(planner, image, symlink=True)

singularity_script = os.path.join(DIR, "run-singularity.sh")
exp.add_resource("run_singularity", singularity_script)

for planner, _ in IMAGES:
    for task in suites.build_suite(BENCHMARKS_DIR, SUITE):
        run = exp.add_run()
        run.add_resource("domain", task.domain_file, "domain.pddl")
        run.add_resource("problem", task.problem_file, "problem.pddl")
        run.add_command(
            "run-planner",
            [
                "{run_singularity}",
                "{%s}" % planner,
                "{domain}",
                "{problem}",
                "sas_plan",
            ],
            time_limit=TIME_LIMIT,
            memory_limit=3584,
        )
        run.set_property("domain", task.domain)
        run.set_property("problem", task.problem)
        run.set_property("algorithm", planner)
        run.set_property("id", [planner, task.domain, task.problem])

report = os.path.join(exp.eval_dir, "{}.html".format(exp.name))
exp.add_report(BaseReport(attributes=ATTRIBUTES), outfile=report)
exp.add_step("open-report", subprocess.call, ["xdg-open", report])

exp.run_steps()
