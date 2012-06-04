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

import logging
import math
import os
import sys

from lab import tools
from lab.steps import Sequence

GRID_STEPS_DIR = os.path.join(tools.USER_DIR, 'grid-steps')


class Environment(object):
    def __init__(self):
        self.exp = None
        self.main_script_file = 'run'

    def write_main_script(self):
        raise NotImplementedError

    def get_env(self):
        env = os.environ.copy()
        env['PYTHONPATH'] = self.exp.path
        return env

    def build_linked_resources(self, run):
        """
        Only if we are building an argo experiment, we need to add all linked
        resources to the resources list.
        """
        pass

    def run_steps(self):
        raise NotImplementedError


class LocalEnvironment(Environment):
    def __init__(self, processes=1):
        """
        *processes* must be in the range [1, ..., #CPUs].
        """
        Environment.__init__(self)
        import multiprocessing
        cores = multiprocessing.cpu_count()
        assert processes <= cores, cores
        self.processes = processes

    def write_main_script(self):
        dirs = [repr(os.path.relpath(run.path, self.exp.path))
                for run in self.exp.runs]
        replacements = {'DIRS': ',\n'.join(dirs),
                        'PROCESSES': str(self.processes)}

        script = open(os.path.join(tools.DATA_DIR,
                                   'local-job-template.py')).read()
        for orig, new in replacements.items():
            script = script.replace('"""' + orig + '"""', new)

        self.exp.add_new_file('MAIN_SCRIPT', self.main_script_file, script)

    def start_exp(self):
        tools.run_command(['./' + self.main_script_file], cwd=self.exp.path,
                          env=self.get_env())

    def run_steps(self, steps):
        Sequence.run_steps(steps)


class GkiGridEnvironment(Environment):
    MAX_TASKS = 75000

    def __init__(self, queue='opteron_core.q', priority=0):
        """
        *queue* must be a valid queue name on the GKI Grid.

        *priority* must be in the range [-1023, ..., 0] where 0 is the highest
        priority. If you're a superuser the value can be in the range
        [-1023, ..., 1024].
        """
        Environment.__init__(self)
        self.queue = queue
        assert priority in xrange(-1023, 1024 + 1)
        self.priority = priority
        self.runs_per_task = 1

        # When submitting an experiment job, wait for this job name.
        self.__wait_for_job_name = None
        self._job_name = None

    def write_main_script(self):
        num_tasks = math.ceil(len(self.exp.runs) / float(self.runs_per_task))
        if num_tasks > self.MAX_TASKS:
            logging.critical('You are trying to submit a job with %d tasks, '
                             'but only %d are allowed.' %
                             (num_tasks, self.MAX_TASKS))
        job_params = {
            'name': self.exp.name,
            'logfile': self.exp.name + '.log',
            'errfile': self.exp.name + '.err',
            'num_tasks': num_tasks,
            'queue': self.queue,
            'priority': self.priority,
        }
        template_file = os.path.join(tools.DATA_DIR,
                                     'gkigrid-job-header-template')
        header = open(template_file).read() % job_params + '\n'
        lines = []

        run_groups = tools.divide_list(self.exp.runs, self.runs_per_task)

        for task_id, run_group in enumerate(run_groups, start=1):
            lines.append('if [[ $SGE_TASK_ID == %s ]]; then' % task_id)
            for run in run_group:
                # Change into the run dir
                lines.append('  cd %s' % os.path.relpath(run.path,
                                                         self.exp.path))
                lines.append('  ./run')
            lines.append('fi')

        script = header + '\n'.join(lines)

        filename = self.exp._get_abs_path(self.main_script_file)
        with open(filename, 'w') as file:
            logging.debug('Writing file "%s"' % filename)
            file.write(script)

    def start_exp(self):
        submitted_file = os.path.join(self.exp.path, 'submitted')
        if os.path.exists(submitted_file):
            tools.confirm('The file "%s" already exists so it seems the '
                          'experiment has already been submitted. Are you '
                          'sure you want to submit it again?' % submitted_file)
        submit = ['qsub']
        if self.__wait_for_job_name:
            submit.extend(['-hold_jid', self.__wait_for_job_name])
        if self._job_name:
            # The name set in the job file will be ignored.
            submit.extend(['-N', self._job_name])
        submit.append(self.main_script_file)
        tools.run_command(submit, cwd=self.exp.path, env=self.get_env())
        # Write "submitted" file.
        with open(submitted_file, 'w') as f:
            f.write('This file is created when the experiment is submitted to '
                    'the queue.')

    def _get_job_name(self, step):
        return '%s-%02d-%s' % (self.exp.name, self.exp.steps.index(step) + 1,
                               step.name)

    def _get_job_header(self, step):
        job_params = {
            'name': self._get_job_name(step),
            'logfile': 'driver.log',
            'errfile': 'driver.err',
            'num_tasks': 1,
            'queue': self.queue,
            'priority': self.priority,
        }
        template_file = os.path.join(tools.DATA_DIR,
                                     'gkigrid-job-header-template')
        return open(template_file).read() % job_params

    def _get_job(self, step):
        # Abort if one step fails.
        return """\
%(job_header)s
if [ -s "%(stderr)s" ]; then
    echo "There was output on stderr. Please check %(stderr)s. Aborting."
    exit 1
fi

cd %(exp_script_dir)s
./%(script)s %(step_name)s
""" % {'exp_script_dir': os.path.dirname(os.path.abspath(sys.argv[0])),
       'script': self.exp._script, 'step_name': step.name,
       'stderr': 'driver.err',
       'job_header': self._get_job_header(step)}

    def run_steps(self, steps):
        if 'xeon' in self.queue:
            logging.critical('Experiments must be run stepwise on xeon, '
                             'because mercurial is missing there.')
        job_dir = os.path.join(GRID_STEPS_DIR, self.exp.name)
        tools.overwrite_dir(job_dir)
        # Build the job files before submitting the other jobs.
        logging.info('Building job scripts')
        for step in steps:
            if step._funcname == 'build':
                script_step = step.copy()
                script_step.kwargs['only_main_script'] = True
                script_step()

        prev_job_name = None
        for number, step in enumerate(self.exp.steps, start=1):
            job_name = self._get_job_name(step)
            # We cannot submit a job from within the grid, so we submit it
            # directly.
            if step._funcname == 'run':
                self.__wait_for_job_name = prev_job_name
                self._job_name = job_name
                step()
            else:
                step_file = os.path.join(job_dir, job_name)
                with open(step_file, 'w') as f:
                    f.write(self._get_job(step))
                submit = ['qsub']
                if prev_job_name:
                    submit.extend(['-hold_jid', prev_job_name])
                submit.append(job_name)
                tools.run_command(submit, cwd=job_dir)
            prev_job_name = job_name
