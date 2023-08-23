import logging
import math
import multiprocessing
import os
import platform
import random
import re
import subprocess
import sys

from lab import tools


def _get_job_prefix(exp_name):
    assert exp_name
    escape_char = "j" if exp_name[0].isdigit() else ""
    return "".join([escape_char, exp_name, "-"])


def is_build_step(step):
    """Return true iff the given step is the "build" step."""
    return step._funcname == "build"


def is_run_step(step):
    """Return true iff the given step is the "run" step."""
    return step._funcname == "start_runs"


class Environment:
    """Abstract base class for all environments."""

    def __init__(self, randomize_task_order=True):
        """
        If *randomize_task_order* is True (default), tasks for runs are
        started in a random order. This is useful to avoid systematic
        noise due to, e.g., one of the algorithms being run on a
        machine with heavy load. Note that due to the randomization,
        run directories may be pristine while the experiment is running
        even though the logs say the runs are finished.

        """
        self.exp = None
        self.randomize_task_order = randomize_task_order

    def _get_task_order(self, num_tasks):
        task_order = list(range(1, num_tasks + 1))
        if self.randomize_task_order:
            random.shuffle(task_order)
        return task_order

    def write_main_script(self):
        raise NotImplementedError

    def start_runs(self):
        """
        Execute all runs that are part of the experiment.
        """
        raise NotImplementedError

    def run_steps(self):
        raise NotImplementedError


class LocalEnvironment(Environment):
    """
    Environment for running experiments locally on a single machine.
    """

    EXP_RUN_SCRIPT = "run"

    def __init__(self, processes=None, **kwargs):
        """
        If given, *processes* must be between 1 and #CPUs. If omitted,
        it will be set to #CPUs.

        See :py:class:`~lab.environments.Environment` for inherited
        parameters.

        """
        Environment.__init__(self, **kwargs)
        cores = multiprocessing.cpu_count()
        if processes is None:
            processes = cores
        if not 1 <= processes <= cores:
            raise ValueError("processes must be in the range [1, ..., #CPUs].")
        self.processes = processes

    def write_main_script(self):
        script = tools.fill_template(
            "local-job.py",
            task_order=self._get_task_order(len(self.exp.runs)),
            processes=self.processes,
        )

        self.exp.add_new_file("", self.EXP_RUN_SCRIPT, script, permissions=0o755)

    def start_runs(self):
        tools.run_command(
            [tools.get_python_executable(), self.EXP_RUN_SCRIPT], cwd=self.exp.path
        )

    def run_steps(self, steps):
        for step in steps:
            step()


class SlurmEnvironment(Environment):
    """Abstract base class for Slurm environments.

    If the main experiment step is part of the selected steps, the
    selected steps are submitted to Slurm. Otherwise, the selected steps
    are run locally.

    .. note::

        If the steps are run by Slurm, this class writes job files to
        the directory ``<exppath>-grid-steps`` and makes them depend on
        one another. Please inspect the \\*.log and \\*.err files in
        this directory if something goes wrong. Since the job files call
        the experiment script during execution, it mustn't be changed
        during the experiment.

    If *email* is provided and the steps run on the grid, a message will
    be sent when the last experiment step finishes.

    Use *extra_options* to pass additional options. The *extra_options*
    string may contain newlines. The first example below uses only a given
    set of nodes (additional nodes will be used if the given ones don't
    satisfy the resource constraints). The second example shows show to
    specify a project account (needed on NSC if you're part of multiple
    projects). ::

        extra_options="#SBATCH --nodelist=ase[1-5,7,10]"
        extra_options="#SBATCH --account=snic2021-5-330"


    *partition* must be a valid Slurm partition name. In Basel you
    can choose from

    * "infai_1": 24 nodes with 16 cores, 64GB memory, 500GB Sata (default)
    * "infai_2": 24 nodes with 20 cores, 128GB memory, 240GB SSD

    *qos* must be a valid Slurm QOS name. In Basel this must be
    "normal".

    *time_limit_per_task* sets the wall-clock time limit for each Slurm task.
    The BaselSlurmEnvironment subclass uses a default of "0", i.e., no limit.
    (Note that there may still be an external limit set in slurm.conf.)
    The TetralithEnvironment class uses a default of "24:00:00", i.e., 24
    hours. This is because in certain situations, the scheduler prefers to
    schedule tasks shorter than 24 hours.

    *memory_per_cpu* must be a string specifying the memory
    allocated for each core. The string must end with one of the
    letters K, M or G. The default is "3872M". The value for
    *memory_per_cpu* should not surpass the amount of memory that is
    available per core, which is "3872M" for infai_1 and "6354M" for
    infai_2. Processes that surpass the *memory_per_cpu* limit are
    terminated with SIGKILL. To impose a soft limit that can be
    caught from within your programs, you can use the
    ``memory_limit`` kwarg of
    :py:func:`~lab.experiment.Run.add_command`. Fast Downward users
    should set memory limits via the ``driver_options``.

    Slurm limits the memory with cgroups. Unfortunately, this often
    fails on our nodes, so we set our own soft memory limit for all
    Slurm jobs. We derive the soft memory limit by multiplying the
    value denoted by the *memory_per_cpu* parameter with 0.98 (the
    Slurm config file contains "AllowedRAMSpace=99" and we add some
    slack). We use a soft instead of a hard limit so that child
    processes can raise the limit.

    *cpus_per_task* sets the number of cores to be allocated per Slurm
    task (default: 1).

    Examples that reserve the maximum amount of memory available per core:

    >>> env1 = BaselSlurmEnvironment(partition="infai_1", memory_per_cpu="3872M")
    >>> env2 = BaselSlurmEnvironment(partition="infai_2", memory_per_cpu="6354M")

    Example that reserves 12 GiB of memory on infai_1:

    >>> # 12 * 1024 / 3872 = 3.17 -> round to next int -> 4 cores per task
    >>> # 12G / 4 = 3G per core
    >>> env = BaselSlurmEnvironment(
    ...     partition="infai_1",
    ...     memory_per_cpu="3G",
    ...     cpus_per_task=4,
    ... )

    Example that reserves 12 GiB of memory on infai_2:

    >>> # 12 * 1024 / 6354 = 1.93 -> round to next int -> 2 cores per task
    >>> # 12G / 2 = 6G per core
    >>> env = BaselSlurmEnvironment(
    ...     partition="infai_2",
    ...     memory_per_cpu="6G",
    ...     cpus_per_task=2,
    ... )

    Use *export* to specify a list of environment variables that
    should be exported from the login node to the compute nodes
    (default: ["PATH"]).

    You can alter the environment in which the experiment runs with
    the *setup* argument. If given, it must be a string of Bash
    commands. Example::

        # Load Singularity module.
        setup="module load Singularity/2.6.1 2> /dev/null"

    Slurm limits the number of job array tasks. You must set the
    appropriate value for your cluster in the *MAX_TASKS* class
    variable. Lab groups `ceil(runs/MAX_TASKS)` runs in one array
    task.

    See :py:class:`~lab.environments.Environment` for inherited
    parameters.

    """

    # Must be overridden in derived classes.
    JOB_HEADER_TEMPLATE_FILE = None
    RUN_JOB_BODY_TEMPLATE_FILE = None
    STEP_JOB_BODY_TEMPLATE_FILE = None
    MAX_TASKS: int = None  # Value between 1 and MaxArraySize-1 (from slurm.conf).
    DEFAULT_PARTITION = None
    DEFAULT_QOS = None
    DEFAULT_MEMORY_PER_CPU = None

    # Can be overridden in derived classes.
    DEFAULT_TIME_LIMIT_PER_TASK = "0"  # No limit.
    DEFAULT_EXPORT = ["PATH"]
    DEFAULT_SETUP = ""
    NICE_VALUE = 0
    JOB_HEADER_TEMPLATE_FILE = "slurm-job-header"
    RUN_JOB_BODY_TEMPLATE_FILE = "slurm-run-job-body"
    STEP_JOB_BODY_TEMPLATE_FILE = "slurm-step-job-body"

    def __init__(
        self,
        email=None,
        extra_options=None,
        partition=None,
        qos=None,
        time_limit_per_task=None,
        memory_per_cpu=None,
        cpus_per_task=1,
        export=None,
        setup=None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.email = email
        self.extra_options = extra_options or "## (not used)"

        if partition is None:
            partition = self.DEFAULT_PARTITION
        if qos is None:
            qos = self.DEFAULT_QOS
        if time_limit_per_task is None:
            time_limit_per_task = self.DEFAULT_TIME_LIMIT_PER_TASK
        if memory_per_cpu is None:
            memory_per_cpu = self.DEFAULT_MEMORY_PER_CPU
        if export is None:
            export = self.DEFAULT_EXPORT
        if setup is None:
            setup = self.DEFAULT_SETUP

        self.partition = partition
        self.qos = qos
        self.time_limit_per_task = time_limit_per_task
        self.memory_per_cpu = memory_per_cpu
        self.cpus_per_task = cpus_per_task
        self.export = export
        self.setup = setup

    @staticmethod
    def _get_memory_in_kb(limit):
        match = re.match(r"^(\d+)(k|m|g)?$", limit, flags=re.I)
        if not match:
            logging.critical(f"malformed memory_per_cpu parameter: {limit}")
        memory = int(match.group(1))
        suffix = match.group(2)
        if suffix is not None:
            suffix = suffix.lower()
        if suffix == "k":
            pass
        elif suffix is None or suffix == "m":
            memory *= 1024
        elif suffix == "g":
            memory *= 1024 * 1024
        return memory

    def start_runs(self):
        # The queue will start the experiment by itself.
        pass

    def _get_job_name(self, step):
        return (
            f"{_get_job_prefix(self.exp.name)}"
            f"{self.exp.steps.index(step) + 1:02d}-{step.name}"
        )

    def _get_num_runs_per_task(self):
        return math.ceil(len(self.exp.runs) / self.MAX_TASKS)

    def _get_num_tasks(self, step):
        if is_run_step(step):
            num_runs = len(self.exp.runs)
            num_tasks = math.ceil(num_runs / self._get_num_runs_per_task())
        else:
            num_tasks = 1
        return num_tasks

    def _get_job_header(self, step, is_last):
        job_params = self._get_job_params(step, is_last)
        return tools.fill_template(self.JOB_HEADER_TEMPLATE_FILE, **job_params)

    def _get_run_job_body(self, run_step):
        num_runs = len(self.exp.runs)
        num_tasks = self._get_num_tasks(run_step)
        logging.info(f"Grouping {num_runs} runs into {num_tasks} Slurm tasks.")
        return tools.fill_template(
            self.RUN_JOB_BODY_TEMPLATE_FILE,
            exp_path="../" + self.exp.name,
            num_runs=num_runs,
            python=tools.get_python_executable(),
            runs_per_task=self._get_num_runs_per_task(),
            task_order=" ".join(str(i) for i in self._get_task_order(num_tasks)),
        )

    def _get_step_job_body(self, step):
        return tools.fill_template(
            self.STEP_JOB_BODY_TEMPLATE_FILE,
            cwd=os.getcwd(),
            python=tools.get_python_executable(),
            script=sys.argv[0],
            step_name=step.name,
        )

    def _get_job_body(self, step):
        if is_run_step(step):
            return self._get_run_job_body(step)
        return self._get_step_job_body(step)

    def _get_job(self, step, is_last):
        return f"{self._get_job_header(step, is_last)}\n\n{self._get_job_body(step)}"

    def write_main_script(self):
        # The main script is written by the run_steps() method.
        pass

    def run_steps(self, steps):
        """
        We can't submit jobs from within the grid, so we submit them
        all at once with dependencies. We also can't rewrite the job
        files after they have been submitted.
        """
        self.exp.build(write_to_disk=False)

        # Prepare job dir.
        job_dir = self.exp.path + "-grid-steps"
        if os.path.exists(job_dir):
            tools.confirm_or_abort(
                f'The path "{job_dir}" already exists, so the experiment has '
                f"already been submitted. Are you sure you want to "
                f"delete the grid-steps and submit it again?"
            )
            tools.remove_path(job_dir)

        # Overwrite exp dir if it exists.
        if any(is_build_step(step) for step in steps):
            self.exp._remove_experiment_dir()

        # Remove eval dir if it exists.
        if os.path.exists(self.exp.eval_dir):
            tools.confirm_or_abort(
                f'The evaluation directory "{self.exp.eval_dir}" already exists. '
                f"Do you want to remove it?"
            )
            tools.remove_path(self.exp.eval_dir)

        # Create job dir only when we need it.
        tools.makedirs(job_dir)

        prev_job_id = None
        for step in steps:
            job_name = self._get_job_name(step)
            job_file = os.path.join(job_dir, job_name)
            job_content = self._get_job(step, is_last=(step == steps[-1]))
            tools.write_file(job_file, job_content)
            prev_job_id = self._submit_job(
                job_name, job_file, job_dir, dependency=prev_job_id
            )

    def _get_job_params(self, step, is_last):
        job_params = {
            "errfile": "driver.err",
            "extra_options": self.extra_options,
            "logfile": "driver.log",
            "name": self._get_job_name(step),
            "num_tasks": self._get_num_tasks(step),
        }

        # Let all tasks write into the same two files. We could use %a
        # (which is replaced by the array ID) to prevent mangled up logs,
        # but we don't want so many files.
        job_params["logfile"] = "slurm.log"
        job_params["errfile"] = "slurm.err"

        job_params["partition"] = self.partition
        job_params["qos"] = self.qos
        job_params["time_limit_per_task"] = self.time_limit_per_task
        job_params["memory_per_cpu"] = self.memory_per_cpu
        job_params["cpus_per_task"] = self.cpus_per_task
        memory_per_cpu_kb = SlurmEnvironment._get_memory_in_kb(self.memory_per_cpu)
        job_params["soft_memory_limit"] = int(
            self.cpus_per_task * memory_per_cpu_kb * 0.98
        )
        job_params["nice"] = self.NICE_VALUE if is_run_step(step) else 0
        job_params["environment_setup"] = self.setup

        if is_last and self.email:
            job_params["mailtype"] = "END,FAIL,REQUEUE,STAGE_OUT"
            job_params["mailuser"] = self.email
        else:
            job_params["mailtype"] = "NONE"
            job_params["mailuser"] = ""

        return job_params

    def _submit_job(self, job_name, job_file, job_dir, dependency=None):
        submit = ["sbatch"]
        if self.export:
            submit += ["--export", ",".join(self.export)]
        if dependency:
            submit.extend(["-d", "afterany:" + dependency, "--kill-on-invalid-dep=yes"])
        submit.append(job_file)
        logging.info(f"Executing {' '.join(submit)}")
        out = subprocess.check_output(submit, cwd=job_dir).decode()
        logging.info(f"Output: {out.strip()}")
        match = re.match(r"Submitted batch job (\d*)", out)
        assert match, f"Submitting job with sbatch failed: '{out}'"
        return match.group(1)


class BaselSlurmEnvironment(SlurmEnvironment):
    """Environment for Basel's AI group."""

    DEFAULT_PARTITION = "infai_1"
    DEFAULT_QOS = "normal"
    # infai_1 nodes have 61964 MiB and 16 cores => 3872.75 MiB per core
    # (see http://issues.fast-downward.org/issue733).
    DEFAULT_MEMORY_PER_CPU = "3872M"
    MAX_TASKS = 150000 - 1  # see slurm.conf
    # Prioritize jobs from Autonice users on Basel grid.
    NICE_VALUE = 5000


class TetralithEnvironment(SlurmEnvironment):
    """Environment for the NSC Tetralith cluster in Linköping."""

    DEFAULT_PARTITION = "tetralith"
    DEFAULT_QOS = "normal"
    # The maximum wall-clock time limit for a task is 7 days. The default
    # is 2 hours. In certain situations, the scheduler prefers to schedule
    # tasks shorter than 24 hours.
    DEFAULT_TIME_LIMIT_PER_TASK = "24:00:00"
    # There are 1908 nodes. 1844 nodes have 93.1 GiB (97637616 KiB) of
    # memory and 64 nodes have 384 GB of memory. All nodes have 32 cores.
    # So for the vast majority of nodes, we have 2979 MiB per core. The
    # slurm.conf file sets DefMemPerCPU=2904. Since this is rather low, we
    # use the default value from the BaselSlurmEnvironment. This also
    # allows us to keep the default memory limit in the
    # FastDownwardExperiment class.
    DEFAULT_MEMORY_PER_CPU = "3872M"
    # See slurm.conf
    MAX_TASKS = 2000

    @classmethod
    def is_present(cls):
        node = platform.node()
        return re.match(r"tetralith\d+\.nsc\.liu\.se|n\d+", node)
