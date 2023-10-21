.. _concepts:

Concepts
========

An **experiment** consists of multiple **steps**. Most experiments will
have steps for building and executing the experiment, and parsing logs:

    >>> from lab.experiment import Experiment
    >>> exp = Experiment()
    >>> exp.add_step("build", exp.build)
    >>> exp.add_step("start", exp.start_runs)
    >>> exp.add_step("parse", exp.parse)

Moreover, there are usually steps for **fetching** the results and making
**reports**:

>>> from lab.reports import Report
>>> exp.add_fetcher(name="fetch")
>>> exp.add_report(Report(attributes=["error"]))

The "build" step creates all necessary files for running the experiment in the
**experiment directory**. After the "start" step has finished running the
experiment, we can parse data from logs and generated files into "properties"
files, and then fetch all properties files from the experiment directory to the
**evaluation directory**. All reports only operate on evaluation directories.

An experiment usually also has multiple **runs**, one for each pair of
algorithm and benchmark.

When calling :meth:`.start_runs`, all **runs** part of the
experiment are executed. You can add runs with the :meth:`.add_run`
method. Each run needs a unique ID and at least one **command**:

>>> for algo in ["algo1", "algo2"]:
...     for value in range(10):
...         run = exp.add_run()
...         run.set_property("id", [algo, str(value)])
...         run.add_command("solve", [algo, str(value)])

You can pass the names of selected steps to your experiment script
or use ``--all`` to execute all steps. At the end of your script,
call ``exp.run_steps()`` to parse the commandline and execute the
selected steps.
