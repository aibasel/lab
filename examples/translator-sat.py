#! /usr/bin/env python

import standard_exp
import translator


SUITE = 'SATISFICING_WITH_IPC11'
CONFIGS = [('blind', ['--search', 'astar(blind())'])]
IPC_CONFIGS = ['seq-sat-fd-autotune-1', 'seq-sat-fd-autotune-2', 'seq-sat-lama-2011']

if standard_exp.REMOTE:
    CONFIG_MODULE = '/home/seipp/projects/portotune/tuned_configs_sat.py'
else:
    CONFIG_MODULE = '/home/jendrik/projects/Downward/portotune/tuned_configs_sat.py'

exp = translator.get_exp('sat', SUITE, CONFIGS, IPC_CONFIGS)
exp.add_config_module(CONFIG_MODULE)
exp()
