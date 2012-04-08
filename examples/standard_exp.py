#! /usr/bin/env python

import os
import platform
from subprocess import call
import sys

from lab.environments import LocalEnvironment, GkiGridEnvironment
from lab.steps import Step

from downward.experiment import DownwardExperiment
from downward.reports.absolute import AbsoluteReport


EXPNAME = 'js-' + os.path.splitext(os.path.basename(sys.argv[0]))[0]
REMOTE_EXPPATH = os.path.join('/home/downward/jendrik/experiments/', EXPNAME)
LOCAL_EXPPATH = os.path.join('/home/jendrik/lab/experiments', EXPNAME)

if platform.node() == 'habakuk':
    EXPPATH = REMOTE_EXPPATH
    REPO = '/home/downward/jendrik/downward'
    ENV = GkiGridEnvironment()
else:
    EXPPATH = LOCAL_EXPPATH
    REPO = '/home/jendrik/projects/Downward/downward'
    ENV = LocalEnvironment()

ATTRIBUTES = ['coverage', 'cost', 'total_time']


class StandardDownwardExperiment(DownwardExperiment):
    def __init__(self, path=EXPPATH, environment=ENV, repo=REPO,
                 combinations=None, limits=None, attributes=None):
        DownwardExperiment.__init__(self, path=path, environment=environment,
                                    repo=repo, combinations=combinations,
                                    limits=limits)

        if attributes is None:
            attributes = ATTRIBUTES

        # Add report steps
        abs_domain_report_file = os.path.join(self.eval_dir, '%s-abs-d.html' % EXPNAME)
        abs_problem_report_file = os.path.join(self.eval_dir, '%s-abs-p.html' % EXPNAME)
        self.add_step(Step('report-abs-d', AbsoluteReport('domain', attributes=attributes),
                                                          self.eval_dir, abs_domain_report_file))
        self.add_step(Step('report-abs-p', AbsoluteReport('problem', attributes=attributes),
                                                          self.eval_dir, abs_problem_report_file))

        # Copy the results
        self.add_step(Step.publish_reports(abs_domain_report_file, abs_problem_report_file))

        # Compress the experiment directory
        self.add_step(Step.zip_exp_dir(self))

        # Copy the results to local directory
        self.add_step(Step('scp', call, ['scp', '-r',
            'downward@habakuk:%s-eval' % REMOTE_EXPPATH, '%s-eval' % LOCAL_EXPPATH]))


def get_exp(suite, configs, combinations=None, limits=None, attributes=None):
    # Test configs on local machine
    if platform.node() != 'habakuk':
        suite = 'gripper:prob01.pddl'

    exp = StandardDownwardExperiment(path=EXPPATH, environment=ENV, repo=REPO,
                                     combinations=combinations, limits=limits,
                                     attributes=attributes)

    exp.add_suite(suite)
    for nick, config in configs:
        exp.add_config(nick, config)
    return exp
