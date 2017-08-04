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
import os
import re
import pkgutil
import subprocess
import sys
import math

from lab.environments import Environment
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

def get_lab_path():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SlurmEnvironment(Environment):
    """Abstract base class for slurm grid environments."""

    DEFAULT_PARTITION = None         # must be overridden in derived classes
    DEFAULT_QOS = None               # must be overridden in derived classes
    ENVIRONMENT_SETUP = ''           # can be overridden in derived classes
    DEFAULT_PRIORITY = 'TOP'         # can be overridden in derived classes
    DEFAULT_MODULES = []             # can be overridden in derived classes
    TEMPLATE_FILE = 'slurm-job-header-template'  # can be overridden in derived classes

    def __init__(self, partition=None, qos=None, priority=None,
                 email=None, export=['PATH'],
                 extra_options=None, **kwargs):
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

        *partition* must be a valid slurm partition name on the grid.

        *qos* must be a valid slurm qos name on the grid.

        *priority* must be in the range [-1023, 0] where 0 is the
        highest priority. If you're a superuser the value can be in the
        range [-1023, 1024]. "TOP" is an alias for the highest allowed
        priority.

        If *email* is provided and the steps run on the grid, a message
        will be sent when the last experiment step finishes.

        Use *export* to specify a list of environment variables that
        should be exported from the login node to the compute nodes.

        Use *extra_options* to pass additional options. The
        *extra_options* string may contain newlines.

        See :py:class:`~lab.environments.Environment` for inherited
        parameters.

        """
        Environment.__init__(self, **kwargs)
        if partition is None:
            partition = self.DEFAULT_PARTITION
        if qos is None:
            qos = self.DEFAULT_QOS
        if priority is None:
            priority = self.DEFAULT_PRIORITY

        self.partition = partition
        self.qos = qos
        assert priority in range(-1023, 1024 + 1) + ['TOP']
        self.priority = priority
        self.runs_per_task = 1
        self.email = email
        self.export = export
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
            'logfile': 'driver.log',
            'name': self._get_job_name(step),
            'mailuser': '',
            'mailtype': 'NONE',
            'num_tasks': self._get_num_tasks(step),
            'priority': self.priority,
            'partition': self.partition,
            'qos': self.qos,
            'environment_setup': self.ENVIRONMENT_SETUP,
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
                job_params['mailtype'] = 'ALL'
                job_params['mailuser'] = self.email
        return pkgutil.get_data('lab', 'data/' + self.TEMPLATE_FILE) % job_params

    def _get_main_job_body(self):
        params = dict(
            num_tasks=self._get_num_runs(),
            errfile='driver.err',
            exp_path='../' + self.exp.name)
        return pkgutil.get_data('lab', 'data/slurm-job-body-template') % params

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
        return '%s\n\n%s\n%s' % (self._get_job_header(step, is_last),
                                 self._get_job_body(step))

    def write_main_script(self):
        # The main script is written by the run_steps() method.
        self._write_run_dispatcher()

    def _submit_slurm_job(self, filename, cwd, dependency=None):
        submit = ['sbatch']
        if self.export:
            submit += ['--export', ",".join(self.export)]
        if dependency:
            submit.extend(['-d', 'afterany:' + dependency, '--kill-on-invalid-dep=yes'])
        submit.append(filename)
        # TODO: this duplicates some code from tools.run_command but we need the output
        logging.info('Executing %s' % (' '.join(submit)))
        out = subprocess.check_output(submit, cwd=cwd)
        print out
        match = re.match(r"Submitted batch job (\d*)", out.decode())
        assert match, "Submitting job with sbatch failed: '%s'" % out.decode()
        return match.group(1)

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
            prev_job_id = self._submit_slurm_job(job_file, job_dir, dependency=prev_job_id)


class BaselSlurmEnvironment(SlurmEnvironment):
    """Environment for Basel's AI group."""

    # TODO: update once we have our own nodes set up
    DEFAULT_PARTITION = 'uni'
    DEFAULT_QOS = 'uni-1week'

    ENVIRONMENT_SETUP = (
        'module load Python/2.7.11-goolf-1.7.20\n'
        'PYTHONPATH="%s:$PYTHONPATH"' % get_lab_path())
