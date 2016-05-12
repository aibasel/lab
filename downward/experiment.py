# -*- coding: utf-8 -*-
#
# downward uses the lab package to conduct experiments with the
# Fast Downward planning system.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
A module for running Fast Downward experiments.
"""

from collections import defaultdict, OrderedDict
import logging
import multiprocessing
import os.path

from lab.experiment import Run, Experiment, get_default_data_dir

from downward.cached_revision import CachedRevision
from downward import suites


DIR = os.path.dirname(os.path.abspath(__file__))
DOWNWARD_SCRIPTS_DIR = os.path.join(DIR, 'scripts')


class FastDownwardRun(Run):
    def __init__(self, exp, algo, task):
        Run.__init__(self, exp)
        self.algo = algo
        self.task = task

        self._set_properties()

        # Linking to instead of copying the PDDL files makes building
        # the experiment twice as fast.
        self.add_resource(
            'DOMAIN', self.task.domain_file(), 'domain.pddl', symlink=True)
        self.add_resource(
            'PROBLEM', self.task.problem_file(), 'problem.pddl', symlink=True)

        self.add_command(
            'fast-downward',
            [algo.cached_revision.get_planner_resource_name()] +
            algo.driver_options + ['DOMAIN', 'PROBLEM'] + algo.component_options)

        self.add_command('parse-preprocess', ['PREPROCESS_PARSER'])
        self.add_command('parse-search', ['SEARCH_PARSER'])

        self.add_command(
            'compress-output-files', ['xz', 'output.sas', 'output'])

    def _set_properties(self):
        self.set_property('algorithm', self.algo.name)
        self.set_property('repo', self.algo.cached_revision.repo)
        self.set_property('local_revision', self.algo.cached_revision.local_rev)
        self.set_property('global_revision', self.algo.cached_revision.global_rev)
        self.set_property('revision_summary', self.algo.cached_revision.summary)
        self.set_property('build_options', self.algo.cached_revision.build_options)
        self.set_property('driver_options', self.algo.driver_options)
        self.set_property('component_options', self.algo.component_options)

        self.set_property('domain', self.task.domain)
        self.set_property('problem', self.task.problem)

        self.set_property('experiment_name', self.experiment.name)

        # TODO: Remove planner_type property. Let portfolios output token instead.
        self.set_property(
            'planner_type', 'portfolio' if self._is_portfolio() else 'single')

        self.set_property('id', [self.algo.name, self.task.domain, self.task.problem])

    def _is_portfolio(self):
        built_in = [
            'seq-opt-fdss-1', 'seq-opt-fdss-2', 'seq-opt-merge-and-shrink'
            'seq-sat-fdss-1', 'seq-sat-fdss-2']
        return any(x in self.algo.driver_options for x in built_in + ['--portfolio'])


class _DownwardAlgorithm(object):
    def __init__(self, name, cached_revision, driver_options, component_options):
        self.name = name
        self.cached_revision = cached_revision
        self.driver_options = driver_options
        self.component_options = component_options


class FastDownwardExperiment(Experiment):
    """Conduct a Fast Downward experiment.

    You can customize an experiment by adding the desired algorithms,
    benchmarks and reports.

    Fast Downward experiments consist of the following steps:

    * Step 1: write experiment files to disk
    * Step 2: run experiment
    * Step 3: fetch results and save them in ``<path>-eval``

    You can add report steps with :meth:`.add_report`.

    """

    DEFAULT_SEARCH_TIME_LIMIT = "30m"
    DEFAULT_SEARCH_MEMORY_LIMIT = "2G"

    def __init__(self, path=None, environment=None, revision_cache=None):
        """
        See :class:`lab.experiment.Experiment` for an explanation of
        the *path* and *environment* parameters.

        *revision_cache* is the directory for caching Fast Downward
        revisions. It defaults to ``<scriptdir>/data/revision-cache``.
        This directory can become very large since each revision uses
        about 30 MB.

        >>> from lab.environments import MaiaEnvironment
        >>> env = MaiaEnvironment(priority=-2)
        >>> exp = FastDownwardExperiment(environment=env)

        """
        Experiment.__init__(self, path=path, environment=environment)

        self.revision_cache = revision_cache or os.path.join(
            get_default_data_dir(), 'revision-cache')

        self._suites = defaultdict(list)

        # Use OrderedDict to ensure that names are unique and ordered.
        self._algorithms = OrderedDict()

    def _get_tasks(self):
        tasks = []
        for benchmarks_dir, suite in self._suites.items():
            tasks.extend(suites.build_suite(benchmarks_dir, suite))
        return tasks

    def add_suite(self, benchmarks_dir, suite):
        """Add benchmarks to the experiment.

        *benchmarks_dir* must be a path to a benchmark directory. It
        must contain domain directories, which in turn hold PDDL files.

        *suite* must be a list of domain or domain:task names.

        >>> repo = os.path.expanduser('~/projects/Downward/downward')
        >>> benchmarks_dir = os.path.join(repo, "benchmarks")
        >>> exp = FastDownwardExperiment()
        >>> exp.add_suite(benchmarks_dir, ["gripper:prob01.pddl"])
        >>> exp.add_suite(benchmarks_dir, ["gripper"])
        >>> exp.add_suite(
        ...     benchmarks_dir,
        ...     ["miconic", "trucks", "grid", "gripper:prob01.pddl"])

        """
        if isinstance(suite, basestring):
            suite = [suite]
        benchmarks_dir = os.path.abspath(benchmarks_dir)
        if not os.path.exists(benchmarks_dir):
            logging.critical(
                'Benchmarks directory {} not found.'.format(benchmarks_dir))
        self._suites[benchmarks_dir].extend(suite)

    def add_algorithm(self, name, repo, rev, component_options,
                      build_options=None, driver_options=None):
        """
        Add a Fast Downward algorithm to the experiment, i.e., a
        planner configuration in a given repository at a given
        revision.

        *name* is a string describing the algorithm (e.g.
        ``"issue123-lmcut"``).

        *repo* must be a path to a Fast Downward repository.

        *rev* must be a valid revision in the given repository (e.g.,
        ``"default"``, ``"tip"``, ``"issue123"``).

        *component_options* must be a list of strings. By default these
        options are passed to the search component. Use
        ``"--translate-options"``, ``"--preprocess-options"`` or
        ``"--search-options"`` within the component options to override
        the default for the following options, until overridden again.

        If given, *build_options* must be a list of strings. They will
        be passed to the ``build.py`` script. Options can be build
        names (e.g., ``"release32"``, ``"debug64"``), ``build.py``
        options (e.g., ``"--debug"``) or options for Make. The list is
        always prepended with ``["-j<num_cpus>"]``. This setting can be
        overriden, e.g., ``driver_options=["-j1"]`` builds the planner
        using a single CPU. If *build_options* is omitted, the
        ``"release32"`` version is built using all CPUs.

        If given, *driver_options* must be a list of strings. They will
        be passed to the ``fast-downward.py`` script. See
        ``fast-downward.py --help`` for available options. The list is
        always prepended with ``["--validate", "--search-time-limit",
        "30m", "--search-memory-limit', "2G"]``. Specifying custom
        limits will override the default limits.

        Example experiment setup:

        >>> import os.path
        >>> exp = FastDownwardExperiment()
        >>> repo = os.path.expanduser("~/projects/Downward/downward")

        Test iPDB in the latest revision on the default branch:

        >>> exp.add_algorithm(
        ...     "ipdb", repo, "default",
        ...     ["--search", "astar(ipdb())"])

        Test LM-Cut in an issue experiment:

        >>> exp.add_algorithm(
        ...     "issue123-v1-lmcut", repo, "issue123-v1",
        ...     ["--search", "astar(lmcut())"])

        Run blind search in debug mode:

        >>> exp.add_algorithm(
        ...     "blind", repo, "default",
        ...     ["--search", "astar(blind())"],
        ...     build_options=["--debug"],
        ...     driver_options=["--debug"])

        Run LAMA-2011 with custom search time limit:

        >>> exp.add_algorithm(
        ...     "lama", repo, "default",
        ...     [],
        ...     driver_options=[
        ...         "--alias", "seq-saq-lama-2011",
        ...         "--search-time-limit", "5m"])

        """
        if not isinstance(name, basestring):
            logging.critical('Algorithm name must be a string: {}'.format(name))
        if name in self._algorithms:
            logging.critical('Algorithm names must be unique: {}'.format(name))
        build_options = self._get_default_build_options() + (build_options or [])
        driver_options = ([
            '--validate',
            '--search-time-limit', self.DEFAULT_SEARCH_TIME_LIMIT,
            '--search-memory-limit', self.DEFAULT_SEARCH_MEMORY_LIMIT] +
            (driver_options or []))
        self._algorithms[name] = _DownwardAlgorithm(
            name, CachedRevision(repo, rev, build_options),
            driver_options, component_options)

    def build(self, **kwargs):
        """Add Fast Downward code, runs and write everything to disk.

        This method is called by the second experiment step.

        """
        if not self._algorithms:
            logging.critical('You must add at least one algorithm.')

        self.set_property('suite', self._suites)
        self.set_property('algorithms', self._algorithms.keys())

        self._cache_revisions()
        self._add_code()
        self._add_runs()

        Experiment.build(self, **kwargs)

    def _get_unique_cached_revisions(self):
        unique_cached_revs = set()
        for algo in self._algorithms.values():
            unique_cached_revs.add(algo.cached_revision)
        return unique_cached_revs

    def _get_default_build_options(self):
        cores = multiprocessing.cpu_count()
        return ['-j{}'.format(cores)]

    def _cache_revisions(self):
        for cached_rev in self._get_unique_cached_revisions():
            cached_rev.cache(self.revision_cache)

    def _add_code(self):
        """Add the compiled code to the experiment."""
        self.add_resource(
            'PREPROCESS_PARSER',
            os.path.join(DOWNWARD_SCRIPTS_DIR, 'preprocess_parser.py'))
        self.add_resource(
            'SEARCH_PARSER',
            os.path.join(DOWNWARD_SCRIPTS_DIR, 'search_parser.py'))

        for cached_rev in self._get_unique_cached_revisions():
            self.add_resource(
                '',
                cached_rev.get_cached_path(),
                cached_rev.get_exp_path())
            # Overwrite the script to set an environment variable.
            self.add_resource(
                cached_rev.get_planner_resource_name(),
                cached_rev.get_cached_path('fast-downward.py'),
                cached_rev.get_exp_path('fast-downward.py'))

    def _add_runs(self):
        for algo in self._algorithms.values():
            for task in self._get_tasks():
                self.add_run(FastDownwardRun(self, algo, task))
