#! /usr/bin/env python

"""
Example experiment for running Singularity/Apptainer planner images.

The time and memory limits set with Lab can be circumvented by solvers that fork
child processes. Their resource usage is not checked. If you're running solvers
that don't check their resource usage like Fast Downward, we recommend using
cgroups or the "runsolver" tool to enforce resource limits. Since setting time
limits for solvers with cgroups is difficult, the experiment below uses the
``runsolver`` tool, which has been used in multiple SAT competitions to enforce
resource limits. For the experiment to run, the runsolver binary needs to be on
the PATH. You can obtain a runsolver copy from
https://github.com/jendrikseipp/runsolver.

Since Singularity (and Apptainer) reserve 1-2 GiB of *virtual* memory when
starting the container, we recommend either enforcing a higher virtual memory
limit with ``runsolver`` or limiting RSS memory with ``runsolver`` (like below).
For limiting RSS memory, you can also use `runlim
<https://github.com/arminbiere/runlim>`_, which is more actively maintained than
runsolver.

A note on running Singularity on clusters: reading large Singularity files over
the network is not optimal, so we recommend copying the images to a local
filesystem (e.g., /tmp/) before running experiments.
"""

import os
import platform
import re
import sys
from pathlib import Path

from singularity_parser import get_parser

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
RUNNING_ON_CLUSTER = re.fullmatch(r"login12|ic[ab]\d\d", NODE)
DIR = Path(__file__).resolve().parent
REPO = DIR.parent
IMAGES_DIR = Path(os.environ["SINGULARITY_IMAGES"])
assert IMAGES_DIR.is_dir(), IMAGES_DIR
BENCHMARKS_DIR = os.environ["DOWNWARD_BENCHMARKS"]
MEMORY_LIMIT = 3584  # MiB
if RUNNING_ON_CLUSTER:
    SUITE = ["depot", "freecell", "gripper", "zenotravel"]
    ENVIRONMENT = BaselSlurmEnvironment(
        partition="infai_2",
        email="my.name@unibas.ch",
        memory_per_cpu="3872M",
        export=["PATH"],
        setup=BaselSlurmEnvironment.DEFAULT_SETUP,
        # Until recently, we had to load the Singularity module here
        # by adding "module load Singularity/2.6.1 2> /dev/null".
    )
    TIME_LIMIT = 1800
else:
    SUITE = ["depot:p01.pddl", "gripper:prob01.pddl", "mystery:prob07.pddl"]
    ENVIRONMENT = LocalEnvironment(processes=2)
    TIME_LIMIT = 5

ATTRIBUTES = [
    "cost",
    "coverage",
    "error",
    "g_values_over_time",
    "run_dir",
    "raw_memory",
    "runtime",
    "virtual_memory",
]

exp = Experiment(environment=ENVIRONMENT)
exp.add_step("build", exp.build)
exp.add_step("start", exp.start_runs)
exp.add_step("parse", exp.parse)
exp.add_fetcher(name="fetch")
exp.add_parser(get_parser())


def get_image(name):
    planner = name.replace("-", "_")
    image = IMAGES_DIR / (name + ".img")
    assert image.is_file(), image
    return planner, image


IMAGES = [get_image("fd1906-lama-first")]

for planner, image in IMAGES:
    exp.add_resource(planner, image, symlink=True)

exp.add_resource("run_singularity", DIR / "run-singularity.sh")
exp.add_resource("filter_stderr", DIR / "filter-stderr.py")

for planner, _ in IMAGES:
    for task in suites.build_suite(BENCHMARKS_DIR, SUITE):
        run = exp.add_run()
        run.add_resource("domain", task.domain_file, "domain.pddl")
        run.add_resource("problem", task.problem_file, "problem.pddl")
        # Use runsolver to limit time and memory. It must be on the system
        # PATH. Important: we cannot use time_limit and memory_limit of
        # Lab's add_command() because setting the same memory limit with
        # runsolver again using setrlimit fails.
        run.add_command(
            "run-planner",
            [
                "runsolver",
                "--cpu-limit",
                TIME_LIMIT,
                "--rss-swap-limit",
                MEMORY_LIMIT,
                "--watcher-data",
                "watch.log",
                "--var",
                "values.log",
                "{run_singularity}",
                f"{{{planner}}}",
                "{domain}",
                "{problem}",
                "sas_plan",
            ],
        )
        # Remove temporary files from old Fast Downward versions.
        run.add_command("rm-tmp-files", ["rm", "-f", "output.sas", "output"])
        run.add_command("filter-stderr", [sys.executable, "{filter_stderr}"])

        run.set_property("domain", task.domain)
        run.set_property("problem", task.problem)
        run.set_property("algorithm", planner)
        run.set_property("id", [planner, task.domain, task.problem])

report = Path(exp.eval_dir) / f"{exp.name}.html"
exp.add_report(BaseReport(attributes=ATTRIBUTES), outfile=report)

exp.run_steps()
