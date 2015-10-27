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

from collections import defaultdict
import logging
import multiprocessing
import os.path

from lab.experiment import Run, Experiment
from lab import tools

from downward.cached_revision import CachedRevision
from downward import suites


DIR = os.path.dirname(os.path.abspath(__file__))
DOWNWARD_SCRIPTS_DIR = os.path.join(os.path.dirname(DIR), 'scripts')


def _get_default_experiment_name():
    """Get default name for experiment.

    Derived from the filename of the main script, e.g.
    "ham/spam/eggs.py" => "eggs".
    """
    return os.path.splitext(os.path.basename(tools.get_script_path()))[0]


def _get_default_data_dir():
    """E.g. "ham/spam/eggs.py" => "ham/spam/data/"."""
    return os.path.join(tools.get_script_dir(), "data")


def _get_default_experiment_dir():
    """E.g. "ham/spam/eggs.py" => "ham/spam/data/eggs"."""
    return os.path.join(
        _get_default_data_dir(), _get_default_experiment_name())


class FastDownwardRun(Run):
    def __init__(self, exp, algo, task):
        Run.__init__(self, exp)
        self.algo = algo
        self.task = task

        self._set_properties()

        self.add_resource('DOMAIN', self.task.domain_file(), 'domain.pddl')
        self.add_resource('PROBLEM', self.task.problem_file(), 'problem.pddl')

        # TODO: After removing DownwardExperiment, use name "fast-downward".
        self.add_command(
            'search',
            ['FAST_DOWNWARD'] + algo.driver_options +
            ['DOMAIN', 'PROBLEM'] + algo.component_options)

        # TODO: Use exp.add_command() once it is available.
        self.add_command('parse-preprocess', ['PREPROCESS_PARSER'])
        self.add_command('parse-search', ['SEARCH_PARSER'])

        self.add_command(
            'compress-output-files',
            ['xz', 'domain.pddl', 'problem.pddl', 'output.sas', 'output'])

    def _set_properties(self):
        self.set_property('algorithm_nick', self.algo.nick)
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

        self.set_property('config', self.algo.nick)

        # TODO: Remove planner_type property. Let portfolios output token instead.
        self.set_property(
            'planner_type', 'portfolio' if self._is_portfolio() else 'single')

        self._save_id([
            self.algo.nick,
            self.task.domain,
            self.task.problem])

    def _save_id(self, run_id):
        self.set_property('id', run_id)
        self.set_property('id_string', ':'.join(run_id))

    def _is_portfolio(self):
        built_in = [
            'seq-opt-fdss-1', 'seq-opt-fdss-2', 'seq-opt-merge-and-shrink'
            'seq-sat-fdss-1', 'seq-sat-fdss-2']
        return any(x in self.algo.driver_options for x in built_in + ['--portfolio'])


class _DownwardAlgorithm(object):
    def __init__(self, nick, cached_revision, driver_options, component_options):
        self.nick = nick
        self.cached_revision = cached_revision
        self.driver_options = driver_options
        self.component_options = component_options


class FastDownwardExperiment(Experiment):
    """Conduct a Fast Downward experiment.

    Experiments can be customized by adding the desired
    configurations, benchmarks and reports. See
    :class:`lab.experiment.Experiment` for inherited methods.

    Fast Downward experiments consist of the following steps:

    * Step 1: write experiment files to disk
    * Step 2: run experiment
    * Step 3: fetch results and save them in ``<path>-eval``

    You can add report steps with :py:func:`add_report()
    <downward.experiment.FastDownwardExperiment.add_report>`.

    """

    DEFAULT_SEARCH_TIME_LIMIT = "30m"
    DEFAULT_SEARCH_MEMORY_LIMIT = "2G"

    def __init__(self, path=None, environment=None, cache_dir=None):
        """
        The experiment will be built at *path*. It defaults to
        ``<scriptdir>/data/<scriptname>/``. E.g. if your script is at
        ``experiments/myexp.py``, *path* will be
        ``experiments/data/myexp/``.

        *environment* must be an :ref:`Environment <environments>`
        instance. By default a :py:class:`LocalEnvironment
        <lab.environments.LocalEnvironment>` is used and the experiment
        is run locally.

        *cache_dir* is used to cache temporary data. It defaults to
        ``<scriptdir>/data/``. Compiled Fast Downward revisions are
        cached under ``<cache_dir>/revision-cache/``.

        Example::

            env = MaiaEnvironment(priority=-2)
            exp = FastDownwardExperiment(environment=env)

        """
        path = path or _get_default_experiment_dir()
        cache_dir = cache_dir or _get_default_data_dir()
        Experiment.__init__(self, path, environment=environment, cache_dir=cache_dir)
        self.revision_cache_dir = os.path.join(self.cache_dir, 'revision-cache')

        self._suites = defaultdict(list)

        # Use OrderedDict to ensure that nicks are unique and ordered.
        self._algorithms = tools.OrderedDict()

    def _get_tasks(self):
        tasks = []
        for benchmarks_dir, suite in self._suites.items():
            tasks.extend(suites.build_suite(benchmarks_dir, suite))
        return tasks

    def add_suite(self, benchmarks_dir, suite):
        """Add benchmarks to the experiment.

        *benchmarks_dir* must be a path to a benchmark directory. It
        must contain domain directories, which in turn hold PDDL files.

        *suite* can either be a string or a list of strings. The
        strings can be tasks or domains. ::

            benchmarks_dir = os.path.join(myrepo, "benchmarks")
            exp.add_suite("gripper:prob01.pddl", benchmarks_dir)
            exp.add_suite("gripper", benchmarks_dir)
            exp.add_suite(
                ["miconic", "trucks", "grid", "gripper:prob01.pddl"],
                benchmarks_dir)

        There are some predefined suites in ``suites.py``. ::

            exp.add_suite(suites.suite_strips(), benchmarks_dir)
            exp.add_suite(suites.suite_ipc_all(), benchmarks_dir)

        """
        if isinstance(suite, basestring):
            suite = [suite]
        benchmarks_dir = os.path.abspath(benchmarks_dir)
        if not os.path.exists(benchmarks_dir):
            logging.critical(
                'Benchmarks directory {} not found.'.format(benchmarks_dir))
        self._suites[benchmarks_dir].extend(suite)

    def add_algorithm(self, nick, repo, rev, component_options,
                      build_options=None, driver_options=None):
        """
        Add a Fast Downward algorithm to the experiment, i.e., a
        planner configuration in a given repository at a given
        revision.

        *nick* is a string describing the algorithm (e.g.
        "issue123-lmcut").

        *repo* must be a path to a Fast Downward repository.

        *rev* must be a valid revision in the given repository (e.g.
        "default", "tip", "issue123").

        *component_options* must be a list of strings. By default these
        options are passed to the search component. Use
        "--translate-options", "--preprocess-options" or
        "--search-options" within the component options to override the
        default for the following options, until overridden again.

        If given, *build_options* must be a list of strings. They will
        be passed to the ``build.py`` script. Options can be build
        names (e.g. "release32", "debug64") or options for Make. The
        default is ``["-j<num_cpus>"]``. This setting causes
        ``build.py`` to build "release32" with all CPUs.

        If given, *driver_options* must be a list of strings. They will
        be passed to the ``fast-downward.py`` script. See
        ``fast-downward.py --help`` for available options. The default
        is ``["--search-time-limit", "30m", "--search-memory-limit',
        "2G"]``.

        Examples::

            # Test iPDB in the latest revision on the default branch.
            exp.add_algorithm(
                "ipdb", "path/to/repo", "default",
                ["--search", "astar(ipdb())"])

            # Test LM-cut in an issue experiment.
            exp.add_algorithm(
                "issue123-v1-lmcut", "path/to/repo", "issue123-v1",
                ["--search", "astar(lmcut())"])

            # Run blind search in debug mode.
            exp.add_algorithm(
                "blind", "path/to/repo", "default",
                ["--search", "astar(blind())"],
                build_options=["debug32"],
                driver_options=["--build", "debug32"])

            # Run LAMA-2011 with custom search time limit.
            exp.add_algorithm(
                "lama", "path/to/repo", "default",
                [],
                driver_options=[
                    "--alias", "seq-saq-lama-2011",
                    "--search-time-limit", "5m"])

        """
        if not isinstance(nick, basestring):
            logging.critical('Config nick must be a string: %s' % nick)
        if nick in self._algorithms:
            logging.critical('Algorithm nicks must be unique: {}' % nick)
        build_options = build_options or self._get_default_build_options()
        driver_options = driver_options or [
            '--search-time-limit', self.DEFAULT_SEARCH_TIME_LIMIT,
            '--search-memory-limit', self.DEFAULT_SEARCH_MEMORY_LIMIT]
        self._algorithms[nick] = _DownwardAlgorithm(
            nick, CachedRevision(repo, rev, build_options),
            driver_options, component_options)

    def build(self, **kwargs):
        """Write the experiment to disk. Called internally by lab."""
        if not self._algorithms:
            logging.critical('You must add at least one algorithm.')

        self.set_property('suite', self._suites)
        self.set_property('algorithm_nicks', self._algorithms.keys())

        self._cache_revisions()
        self._add_code()
        self._add_runs()

        Experiment.build(self, **kwargs)

    def _get_default_build_options(self):
        cores = multiprocessing.cpu_count()
        return ['-j{}'.format(cores)]

    def _cache_revisions(self):
        for algo in self._algorithms.values():
            algo.cached_revision.cache(self.revision_cache_dir)

    def _add_code(self):
        """Add the compiled code to the experiment."""
        self.add_resource(
            'PREPROCESS_PARSER',
            os.path.join(DOWNWARD_SCRIPTS_DIR, 'preprocess_parser.py'))
        self.add_resource(
            'SEARCH_PARSER',
            os.path.join(DOWNWARD_SCRIPTS_DIR, 'search_parser.py'))
        for algo in self._algorithms.values():
            cached_rev = algo.cached_revision
            self.add_resource(
                '',
                cached_rev.get_cached_path(),
                cached_rev.get_exp_path())
            # Overwrite the script to set an environment variable.
            self.add_resource(
                'FAST_DOWNWARD',
                cached_rev.get_cached_path('fast-downward.py'),
                cached_rev.get_exp_path('fast-downward.py'))

    def _add_runs(self):
        for algo in self._algorithms.values():
            for task in self._get_tasks():
                self.add_run(FastDownwardRun(self, algo, task))
