#! /usr/bin/env python

import os
import platform

from lab.steps import Step
from lab.fetcher import Fetcher
from downward.checkouts import Translator, Preprocessor, Planner
from downward.reports.absolute import AbsoluteReport
from downward.reports.relative import RelativeReport
from downward.reports import scatter

from examples import standard_exp

if platform.node() == 'habakuk':
    REPO = '/home/downward/jendrik/downward'
    TRANSLATOR_REPO = '/home/downward/jendrik/jendrik-downward'
    PYTHON = '/home/downward/jendrik/Python2.7.3/python'
else:
    REPO = '/home/jendrik/projects/Downward/downward'
    TRANSLATOR_REPO = '/home/jendrik/projects/Downward/jendrik-downward'
    PYTHON = '/usr/bin/python2.7'

COMBOS = [
    (Translator(repo=REPO),
     Preprocessor(repo=REPO),
     Planner(repo=REPO)),
    (Translator(repo=TRANSLATOR_REPO, rev="issue329", dest="issue329"),
     Preprocessor(repo=REPO),
     Planner(repo=REPO)),
]

CONFIGS = []
ATTRIBUTES = ['translator_time_*', 'translator_peak_memory']

class TranslatorExperiment(standard_exp.StandardDownwardExperiment):
    def _make_preprocess_runs(self):
        standard_exp.StandardDownwardExperiment._make_preprocess_runs(self)
        for run in self.runs:
            # Use different python interpreter.
            args, kwargs = run.commands['translate']
            args.insert(0, PYTHON)
            run.commands['translate'] = (args, kwargs)

exp = TranslatorExperiment(path=standard_exp.EXPPATH + '-2', combinations=COMBOS,
                           attributes=ATTRIBUTES)
exp.add_suite('ALL')

for step_name in ['fetch-preprocess-results', 'build-search-exp',
                  'run-search-exp', 'fetch-search-results']:
    exp.steps.remove_step(step_name)

# Use normal eval-dir for preprocess results.
exp.steps.insert(2, Step('fetch-preprocess-results', Fetcher(), exp.preprocess_exp_path, exp.eval_dir))

for attribute in [u'translator_time_building_dictionary_for_full_mutex_groups',
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
    pass
    #exp.add_step(Step('scatter-%s' % attribute, scatter.ScatterPlotReport(attributes=[attribute]),
    #                  exp.eval_dir, os.path.join(exp.eval_dir, '%s.png' % attribute)))

exp()
