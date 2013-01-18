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
from downward.suites import suite_optimal_with_ipc11, suite_satisficing_with_ipc11, config_suite_optimal, config_suite_satisficing
from lab.steps import Step


class CompareRevisionsExperiment(DownwardExperiment):
    """
    Convenience class that runs test comparing two revisions or comparing the
    latest revision on a branch to the revision the branch is based on.
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

            exp = CompareRevisionsExperiment(exppath, repo, 'opt', 'issue999', 
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

        # ------ suites and configs ------------------------------------

        if opt_or_sat == 'opt':
            self.add_suite(suite_optimal_with_ipc11())
            configs = config_suite_optimal(use_core_configs, use_ipc_configs, use_extended_configs)
        elif opt_or_sat == 'sat':
            self.add_suite(suite_satisficing_with_ipc11())
            configs = config_suite_satisficing(use_core_configs, use_ipc_configs, use_extended_configs)
        else:
            logging.critical('Select to test either \'opt\' or \'sat\' configurations')

        for nick, command in configs.items():
            self.add_config(nick, command)

        # ------ reports -----------------------------------------------

        compare_report = CompareRevisionsReport(
                            revisions=[base_revision, branch],
                            resolution='combined',
                            # TODO add more scores
                            attributes=['coverage', 'score_expansions', 'score_total_time'])
        exp.add_step(Step('report-compare-scores',
                          compare_report,
                          exp.eval_dir,
                          os.path.join(exp.eval_dir, 'report-compare-scores.html')))

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

