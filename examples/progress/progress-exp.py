#! /usr/bin/env python

import os
import platform
import sys
from subprocess import call

from downward.experiment import DownwardExperiment
from downward.reports.absolute import AbsoluteReport
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

ATTRIBUTES = ['coverage', 'total_time']

MAS1 = ["--search",
        "astar(merge_and_shrink(merge_strategy=merge_linear_reverse_level,"
        "shrink_strategy=shrink_bisimulation(max_states=infinity,threshold=1,"
        "greedy=true,group_by_h=false)))"]
MAS2 = ["--search",
        "astar(merge_and_shrink(merge_strategy=merge_linear_reverse_level,"
        "shrink_strategy=shrink_bisimulation(max_states=200000,greedy=false,"
        "group_by_h=true)))"]
LMCOUNT = ["--search",
           "astar(lmcount(lm_merged([lm_rhw(),lm_hm(m=1)]),admissible=true),mpd=true)"]
LMCUT = ["--search", "astar(lmcut())"]


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
exp.add_config('mas1', MAS1)
exp.add_config('mas2', MAS2)
exp.add_config('lmcount', LMCOUNT)
exp.add_config('lmcut', LMCUT)

# Add report steps
progress_report_path = os.path.join(exp.eval_dir, 'progress.html')
exp.add_step(Step('report-progress', ProgressReport(filters=[
        lambda run: (True#run['domain'] == 'blocks' #and
                     #run['problem'] == 'probBLOCKS-10-2.pddl'
                     )]), exp.eval_dir, progress_report_path))
abs_domain_report_file = os.path.join(REPORTS, '%s-abs-d.html' % EXPNAME)
abs_problem_report_file = os.path.join(REPORTS, '%s-abs-p.html' % EXPNAME)
oracle_eval_dir = os.path.join(exp.eval_dir, '..', 'progress-oracle-eval')
exp.add_step(Step('report-abs-d', AbsoluteReport('domain', attributes=ATTRIBUTES),
                                                 oracle_eval_dir, abs_domain_report_file))
exp.add_step(Step('report-abs-p', AbsoluteReport('problem', attributes=ATTRIBUTES),
                                                 oracle_eval_dir, abs_problem_report_file))

def remove_single_searches(run):
    return run.get('config_nick') not in ['mas1', 'mas2', 'lmcount', 'lmcut']

exp.add_step(Step('report-oracle-d', AbsoluteReport('domain', attributes=ATTRIBUTES, filters=[remove_single_searches]),
                                                 oracle_eval_dir, os.path.join(REPORTS, '%s-oracle-d.html' % EXPNAME)))
#exp.add_step(Step('report-oracle-p', AbsoluteReport('problem', attributes=ATTRIBUTES, filters=[remove_single_searches]),
#                                                 oracle_eval_dir, os.path.join(REPORTS, '%s-oracle-p.html' % EXPNAME)))

#exp.add_step(Step('report-dynamic', call,
#                  ['/home/jendrik/projects/Downward/fastr/new-scripts/downward-reports.py',
#                   '-r', 'js', oracle_eval_dir, '-a', ','.join(ATTRIBUTES)]))

# Copy the results
exp.add_step(Step.publish_reports(abs_domain_report_file, abs_problem_report_file))


if __name__ == '__main__':
    # This method parses the commandline. We assume this file is called exp.py.
    # Supported styles:
    # ./exp.py 1
    # ./exp.py 4 5 6
    # ./exp.py all
    exp()
