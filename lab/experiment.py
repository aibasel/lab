#! /usr/bin/env python
"""
Main module for experiment creation
"""

from __future__ import with_statement

import os
import sys
import logging

from lab import tools
from lab.external.ordereddict import OrderedDict
from lab.fetcher import Fetcher
from lab.steps import Step, Sequence


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
        """
        Add a key-value property. These can be used later for evaluation.

        Example:
        >>> exp.set_property('translator', '4321')
        """
        self.properties[name] = value

    def add_resource(self, resource_name, source, dest, required=True, symlink=False):
        """
        Example:
        >>> experiment.add_resource('PLANNER', 'path/to/planner', 'dest-name')

        Includes a "global" file, i.e., one needed for all runs, into the
        experiment archive. In case of GkiGridExperiment, copies it to the
        main directory of the experiment. The name "PLANNER" is an ID for
        this resource that can also be used to refer to it in shell scripts.

        Example:
        >>> run.add_resource('DOMAIN', '../benchmarks/gripper/domain.pddl',
                             'domain.pddl')

        Copy "../benchmarks/gripper/domain.pddl" into the run
        directory under name "domain.pddl" and make it available as
        resource "DOMAIN" (usable as environment variable $DOMAIN).
        """
        if not (source, dest) in self.resources:
            self.resources.append((source, dest, required, symlink))
        self.env_vars[resource_name] = dest

    def _get_abs_path(self, rel_path):
        """
        Return absolute path by applying rel_path to the base dir

        Example:
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
        self.new_files.append((dest, content))
        self.env_vars[resource_name] = dest


class Experiment(_Buildable):
    def __init__(self, path, env):
        _Buildable.__init__(self)
        self.path = os.path.abspath(path)
        self.environment = env
        self.environment.exp = self
        self.fetcher = Fetcher()
        self.shard_size = SHARD_SIZE
        self.argparser = tools.ArgParser()

        self.runs = []

        self.set_property('experiment_file', os.path.basename(sys.argv[0]))

        # Include the experiment code
        self.add_resource('LAB', tools.SCRIPTS_DIR, 'lab')

        self.steps = Sequence()
        self.add_step(Step('build', self.build))
        self.add_step(Step('start', self.run))
        self.add_step(Step('fetch', self.fetcher, self.path))

    @property
    def name(self):
        # Derive the experiment name from the path
        return os.path.basename(self.path)

    @property
    def eval_dir(self):
        return self.path + '-eval'

    def add_step(self, step):
        self.steps.append(step)

    def add_run(self, run=None):
        """
        Factory for Runs
        Schedule this run to be part of the experiment.
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
        self.steps.process_step_names(self.args.steps)

    def run(self):
        self.environment.start_exp()

    def build(self, overwrite=False, only_main_script=False, no_main_script=False):
        """
        Apply all the actions to the filesystem
        """
        logging.info('Exp Dir: "%s"' % self.path)

        # Make the variables absolute
        self.env_vars = dict([(var, self._get_abs_path(path))
                              for (var, path) in self.env_vars.items()])

        self._set_run_dirs()

        if not no_main_script:
            # This is the first part where we only write the main script.
            # We only overwrite the exp dir in the first part.
            tools.overwrite_dir(self.path, overwrite)
            self._build_main_script()
        if only_main_script:
            sys.exit()

        # This is the second part where we write everything else
        self._build_resources()
        self._build_runs()
        self._build_properties_file()

    def _set_run_dirs(self):
        """
        Sets the relative run directories as instance variables for all runs
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
        """
        Generates the main script
        """
        self.environment.write_main_script()

    def _build_runs(self):
        """
        Uses the relative directory information and writes all runs to disc
        """
        num_runs = len(self.runs)
        self.set_property('runs', num_runs)
        logging.info('Building %d runs' % num_runs)
        for index, run in enumerate(self.runs, 1):
            run.build()
            if index % 100 == 0:
                logging.info('Built run %6d/%d' % (index, num_runs))


class Run(_Buildable):
    """
    A Task can consist of one or multiple Runs
    """
    def __init__(self, experiment):
        _Buildable.__init__(self)
        self.experiment = experiment

        self.path = ''
        self.linked_resources = []
        self.commands = OrderedDict()

        self.optional_output = []
        self.required_output = []

    def require_resource(self, resource_name):
        """
        Some resources can be used by linking to the resource in the
        experiment directory without copying it into each run

        In the argo cluster however, requiring a resource implies copying it
        into the task directory.

        Example:
        >>> run.require_resource('PLANNER')

        Make the planner resource available for this run
        In environments like the argo cluster, this implies
        copying the planner into each task. For the gkigrid, we merely
        need to set up the PLANNER environment variable.
        """
        self.linked_resources.append(resource_name)

    def add_command(self, name, command, **kwargs):
        """Adds a command to the run.

        "name" is the command's name.
        "command" has to be a list of strings.

        The items in kwargs are passed to the calls.call.Call() class. You can
        find the valid keys there.

        kwargs can also contain a value for "abort_on_failure" which makes the
        run abort if the command does not return 0.

        The remaining items in kwargs are passed to subprocess.Popen()
        The allowed parameters can be found at
        http://docs.python.org/library/subprocess.html

        Examples:
        >>> run.add_command('translate', [run.translator.shell_name,
                                          'domain.pddl', 'problem.pddl'])
        >>> run.add_command('preprocess', [run.preprocessor.shell_name],
                            {'stdin': 'output.sas'})
        >>> run.add_command('validate', ['VALIDATE', 'DOMAIN', 'PROBLEM',
                                         'sas_plan'])

        """
        assert type(name) is str, 'The command name must be a string'
        assert type(command) in (tuple, list), 'The command must be a list'
        name = name.replace(' ', '_')
        self.commands[name] = (command, kwargs)

    def declare_optional_output(self, file_glob):
        """
        Example:
        >>> run.declare_optional_output('plan.soln*')

        Specifies that all files names "plan.soln*" (using
        shell-style glob patterns) are part of the experiment output.
        """
        self.optional_output.append(file_glob)

    def declare_required_output(self, filename):
        """
        Declare output files that must be present at the end or we have an
        error. A specification like this is e.g. necessary for the Argo
        cluster. On the gkigrid, this wouldn't do anything, although
        the declared outputs should be stored somewhere so that we
        can later verify that all went according to plan.
        """
        self.required_output.append(filename)

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
            if not type(cmd) is list:
                logging.critical('Commands have to be lists of strings. '
                                 'The command <%s> is not a list.' % cmd)
            if not cmd:
                logging.critical('Command "%s" cannot be empty' % name)

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
                         '    print_(driver_log, "%s returned %%s" %% retcode)\n'
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
        if not isinstance(run_id, list):
            logging.critical('id must be a list, but %s is not' % run_id)
        self.properties['id'] = [str(item) for item in run_id]
        _Buildable._build_properties_file(self)
