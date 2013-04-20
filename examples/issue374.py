#! /usr/bin/env python

import os

from lab.environments import LocalEnvironment

from downward.experiments.comparerevisions import CompareRevisionsExperiment


BRANCH = 'issue374'
REPO = '/path/to/fast-downward/repo'
EXPPATH = os.path.join('/tmp', 'experiments', BRANCH)
ENV = LocalEnvironment(processes=2)

# Use custom configuration.
exp = CompareRevisionsExperiment(EXPPATH, REPO, 'opt', BRANCH,
                                 use_core_configs=False,
                                 use_ipc_configs=False,
                                 use_extended_configs=False,
                                 environment=ENV,
                                 limits={'search_time': 10})
exp.add_config('seq_sat_lama_2011', ['ipc', 'seq-sat-lama-2011'])

# Use custom suite.
exp.suites = ['grid:prob01.pddl', 'logistics98:prob01.pddl']

exp()
