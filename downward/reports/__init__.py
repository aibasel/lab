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
Module that permits generating downward reports by reading properties files
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


def quality(problem_runs):
    """IPC score."""
    min_cost = reports.minimum(run.get('cost') for run in problem_runs)
    for run in problem_runs:
        cost = run.get('cost')
        if cost is None or not run.get('coverage'):
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
        called for every problem in the suite. A function that computes the
        IPC score based on the results of the experiment is added automatically
        to the *derived_properties* list and serves as an example here:

        .. literalinclude:: ../downward/reports/__init__.py
           :pyobject: quality

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

        Tip: When you append ``_relative`` to an attribute, you will get a table
        containing the attribute's values of each algorithm relative to the
        leftmost column.

        """
        # Allow specifying a single property or a list of properties.
        if hasattr(derived_properties, '__call__'):
            derived_properties = [derived_properties]
        self.derived_properties = derived_properties or []

        # Set non-default options for some attributes.
        attributes = tools.make_list(kwargs.get('attributes') or [])
        kwargs['attributes'] = [self._prepare_attribute(attr) for attr in attributes]

        self._handle_relative_attributes(kwargs['attributes'])

        # Remember the order of algorithms if it is given as a keyword argument filter.
        self.filter_algorithm = tools.make_list(kwargs.get('filter_algorithm', []))

        Report.__init__(self, **kwargs)
        self.derived_properties.append(quality)

    def get_text(self):
        markup = Report.get_text(self)
        unxeplained_errors = 0
        for run in self.runs.values():
            if run.get('error', '').startswith('unexplained'):
                logging.warning('Unexplained error in \'%s\': %s' %
                                (run.get('run_dir'), run.get('error')))
                unxeplained_errors += 1
        if unxeplained_errors:
            logging.warning('There were %s runs with unexplained errors.' %
                            unxeplained_errors)
        return markup

    def _prepare_attribute(self, attr):
        if not isinstance(attr, Attribute):
            if attr in self.ATTRIBUTES:
                return self.ATTRIBUTES[attr]
            for pattern in self.ATTRIBUTES.values():
                if (fnmatch(attr, pattern) or fnmatch(attr, pattern + '_relative')):
                    return pattern.copy(attr)
        return Report._prepare_attribute(self, attr)

    def _get_relative_attribute_function(self, attr):
        def get_ratio(v1, v2):
            try:
                return v2 / v1
            except (TypeError, ZeroDivisionError):
                pass
            return None

        def relative_attr(runs):
            relname = '%s_relative' % attr
            first_val = runs[0].get(attr)
            for run in runs:
                val = run.get(attr)
                if (all(isinstance(v, (list, tuple)) for v in [first_val, val]) and
                        len(first_val) == len(val)):
                    run[relname] = [get_ratio(v1, v2) for v1, v2 in zip(first_val, val)]
                else:
                    run[relname] = get_ratio(first_val, val)

        return relative_attr

    def _handle_relative_attributes(self, attributes):
        for attr in attributes:
            if attr.endswith('_relative'):
                # Change name, but keep parameters.
                abs_attr = attr.copy(attr[:-len('_relative')])
                attr.functions = [reports.gm, reports.avg]
                self.derived_properties.append(
                    self._get_relative_attribute_function(abs_attr))

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
        info = defaultdict(dict)
        # TODO: Only scan first run.
        for (domain, problem), runs in self.problem_runs.items():
            for run in runs:
                info[run['algorithm']].update(
                    (attr, run.get(attr, '?'))
                    for attr in self.INFO_ATTRIBUTES)
            # Abort when we have found information for all algorithms.
            if len(info) == len(self.algorithms):
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
