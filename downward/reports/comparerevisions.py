from lab import reports

from lab.reports import DynamicDataModule
from downward.reports.absolute import AbsoluteReport


class CompareRevisionsReport(AbsoluteReport):
    def __init__(self, revisions, **kwargs):
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
                    config_nick = config[len(rev)+1:]
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
    def __init__(self, config_nicks, revisions, summary_functions):
        self.config_nicks = config_nicks
        assert len(revisions) == 2, revisions
        self.revisions = revisions
        self.summary_functions = summary_functions

    def collect(self, table, cells):
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

