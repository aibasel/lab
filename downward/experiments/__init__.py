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
import os
import sys
import logging
import multiprocessing
import shutil
import subprocess

from lab.experiment import Run, Experiment
from lab import tools
from lab.steps import Step, Sequence

from downward.checkouts import Checkout, Translator, Preprocessor, Planner
from downward import suites


DOWNWARD_SCRIPTS_DIR = os.path.join(tools.BASE_DIR, 'downward', 'scripts')


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
import platform
import sys
sys.stdout.write('Translator Python version: %s\\n' % platform.python_version())
if sys.version_info[0] == 2 and sys.version_info[1] != 7:
    sys.exit(1)
'''


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
            self.set_property(part.part + '_summary', part.summary)

        self.set_property('domain', self.problem.domain)
        self.set_property('problem', self.problem.problem)

        self.set_property('experiment_name', self.experiment.name)

    def _save_limits(self):
        for name, limit in self.experiment.limits.items():
            self.set_property('limit_' + name, limit)

    def _save_ext_config(self):
        self.set_property('config', self._get_ext_config())

    def _save_id(self):
        run_id = self._get_id()
        self.set_property('id', run_id)
        self.set_property('id_string', ':'.join(run_id))


class PreprocessRun(DownwardRun):
    def __init__(self, exp, translator, preprocessor, problem):
        DownwardRun.__init__(self, exp, [translator, preprocessor], problem)

        self.require_resource(preprocessor.shell_name)

        self.add_resource('DOMAIN', self.problem.domain_file(), 'domain.pddl')
        self.add_resource('PROBLEM', self.problem.problem_file(), 'problem.pddl')

        python = exp._get_path_to_python()

        # Print python version used for translator.
        # python -V prints to stderr so we execute a little program.
        self.add_command('print-python-version', [python, '-c',
                    "import platform; "
                    "print 'Python version: %s' % platform.python_version()"])
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
        self._save_ext_config()
        self._save_id()

    def _get_ext_config(self):
        # Use nicks for run['config'] which appears in report table headers.
        return '-'.join(part.nick for part in self.parts)

    def _get_id(self):
        # Use global revisions for ids to allow for correct cashing.
        return ['-'.join(part.rev for part in self.parts),
                self.problem.domain,
                self.problem.problem]


class SearchRun(DownwardRun):
    def __init__(self, exp, translator, preprocessor, planner, problem,
                 config_nick, config):
        DownwardRun.__init__(self, exp, [translator, preprocessor, planner], problem)

        self.require_resource(planner.shell_name)
        if config:
            # We have a single planner configuration
            planner_type = 'single'
            assert isinstance(config_nick, basestring), config_nick
            if not isinstance(config, list):
                logging.error('Config strings are not supported. Please use a list: %s' %
                              config)
                sys.exit(1)
            search_cmd = [planner.shell_name] + config
        else:
            # We have a portfolio, config_nick is the path to the portfolio file
            planner_type = 'portfolio'
            config_nick = os.path.basename(config_nick)
            search_cmd = [planner.shell_name, '--portfolio', config_nick]
        self.config_nick = config_nick

        self.add_command('search', search_cmd, stdin='OUTPUT',
                         time_limit=exp.limits['search_time'],
                         mem_limit=exp.limits['search_memory'])

        # Remove temporary files (we need bash for globbing).
        self.add_command('rm-tmp-files', ['bash', '-c', 'rm -f downward.tmp.*'])

        # Validation
        self.require_resource('VALIDATE')
        self.require_resource('DOWNWARD_VALIDATE')
        self.add_command('validate', ['DOWNWARD_VALIDATE', 'VALIDATE', 'DOMAIN',
                                      'PROBLEM'])

        self.add_command('parse-search', ['SEARCH_PARSER'])

        self.set_property('config_nick', config_nick)
        self.set_property('commandline_config', config)
        self.set_property('planner_type', planner_type)
        self.set_property('stage', 'search')

        self._save_ext_config()
        self._save_id()

    def _get_ext_config(self):
        # Use nicks for ext_config which appears in report table headers.
        nicks = [part.nick for part in self.parts]
        # If all three parts have the same nick just print it once in reports.
        if len(set(nicks)) == 1:
            nicks = [nicks[0]]
        nicks.append(self.config_nick)
        return '-'.join(nicks)

    def _get_id(self):
        # Use global revisions for ids to allow for correct cashing.
        revs = [part.rev for part in self.parts]
        if len(revs) == 3 and len(set(revs)) == 1:
            revs = [revs[0]]
        return ['-'.join(revs + [self.config_nick]),
                self.problem.domain,
                self.problem.problem]


class DownwardExperiment(Experiment):
    """Conduct a Fast Downward experiment.

    This is the base class for Fast Downward experiments. It can be customized
    by adding the desired configurations, benchmarks and reports.
    See :py:class:`Experiment <lab.experiment.Experiment>` for inherited
    methods.

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

        *repo* must be the path to a Fast Downward repository. This repository
        is used to search for problem files.

        *environment* must be an :ref:`Environment <environments>` instance.

        If given, *combinations* must be a list of :ref:`Checkout <checkouts>`
        tuples of the form (Translator, Preprocessor, Planner). If combinations
        is None (default), perform an experiment with the working copy in *repo*.

        If *compact* is True, link to benchmarks and preprocessed files instead
        of copying them. Only use this option if the linked files will **not**
        be changed during the experiment.

        If *limits* is given, it must be a dictionary and it will be used to
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
                       Planner(repo, rev='tip', dest='myplanner-version')]
            exp = DownwardExperiment('/tmp/path', repo, environment=env,
                                     combinations=combos, compact=False,
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
        self.suites = []
        self.configs = []
        self.portfolios = []

        limits = limits or {}
        for key, value in limits.items():
            if key not in LIMITS:
                logging.critical('Unknown limit: %s' % key)
        self.limits = LIMITS
        self.limits.update(limits)

        # Save if this is a compact experiment i.e. preprocess files are copied
        self.set_property('compact', compact)

        self.include_preprocess_results_in_search_runs = True

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
        benchmark_dir = os.path.join(self.repo, 'benchmarks')
        return suites.build_suite(benchmark_dir, self.suites)

    def add_suite(self, suite):
        """
        *suite* can either be a string or a list of strings. The strings can be
        tasks or domains. ::

            exp.add_suite("gripper:prob01.pddl")
            exp.add_suite("gripper")
            exp.add_suite(["miconic", "trucks", "grid", "gripper:prob01.pddl"])

        There are some predefined suites in ``suites.py``. ::

            exp.add_suite(suites.suite_strips())
            exp.add_suite(suites.suite_ipc_all())

        """
        if isinstance(suite, basestring):
            parts = [part.strip() for part in suite.split(',')]
            self.suites.extend([part for part in parts if part])
        else:
            self.suites.extend(suite)

    def add_config(self, nick, config):
        """
        *nick* is the name the config will get in the reports.
        *config* must be a list of arguments that can be passed to the planner
        (see http://www.fast-downward.org/SearchEngine for details). ::

            exp.add_config("lmcut", ["--search", "astar(lmcut())"])
        """
        self.configs.append((nick, config))

    def add_portfolio(self, portfolio_file):
        """
        *portfolio_file* must be the path to a Fast Downward portfolio file.
        """
        self.portfolios.append(portfolio_file)

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
        """Abort if the Python version is smaller than 2.7."""
        p = subprocess.Popen([self._get_path_to_python(), '-c', VERSION_STMT])
        p.wait()
        if p.returncode != 0:
            logging.critical('The translator requires at least Python 2.7. '
                             'Use exp.set_path_to_python(path) to use a local '
                             'Python interpreter.')

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
        self.set_property('configs', [nick for nick, config in self.configs])
        self.set_property('portfolios', self.portfolios)
        self.set_property('repo', self.repo)
        self.set_property('limits', self.limits)
        self.set_property('combinations', ['-'.join(part.rev for part in combo)
                                           for combo in self.combinations])

        self.runs = []
        self.new_files = []
        self.resources = []

        # Include the experiment code again.
        self.add_resource('', tools.SCRIPTS_DIR, 'lab')

        self._adapt_path(stage)
        self._setup_ignores(stage)
        self._checkout_and_compile(stage, **kwargs)

        if stage == 'preprocess':
            self._check_python_version()
            self.add_resource('PREPROCESS_PARSER',
                    os.path.join(DOWNWARD_SCRIPTS_DIR, 'preprocess_parser.py'),
                    'preprocess_parser.py')
            self._make_preprocess_runs()
        elif stage == 'search':
            self.add_resource('SEARCH_PARSER',
                        os.path.join(DOWNWARD_SCRIPTS_DIR, 'search_parser.py'),
                        'search_parser.py')
            self._make_search_runs()
        else:
            logging.critical('There is no stage "%s"' % stage)

        Experiment.build(self, **kwargs)
        self.path = self.orig_path

    def _require_part(self, part):
        logging.info('Requiring %s' % part.src_dir)
        self.add_resource('', part.src_dir, part.get_path_dest())

    def _checkout_and_compile(self, stage, **kwargs):
        translators = set()
        preprocessors = set()
        planners = set()
        for translator, preprocessor, planner in self.combinations:
            translators.add(translator)
            preprocessors.add(preprocessor)
            planners.add(planner)

        if stage == 'preprocess':
            for part in sorted(translators | preprocessors):
                part.checkout()
                self._require_part(part)
            for preprocessor in sorted(preprocessors):
                preprocessor.compile(options=['-j%d' % self._jobs])
        elif stage == 'search':
            for planner in sorted(planners):
                planner.checkout()
                planner.compile(options=['-j%d' % self._jobs])
                self._require_part(planner)
        else:
            logging.critical('There is no stage "%s"' % stage)

        # Save space by deleting the benchmarks.
        if not kwargs.get('only_main_script', False):
            for part in sorted(translators | preprocessors | planners):
                if part.rev != 'WORK':
                    benchmarks = part.get_path('benchmarks')
                    logging.info('Removing %s to save space.' % benchmarks)
                    shutil.rmtree(benchmarks, ignore_errors=True)

    def _setup_ignores(self, stage):
        self.ignores = []

        # Do not copy the .obj directory into the experiment directory.
        self.ignores.append('*.obj')

        # We don't need VAL's sources.
        self.ignores.append('VAL')

        if stage == 'preprocess':
            # We don't need the search dir and validator for preprocessing.
            self.ignores.extend(['search', 'validate'])

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

        # Find all portfolios and copy them into the experiment directory
        for portfolio in self.portfolios:
            if not os.path.isfile(portfolio):
                logging.error('Portfolio file %s could not be found.' % portfolio)
                sys.exit(1)
            #  Portfolio has to be executable
            if not os.access(portfolio, os.X_OK):
                os.chmod(portfolio, 0755)
            name = os.path.basename(portfolio)
            self.add_resource('', portfolio,
                              planner.get_path_dest('search', name))

        # The tip changeset has the newest validator version so we use this one
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
        unique_preprocessing = set()
        for translator, preprocessor, planner in self.combinations:
            unique_preprocessing.add((translator, preprocessor))

        for translator, preprocessor in sorted(unique_preprocessing):
            self._prepare_translator_and_preprocessor(translator, preprocessor)

            for prob in self._problems:
                self.add_run(PreprocessRun(self, translator, preprocessor, prob))

    def _make_search_runs(self):
        if not self.configs and not self.portfolios:
            logging.critical('You must add at least one config or portfolio.')
        for translator, preprocessor, planner in self.combinations:
            self._prepare_planner(planner)

            portfolios = [(path, '') for path in self.portfolios]
            for config_nick, config in self.configs + portfolios:
                for prob in self._problems:
                    self._make_search_run(translator, preprocessor, planner,
                                          config_nick, config, prob)

    def _make_search_run(self, translator, preprocessor, planner, config_nick,
                         config, prob):
        preprocess_dir = os.path.join(self.preprocessed_tasks_dir,
                                      translator.rev + '-' + preprocessor.rev,
                                      prob.domain, prob.problem)

        def path(filename):
            return os.path.join(preprocess_dir, filename)

        run = SearchRun(self, translator, preprocessor, planner, prob,
                        config_nick, config)
        self.add_run(run)

        run.set_property('preprocess_dir', preprocess_dir)

        run.set_property('compact', self.compact)
        sym = self.compact

        # We definitely need the output file.
        run.add_resource('OUTPUT', path('output'), 'output', symlink=sym)

        # Needed for validation.
        run.add_resource('DOMAIN', path('domain.pddl'), 'domain.pddl', symlink=sym)
        run.add_resource('PROBLEM', path('problem.pddl'), 'problem.pddl', symlink=sym)

        # The other files are optional.
        if self.include_preprocess_results_in_search_runs:
            # Properties files and logs have to be copied, not linked.
            run.add_resource('', path('properties'), 'properties')
            run.add_resource('', path('run.log'), 'run.log')
            run.add_resource('', path('run.err'), 'run.err')

            run.add_resource('', path('output.sas'), 'output.sas',
                             symlink=sym, required=False)

            # {all,test}.groups were created by old versions of the planner.
            run.add_resource('', path('all.groups'), 'all.groups',
                             symlink=sym, required=False)
            run.add_resource('', path('test.groups'), 'test.groups',
                             symlink=sym, required=False)
