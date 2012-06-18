#! /usr/bin/env python

import os
import platform
import shutil
from subprocess import call
import sys

from lab.environments import LocalEnvironment, GkiGridEnvironment
from lab.steps import Step
from lab import tools

from downward.experiment import DownwardExperiment
from downward.reports.absolute import AbsoluteReport


NODE = platform.node()
REMOTE = NODE.startswith('gkigrid') or NODE == 'habakuk'
ATTRIBUTES = ['coverage', 'cost', 'total_time']

REMOTE_EXPS = '/users/seipp/experiments/'
LOCAL_EXPS = '/home/jendrik/lab/experiments'

REMOTE_REPO = '/home/seipp/projects/downward'
LOCAL_REPO = '/home/jendrik/projects/Downward/downward'

REMOTE_PYTHON = '/home/seipp/bin/Python/Python-2.7.3/installed/usr/local/bin/python'
LOCAL_PYTHON = 'python2.7'

if REMOTE:
    EXPS = REMOTE_EXPS
    REPO = REMOTE_REPO
    PYTHON = REMOTE_PYTHON
else:
    EXPS = LOCAL_EXPS
    REPO = LOCAL_REPO
    PYTHON = LOCAL_PYTHON


class StandardDownwardExperiment(DownwardExperiment):
    def __init__(self, path=None, repo=None, environment=None,
                 combinations=None, limits=None, attributes=None, priority=0):
        if path is None:
            path = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        assert not os.path.isabs(path), path
        expname = path

        remote_exppath = os.path.join(REMOTE_EXPS, path)
        local_exppath = os.path.join(LOCAL_EXPS, path)

        if REMOTE:
            exppath = remote_exppath
            repo = repo or REMOTE_REPO
            environment = environment or GkiGridEnvironment(priority=priority)
        else:
            exppath = local_exppath
            repo = repo or LOCAL_REPO
            environment = environment or LocalEnvironment()

        DownwardExperiment.__init__(self, path=exppath, environment=environment,
                                    repo=repo, combinations=combinations,
                                    limits=limits)

        if attributes is None:
            attributes = ATTRIBUTES

        # Add report steps
        abs_domain_report_file = os.path.join(self.eval_dir, '%s-abs-d.html' % expname)
        abs_problem_report_file = os.path.join(self.eval_dir, '%s-abs-p.html' % expname)
        self.add_step(Step('report-abs-d', AbsoluteReport('domain', attributes=attributes),
                                                          self.eval_dir, abs_domain_report_file))
        self.add_step(Step('report-abs-p', AbsoluteReport('problem', attributes=attributes),
                                                          self.eval_dir, abs_problem_report_file))

        # Copy the results
        self.add_step(Step.publish_reports(abs_domain_report_file, abs_problem_report_file))

        # Compress the experiment directory
        self.add_step(Step.zip_exp_dir(self))

        if not REMOTE:
            # Unzip the experiment directory
            self.add_step(Step.unzip_exp_dir(self))

            # Remove eval dir for a clean scp copy.
            self.add_step(Step('remove-eval-dir', shutil.rmtree, self.eval_dir))

            # Copy the results to local directory
            self.add_step(Step('scp-eval-dir', call, ['scp', '-r',
                'downward@habakuk:%s-eval' % remote_exppath, '%s-eval' % local_exppath]))

            # Copy the zipped experiment directory to local directory
            self.add_step(Step('scp-exp-dir', call, ['scp', '-r',
                'downward@habakuk:%s.tar.gz' % remote_exppath, '%s.tar.gz' % local_exppath]))

        self.add_step(Step('sendmail', tools.sendmail, 'seipp@informatik.uni-freiburg.de',
                           'seipp@informatik.uni-freiburg.de', 'Exp finished: %s' % self.name,
                           'Path: %s' % self.path))

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
