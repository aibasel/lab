# -*- coding: utf-8 -*-
#
# Lab is a Python package for evaluating algorithms.
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

"""Main module for creating experiments."""

from collections import OrderedDict
from glob import glob
import logging
import os
import subprocess
import sys

from lab import environments
from lab import tools
from lab.fetcher import Fetcher
from lab.steps import Step, get_step, get_steps_text


# How many tasks to group into one top-level directory.
SHARD_SIZE = 100

# Make argparser available globally so users can add custom arguments.
ARGPARSER = tools.get_argument_parser()
ARGPARSER.epilog = "The list of available steps will be added later."
steps_group = ARGPARSER.add_mutually_exclusive_group()
steps_group.add_argument(
    'steps', metavar='step', nargs='*', default=[],
    help='Name or number of a step below. If none is given, print help.')
steps_group.add_argument(
    '--all', dest='run_all_steps', action='store_true',
    help='Run all steps.')

STATIC_EXPERIMENT_PROPERTIES_FILENAME = 'static-experiment-properties'
STATIC_RUN_PROPERTIES_FILENAME = 'static-properties'


def get_default_data_dir():
    """E.g. "ham/spam/eggs.py" => "ham/spam/data/"."""
    return os.path.join(os.path.dirname(tools.get_script_path()), "data")


def _get_default_experiment_name():
    """Get default name for experiment.

    Derived from the filename of the main script, e.g.
    "ham/spam/eggs.py" => "eggs".
    """
    return os.path.splitext(os.path.basename(tools.get_script_path()))[0]


def _get_default_experiment_dir():
    """E.g. "ham/spam/eggs.py" => "ham/spam/data/eggs"."""
    return os.path.join(
        get_default_data_dir(), _get_default_experiment_name())


def get_run_dir(task_id):
    lower = ((task_id - 1) // SHARD_SIZE) * SHARD_SIZE + 1
    upper = ((task_id + SHARD_SIZE - 1) // SHARD_SIZE) * SHARD_SIZE
    return "runs-{lower:0>5}-{upper:0>5}/{task_id:0>5}".format(**locals())


def _check_name(name, typ, extra_chars=''):
    if not isinstance(name, tools.string_type):
        logging.critical('Name for {typ} must be a string: {name}'.format(**locals()))
    if not name:
        logging.critical('Name for {typ} must not be empty'.format(**locals()))
    alpha_num_name = name
    for c in extra_chars:
        alpha_num_name = alpha_num_name.replace(c, '')
    if not name[0].isalpha():
        logging.critical(
            'Name for {typ} must start with a letter.'.format(**locals()))
    if not alpha_num_name.isalnum():
        logging.critical(
            'Name for {typ} may only use characters from'
            ' [A-Z], [a-z], [0-9], [{extra_chars}]: {name}'.format(**locals()))


class _Resource(object):
    def __init__(self, name, source, dest, symlink, is_parser):
        self.name = name
        self.source = source
        self.dest = dest
        self.symlink = symlink
        self.is_parser = is_parser


class _Buildable(object):
    """Abstract base class for Experiment and Run."""
    def __init__(self):
        self.resources = []
        self.new_files = []
        self.env_vars_relative = {}
        self.commands = OrderedDict()
        self.properties = tools.Properties()

    def set_property(self, name, value):
        """Add a key-value property.

        These can be used later, for example, in reports. ::

        >>> exp = Experiment()
        >>> exp.set_property('suite', ['gripper', 'grid'])
        >>> run = exp.add_run()
        >>> run.set_property('domain', 'gripper')
        >>> run.set_property('problem', 'prob01.pddl')

        Each run must have the property *id* which must be a *unique*
        list of strings. They determine where the results for this run
        will land in the combined properties file. ::

        >>> run.set_property('id', ["algo1", "task1"])
        >>> run.set_property('id', ["algo2", "domain1", "problem1"])

        """
        self.properties[name] = value

    def _check_alias(self, name):
        _check_name(name, 'parser or resource', extra_chars='_')
        if name in self.env_vars_relative:
            logging.critical(
                'Parser and resource names must be unique: {!r}'.format(name))

    def add_resource(self, name, source, dest='', symlink=False):
        """Include the file or directory *source* in the experiment or run.

        *name* is an alias for the resource in commands. It must start with a
        letter and consist exclusively of letters, numbers and underscores.
        If you don't need an alias for the resource, set name=''.

        *source* is copied to /path/to/exp-or-run/*dest*. If *dest* is
        omitted, the last part of the path to *source* will be taken as the
        destination filename. If you only want an alias for your resource, but
        don't want to copy or link it, set *dest* to None.

        Example::

        >>> exp = Experiment()
        >>> exp.add_resource('planner', 'path/to/planner')

        includes my-planner in the experiment directory. You can use
        ``{planner}`` to reference my-planner in a run's commands::

        >>> run = exp.add_run()
        >>> run.add_resource('domain', 'path-to/gripper/domain.pddl')
        >>> run.add_resource('task', 'path-to/gripper/prob01.pddl')
        >>> run.add_command('plan', ['{planner}', '{domain}', '{task}'])

        """
        if dest == '':
            dest = os.path.basename(source)
        if dest is None:
            dest = os.path.abspath(source)
        if name:
            self._check_alias(name)
            self.env_vars_relative[name] = dest
        self.resources.append(
            _Resource(name, source, dest, symlink, is_parser=False))

    def add_new_file(self, name, dest, content, permissions=0o644):
        """
        Write *content* to /path/to/exp-or-run/*dest* and make the new file
        available to the commands as *name*.

        *name* is an alias for the resource in commands. It must start with a
        letter and consist exclusively of letters, numbers and underscores. ::

        >>> exp = Experiment()
        >>> run = exp.add_run()
        >>> run.add_new_file('learn', 'learn.txt', 'a = 5; b = 2; c = 5')
        >>> run.add_command('print-trainingset', ['cat', '{learn}'])

        """
        if name:
            self._check_alias(name)
            self.env_vars_relative[name] = dest
        self.new_files.append((dest, content, permissions))

    def add_command(self, name, command, time_limit=None, memory_limit=None,
                    soft_stdout_limit=1024, hard_stdout_limit=10 * 1024,
                    soft_stderr_limit=64, hard_stderr_limit=10 * 1024,
                    **kwargs):
        """Call an executable.

        If invoked on a *run*, this method adds the command to the
        **specific** run. If invoked on the experiment, the command is
        appended to the list of commands of **all** runs.

        *name* is a string describing the command. It must start with a
        letter and consist exclusively of letters, numbers, underscores
        and hyphens.

        *command* has to be a list of strings where the first item is
        the executable.

        After *time_limit* seconds the signal SIGXCPU is sent to the
        command. The process can catch this signal and exit gracefully.
        If it doesn't catch the SIGXCPU signal, the command is aborted
        with SIGKILL after five additional seconds.

        The command is aborted with SIGKILL when it uses more than
        *memory_limit* MiB.

        You can limit the log size (in KiB) with a soft and hard limit
        for both stdout and stderr. When the soft limit is hit, an
        unexplained error is registered for this run, but the command is
        allowed to continue running. When the hard limit is hit, the
        command is killed with SIGTERM. This signal can be caught and
        handled by the process.

        By default, there are limits for the log and error output, but
        time and memory are not restricted.

        All *kwargs* (except ``stdin``) are passed to `subprocess.Popen
        <http://docs.python.org/library/subprocess.html>`_. Instead of
        file handles you can also pass filenames for the ``stdout`` and
        ``stderr`` keyword arguments. Specifying the ``stdin`` kwarg is
        not supported.

        >>> exp = Experiment()
        >>> run = exp.add_run()
        >>> # Add commands to a *specific* run.
        >>> run.add_command('list-directory', ['ls', '-al'])
        >>> run.add_command(
        ...     'solver', ['mysolver', 'input-file'], time_limit=60)
        >>> # Add a command to *all* runs.
        >>> exp.add_command('cleanup', ['rm', 'my-temp-file'])

        """
        _check_name(name, "command", extra_chars='_-')
        if name in self.commands:
            logging.critical('Command names must be unique: {}'.format(name))

        if not isinstance(command, list):
            logging.critical(
                'The command for {name} is not a list: {command}'.format(**locals()))
        if not command:
            logging.critical('Command "{}" must not be empty'.format(name))

        if 'stdin' in kwargs:
            logging.critical('redirecting stdin is not supported')
        kwargs['time_limit'] = time_limit
        kwargs['memory_limit'] = memory_limit
        kwargs['soft_stdout_limit'] = soft_stdout_limit
        kwargs['hard_stdout_limit'] = hard_stdout_limit
        kwargs['soft_stderr_limit'] = soft_stderr_limit
        kwargs['hard_stderr_limit'] = hard_stderr_limit
        self.commands[name] = (command, kwargs)

    @property
    def _env_vars(self):
        return dict(
            (name, self._get_abs_path(dest))
            for name, dest in self.env_vars_relative.items())

    def _get_abs_path(self, rel_path):
        """Return absolute path by applying rel_path to the base dir."""
        return os.path.join(self.path, rel_path)

    def _get_rel_path(self, abs_path):
        return os.path.relpath(abs_path, start=self.path)

    def _build_properties_file(self, properties_filename):
        combined_props = tools.Properties(self._get_abs_path(properties_filename))
        combined_props.update(self.properties)
        combined_props.write()

    def _build_new_files(self):
        for dest, content, permissions in self.new_files:
            filename = self._get_abs_path(dest)
            tools.makedirs(os.path.dirname(filename))
            logging.debug('Writing file "%s"' % filename)
            tools.write_file(filename, content)
            os.chmod(filename, permissions)

    def _build_resources(self, only_parsers=False):
        for resource in self.resources:
            if only_parsers and not resource.is_parser:
                continue
            if not os.path.exists(resource.source):
                logging.critical('Resource not found: {}'.format(resource.source))
            dest = self._get_abs_path(resource.dest)
            if not dest.startswith(self.path):
                # Only copy resources that reside in the experiment/run dir.
                continue
            if resource.symlink:
                # Do not create a symlink if the file doesn't exist.
                if not os.path.exists(resource.source):
                    continue
                source = self._get_rel_path(resource.source)
                os.symlink(source, dest)
                logging.debug('Linking from %s to %s' % (source, dest))
                continue

            # Even if the directory containing a resource has already been added,
            # we copy the resource since we might want to overwrite it.
            logging.debug('Copying %s to %s' % (resource.source, dest))
            tools.copy(resource.source, dest)


class Experiment(_Buildable):
    """Base class for Lab experiments.

    An **experiment** consists of multiple **steps**. Most experiments
    will have steps for building and executing the experiment:

    >>> exp = Experiment()
    >>> exp.add_step('build', exp.build)
    >>> exp.add_step('start', exp.start_runs)

    Moreover, there are usually steps for fetching the results and
    making reports:

    >>> from lab.reports import Report
    >>> exp.add_fetcher(name='fetch')
    >>> exp.add_report(Report(attributes=["error"]))

    When calling :meth:`.start_runs`, all **runs** part of the
    experiment are executed. You can add runs with the :meth:`.add_run`
    method. Each run needs a unique ID and at least one **command**:

    >>> for algo in ["algo1", "algo2"]:
    ...     for value in range(10):
    ...         run = exp.add_run()
    ...         run.set_property('id', [algo, str(value)])
    ...         run.add_command('solve', [algo, str(value)])

    You can pass the names of selected steps to your experiment script
    or use ``--all`` to execute all steps. At the end of your script,
    call ``exp.run_steps()`` to parse the commandline and execute the
    selected steps.

    """

    def __init__(self, path=None, environment=None):
        """
        The experiment will be built at *path*. It defaults to
        ``<scriptdir>/data/<scriptname>/``. E.g., for the script
        ``experiments/myexp.py``, the default *path* will be
        ``experiments/data/myexp/``.

        *environment* must be an :ref:`Environment <environments>`
        instance. You can use
        :class:`~lab.environments.LocalEnvironment` to run your
        experiment on a single computer (default). If you have access to
        the computer grid in Basel you can use the predefined grid
        environment :class:`~lab.environments.BaselSlurmEnvironment`.
        Alternatively, you can derive your own class from
        :ref:`Environment <environments>`.

        """
        tools.configure_logging(ARGPARSER.parse_args().log_level)

        _Buildable.__init__(self)
        path = path or _get_default_experiment_dir()
        self.path = os.path.abspath(path)
        if any(char in self.path for char in (':', ',')):
            logging.critical('Path contains commas or colons: %s' % self.path)
        self.environment = environment or environments.LocalEnvironment()
        self.environment.exp = self

        self.steps = []
        self.runs = []

        self.set_property('experiment_file', self._script)

    @property
    def name(self):
        """Return the directory name of the experiment's ``path``."""
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

    def add_step(self, name, function, *args, **kwargs):
        """Add a step to the list of experiment steps.

        Use this method to add experiment steps like writing the
        experiment file to disk, removing directories and publishing
        results. To add fetch and report steps, use the convenience
        methods :meth:`.add_fetcher` and :meth:`.add_report`.

        *name* is a descriptive name for the step. When selecting steps
        on the command line, you may either use step names or their
        indices.

        *function* must be a callable Python object, e.g., a function
        or a class implementing `__call__`.

        *args* and *kwargs* will be passed to *function* when the step
        is executed.

        >>> import shutil
        >>> import subprocess
        >>> from lab.experiment import Experiment
        >>> exp = Experiment('/tmp/myexp')
        >>> exp.add_step('build', exp.build)
        >>> exp.add_step('start', exp.start_runs)
        >>> exp.add_step('rm-eval-dir', shutil.rmtree, exp.eval_dir)
        >>> exp.add_step('greet', subprocess.call, ['echo', 'Hello'])

        """
        if not isinstance(name, tools.string_type):
            logging.critical('Step name must be a string: {}'.format(name))
        if not name:
            logging.critical('Step name must not be empty')
        if any(step.name == name for step in self.steps):
            raise ValueError("Step names must be unique: {}".format(name))
        self.steps.append(Step(name, function, *args, **kwargs))

    def add_parser(self, path_to_parser):
        """
        Add a parser to each run of the experiment.

        Add the parser as a resource to the experiment and add a command
        that executes the parser to each run. Since commands are
        executed in the order they are added, parsers should be added
        after all other commands. If you need to change your parsers and
        execute them again you can use the :meth:`.add_parse_again_step`
        method.

        *path_to_parser* must be the path to an executable file. The
        parser is executed in the run directory and manipulates the
        run's "properties" file. The last part of the filename (without
        the extension) is used as a resource name. Therefore, it must be
        unique among all parsers and other resources. Also, it must
        start with a letter and contain only letters, numbers,
        underscores and dashes (which are converted to underscores
        automatically).

        For information about how to write parsers see :ref:`parsing`.

        """
        name, _ = os.path.splitext(os.path.basename(path_to_parser))
        name = name.replace('-', '_')
        self._check_alias(name)
        if not os.path.isfile(path_to_parser):
            logging.critical('Parser %s could not be found.' % path_to_parser)
        if not os.access(path_to_parser, os.X_OK):
            logging.critical('Parser %s is not executable.' % path_to_parser)

        dest = os.path.basename(path_to_parser)
        self.env_vars_relative[name] = dest
        self.resources.append(_Resource(
            name, path_to_parser, dest, symlink=False, is_parser=True))
        self.add_command(name, ["{{{}}}".format(name)])

    def add_parse_again_step(self):
        """
        Add a step that copies the parsers from their originally specified
        locations to the experiment directory and runs all of them again. This
        step overwrites the existing properties file in each run dir.

        Do not forget to run the default fetch step again to overwrite
        existing data in the -eval dir of the experiment.
        """
        def run_parsers():
            if not os.path.isdir(self.path):
                logging.critical('{} is missing or not a directory'.format(self.path))

            # Copy all parsers from their source to their destination again.
            self._build_resources(only_parsers=True)

            run_dirs = sorted(glob(os.path.join(self.path, 'runs-*-*', '*')))

            total_dirs = len(run_dirs)
            logging.info(
                'Parsing properties in {:d} run directories'.format(total_dirs))
            for index, run_dir in enumerate(run_dirs, start=1):
                if os.path.exists(os.path.join(run_dir, 'properties')):
                    # print "removing path {}".format(os.path.join(run_dir, 'properties'))
                    tools.remove_path(os.path.join(run_dir, 'properties'))
                loglevel = logging.INFO if index % 100 == 0 else logging.DEBUG
                logging.log(loglevel, 'Parsing run: {:6d}/{:d}'.format(index, total_dirs))
                for resource in self.resources:
                    if resource.is_parser:
                        parser_filename = self.env_vars_relative[resource.name]
                        rel_parser = os.path.join('../../', parser_filename)
                        with open(os.devnull, 'w') as devnull:
                            # Since parsers often produce output which we would
                            # rather not want to see for each individual run, we
                            # suppress it here.
                            subprocess.check_call(
                                [rel_parser], cwd=run_dir, stdout=devnull)

        self.add_step('parse-again', run_parsers)

    def add_fetcher(self, src=None, dest=None, merge=None, name=None,
                    filter=None, **kwargs):
        """
        Add a step that fetches results from experiment or evaluation
        directories into a new or existing evaluation directory.

        You can use this method to combine results from multiple
        experiments.

        *src* can be an experiment or evaluation directory. It defaults
        to ``exp.path``.

        *dest* must be a new or existing evaluation directory. It
        defaults to ``exp.eval_dir``. If *dest* already contains
        data and *merge* is set to None, the user will be prompted
        whether to override the existing data or to merge the old and
        new data. Setting *merge* to True or to False has the effect
        that the old data is merged or replaced (and the user will not
        be prompted).

        If no *name* is given, call this step "fetch-``basename(src)``".

        You can fetch only a subset of runs (e.g., runs for specific
        domains or algorithms) by passing :py:class:`filters <.Report>`
        with the *filter* argument.

        Example setup:

        >>> exp = Experiment('/tmp/exp')

        Fetch all results and write a single combined properties file
        to the default evaluation directory (this step is added by
        default):

        >>> exp.add_fetcher(name='fetch')

        Merge the results from "other-exp" into this experiment's
        results:

        >>> exp.add_fetcher(src='/path/to/other-exp-eval')

        Fetch only the runs for certain algorithms:

        >>> exp.add_fetcher(filter_algorithm=['algo_1', 'algo_5'])

        """
        src = src or self.path
        dest = dest or self.eval_dir
        name = name or 'fetch-%s' % os.path.basename(src.rstrip('/'))
        self.add_step(
            name, Fetcher(), src, dest, merge=merge, filter=filter,
            **kwargs)

    def add_report(self, report, name='', eval_dir='', outfile=''):
        """Add *report* to the list of experiment steps.

        This method is a shortcut for ``add_step(name, report,
        eval_dir, outfile)`` and uses sensible defaults for omitted
        arguments.

        If no *name* is given, use *outfile* or the *report*'s class name.

        By default, use the experiment's standard *eval_dir*.

        If *outfile* is omitted, compose a filename from *name* and the
        *report*'s format. If *outfile* is a relative path, put it under
        *eval_dir*.

        >>> from downward.reports.absolute import AbsoluteReport
        >>> exp = Experiment("/tmp/exp")
        >>> exp.add_report(AbsoluteReport(attributes=["coverage"]))

        """
        name = name or os.path.basename(outfile) or report.__class__.__name__.lower()
        eval_dir = eval_dir or self.eval_dir
        outfile = outfile or '%s.%s' % (name, report.output_format)
        if not os.path.isabs(outfile):
            outfile = os.path.join(eval_dir, outfile)
        self.add_step(name, report, eval_dir, outfile)

    def add_run(self, run=None):
        """Schedule *run* to be part of the experiment.

        If *run* is None, create a new run, add it to the experiment
        and return it.

        """
        run = run or Run(self)
        self.runs.append(run)
        return run

    def run_steps(self):
        """Parse the commandline and run selected steps."""
        ARGPARSER.epilog = get_steps_text(self.steps)
        args = ARGPARSER.parse_args()
        assert not args.steps or not args.run_all_steps
        if not args.steps and not args.run_all_steps:
            ARGPARSER.print_help()
            sys.exit(0)
        # Run all steps if --all is passed.
        steps = [get_step(self.steps, name) for name in args.steps] or self.steps
        # Use LocalEnvironment if the main experiment step is inactive.
        if any(environments.is_run_step(step) for step in steps):
            env = self.environment
        else:
            env = environments.LocalEnvironment()
        env.run_steps(steps)

    def _remove_experiment_dir(self):
        if os.path.exists(self.path):
            tools.confirm_overwrite_or_abort(self.path)
            tools.remove_path(self.path)

    def build(self, write_to_disk=True):
        """
        Finalize the internal data structures, then write all files
        needed for the experiment to disk.

        If *write_to_disk* is False, only compute the internal data
        structures. This is only needed on grids for
        FastDownwardExperiments.build() which turns the added algorithms
        and benchmarks into Runs.

        """
        if not write_to_disk:
            return

        logging.info('Experiment path: "%s"' % self.path)
        self._remove_experiment_dir()
        tools.makedirs(self.path)
        self.environment.write_main_script()

        self._build_new_files()
        self._build_resources()
        self._build_runs()
        self._build_properties_file(STATIC_EXPERIMENT_PROPERTIES_FILENAME)

    def start_runs(self):
        """Execute all runs that were added to the experiment.

        Depending on the selected environment this method will start
        the runs locally or on a computer grid.

        """
        self.environment.start_runs()

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
            if index % 100 == 0:
                logging.info('Build run %6d/%d' % (index, num_runs))
            for name, (command, kwargs) in self.commands.items():
                run.add_command(name, command, **kwargs)
            run.build(index)
        logging.info('Finished building runs')


class Run(_Buildable):
    """
    An experiment consists of multiple runs. There should be one run
    for each (algorithm, benchmark) pair.

    A run consists of one or more commands.
    """
    def __init__(self, experiment):
        """
        *experiment* must be an :class:`~lab.experiment.Experiment` instance.
        """
        _Buildable.__init__(self)
        self.experiment = experiment
        self.path = None

    def build(self, run_id):
        """Write the run's files to disk.

        This method is called automatically by the experiment.

        """
        rel_run_dir = get_run_dir(run_id)
        self.set_property('run_dir', rel_run_dir)
        self.path = os.path.join(self.experiment.path, rel_run_dir)
        os.makedirs(self.path)

        # We need to build the run script before the resources, because
        # the run script is added as a resource.
        self._build_run_script()
        self._build_new_files()
        self._build_resources()
        self._check_id()
        self._build_properties_file(STATIC_RUN_PROPERTIES_FILENAME)

    def _build_run_script(self):
        if not self.commands:
            logging.critical('Please add at least one command')

        exp_vars = self.experiment._env_vars
        run_vars = self._env_vars
        doubly_used_vars = set(exp_vars) & set(run_vars)
        if doubly_used_vars:
            logging.critical(
                'Resource names cannot be shared between experiments '
                'and runs, they must be unique: {}'.format(doubly_used_vars))
        env_vars = exp_vars
        env_vars.update(run_vars)
        env_vars = self._prepare_env_vars(env_vars)

        def make_call(name, cmd, kwargs):
            kwargs['name'] = name

            # Support running globally installed binaries.
            def format_arg(arg):
                if isinstance(arg, tools.string_type):
                    try:
                        return repr(arg.format(**env_vars))
                    except KeyError as err:
                        logging.critical('Resource {} is undefined.'.format(err))
                else:
                    return repr(str(arg))

            def format_key_value_pair(key, val):
                if isinstance(val, tools.string_type):
                    formatted_value = format_arg(val)
                else:
                    formatted_value = repr(val)
                return '{}={}'.format(key, formatted_value)

            cmd_string = '[{}]'.format(', '.join([format_arg(arg) for arg in cmd]))
            kwargs_string = ', '.join(format_key_value_pair(key, value)
                                      for key, value in sorted(kwargs.items()))
            parts = [cmd_string]
            if kwargs_string:
                parts.append(kwargs_string)
            return ('Call({}, **redirects).wait()\n'.format(', '.join(parts)))

        calls_text = '\n'.join(
            make_call(name, cmd, kwargs)
            for name, (cmd, kwargs) in self.commands.items())
        run_script = tools.fill_template('run.py', calls=calls_text)

        self.add_new_file('', 'run', run_script, permissions=0o755)

    def _prepare_env_vars(self, env_vars):
        """Use relative filenames for paths in the experiment dir."""
        new_env_vars = {}
        for var, path in env_vars.items():
            abspath = self._get_abs_path(path)
            if abspath.startswith(self.experiment.path):
                new_env_vars[var] = self._get_rel_path(path)
            else:
                new_env_vars[var] = abspath
        return new_env_vars

    def _check_id(self):
        run_id = self.properties.get('id')
        if run_id is None:
            logging.critical('Each run must have an id')
        if not isinstance(run_id, (list, tuple)):
            logging.critical('id must be a list: {}'.format(run_id))
        for id_part in run_id:
            if not isinstance(id_part, tools.string_type):
                logging.critical('run IDs must be a list of strings: {}'.format(run_id))
