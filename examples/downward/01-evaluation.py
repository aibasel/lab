#! /usr/bin/env python

from pathlib import Path

import project

from lab.experiment import Experiment

ATTRIBUTES = [
    "error",
    "run_dir",
    "planner_time",
    "initial_h_value",
    "coverage",
    "cost",
    "evaluations",
    "memory",
    project.EVALUATIONS_PER_TIME,
]

exp = Experiment()
exp.add_step(
    "remove-combined-properties", project.remove_file, Path(exp.eval_dir) / "properties"
)

project.fetch_algorithm(exp, "2020-09-11-A-cg-vs-ff", "01-cg", new_algo="cg")
project.fetch_algorithms(exp, "2020-09-11-B-bounded-cost")

filters = [project.add_evaluations_per_time]

project.add_absolute_report(
    exp, attributes=ATTRIBUTES, filter=filters, name=f"{exp.name}"
)


exp.run_steps()
