#! /usr/bin/env python

import os

from lab.steps import Step
from lab.fetcher import Fetcher
from lab.reports import filter

from downward.checkouts import Translator, Preprocessor, Planner
from downward.reports.absolute import AbsoluteReport
from downward.reports.relative import RelativeReport
from downward.reports import scatter

from examples import standard_exp

INITIALS = 'js'
NEW_BRANCH = 'issue22'
VERSION = '2.7.3'
SHORTVERSION = VERSION[:3]
PREPROCESS_ONLY = True

PRIORITY = -3
ATTRIBUTES = ['translator_time_*', 'translator_peak_memory']
if not PREPROCESS_ONLY:
    ATTRIBUTES.extend(['coverage', 'expansions', 'total_time', 'search_time',
                       'cost', 'score_*'])
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


def rename(run):
    # Group the same configs next to each other.
    config = run['config']
    # Move the branch name from the beginning to the end of the config name.
    if config.startswith(NEW_BRANCH) and not config.endswith(NEW_BRANCH):
        config = config.replace('%s-WORK-WORK' % NEW_BRANCH, 'WORK') + '-' + NEW_BRANCH
    run['config'] = config
    return run

class TranslatorExperiment(standard_exp.StandardDownwardExperiment):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('priority', PRIORITY)
        standard_exp.StandardDownwardExperiment.__init__(self, *args, **kwargs)

        self.set_path_to_python(PYTHON)

        if PREPROCESS_ONLY:
            for step_name in ['fetch-preprocess-results', 'build-search-exp',
                  'run-search-exp', 'fetch-search-results']:
                self.steps.remove_step(step_name)

            # Use normal eval-dir for preprocess results.
            self.steps.insert(2, Step('fetch-preprocess-results', Fetcher(),
                                      self.preprocess_exp_path, self.eval_dir))

        else:
            self.steps.insert(6, Step('rename-configs', filter.FilterReport(filter=rename),
                                      self.eval_dir, os.path.join(self.eval_dir, 'properties')))

        try:
            import matplotlib
            self.add_scatter_plot_steps()
        except ImportError:
            pass

    def add_scatter_plot_steps(self):
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
            self.add_step(Step('scatter-%s' % attribute, scatter.ScatterPlotReport(attributes=[attribute]),
                               self.eval_dir, os.path.join(self.eval_dir, '%s.png' % attribute)))


def get_exp(track, suite, configs, ipc_configs):
    exp = TranslatorExperiment(path='-'.join([INITIALS, NEW_BRANCH, track]), combinations=COMBOS,
                               attributes=ATTRIBUTES, limits=LIMITS)
    exp.add_suite(suite)
    for nick, config in configs:
        exp.add_config(nick, config)
    for name in ipc_configs:
        exp.add_ipc_config(name)

    return exp
