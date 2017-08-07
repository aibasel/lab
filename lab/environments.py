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
    return (
        step.name == 'build' and step._funcname == 'build' and
        not step.args and not step.kwargs)


def is_run_step(step):
    """Return true iff the given step is the "run" step."""
    return (
        step.name == 'run' and step._funcname == 'start_runs' and
        not step.args and not step.kwargs)


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

    def _write_run_dispatcher(self):
        task_order = range(1, len(self.exp.runs) + 1)
        if self.randomize_task_order:
            random.shuffle(task_order)
        dispatcher_content = tools.fill_template(
            'run-dispatcher.py',
            task_order=str(task_order))
        self.exp.add_new_file(
            '', 'run-dispatcher.py', dispatcher_content, permissions=0o755)

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
        self._write_run_dispatcher()
        script = tools.fill_template(
            'local-job.py',
            num_tasks=len(self.exp.runs),
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

        If the main experiment step ('run') is part of the selected
        steps, the selected steps are submitted to the grid engine.
        Otherwise, the selected steps are run locally.

        .. note::

            For correct sequential execution, this class writes job
            files to the experiment directory and makes them depend on
            one another. The driver.log and driver.err files in this
            directory can be inspected if something goes wrong. Since
            the job files call the experiment script during execution,
            it mustn't be changed during the experiment.

        If *email* is provided and the steps run on the grid, a message
        will be sent when the last experiment step finishes.

        Use *extra_options* to pass additional options. The
        *extra_options* string may contain newlines. Example that
        allocates 16 cores per run with OGE::

            extra_options='#$ -pe smp 16'

        Example that runs each task on its own node with Slurm::

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

    def _get_script_args(self):
        """
        Retrieve additional commandline parameters given when the experiment
        is called by the user and pass them again when the step is called by
        the grid.
        """
        # Remove step names from the back of the commandline to avoid deleting
        # custom args by accident.
        commandline = list(reversed(sys.argv[1:]))
        if '--all' in commandline:
            commandline.remove('--all')
        for step_name in self.exp.args.steps:
            commandline.remove(step_name)
        return list(reversed(commandline))

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
            num_tasks=self._get_num_runs(),
            errfile='driver.err',
            exp_path='../' + self.exp.name)

    def _get_step_job_body(self, step):
        return tools.fill_template(
            self.STEP_JOB_BODY_TEMPLATE_FILE,
            cwd=os.getcwd(),
            python=sys.executable or 'python',
            script=sys.argv[0],
            args=' '.join(repr(arg) for arg in self._get_script_args()),
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
        self._write_run_dispatcher()

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


class OracleGridEngineEnvironment(GridEnvironment):
    """Abstract base class for grid environments using OGE."""
    # Must be overridden in derived classes.
    DEFAULT_QUEUE = None

    # Can be overridden in derived classes.
    JOB_HEADER_TEMPLATE_FILE = 'oge-job-header'
    RUN_JOB_BODY_TEMPLATE_FILE = 'oge-run-job-body'
    STEP_JOB_BODY_TEMPLATE_FILE = 'oge-step-job-body'
    DEFAULT_PRIORITY = 0
    HOST_RESTRICTIONS = {}
    DEFAULT_HOST_RESTRICTION = ""

    def __init__(self, queue=None, priority=None, host_restriction=None, **kwargs):
        """
        *queue* must be a valid queue name on the grid.

        *priority* must be in the range [-1023, 0] where 0 is the
        highest priority. If you're a superuser the value can be in the
        range [-1023, 1024].

        See :py:class:`~lab.environments.GridEnvironment` for inherited
        parameters.

        """
        GridEnvironment.__init__(self, **kwargs)

        if queue is None:
            queue = self.DEFAULT_QUEUE
        if priority is None:
            priority = self.DEFAULT_PRIORITY
        if host_restriction is None:
            host_restriction = self.DEFAULT_HOST_RESTRICTION

        self.queue = queue
        self.priority = priority
        assert self.priority in xrange(-1023, 1024 + 1)
        self.host_spec = self._get_host_spec(host_restriction)

    def _get_job_params(self, step, is_last):
        job_params = GridEnvironment._get_job_params(self, step, is_last)
        job_params['priority'] = self.priority
        job_params['queue'] = self.queue
        job_params['host_spec'] = self.host_spec
        job_params['notification'] = '#$ -m n'
        if is_last and self.email:
            if is_run_step(step):
                logging.warning(
                    "The cluster sends mails per run, not per step."
                    " Since the last of the submitted steps would send"
                    " too many mails, we disable the notification."
                    " We recommend submitting the 'run' step together"
                    " with the 'fetch' step.")
            else:
                job_params['notification'] = '#$ -M %s\n#$ -m e' % self.email

        return job_params

    def _get_host_spec(self, host_restriction):
        if not host_restriction:
            return '## (not used)'
        else:
            hosts = self.HOST_RESTRICTIONS[host_restriction]
            return '#$ -l hostname="%s"' % '|'.join(hosts)

    def _submit_job(self, job_name, job_file, job_dir, dependency=None):
        submit = ['qsub']
        if dependency:
            submit.extend(['-hold_jid', dependency])
        submit.append(job_file)
        tools.run_command(submit, cwd=job_dir)
        return job_name


class SlurmEnvironment(GridEnvironment):
    """Abstract base class for slurm grid environments."""
    # Must be overridden in derived classes.
    DEFAULT_PARTITION = None
    DEFAULT_QOS = None

    # Can be overridden in derived classes.
    JOB_HEADER_TEMPLATE_FILE = 'slurm-job-header'
    RUN_JOB_BODY_TEMPLATE_FILE = 'slurm-run-job-body'
    STEP_JOB_BODY_TEMPLATE_FILE = 'slurm-step-job-body'
    ENVIRONMENT_SETUP = ''
    DEFAULT_PRIORITY = 0

    def __init__(self, partition=None, qos=None, priority=None,
                 export=['PATH'], **kwargs):
        """

        *partition* must be a valid slurm partition name on the grid.

        *qos* must be a valid slurm qos name on the grid.

        *priority* must be in the range [-2147483645, 0] where 0 is the
        highest priority. If you're a superuser the value can be in the
        range [-2147483645, 2147483645].

        Use *export* to specify a list of environment variables that
        should be exported from the login node to the compute nodes.

        See :py:class:`~lab.environments.GridEnvironment` for inherited
        parameters.

        """
        GridEnvironment.__init__(self, **kwargs)

        if partition is None:
            partition = self.DEFAULT_PARTITION
        if qos is None:
            qos = self.DEFAULT_QOS
        if priority is None:
            priority = self.DEFAULT_PRIORITY
        assert -2147483645 <= priority <= 2147483645

        self.partition = partition
        self.qos = qos
        self.export = export
        self.nice = -priority

    def _get_job_params(self, step, is_last):
        job_params = GridEnvironment._get_job_params(self, step, is_last)

        job_params['partition'] = self.partition
        job_params['qos'] = self.qos
        job_params['nice'] = self.nice
        job_params['environment_setup'] = self.ENVIRONMENT_SETUP

        if is_last and self.email:
            job_params['mailtype'] = 'ALL'
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
        # TODO: this duplicates some code from tools.run_command but we need the output
        logging.info('Executing %s' % (' '.join(submit)))
        out = subprocess.check_output(submit, cwd=job_dir)
        print out
        match = re.match(r"Submitted batch job (\d*)", out.decode())
        assert match, "Submitting job with sbatch failed: '%s'" % out.decode()
        return match.group(1)


class GkiGridEnvironment(OracleGridEngineEnvironment):
    """Environment for Freiburg's AI group."""

    DEFAULT_QUEUE = 'opteron_core.q'
    MAX_TASKS = 75000

    def run_steps(self, steps):
        if 'xeon' in self.queue:
            logging.critical('Experiments must be run stepwise on xeon, '
                             'because mercurial is missing there.')
        OracleGridEngineEnvironment.run_steps(self, steps)


def _host_range(prefix, from_num, to_num):
    return ['%s%02d*' % (prefix, num) for num in xrange(from_num, to_num + 1)]


class MaiaEnvironment(OracleGridEngineEnvironment):
    """Environment for Basel's AI group."""

    DEFAULT_QUEUE = '"all.q@ase*"'
    DEFAULT_HOST_RESTRICTION = ''

    # Note: the hosts in the following host restrictions are part of the
    # queue 'all.q' and not part of the default queue '"all.q@ase*"'.
    # Use them like this:
    # MaiaEnvironment(queue='all.q', host_restrictions='maia-six')
    HOST_RESTRICTIONS = {
        'maia-quad': _host_range('uni', 1, 32) + _host_range('ugi', 1, 8),
        'maia-six': _host_range('uni', 33, 72),
    }


class BaselSlurmEnvironment(SlurmEnvironment):
    """Environment for Basel's AI group."""

    # TODO: update once we have our own nodes set up
    DEFAULT_PARTITION = 'uni'
    DEFAULT_QOS = 'uni-1week'

    ENVIRONMENT_SETUP = (
        'module load Python/2.7.11-goolf-1.7.20\n'
        'PYTHONPATH="%s:$PYTHONPATH"' % tools.get_lab_path())
