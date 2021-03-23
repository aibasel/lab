import logging

from downward.reports.absolute import AbsoluteReport
from lab import reports


class ComparativeReport(AbsoluteReport):
    """Compare pairs of algorithms."""

    def __init__(self, algorithm_pairs, **kwargs):
        """
        See :py:class:`AbsoluteReport <downward.reports.absolute.AbsoluteReport>`
        for inherited parameters.

        *algorithm_pairs* is the list of algorithm pairs you want to
        compare.

        All columns in the report will be arranged such that the
        compared algorithms appear next to each other. After the two
        columns containing absolute values for the compared algorithms,
        a third column ("Diff") is added showing the difference between
        the two values.

        Algorithms may appear in multiple comparisons. Algorithms not
        mentioned in *algorithm_pairs* are not included in the report.

        If you want to compare algorithms A and B, instead of a pair
        ``('A', 'B')`` you may pass a triple ``('A', 'B', 'A vs.
        B')``. The third entry of the triple will be used as the name
        of the corresponding "Diff" column.

        For example, if the properties file contains algorithms A, B, C
        and D and *algorithm_pairs* is ``[('A', 'B', 'Diff BA'), ('A',
        'C')]`` the resulting columns will be A, B, Diff BA (contains B
        - A), A, C , Diff (contains C - A).

        Example:

        >>> from downward.experiment import FastDownwardExperiment
        >>> exp = FastDownwardExperiment()
        >>> algorithm_pairs = [("default-lmcut", "issue123-lmcut", "Diff lmcut")]
        >>> exp.add_report(ComparativeReport(algorithm_pairs, attributes=["coverage"]))

        Example output:

            +----------+---------------+----------------+------------+
            | coverage | default-lmcut | issue123-lmcut | Diff lmcut |
            +==========+===============+================+============+
            | depot    |            15 |             17 |          2 |
            +----------+---------------+----------------+------------+
            | gripper  |             7 |              6 |         -1 |
            +----------+---------------+----------------+------------+

        """
        if "filter_algorithm" in kwargs:
            logging.critical(
                'ComparativeReport doesn\'t support "filter_algorithm". '
                'Use "algorithm_pairs" to select and order algorithms.'
            )
        if algorithm_pairs:
            algos = set()
            for tup in algorithm_pairs:
                for algo in tup[:2]:
                    algos.add(algo)
            kwargs["filter_algorithm"] = algos
        AbsoluteReport.__init__(self, **kwargs)
        self._algorithm_pairs = algorithm_pairs

    def _get_empty_table(self, attribute=None, title=None, columns=None):
        table = AbsoluteReport._get_empty_table(
            self, attribute=attribute, title=title, columns=columns
        )
        summary_functions = [sum, reports.arithmetic_mean]
        if title == "Summary":
            summary_functions = []
        diff_module = DiffColumnsModule(self._algorithm_pairs, summary_functions)
        table.dynamic_data_modules.append(diff_module)
        return table


class DiffColumnsModule(reports.DynamicDataModule):
    """
    Add multiple columns, each comparing the values of two algorithms.
    """

    def __init__(self, algorithm_pairs, summary_functions):
        """
        See :py:class:`.ComparativeReport` for how to choose the
        compared algorithms.

        *summary_functions* is a list of functions that will be
        calculated for all entries in the diff columns.

        Example::

            algorithm_pairs = [
                ('default-lmcut', 'issue123-lmcut', 'Diff (lmcut)'),
                ('default-ff', 'issue123-ff', 'Diff (ff)')]
            summary_functions = [sum, reports.arithmetic_mean]
            diff_module = DiffColumnsModule(algorithm_pairs, summary_functions)
            table.dynamic_data_modules.append(diff_module)

        """
        self.header_names = []
        diff_column_names = set()
        for tup in algorithm_pairs:
            diff_name = "Diff"
            if len(tup) == 3:
                diff_name = tup[2]
            # diff_name is printed in the column header and does not have to be unique.
            # To identify the column we thus calculate a uniqe name.
            uniq_count = 0
            col_name = None
            while col_name is None or col_name in diff_column_names:
                uniq_count += 1
                col_name = f"diff_column_{uniq_count}"
            diff_column_names.add(col_name)
            self.header_names.append(((tup[0], tup[1]), diff_name, col_name))
        self.summary_functions = summary_functions

    @staticmethod
    def _get_function_name(function):
        return reports.function_name(function) + " of diffs"

    def collect(self, table, cells):
        """
        Add cells for the specified diff columns and dynamically compute their values
        from the respective data columns. If one of the values is None, set the difference
        to the string '-'. Calculate the summary functions over all values were both
        columns have a value. Also add an empty header for a dummy column after every diff
        column.
        """
        for col_names, diff_col_header, diff_col_name in self.header_names:
            non_none_values = []
            cells[table.header_row][diff_col_name] = diff_col_header
            for row_name in table.row_names:
                values = [table[row_name].get(col_name, None) for col_name in col_names]
                try:
                    diff = float(values[1]) - float(values[0])
                except (ValueError, TypeError, OverflowError):
                    diff = None
                if diff is not None:
                    non_none_values.append(diff)
                    cells[row_name][diff_col_name] = diff
            for func in self.summary_functions:
                func_name = self._get_function_name(func)
                cells[func_name][table.header_column] = func_name.capitalize()
                cells[func_name][diff_col_name] = (
                    func(non_none_values) if non_none_values else None
                )
        return cells

    def format(self, table, formatted_cells):
        """
        Format all columns added by this module. Diff values are green if they are better
        in the second column, red if they are worse and grey if there is no difference.
        "Better" and "worse" are with respect to the min_wins information of the table for
        each row.
        Do not format dummy columns and summary functions.
        """
        for _, _, diff_col_name in self.header_names:
            for row_name in table.row_names:
                formatted_value = formatted_cells[row_name].get(diff_col_name)
                min_wins = table.get_min_wins(row_name)
                try:
                    value = float(formatted_value)
                except (ValueError, TypeError):
                    value = "-"
                if value == 0 or value == "-" or min_wins is None:
                    color = "grey"
                elif (value < 0 and min_wins) or (value > 0 and not min_wins):
                    color = "green"
                else:
                    color = "red"
                # Add space in front of value to right-justify it.
                formatted_value = f" {{{value}|color:{color}}}"
                formatted_cells[row_name][diff_col_name] = formatted_value

    def modify_printable_column_order(self, table, column_order):
        """
        Reorder algorithms in the order defined by algorithm_pairs.
        Hide all other columns.
        """
        new_column_order = [table.header_column]
        for col_names, _, diff_col_name in self.header_names:
            if len(new_column_order) >= 4:
                new_column_order.append("DiffDummy")
            for col_name in col_names:
                new_column_order.append(col_name)
            new_column_order.append(diff_col_name)
        return new_column_order

    def modify_printable_row_order(self, table, row_order):
        """
        Append lines for all summary functions that are not already used to the row order.
        """
        for func in self.summary_functions:
            func_name = self._get_function_name(func)
            if func_name not in row_order:
                row_order.append(func_name)
        return row_order
