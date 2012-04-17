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

import math
import os

from lab import tools


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


class GkiGridEnvironment(Environment):
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

    def write_main_script(self):
        num_tasks = math.ceil(len(self.exp.runs) / float(self.runs_per_task))
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
        self.exp.add_new_file('MAIN_SCRIPT', self.main_script_file, script)

    def start_exp(self):
        submitted_file = os.path.join(self.exp.path, 'submitted')
        if os.path.exists(submitted_file):
            tools.confirm('The file %s exists. It seems the experiment has '
                          'already been submitted. Are you sure you want to '
                          'submit it again?' % submitted_file)
        tools.run_command(['qsub', self.main_script_file], cwd=self.exp.path,
                          env=self.get_env())
        # Touch "submitted" file.
        with open(submitted_file, 'w') as f:
            f.write('This file is created when the experiment is submitted to '
                    'the queue.')
