# -*- coding: utf-8 -*-
#
# downward uses the lab package to conduct experiments with the
# Fast Downward planning system.
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

from lab.steps import Step
from lab import tools

from downward.checkouts import Translator, Preprocessor, Planner
from downward.experiment import DownwardExperiment
from downward.suites import suite_optimal_with_ipc11, suite_satisficing_with_ipc11
from downward.configs import config_suite_optimal, config_suite_satisficing
from downward.reports.compare import CompareRevisionsReport
from downward.reports.scatter import ScatterPlotReport

# TODO: Remove code duplication.


COMPARED_ATTRIBUTES = ['coverage', 'search_time', 'score_search_time', 'total_time',
                       'score_total_time', 'expansions', 'score_expansions',
                       'expansions_until_last_jump', 'evaluations', 'score_evaluations',
                       'generated', 'score_generated', 'memory', 'score_memory',
                       'run_dir', 'cost']

SCATTER_PLOT_ATTRIBUTES = ['total_time', 'search_time', 'memory',
                           'expansions_until_last_jump']


def greatest_common_ancestor(repo, rev1, rev2):
    long_rev = tools.get_command_output(['hg', 'debugancestor', rev1, rev2],
                                        cwd=repo, quiet=True)
    number, hexcode = long_rev.split(':')
    pipe = subprocess.Popen(
        ['hg', 'id', '-r', hexcode], cwd=repo, stdout=subprocess.PIPE
    )
    return pipe.stdout.read().strip()


def domain_tuple_category(run1, run2):
    return run1['domain']


class CompareRevisionsExperiment(DownwardExperiment):
    """
    Convenience experiment that compares two revisions or compares the
    latest revision on a branch to the revision the branch is based on.
    Both revisions are tested with all the most important configurations.
    Reports that allow a before-after comparison are automaticaly added.
    """
    def __init__(self, path, repo, opt_or_sat, rev, base_rev=None,
                 use_core_configs=True, use_ipc_configs=True, use_extended_configs=False,
                 **kwargs):
        """
        See :py:class:`DownwardExperiment <downward.experiments.DownwardExperiment>`
        for inherited parameters.

        The experiment will be built at *path*.

        *repo* must be the path to a Fast Downward repository. This repository
        is used to search for problem files.

        If *opt_or_sat* is 'opt', configurations for optimal planning will be
        tested on all domains suited for optimal planning. If it is 'sat',
        configurations for satisficing planning will be tested on the
        satisficing suite.

        *rev* determines the new revision to test.

        If *base_rev* is None (default), the latest revision on the branch default
        that is an ancestor of *rev* will be used.

        *use_core_configs* determines if the most common configurations are tested
        (default: True).

        *use_ipc_configs* determines if the configurations used in the IPCs are tested
        (default: True).

        *use_extended_configs* determines if some less common configurations are tested
        (default: False).

        """
        DownwardExperiment.__init__(self, path, repo, combinations=[], **kwargs)
        self.add_revision(rev, add_ancestor=True)

        # ------ suites and configs ------------------------------------

        if opt_or_sat == 'opt':
            self.add_suite(suite_optimal_with_ipc11())
            configs = config_suite_optimal(use_core_configs,
                                           use_ipc_configs,
                                           use_extended_configs)
        elif opt_or_sat == 'sat':
            self.add_suite(suite_satisficing_with_ipc11())
            configs = config_suite_satisficing(use_core_configs,
                                               use_ipc_configs,
                                               use_extended_configs)
        else:
            logging.critical('Select to test either \'opt\' or \'sat\' configurations')

        for nick, command in configs.items():
            self.add_config(nick, command)

        # ------ reports -----------------------------------------------

        compare_report = CompareRevisionsReport(rev1=base_rev,
                                                rev2=rev,
                                                resolution='combined',
                                                attributes=COMPARED_ATTRIBUTES)
        self.add_step(Step('report-compare-scores',
                           compare_report,
                           self.eval_dir,
                           os.path.join(self.eval_dir, 'report-compare-scores.html')))

        for nick in configs.keys():
            config_before = '%s-%s' % (base_rev, nick)
            config_after = '%s-%s' % (rev, nick)
            for attribute in SCATTER_PLOT_ATTRIBUTES:
                name = 'scatter-%s-%s' % (attribute, nick)
                self.add_step(Step(name,
                                   ScatterPlotReport(
                                       filter_config=[config_before, config_after],
                                       attributes=[attribute],
                                       get_category=domain_tuple_category,
                                       legend_location=(1.3, 0.5)),
                                   self.eval_dir,
                                   os.path.join(self.eval_dir, name)))
