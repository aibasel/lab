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

"""
Module that permits generating downward reports by reading properties files.
"""

from __future__ import with_statement, division

from collections import defaultdict
from fnmatch import fnmatch
import logging

from lab import reports
from lab import tools
from lab.reports import Attribute, Report, geometric_mean


class QualityFilters(object):
    """Compute the IPC score.

    This class provide two filters. The first stores costs, the second
    computes IPC scores.

    """
    def __init__(self):
        self.tasks_to_costs = defaultdict(list)

    def _get_task(self, run):
        return (run['domain'], run['problem'])

    def _compute_quality(self, cost, all_costs):
        if cost is None:
            return 0.0
        assert all_costs
        min_cost = min(all_costs)
        if cost == 0:
            assert min_cost == 0
            return 1.0
        return min_cost / cost

    def store_costs(self, run):
        cost = run.get('cost')
        if cost is not None and run.get('coverage'):
            self.tasks_to_costs[self._get_task(run)].append(cost)
        return True

    def add_quality(self, run):
        run['quality'] = self._compute_quality(
            run.get('cost'), self.tasks_to_costs[self._get_task(run)])
        return run


class PlanningReport(Report):
    """
    This is the base class for all Downward reports.
    """
    ATTRIBUTES = dict((str(attr), attr) for attr in [
        Attribute('coverage', absolute=True, min_wins=False),
        Attribute('initial_h_value', min_wins=False),
        Attribute('quality', absolute=True, min_wins=False),
        Attribute('unsolvable', absolute=True, min_wins=False),
        Attribute('search_time', functions=geometric_mean),
        Attribute('total_time', functions=geometric_mean),
        Attribute('evaluations', functions=geometric_mean),
        Attribute('expansions', functions=geometric_mean),
        Attribute('generated', functions=geometric_mean),
        Attribute('dead_ends', min_wins=False),
        Attribute(
            'score_*', min_wins=False, functions=[reports.arithmetic_mean, sum]),
    ])

    INFO_ATTRIBUTES = [
        'local_revision', 'global_revision', 'revision_summary',
        'build_options', 'driver_options', 'component_options'
    ]

    def __init__(self, **kwargs):
        """
        See :class:`~lab.reports.Report` for inherited parameters.

        You can include only specific domains or algorithms by
        using :py:class:`filters <.Report>`. If you provide a list for
        *filter_algorithm*, it will be used to determine the order of
        algorithms in the report. ::

            # Use a filter function: algorithms sorted alphabetically.
            def only_blind_and_lmcut(run):
                return run['algorithm'] in ['blind', 'lmcut']
            PlanningReport(filter=only_blind_and_lmcut)

            # Use "filter_algorithm": list orders algorithms.
            PlanningReport(filter_algorithm=['lmcut', 'blind'])

        The constructor automatically adds two filters that together
        compute and store IPC scores in the "quality" attribute. The
        first caches the costs and the second computes and adds the IPC
        score to each run.

        """
        # Set non-default options for some attributes.
        attributes = tools.make_list(kwargs.get('attributes') or [])
        kwargs['attributes'] = [self._prepare_attribute(attr) for attr in attributes]

        # Remember the order of algorithms if it is given as a keyword argument filter.
        self.filter_algorithm = tools.make_list(kwargs.get('filter_algorithm', []))

        # Compute IPC scores.
        quality_filters = QualityFilters()
        filters = tools.make_list(kwargs.get('filter', []))
        filters.append(quality_filters.store_costs)
        filters.append(quality_filters.add_quality)
        kwargs['filter'] = filters

        Report.__init__(self, **kwargs)

    def get_text(self):
        markup = Report.get_text(self)
        unxeplained_errors = 0
        for run in self.runs.values():
            if run.get('error', '').startswith('unexplained'):
                logging.warning(
                    'Unexplained error in "{run_dir}": {error}'.format(**run))
                unxeplained_errors += 1
        if unxeplained_errors:
            logging.warning(
                'There were {} runs with unexplained errors.'.format(
                    unxeplained_errors))
        return markup

    def _prepare_attribute(self, attr):
        if not isinstance(attr, Attribute):
            if attr in self.ATTRIBUTES:
                return self.ATTRIBUTES[attr]
            for pattern in self.ATTRIBUTES.values():
                if (fnmatch(attr, pattern)):
                    return pattern.copy(attr)
        return Report._prepare_attribute(self, attr)

    def _scan_data(self):
        self._scan_planning_data()
        Report._scan_data(self)

    def _scan_planning_data(self):
        # Use local variables first to avoid lookups.
        problems = set()
        domains = defaultdict(list)
        problem_runs = defaultdict(list)
        domain_algorithm_runs = defaultdict(list)
        runs = {}
        for run_name, run in self.props.items():
            if 'coverage' not in run:
                if 'error' not in run:
                    run['error'] = 'unexplained-crash'

            domain, problem, algo = run['domain'], run['problem'], run['algorithm']
            problems.add((domain, problem))
            problem_runs[(domain, problem)].append(run)
            domain_algorithm_runs[(domain, algo)].append(run)
            runs[(domain, problem, algo)] = run
        for domain, problem in problems:
            domains[domain].append(problem)
        self.algorithms = self._get_algorithm_order()
        self.problems = list(sorted(problems))
        self.domains = domains

        # Sort each entry in problem_runs by algorithm.
        # TODO: Remove O(n) lookup.
        def run_key(run):
            return self.algorithms.index(run['algorithm'])

        for key, run_list in problem_runs.items():
            problem_runs[key] = sorted(run_list, key=run_key)

        self.problem_runs = problem_runs
        self.domain_algorithm_runs = domain_algorithm_runs
        self.runs = runs

        assert sum(len(probs) for probs in self.domains.values()) == len(self.problems)
        assert len(self.problem_runs) == len(self.problems)
        assert sum(len(runs) for runs in self.problem_runs.values()) == len(self.runs)

        self.algorithm_info = self._scan_algorithm_info()
        self._perform_sanity_check()

    def _scan_algorithm_info(self):
        info = {}
        for (domain, problem), runs in self.problem_runs.items():
            for run in runs:
                info[run['algorithm']] = dict(
                    (attr, run.get(attr, '?'))
                    for attr in self.INFO_ATTRIBUTES)
            # We only need to scan the algorithms for one task.
            break
        return info

    def _perform_sanity_check(self):
        if len(self.problems) * len(self.algorithms) != len(self.runs) or True:
            logging.warning(
                'Not every algorithm has been run on every task. '
                'However, if you applied a filter this is to be '
                'expected. If not, there might be old properties in the '
                'eval-dir that got included in the report. '
                'Algorithms (%d): %s, problems (%d), domains (%d): %s, runs (%d)' %
                (len(self.algorithms), self.algorithms, len(self.problems),
                 len(self.domains), self.domains.keys(), len(self.runs)))

    def _get_warnings_table(self):
        """
        Return a :py:class:`Table <lab.reports.Table>` containing one line for
        each run where an unexpected error occured.
        """
        columns = [
            'domain', 'problem', 'algorithm', 'error',
            'fast-downward_wall_clock_time', 'raw_memory']
        table = reports.Table(title='Unexplained errors')
        table.set_column_order(columns)
        for run in self.props.values():
            if run.get('error', '').startswith('unexplained'):
                for column in columns:
                    table.add_cell(run['run_dir'], column, run[column])
        return table

    def _get_algorithm_order(self):
        """
        Return a list of algorithms in the order determined by the user.

        If 'filter_algorithm' is given, algorithms are sorted in that
        order. Otherwise, they are sorted alphabetically.

        You can use the order of algorithms in your own custom report
        subclasses by accessing self.algorithms which is calculated in
        self._scan_planning_data.

        """
        all_algos = set(run['algorithm'] for run in self.props.values())
        if self.filter_algorithm:
            # Other filters may have changed the set of available algorithms by either
            # removing all runs for one algorithm or changing run['algorithm'] for a run.
            # Maintain the original order of algorithms and only keep algorithms that
            # still have runs after filtering. Then add all new algorithms
            # sorted naturally at the end.
            algo_order = (
                [c for c in self.filter_algorithm if c in all_algos] +
                tools.natural_sort(all_algos - set(self.filter_algorithm)))
        else:
            algo_order = tools.natural_sort(all_algos)
        return algo_order
