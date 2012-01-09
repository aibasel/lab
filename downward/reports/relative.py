import logging
import sys

from downward.reports.absolute import AbsoluteReport


class RelativeReport(AbsoluteReport):
    """
    Write a relative report about the focus attribute, e.g.

    || expanded        | fF               | yY               |
    | **gripper     ** | 1.0              | 0.6102           |
    | **zenotravel  ** | 1.0              | 0.8095           |
    """
    def __init__(self, resolution, rel_change=0, abs_change=0.0, **kwargs):
        """
        rel_change = Percentage that the value must have changed between two
                     configs to be appended to the result table.
        abs_change = Only add pairs of values to the result if their absolute
                     difference is bigger than this number
        """
        AbsoluteReport.__init__(self, resolution, **kwargs)
        self.rel_change = rel_change
        self.abs_change = abs_change

    def write(self):
        configs = self.get_configs()
        if not len(configs) == 2:
            logging.error('Relative reports are only possible for 2 configs. '
                          'Selected configs: "%s"' % configs)
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

        table.add_col('ZZ1-SORT:Factor', quotient_col)
        #table.add_col('ZZ2-SORT:%-Change', percent_col)
        table.highlight = False
        table.summary_funcs = []
        return table
