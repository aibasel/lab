#! /usr/bin/env python
"""
Module that permits generating downward reports by reading properties files
"""

from __future__ import with_statement, division

import logging

from lab import reports
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


class PlanningReport(Report):
    def __init__(self, *args, **kwargs):
        Report.__init__(self, *args, **kwargs)

        self.problems = []
        self.configs = []

        def filter_by_problem(run):
            """
            If suite is set, only process problems from the suite,
            otherwise process all problems
            """
            return any(prob.domain == run['domain'] and
                       prob.problem == run['problem'] for prob in self.problems)

        def filter_by_config(run):
            """
            If configs is set, only process those configs, otherwise process
            all configs
            """
            return any(config == run['config'] for config in self.configs)

        filter_funcs = []
        if self.configs:
            filter_funcs.append(filter_by_config)
        if self.problems:
            filter_funcs.append(filter_by_problem)
        if filter_funcs:
            self.data.filter(*filter_funcs)

    def get_markup(self):
        # list of (attribute, table) pairs
        tables = []
        for attribute in self.attributes:
            logging.info('Creating table for %s' % attribute)
            table = self._get_table(attribute)
            # We return None for a table if we don't want to add it
            if table:
                tables.append((attribute, str(table)))

        return ''.join(['+ %s +\n%s\n' % (attr, table)
                        for (attr, table) in tables])

    def get_configs(self):
        """Return the list of configs."""
        return list(set([run['config'] for run in self.data]))

    def _get_empty_table(self, attribute):
        '''
        Returns an empty table. Used and filled by subclasses.
        '''
        # Decide whether we want to highlight minima or maxima
        max_attribute_parts = ['score', 'initial_h_value', 'coverage',
                               'quality']
        min_wins = True
        for attr_part in max_attribute_parts:
            if attr_part in attribute:
                min_wins = False
        table = PlanningTable(attribute, min_wins=min_wins)
        return table
