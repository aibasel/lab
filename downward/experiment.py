"""
A module for running Fast Downward experiments.
"""

from collections import defaultdict, OrderedDict
import logging
import os.path

from downward import suites
from downward.cached_revision import CachedFastDownwardRevision
from lab import tools
from lab.experiment import Experiment, get_default_data_dir, Run


DIR = os.path.dirname(os.path.abspath(__file__))
DOWNWARD_SCRIPTS_DIR = os.path.join(DIR, "scripts")


def _get_solver_resource_name(cached_rev):
    return "fast_downward_" + cached_rev.name


class FastDownwardRun(Run):
    def __init__(self, exp, algo, task):
        Run.__init__(self, exp)
        self.algo = algo
        self.task = task

        self.driver_options = algo.driver_options[:]

        if self.task.domain_file is None:
            self.add_resource("task", self.task.problem_file, "task.sas", symlink=True)
            input_files = ["{task}"]
            # Without PDDL input files, we can't validate the solution.
            self.driver_options.remove("--validate")
        else:
            self.add_resource(
                "domain", self.task.domain_file, "domain.pddl", symlink=True
            )
            self.add_resource(
                "problem", self.task.problem_file, "problem.pddl", symlink=True
            )
            input_files = ["{domain}", "{problem}"]

        self.add_command(
            "planner",
            [tools.get_python_executable()]
            + ["{" + _get_solver_resource_name(algo.cached_revision) + "}"]
            + self.driver_options
            + input_files
            + algo.component_options,
        )

        self._set_properties()

    def _set_properties(self):
        self.set_property("algorithm", self.algo.name)
        self.set_property("repo", self.algo.cached_revision.repo)
        self.set_property("local_revision", self.algo.cached_revision.local_rev)
        self.set_property("global_revision", self.algo.cached_revision.global_rev)
        self.set_property("build_options", self.algo.cached_revision.build_options)
        self.set_property("driver_options", self.driver_options)
        self.set_property("component_options", self.algo.component_options)

        for key, value in self.task.properties.items():
            self.set_property(key, value)

        self.set_property("experiment_name", self.experiment.name)

        self.set_property("id", [self.algo.name, self.task.domain, self.task.problem])


class _DownwardAlgorithm:
    def __init__(self, name, cached_revision, driver_options, component_options):
        self.name = name
        self.cached_revision = cached_revision
        self.driver_options = driver_options
        self.component_options = component_options

    def __eq__(self, other):
        """Return true iff all components (excluding the name) match."""
        return (
            self.cached_revision == other.cached_revision
            and self.driver_options == other.driver_options
            and self.component_options == other.component_options
        )


class FastDownwardExperiment(Experiment):
    """Conduct a Fast Downward experiment.

    The most important methods for customizing an experiment are
    :meth:`.add_algorithm`, :meth:`.add_suite`, :meth:`.add_parser`,
    :meth:`.add_step` and :meth:`.add_report`.

    .. note::

        To build the experiment, execute its runs and fetch the results,
        add the following steps:

        >>> exp = FastDownwardExperiment()
        >>> exp.add_step("build", exp.build)
        >>> exp.add_step("start", exp.start_runs)
        >>> exp.add_fetcher(name="fetch")

    """

    # Built-in parsers that can be passed to exp.add_parser().

    #: Parsed attributes: "error", "planner_exit_code", "unsolvable".
    EXITCODE_PARSER = os.path.join(DOWNWARD_SCRIPTS_DIR, "exitcode-parser.py")

    #: Parsed attributes: "translator_peak_memory", "translator_time_done", etc.
    TRANSLATOR_PARSER = os.path.join(DOWNWARD_SCRIPTS_DIR, "translator-parser.py")

    #: Parsed attributes: "coverage", "memory", "total_time", etc.
    SINGLE_SEARCH_PARSER = os.path.join(DOWNWARD_SCRIPTS_DIR, "single-search-parser.py")

    #: Parsed attributes: "cost", "cost:all", "coverage".
    ANYTIME_SEARCH_PARSER = os.path.join(
        DOWNWARD_SCRIPTS_DIR, "anytime-search-parser.py"
    )

    #: Used attributes: "memory", "total_time",
    #: "translator_peak_memory", "translator_time_done".
    #:
    #: Parsed attributes: "node", "planner_memory", "planner_time",
    #: "planner_wall_clock_time", "score_planner_memory", "score_planner_time".
    PLANNER_PARSER = os.path.join(DOWNWARD_SCRIPTS_DIR, "planner-parser.py")

    def __init__(self, path=None, environment=None, revision_cache=None):
        """
        See :class:`lab.experiment.Experiment` for an explanation of
        the *path* and *environment* parameters.

        *revision_cache* is the directory for caching Fast Downward
        revisions. It defaults to ``<scriptdir>/data/revision-cache``.
        This directory can become very large since each revision uses
        about 30 MB.

        >>> from lab.environments import BaselSlurmEnvironment
        >>> env = BaselSlurmEnvironment(email="my.name@unibas.ch")
        >>> exp = FastDownwardExperiment(environment=env)

        You can add parsers with :meth:`.add_parser()`. See
        :ref:`parsing` for how to write custom parsers and
        :ref:`downward-parsers` for the list of built-in parsers. Which
        parsers you should use depends on the algorithms you're running.
        For single-search experiments, we recommend adding the following
        parsers in this order:

        >>> exp.add_parser(exp.EXITCODE_PARSER)
        >>> exp.add_parser(exp.TRANSLATOR_PARSER)
        >>> exp.add_parser(exp.SINGLE_SEARCH_PARSER)
        >>> exp.add_parser(exp.PLANNER_PARSER)

        """
        Experiment.__init__(self, path=path, environment=environment)

        self.revision_cache = revision_cache or os.path.join(
            get_default_data_dir(), "revision-cache"
        )

        self._suites = defaultdict(list)

        # Use OrderedDict to ensure that names are unique and ordered.
        self._algorithms = OrderedDict()

    def _get_tasks(self):
        tasks = []
        for benchmarks_dir, suite in self._suites.items():
            tasks.extend(suites.build_suite(benchmarks_dir, suite))
        return tasks

    def add_suite(self, benchmarks_dir, suite):
        """Add PDDL or SAS+ benchmarks to the experiment.

        *benchmarks_dir* must be a path to a benchmark directory. It must
        contain domain directories, which in turn hold PDDL or SAS+ files
        (ending with ".pddl" or ".sas").

        *suite* must be a list of domain or domain:task names. ::

            >>> benchmarks_dir = os.environ["DOWNWARD_BENCHMARKS"]
            >>> exp = FastDownwardExperiment()
            >>> exp.add_suite(benchmarks_dir, ["depot", "gripper"])
            >>> exp.add_suite(benchmarks_dir, ["gripper:prob01.pddl"])
            >>> exp.add_suite(benchmarks_dir, ["rubiks-cube:p01.sas"])

        One source for benchmarks is
        https://github.com/aibasel/downward-benchmarks. After cloning the repo,
        you can generate suites with the ``suites.py`` script. We recommend
        using the suite ``optimal_strips`` for optimal STRIPS planners and
        ``satisficing`` for satisficing planners::

            # Create standard optimal planning suite. $
            path/to/downward-benchmarks/suites.py optimal_strips ['airport',
            ..., 'zenotravel']

        Then you can copy the generated list into your experiment script::

            >>> exp.add_suite(benchmarks_dir, ["airport", "zenotravel"])

        """
        if isinstance(suite, str):
            suite = [suite]
        benchmarks_dir = os.path.abspath(benchmarks_dir)
        if not os.path.exists(benchmarks_dir):
            logging.critical(f"Benchmarks directory {benchmarks_dir} not found.")
        self._suites[benchmarks_dir].extend(suite)

    def add_algorithm(
        self,
        name,
        repo,
        rev,
        component_options,
        build_options=None,
        driver_options=None,
    ):
        """
        Add a Fast Downward algorithm to the experiment, i.e., a
        planner configuration in a given repository at a given
        revision.

        *name* is a string describing the algorithm (e.g.
        ``"issue123-lmcut"``).

        *repo* must be a path to a Fast Downward repository.

        *rev* must be a valid revision in the given repository (e.g.,
        ``"e9c2370e6"``, ``"my-branch"``, ``"issue123"``).

        *component_options* must be a list of strings. By default these
        options are passed to the search component. Use
        ``"--translate-options"``, ``"--preprocess-options"`` or
        ``"--search-options"`` within the component options to override
        the default for the following options, until overridden again.

        If given, *build_options* must be a list of strings. They will be
        passed to the ``build.py`` script. Options can be build names
        (e.g., ``"releasenolp"``), ``build.py`` options (e.g.,
        ``"--debug"``) or options for Make. If *build_options* is omitted,
        the ``"release"`` version is built.

        If given, *driver_options* must be a list of strings. They will be
        passed to the ``fast-downward.py`` script. See ``fast-downward.py
        --help`` for available options. The list is always prepended with
        ``["--validate", "--overall-time-limit", "30m",
        "--overall-memory-limit', "3584M"]``. Specifying custom limits
        overrides the default limits.

        Example experiment setup:

        >>> import os
        >>> exp = FastDownwardExperiment()
        >>> repo = os.environ["DOWNWARD_REPO"]
        >>> rev = "main"

        Run iPDB using the latest revision on the main branch:

        >>> exp.add_algorithm("ipdb", repo, rev, ["--search", "astar(ipdb())"])

        Run blind search in debug mode:

        >>> exp.add_algorithm(
        ...     "blind",
        ...     repo,
        ...     rev,
        ...     ["--search", "astar(blind())"],
        ...     build_options=["--debug"],
        ...     driver_options=["--debug"],
        ... )

        Run LAMA-2011 with custom planner time limit:

        >>> exp.add_algorithm(
        ...     "lama",
        ...     repo,
        ...     rev,
        ...     [],
        ...     driver_options=[
        ...         "--alias",
        ...         "seq-saq-lama-2011",
        ...         "--overall-time-limit",
        ...         "5m",
        ...     ],
        ... )

        """
        if not isinstance(name, str):
            logging.critical(f"Algorithm name must be a string: {name}")
        if name in self._algorithms:
            logging.critical(f"Algorithm names must be unique: {name}")
        build_options = build_options or []
        driver_options = [
            "--validate",
            "--overall-time-limit",
            "30m",
            "--overall-memory-limit",
            "3584M",
        ] + (driver_options or [])
        algorithm = _DownwardAlgorithm(
            name,
            CachedFastDownwardRevision(repo, rev, build_options),
            driver_options,
            component_options,
        )
        for algo in self._algorithms.values():
            if algorithm == algo:
                logging.critical(
                    f"Algorithms {algo.name} and {algorithm.name} are identical."
                )
        self._algorithms[name] = algorithm

    def build(self, **kwargs):
        """Add Fast Downward code, runs and write everything to disk.

        This method is called by the second experiment step.

        """
        if not self._algorithms:
            logging.critical("You must add at least one algorithm.")

        # We convert the problems in suites to strings to avoid errors when converting
        # properties to JSON later. The clean but more complex solution would be to add
        # a method to the JSONEncoder that recognizes and correctly serializes the class
        # Problem.
        serialized_suites = {
            benchmarks_dir: [str(problem) for problem in benchmarks]
            for benchmarks_dir, benchmarks in self._suites.items()
        }
        self.set_property("suite", serialized_suites)
        self.set_property("algorithms", list(self._algorithms.keys()))

        self._cache_revisions()
        self._add_code()
        self._add_runs()

        Experiment.build(self, **kwargs)

    def _get_unique_cached_revisions(self):
        unique_cached_revs = set()
        for algo in self._algorithms.values():
            unique_cached_revs.add(algo.cached_revision)
        return unique_cached_revs

    def _cache_revisions(self):
        for cached_rev in self._get_unique_cached_revisions():
            cached_rev.cache(self.revision_cache)

    def _add_code(self):
        """Add the compiled code to the experiment."""
        for cached_rev in self._get_unique_cached_revisions():
            cache_path = os.path.join(self.revision_cache, cached_rev.name)
            dest_path = "code-" + cached_rev.name
            self.add_resource("", cache_path, dest_path)
            # Overwrite the script to set an environment variable.
            self.add_resource(
                _get_solver_resource_name(cached_rev),
                os.path.join(cache_path, "fast-downward.py"),
                os.path.join(dest_path, "fast-downward.py"),
            )

    def _add_runs(self):
        tasks = self._get_tasks()
        for algo in self._algorithms.values():
            for task in tasks:
                self.add_run(FastDownwardRun(self, algo, task))
