News
====

v1.1
----

lab
^^^
* Add filter shortcuts: ``filter_config_nick=['lama', 'hcea'], filter_domain=['depot']`` (see :py:class:`Report <lab.reports.Report>`) (Florian)
* Ability to use more than one filter function (Florian)
* Pass an optional filter to :py:class:`Fetcher <lab.fetcher.Fetcher>` to fetch only a subset of results (Florian)
* Better handling of timeouts and memory-outs (Florian)
* Try to guess error reason when run was killed because of resource limits (Florian)
* Do not abort after failed commands by default
* Grid: When --all is passed only run all steps if none are supplied
* Environments: Support Uni Basel maia cluster (Malte)
* Add "pi" example
* Add example showing how to parse custom attributes
* Do not add resources and files again if they are already added to the experiment
* Abort if no runs have been added to the experiment
* Round all float values for the tables
* Add function :py:func:`lab.tools.sendmail` for sending e-mails
* Many bugfixes
* Added more tests
* Improved documentation

downward
^^^^^^^^
* Make the files output.sas, domain.pddl and problem.pddl optional for search experiments
* Use more compact table of contents for AbsoluteReports
* Use named anchors in AbsoluteReport (``report.html#expansions``, ``report.html#expansions-gripper``)
* Add colored absolute tables (see :py:class:`AbsoluteReport <downward.reports.absolute.AbsoluteReport>`)
* Do not add summary functions in problem-wise reports
* New report class :py:class:`ProblemPlotReport <downward.reports.plot.ProblemPlotReport>`
* Save more properties about experiments in the experiments's properties file for easy lookup (suite, configs, portfolios, etc.)
* Use separate table for each domain in problem-wise reports
* Sort table columns based on given config filters if given (Florian)
* Do not add VAL source files to experiment
* Parse number of reopened states
* Remove temporary downward files even if downward was killed
* Divide scatter-plot points into categories and lable them (see :py:class:`ScatterPlotReport <downward.reports.scatter.ScatterPlotReport>`) (Florian)
* Only add a highlighting and summary functions for numeric attributes in AbsoluteReports
* Compile validator if it isn't compiled already
* Downward suites: Allow writing SUITE_NAME_FIRST to run the first instance of all domains in SUITE_NAME
* LocalEnvironment: If ``processes`` is given, use as many jobs to compile the planner in parallel
* Check python version before creating preprocess experiment
* Add avg, min, max and stddev rows to relative reports
* Add RelativeReport
* Add :py:func:`DownwardExperiment.set_path_to_python() <downward.experiment.DownwardExperiment.set_path_to_python>`
* Many bugfixes
* Improved documentation
