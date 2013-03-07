# -*- coding: utf-8 -*-
#
# downward uses the lab package to conduct experiments with the
# Fast Downward planning system.
#
# Copyright (C) 2012  Florian Pommerening (florian.pommerening@unibas.ch)
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

from downward.reports.absolute import AbsoluteReport
from lab import reports

import logging


class CompareConfigsReport(AbsoluteReport):
    """Allows to compare different configurations."""

    def __init__(self, compare_configs, **kwargs):
        """
        See :py:class:`AbsoluteReport <downward.reports.AbsoluteReport>`
        for inherited parameters.

        See :py:class:`DiffColumnsModule <downward.reports.compare.DiffColumnsModule>`
        for an explanation of how to set the configs to compare with *compare_configs*.
        """
        if 'filter_config' in kwargs or 'filter_config_nick' in kwargs:
            logging.critical('Filtering config(nicks) is not supported in '
                             'CompareConfigsReport. Use the parameter '
                             '"compare_configs" to define which configs are shown '
                             'and in what order they should appear.')
        if compare_configs:
            configs = set()
            for t in compare_configs:
                for config in t[0:2]:
                    configs.add(config)
            print configs
            kwargs['filter_config'] = configs
        AbsoluteReport.__init__(self, **kwargs)
        self._compare_configs = compare_configs

    def _get_compare_configs(self):
        return self._compare_configs

    def _get_empty_table(self, attribute=None, title=None, columns=None):
        table = AbsoluteReport._get_empty_table(self, attribute=attribute,
                                                title=title, columns=columns)
        summary_functions = [sum, reports.avg]
        if title == 'summary':
            summary_functions = []
        diff_module = DiffColumnsModule(self._get_compare_configs(), summary_functions)
        table.dynamic_data_modules.append(diff_module)
        return table


class CompareRevisionsReport(CompareConfigsReport):
    """Allows to compare the same configurations in two revisions of the planner."""
    def __init__(self, revisions, **kwargs):
        """
        See :py:class:`AbsoluteReport <downward.reports.AbsoluteReport>`
        for inherited parameters.

        *revisions* is a list of 2 revisions. All columns in the report will be arragned
        such that the same configurations run for the given revisions are next to each
        other. After those two columns a diff column is added that shows the difference
        between the two values. All other columns are not printed.
        """
        CompareConfigsReport.__init__(self, None, **kwargs)
        assert len(revisions) == 2, revisions
        self._revisions = revisions
        self._config_nicks = []

    def _get_compare_configs(self):
        # Extract the config_nicks from the order of columns defined by the
        # report. Maintain the order as good as possible by ordering each
        # config nick at the relative position where it first occured.
        if not self._config_nicks:
            self._config_nicks = []
            for config in self._get_config_order():
                for rev in self._revisions:
                    if config.startswith('%s-' % rev):
                        config_nick = config[len(rev) + 1:]
                        if config_nick not in self.config_nicks:
                            self.config_nicks.append(config_nick)
        compare_configs = []
        for config_nick in self._config_nicks:
            col_names = ['%s-%s' % (r, config_nick) for r in self._revisions]
            compare_configs.append((col_names[0], col_names[1],
                                   'Diff - %s' % config_nick))
        return compare_configs


class DiffColumnsModule(reports.DynamicDataModule):
    """Adds multiple columns each comparing the values in two configs."""
    def __init__(self, compare_configs, summary_functions):
        """
        *compare_configs* is a list of tuples of 2 or 3 elements. The first two entries in
        each tuple are configs that should be compared. If a third entry is present it
        is used as the name of the column showing the difference between the two configs.
        Otherwise the column will be named 'Diff'.
        All columns in the report will be arragned such that the configurations that are
        compared are next to each other. After those two columns a diff column is added
        that shows the difference between the two values. If a config occurs in more than
        one comparison it is repeated every time. All other columns are not printed.
        For example if the data contains configs A, B, C and D and *compare_configs* is
        [('A', 'B', 'Diff BA'), ('A', 'C')] the resulting columns will be
        'A', 'B', 'Diff BA' (contains B - A), 'A', 'C' , 'Diff' (contains C - A)

        *summary_functions* contains a list of functions that will be calculated for all
        entries in the diff columns.
        """
        self.compare_configs = []
        diff_column_names = set()
        for t in compare_configs:
            diff_name = 'Diff'
            if len(t) == 3:
                diff_name = t[2]
            uniq_count = 0
            uniq_diff_name = diff_name
            while uniq_diff_name in diff_column_names:
                uniq_count += 1
                uniq_diff_name = diff_name + str(uniq_count)
            diff_column_names.add(uniq_diff_name)
            self.compare_configs.append(((t[0], t[1]), diff_name, uniq_diff_name))
        self.summary_functions = summary_functions

    def collect(self, table, cells):
        """
        Adds cells for the specified diff columns and dynamically computes their values
        from the respective data columns. If one of the values is None, the difference
        is set to the string '-'. The summary functions are calculated over all values
        were both columns have a value. Also adds an empty header for a dummy column after
        every diff column.
        """
        for col_names, diff_col_header, diff_col_name in self.compare_configs:
            non_none_values = []
            cells[table.header_row][diff_col_name] = diff_col_header
            for row_name in table.row_names:
                values = [table[row_name].get(col_name, None) for col_name in col_names]
                try:
                    diff = float(values[1]) - float(values[0])
                    non_none_values.append(diff)
                    cells[row_name][diff_col_name] = diff
                except:
                    pass
            for func in self.summary_functions:
                func_name = reports.function_name(func)
                cells[func_name][table.header_column] = func_name.capitalize()
                cells[func_name][diff_col_name] = func(non_none_values)
        return cells

    def format(self, table, formated_cells):
        """
        Formats all columns added by this module. Diff values are green if they are better
        in the second column, red if they are worse and grey if there is no difference.
        "Better" and "worse" are with respect to the min_wins information of the table for
        each row.
        Dummy columns and summary functions are not formatted.
        """
        for col_names, diff_col_header, diff_col_name in self.compare_configs:
            for row_name in table.row_names:
                formated_value = formated_cells[row_name].get(diff_col_name)
                try:
                    value = float(formated_value)
                except:
                    value = '-'
                if value == 0 or value == '-':
                    color = 'grey'
                elif ((value < 0 and table.get_min_wins(row_name)) or
                      (value > 0 and not table.get_min_wins(row_name))):
                    color = 'green'
                else:
                    color = 'red'
                formated_value = '{%s|color:%s}' % (value, color)
                formated_cells[row_name][diff_col_name] = formated_value

    def modify_printable_column_order(self, table, column_order):
        """
        Reorder configs such that it contains only those that for
        self.revisions and the configs that only differ in their revisions
        are next to each other.
        """
        new_column_order = [table.header_column]
        for col_names, diff_col_header, diff_col_name in self.compare_configs:
            if len(new_column_order) > 1:
                new_column_order.append('DiffDummy')
            for col_name in col_names:
                new_column_order.append(col_name)
            new_column_order.append(diff_col_name)
        return new_column_order

    def modify_printable_row_order(self, table, row_order):
        for func in self.summary_functions:
            func_name = reports.function_name(func)
            if func_name not in row_order:
                row_order.append(func_name)
        return row_order
