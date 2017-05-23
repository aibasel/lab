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
import math
import multiprocessing
import os
import pkgutil
import random
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
        dispatcher_content = pkgutil.get_data('lab', 'data/run-dispatcher.py').replace(
            '"""TASK_ORDER"""', str(task_order))
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
        script = pkgutil.get_data('lab', 'data/local-job-template.py')
        replacements = {
            'NUM_TASKS': str(len(self.exp.runs)),
            'PROCESSES': str(self.processes)}
        for orig, new in replacements.items():
            script = script.replace('"""' + orig + '"""', new)

        self.exp.add_new_file('', self.EXP_RUN_SCRIPT, script, permissions=0o755)

    def start_runs(self):
        tools.run_command([sys.executable, self.EXP_RUN_SCRIPT], cwd=self.exp.path)

    def run_steps(self, steps):
        for step in steps:
            step()


class OracleGridEngineEnvironment(Environment):
    """Abstract base class for grid environments."""

    DEFAULT_QUEUE = None             # must be overridden in derived classes
    TEMPLATE_FILE = 'grid-job-header-template'  # can be overridden in derived classes
    MAX_TASKS = float('inf')         # can be overridden in derived classes
    DEFAULT_PRIORITY = 0             # can be overridden in derived classes
    HOST_RESTRICTIONS = {}           # can be overridden in derived classes
    DEFAULT_HOST_RESTRICTION = ""    # can be overridden in derived classes

    def __init__(self, queue=None, priority=None, host_restriction=None,
                 email=None, extra_options=None, **kwargs):
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

        *queue* must be a valid queue name on the grid.

        *priority* must be in the range [-1023, 0] where 0 is the
        highest priority. If you're a superuser the value can be in the
        range [-1023, 1024].

        If *email* is provided and the steps run on the grid, a message
        will be sent when the last experiment step finishes.

        Use *extra_options* to pass additional options. The
        *extra_options* string may contain newlines. Example that
        allocates 16 cores per run on maia::

            extra_options='#$ -pe smp 16'

        See :py:class:`~lab.environments.Environment` for inherited
        parameters.

        """
        Environment.__init__(self, **kwargs)
        if queue is None:
            queue = self.DEFAULT_QUEUE
        if priority is None:
            priority = self.DEFAULT_PRIORITY
        if host_restriction is None:
            host_restriction = self.DEFAULT_HOST_RESTRICTION

        self.queue = queue
        self.host_spec = self._get_host_spec(host_restriction)
        assert priority in xrange(-1023, 1024 + 1)
        self.priority = priority
        self.runs_per_task = 1
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
        num_runs = int(math.ceil(len(self.exp.runs) / float(self.runs_per_task)))
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

    def _get_job_params(self, step):
        return {
            'errfile': 'driver.err',
            'extra_options': self.extra_options,
            'host_spec': self.host_spec,
            'logfile': 'driver.log',
            'name': self._get_job_name(step),
            'notification': '#$ -m n',
            'num_tasks': self._get_num_tasks(step),
            'priority': self.priority,
            'queue': self.queue,
        }

    def _get_job_header(self, step, is_last):
        job_params = self._get_job_params(step)
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
        return pkgutil.get_data('lab', 'data/' + self.TEMPLATE_FILE) % job_params

    def _get_main_job_body(self):
        params = dict(
            num_tasks=self._get_num_runs(),
            errfile='driver.err',
            exp_path='../' + self.exp.name)
        return pkgutil.get_data('lab', 'data/grid-job-body-template') % params

    def _get_job_body(self, step):
        if is_run_step(step):
            return self._get_main_job_body()
        return 'cd "%(cwd)s"\n"%(python)s" "%(script)s" %(args)s "%(step_name)s"\n' % {
            'cwd': os.getcwd(),
            'python': sys.executable or 'python',
            'script': sys.argv[0],
            'args': ' '.join(repr(arg) for arg in self._get_script_args()),
            'step_name': step.name}

    def _get_job(self, step, is_last):
        return '%s\n\n%s' % (self._get_job_header(step, is_last),
                             self._get_job_body(step))

    def _get_host_spec(self, host_restriction):
        if not host_restriction:
            return '## (not used)'
        else:
            hosts = self.HOST_RESTRICTIONS[host_restriction]
            return '#$ -l hostname="%s"' % '|'.join(hosts)

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

        prev_job_name = None
        for step in steps:
            job_name = self._get_job_name(step)
            tools.write_file(
                os.path.join(job_dir, job_name),
                self._get_job(step, is_last=(step == steps[-1])))
            submit = ['qsub']
            if prev_job_name:
                submit.extend(['-hold_jid', prev_job_name])
            submit.append(job_name)
            tools.run_command(submit, cwd=job_dir)
            prev_job_name = job_name


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
