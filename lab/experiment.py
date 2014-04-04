# -*- coding: utf-8 -*-
#
# lab is a Python API for running and evaluating algorithms.
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
Main module for experiment creation
"""

import os
import pkgutil
import sys
import logging

from lab import tools
from lab.fetcher import Fetcher
from lab.steps import Step, Sequence
from lab.environments import LocalEnvironment

try:
    # Python 2.7, 3.1 and above.
    from collections import OrderedDict
    OrderedDict  # Silence pyflakes
except ImportError:
    from lab.external.ordereddict import OrderedDict


DEFAULT_ABORT_ON_FAILURE = False
# How many tasks to group into one top-level directory
SHARD_SIZE = 100

# Make argparser available globally so users can add custom arguments.
ARGPARSER = tools.ArgParser()
ARGPARSER.epilog = "The list of available steps will be added later."
ARGPARSER.add_argument('steps', metavar='step', nargs='*', default=[],
        help='Name or number of a step below. If none is given, print help.')
ARGPARSER.add_argument('--all', dest='run_all_steps', action='store_true',
        help='Run all supplied steps. If none are given, run all steps '
        'in the experiment. For local experiments this option has no '
        'effect if any steps are given on the commandline. Use this '
        'option to run unattended experiments on computer grids. '
        'If this option is used, make sure that the experiment script '
        'doesn\'t change while the experiment is running, because it '
        'will be called for each step.')


class _Buildable(object):
    def __init__(self):
        self.resources = []
        self.new_files = []
        # List of glob-style patterns used to exclude files (not full paths).
        self.ignores = []

        self.properties = tools.Properties()

    def set_property(self, name, value):
        """Add a key-value property. These can be used later for evaluation. ::

            exp.set_property('compact', True)
            run.set_property('domain', 'gripper')

        Each run must have the property *id* which must be a *unique* list of
        strings. They determine where the results for this run will land on
        disk and in the combined properties file. ::

            run.set_property('id', [algorithm, benchmark])
            run.set_property('id', [config, domain, problem])

        """
        self.properties[name] = value

    @classmethod
    def _check_alias(cls, name):
        if name and not (name[0].isalpha() and name.replace('_', '').isalnum()):
            logging.critical(
                'Names for resources must start with a letter and consist '
                'exclusively of letters, numbers and underscores: %s' %
                name)

    def add_resource(self, name, source, dest='', required=True, symlink=False):
        """Include the file or directory *source* in the experiment or run.

        *name* is an alias for the resource in commands. It must start with a
        letter and consist exclusively of letters, numbers and underscores.
        If you don't need an alias for the resource, set name=''.

        *source* is copied to /path/to/exp-or-run/*dest*. If *dest* is
        omitted, the last part of the path to *source* will be taken as the
        destination filename. If you only want an alias for your resource, but
        don't want to copy or link it, set *dest* to None.

        Example::

            exp.add_resource('PLANNER', 'path/to/my-planner', 'planner')

        includes "planner" in the experiment directory. The name "PLANNER" can
        be used to reference it in a run's commands::

            run.require_resource('PLANNER')
            run.add_resource('DOMAIN', 'benchmarks/gripper/domain.pddl')
            run.add_resource('PROBLEM', 'benchmarks/gripper/prob01.pddl')
            run.add_command('find-plan', ['PLANNER', 'DOMAIN', 'PROBLEM'])

        """
        if dest == '':
            dest = os.path.basename(source)
        if dest is None:
            dest = os.path.abspath(source)
        self._check_alias(name)
        resource = (name, source, dest, required, symlink)
        if not resource in self.resources:
            self.resources.append(resource)

    def add_new_file(self, name, dest, content):
        """
        Write *content* to /path/to/exp-or-run/*dest* and make the new file
        available to the commands as *name*.

        *name* is an alias for the resource in commands. It must start with a
        letter and consist exclusively of letters, numbers and underscores. ::

            run.add_new_file('LEARN', 'learn.txt', 'a = 5; b = 2; c = 5')
            run.add_command('print-trainingset', ['cat', 'LEARN'])

        """
        self._check_alias(name)
        new_file = (name, dest, content)
        if not new_file in self.new_files:
            self.new_files.append(new_file)

    @property
    def _env_vars(self):
        pairs = ([(name, dest) for name, dest, content in self.new_files] +
                 [(name, dest) for name, source, dest, req, sym in self.resources])
        return dict((name, self._get_abs_path(dest)) for name, dest in pairs if name)

    def _get_abs_path(self, rel_path):
        """Return absolute path by applying rel_path to the base dir."""
        return os.path.join(self.path, rel_path)

    def _get_rel_path(self, abs_path):
        return os.path.relpath(abs_path, start=self.path)

    def _build_properties_file(self):
        """
        Load existing properties file if there is any and update it with the new
        properties.
        """
        combined_props = tools.Properties(self._get_abs_path('properties'))
        combined_props.update(self.properties)
        combined_props.write()

    def _build_resources(self):
        for name, dest, content in self.new_files:
            filename = self._get_abs_path(dest)
            tools.makedirs(os.path.dirname(filename))
            with open(filename, 'w') as file:
                logging.debug('Writing file "%s"' % filename)
                file.write(content)
                if dest == 'run':
                    # Make run script executable
                    os.chmod(filename, 0755)

        for name, source, dest, required, symlink in self.resources:
            if required and not os.path.exists(source):
                logging.critical('The required resource can not be found: %s' %
                                 source)
            dest = self._get_abs_path(dest)
            if not dest.startswith(self.path):
                # Only copy resources that reside in the experiment/run dir.
                continue
            if symlink:
                # Do not create a symlink if the file doesn't exist.
                if not os.path.exists(source):
                    continue
                source = self._get_rel_path(source)
                os.symlink(source, dest)
                logging.debug('Linking from %s to %s' % (source, dest))
                continue

            # Even if the directory containing a resource has already been added,
            # we copy the resource since we might want to overwrite it.
            logging.debug('Copying %s to %s' % (source, dest))
            tools.copy(source, dest, required, self.ignores)


class Experiment(_Buildable):
    def __init__(self, path, environment=None, cache_dir=None):
        """
        Create a new experiment that will be built at *path* using the methods
        provided by :ref:`Environment <environments>` *environment*. If
        *environment* is None, ``LocalEnvironment`` is used (default).

        Lab will use the *cache_dir* for storing temporary files.
        In case you run :py:class:`Fast Downward experiments
        <downward.experiments.DownwardExperiment>` this directory can become
        very large (tens of GB) since it is used to cache revisions and
        preprocessed tasks. By default *cache_dir* points to ``~/lab``.

        An experiment consists of multiple steps. Every experiment will need at
        least the following steps:

        * Build the experiment.
        * Run it.
        * Fetch the results.
        * Make a report.

        In the "Run it" step all runs that have been added to the experiment
        will be executed. Each run consists of one or multiple commands.
        """
        _Buildable.__init__(self)
        self.path = os.path.abspath(path)
        if any(char in self.path for char in (':', ',')):
            logging.critical('Path contains commas or colons: %s' % self.path)
        self.environment = environment or LocalEnvironment()
        self.environment.exp = self
        self.cache_dir = cache_dir or tools.DEFAULT_USER_DIR
        tools.makedirs(self.cache_dir)
        self.shard_size = SHARD_SIZE

        self.runs = []

        self.set_property('experiment_file', self._script)

        self.steps = Sequence()
        self.add_step(Step('build', self.build))
        self.add_step(Step('start', self.run))
        self.add_fetcher(name='fetch')

    @property
    def name(self):
        """Return the directory name of the experiment's path."""
        return os.path.basename(self.path)

    @property
    def eval_dir(self):
        """Return the name of the default evaluation directory.

        This is the directory where the fetched and parsed results will land by
        default.

        """
        return self.path + '-eval'

    @property
    def _script(self):
        """Return the filename of the experiment script."""
        return os.path.basename(sys.argv[0])

    def add_step(self, step):
        """Add :ref:`Step <steps>` *step* to the list of experiment steps.

        >>> import shutil
        >>> from lab.experiment import Experiment
        >>> exp = Experiment('/tmp/myexp')
        >>> exp.add_step(Step('remove-exp-dir', shutil.rmtree, exp.path))

        """
        self.steps.append(step)

    def add_fetcher(self, src=None, dest=None, name=None, **kwargs):
        """
        Add a step that fetches results from experiment or
        evaluation directories into a new or existing evaluation
        directory. Use this method to combine results from multiple
        experiments.

        *src* can be an experiment or evaluation directory. It defaults to
        ``exp.path``.

        *dest* must be a new or existing evaluation directory. It
        defaults to ``exp.eval_dir``. If *dest* already contains
        data, the old and new data will be merged, not replaced.

        If no *name* is given, call this step "fetch-``basename(src)``".

        Valid keyword args:

        If *copy_all* is True (default: False), copy all files from the run
        dirs to a new directory tree at *dest*. Without this option only
        the combined properties file is written do disk.

        If *write_combined_props* is True (default), write the combined
        properties file.

        You can include only specific domains or configurations by using
        :py:class:`filters <.Report>`.

        *parsers* can be a list of paths to parser scripts. If given, each
        parser is called in each run directory and the results are added to
        the properties file which is fetched afterwards. This option is
        useful if you forgot to parse some attributes during the experiment.

        Examples:

        Merge the results from "other-exp" into this experiment's results::

            exp.add_fetcher(src='/path/to/other-exp-eval')

        Merge two evaluation directories at the location of the second one::

            exp.add_fetcher(src=eval_dir1, dest=combined_eval_dir, name='merge')

        Fetch only the runs for certain configuration from an older experiment::

            exp.add_fetcher(src='/path/to/eval-dir',
                            filter_config_nick=['config_1', 'config_5'])
        """
        src = src or self.path
        dest = dest or self.eval_dir
        name = name or 'fetch-%s' % os.path.basename(src)
        self.add_step(Step(name, Fetcher(), src, dest, **kwargs))

    def add_report(self, report, name='', eval_dir='', outfile=''):
        """Add *report* to the list of experiment steps.

        This method is a shortcut for
        ``add_step(Step(name, report, eval_dir, outfile))``.

        If no *name* is given, use *outfile* or the *report*'s class name.

        By default, use the experiment's standard *eval_dir*.

        If *outfile* is omitted, compose a filename from *name* and the
        *report*'s format. If *outfile* is a relative path, put it under
        *eval_dir*.
        """
        name = name or os.path.basename(outfile) or report.__class__.__name__.lower()
        eval_dir = eval_dir or self.eval_dir
        outfile = outfile or '%s.%s' % (name, report.output_format)
        if not os.path.isabs(outfile):
            outfile = os.path.join(eval_dir, outfile)
        self.add_step(Step(name, report, eval_dir, outfile))

    def add_run(self, run=None):
        """Schedule *run* to be part of the experiment.

        If *run* is None, create a new run, add it to the experiment and return
        it.

        """
        run = run or Run(self)
        self.runs.append(run)
        return run

    def __call__(self):
        ARGPARSER.epilog = self.steps.get_steps_text()
        self.args = ARGPARSER.parse_args()
        if not self.args.steps and not self.args.run_all_steps:
            ARGPARSER.print_help()
            sys.exit(0)
        # If no steps were given on the commandline, run all exp steps.
        steps = [self.steps.get_step(name) for name in self.args.steps] or self.steps
        if self.args.run_all_steps:
            self.environment.run_steps(steps)
        else:
            Sequence.run_steps(steps)

    def run(self):
        """Start the experiment by running all runs that were added to it.

        Depending on the selected environment this may start the runs locally
        or on a computer cluster."""
        self.environment.start_exp()

    def build(self, overwrite=False, only_main_script=False, no_main_script=False):
        """Apply all the actions to the filesystem.

        If *overwrite* is True and the experiment directory exists, it is
        overwritten without prior confirmation.
        """
        logging.info('Exp Dir: "%s"' % self.path)

        self._set_run_dirs()

        # TODO: Currently no_main_script is always False.
        if not no_main_script:
            # This is the first part where we only write the main script.
            # We only overwrite the exp dir in the first part.
            if os.path.exists(self.path):
                runs_exist = any(path.startswith('runs')
                                 for path in os.listdir(self.path))
                logging.info('The directory "%s" contains run directories: %s' %
                             (self.path, runs_exist))
                # Overwrite if overwrite is True or if no runs exist.
                tools.overwrite_dir(self.path, overwrite or not runs_exist)
            else:
                tools.makedirs(self.path)
            self._build_main_script()
        if only_main_script:
            return

        # This is the second part where we write everything else
        self._build_resources()
        self._build_runs()
        self._build_properties_file()

    def _set_run_dirs(self):
        """
        Sets the relative run directories as instance variables for all runs.
        """
        def run_number(number):
            return str(number).zfill(5)

        def get_shard_dir(shard_number):
            first_run = self.shard_size * (shard_number - 1) + 1
            last_run = self.shard_size * (shard_number)
            return 'runs-%s-%s' % (run_number(first_run), run_number(last_run))

        current_run = 0
        shards = tools.divide_list(self.runs, self.shard_size)

        for shard_number, shard in enumerate(shards, start=1):
            for run in shard:
                current_run += 1
                rel_dir = os.path.join(get_shard_dir(shard_number),
                                       run_number(current_run))
                run.path = self._get_abs_path(rel_dir)
                run.set_property('run_dir', os.path.relpath(run.path, self.path))

    def _build_main_script(self):
        """Generates the main script."""
        self.environment.write_main_script()

    def _build_runs(self):
        """
        Uses the relative directory information and writes all runs to disc.
        """
        if not self.runs:
            logging.critical('No runs have been added to the experiment.')
        num_runs = len(self.runs)
        self.set_property('runs', num_runs)
        logging.info('Building %d runs' % num_runs)
        for index, run in enumerate(self.runs, 1):
            run.build()
            if index % 100 == 0:
                logging.info('Built run %6d/%d' % (index, num_runs))


class Run(_Buildable):
    def __init__(self, experiment):
        """Create a new run.

        An experiment consists of one or multiple runs. If you run various
        algrithms on a set of benchmarks, there should be one run for each
        (algorithm, benchmark) pair.

        A run consists of one or more commands.
        """
        _Buildable.__init__(self)
        self.experiment = experiment

        self.path = ''
        self.linked_resources = []
        self.commands = OrderedDict()

    def require_resource(self, resource_name):
        """Make *resource_name* available for this run.

        In environments like the argo cluster, this implies
        copying the resource into each run. For the gkigrid, we merely
        need to set up the PLANNER environment variable.

        Currently, this method is not needed, because we always make all aliases
        available for the commands and the argo cluster is not yet supported. ::

            run.require_resource('PLANNER')

        """
        self.linked_resources.append(resource_name)

    def add_command(self, name, command, **kwargs):
        """Add a command to the run.

        *name* is a descriptive name for the command.

        *command* has to be a list of strings where the first item is the
        executable.

        If you pass ``abort_on_failure=True`` and the command does not exit with
        code 0, subsequent commands of this run are not executed.

        The other items in *kwargs* are passed to the :ref:`Call <call>` class.

        Examples::

            run.add_command('list-directory', ['ls', '-al'])
            run.add_command('translate', [run.translator.shell_name,
                                          'domain.pddl', 'problem.pddl'])
            run.add_command('preprocess', [run.preprocessor.shell_name],
                            {'stdin': 'output.sas'})
            run.add_command('validate', ['VALIDATE', 'DOMAIN', 'PROBLEM',
                                         'sas_plan'])
        """
        assert isinstance(name, basestring), 'name %s is not a string' % name
        assert isinstance(command, (list, tuple)), '%s is not a list' % command
        assert command, 'Command "%s" cannot be empty' % name
        name = name.replace(' ', '_')
        self.commands[name] = (command, kwargs)

    def build(self):
        """
        After having made all the necessary adjustments with the methods above,
        this method can be used to write everything to the disk.
        """
        assert self.path
        tools.overwrite_dir(self.path)

        # We need to build the linked resources before the run script.
        # Only this way we have all resources in self.resources
        # (linked ones too).
        # We need to build the run script before the resources, because the run
        # script is a resource.
        self._build_linked_resources()
        self._build_run_script()
        self._build_resources()
        self._build_properties_file()

    def _build_run_script(self):
        if not self.commands:
            raise SystemExit('Please add at least one command')

        # Copy missing env_vars from experiment.
        env_vars = self.experiment._env_vars
        env_vars.update(self._env_vars)

        run_script = pkgutil.get_data('lab', 'data/run-template.py')

        def make_call(name, cmd, kwargs):
            abort_on_failure = kwargs.pop('abort_on_failure',
                                          DEFAULT_ABORT_ON_FAILURE)

            # Support running globally installed binaries
            def format_arg(arg):
                return arg if arg in env_vars else '"%s"' % arg

            def format_key_value_pair(key, val):
                return '%s=%s' % (key, val if val in env_vars else repr(val))

            cmd_string = '[%s]' % ', '.join([format_arg(arg) for arg in cmd])
            kwargs_string = ', '.join(format_key_value_pair(key, value)
                                      for key, value in kwargs.items())
            parts = [cmd_string]
            if kwargs_string:
                parts.append(kwargs_string)
            call = ('retcode = Call(%s, name="%s", **redirects).wait()\n'
                    'save_returncode("%s", retcode)\n' %
                    (', '.join(parts), name, name))
            if abort_on_failure:
                call += ('if not retcode == 0:\n'
                         '    print_(driver_err, "%s returned %%s" %% retcode)\n'
                         '    sys.exit(1)\n' % name)
            return call

        calls_text = '\n'.join(make_call(name, cmd, kwargs)
                               for name, (cmd, kwargs) in self.commands.items())

        if env_vars:
            env_vars_text = ''
            for var, filename in sorted(env_vars.items()):
                filename = self._get_abs_path(filename)
                # Only use relative filename for paths in the experiment dir.
                if filename.startswith(self.experiment.path):
                    filename = self._get_rel_path(filename)
                env_vars_text += ('%s = "%s"\n' % (var, filename))
        else:
            env_vars_text = '"Here you would find variable declarations"'

        for old, new in [('VARIABLES', env_vars_text), ('CALLS', calls_text)]:
            run_script = run_script.replace('"""%s"""' % old, new)

        self.add_new_file('', 'run', run_script)

    def _build_linked_resources(self):
        """
        If we are building an argo experiment, add all linked resources to
        the resources list.
        """
        self.experiment.environment.build_linked_resources(self)

    def _build_properties_file(self):
        # Check correctness of id property
        run_id = self.properties.get('id')
        if run_id is None:
            logging.critical('Each run must have an id')
        if not isinstance(run_id, (list, tuple)):
            logging.critical('id must be a list, but %s is not' % run_id)
        run_id = [str(item) for item in run_id]
        self.properties['id'] = run_id
        # Save the id as a string as well to allow for easier grepping
        self.properties['id_string'] = ':'.join(run_id)
        _Buildable._build_properties_file(self)
