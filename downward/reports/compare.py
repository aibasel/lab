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
        """Extract the config_nicks from the order of columns defined by the
        report. Maintain the order as good as possible by ordering each
        config nick at the relative position where it first occured."""
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
        compare_configs = []
        for config_nick in config_nicks:
            col_names = ['%s-%s' % (r, config_nick) for r in self.revisions]
            compare_configs.append((col_names[0], col_names[1], 'Diff - %s' % config_nick))
        diff_module = DiffColumnsModule(compare_configs, summary_functions)
        table.dynamic_data_modules.append(diff_module)
        return table

class CompareConfigsReport(AbsoluteReport):
    def __init__(self, compare_configs, **kwargs):
        AbsoluteReport.__init__(self, **kwargs)
        self.compare_configs = compare_configs

    def _get_empty_table(self, attribute=None, title=None, columns=None):
        table = AbsoluteReport._get_empty_table(self, attribute=attribute,
                                                title=title, columns=columns)
        summary_functions = [sum, reports.avg]
        if title == 'summary':
            summary_functions = []
        diff_module = DiffColumnsModule(self.compare_configs, summary_functions)
        table.dynamic_data_modules.append(diff_module)
        return table


class DiffColumnsModule(DynamicDataModule):
    """Adds multiple columns each comparing the values in two columns that
    contain the same config but different revisions."""
        def __init__(self, compare_configs, summary_functions):
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
