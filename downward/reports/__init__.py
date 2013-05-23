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
import fnmatch
import logging

from lab import reports
from lab import tools
from lab.reports import Attribute, Report


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
        Attribute('*_error', absolute=True),
    ])

    def __init__(self, derived_properties=None, **kwargs):
        """
        See :py:class:`Report <lab.reports.Report>` for inherited parameters.

        *derived_properties* must be a function or a list of functions taking a
        single argument. This argument is a list of problem runs i.e. it contains
        one run-dictionary for each config in the experiment. The function is
        called for every problem in the suite. A function that computes the
        IPC score based on the results of the experiment is added automatically
        to the *derived_properties* list and serves as an example here:

        .. literalinclude:: ../downward/reports/__init__.py
           :pyobject: quality

        You can include only specific domains or configurations by using
        :py:class:`filters <.Report>`.
        If you provide a list for *filter_config* or *filter_config_nick*, it
        will be used to determine the order of configurations in the report. ::

            # Use a filter function.
            def only_blind_and_lmcut(run):
                return run['config'] in ['WORK-blind', 'WORK-lmcut']
            PlanningReport(filter=only_blind_and_lmcut)

            # Filter with a list and set the order of the configs.
            PlanningReport(filter_config=['WORK-lmcut', 'WORK-blind'])
            PlanningReport(filter_config_nick=['lmcut', 'blind'])

        Tip: When you append ´´_relative´´ to an attribute, you will get a table
        containing the attribute's values of each configuration relative to the
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

        # Remember the order of the configs if it is given as a key word argument filter.
        self.filter_config = tools.make_list(kwargs.get('filter_config') or [])
        self.filter_config_nick = tools.make_list(kwargs.get('filter_config_nick') or [])

        Report.__init__(self, **kwargs)
        self.derived_properties.append(quality)

    def get_text(self):
        markup = Report.get_text(self)
        unxeplained_errors = 0
        for run in self.runs.values():
            if run.get('unexplained_error'):
                logging.warning('Unexplained error in: \'%s\'' % run.get('run_dir'))
                unxeplained_errors += 1
        if unxeplained_errors:
            logging.warning('There were %s runs with unexplained errors.'
                            % unxeplained_errors)
        return markup

    def _prepare_attribute(self, attr):
        if not isinstance(attr, Attribute):
            if attr in self.ATTRIBUTES:
                return self.ATTRIBUTES[attr]
            for pattern in self.ATTRIBUTES.values():
                if fnmatch.fnmatch(attr, pattern):
                    return pattern.copy(attr)
        return Report._prepare_attribute(self, attr)

    def _get_relative_attribute_function(self, attr):
        def relative_attr(runs):
            first_val = runs[0].get(attr)
            for run in runs:
                val = run.get(attr)
                if val and first_val:
                    run['%s_relative' % attr] = val / float(first_val)
        return relative_attr

    def _handle_relative_attributes(self, attributes):
        for attr in attributes:
            if attr.endswith('_relative'):
                # Change name, but keep parameters.
                abs_attr = attr.copy(attr[:-len('_relative')])
                attr.functions = [reports.gm]
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
        domain_config_runs = defaultdict(list)
        runs = {}
        for run_name, run in self.props.items():
            # Sanity checks
            if run.get('stage') == 'search':
                assert 'coverage' in run, ('The run in %s has no coverage value' %
                                           run.get('run_dir'))

            domain, problem, config = run['domain'], run['problem'], run['config']
            problems.add((domain, problem))
            problem_runs[(domain, problem)].append(run)
            domain_config_runs[(domain, config)].append(run)
            runs[(domain, problem, config)] = run
        for domain, problem in problems:
            domains[domain].append(problem)
        self.configs = self._get_config_order()
        self.problems = list(sorted(problems))
        self.domains = domains

        # Sort each entry in problem_runs by their config values.
        def run_key(run):
            return self.configs.index(run['config'])
        for key, run_list in problem_runs.items():
            problem_runs[key] = sorted(run_list, key=run_key)

        self.problem_runs = problem_runs
        self.domain_config_runs = domain_config_runs
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
        assert len(self.domains) * len(self.configs) == len(self.domain_config_runs)
        assert (sum(len(runs) for runs in self.domain_config_runs.values()) ==
                len(self.runs))

    def _compute_derived_properties(self):
        for func in self.derived_properties:
            for (domain, problem), runs in self.problem_runs.items():
                func(runs)
                # Update the data with the new properties.
                for run in runs:
                    run_id = '-'.join((run['config'], run['domain'], run['problem']))
                    self.props[run_id] = run

    def _get_warnings_table(self):
        """
        Returns a :py:class:`Table <lab.reports.Table>` containing one line for
        each run where an unexpected error occured.
        """
        columns = ['domain', 'problem', 'config', 'error',
                   'last_logged_time', 'last_logged_memory']
        table = reports.Table(title='Unexplained errors')
        table.set_column_order(columns)
        for run in self.props.values():
            if run.get('unexplained_error'):
                for column in columns:
                    table.add_cell(run['run_dir'], column, run.get(column, '?'))
        return table

    def _get_config_order(self):
        """ Returns a list of configs in the order that was determined by the user.

        You can use the order of configs in your own custom report subclasses
        by accessing self.configs which is calculated in self._scan_planning_data.

        In order of decreasing priority these are the three ways to determine the order:
        1. A filter for 'config' is given with filter_config.
        2. A filter for 'config_nick' is given with filter_config_nick.
           In this case all configs that are represented by the same nick are sorted
           alphabetically.
        3. If no explicit order is given, the configs will be sorted alphabetically.
        """
        all_configs = set()
        config_nicks_to_config = defaultdict(set)
        for run in self.props.values():
            config = run['config']
            all_configs.add(config)
            # For preprocess experiments config_nick is not set.
            nick = run.get('config_nick', config)
            config_nicks_to_config[nick].add(config)
        if self.filter_config_nick and not self.filter_config:
            for nick in self.filter_config_nick:
                self.filter_config += sorted(config_nicks_to_config[nick])
        if self.filter_config:
            # Other filters may have changed the set of available configs by either
            # removing all runs from one config or changing the run['config'] for a run.
            # Maintain the original order of configs and only keep configs that still
            # have available runs after filtering. Then add all new configs sorted
            # naturally at the end.
            config_order = [c for c in self.filter_config if c in all_configs]
            config_order += list(tools.natural_sort(all_configs -
                                                    set(self.filter_config)))
        else:
            config_order = list(tools.natural_sort(all_configs))
        return config_order
