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

    def __init__(self, compared_configs, **kwargs):
        """
        See :py:class:`AbsoluteReport <downward.reports.AbsoluteReport>`
        for inherited parameters.

        See :py:class:`DiffColumnsModule <downward.reports.compare.DiffColumnsModule>`
        for an explanation of how to set the configs to compare with *compared_configs*.
        """
        if 'filter_config' in kwargs or 'filter_config_nick' in kwargs:
            logging.critical('Filtering config(nicks) is not supported in '
                             'CompareConfigsReport. Use the parameter '
                             '"compared_configs" to define which configs are shown '
                             'and in what order they should appear.')
        if compared_configs:
            configs = set()
            for t in compared_configs:
                for config in t[0:2]:
                    configs.add(config)
            print configs
            kwargs['filter_config'] = configs
        AbsoluteReport.__init__(self, **kwargs)
        self._compared_configs = compared_configs

    def _get_compared_configs(self):
        return self._compared_configs

    def _get_empty_table(self, attribute=None, title=None, columns=None):
        table = AbsoluteReport._get_empty_table(self, attribute=attribute,
                                                title=title, columns=columns)
        summary_functions = [sum, reports.avg]
        if title == 'summary':
            summary_functions = []
        diff_module = DiffColumnsModule(self._get_compared_configs(), summary_functions)
        table.dynamic_data_modules.append(diff_module)
        return table


class CompareRevisionsReport(CompareConfigsReport):
    """Allows to compare the same configurations in two revisions of the planner."""
    def __init__(self, rev1, rev2, **kwargs):
        """
        See :py:class:`AbsoluteReport <downward.reports.AbsoluteReport>`
        for inherited parameters.

        *rev1* and *rev2* are the revisions that should be compared. All columns in the
        report will be arranged such that the same configurations run for the given
        revisions are next to each other. After those two columns a diff column is added
        that shows the difference between the two values. All other columns are not
        printed.
        """
        CompareConfigsReport.__init__(self, None, **kwargs)
        self._revisions = [rev1, rev2]
        # Built lazily when actual configs are available
        self._compared_configs = None

    def _get_compared_configs(self):
        # Compared configs are cached to speed up access.
        if self._compared_configs is None:
            # Extract the config_nicks from the order of columns defined by the
            # report. Maintain the order as good as possible by ordering each
            # config nick at the relative position where it first occured.
            config_nicks = []
            for config in self._get_config_order():
                for rev in self._revisions:
                    if config.startswith('%s-' % rev):
                        config_nick = config[len(rev) + 1:]
                        if config_nick not in config_nicks:
                            config_nicks.append(config_nick)
            self._compared_configs = []
            for config_nick in config_nicks:
                col_names = ['%s-%s' % (r, config_nick) for r in self._revisions]
                self._compared_configs.append((col_names[0], col_names[1],
                                   'Diff - %s' % config_nick))
        return self._compared_configs


class DiffColumnsModule(reports.DynamicDataModule):
    """Adds multiple columns each comparing the values in two configs."""
    def __init__(self, compared_configs, summary_functions):
        """
        *compared_configs* is a list of tuples of 2 or 3 elements. The first two entries
        in each tuple are configs that should be compared. If a third entry is present it
        is used as the name of the column showing the difference between the two configs.
        Otherwise the column will be named 'Diff'.
        All columns in the report will be arranged such that the configurations that are
        compared are next to each other. After those two columns a diff column is added
        that shows the difference between the two values. If a config occurs in more than
        one comparison it is repeated every time. Configs that are in the original data
        but are not mentioned in compared_configs are not printed.
        For example if the data contains configs A, B, C and D and *compared_configs* is
        [('A', 'B', 'Diff BA'), ('A', 'C')] the resulting columns will be
        'A', 'B', 'Diff BA' (contains B - A), 'A', 'C' , 'Diff' (contains C - A)

        *summary_functions* contains a list of functions that will be calculated for all
        entries in the diff columns.

        Example::

            compared_configs = [
                ('c406c4f77e13-astar_lmcut', '6e09db9b3003-astar_lmcut', 'Diff (lmcut)'),
                ('c406c4f77e13-astar_ff', '6e09db9b3003-astar_ff', 'Diff (ff)')]
            summary_functions = [sum, reports.avg]
            diff_module = DiffColumnsModule(compared_configs, summary_functions)
            table.dynamic_data_modules.append(diff_module)
        """
        self.compared_configs = []
        diff_column_names = set()
        for t in compared_configs:
            diff_name = 'Diff'
            if len(t) == 3:
                diff_name = t[2]
            # diff_name is printed in the column header and does not have to be unique.
            # To identify the column we thus calculate a uniqe name.
            uniq_count = 0
            col_name = None
            while col_name is None or col_name in diff_column_names:
                uniq_count += 1
                col_name = 'diff_column_%s' % uniq_count
            diff_column_names.add(col_name)
            self.compared_configs.append(((t[0], t[1]), diff_name, col_name))
        self.summary_functions = summary_functions

    def collect(self, table, cells):
        """
        Add cells for the specified diff columns and dynamically compute their values
        from the respective data columns. If one of the values is None, set the difference
        to the string '-'. Calculate the summary functions over all values were both
        columns have a value. Also add an empty header for a dummy column after every diff
        column.
        """
        for col_names, diff_col_header, diff_col_name in self.compared_configs:
            non_none_values = []
            cells[table.header_row][diff_col_name] = diff_col_header
            for row_name in table.row_names:
                values = [table[row_name].get(col_name, None) for col_name in col_names]
                try:
                    diff = float(values[1]) - float(values[0])
                except ValueError:
                    diff = None
                if diff is not None:
                    non_none_values.append(diff)
                    cells[row_name][diff_col_name] = diff
            for func in self.summary_functions:
                func_name = reports.function_name(func)
                cells[func_name][table.header_column] = func_name.capitalize()
                cells[func_name][diff_col_name] = func(non_none_values)
        return cells

    def format(self, table, formatted_cells):
        """
        Format all columns added by this module. Diff values are green if they are better
        in the second column, red if they are worse and grey if there is no difference.
        "Better" and "worse" are with respect to the min_wins information of the table for
        each row.
        Do not format dummy columns and summary functions.
        """
        for col_names, diff_col_header, diff_col_name in self.compared_configs:
            for row_name in table.row_names:
                formatted_value = formatted_cells[row_name].get(diff_col_name)
                try:
                    value = float(formatted_value)
                except ValueError:
                    value = '-'
                if value == 0 or value == '-':
                    color = 'grey'
                elif ((value < 0 and table.get_min_wins(row_name)) or
                      (value > 0 and not table.get_min_wins(row_name))):
                    color = 'green'
                else:
                    color = 'red'
                formatted_value = '{%s|color:%s}' % (value, color)
                formatted_cells[row_name][diff_col_name] = formatted_value

    def modify_printable_column_order(self, table, column_order):
        """
        Reorder configs in the order defined by compared_configs. Hide all other columns.
        """
        new_column_order = [table.header_column]
        for col_names, diff_col_header, diff_col_name in self.compared_configs:
            if len(new_column_order) >= 4:
                new_column_order.append('DiffDummy')
            for col_name in col_names:
                new_column_order.append(col_name)
            new_column_order.append(diff_col_name)
        return new_column_order

    def modify_printable_row_order(self, table, row_order):
        """
        Append lines for all summary functions that are not already used to the row order.
        """
        for func in self.summary_functions:
            func_name = reports.function_name(func)
            if func_name not in row_order:
                row_order.append(func_name)
        return row_order
