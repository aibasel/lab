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


class StandardDownwardExperiment(DownwardExperiment):
    def __init__(self, path=None, environment=None, repo=None,
                 combinations=None, limits=None, attributes=None, priority=0):
        if path is None:
            path = 'js-' + os.path.splitext(os.path.basename(sys.argv[0]))[0]
        assert not os.path.isabs(path), path
        expname = path

        REMOTE_EXPPATH = os.path.join('/home/downward/jendrik/experiments/', path)
        LOCAL_EXPPATH = os.path.join('/home/jendrik/lab/experiments', path)

        if REMOTE:
            EXPPATH = REMOTE_EXPPATH
            repo = repo or '/home/downward/jendrik/downward'
            environment = environment or GkiGridEnvironment(priority=priority)
        else:
            EXPPATH = LOCAL_EXPPATH
            repo = repo or '/home/jendrik/projects/Downward/downward'
            environment = environment or LocalEnvironment()

        DownwardExperiment.__init__(self, path=EXPPATH, environment=environment,
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
                'downward@habakuk:%s-eval' % REMOTE_EXPPATH, '%s-eval' % LOCAL_EXPPATH]))

            # Copy the zipped experiment directory to local directory
            self.add_step(Step('scp-exp-dir', call, ['scp', '-r',
                'downward@habakuk:%s.tar.gz' % REMOTE_EXPPATH, '%s.tar.gz' % LOCAL_EXPPATH]))

        self.add_step(Step('sendmail', tools.sendmail, 'seipp@informatik.uni-freiburg.de',
                           'seipp@informatik.uni-freiburg.de', 'Exp finished: %s' % self.name,
                           'Path: %s' % self.path))

    def add_suite(self, suite):
        # Use test suite on local machine
        if not REMOTE:
            suite = 'gripper:prob01.pddl'
        DownwardExperiment.add_suite(self, suite)

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
