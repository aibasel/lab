# -*- coding: utf-8 -*-
#
# downward uses the lab package to conduct experiments with the
# Fast Downward planning system.
#
# Copyright (C) 2012  Florian Pommerening (florian.pommerening@unibas.ch)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

#!/usr/bin/env python

import os
import logging
import subprocess
from downward.checkouts import Translator, Preprocessor, Planner
from downward.experiment import DownwardExperiment
from downward.suites import suite_optimal_with_ipc11, suite_satisficing_with_ipc11
from lab.steps import Step


class CompareRevisionsExperiment(DownwardExperiment):
    """
    Convenience class that runs test comparing the latest revision on a
    branch to the base revision the branch is based on.
    Both revisions are tested with all the most important configurations.
    Reports that allow a before-after comparison are automaticaly added.
    """
    def __init__(self, path, repo, opt_or_sat, branch, base_revision=None, 
                 use_core_configs=True, use_ipc_configs=True, use_extended_configs=False,
                 **kwargs):
        """
        See :py:class:`DownwardExperiment <downward.experiment.DownwardExperiment>` for inherited parameters.

        The experiment will be built at *path*.

        *repo* must be the path to a Fast Downward repository. This repository
        is used to search for problem files.

        If *opt_or_sat* is 'opt', configurations for optimal planning will be
        tested on all domains suited for optimal planning. If it is 'sat',
        configurations for satisficing planning will be tested on the 
        satisficing suite.

        *branch* determines the revision to test.

        If *base_revision* is None (default), the latest revision on the branch default
        that is an ancestor of *branch* will be used.

        *use_core_configs* determines if the most common configurations are tested (default: True).

        *use_ipc_configs* determines if the configurations used in the IPCs are tested (default: True).

        *use_extended_configs* determines if some less common configurations are tested (default: False).

        Example: ::

            repo = '/path/to/downward-repo'
            env = GkiGridEnvironment(queue='xeon_core.q', priority=-2)
            exppath = os.path.join(HOME, 'experiments/exec', 'issue999-opt')

            exp = EvaluateBranchExperiment(exppath, repo, 'opt', 'issue999', 
                                           use_extended_configs=True,
                                           environment=env)
        """
        if base_revision is None:
            base_revision = greatest_common_ancestor(repo, branch, 'default')
        if not base_revision:
            logging.critical('Base revision for branch \'%s\' could not be determined. ' +
                             'Please provide it manually.' % branch)

        combinations=[(Translator(repo, rev=r), Preprocessor(repo, rev=r), Planner(repo, rev=r))
                      for r in (branch, base_revision)]
        DownwardExperiment.__init__(self, path, repo, combinations=combinations, **kwargs)

        # ------ suites ------------------------------------------------

        if opt_or_sat == 'opt':
            self.add_suite(suite_optimal_with_ipc11())
        elif opt_or_sat == 'sat':
            self.add_suite(suite_satisficing_with_ipc11())
        else:
            logging.critical('Select to test either \'opt\' or \'sat\' configurations')

        # ------ configs -----------------------------------------------

        configs = {}
        if use_core_configs:
            configs.update(CORE_CONFIGS[opt_or_sat])
        if use_ipc_configs:
            configs.update(IPC_CONFIGS[opt_or_sat])
        if use_extended_configs:
            configs.update(EXTENDED_CONFIGS[opt_or_sat])
        for nick, command in configs.items():
            self.add_config(nick, command)

        # ------ reports -----------------------------------------------

        self.add_step(Step('report-abs-all-d', 
                           AbsoluteReport('domain'),
                           exp.eval_dir,
                           os.path.join(exp.eval_dir, 'report-abs-all-d.html')))

        self.add_step(Step('report-abs-all-p', 
                           AbsoluteReport('problem'),
                           exp.eval_dir,
                           os.path.join(exp.eval_dir, 'report-abs-all-p.html')))

        for nick in configs.keys():
            config_before = '%s-%s-%s-%s' % (base_revision, base_revision, base_revision, nick)
            config_after = '%s-%s-%s-%s' % (branch, branch, branch, nick)
            for attribute in ['total_time', 'search_time', 'memory', 'expansions']:
                name = 'scatter-%s-%s' % (attribute, nick)
                exp.add_step(Step(name,
                              ScatterPlotReport(filter_config=[config_before, config_after],
                                                attributes=[attribute],
                                                get_category=domain_tuple_category),
                              exp.eval_dir,
                              os.path.join(exp.eval_dir, name)))


# ------ utility functions ---------------------------------------------

def greatest_common_ancestor(repo, rev1, rev2):
    pipe = subprocess.Popen(
        ['hg', 'id', '--cwd', repo, '-r', 'ancestor(\'%s\', \'%s\')' % (rev1, rev2)],
        stdout=subprocess.PIPE
        )
    return pipe.stdout.read().strip()

def domain_tuple_category(run1, run2):
    return run1['domain']

# ------- Configs ------------------------------------------------------

CORE_CONFIGS = {}
CORE_CONFIGS['opt'] = {
    # A*
    'astar_blind': ['--search', 'astar(blind)'],
    'astar_h2': ['--search', 'astar(hm(2))'],
    'astar_ipdb': ['--search', 'astar(ipdb)'],
    'astar_lmcount_lm_merged_rhw_hm': ['--search', 'astar(lmcount(lm_merged([lm_rhw(),lm_hm(m=1)]),admissible=true),mpd=true)'],
    'astar_lmcut': ['--search', 'astar(lmcut)'],
    'astar_hmax': ['--search', 'astar(hmax)'],
    'astar_merge_and_shrink_bisim': ['--search', 'astar(merge_and_shrink(merge_strategy=merge_linear_reverse_level,shrink_strategy=shrink_bisimulation(max_states=200000,greedy=false,group_by_h=true)))'],
    'astar_merge_and_shrink_greedy_bisim': ['--search', 'astar(merge_and_shrink(merge_strategy=merge_linear_reverse_level,shrink_strategy=shrink_bisimulation(max_states=infinity,threshold=1,greedy=true,group_by_h=false)))'],
    'astar_selmax_lmcut_lmcount': ['--search', 'astar(selmax([lmcut(),lmcount(lm_merged([lm_hm(m=1),lm_rhw()]),admissible=true)],training_set=1000),mpd=true)'],
}
CORE_CONFIGS['sat'] = {
    # A*
    'astar_goalcount': ['--search', 'astar(goalcount)'],
    # eager greedy
    'eager_greedy_ff': ['--heuristic', 'h=ff()', '--search', 'eager_greedy(h, preferred=h)'],
    'eager_greedy_add': ['--heuristic', 'h=add()', '--search', 'eager_greedy(h, preferred=h)'],
    'eager_greedy_cg': ['--heuristic', 'h=cg()', '--search', 'eager_greedy(h, preferred=h)'],
    'eager_greedy_cea': ['--heuristic', 'h=cea()', '--search', 'eager_greedy(h, preferred=h)'],
    # lazy greedy
    'lazy_greedy_ff': ['--heuristic', 'h=ff()', '--search', 'lazy_greedy(h, preferred=h)'],
    'lazy_greedy_add': ['--heuristic', 'h=add()', '--search', 'lazy_greedy(h, preferred=h)'],
    'lazy_greedy_cg': ['--heuristic', 'h=cg()', '--search', 'lazy_greedy(h, preferred=h)'],
}

IPC_CONFIGS = {}
IPC_CONFIGS['opt'] = {
    'seq_opt_merge_and_shrink' : ['ipc', 'seq-opt-merge-and-shrink'],
    'seq_opt_fdss_1' : ['ipc', 'seq-opt-fdss-1'],
    'seq_opt_fdss_2' : ['ipc', 'seq-opt-fdss-2'],
}
IPC_CONFIGS['sat'] = {
    'seq_sat_lama_2011' : ['ipc', 'seq-sat-lama-2011'],
    'seq_sat_fdss_1' : ['ipc', 'seq-sat-fdss-1'],
    'seq_sat_fdss_2' : ['ipc', 'seq-sat-fdss-2'],
}

EXTENDED_CONFIGS = {}
EXTENDED_CONFIGS['opt'] = {
    # A*
    'astar_lmcount_lm_merged_rhw_hm_no_order': ['--search', 'astar(lmcount(lm_merged([lm_rhw(),lm_hm(m=1)]),admissible=true),mpd=true)'],
    # pareto open list
    'pareto_lmcut': ['--heuristic', 'h=lmcut()', '--search', 'eager(pareto([sum([g(), h]), h]), reopen_closed=true, pathmax=false, progress_evaluator=sum([g(), h]))'],
    # bucket-based open list
    'bucket_lmcut': ['--heuristic', 'h=lmcut()', '--search', 'eager(single_buckets(h), reopen_closed=true, pathmax=false)'],
}
EXTENDED_CONFIGS['sat'] = {
    # eager greedy
    'eager_greedy_alt_ff_cg': ['--heuristic', 'hff=ff()', '--heuristic', 'hcg=cg()', '--search', 'eager_greedy(hff,hcg,preferred=[hff,hcg])'],
    'eager_greedy_ff_no_pref': ['--search', 'eager_greedy(ff())'],
    # lazy greedy
    'lazy_greedy_alt_cea_cg': ['--heuristic', 'hcea=cea()', '--heuristic', 'hcg=cg()', '--search', 'lazy_greedy(hcea,hcg,preferred=[hcea,hcg])'],
    'lazy_greedy_ff_no_pref': ['--search', 'lazy_greedy(ff())'],
    'lazy_greedy_cea': ['--heuristic', 'h=cea()', '--search', 'lazy_greedy(h, preferred=h)'],
    # lazy wA*
    'lazy_wa3_ff': ['--heuristic', 'h=ff()', '--search', 'lazy_wastar(h,w=3,preferred=h)'],
    # eager wA*
    'eager_wa3_cg': ['--heuristic', 'h=cg()', '--search', 'eager(single(sum([g(),weight(h,3)])),preferred=h)'],
    # ehc
    'ehc_ff': ['--search', 'ehc(ff())'],
    # iterated
    'iterated_wa_merge_and_shrink': ['--heuristic', 'h=merge_and_shrink()', '--search', 'iterated([lazy_wastar(h,w=10), lazy_wastar(h,w=5), lazy_wastar(h,w=3), lazy_wastar(h,w=2), lazy_wastar(h,w=1)])'],
}
