# -*- coding: utf-8 -*-
#
# downward uses the lab package to conduct experiments with the
# Fast Downward planning system.
#
# Copyright (C) 2012  Jendrik Seipp (jendrikseipp@web.de)
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
import itertools

from lab.experiment import Run, Experiment
from downward import checkouts
from downward.checkouts import Translator, Preprocessor, Planner
from downward import suites
from lab import tools
from lab.steps import Step, Sequence


PREPROCESSED_TASKS_DIR = os.path.join(tools.USER_DIR, 'preprocessed-tasks')
tools.makedirs(PREPROCESSED_TASKS_DIR)

DOWNWARD_SCRIPTS_DIR = os.path.join(tools.BASE_DIR, 'downward', 'scripts')


# Limits can be overwritten in DownwardExperiment
LIMITS = {
    'translate_time': 7200,
    'translate_memory': 8192,
    'preprocess_time': 7200,
    'preprocess_memory': 8192,
    'search_time': 1800,
    'search_memory': 2048,
    }


# At least one of those must be found (First is taken if many are present)
PLANNER_BINARIES = ['downward', 'downward-debug', 'downward-profile',
                    'release-search', 'search']


def _require_src_dirs(exp, combinations):
    for checkout in set(itertools.chain(*combinations)):
        logging.info('Requiring %s' % checkout.src_dir)
        exp.add_resource('SRC_%s' % checkout.name, checkout.src_dir,
                         'code-%s' % checkout.name)


class DownwardRun(Run):
    def __init__(self, exp, translator, preprocessor, problem):
        Run.__init__(self, exp)

        self.translator = translator
        self.preprocessor = preprocessor

        self.problem = problem

        self._set_properties()
        self._save_limits()

    def _set_properties(self):
        self.domain_name = self.problem.domain
        self.problem_name = self.problem.problem

        self.set_property('translator', self.translator.rev)
        self.set_property('preprocessor', self.preprocessor.rev)

        self.set_property('translator_parent', self.translator.parent_rev)
        self.set_property('preprocessor_parent', self.preprocessor.parent_rev)

        self.set_property('domain', self.domain_name)
        self.set_property('problem', self.problem_name)

        self.set_property('experiment_name', self.experiment.name)

    def _save_limits(self):
        for name, limit in self.experiment.limits.items():
            self.set_property('limit_' + name, limit)

    def _save_id(self, ext_config):
        self.set_property('config', ext_config)
        run_id = [ext_config, self.domain_name, self.problem_name]
        self.set_property('id', run_id)
        self.set_property('id_string', ':'.join(run_id))


class PreprocessRun(DownwardRun):
    def __init__(self, exp, translator, preprocessor, problem):
        DownwardRun.__init__(self, exp, translator, preprocessor, problem)

        self.require_resource(self.preprocessor.shell_name)

        self.add_resource("DOMAIN", self.problem.domain_file(), "domain.pddl")
        self.add_resource("PROBLEM", self.problem.problem_file(), "problem.pddl")

        self.add_command('translate', [self.translator.shell_name, 'DOMAIN', 'PROBLEM'],
                         time_limit=exp.limits['translate_time'],
                         mem_limit=exp.limits['translate_memory'])
        self.add_command('preprocess', [self.preprocessor.shell_name],
                         stdin='output.sas',
                         time_limit=exp.limits['preprocess_time'],
                         mem_limit=exp.limits['preprocess_memory'])
        self.add_command('parse-preprocess', ['PREPROCESS_PARSER'])

        ext_config = '-'.join([self.translator.name, self.preprocessor.name])
        self._save_id(ext_config)


class SearchRun(DownwardRun):
    def __init__(self, exp, translator, preprocessor, planner, problem, config_nick, config):
        DownwardRun.__init__(self, exp, translator, preprocessor, problem)

        self.planner = planner
        self.set_property('planner', self.planner.rev)
        self.set_property('planner_parent', self.planner.parent_rev)

        self.require_resource(self.planner.shell_name)
        if config:
            # We have a single planner configuration
            assert isinstance(config_nick, basestring), config_nick
            if not isinstance(config, list):
                logging.error('Config strings are not supported. Please use a list: %s' %
                              config)
                sys.exit(1)
            search_cmd = [self.planner.shell_name] + config
        else:
            # We have a portfolio, config_nick is the path to the portfolio file
            config_nick = os.path.basename(config_nick)
            search_cmd = [self.planner.shell_name, '--portfolio', config_nick,
                          '--plan-file', 'sas_plan']
        self.add_command('search', search_cmd, stdin='output',
                         time_limit=exp.limits['search_time'],
                         mem_limit=exp.limits['search_memory'],
                         abort_on_failure=False)

        # Validation
        self.require_resource('VALIDATE')
        self.require_resource('DOWNWARD_VALIDATE')
        self.add_command('validate', ['DOWNWARD_VALIDATE', 'VALIDATE', 'DOMAIN',
                                      'PROBLEM'])
        self.add_command('parse-search', ['SEARCH_PARSER'])

        self.set_property('config_nick', config_nick)
        self.set_property('commandline_config', config)

        # If all three parts have the same revision don't clutter the reports
        names = [self.translator.name, self.preprocessor.name, self.planner.name]
        if len(set(names)) == 1:
            names = [names[0]]
        ext_config = '-'.join(names + [config_nick])
        self._save_id(ext_config)


class DownwardExperiment(Experiment):
    """
    *repo* must be the path to a Fast Downward repository. This repository is
    used to search for problem files and if *combinations* is None.

    *combinations* is a list of Checkout tuples of the form
    (Translator, Preprocessor, Planner). If no combinations are given, perform
    an experiment with the working copy in *repo*.

    If *compact* is True, link to preprocessing files instead of copying them.
    Only use this option if the preprocessed files will **not** be changed
    during the experiment.

    If *limits* is given, it must be a dictionary and it will be used to
    overwrite the default limits.

    >>> repo = '/path/to/downward-repo'
    >>> combos = [(Translator(repo, rev=123),
                   Preprocessor(repo, rev='e2a018c865f7'),
                   Planner(repo, rev='tip', dest='myplanner-version')]
    >>> exp = DownwardExperiment('/tmp/path', repo,
                                 combinations=combos, compact=False,
                                 limits={'search_time': 30})

    """
    def __init__(self, path, repo, environment=None, combinations=None, compact=True,
                 limits=None):
        Experiment.__init__(self, path, environment)

        self.repo = repo
        self.search_exp_path = self.path
        self.preprocess_exp_path = self.path + '-p'

        self.combinations = (combinations or
                    [(Translator(repo), Preprocessor(repo), Planner(repo))])
        self.compact = compact
        self.suites = []
        self.configs = []
        self.portfolios = []

        self.limits = LIMITS
        if limits:
            self.limits.update(limits)

        # Do not copy the .obj directory into the experiment directory.
        self.ignores.append('*.obj')

        # Save if this is a compact experiment i.e. preprocess files are copied
        self.set_property('compact', compact)

        # Remove the default experiment steps
        self.steps = Sequence()

        self.add_step(Step('build-preprocess-exp', self.build, stage='preprocess'))
        self.add_step(Step('run-preprocess-exp', self.run, stage='preprocess'))
        self.add_step(Step('fetch-preprocess-results', self.fetcher,
                           self.preprocess_exp_path, eval_dir=PREPROCESSED_TASKS_DIR,
                           copy_all=True, write_combined_props=False))
        self.add_step(Step('build-search-exp', self.build, stage='search'))
        self.add_step(Step('run-search-exp', self.run, stage='search'))
        self.add_step(Step('fetch-search-results', self.fetcher, self.search_exp_path))

    @property
    def _problems(self):
        benchmark_dir = os.path.join(self.repo, 'benchmarks')
        return suites.build_suite(benchmark_dir, self.suites)

    def add_suite(self, suite):
        """
        *suite* can either be a string or a list of strings. The strings can be
        tasks, domains or suites:

        >>> exp.add_suite("gripper")
        >>> exp.add_suite("gripper:prob01.pddl")
        >>> exp.add_suite("STRIPS")
        >>> exp.add_suite(["miconic", "trucks", "grid"])
        """
        if isinstance(suite, basestring):
            parts = [part.strip() for part in suite.split(',')]
            self.suites.extend([part for part in parts if part])
        else:
            self.suites.extend(suite)

    def add_config(self, nick, config):
        """
        *nick* is the name the config will get in the reports.
        *config* must be a list of arguments that can be passed to the planner.

        >>> exp.add_config("lmcut", ["--search", "astar(lmcut())"])
        """
        self.configs.append((nick, config))

    def add_portfolio(self, portfolio_file):
        """
        *portfolio_file* must be the path to a Fast Downward portfolio file.
        """
        self.portfolios.append(portfolio_file)

    def run(self, stage):
        """Run the specified experiment stage.

        *stage* can be "preprocess" or "search".

        """
        if stage == 'preprocess':
            self.path = self.preprocess_exp_path
        elif stage == 'search':
            self.path = self.search_exp_path
        else:
            logging.error('There is no stage "%s"' % stage)
            sys.exit(1)
        Experiment.run(self)

    def build(self, stage, overwrite=False):
        """Write the experiment to disk.

        If *overwrite* is False and the experiment directory exists, it is
        overwritten without prior confirmation.

        """
        # Save the experiment stage in the properties
        self.set_property('stage', stage)
        checkouts.checkout(self.combinations)
        checkouts.compile(self.combinations)
        self.runs = []
        self.new_files = []
        self.resources = []
        self.env_vars = {}
        # Include the experiment code again.
        self.add_resource('LAB', tools.SCRIPTS_DIR, 'lab')
        _require_src_dirs(self, self.combinations)
        if stage == 'preprocess':
            self.path = self.preprocess_exp_path
            self.add_resource('PREPROCESS_PARSER',
                    os.path.join(DOWNWARD_SCRIPTS_DIR, 'preprocess_parser.py'),
                    'preprocess_parser.py')
            self._make_preprocess_runs()
        elif stage == 'search':
            self.path = self.search_exp_path
            self.add_resource('SEARCH_PARSER',
                        os.path.join(DOWNWARD_SCRIPTS_DIR, 'search_parser.py'),
                        'search_parser.py')
            self._make_search_runs()
        else:
            logging.error('There is no stage "%s"' % stage)
            sys.exit(1)

        Experiment.build(self, overwrite=overwrite)

    def _prepare_translator_and_preprocessor(self, translator, preprocessor):
        # Copy the whole translate directory
        self.add_resource(translator.shell_name + '_DIR', translator.bin_dir,
                          translator.get_path_dest('translate'))
        # In order to set an environment variable, overwrite the executable
        self.add_resource(translator.shell_name,
                          translator.get_bin('translate.py'),
                          translator.get_path_dest('translate', 'translate.py'))
        self.add_resource(preprocessor.shell_name,
                          preprocessor.get_bin('preprocess'),
                          preprocessor.get_bin_dest())

    def _prepare_planner(self, planner):
        # Get the planner binary
        bin = None
        for name in PLANNER_BINARIES:
            path = planner.get_bin(name)
            if os.path.isfile(path):
                bin = path
                break
        if not bin:
            logging.error('None of the binaries %s could be found in %s' %
                          (PLANNER_BINARIES, planner.bin_dir))
            sys.exit(1)
        self.add_resource(planner.shell_name, bin, planner.get_bin_dest())

        # Find all portfolios and copy them into the experiment directory
        for portfolio in self.portfolios:
            if not os.path.isfile(portfolio):
                logging.error('Portfolio file %s could not be found.' % portfolio)
                sys.exit(1)
            #  Portfolio has to be executable
            if not os.access(portfolio, os.X_OK):
                os.chmod(portfolio, 0755)
            name = os.path.basename(portfolio)
            self.add_resource(tools.shell_escape(name), portfolio,
                              planner.get_path_dest('search', name))

        # The tip changeset has the newest validator version so we use this one
        validate = os.path.join(self.repo, 'src', 'validate')
        if not os.path.exists(validate):
            logging.error('Please run ./build_all in the src directory first '
                          'to compile the validator')
            sys.exit(1)
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
        for translator, preprocessor, planner in self.combinations:
            self._prepare_planner(planner)

            for config_nick, config in self.configs + [(path, '') for path in self.portfolios]:
                for prob in self._problems:
                    self._make_search_run(translator, preprocessor, planner,
                                          config_nick, config, prob)

    def _make_search_run(self, translator, preprocessor, planner, config_nick,
                         config, prob):
        preprocess_dir = os.path.join(PREPROCESSED_TASKS_DIR,
                                      translator.name + '-' + preprocessor.name,
                                      prob.domain, prob.problem)

        def path(filename):
            return os.path.join(preprocess_dir, filename)

        run = SearchRun(self, translator, preprocessor, planner, prob, config_nick, config)
        self.add_run(run)

        run.set_property('preprocess_dir', preprocess_dir)

        run.set_property('compact', self.compact)
        sym = self.compact

        # Add the preprocess files for later parsing
        run.add_resource('OUTPUT', path('output'), 'output', symlink=sym)
        run.add_resource('ALL_GROUPS', path('all.groups'), 'all.groups', symlink=sym, required=False)
        run.add_resource('TEST_GROUPS', path('test.groups'), 'test.groups', symlink=sym, required=False)
        run.add_resource('OUTPUT_SAS', path('output.sas'), 'output.sas', symlink=sym)
        run.add_resource('DOMAIN', path('domain.pddl'), 'domain.pddl', symlink=sym)
        run.add_resource('PROBLEM', path('problem.pddl'), 'problem.pddl', symlink=sym)
        run.add_resource('PREPROCESS_PROPERTIES', path('properties'), 'properties')

        # The logs have to be copied, not linked
        run.add_resource('RUN_LOG', path('run.log'), 'run.log')
        run.add_resource('RUN_ERR', path('run.err'), 'run.err')
