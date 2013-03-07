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

from lab import reports

from lab.reports import DynamicDataModule
from downward.reports.absolute import AbsoluteReport


class CompareRevisionsReport(AbsoluteReport):
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
        AbsoluteReport.__init__(self, **kwargs)
        assert len(revisions) == 2, revisions
        self.revisions = revisions
        self.config_nicks = []

    def _get_config_nick_order(self):
        """
        Extract the config_nicks from the order of columns defined by the
        report. Maintain the order as good as possible by ordering each
        config nick at the relative position where it first occured.
        """
        if self.config_nicks:
            return self.config_nicks
        self.config_nicks = []
        for config in self._get_config_order():
            for rev in self.revisions:
                if config.startswith('%s-' % rev):
                    config_nick = config[len(rev) + 1:]
                    if config_nick not in self.config_nicks:
                        self.config_nicks.append(config_nick)
        return self.config_nicks

    def _get_empty_table(self, attribute=None, title=None, columns=None):
        table = AbsoluteReport._get_empty_table(self, attribute=attribute,
                                                title=title, columns=columns)
        summary_functions = [sum, reports.avg]
        if title == 'summary':
            summary_functions = []
        config_nicks = self._get_config_nick_order()
        diff_module = DiffColumnsModule(config_nicks, self.revisions, summary_functions)
        table.dynamic_data_modules.append(diff_module)
        return table


class DiffColumnsModule(DynamicDataModule):
    """
    Adds multiple columns each comparing the values in two columns that
    contain the same config but different revisions.
    """
    def __init__(self, config_nicks, revisions, summary_functions):
        """
        *config_nicks* is a list of config_nicks for which the diff columns will be added.
        *revisions* is a list of 2 revisions. All columns in the report will be arragned
        such that the configurations given in *config_nicks* run for the given revisions
        are next to each other. After those two columns a diff column is added that shows
        the difference between the two values. All other columns are not printed.
        """
        self.config_nicks = config_nicks
        assert len(revisions) == 2, revisions
        self.revisions = revisions
        self.summary_functions = summary_functions

    def collect(self, table, cells):
        """
        Adds cells for the specified diff columns and dynamically computes their values
        from the respective data columns. If one of the values is None, the difference
        is set to the string '-'. The summary functions are calculated over all values
        were both columns have a value. Also adds an empty header for a dummy column after
        every diff column.
        """
        for config_nick in self.config_nicks:
            non_none_values = []
            col_names = ['%s-%s' % (r, config_nick) for r in self.revisions]
            diff_col_name = 'Diff - %s' % config_nick
            cells[table.header_row][diff_col_name] = diff_col_name
            dummy_col_name = 'DiffDummy - %s' % config_nick
            cells[table.header_row][dummy_col_name] = ''
            for row_name in table.row_names:
                values = [table[row_name].get(col_name, None) for col_name in col_names]
                if any(value is None for value in values):
                    diff = '-'
                else:
                    diff = values[1] - values[0]
                    non_none_values.append(diff)
                cells[row_name][diff_col_name] = diff
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
        for config_nick in self.config_nicks:
            diff_col_name = 'Diff - %s' % config_nick
            for row_name in table.row_names:
                formated_value = formated_cells[row_name][diff_col_name]
                try:
                    value = float(formated_value)
                except:
                    value = 0
                if value == 0:
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
        for config_nick in self.config_nicks:
            if len(new_column_order) > 1:
                new_column_order.append('DiffDummy - %s' % config_nick)
            for rev in self.revisions:
                new_column_order.append('%s-%s' % (rev, config_nick))
            new_column_order.append('Diff - %s' % config_nick)
        return new_column_order

    def modify_printable_row_order(self, table, row_order):
        for func in self.summary_functions:
            func_name = reports.function_name(func)
            if func_name not in row_order:
                row_order.append(func_name)
        return row_order
