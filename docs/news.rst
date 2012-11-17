News
====

v1.2
----

lab
^^^
* Fetcher: Only copy the link not the content for symbolic links.
* Make properties files more compact by using an indent of 2 instead of 4.
* Nicer format for commandline help for experiments.
* Reports: Only print available attributes if none have been set.
* Fetcher: Pass custom parsers to fetcher to parse values from a finished experiment.
* For geometric mean calculation substitute 0.1 for values <= 0.
* Only show warning if not all attributes for the report are found in the evaluation dir,
  don't abort if at least one attribute is found.
* If an attribute is None for all runs, do not conclude it is not numeric.
* Abort if experiment path contains a colon.
* Abort with warning if all runs have been filtered for a report.
* Reports: Allow specifying a *single* attribute as a string instead of
  a list of one string (e.g. attributes='coverage').

downward
^^^^^^^^
* If compact=True for a DownwardExperiment, link to the benchmarks instead of copying them.
* Do not call ./build-all script, but build components only if needed.
* Fetch and compile sources only when needed: Only prepare translator and
  preprocessor for preprocessing experiments and only prepare planners for
  search experiments. Do it in a grid job if possible.
* Save space by deleting the benchmarks directories and omitting the search
  directory and validator for preprocess experiments.
* Only support using 'src' directory, not the old 'downward' dir.
* Use downward script regardless of other binaries found in the search directory.
* Do not try to set parent-revision property. It cannot be determined without
  fetching the code first.
* Make ProblemPlotReport class more general by allowing the get_points() method
  to return an arbitrary number of points and categories.
* Specify xscale and yscale (linear, log, symlog) in PlotReports.
* Fix removing downward.tmp.* files (use bash for globbing). This greatly reduces
  the needed space for an experiment.
* Label axes in ProblemPlots with ``xlabel`` and ``ylabel``.
* If a grid environment is selected, use all CPUs for compiling Fast Downward.
* Do not use the same plot style again if it has already been assigned by the user.
* Only write plot if valid points have been added.
* DownwardExperiment: Add member ``include_preprocess_results_in_search_runs``.
* Colored reports: If all configs have the same value in a row and some are None,
  highlight the values in green instead of making them grey.
* Never set 'error' to 'none' if 'search_error' is true.
* PlotReport: Add ``legend_location`` parameter.
* Plots: Sort coordinates by x-value for correct connections between points.
* Plots: Filter duplicate coordinates for nicer drawing.
* Use less padding for linear scatterplots.
* Scatterplots: Add ``show_missing`` parameter.
* Absolute reports: For absolute attributes (like coverage and search_error)
  print a list of numbers of problems behind the domain name if not all configs
  have a value for the same number of problems.
* Make 'unsolvable' an absolute attribute, i.e. one where we consider problem
  runs for which not all configs have a value.
* If a non-numeric attribute is present in a domain-wise report, state its type
  in the error message.
* Let plots use the ``format`` parameter given in constructor.
* Allow generation of pgf plot files (only available in matplotlib 1.2).
* Allow generation of pdf and eps plots.
* DownwardReport: Allow passing a single function for ``derived_properties``.
* Plots: Remove code that sets parameters explicitly, sort items in legend.
* Add parameters to PlotReport that set the axes' limits.
* Add more items to downward FAQ.


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
