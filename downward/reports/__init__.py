# -*- coding: utf-8 -*-
#
# Downward Lab uses the Lab package to conduct experiments with the
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
Module that permits generating planner reports by reading properties files.
"""

from collections import defaultdict
from fnmatch import fnmatch
import logging

from lab import reports
from lab import tools
from lab.reports import Attribute, Report, geometric_mean


class PlanningReport(Report):
    """
    This is the base class for planner reports.

    The :py:attr:`~INFO_ATTRIBUTES` and :py:attr:`~ERROR_ATTRIBUTES`
    class members hold attributes for Fast Downward experiments by
    default. You may want to adjust the two lists in derived classes.

    """
    #: List of predefined :py:class:`~Attribute` instances. If
    #: PlanningReport receives ``attributes=['coverage']``, it converts
    #: the plain string ``'coverage'`` to the attribute instance
    #: ``Attribute('coverage', absolute=True, min_wins=False, scale='linear')``.
    #: The list can be overriden in subclasses.
    PREDEFINED_ATTRIBUTES = [
        Attribute('cost', scale='linear'),
        Attribute('coverage', absolute=True, min_wins=False, scale='linear'),
        Attribute('dead_ends', min_wins=False),
        Attribute('evaluations', functions=geometric_mean),
        Attribute('expansions', functions=geometric_mean),
        Attribute('generated', functions=geometric_mean),
        Attribute(
            'initial_h_value', min_wins=False, scale='linear',
            functions=reports.finite_sum),
        Attribute('plan_length', scale='linear'),
        Attribute('planner_time', functions=geometric_mean),
        Attribute('quality', absolute=True, min_wins=False),
        Attribute('score_*', min_wins=False, digits=4),
        Attribute('search_time', functions=geometric_mean),
        Attribute('total_time', functions=geometric_mean),
        Attribute('unsolvable', absolute=True, min_wins=False),
    ]

    #: Attributes shown in the algorithm info table. Can be overriden in
    #: subclasses.
    INFO_ATTRIBUTES = [
        'local_revision', 'global_revision', 'revision_summary',
        'build_options', 'driver_options', 'component_options'
    ]

    #: Attributes shown in the unexplained-errors table. Can be overriden
    #: in subclasses.
    ERROR_ATTRIBUTES = [
        'domain', 'problem', 'algorithm', 'unexplained_errors',
        'error', 'planner_wall_clock_time', 'raw_memory', 'node'
    ]

    def __init__(self, **kwargs):
        """
        See :class:`~lab.reports.Report` for inherited parameters.

        You can filter and modify runs for a report with
        :py:class:`filters <.Report>`. For example, you can include only
        a subset of algorithms or compute new attributes. If you provide
        a list for *filter_algorithm*, it will be used to determine the
        order of algorithms in the report.

        >>> # Use a filter function to select algorithms.
        >>> def only_blind_and_lmcut(run):
        ...     return run['algorithm'] in ['blind', 'lmcut']
        >>> report = PlanningReport(filter=only_blind_and_lmcut)

        >>> # Use "filter_algorithm" to select and *order* algorithms.
        >>> r = PlanningReport(filter_algorithm=['lmcut', 'blind'])

        :py:class:`Filters <.Report>` can be very helpful so we
        recommend reading up on them to use their full potential.

        """
        # Set non-default options for some attributes.
        attributes = tools.make_list(kwargs.get('attributes') or [])
        kwargs['attributes'] = [self._prepare_attribute(attr) for attr in attributes]

        # Remember the order of algorithms if it is given as a keyword argument filter.
        self.filter_algorithm = tools.make_list(kwargs.get('filter_algorithm', []))

        Report.__init__(self, **kwargs)

    def _prepare_attribute(self, attr):
        predefined = dict((str(attr), attr) for attr in self.PREDEFINED_ATTRIBUTES)
        if not isinstance(attr, Attribute):
            if attr in predefined:
                return predefined[attr]
            for pattern in predefined.values():
                if (fnmatch(attr, pattern)):
                    return pattern.copy(attr)
        return Report._prepare_attribute(self, attr)

    def _scan_data(self):
        self._scan_planning_data()
        Report._scan_data(self)

    def _scan_planning_data(self):
        problems = set()
        self.domains = defaultdict(list)
        self.problem_runs = defaultdict(list)
        self.domain_algorithm_runs = defaultdict(list)
        self.runs = {}
        for run in self.props.values():
            domain, problem, algo = run['domain'], run['problem'], run['algorithm']
            problems.add((domain, problem))
            self.problem_runs[(domain, problem)].append(run)
            self.domain_algorithm_runs[(domain, algo)].append(run)
            self.runs[(domain, problem, algo)] = run
        for domain, problem in problems:
            self.domains[domain].append(problem)

        self.algorithms = self._get_algorithm_order()

        if len(problems) * len(self.algorithms) != len(self.runs):
            logging.warning(
                'Not every algorithm has been run on every task. '
                'However, if you applied a filter this is to be '
                'expected. If not, there might be old properties in the '
                'eval-dir that got included in the report. '
                'Algorithms (%d): %s, problems (%d), domains (%d): %s, runs (%d)' %
                (len(self.algorithms), self.algorithms, len(problems),
                 len(self.domains), list(self.domains.keys()), len(self.runs)))

        # Sort each entry in problem_runs by algorithm.
        algo_to_index = dict(
            (algorithm, index)
            for index, algorithm in enumerate(self.algorithms))

        def run_key(run):
            return algo_to_index[run['algorithm']]

        for problem_runs in self.problem_runs.values():
            problem_runs.sort(key=run_key)

        self.algorithm_info = self._scan_algorithm_info()

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

    def _get_node_names(self):
        return set(
            run.get("node", "<attribute 'node' missing>")
            for run in self.runs.values())

    def _get_warnings_text_and_table(self):
        """
        Return a :py:class:`Table <lab.reports.Table>` containing one line for
        each run where an unexplained error occured.
        """
        if not self.ERROR_ATTRIBUTES:
            logging.critical('The list of error attributes must not be empty.')

        table = reports.Table(title='Unexplained errors')
        table.set_column_order(self.ERROR_ATTRIBUTES)

        wrote_to_slurm_err = any(
            'output-to-slurm.err' in run.get('unexplained_errors', [])
            for run in self.runs.values())

        num_unexplained_errors = 0
        for run in self.runs.values():
            error_message = tools.get_unexplained_errors_message(run)
            if error_message:
                logging.error(error_message)
                num_unexplained_errors += 1
                for attr in self.ERROR_ATTRIBUTES:
                    table.add_cell(run['run_dir'], attr, run.get(attr, '?'))

        if num_unexplained_errors:
            logging.error(
                'There were {num_unexplained_errors} runs with unexplained'
                ' errors.'.format(**locals()))

        errors = []

        if wrote_to_slurm_err:
            src_dir = self.eval_dir.rstrip('/')[:-len('-eval')]
            slurm_err_file = src_dir + '-grid-steps/slurm.err'
            try:
                slurm_err_content = tools.get_slurm_err_content(src_dir)
            except IOError:
                slurm_err_content = (
                    'The slurm.err file was missing while creating the report.')
            else:
                slurm_err_content = tools.filter_slurm_err_content(slurm_err_content)

            logging.error(
                'There was output to {slurm_err_file}.'.format(**locals()))

            errors.append(
                ' Contents of {slurm_err_file} without "memory cg"'
                ' errors:\n```\n{slurm_err_content}\n```'.format(**locals()))

        if table:
            errors.append(str(table))

        infai_1_nodes = set('ase{:02d}.cluster.bc2.ch'.format(i) for i in range(1, 25))
        infai_2_nodes = set('ase{:02d}.cluster.bc2.ch'.format(i) for i in range(31, 55))
        nodes = self._get_node_names()
        if nodes & infai_1_nodes and nodes & infai_2_nodes:
            errors.append('Report combines runs from infai_1 and infai_2 partitions.')

        return '\n'.join(errors)

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
