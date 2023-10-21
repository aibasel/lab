"""Main module for creating experiments."""

from collections import OrderedDict
import logging
import os
from pathlib import Path
import sys

from lab import environments, tools
from lab.fetcher import Fetcher
from lab.parser import Parser
from lab.steps import get_step, get_steps_text, Step


# How many tasks to group into one top-level directory.
SHARD_SIZE = 100

# Make argparser available globally so users can add custom arguments.
ARGPARSER = tools.get_argument_parser()
ARGPARSER.epilog = "The list of available steps will be added later."
steps_group = ARGPARSER.add_mutually_exclusive_group()
steps_group.add_argument(
    "steps",
    metavar="step",
    nargs="*",
    default=[],
    help="Name or number of a step below. If none is given, print help.",
)
steps_group.add_argument(
    "--all", dest="run_all_steps", action="store_true", help="Run all steps."
)

STATIC_EXPERIMENT_PROPERTIES_FILENAME = "static-experiment-properties"
STATIC_RUN_PROPERTIES_FILENAME = "static-properties"


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
    return os.path.join(get_default_data_dir(), _get_default_experiment_name())


def get_run_dir(task_id):
    lower = ((task_id - 1) // SHARD_SIZE) * SHARD_SIZE + 1
    upper = ((task_id + SHARD_SIZE - 1) // SHARD_SIZE) * SHARD_SIZE
    return f"runs-{lower:0>5}-{upper:0>5}/{task_id:0>5}"


def _check_name(name, typ, extra_chars=""):
    if not isinstance(name, str):
        logging.critical(f"Name for {typ} must be a string: {name}")
    if not name:
        logging.critical(f"Name for {typ} must not be empty")
    alpha_num_name = name
    for c in extra_chars:
        alpha_num_name = alpha_num_name.replace(c, "")
    if not name[0].isalpha():
        logging.critical(f"Name for {typ} must start with a letter.")
    if not alpha_num_name.isalnum():
        logging.critical(
            f"Name for {typ} may only use characters from"
            f" [A-Z], [a-z], [0-9], [{extra_chars}]: {name}"
        )


class _Resource:
    def __init__(self, name, source, dest, symlink):
        self.name = name
        self.source = source
        self.dest = dest
        self.symlink = symlink


class _Buildable:
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
        >>> exp.set_property("suite", ["gripper", "grid"])
        >>> run = exp.add_run()
        >>> run.set_property("domain", "gripper")
        >>> run.set_property("problem", "prob01.pddl")

        Each run must have the property *id* which must be a *unique*
        list of strings. They determine where the results for this run
        will land in the combined properties file. ::

        >>> run.set_property("id", ["algo1", "task1"])
        >>> run.set_property("id", ["algo2", "domain1", "problem1"])

        """
        self.properties[name] = value

    def _check_alias(self, name):
        _check_name(name, "parser or resource", extra_chars="_")
        if name in self.env_vars_relative:
            logging.critical(f"Parser and resource names must be unique: {name!r}")

    def add_resource(self, name, source, dest="", symlink=False):
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
        >>> exp.add_resource("planner", "path/to/my-planner")

        includes my-planner in the experiment directory. You can use
        ``{planner}`` to reference my-planner in a run's commands::

        >>> run = exp.add_run()
        >>> run.add_resource("domain", "path-to/gripper/domain.pddl")
        >>> run.add_resource("task", "path-to/gripper/prob01.pddl")
        >>> run.add_command("plan", ["{planner}", "{domain}", "{task}"])

        """
        if dest == "":
            dest = os.path.basename(source)
        if dest is None:
            dest = os.path.abspath(source)
        if name:
            self._check_alias(name)
            self.env_vars_relative[name] = dest
        self.resources.append(_Resource(name, source, dest, symlink))

    def add_new_file(self, name, dest, content, permissions=0o644):
        """
        Write *content* to /path/to/exp-or-run/*dest* and make the new file
        available to the commands as *name*.

        *name* is an alias for the resource in commands. It must start with a
        letter and consist exclusively of letters, numbers and underscores. ::

        >>> exp = Experiment()
        >>> run = exp.add_run()
        >>> run.add_new_file("learn", "learn.txt", "a = 5; b = 2; c = 5")
        >>> run.add_command("print-trainingset", ["cat", "{learn}"])

        """
        if name:
            self._check_alias(name)
            self.env_vars_relative[name] = dest
        self.new_files.append((dest, content, permissions))

    def add_command(
        self,
        name,
        command,
        time_limit=None,
        memory_limit=None,
        soft_stdout_limit=1024,
        hard_stdout_limit=10 * 1024,
        soft_stderr_limit=64,
        hard_stderr_limit=10 * 1024,
        **kwargs,
    ):
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
        with SIGKILL after five additional seconds. The time spent by a
        command is the sum of time spent across all threads of the
        process.

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
        >>> run.add_command("solver", ["mysolver", "input-file"], time_limit=60)
        >>> # Add a command to *all* runs.
        >>> exp.add_command("cleanup", ["rm", "my-temp-file"])

        Make sure to call all Python programs from the currently active
        Python interpreter, i.e., ``sys.executable``. Otherwise, the
        system Python version might be used instead of the Python version
        from the virtual environment.

        >>> run.add_command("myplanner", [sys.executable, "planner.py", "input-file"])

        """
        _check_name(name, "command", extra_chars="_-")
        if name in self.commands:
            logging.critical(f"Command names must be unique: {name}")

        if not isinstance(command, list):
            logging.critical(f"The command for {name} is not a list: {command}")
        if not command:
            logging.critical(f'Command "{name}" must not be empty')

        if "stdin" in kwargs:
            logging.critical("redirecting stdin is not supported")
        kwargs["time_limit"] = time_limit
        kwargs["memory_limit"] = memory_limit
        kwargs["soft_stdout_limit"] = soft_stdout_limit
        kwargs["hard_stdout_limit"] = hard_stdout_limit
        kwargs["soft_stderr_limit"] = soft_stderr_limit
        kwargs["hard_stderr_limit"] = hard_stderr_limit
        self.commands[name] = (command, kwargs)

    @property
    def _env_vars(self):
        return {
            name: self._get_abs_path(dest)
            for name, dest in self.env_vars_relative.items()
        }

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
            logging.debug(f'Writing file "{filename}"')
            tools.write_file(filename, content)
            os.chmod(filename, permissions)

    def _build_resources(self):
        for resource in self.resources:
            if not os.path.exists(resource.source):
                logging.critical(f"Resource not found: {resource.source}")
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
                logging.debug(f"Linking from {source} to {dest}")
                continue

            # Even if the directory containing a resource has already been added,
            # we copy the resource since we might want to overwrite it.
            logging.debug(f"Copying {resource.source} to {dest}")
            tools.copy(resource.source, dest)


class Experiment(_Buildable):
    """Base class for Lab experiments.

    See :ref:`concepts` for a description of how Lab experiments are
    structured.

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
        tools.configure_logging()

        _Buildable.__init__(self)
        path = path or _get_default_experiment_dir()
        self.path = os.path.abspath(path)
        if any(char in self.path for char in (":", ",")):
            logging.critical(f"Path contains commas or colons: {self.path}")
        self.environment = environment or environments.LocalEnvironment()
        self.environment.exp = self

        self.steps = []
        self.runs = []
        self.parsers = []

        self.set_property("experiment_file", self._script)

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
        return self.path + "-eval"

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
        >>> exp = Experiment("/tmp/myexp")
        >>> exp.add_step("build", exp.build)
        >>> exp.add_step("start", exp.start_runs)
        >>> exp.add_step("rm-eval-dir", shutil.rmtree, exp.eval_dir)
        >>> exp.add_step("greet", subprocess.call, ["echo", "Hello"])

        """
        if not isinstance(name, str):
            logging.critical(f"Step name must be a string: {name}")
        if not name:
            logging.critical("Step name must not be empty")
        if any(step.name == name for step in self.steps):
            raise ValueError(f"Step names must be unique: {name}")
        self.steps.append(Step(name, function, *args, **kwargs))

    def add_parser(self, parser):
        """
        Add a :class:`lab.parser.Parser` to each run of the experiment.

        Each parser is executed in each run directory and manipulates the run's
        "properties" file. For information about how to write parsers see
        :ref:`parsing`.

        """
        if not isinstance(parser, Parser):
            raise TypeError(f'"{parser}" must be a Parser instance')
        self.parsers.append(parser)

    def parse(self):
        """
        Run all parsers that have been added to the experiment with
        :meth:`.add_parser`.

        After parsing, you'll want to run a "fetch" step to collect the parsed
        data from the experiment into the evaluation directory.
        """

        if not os.path.isdir(self.path):
            logging.critical(f"{self.path} is missing or not a directory")

        run_dirs = sorted(Path(self.path).glob("runs-*-*/*"))
        num_runs = len(run_dirs)
        logging.info(
            f"Running {len(self.parsers)} parsers in {num_runs:d} run directories."
        )
        for index, run_dir in enumerate(run_dirs, start=1):
            props_path = run_dir / "properties"
            if props_path.is_file():
                props_path.unlink()

            loglevel = logging.INFO if index % 100 == 0 else logging.DEBUG
            logging.log(loglevel, f"Parsing run: {index:6d}/{num_runs:d}")
            props = tools.Properties(filename=props_path)
            for parser in self.parsers:
                parser.parse(run_dir, props)
            props.write()

    def add_fetcher(
        self, src=None, dest=None, merge=None, name=None, filter=None, **kwargs
    ):
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

        >>> exp = Experiment("/tmp/exp")

        Fetch all results and write a single combined properties file
        to the default evaluation directory (this step is added by
        default):

        >>> exp.add_fetcher(name="fetch")

        Merge the results from "other-exp" into this experiment's
        results:

        >>> exp.add_fetcher(src="/path/to/other-exp-eval")

        Fetch only the runs for certain algorithms:

        >>> exp.add_fetcher(filter_algorithm=["algo_1", "algo_5"])

        """
        src = src or self.path
        dest = dest or self.eval_dir
        name = name or f"fetch-{os.path.basename(src.rstrip('/'))}"
        self.add_step(name, Fetcher(), src, dest, merge=merge, filter=filter, **kwargs)

    def add_report(self, report, name="", eval_dir="", outfile=""):
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
        outfile = outfile or f"{name}.{report.output_format}"
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
            return
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

        logging.info(f'Experiment path: "{tools.get_relative_path(self.path)}"')
        self._remove_experiment_dir()
        tools.makedirs(self.path)

        self._build_resources()
        self._build_runs()
        self._build_properties_file(STATIC_EXPERIMENT_PROPERTIES_FILENAME)

        # The main script can need other experiment files and it adds new files
        self.environment.write_main_script()
        self._build_new_files()

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
            logging.critical("No runs have been added to the experiment.")
        num_runs = len(self.runs)
        self.set_property("runs", num_runs)
        logging.info(f"Building {num_runs} runs")
        for index, run in enumerate(self.runs, 1):
            if index % 100 == 0:
                logging.info(f"Build run {index:6}/{num_runs}")
            for name, (command, kwargs) in self.commands.items():
                run.add_command(name, command, **kwargs)
            run.build(index)
        logging.info("Finished building runs")


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
        self.set_property("run_dir", rel_run_dir)
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
            logging.critical("Please add at least one command")

        exp_vars = self.experiment._env_vars
        run_vars = self._env_vars
        doubly_used_vars = set(exp_vars) & set(run_vars)
        if doubly_used_vars:
            logging.critical(
                f"Resource names cannot be shared between experiments "
                f"and runs, they must be unique: {doubly_used_vars}"
            )
        env_vars = exp_vars
        env_vars.update(run_vars)
        env_vars = self._prepare_env_vars(env_vars)

        def make_call(name, cmd, kwargs):
            kwargs["name"] = name

            # Support running globally installed binaries.
            def format_arg(arg):
                if isinstance(arg, str):
                    try:
                        return repr(arg.format(**env_vars))
                    except KeyError as err:
                        logging.critical(f"Resource {err} is undefined.")
                else:
                    return repr(str(arg))

            def format_key_value_pair(key, val):
                if isinstance(val, str):
                    formatted_value = format_arg(val)
                else:
                    formatted_value = repr(val)
                return f"{key}={formatted_value}"

            cmd_string = f"[{', '.join([format_arg(arg) for arg in cmd])}]"
            kwargs_string = ", ".join(
                format_key_value_pair(key, value)
                for key, value in sorted(kwargs.items())
            )
            parts = [cmd_string]
            if kwargs_string:
                parts.append(kwargs_string)
            return f"Call({', '.join(parts)}, **redirects).wait()\n"

        calls_text = "\n".join(
            make_call(name, cmd, kwargs)
            for name, (cmd, kwargs) in self.commands.items()
        )
        run_script = tools.fill_template("run.py", calls=calls_text)

        self.add_new_file("", "run", run_script, permissions=0o755)

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
        run_id = self.properties.get("id")
        if run_id is None:
            logging.critical("Each run must have an id")
        if not isinstance(run_id, (list, tuple)):
            logging.critical(f"id must be a list: {run_id}")
        for id_part in run_id:
            if not isinstance(id_part, str):
                logging.critical(f"run IDs must be a list of strings: {run_id}")
