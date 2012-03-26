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

from collections import defaultdict
import logging

from lab.reports import avg, gm

from downward.reports import PlanningReport


class AbsoluteReport(PlanningReport):
    """
    Write an absolute report about the attribute attribute, e.g.

    || expanded        | fF               | yY               |
    | **gripper     ** | 118              | 72               |
    | **zenotravel  ** | 21               | 17               |
    """
    def __init__(self, resolution, *args, **kwargs):
        """
        resolution: One of "domain" or "problem".
        """
        self.resolution = resolution
        PlanningReport.__init__(self, *args, **kwargs)

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

    def _attribute_is_absolute(self, attribute):
        """
        The domain-wise sum of the values for coverage and *_error even makes
        sense if not all configs have values for those attributes.
        """
        return (attribute in ['coverage', 'quality', 'single_solver'] or
                attribute.endswith('_error'))

    def _get_group_func(self, attribute):
        """Decide on a group function for this attribute."""
        if 'score' in attribute:
            return 'average', avg
        elif attribute in ['search_time', 'total_time']:
            return 'geometric mean', gm
        return 'sum', sum

    def _add_table_info(self, attribute, func_name, table):
        """
        Add some information to the table for attributes where data is missing.
        """
        if self._attribute_is_absolute(attribute):
            return

        table.info.append('Only instances where all configurations have a '
                          'value for "%s" are considered.' % attribute)
        table.info.append('Each table entry gives the %s of "%s" for that '
                          'domain.' % (func_name, attribute))
        summary_names = [name.lower() for name, sum_func in table.summary_funcs]
        if len(summary_names) == 1:
            table.info.append('The last row gives the %s across all domains.' %
                              summary_names[0])
        elif len(summary_names) > 1:
            table.info.append('The last rows give the %s across all domains.' %
                              ' and '.join(summary_names))

    def _get_table(self, attribute):
        table = PlanningReport._get_empty_table(self, attribute)
        func_name, func = self._get_group_func(attribute)

        if self.resolution == 'domain':
            num_values = 0
            self._add_table_info(attribute, func_name, table)
            domain_config_values = defaultdict(list)
            for domain, problems in self.domains.items():
                for problem in problems:
                    runs = self.problem_runs[(domain, problem)]
                    if any(run.get(attribute) is None for run in runs):
                        continue
                    num_values += 1
                    for config in self.configs:
                        value = self.runs[(domain, problem, config)].get(attribute)
                        if value is not None:
                            domain_config_values[(domain, config)].append(value)
            for (domain, config), values in domain_config_values.items():
                table.add_cell('%s (%s)' % (domain, len(values)), config, func(values))
            table.num_values = num_values
        elif self.resolution == 'problem':
            for (domain, problem, config), run in self.runs.items():
                table.add_cell(domain + ':' + problem, config, run.get(attribute))
        return table
