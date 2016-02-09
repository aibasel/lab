# -*- coding: utf-8 -*-
#
# downward uses the lab package to conduct experiments with the
# Fast Downward planning system.
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

from __future__ import division

import logging

from lab import reports

from downward.reports.absolute import AbsoluteReport

NOT_AVAILABLE = None


class RelativeReport(AbsoluteReport):
    def __init__(self, resolution='combined', rel_change=0.0, abs_change=0, **kwargs):
        """
        Compare exactly two algorithms. For each problem and attribute
        add a table row with the two absolute values and their quotient.

        *resolution* must be one of "domain" or "problem".

        Only include pairs of attribute values x and y if
        abs(y/x - 1) >= *rel_change*.

        Only include pairs of values if their absolute difference is
        bigger than *abs_change*.

        If neither *rel_change* nor *abs_change* are given, no problem
        rows are filtered out.

        """
        AbsoluteReport.__init__(self, resolution, **kwargs)
        self.rel_change = rel_change
        self.abs_change = abs_change

    def write(self):
        if not len(self.algorithms) == 2:
            logging.critical(
                'Relative reports need exactly 2 algorithms. '
                'Selected algorithms: "%s"' % self.algorithms)
        AbsoluteReport.write(self)

    def _get_table(self, attribute, domain=None):
        table = AbsoluteReport._get_table(self, attribute, domain)
        quotient_col = {}
        percent_col = {}

        # Filter those rows which have no significant changes
        for row in table.row_names:
            val1, val2 = table.get_row(row)

            if not val1 and not val2:
                # Delete row if both values are missing (None) or 0.
                del table[row]
                continue
            elif val1 is None or val2 is None:
                # Don't add quotient if exactly one value is None.
                quotient_col[row] = NOT_AVAILABLE
                continue

            abs_change = abs(val1 - val2)

            if val1 == 0 or val2 == 0:
                # If one value is 0, only add row if the change is big enough.
                if abs_change >= self.abs_change:
                    quotient_col[row] = NOT_AVAILABLE
                else:
                    del table[row]
                continue

            quotient = val2 / val1
            percent_change = abs(quotient - 1.0)

            if (percent_change >= self.rel_change and
                    abs_change >= self.abs_change):
                quotient_col[row] = quotient
                percent_col[row] = percent_change
            else:
                del table[row]

        # Add table also if there were missing cells
        if len(quotient_col) == 0:
            return 'No changes.'

        table.set_column_order(table.col_names + ['Factor'])
        table.add_col('Factor', quotient_col)
        table.add_col('%-Change', percent_col)
        table.min_wins = None
        table.colored = False
        return table

    def _add_summary_functions(self, table, attribute):
        for funcname, func in [
                ('avg', reports.avg), ('min', reports.minimum),
                ('max', reports.maximum), ('StdDev', reports.stddev)]:
            table.add_summary_function(funcname.capitalize(), func)
