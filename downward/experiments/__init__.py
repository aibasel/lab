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
A module for cloning different revisions of the three
components of Fast Downward (translate, preprocess, search) and performing
experiments with them.
"""
from collections import defaultdict
import logging
import multiprocessing
import os
import subprocess

from lab.experiment import Run, Experiment
from lab import tools
from lab.steps import Step, Sequence

from downward.checkouts import Checkout, Translator, Preprocessor, Planner
from downward import suites


DOWNWARD_SCRIPTS_DIR = os.path.abspath(os.path.join(__file__, '..', '..', 'scripts'))


# Limits can be overwritten in DownwardExperiment constructor.
LIMITS = {
    'translate_time': 7200,
    'translate_memory': 8192,
    'preprocess_time': 7200,
    'preprocess_memory': 8192,
    'search_time': 1800,
    'search_memory': 2048,
}


# Make the same check as in src/translate/translate.py.
VERSION_STMT = '''\
import sys

def python_version_supported():
    major, minor = sys.version_info[:2]
    return (major == 2 and minor >= 7) or (major, minor) >= (3, 2)

if not python_version_supported():
    sys.exit("Error: Translator only supports Python >= 2.7 and Python >= 3.2.")
'''

PRINT_PYTHON_VERSION = """\
import platform; print 'Python version: %s' % platform.python_version()"""


def _get_rev_nick(translator, preprocessor, planner):
    nicks = [part.nick for part in (translator, preprocessor, planner)]
    if len(set(nicks)) == 1:
        nicks = [nicks[0]]
    return '-'.join(nicks)


class DownwardRun(Run):
    def __init__(self, exp, parts, problem):
        Run.__init__(self, exp)

        self.parts = parts
        self.problem = problem

        self._set_properties()
        self._save_limits()

    def _set_properties(self):
        for part in self.parts:
            self.set_property(part.part + '_rev', part.rev)
            self.set_property(part.part + '_nick', part.nick)
            self.set_property(part.part + '_summary', part.summary)

        self.set_property('domain', self.problem.domain)
        self.set_property('problem', self.problem.problem)

        self.set_property('experiment_name', self.experiment.name)

    def _save_limits(self):
        for name, limit in self.experiment.limits.items():
            self.set_property('limit_' + name, limit)

    def _save_ext_config(self, ext_config):
        self.set_property('config', ext_config)

    def _save_id(self, run_id):
        self.set_property('id', run_id)
        self.set_property('id_string', ':'.join(run_id))

    def add_parsers(self, parsers):
        for parser_name, parser_path in parsers:
            self.require_resource(parser_name.upper())
            self.add_command('run-' + parser_name, [parser_name.upper()])


class PreprocessRun(DownwardRun):
    def __init__(self, exp, translator, preprocessor, problem):
        DownwardRun.__init__(self, exp, [translator, preprocessor], problem)

        self.require_resource(preprocessor.shell_name)

        self.add_resource('DOMAIN', self.problem.domain_file(), 'domain.pddl')
        self.add_resource('PROBLEM', self.problem.problem_file(), 'problem.pddl')

        python = exp._get_path_to_python()

        # Print python version used for translator.
        # python -V prints to stderr so we execute a little program.
        self.add_command('print-python-version',
                         [python, '-c', PRINT_PYTHON_VERSION])
        self.add_command('translate', [python, translator.shell_name,
                                       'DOMAIN', 'PROBLEM'],
                         time_limit=exp.limits['translate_time'],
                         mem_limit=exp.limits['translate_memory'])
        self.add_command('preprocess', [preprocessor.shell_name],
                         stdin='output.sas',
                         time_limit=exp.limits['preprocess_time'],
                         mem_limit=exp.limits['preprocess_memory'])
        self.add_command('parse-preprocess', ['PREPROCESS_PARSER'])

        if exp.compact:
            # Compress and delete output.sas.
            self.add_command('compress-output-sas', ['bzip2', 'output.sas'])

        self.set_property('stage', 'preprocess')
        self._save_ext_config('-'.join(part.nick for part in self.parts))
        # Use global revisions for ids to allow for correct cashing.
        self._save_id([
            '-'.join(part.rev for part in self.parts),
            self.problem.domain,
            self.problem.problem])


class SearchRun(DownwardRun):
    def __init__(self, exp, algo, problem):
        parts = [algo.translator, algo.preprocessor, algo.planner]
        DownwardRun.__init__(self, exp, parts, problem)

        self.require_resource(algo.planner.shell_name)

        self.add_command('search',
                         [algo.planner.shell_name] + algo.config,
                         stdin='OUTPUT',
                         time_limit=algo.timeout or exp.limits['search_time'],
                         mem_limit=exp.limits['search_memory'])

        # Remove temporary files (we need bash for globbing).
        self.add_command('rm-tmp-files', ['bash', '-c', 'rm -f downward.tmp.*'])

        # Validation
        self.require_resource('VALIDATE')
        self.require_resource('DOWNWARD_VALIDATE')
        self.add_command('validate', ['DOWNWARD_VALIDATE', 'VALIDATE', 'DOMAIN',
                                      'PROBLEM'])

        planner_type = 'portfolio' if self._is_portfolio(algo.config) else 'single'

        # Restore the config_nick by stripping combo_nick from
        # algo.nick and save it for backwards compatibility.
        combo_nick = _get_rev_nick(algo.translator, algo.preprocessor, algo.planner)
        if algo.nick.startswith(combo_nick + '-'):
            config_nick = algo.nick[len(combo_nick + '-'):]
        else:
            config_nick = algo.nick
        self.set_property('config_nick', config_nick)
        self.set_property('commandline_config', algo.config)
        self.set_property('planner_type', planner_type)
        self.set_property('stage', 'search')

        self._save_ext_config(algo.nick)
        self._save_id([algo.nick, self.problem.domain, self.problem.problem])

        if algo.timeout is not None:
            self.set_property('limit_search_time', algo.timeout)

    @classmethod
    def _is_portfolio(cls, config):
        built_in = ['seq-opt-fdss-1', 'seq-opt-fdss-2',
                    'seq-sat-fdss-1', 'seq-sat-fdss-2']
        return any(x in config for x in built_in + ['--portfolio'])


class _DownwardAlgorithm(object):
    def __init__(self, nick, config, translator, preprocessor, planner, timeout=None):
        self.nick = nick
        self.config = config
        self.translator = translator
        self.preprocessor = preprocessor
        self.planner = planner
        self.timeout = timeout


class DownwardExperiment(Experiment):
    """Conduct a Fast Downward experiment.

    This is the base class for Fast Downward experiments. It can be customized
    by adding the desired configurations, benchmarks and reports.
    See :py:class:`lab.experiment.Experiment` for inherited methods.

    .. note::

        You only have to run preprocessing experiments and fetch the results for
        each pair of translator and preprocessor revision once, since the results
        are cached. When you build a search experiment, the results are
        automatically taken from the cache. You can change the location of the
        cache by passing the *cache_dir* parameter.
    """
    def __init__(self, path, repo, environment=None, combinations=None,
                 compact=True, limits=None, cache_dir=None):
        """
        The experiment will be built at *path*.

        *repo* must be the path to a Fast Downward repository. Among other things
        this repository is used to search for benchmark files.

        *environment* must be an :ref:`Environment <environments>` instance.
        By default the experiment is run locally.

        If given, *combinations* must be a list of :ref:`Checkout <checkouts>`
        tuples of the form (Translator, Preprocessor, Planner). If combinations
        is None (default), perform an experiment with the working copy in *repo*.

        If *compact* is True, reference benchmarks and preprocessed files instead
        of copying them. Only use this option if the referenced files will **not**
        be changed during the experiment. Set *compact* to False if you want a
        portable experiment.

        If *limits* is given, it must be a dictionary which will be used to
        overwrite the default limits. ::

            default_limits = {
                'translate_time': 7200,
                'translate_memory': 8192,
                'preprocess_time': 7200,
                'preprocess_memory': 8192,
                'search_time': 1800,
                'search_memory': 2048,
            }

        *cache_dir* is used to cache Fast Downward clones and preprocessed
        tasks. By default it points to ``~/lab``.

        .. note::

            The directory *cache_dir* can grow very large (tens of GB).

        Example: ::

            repo = '/path/to/downward-repo'
            env = GkiGridEnvironment(queue='xeon_core.q', priority=-2)
            combos = [(Translator(repo, rev=123),
                       Preprocessor(repo, rev='e2a018c865f7'),
                       Planner(repo, rev='tip')]
            exp = DownwardExperiment('/tmp/path', repo, environment=env,
                                     combinations=combos,
                                     limits={'search_time': 30,
                                             'search_memory': 1024})

        """
        Experiment.__init__(self, path, environment=environment, cache_dir=cache_dir)

        if not repo or not os.path.isdir(repo):
            logging.critical('The path "%s" is not a local Fast Downward '
                             'repository.' % repo)
        self.repo = repo
        self.orig_path = self.path
        self.search_exp_path = self.path
        self.preprocess_exp_path = self.path + '-p'
        self._path_to_python = None
        Checkout.REV_CACHE_DIR = os.path.join(self.cache_dir, 'revision-cache')
        self.preprocessed_tasks_dir = os.path.join(self.cache_dir, 'preprocessed-tasks')
        tools.makedirs(self.preprocessed_tasks_dir)

        self.combinations = (combinations or
                             [(Translator(repo), Preprocessor(repo), Planner(repo))])

        self.compact = compact
        self.suites = defaultdict(list)
        self._algorithms = []
        self._portfolios = []

        limits = limits or {}
        for key, value in limits.items():
            if key not in LIMITS:
                logging.critical('Unknown limit: %s' % key)
        self.limits = LIMITS
        self.limits.update(limits)

        # Save if this is a compact experiment i.e. preprocess files are copied
        self.set_property('compact', compact)

        self.include_preprocess_results_in_search_runs = True
        self.compilation_options = ['-j%d' % self._jobs]

        self._search_parsers = []
        self.add_search_parser(os.path.join(DOWNWARD_SCRIPTS_DIR, 'search_parser.py'))

        # Remove the default experiment steps
        self.steps = Sequence()

        self.add_step(Step('build-preprocess-exp', self.build, stage='preprocess'))
        self.add_step(Step('run-preprocess-exp', self.run, stage='preprocess'))
        self.add_fetcher(src=self.preprocess_exp_path,
                         dest=self.preprocessed_tasks_dir,
                         name='fetch-preprocess-results',
                         copy_all=True,
                         write_combined_props=False)
        self.add_step(Step('build-search-exp', self.build, stage='search'))
        self.add_step(Step('run-search-exp', self.run, stage='search'))
        self.add_fetcher(src=self.search_exp_path, name='fetch-search-results')

    @property
    def _problems(self):
        tasks = []
        for benchmark_dir, suite in self.suites.items():
            tasks.extend(suites.build_suite(benchmark_dir, suite))
        return tasks

    def add_suite(self, suite, benchmark_dir=None):
        """
        *suite* can either be a string or a list of strings. The strings can be
        tasks or domains. ::

            exp.add_suite("gripper:prob01.pddl")
            exp.add_suite("gripper")
            exp.add_suite(["miconic", "trucks", "grid", "gripper:prob01.pddl"])

        There are some predefined suites in ``suites.py``. ::

            exp.add_suite(suites.suite_strips())
            exp.add_suite(suites.suite_ipc_all())

        If *benchmark_dir* is given, it must be the path to a benchmark directory.
        The default is <repo>/benchmarks. The benchmark directory must contain
        domain directories, which in turn hold the PDDL files.
        """
        if isinstance(suite, basestring):
            parts = [part.strip() for part in suite.split(',')]
            suite = [part for part in parts if part]
        if benchmark_dir is None:
            benchmark_dir = os.path.join(self.repo, 'benchmarks')
        benchmark_dir = os.path.abspath(benchmark_dir)
        self.suites[benchmark_dir].extend(suite)

    def add_config(self, nick, config, timeout=None):
        """
        Add a Fast Downward configuration to the experiment.

        *config* must be a list of Fast Downward arguments
        (see http://www.fast-downward.org/SearchEngine). It will
        be run for all (translator, preprocessor, planner) combinations
        given in the constructor.

        *nick* is an abbreviation for the configuration used in the reports.

        If *timeout* is given it will be used for this config
        instead of the global time limit set in the constructor. ::

            exp.add_config('lmcut', ['--search', 'astar(lmcut())'])
        """
        if not isinstance(nick, basestring):
            logging.critical('Config nick must be a string: %s' % nick)
        if not isinstance(config, list):
            logging.critical('Config must be a list: %s' % config)
        if not nick.endswith('.py') and not config:
            logging.critical('Config cannot be empty: %s' % config)
        for translator, preprocessor, planner in self.combinations:
            algo_nick = _get_rev_nick(translator, preprocessor, planner) + '-' + nick
            self._algorithms.append(_DownwardAlgorithm(
                algo_nick, config, timeout=timeout,
                translator=translator, preprocessor=preprocessor, planner=planner))

    def add_portfolio(self, portfolio, nick=None, **kwargs):
        """
        *portfolio* must be the path to a Fast Downward portfolio file.

        *nick* is the name of the portfolio in reports. If it is not
        set explicitly, the portfolio's filename will be used.

        Arguments in *kwargs* are passed to :py:meth:`.add_config`. ::

            exp.add_portfolio('/home/john/my_portfolio.py')
            exp.add_portfolio('/home/john/my_portfolio.py',
                              nick='issue123-my_portfolio')
        """
        if not isinstance(portfolio, basestring):
            logging.critical('portfolio must be a string: %s' % portfolio)
        if not portfolio.endswith('.py'):
            logging.critical('Path to portfolio must end on .py: %s' % portfolio)
        if not os.path.isfile(portfolio):
            logging.critical('Portfolio %s could not be found.' % portfolio)
        if not os.access(portfolio, os.X_OK):
            logging.critical('Portfolio is not executable. Run "chmod +x %s"' % portfolio)
        nick = nick or os.path.basename(portfolio)
        self._portfolios.append(portfolio)
        self.add_config(nick, ['--portfolio', os.path.basename(portfolio)], **kwargs)

    def add_search_parser(self, path_to_parser):
        """
        Invoke script at *path_to_parser* at the end of each search run. ::

            exp.add_search_parser('path/to/parser')
        """
        self._search_parsers.append(('search_parser%d' % len(self._search_parsers),
                                     path_to_parser))

    def set_path_to_python(self, path):
        """
        Instead of the default python interpreter "python", let the translator
        use a different one.

        *path* must be an absolute path to a python interpreter or a name that
        will be found on the system PATH like "python2.7". ::

            exp.set_path_to_python('/home/john/bin/Python-2.7.3/python')
            exp.set_path_to_python('/usr/bin/python3.2')
            exp.set_path_to_python('python2.7')
        """
        self._path_to_python = path

    def _get_path_to_python(self):
        return self._path_to_python or 'python'

    def _check_python_version(self):
        """Abort if the Python version is not supported by the translator."""
        p = subprocess.Popen([self._get_path_to_python(), '-c', VERSION_STMT])
        p.wait()
        if p.returncode != 0:
            logging.critical('Use exp.set_path_to_python(path) to select a '
                             'supported Python interpreter.')

    def _adapt_path(self, stage):
        if stage == 'preprocess':
            self.path = self.preprocess_exp_path
        elif stage == 'search':
            self.path = self.search_exp_path
        else:
            logging.critical('There is no stage "%s"' % stage)

    def run(self, stage):
        """Run the specified experiment stage.

        *stage* can be "preprocess" or "search".

        """
        self._adapt_path(stage)
        Experiment.run(self)
        self.path = self.orig_path

    @property
    def _jobs(self):
        """Return the number of jobs to use when building binaries."""
        jobs = getattr(self.environment, 'processes', None)
        return jobs or max(1, int(multiprocessing.cpu_count() / 2))

    def build(self, stage, **kwargs):
        """Write the experiment to disk.

        Overriding methods cannot add resources or new files here, because we
        clear those lists in this method.
        """
        # Save the experiment stage in the properties
        self.set_property('stage', stage)
        self.set_property('suite', self.suites)
        self.set_property('algorithms', [algo.nick for algo in self._algorithms])
        self.set_property('repo', self.repo)
        self.set_property('default_limits', self.limits)

        self.runs = []
        self.new_files = []
        self.resources = []

        self._adapt_path(stage)
        self._setup_ignores(stage)
        self._checkout_and_compile(stage, **kwargs)

        if stage == 'preprocess':
            self._make_preprocess_runs()
        elif stage == 'search':
            self._make_search_runs()
        else:
            logging.critical('There is no stage "%s"' % stage)

        Experiment.build(self, **kwargs)
        self.path = self.orig_path

    def _require_part(self, part):
        logging.info('Requiring %s' % part.src_dir)
        self.add_resource('', part.src_dir, part.get_path_dest())

    def _get_unique_checkouts(self):
        translators = set()
        preprocessors = set()
        planners = set()
        for algo in self._algorithms:
            translators.add(algo.translator)
            preprocessors.add(algo.preprocessor)
            planners.add(algo.planner)
        return translators, preprocessors, planners

    def _checkout_and_compile(self, stage, **kwargs):
        translators, preprocessors, planners = self._get_unique_checkouts()

        for part in sorted(translators | preprocessors | planners):
            part.checkout(self.compilation_options)

        if stage == 'preprocess':
            for part in sorted(translators | preprocessors):
                self._require_part(part)
        elif stage == 'search':
            for planner in sorted(planners):
                self._require_part(planner)
        else:
            logging.critical('There is no stage "%s"' % stage)

    def _setup_ignores(self, stage):
        self.ignores = []

        # Ignore some scripts.
        self.ignores.extend(['build_all', 'cleanup', 'plan', 'plan-ipc'])

        if stage == 'preprocess':
            self.ignores.extend(['search'])
            self.ignores.extend(['regression-tests', 'tests'])
        elif stage == 'search':
            self.ignores.extend(['translate', 'preprocess'])

    def _prepare_translator_and_preprocessor(self, translator, preprocessor):
        # In order to set an environment variable, overwrite the executable
        self.add_resource(translator.shell_name,
                          translator.get_bin('translate.py'),
                          translator.get_bin_dest())
        self.add_resource(preprocessor.shell_name,
                          preprocessor.get_bin('preprocess'),
                          preprocessor.get_bin_dest())

    def _prepare_planner(self, planner):
        self.add_resource(planner.shell_name, planner.get_bin('downward'),
                          planner.get_bin_dest())

        # Copy portfolios into experiment directory.
        for portfolio in self._portfolios:
            name = os.path.basename(portfolio)
            self.add_resource('', portfolio, planner.get_path_dest('search', name))

    def _prepare_validator(self):
        validate = os.path.join(self.repo, 'src', 'VAL', 'validate')
        if not os.path.exists(validate):
            logging.info('Building the validator in the experiment repository.')
            tools.run_command(['make', '-j%d' % self._jobs],
                              cwd=os.path.dirname(validate))
        assert os.path.exists(validate), validate
        self.add_resource('VALIDATE', validate, 'validate')

        downward_validate = os.path.join(DOWNWARD_SCRIPTS_DIR, 'validate.py')
        self.add_resource('DOWNWARD_VALIDATE', downward_validate, 'downward-validate')

    def _make_preprocess_runs(self):
        self._check_python_version()
        self.add_resource(
            'PREPROCESS_PARSER',
            os.path.join(DOWNWARD_SCRIPTS_DIR, 'preprocess_parser.py'))

        unique_preprocessing = set()
        for algo in self._algorithms:
            unique_preprocessing.add((algo.translator, algo.preprocessor))

        for translator, preprocessor in sorted(unique_preprocessing):
            self._prepare_translator_and_preprocessor(translator, preprocessor)

            for prob in self._problems:
                self.add_run(PreprocessRun(self, translator, preprocessor, prob))

    def _make_search_runs(self):
        if not self._algorithms:
            logging.critical('You must add at least one config or portfolio.')
        for parser_name, parser_path in self._search_parsers:
            self.add_resource(parser_name.upper(), parser_path)
        _, _, planners = self._get_unique_checkouts()
        for planner in planners:
            self._prepare_planner(planner)
        self._prepare_validator()
        for algo in self._algorithms:
            for prob in self._problems:
                self._make_search_run(algo, prob)

    def _make_search_run(self, algo, prob):
        preprocess_dir = os.path.join(
            self.preprocessed_tasks_dir,
            algo.translator.rev + '-' + algo.preprocessor.rev,
            prob.domain, prob.problem)

        def source(filename):
            return os.path.join(preprocess_dir, filename)

        def source_and_dest(filename):
            dest = None if self.compact else filename
            return source(filename), dest

        run = SearchRun(self, algo, prob)
        self.add_run(run)

        run.add_parsers(self._search_parsers)

        run.set_property('preprocess_dir', preprocess_dir)
        run.set_property('compact', self.compact)

        # We definitely need the output file.
        run.add_resource('OUTPUT', *source_and_dest('output'))

        # Needed for validation.
        run.add_resource('DOMAIN', *source_and_dest('domain.pddl'))
        run.add_resource('PROBLEM', *source_and_dest('problem.pddl'))

        # The other files are optional.
        if self.include_preprocess_results_in_search_runs:
            # Properties have to be copied, not linked.
            run.add_resource('', source('properties'), 'properties')

            # {all,test}.groups were created by old versions of the planner.
            run.add_resource('', *source_and_dest('all.groups'), required=False)
            run.add_resource('', *source_and_dest('test.groups'), required=False)
