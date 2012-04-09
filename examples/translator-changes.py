#! /usr/bin/env python

import os
import platform

from lab.steps import Step
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
    (Translator(repo=TRANSLATOR_REPO, rev="issue278", dest="issue278"),
     Preprocessor(repo=REPO),
     Planner(repo=REPO)),
]

CONFIGS = [('lama11', ['ipc', 'seq-sat-lama-2011', '--plan-file', 'sas_plan'])]
ATTRIBUTES = []

exp = standard_exp.get_exp('ALL', CONFIGS, combinations=COMBOS, attributes=ATTRIBUTES)

def parking(run):
    return run['domain'] == 'parking-sat11-strips'
exp.add_step(Step('parking-p', AbsoluteReport('problem', filter=parking, attributes=[]),
                                              exp.eval_dir, os.path.join(exp.eval_dir, 'parking-p.html')))

exp.add_step(Step('parking-p-rel', RelativeReport('problem', rel_change=0.1, filter=parking, attributes=[]),
                                              exp.eval_dir, os.path.join(exp.eval_dir, 'parking-p-rel.html')))
exp()
