import math
import os
from subprocess import call

from experiment import Step
import tools

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


class Environment(object):
    def __init__(self):
        self.exp = None

    def write_main_script(self):
        raise NotImplementedError

    def build_linked_resources(self, run):
        """
        Only if we are building an argo experiment, we need to add all linked
        resources to the resources list.
        """
        pass

    @property
    def main_script_file(self):
        raise NotImplementedError


class LocalEnvironment(Environment):
    def __init__(self, processes=1):
        Environment.__init__(self)
        import multiprocessing
        cores = multiprocessing.cpu_count()
        assert processes <= cores, cores
        self.processes = processes

    @property
    def main_script_file(self):
        return self.exp._get_abs_path('run')

    def write_main_script(self):
        dirs = [repr(os.path.relpath(run.dir, self.exp.path)) for run in self.exp.runs]
        replacements = {'DIRS': ',\n'.join(dirs),
                        'PROCESSES': str(self.processes)}

        script = open(os.path.join(tools.DATA_DIR, 'local-job-template.py')).read()
        for orig, new in replacements.items():
            script = script.replace('"""' + orig + '"""', new)

        with open(self.main_script_file, 'w') as file:
            file.write(script)
            # Make run script executable
            os.chmod(file.name, 0755)

    def get_start_exp_step(self):
        return Step('run-exp', call, [self.main_script_file], cwd=self.exp.path)


class GkiGridEnvironment(Environment):
    def __init__(self, queue='opteron_core.q', priority=0):
        Environment.__init__(self)
        self.queue = queue
        assert priority in xrange(-1023, 1024 + 1)
        self.priority = priority
        self.runs_per_task = 1

    @property
    def main_script_file(self):
        return self.exp._get_abs_path(self.exp.name + '.q')

    def write_main_script(self):
        num_tasks = math.ceil(len(self.exp.runs) / float(self.runs_per_task))
        job_params = {
            'logfile': self.exp.name + '.log',
            'errfile': self.exp.name + '.err',
            'num_tasks': num_tasks,
            'queue': self.queue,
            'priority': self.priority,
        }
        template_file = os.path.join(tools.DATA_DIR, 'gkigrid-job-header-template')
        script_template = open(template_file).read()
        script = script_template % job_params

        script += '\n'

        run_groups = tools.divide_list(self.exp.runs, self.runs_per_task)

        for task_id, run_group in enumerate(run_groups, start=1):
            script += 'if [[ $SGE_TASK_ID == %s ]]; then\n' % task_id
            for run in run_group:
                # Change into the run dir
                script += '  cd %s\n' % os.path.relpath(run.dir, self.exp.path)
                script += '  ./run\n'
            script += 'fi\n'

        with open(self.main_script_file, 'w') as file:
            file.write(script)

    def get_start_exp_step(self):
        return Step('start', call, ['qsub', self.main_script_file], cwd=self.exp.path)
