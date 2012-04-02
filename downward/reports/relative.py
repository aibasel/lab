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

from __future__ import division

import logging
import sys

from downward.reports.absolute import AbsoluteReport


class RelativeReport(AbsoluteReport):
    def __init__(self, resolution, rel_change=0, abs_change=0.0, **kwargs):
        """
        Compare exactly two configurations.

        *resolution* must be one of "domain" or "problem".

        *rel_change* is the percentage that the value must have changed between
        two configs to be appended to the result table.

        Only add pairs of values to the result if their absolute difference is
        bigger than *abs_change*.
        """
        AbsoluteReport.__init__(self, resolution, **kwargs)
        self.rel_change = rel_change
        self.abs_change = abs_change

    def write(self):
        if not len(self.configs) == 2:
            logging.error('Relative reports are only possible for 2 configs. '
                          'Selected configs: "%s"' % self.configs)
            sys.exit(1)
        AbsoluteReport.write(self)

    def _get_table(self, attribute):
        table = AbsoluteReport._get_table(self, attribute)
        quotient_col = {}
        percent_col = {}

        # Filter those rows which have no significant changes
        for row in table.rows:
            val1, val2 = table.get_row(row)

            # Handle cases where one value is not present (None) or zero
            if not val1 or not val2:
                quotient_col[row] = '---'
                continue

            quotient = val2 / val1
            percent_change = abs(quotient - 1.0) * 100
            abs_change = abs(val1 - val2)

            if (percent_change >= self.rel_change and
                abs_change >= self.abs_change):
                quotient_col[row] = round(quotient, 4)
                percent_col[row] = round(percent_change, 4)
            else:
                del table[row]

        # Add table also if there were missing cells
        if len(quotient_col) == 0:
            logging.info('No changes above for "%s"' % attribute)
            return None

        table.add_col('ZZ1:sort:Factor', quotient_col)
        #table.add_col('ZZ2:sort:%-Change', percent_col)
        table.highlight = False
        table.summary_funcs = []
        return table
