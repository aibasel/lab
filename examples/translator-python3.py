#! /usr/bin/env python

import os
import platform

from lab.steps import Step
from lab.fetcher import Fetcher
from downward.checkouts import Translator, Preprocessor, Planner
from downward.reports.absolute import AbsoluteReport
from downward.reports.relative import RelativeReport

from examples import standard_exp

if platform.node() == 'habakuk':
    REPO = '/home/downward/jendrik/downward'
    TRANSLATOR_REPO = '/home/downward/jendrik/jendrik-downward'
else:
    REPO = '/home/jendrik/projects/Downward/downward'
    TRANSLATOR_REPO = '/home/jendrik/projects/Downward/jendrik-downward'

COMBOS = [
    (Translator(repo=REPO),
     Preprocessor(repo=REPO),
     Planner(repo=REPO)),
    (Translator(repo=TRANSLATOR_REPO, rev="issue329", dest="issue329"),
     Preprocessor(repo=REPO),
     Planner(repo=REPO)),
]

CONFIGS = []
ATTRIBUTES = []

exp = standard_exp.get_exp('ALL', CONFIGS, combinations=COMBOS, attributes=ATTRIBUTES)
for step_name in ['fetch-preprocess-results', 'build-search-exp',
                  'run-search-exp', 'fetch-search-results']:
    exp.steps.remove_step(step_name)

# Use normal eval-dir for preprocess results.
exp.steps.insert(2, Step('fetch-preprocess-results', Fetcher(), exp.preprocess_exp_path, exp.eval_dir))

exp()
