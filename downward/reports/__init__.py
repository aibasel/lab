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
import sys
import traceback

from lab import reports
from lab import tools
from lab.reports import Attribute, Report


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
        min_cost = reports.minimum(all_costs)
        if min_cost is None:
            return 0.0
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
        Attribute('search_time', functions=reports.gm),
        Attribute('total_time', functions=reports.gm),
        Attribute('evaluations', functions=reports.gm),
        Attribute('expansions', functions=reports.gm),
        Attribute('generated', functions=reports.gm),
        Attribute('score_*', min_wins=False, functions=[reports.avg, sum]),
    ])

    INFO_ATTRIBUTES = [
        'local_revision', 'global_revision', 'revision_summary',
        'build_options', 'driver_options', 'component_options'
    ]

    def __init__(self, derived_properties=None, **kwargs):
        """
        See :py:class:`Report <lab.reports.Report>` for inherited parameters.

        *derived_properties* must be a function or a list of functions taking a
        single argument. This argument is a list of problem runs i.e. it contains
        one run-dictionary for each algorithm in the experiment. The function is
        called for every problem in the suite.

        You can include only specific domains or algorithms by
        using :py:class:`filters <.Report>`. If you provide a list for
        *filter_algorithm*, it will be used to determine the order of
        algorithms in the report. ::

            # Use a filter function: algorithms sorted alphabetically.
            def only_blind_and_lmcut(run):
                return run['algorithm'] in ['blind', 'lmcut']
            PlanningReport(filter=only_blind_and_lmcut)

            # Filter with "filter_algorithm": list orders algorithms.
            PlanningReport(filter_algorithm=['lmcut', 'blind'])

        """
        # Allow specifying a single property or a list of properties.
        if hasattr(derived_properties, '__call__'):
            derived_properties = [derived_properties]
        self.derived_properties = derived_properties or []

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
        self._compute_derived_properties()
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
        self.algorithm_info = self._scan_algorithm_info()
        try:
            self._perform_sanity_checks()
        except AssertionError:
            logging.warning(
                'The following sanity check failed. Did you filter the intended runs? '
                'Are there old properties in the eval-dir you don\'t want to merge?')
            traceback.print_exc(file=sys.stdout)

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

    def _perform_sanity_checks(self):
        # Sanity checks
        assert len(self.problems) * len(self.algorithms) == len(self.runs), (
            'Every problem must be run for all algorithms\n'
            'Algorithms (%d):\n%s\nProblems: %d\nDomains (%d):\n%s\nRuns: %d' %
            (len(self.algorithms), self.algorithms, len(self.problems), len(self.domains),
             self.domains.keys(), len(self.runs)))
        assert sum(len(probs) for probs in self.domains.values()) == len(self.problems)
        assert len(self.problem_runs) == len(self.problems)
        for (domain, problem), runs in self.problem_runs.items():
            if len(runs) != len(self.algorithms):
                prob_algos = [run['algorithm'] for run in runs]
                print 'Error: Algorithms for problem (%d) != Total algorithms (%d)' % (
                    len(prob_algos), len(self.algorithms))
                times = defaultdict(int)
                for algo in prob_algos:
                    times[algo] += 1
                print 'The problem is run more than once for the algorithms:',
                print ', '.join(['%s: %dx' % (algo, num_runs)
                                 for (algo, num_runs) in times.items() if num_runs > 1])
                logging.critical('Sanity check failed')
        assert sum(len(runs) for runs in self.problem_runs.values()) == len(self.runs)
        assert len(self.domains) * len(self.algorithms) == len(self.domain_algorithm_runs)
        assert (sum(len(runs) for runs in self.domain_algorithm_runs.values()) ==
                len(self.runs))

    def _compute_derived_properties(self):
        for func in self.derived_properties:
            for (domain, problem), runs in self.problem_runs.items():
                func(runs)
                # Update the data with the new properties.
                for run in runs:
                    run_id = '-'.join((run['algorithm'], run['domain'], run['problem']))
                    self.props[run_id] = run

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
