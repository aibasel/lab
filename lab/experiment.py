# -*- coding: utf-8 -*-
#
# lab is a Python API for running and evaluating algorithms.
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
Main module for experiment creation
"""

import os
import sys
import logging

from lab import tools
from lab.external.ordereddict import OrderedDict
from lab.fetcher import Fetcher
from lab.steps import Step, Sequence
from lab.environments import LocalEnvironment


DEFAULT_ABORT_ON_FAILURE = True
# How many tasks to group into one top-level directory
SHARD_SIZE = 100


class _Buildable(object):
    def __init__(self):
        self.resources = []
        self.new_files = []
        self.env_vars = {}
        self.ignores = []

        self.properties = tools.Properties()

    def set_property(self, name, value):
        """Add a key-value property. These can be used later for evaluation.

        >>> exp.set_property('compact', True)
        >>> run.set_property('domain', 'gripper')

        Each run must have the property *id* which must be a *unique* list of
        strings. They determine where the results for this run will land on
        disk and in the combined properties file.

        >>> run.set_property('id', [algorithm, benchmark])
        >>> run.set_property('id', [config, domain, problem])

        """
        self.properties[name] = value

    def add_resource(self, resource_name, source, dest, required=True,
                     symlink=False):
        """Include a file or directory in the experiment or run.

        >>> experiment.add_resource('PLANNER', 'path/to/planner', 'dest-name')

        includes a "global" file, i.e., one needed for all runs, into the
        main directory of the **experiment**. The name "PLANNER" is an ID for
        this resource that can also be used to refer to it in a command.

        >>> run.add_resource('DOMAIN', 'benchmarks/gripper/domain.pddl',
                             'domain.pddl')
        >>> run.add_command('print-domain', ['cat', 'DOMAIN'])

        copies "benchmarks/gripper/domain.pddl" into the **run** directory as
        "domain.pddl" and makes it available to commands as "DOMAIN".
        """
        if not (source, dest) in self.resources:
            self.resources.append((source, dest, required, symlink))
        self.env_vars[resource_name] = dest

    def _get_abs_path(self, rel_path):
        """
        Return absolute path by applying rel_path to the base dir

        >>> _get_abs_path('mytest.q')
        /home/user/mytestjob/mytest.q
        """
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
        for dest, content in self.new_files:
            filename = self._get_abs_path(dest)
            with open(filename, 'w') as file:
                logging.debug('Writing file "%s"' % filename)
                file.write(content)
                if dest == 'run':
                    # Make run script executable
                    os.chmod(filename, 0755)

        for source, dest, required, symlink in self.resources:
            if required and not os.path.exists(source):
                logging.critical('The required resource can not be found: %s' %
                                 source)
            dest = self._get_abs_path(dest)
            if symlink:
                # Do not create a symlink if the file doesn't exist.
                if not os.path.exists(source):
                    continue
                source = self._get_rel_path(source)
                os.symlink(source, dest)
                logging.debug('Linking from %s to %s' % (source, dest))
                continue

            logging.debug('Copying %s to %s' % (source, dest))
            tools.copy(source, dest, required, self.ignores)

    def add_new_file(self, resource_name, dest, content):
        """
        Write *content* to *dest* and make the file available to the commands as
        *resource_name*.

        >>> run.add_new_file('LEARN', 'learn.txt', learning_instances)

        """
        self.new_files.append((dest, content))
        self.env_vars[resource_name] = dest


class Experiment(_Buildable):
    def __init__(self, path, environment=None):
        """
        Create a new experiment that will be built at *path* using the methods
        provided by :ref:`Environment <environments>` *environment*. If
        *environment* is None, ``LocalEnvironment`` is used (default).

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
        self.environment = environment or LocalEnvironment()
        self.environment.exp = self
        self.fetcher = Fetcher()
        self.shard_size = SHARD_SIZE
        self.argparser = tools.ArgParser()

        self.runs = []

        self.set_property('experiment_file', self._script)

        # Include the experiment code
        self.add_resource('LAB', tools.SCRIPTS_DIR, 'lab')

        self.steps = Sequence()
        self.add_step(Step('build', self.build))
        self.add_step(Step('start', self.run))
        self.add_step(Step('fetch', self.fetcher, self.path))

    @property
    def name(self):
        """Return the directory name of the experiment's path."""
        return os.path.basename(self.path)

    @property
    def eval_dir(self):
        """Return the name of the default evaluation directory.

        This is the directory where the fetched and parsed results will land.

        """
        return self.path + '-eval'

    @property
    def _script(self):
        """Return the filename of the experiment script."""
        return os.path.basename(sys.argv[0])

    def add_step(self, step):
        """Add :ref:`Step <steps>` *step* to the list of experiment steps.

        >>> exp.add_step(Step('remove-exp-dir', shutil.rmtree, exp.path))

        """
        self.steps.append(step)

    def add_run(self, run=None):
        """Schedule *run* to be part of the experiment.

        If *run* is None, create a new run, add it to the experiment and return
        it.

        """
        run = run or Run(self)
        self.runs.append(run)
        return run

    def __call__(self):
        self.argparser.epilog = self.steps.get_steps_text()
        self.argparser.add_argument('steps', nargs='*')
        self.args = self.argparser.parse_args()
        if not self.args.steps:
            self.argparser.print_help()
            sys.exit()
        if 'all' in self.args.steps:
            self.environment.run_all_steps()
        else:
            self.steps.process_step_names(self.args.steps)

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

        # Make the variables absolute
        self.env_vars = dict([(var, self._get_abs_path(path))
                              for (var, path) in self.env_vars.items()])

        self._set_run_dirs()

        if not no_main_script:
            # This is the first part where we only write the main script.
            # We only overwrite the exp dir in the first part.
            if os.path.isdir(self.path):
                runs_exist = any(path.startswith('runs') for path in os.listdir(self.path))
                logging.info('The directory "%s" contains run directories: %s' % (self.path, runs_exist))
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
        """
        Some resources can be used by linking to the resource in the
        experiment directory without copying it into each run.

        In the argo cluster however, requiring a resource implies copying it
        into the task directory.

        >>> run.require_resource('PLANNER')

        Make the planner resource available for this run.
        In environments like the argo cluster, this implies
        copying the planner into each task. For the gkigrid, we merely
        need to set up the PLANNER environment variable.
        """
        self.linked_resources.append(resource_name)

    def add_command(self, name, command, **kwargs):
        """Adds a command to the run.

        *name* is the command's name.

        *command* has to be a list of strings.

        The items in *kwargs* are passed to the calls.call.Call() class. You can
        find the valid keys there.

        If *kwargs["abort_on_failure"]* is True and the command does not return
        0, subsequent commands of this run are not executed.

        The remaining items in *kwargs* are passed to subprocess.Popen()
        The allowed parameters can be found at
        http://docs.python.org/library/subprocess.html

        Examples:

        >>> run.add_command('list-directory', ['ls', '-al'])
        >>> run.add_command('translate', [run.translator.shell_name,
                                          'domain.pddl', 'problem.pddl'])
        >>> run.add_command('preprocess', [run.preprocessor.shell_name],
                            {'stdin': 'output.sas'})
        >>> run.add_command('validate', ['VALIDATE', 'DOMAIN', 'PROBLEM',
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
        # (linked ones too)
        self._build_linked_resources()
        self._build_run_script()
        self._build_resources()
        self._build_properties_file()

    def _build_run_script(self):
        if not self.commands:
            raise SystemExit('Please add at least one command')

        self.experiment.env_vars.update(self.env_vars)
        self.env_vars = self.experiment.env_vars.copy()

        run_script = open(os.path.join(tools.DATA_DIR, 'run-template.py')).read()

        def make_call(name, cmd, kwargs):
            abort_on_failure = kwargs.pop('abort_on_failure',
                                          DEFAULT_ABORT_ON_FAILURE)

            # Support running globally installed binaries
            def format_arg(arg):
                return arg if arg in self.env_vars else '"%s"' % arg

            def format_key_value_pair(key, val):
                return '%s=%s' % (key, val if val in self.env_vars else repr(val))

            cmd_string = '[%s]' % ', '.join([format_arg(arg) for arg in cmd])
            kwargs_string = ', '.join(format_key_value_pair(key, value)
                                      for key, value in kwargs.items())
            parts = [cmd_string]
            if kwargs_string:
                parts.append(kwargs_string)
            call = ('retcode = Call(%s, **redirects).wait()\n'
                    'save_returncode("%s", retcode)\n') % (', '.join(parts), name)
            if abort_on_failure:
                call += ('if not retcode == 0:\n'
                         '    print_(driver_err, "%s returned %%s" %% retcode)\n'
                         '    sys.exit(1)\n' % name)
            return call

        calls_text = '\n'.join(make_call(name, cmd, kwargs)
                               for name, (cmd, kwargs) in self.commands.items())

        if self.env_vars:
            env_vars_text = ''
            for var, filename in sorted(self.env_vars.items()):
                abs_filename = self._get_abs_path(filename)
                rel_filename = self._get_rel_path(abs_filename)
                env_vars_text += ('%s = "%s"\n' % (var, rel_filename))
        else:
            env_vars_text = '"Here you would find variable declarations"'

        for old, new in [('VARIABLES', env_vars_text), ('CALLS', calls_text)]:
            run_script = run_script.replace('"""%s"""' % old, new)

        self.add_new_file('RUN_SCRIPT', 'run', run_script)
        return

    def _build_linked_resources(self):
        """
        If we are building an argo experiment, add all linked resources to
        the resources list
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
