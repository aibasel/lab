#! /usr/bin/env python

import os
import platform

from lab.steps import Step
from lab.fetcher import Fetcher
from lab.reports import filter

from downward.checkouts import Translator, Preprocessor, Planner
from downward.reports.absolute import AbsoluteReport
from downward.reports.relative import RelativeReport
from downward.reports import scatter

from examples import standard_exp

NEW_BRANCH = 'issue22'
VERSION = '2.7.3'
SHORTVERSION = VERSION[:3]
CONFIG_MODULE = '/home/jendrik/projects/Downward/portotune/tuned_configs_sat.py'
CONFIGS = [
    ('mas1', ['--search',
           'astar(merge_and_shrink(merge_strategy=merge_linear_reverse_level,shrink_strategy=shrink_bisimulation(max_states=infinity,threshold=1,greedy=true,group_by_h=false)))']),
    ('mas2', ['--search',
           'astar(merge_and_shrink(merge_strategy=merge_linear_reverse_level,shrink_strategy=shrink_bisimulation(max_states=200000,greedy=false,group_by_h=true)))']),
    ('bjolp', ['--search',
           'astar(lmcount(lm_merged([lm_rhw(),lm_hm(m=1)]),admissible=true),mpd=true)']),
    ('lmcut', ['--search',
           'astar(lmcut())']),
    ]
IPC_CONFIGS = ['seq-sat-fd-autotune-1', 'seq-sat-fd-autotune-2',
               'seq-sat-lama-2011', 'seq-opt-fd-autotune', 'seq-opt-selmax']
ATTRIBUTES = ['translator_time_*', 'translator_peak_memory', 'coverage',
              'expansions', 'total_time', 'search_time', 'cost']
LIMITS = {'search_time': 900}

if standard_exp.REMOTE:
    REPO = '/home/downward/jendrik/downward'
    TRANSLATOR_REPO = '/home/downward/jendrik/jendrik-downward'
    PYTHON = '/home/downward/jendrik/Python-%s/installed/usr/local/bin/python%s' % (VERSION, SHORTVERSION)
else:
    REPO = '/home/jendrik/projects/Downward/downward'
    TRANSLATOR_REPO = '/home/jendrik/projects/Downward/jendrik-downward'
    PYTHON = '/usr/bin/python%s' % SHORTVERSION

COMBOS = [
    (Translator(repo=REPO), Preprocessor(repo=REPO), Planner(repo=REPO)),
    (Translator(repo=TRANSLATOR_REPO, rev=NEW_BRANCH, dest=NEW_BRANCH),
     Preprocessor(repo=REPO),
     Planner(repo=REPO)),
]

class TranslatorExperiment(standard_exp.StandardDownwardExperiment):
    def _make_preprocess_runs(self):
        standard_exp.StandardDownwardExperiment._make_preprocess_runs(self)
        for run in self.runs:
            # Use different python interpreter.
            args, kwargs = run.commands['translate']
            args.insert(0, PYTHON)
            run.commands['translate'] = (args, kwargs)

            args, kwargs = run.commands['print-python-version']
            args[0] = PYTHON
            run.commands['print-python-version'] = (args, kwargs)

exp = TranslatorExperiment(path='js-%s' % NEW_BRANCH, combinations=COMBOS,
                           attributes=ATTRIBUTES)
exp.add_suite('ALL')
for nick, config in CONFIGS:
    exp.add_config(nick, config)
for name in IPC_CONFIGS:
    exp.add_ipc_config(name)
exp.add_config_module(CONFIG_MODULE)

def rename(run):
    # Group the same configs next to each other.
    config = run['config']
    # Move the branch name from the beginning to the end of the config name.
    if config.startswith(NEW_BRANCH) and not config.endswith(NEW_BRANCH):
        config = config.replace('%s-WORK-WORK' % NEW_BRANCH, 'WORK') + '-' + NEW_BRANCH
    run['config'] = config
    return run
exp.steps.insert(6, Step('rename-configs', filter.FilterReport(filter=rename), exp.eval_dir,
                         os.path.join(exp.eval_dir, 'properties')))

def add_scatter_plot_steps():
    for attribute in [u'translator_peak_memory',
                      u'translator_time_building_dictionary_for_full_mutex_groups',
                      u'translator_time_building_mutex_information',
                      u'translator_time_building_strips_to_sas_dictionary',
                      u'translator_time_building_translation_key',
                      u'translator_time_checking_invariant_weight',
                      u'translator_time_choosing_groups',
                      u'translator_time_collecting_mutex_groups',
                      u'translator_time_completing_instantiation',
                      u'translator_time_computing_fact_groups',
                      u'translator_time_computing_model',
                      u'translator_time_detecting_unreachable_propositions',
                      u'translator_time_done',
                      u'translator_time_finding_invariants',
                      u'translator_time_generating_datalog_program',
                      u'translator_time_instantiating',
                      u'translator_time_instantiating_groups',
                      u'translator_time_normalizing_datalog_program',
                      u'translator_time_normalizing_task',
                      u'translator_time_parsing',
                      u'translator_time_preparing_model',
                      u'translator_time_processing_axioms',
                      u'translator_time_simplifying_axioms',
                      u'translator_time_translating_task',
                      u'translator_time_writing_output',
                    ]:
        exp.add_step(Step('scatter-%s' % attribute, scatter.ScatterPlotReport(attributes=[attribute]),
                          exp.eval_dir, os.path.join(exp.eval_dir, '%s.png' % attribute)))

try:
    import matplotlib
    add_scatter_plot_steps()
except ImportError:
    pass

exp()
