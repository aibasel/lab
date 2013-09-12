#! /usr/bin/env python

import os
import platform
import shutil
from subprocess import call
import sys

from lab.environments import LocalEnvironment, MaiaEnvironment
from lab.steps import Step
from lab import tools

from downward.experiment import DownwardExperiment
from downward.reports.absolute import AbsoluteReport


NODE = platform.node()
REMOTE = NODE.startswith('gkigrid') or NODE.endswith('cluster') or NODE in ['habakuk', 'turtur']
SCP_LOGIN = 'seipp@maia'
ATTRIBUTES = ['coverage', 'cost', 'total_time']

REMOTE_EXPS = os.path.expanduser('/infai/seipp/experiments/')
LOCAL_EXPS = os.path.expanduser('/home/jendrik/lab/experiments/')

REMOTE_REPO = os.path.expanduser('/infai/seipp/projects/downward')
LOCAL_REPO = os.path.expanduser('/home/jendrik/projects/Downward/downward')

REMOTE_PYTHON = os.path.expanduser('~/bin/python/2.7.3/usr/local/bin/python')
LOCAL_PYTHON = 'python2.7'

if REMOTE:
    EXPS = REMOTE_EXPS
    REPO = REMOTE_REPO
    PYTHON = REMOTE_PYTHON
    CACHE_DIR = os.path.expanduser('~/lab/')
else:
    EXPS = LOCAL_EXPS
    REPO = LOCAL_REPO
    PYTHON = LOCAL_PYTHON
    CACHE_DIR = os.path.expanduser('~/lab/')


class StandardDownwardExperiment(DownwardExperiment):
    def __init__(self, path=None, repo=None, environment=None,
                 combinations=None, limits=None, attributes=None, priority=0,
                 queue=None, processes=2, email=None, cache_dir=CACHE_DIR, **kwargs):
        if path is None:
            path = os.path.splitext(os.path.basename(sys.argv[0]))[0]

        expname = os.path.basename(path)

        remote_exppath = os.path.join(REMOTE_EXPS, path)
        local_exppath = os.path.join(LOCAL_EXPS, path)

        if REMOTE:
            exppath = remote_exppath
            repo = repo or REMOTE_REPO
            environment = environment or MaiaEnvironment(priority=priority,
                                                         queue=queue,
                                                         email=email)
        else:
            exppath = local_exppath
            repo = repo or LOCAL_REPO
            environment = environment or LocalEnvironment(processes=processes)

        DownwardExperiment.__init__(self, path=exppath, environment=environment,
                                    repo=repo, combinations=combinations,
                                    limits=limits, cache_dir=cache_dir, **kwargs)

        self.set_path_to_python(PYTHON)

        if attributes is None:
            attributes = ATTRIBUTES

        # Add report steps
        abs_report_file = os.path.join(self.eval_dir, '%s-abs.html' % expname)
        self.add_report(AbsoluteReport(attributes=attributes, colored=True),
                        name='report-abs', outfile=abs_report_file)

        if REMOTE:
            # Compress the experiment directory
            self.add_step(Step.zip_exp_dir(self))
            self.add_step(Step('zip-eval-dir', call,
                               ['tar', '-cjf', self.name + '-eval.tar.bz2', self.name + '-eval'],
                          cwd=os.path.dirname(self.path)))

        self.add_step(Step.remove_exp_dir(self))
        self.add_step(Step('remove-eval-dir', shutil.rmtree, self.eval_dir, ignore_errors=True))

        if not REMOTE:
            # Copy the results to local directory
            self.add_step(Step('scp-eval-dir', call, [
                'scp', '-r',
                '%s:%s-eval' % (SCP_LOGIN, remote_exppath),
                '%s-eval' % local_exppath]))

            # Copy the results to local directory
            self.add_step(Step('scp-zipped-eval-dir', call, [
                'scp', '-r',
                '%s:%s-eval.tar.bz2' % (SCP_LOGIN, remote_exppath),
                '%s-eval.tar.bz2' % local_exppath]))

            # Copy the zipped experiment directory to local directory
            self.add_step(Step('scp-exp-dir', call, [
                'scp', '-r',
                '%s:%s.tar.bz2' % (SCP_LOGIN, remote_exppath),
                '%s.tar.bz2' % local_exppath]))

        # Unzip the experiment directory
        self.add_step(Step.unzip_exp_dir(self))
        self.add_step(Step('unzip-eval-dir', call,
                           ['tar', '-xjf', self.name + '-eval.tar.bz2'],
                      cwd=os.path.dirname(self.path)))

    def add_config_module(self, path):
        """*path* must be a path to a python module containing only Fast
        Downward configurations in the form

        my_config = ["--search", "astar(lmcut())"]
        """
        module = tools.import_python_file(path)
        configs = [(c, getattr(module, c)) for c in dir(module)
                   if not c.startswith('__')]
        for nick, config in configs:
            self.add_config(nick, config)

    def add_ipc_config(self, ipc_config_name):
        """Example: ::

            exp.add_ipc_config('seq-sat-lama-2011')
        """
        self.add_config(ipc_config_name, ['ipc', ipc_config_name, '--plan-file', 'sas_plan'])


def get_exp(suite, configs, combinations=None, limits=None, attributes=None):
    exp = StandardDownwardExperiment(combinations=combinations, limits=limits,
                                     attributes=attributes)

    exp.add_suite(suite)
    for nick, config in configs:
        exp.add_config(nick, config)
    return exp
