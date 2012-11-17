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
import fnmatch
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
    MAX_ATTRIBUTE_PARTS = ['score', 'initial_h_value', 'coverage',
                           'quality', 'single_solver', 'avg_h',
                           'offline_abstraction_done']
    ABSOLUTE_ATTRIBUTES = ['coverage', 'quality', 'single_solver', 'unsolvable',
                           '*_error', '*_relative_to_first']

    def __init__(self, resolution, colored=False, **kwargs):
        """
        *resolution* must be one of "domain" or "problem" or "combined" (default).

        If *colored* is True, the values of each row will be given colors from a
        colormap. Only HTML reports can be colored currently.
        """
        PlanningReport.__init__(self, **kwargs)
        assert resolution in ['domain', 'problem', 'combined']
        self.resolution = resolution
        if colored and not 'html' in self.output_format:
            logging.critical('Only HTML reports can be colored.')
        self.colored = colored
        self.toc = False

    def get_markup(self):
        sections = []
        toc_lines = []
        for attribute in self.attributes:
            logging.info('Creating table(s) for %s' % attribute)
            tables = []
            if self.resolution in ['domain', 'combined']:
                tables.append(('', self._get_table(attribute)))
            if self.resolution in ['problem', 'combined']:
                for domain in sorted(self.domains.keys()):
                    tables.append((domain, self._get_table(attribute, domain)))

            parts = []
            toc_line = []
            for (domain, table) in tables:
                if domain:
                    toc_line.append('[""%(domain)s"" #%(attribute)s-%(domain)s]' %
                                    locals())
                    parts.append('== %(domain)s ==[%(attribute)s-%(domain)s]\n'
                                 '%(table)s\n' % locals())
                else:
                    parts.append('%(table)s\n' % locals())

            toc_lines.append('- **[""%s"" #%s]**' % (attribute, attribute))
            toc_lines.append('  - ' + ' '.join(toc_line))
            sections.append((attribute, '\n'.join(parts)))

        if self.resolution == 'domain':
            toc = '- ' + ' '.join('[""%s"" #%s]' % (attr, attr)
                                  for (attr, section) in sections)
        else:
            toc = '\n'.join(toc_lines)

        content = '\n'.join('= %s =[%s]\n\n%s' % (attr, attr, section)
                            for (attr, section) in sections)
        return '%s\n\n\n%s' % (toc, content)

    def _attribute_is_absolute(self, attribute):
        """
        The domain-wise aggregation of the values make sense for some attributes
        like coverage, unsolvable and search_error even if not all configs have
        values for those attributes.
        """
        return any(fnmatch.fnmatch(attribute, abs_attr)
                   for abs_attr in self.ABSOLUTE_ATTRIBUTES)

    def _get_group_func(self, attribute):
        """Decide on a group function for this attribute."""
        if 'score' in attribute:
            # When summarising score results from multiple domains we show
            # normalised averages so that each domain is weighed equally.
            return 'average', reports.avg
        elif (attribute in ['search_time', 'total_time', 'evaluations',
                           'expansions', 'generated'] or
              attribute.endswith('_rel') or
              attribute.endswith('_relative_to_first')):
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
            logging.critical('Domain-wise reports only support numeric attributes, '
                             'but %s is of %s' %
                             (attribute, self._all_attributes[attribute]))
        table = self._get_empty_table(attribute)
        self._add_summary_functions(table, attribute)
        func_name, func = self._get_group_func(attribute)
        num_probs = 0
        self._add_table_info(attribute, func_name, table)
        domain_config_values = defaultdict(list)
        for domain, problems in self.domains.items():
            for problem in problems:
                runs = self.problem_runs[(domain, problem)]
                if (not self._attribute_is_absolute(attribute) and
                        any(run.get(attribute) is None for run in runs)):
                    continue
                num_probs += 1
                for run in runs:
                    value = run.get(attribute)
                    if value is not None:
                        domain_config_values[(domain, run['config'])].append(value)

        # If the attribute is absolute (e.g. coverage, search_error) we may have
        # added problems for which not all configs have a value. Therefore, we
        # can only print the number of instances (in brackets after the domain
        # name) if that number is the same for all configs. If not all configs
        # have values for the same number of problems, we write the full list of
        # different problem numbers.
        num_values_lists = defaultdict(list)
        for domain in self.domains:
            for config in self.configs:
                values = domain_config_values.get((domain, config), [])
                num_values_lists[domain].append(str(len(values)))
        num_values_text = {}
        for domain, num_values_list in num_values_lists.items():
            if len(set(num_values_list)) == 1:
                text = num_values_list[0]
            else:
                text = ','.join(num_values_list)
            num_values_text[domain] = text

        for (domain, config), values in domain_config_values.items():
            table.add_cell('%s (%s)' % (domain, num_values_text[domain]), config,
                           func(values))
        table.num_values = num_probs
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
            min_wins = not any(part in attribute for part in self.MAX_ATTRIBUTE_PARTS)
        else:
            # Do not highlight anything.
            min_wins = None
            colored = False

        table = reports.Table(title=attribute, min_wins=min_wins, colored=colored)
        table.set_column_order(self._get_config_order())
        return table

    def _add_summary_functions(self, table, attribute):
        funcname, func = self._get_group_func(attribute)
        table.add_summary_function(funcname.upper(), func)
        if 'score' in attribute:
            table.add_summary_function('SUM', sum)
