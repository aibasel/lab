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

import logging
from collections import defaultdict

from lab import reports
from lab import tools
from lab.reports import Report, Table


class PlanningTable(Table):
    def __init__(self, *args, **kwargs):
        Table.__init__(self, *args, **kwargs)

        if self.title in ['search_time', 'total_time']:
            self.add_summary_function('GEOMETRIC MEAN', reports.gm)
        else:
            self.add_summary_function('SUM', sum)

        if 'score' in self.title:
            # When summarising score results from multiple domains we show
            # normalised averages so that each domain is weighed equally.
            self.add_summary_function('AVERAGE', reports.avg)


def quality(problem_runs):
    """IPC score."""
    min_cost = tools.minimum(run.get('cost') for run in problem_runs)
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


def single_solver(problem_runs):
    solvers = sum(run.get('coverage') for run in problem_runs)
    for run in problem_runs:
        single_solver = (solvers == 1 and run.get('coverage') == 1)
        run['single_solver'] = int(single_solver)


class PlanningReport(Report):
    def __init__(self, *args, **kwargs):
        self.derived_properties = kwargs.pop('derived_properties', [])
        Report.__init__(self, *args, **kwargs)
        self.derived_properties.append(quality)
        self.derived_properties.append(single_solver)

    def _scan_data(self):
        self.scan_planning_data()
        self.compute_derived_properties()
        Report._scan_data(self)

    def scan_planning_data(self):
        # Use local variables first to save lookups
        problems = set()
        domains = defaultdict(list)
        configs = set()
        problem_runs = defaultdict(list)
        domain_runs = defaultdict(list)
        runs = {}
        for run_name, run in self.props.items():
            # Sanity checks
            assert 'coverage' in run, ('The run in %s has no coverage value' %
                                       run.get('run_dir'))

            configs.add(run['config'])
            domain, problem, config = run['domain'], run['problem'], run['config']
            problems.add((domain, problem))
            problem_runs[(domain, problem)].append(run)
            domain_runs[(domain, config)].append(run)
            runs[(domain, problem, config)] = run
        for domain, problem in problems:
            domains[domain].append(problem)
        self.configs = list(sorted(configs))
        self.problems = list(sorted(problems))
        self.domains = domains
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

    def compute_derived_properties(self):
        for func in self.derived_properties:
            for (domain, problem), runs in self.problem_runs.items():
                func(runs)
                # update the data with the new properties
                for run in runs:
                    run_id = '-'.join((run['config'], run['domain'], run['problem']))
                    self.props[run_id] = run

    def _get_empty_table(self, attribute):
        '''
        Returns an empty table. Used and filled by subclasses.
        '''
        # Decide whether we want to highlight minima or maxima
        max_attribute_parts = ['score', 'initial_h_value', 'coverage',
                               'quality', 'single_solver']
        min_wins = True
        for attr_part in max_attribute_parts:
            if attr_part in attribute:
                min_wins = False
        table = PlanningTable(attribute, min_wins=min_wins)
        return table
