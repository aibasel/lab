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

import logging
import multiprocessing
import os
import random
import re
import subprocess
import sys

from lab import tools


def _get_job_prefix(exp_name):
    assert exp_name
    escape_char = 'j' if exp_name[0].isdigit() else ''
    return ''.join([escape_char, exp_name, '-'])


def is_build_step(step):
    """Return true iff the given step is the "build" step."""
    return step._funcname == 'build'


def is_run_step(step):
    """Return true iff the given step is the "run" step."""
    return step._funcname == 'start_runs'


class Environment(object):
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

    def _get_task_order(self):
        task_order = range(1, len(self.exp.runs) + 1)
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

    EXP_RUN_SCRIPT = 'run'

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
            'local-job.py',
            task_order=self._get_task_order(),
            processes=self.processes)

        self.exp.add_new_file('', self.EXP_RUN_SCRIPT, script, permissions=0o755)

    def start_runs(self):
        tools.run_command([sys.executable, self.EXP_RUN_SCRIPT], cwd=self.exp.path)

    def run_steps(self, steps):
        for step in steps:
            step()


class GridEnvironment(Environment):
    """Abstract base class for grid environments."""
    # Must be overridden in derived classes.
    JOB_HEADER_TEMPLATE_FILE = None
    RUN_JOB_BODY_TEMPLATE_FILE = None
    STEP_JOB_BODY_TEMPLATE_FILE = None

    # Can be overridden in derived classes.
    MAX_TASKS = float('inf')

    def __init__(self, email=None, extra_options=None, **kwargs):
        """

        If the main experiment step is part of the selected steps, the
        selected steps are submitted to the grid engine. Otherwise, the
        selected steps are run locally.

        .. note::

            If the steps are run by the grid engine, this class writes
            job files to the directory ``<exppath>-grid-steps`` and
            makes them depend on one another. Please inspect the \\*.log
            and \\*.err files in this directory if something goes wrong.
            Since the job files call the experiment script during
            execution, it mustn't be changed during the experiment.

        If *email* is provided and the steps run on the grid, a message
        will be sent when the last experiment step finishes.

        Use *extra_options* to pass additional options. The
        *extra_options* string may contain newlines. Example that runs
        each task on its own node with Slurm::

            extra_options='#SBATCH --exclusive'

        See :py:class:`~lab.environments.Environment` for inherited
        parameters.

        """
        Environment.__init__(self, **kwargs)
        self.email = email
        self.extra_options = extra_options or '## (not used)'

    def start_runs(self):
        # The queue will start the experiment by itself.
        pass

    def _get_job_name(self, step):
        return '%s%02d-%s' % (
            _get_job_prefix(self.exp.name),
            self.exp.steps.index(step) + 1,
            step.name)

    def _get_num_runs(self):
        num_runs = len(self.exp.runs)
        if num_runs > self.MAX_TASKS:
            logging.critical('You are trying to submit a job with %d tasks, '
                             'but only %d are allowed.' %
                             (num_runs, self.MAX_TASKS))
        return num_runs

    def _get_num_tasks(self, step):
        if is_run_step(step):
            return self._get_num_runs()
        else:
            return 1

    def _get_job_params(self, step, is_last):
        return {
            'errfile': 'driver.err',
            'extra_options': self.extra_options,
            'logfile': 'driver.log',
            'name': self._get_job_name(step),
            'num_tasks': self._get_num_tasks(step),
        }

    def _get_job_header(self, step, is_last):
        job_params = self._get_job_params(step, is_last)
        return tools.fill_template(self.JOB_HEADER_TEMPLATE_FILE, **job_params)

    def _get_run_job_body(self):
        return tools.fill_template(
            self.RUN_JOB_BODY_TEMPLATE_FILE,
            task_order=' '.join(str(i) for i in self._get_task_order()),
            exp_path='../' + self.exp.name)

    def _get_step_job_body(self, step):
        return tools.fill_template(
            self.STEP_JOB_BODY_TEMPLATE_FILE,
            cwd=os.getcwd(),
            python=sys.executable or 'python',
            script=sys.argv[0],
            step_name=step.name)

    def _get_job_body(self, step):
        if is_run_step(step):
            return self._get_run_job_body()
        return self._get_step_job_body(step)

    def _get_job(self, step, is_last):
        return '%s\n\n%s' % (self._get_job_header(step, is_last),
                             self._get_job_body(step))

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
        job_dir = self.exp.path + '-grid-steps'
        if os.path.exists(job_dir):
            tools.confirm_or_abort(
                'The path "%s" already exists, so the experiment has '
                'already been submitted. Are you sure you want to '
                'delete the grid-steps and submit it again?' % job_dir)
            tools.remove_path(job_dir)

        # Overwrite exp dir if it exists.
        if any(is_build_step(step) for step in steps):
            self.exp._remove_experiment_dir()

        # Remove eval dir if it exists.
        if os.path.exists(self.exp.eval_dir):
            tools.confirm_or_abort(
                'The evalution directory "%s" already exists. '
                'Do you want to remove it?' % self.exp.eval_dir)
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
                job_name, job_file, job_dir, dependency=prev_job_id)

    def _submit_job(self, job_name, job_file, job_dir, dependency=None):
        raise NotImplementedError


class SlurmEnvironment(GridEnvironment):
    """Abstract base class for slurm grid environments."""
    # Must be overridden in derived classes.
    DEFAULT_PARTITION = None
    DEFAULT_QOS = None
    DEFAULT_MEMORY_PER_CPU = None

    # Can be overridden in derived classes.
    DEFAULT_EXPORT = ['PATH']
    DEFAULT_SETUP = ''
    JOB_HEADER_TEMPLATE_FILE = 'slurm-job-header'
    RUN_JOB_BODY_TEMPLATE_FILE = 'slurm-run-job-body'
    STEP_JOB_BODY_TEMPLATE_FILE = 'slurm-step-job-body'

    def __init__(self, partition=None, qos=None, memory_per_cpu=None,
                 export=None, setup=None, **kwargs):
        """

        *partition* must be a valid Slurm partition name. In Basel you
        can choose from

        * "infai_1": 24 nodes with 16 cores, 64GB memory, 500GB Sata (default)
        * "infai_2": 24 nodes with 20 cores, 128GB memory, 240GB SSD
        * "infai_all": combination of "infai_1" and "infai_2"
          (only use this when runtime is irrelevant)

        *qos* must be a valid Slurm QOS name.

        *memory_per_cpu* must be a string specifying the memory
        allocated for each core. The string must end with one of the
        letters K, M or G. The default is "3872M", which is the maximum
        amount that allows using all 16 infai_1 cores in parallel.
        Processes that surpass the memory limit are terminated with
        SIGKILL. Unless you need more memory you should not have to
        change this variable. Instead, we recommend using the
        ``memory_limit`` kwarg of
        :py:func:`~lab.experiment.Run.add_command` for imposing a soft
        memory limit that can be caught from inside your programs. Fast
        Downward users should set memory limits via the
        ``driver_options``.

        Slurm limits the memory with cgroups. Unfortunately, this often
        fails on our nodes, so we set our own soft memory limit of 3600
        MiB for all Slurm jobs. We use a soft instead of a hard limit so
        that child processes can raise the limit. The value of 3600 MiB
        stems from the fact that the infai_1 nodes have 3872 MiB per
        core and we want to leave some slack.

        Use *export* to specify a list of environment variables that
        should be exported from the login node to the compute nodes
        (default: ["PATH"]).

        You can alter the environment in which the experiment runs with
        the **setup** argument. If given, it must be a string of Bash
        commands. If omitted,
        :class:`~lab.environments.BaselSlurmEnvironment` loads a
        suitable Python version and adds Lab to the PYTHONPATH.

        See :py:class:`~lab.environments.GridEnvironment` for inherited
        parameters.

        """
        GridEnvironment.__init__(self, **kwargs)

        if partition is None:
            partition = self.DEFAULT_PARTITION
        if qos is None:
            qos = self.DEFAULT_QOS
        if memory_per_cpu is None:
            memory_per_cpu = self.DEFAULT_MEMORY_PER_CPU
        if export is None:
            export = self.DEFAULT_EXPORT
        if setup is None:
            setup = self.DEFAULT_SETUP

        self.partition = partition
        self.qos = qos
        self.memory_per_cpu = memory_per_cpu
        self.export = export
        self.setup = setup

    def _get_job_params(self, step, is_last):
        job_params = GridEnvironment._get_job_params(self, step, is_last)

        # Let all tasks write into the same two files. We could use %a
        # (which is replaced by the array ID) to prevent mangled up logs,
        # but we don't want so many files.
        job_params['logfile'] = 'slurm.log'
        job_params['errfile'] = 'slurm.err'

        job_params['partition'] = self.partition
        job_params['qos'] = self.qos
        job_params['memory_per_cpu'] = self.memory_per_cpu
        # Ensure that single-core tasks always run before multi-core tasks.
        job_params['nice'] = 2000 if is_run_step(step) else 0
        job_params['environment_setup'] = self.setup

        if is_last and self.email:
            job_params['mailtype'] = 'END,FAIL,REQUEUE,STAGE_OUT'
            job_params['mailuser'] = self.email
        else:
            job_params['mailtype'] = 'NONE'
            job_params['mailuser'] = ''

        return job_params

    def _submit_job(self, job_name, job_file, job_dir, dependency=None):
        submit = ['sbatch']
        if self.export:
            submit += ['--export', ",".join(self.export)]
        if dependency:
            submit.extend(['-d', 'afterany:' + dependency, '--kill-on-invalid-dep=yes'])
        submit.append(job_file)
        logging.info('Executing %s' % (' '.join(submit)))
        out = subprocess.check_output(submit, cwd=job_dir).decode()
        print out.strip()
        match = re.match(r"Submitted batch job (\d*)", out)
        assert match, "Submitting job with sbatch failed: '{out}'".format(**locals())
        return match.group(1)


class BaselSlurmEnvironment(SlurmEnvironment):
    """Environment for Basel's AI group."""

    DEFAULT_PARTITION = 'infai_1'
    DEFAULT_QOS = 'normal'
    # infai nodes have 61964 MiB and 16 cores => 3872.75 MiB per core
    # (see http://issues.fast-downward.org/issue733).
    DEFAULT_MEMORY_PER_CPU = '3872M'
    DEFAULT_SETUP = (
        'module load Python/2.7.11-goolf-1.7.20\n'
        'PYTHONPATH="%s:$PYTHONPATH"' % tools.get_lab_path())
