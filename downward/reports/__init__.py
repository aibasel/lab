# -*- coding: utf-8 -*-
#
# downward uses the lab package to conduct experiments with the
# Fast Downward planning system.
#
# Copyright (C) 2012  Jendrik Seipp (jendrikseipp@web.de)
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

"""
Module that permits generating downward reports by reading properties files
"""

from __future__ import with_statement, division

from collections import defaultdict
import logging

from lab import reports
from lab import tools
from lab.reports import Report, Table


def quality(problem_runs):
    """IPC score."""
    min_cost = reports.minimum(run.get('cost') for run in problem_runs)
    for run in problem_runs:
        cost = run.get('cost')
        if cost is None:
            quality = 0.0
        elif cost == 0:
            assert min_cost == 0
            quality = 1.0
        else:
            quality = min_cost / cost
        run['quality'] = round(quality, 4)


class PlanningReport(Report):
    """
    This is the base class for all Downward reports.
    """
    def __init__(self, configs=None, *args, **kwargs):
        """
        kwargs can contain the following items:

        *derived_properties* must be a list of functions that take a single
        argument. This argument is a list of problem runs i.e. it contains one
        run-dictionary for each config in the experiment. The function is
        called for every problem in the suite. A function that computes the
        IPC score based on the results of the experiment is added automatically
        to the *derived_properties* list and serves as an example here: ::

            def quality(problem_runs):
                min_cost = reports.minimum(run.get('cost') for run in problem_runs)
                for run in problem_runs:
                    cost = run.get('cost')
                    if cost is None:
                        quality = 0.0
                    elif cost == 0:
                        assert min_cost == 0
                        quality = 1.0
                    else:
                        quality = min_cost / cost
                    run['quality'] = round(quality, 4)

        *filter_config* can be a list of configuration names. This is a
        shortcut to show only some configurations and also determines the
        order in which the configurations are shown in the report.
        The following three reports all filter the same runs but only the
        last one shows the configurations in the order [c2, c1]::

            def filter_c1_and_c2(run):
                return run['config'] in ['c2', 'c1']
            PlanningReport(filter=filter_c1_and_c2, attributes=['coverage'])

            PlanningReport(filter_config=['c1', 'c2'], attributes=['coverage'])

            PlanningReport(filter_config=['c2', 'c1'], attributes=['coverage'])
        """
        self.derived_properties = kwargs.pop('derived_properties', [])
        # Remember the order of the configs if it is given as a key word argument filter
        self.configs = kwargs.get('filter_config', None)
        self.config_nicks = kwargs.get('filter_config_nick', None)

        Report.__init__(self, *args, **kwargs)
        self.derived_properties.append(quality)

    def _scan_data(self):
        self._scan_planning_data()
        self._compute_derived_properties()
        Report._scan_data(self)

    def _scan_planning_data(self):
        # Use local variables first to avoid lookups
        problems = set()
        domains = defaultdict(list)
        problem_runs = defaultdict(list)
        domain_runs = defaultdict(list)
        runs = {}
        for run_name, run in self.props.items():
            # Sanity checks
            if run.get('stage') == 'search':
                assert 'coverage' in run, ('The run in %s has no coverage value' %
                                           run.get('run_dir'))

            domain, problem, config = run['domain'], run['problem'], run['config']
            problems.add((domain, problem))
            problem_runs[(domain, problem)].append(run)
            domain_runs[(domain, config)].append(run)
            runs[(domain, problem, config)] = run
        for domain, problem in problems:
            domains[domain].append(problem)
        self.configs = self._get_config_order()
        self.problems = list(sorted(problems))
        self.domains = domains

        # Sort each entry in problem_runs by their config values
        def run_key(run):
            return self.configs.index(run['config'])
        for key, run_list in problem_runs.items():
            problem_runs[key] = sorted(run_list, key=run_key)
        self.problem_runs = problem_runs
        self.domain_runs = domain_runs
        self.runs = runs

        # Sanity checks
        assert len(self.problems) * len(self.configs) == len(self.runs), (
            'Every problem must be run for all configs\n'
            'Configs (%d):\n%s\nProblems: %d\nDomains (%d):\n%s\nRuns: %d' %
            (len(self.configs), self.configs, len(self.problems), len(self.domains),
             self.domains.keys(), len(self.runs)))
        assert sum(len(probs) for probs in domains.values()) == len(self.problems)
        assert len(self.problem_runs) == len(self.problems)
        for (domain, problem), runs in self.problem_runs.items():
            if len(runs) != len(self.configs):
                prob_configs = [run['config'] for run in runs]
                print 'Error:          Problem configs (%d) != Configs (%d)' % (
                    len(prob_configs), len(self.configs))
                times = defaultdict(int)
                for config in prob_configs:
                    times[config] += 1
                print 'The problem is run more than once for the configs:',
                print ', '.join(['%s: %dx' % (config, num_runs)
                                 for (config, num_runs) in times.items() if num_runs > 1])
                logging.critical('Sanity check failed')
        assert sum(len(runs) for runs in self.problem_runs.values()) == len(self.runs)
        assert len(self.domains) * len(self.configs) == len(self.domain_runs)
        assert sum(len(runs) for runs in self.domain_runs.values()) == len(self.runs)

    def _compute_derived_properties(self):
        for func in self.derived_properties:
            for (domain, problem), runs in self.problem_runs.items():
                func(runs)
                # update the data with the new properties
                for run in runs:
                    run_id = '-'.join((run['config'], run['domain'], run['problem']))
                    self.props[run_id] = run

    def _get_config_order(self):
        configs = set()
        config_nicks_to_config = defaultdict(set)
        for run in self.props.values():
            configs.add(run['config'])
            config_nicks_to_config[run['config_nick']].add(run['config'])
        if self.config_nicks and not self.configs:
            self.configs = []
            for nick in self.config_nicks:
                self.configs += sorted(config_nicks_to_config[nick])
        if self.configs:
            # Other filters may have changed the set of available configs by either
            # removing all runs from one config or changing the run['config'] for a run.
            # Maintain the original order of configs and only keep configs that still
            # have available runs after filtering. Then add all new configs sorted
            # naturally at the end
            config_order = [c for c in self.configs if c in configs]
            config_order += list(tools.natural_sort(configs - set(self.configs)))
        else:
            config_order = list(tools.natural_sort(configs))
        return config_order

    def _get_empty_table(self, attribute):
        '''
        Returns an empty table. Used and filled by subclasses.
        '''
        # Only add a highlighting and summary functions for numeric attributes.
        if self._all_attributes[attribute] not in [int, float]:
            table = Table(title=attribute, min_wins=None)
            table.set_column_order(self._get_config_order())
            return table

        # Decide whether we want to highlight minima or maxima
        max_attribute_parts = ['score', 'initial_h_value', 'coverage',
                               'quality', 'single_solver']
        min_wins = True
        for attr_part in max_attribute_parts:
            if attr_part in attribute:
                min_wins = False

        table = Table(title=attribute, min_wins=min_wins)

        if attribute in ['search_time', 'total_time']:
            table.add_summary_function('GEOMETRIC MEAN', reports.gm)
        else:
            table.add_summary_function('SUM', sum)

        if 'score' in attribute:
            # When summarising score results from multiple domains we show
            # normalised averages so that each domain is weighed equally.
            table.add_summary_function('AVERAGE', reports.avg)

        table.set_column_order(self._get_config_order())
        return table
