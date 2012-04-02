#! /usr/bin/env python

import platform

from downward.checkouts import Translator, Preprocessor, Planner

from examples import standard_exp

if platform.node() == 'habakuk':
    REPO = '/home/downward/jendrik/downward'
    TRANSLATOR_REPO = '/home/downward/jendrik/jendrik-downward'
else:
    REPO = '/home/jendrik/projects/Downward/downward'
    TRANSLATOR_REPO = '/home/jendrik/projects/Downward/jendrik-downward'

COMBOS = [
    (Translator(repo=REPO, rev="default", dest="default"),
     Preprocessor(repo=REPO, rev="default", dest="default"),
     Planner(repo=REPO, rev="default", dest="default")),
    (Translator(repo=TRANSLATOR_REPO, rev="issue278", dest="issue278"),
     Preprocessor(repo=REPO, rev="default", dest="default"),
     Planner(repo=REPO, rev="default", dest="default")),
]

CONFIGS = [('lama11', ['ipc', 'seq-sat-lama-2011', '--plan-file', 'sas_plan'])]
ATTRIBUTES = []

exp = standard_exp.get_exp('ALL', CONFIGS, combinations=COMBOS, attributes=ATTRIBUTES)
exp()
