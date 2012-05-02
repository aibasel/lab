#! /usr/bin/env python

import translator


SUITE = 'OPTIMAL_WITH_IPC11'
CONFIGS = [
    ('mas1', ['--search',
           'astar(merge_and_shrink(merge_strategy=merge_linear_reverse_level,shrink_strategy=shrink_bisimulation(max_states=infinity,threshold=1,greedy=true,group_by_h=false)))']),
    ('mas2', ['--search',
           'astar(merge_and_shrink(merge_strategy=merge_linear_reverse_level,shrink_strategy=shrink_bisimulation(max_states=200000,greedy=false,group_by_h=true)))']),
    ('bjolp', ['--search',
           'astar(lmcount(lm_merged([lm_rhw(),lm_hm(m=1)]),admissible=true),mpd=true)']),
    ('lmcut', ['--search',
           'astar(lmcut())']),
    ('blind', ['--search',
           'astar(blind())']),
    ]
IPC_CONFIGS = ['seq-opt-fd-autotune', 'seq-opt-selmax']

exp = translator.get_exp('opt', SUITE, CONFIGS, IPC_CONFIGS)
exp()
