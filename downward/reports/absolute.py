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

from lab import reports

from downward.reports import PlanningReport


class AbsoluteReport(PlanningReport):
    """
    Write an absolute report about the attribute attribute, e.g. ::

        || expanded    | fF     | yY     |
        | gripper      | 118    | 72     |
        | zenotravel   | 21     | 17     |
    """
    def __init__(self, resolution, colored=False, **kwargs):
        """
        *resolution* must be one of "domain" or "problem".

        If *colored* is True, the values of each row will be given colors from a
        colormap.
        """
        assert resolution in ['domain', 'problem']
        self.resolution = resolution
        self.colored = colored
        PlanningReport.__init__(self, **kwargs)

    def get_markup(self):
        sections = []
        for attribute in self.attributes:
            logging.info('Creating table(s) for %s' % attribute)
            if self.resolution == 'domain':
                table = self._get_table(attribute)
                # We return None for a table if we don't want to add it
                if table:
                    sections.append((attribute, str(table)))
            else:
                tables = []
                for domain in sorted(self.domains.keys()):
                    table = self._get_table(attribute, domain)
                    # We return None for a table if we don't want to add it
                    if table:
                        tables.append((domain, str(table)))
                if tables:
                    section = '\n'.join(['== %s ==\n%s\n' % (domain, table)
                                         for (domain, table) in tables])
                    sections.append((attribute, section))

        return '\n'.join(['= %s =\n\n%s' % (attr, section)
                          for (attr, section) in sections])

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
            return 'average', reports.avg
        elif attribute in ['search_time', 'total_time']:
            return 'geometric mean', reports.gm
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

    def _get_suite_table(self, attribute):
        if not self.attribute_is_numeric(attribute):
            logging.critical('Domain-wise reports only support numeric attributes.')
        table = self._get_empty_table(attribute)
        self._add_summary_functions(table, attribute)
        func_name, func = self._get_group_func(attribute)
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
        return table

    def _get_domain_table(self, attribute, domain):
        table = self._get_empty_table(attribute)

        for config in self.configs:
            for run in self.domain_config_runs[domain, config]:
                table.add_cell(run['problem'], config, run.get(attribute))
        return table

    def _get_table(self, attribute, domain=None):
        if domain:
            return self._get_domain_table(attribute, domain)
        return self._get_suite_table(attribute)

    def _get_empty_table(self, attribute):
        """Return an empty table."""
        colored = self.colored
        if self.attribute_is_numeric(attribute):
            # Decide whether we want to highlight minima or maxima.
            max_attribute_parts = ['score', 'initial_h_value', 'coverage',
                                   'quality', 'single_solver']
            min_wins = not any(part in attribute for part in max_attribute_parts)
        else:
            # Do not highlight anything.
            min_wins = None
            colored = False

        table = reports.Table(title=attribute, min_wins=min_wins, colored=colored)
        table.set_column_order(self._get_config_order())
        return table

    def _add_summary_functions(self, table, attribute):
        if attribute in ['search_time', 'total_time']:
            table.add_summary_function('GEOMETRIC MEAN', reports.gm)
        else:
            table.add_summary_function('SUM', sum)

        if 'score' in attribute:
            # When summarising score results from multiple domains we show
            # normalised averages so that each domain is weighed equally.
            table.add_summary_function('AVERAGE', reports.avg)
