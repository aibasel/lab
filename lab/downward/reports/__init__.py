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
    # TODO: Remove dataset in favor of self.configs, self.problems, self.get_run(domain, problem, config)?
    def __init__(self, *args, **kwargs):
        Report.__init__(self, *args, **kwargs)

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
