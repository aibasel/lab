#! /usr/bin/env python

import os
import platform
import sys

from lab.downward.downward_experiment import DownwardExperiment
from lab.downward.reports.absolute import AbsoluteReport
from lab.environments import LocalEnvironment, GkiGridEnvironment
from lab.experiment import Step
from lab import tools

from progress_report import ProgressReport


DIR = os.path.join(tools.BASE_DIR, 'examples', 'progress')

EXPNAME = 'js-' + os.path.splitext(os.path.basename(__file__))[0]
if platform.node() == 'habakuk':
    EXPPATH = os.path.join('/home/downward/jendrik/experiments/', EXPNAME)
    REPORTS = '/home/downward/jendrik/reports'
    REPO = '/home/downward/jendrik/downward'
    SUITE = 'LMCUT_DOMAINS'
    ENV = GkiGridEnvironment()
else:
    EXPPATH = os.path.join(tools.DEFAULT_EXP_DIR, EXPNAME)
    REPORTS = tools.DEFAULT_REPORTS_DIR
    REPO = '/home/jendrik/projects/Downward/downward'
    SUITE = 'gripper:prob01.pddl'
    ENV = LocalEnvironment()

ATTRIBUTES = None  # Include all attributes

OPT1 =   ["--landmarks", "lmg=lm_rhw(only_causal_landmarks=false,"
                         "disjunctive_landmarks=true,"
                         "conjunctive_landmarks=true,no_orders=false)",
          "--heuristic", "hLMCut=lmcut()",
          "--heuristic", "hLM=lmcount(lmg,admissible=true)",
          "--heuristic", "hCombinedMax=max([hLM,hLMCut])",
          "--search", "astar(hCombinedMax,mpd=true,pathmax=false,cost_type=0)"]

LMCUT =  ["--heuristic", "hLMCut=lmcut()",
          "--search", "astar(hLMCut,mpd=true,pathmax=false,cost_type=0)"]

IPDB =   ["--heuristic", "hipdb=ipdb()",
          "--search", "astar(hipdb,mpd=true,pathmax=false,cost_type=0)"]

class ProgressExperiment(DownwardExperiment):
    def __init__(self, *args, **kwargs):
        DownwardExperiment.__init__(self, *args, **kwargs)
        self.add_resource('PROGRESS_PARSER',
                          os.path.join(DIR, 'progress-parser.py'),
                          'progress-parser.py')

    def _make_search_runs(self):
        DownwardExperiment._make_search_runs(self)
        for run in self.runs:
            run.add_command('parse-progress', ['PROGRESS_PARSER'])

exp = ProgressExperiment(path=EXPPATH, env=ENV, repo=REPO)

exp.add_suite(SUITE)
exp.add_config('opt-initial', OPT1)
exp.add_config('lmcut', LMCUT)
exp.add_config('ipdb', IPDB)

# Add report steps
abs_domain_report_file = os.path.join(REPORTS, '%s-abs-d.html' % EXPNAME)
abs_problem_report_file = os.path.join(REPORTS, '%s-abs-p.html' % EXPNAME)
exp.add_step(Step('report-abs-d', AbsoluteReport('domain', attributes=ATTRIBUTES),
                                                 exp.eval_dir, abs_domain_report_file))
exp.add_step(Step('report-abs-p', AbsoluteReport('problem', attributes=ATTRIBUTES),
                                                 exp.eval_dir, abs_problem_report_file))
progress_report_path = os.path.join(exp.eval_dir, 'progress.html')
exp.add_step(Step('report-progress', ProgressReport(), exp.eval_dir, progress_report_path))

# Copy the results
exp.add_step(Step.publish_reports(abs_domain_report_file, abs_problem_report_file))


if __name__ == '__main__':
    # This method parses the commandline. We assume this file is called exp.py.
    # Supported styles:
    # ./exp.py 1
    # ./exp.py 4 5 6
    # ./exp.py all
    exp()
