# -*- coding: utf-8 -*-
#
# lab is a Python API for running and evaluating algorithms.
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

"""
Module that permits generating reports by reading properties files
"""

from __future__ import with_statement, division

import os
import sys
import logging
import collections
import math
from collections import defaultdict

from lab import tools
from markup import Document
from lab.external import txt2tags


def avg(values):
    """Computes the arithmetic mean of a list of numbers.

    >>> avg([20, 30, 70])
    40.0
    """
    assert len(values) >= 1
    return round(math.fsum(values) / len(values), 4)


def gm(values):
    """Computes the geometric mean of a list of numbers.

    >>> gm([2, 8])
    4.0
    """
    assert len(values) >= 1
    exp = 1.0 / len(values)
    return round(tools.prod([val ** exp for val in values]), 4)


class Report(object):
    """
    Base class for all reports.
    """
    def __init__(self, attributes=None, format='html', filter=None):
        """
        *attributes* is a list of the attributes you want to include in your
        report. If omitted, use all found numerical attributes.

        *format* can be one of e.g. html, tex, wiki (MediaWiki),
        gwiki (Google Code Wiki), doku (DokuWiki), pmw (PmWiki),
        moin (MoinMoin), txt (Plain text) and art (ASCII art).

        If given, *filter* must be a function that is passed a dictionary of a
        run's keys and values and returns True or False. Depending on the
        returned value, the run is included or excluded from the report.
        Alternatively, the function can return a dictionary that will overwrite
        the old run's dictionary for the report.

        Examples:

        Include only *coverage* and *expansions* in the report and write a
        LaTeX file at ``myreport.tex``: ::

            report = Report(attributes=['coverage', 'expansions'], format='tex')
            report(path_to_eval_dir, 'myreport.tex')

        Only include successful runs in the report: ::

            def solved(run):
                return run['coverage']
            report = Report(filter=solved)
            report(path_to_eval_dir, 'myreport.html')

        Filter function that filters, renames and sorts columns: ::

            def paper_configs(run):
                config = run['config'].replace('WORK-', '')
                # We want lama11 to be the leftmost column.
                configs = ['lama11', 'fdss_sat1', 'fdss_sat2']
                paper_names = {'lama11': 'LAMA 2011', 'fdss_sat1': 'FDSS 1',
                               'fdss_sat2': 'FDSS 2'}
                if not config in configs:
                    return False
                pos = configs.index(config)
                # "...:sort:" will be removed in the output and is only used
                # for sorting.
                run['config'] = '%d:sort:%s' % (pos, paper_names[config])
                return run
        """
        self.attributes = attributes or []
        assert format in txt2tags.TARGETS
        self.output_format = format
        self.filter = filter

    def __call__(self, eval_dir, outfile):
        """Make the report.

        *eval_dir* must be a path to an evaluation directory containing a
        ``properties`` file.

        The report will be written to *outfile*.
        """
        if not eval_dir.endswith('-eval'):
            msg = ('The source directory does not end with "-eval". '
                   'Are you sure you this is an evaluation directory? (Y/N): ')
            if not raw_input(msg).upper() == 'Y':
                sys.exit()
        self.eval_dir = os.path.abspath(eval_dir)
        self.outfile = os.path.abspath(outfile)

        self._load_data()
        self._apply_filter()
        self._scan_data()
        logging.info('Available attributes: %s' % self.all_attributes)

        if not self.attributes:
            self.attributes = self._get_numerical_attributes()
        else:
            # Make sure that all selected attributes are present in the dataset
            not_found = set(self.attributes) - set(self.all_attributes)
            if not_found:
                logging.critical('The following attributes are not present in '
                                 'the dataset: %s' % sorted(not_found))
        self.attributes.sort()
        logging.info('Selected Attributes: %s' % self.attributes)

        self.write()

    def _get_numerical_attributes(self):
        def is_numerical(attribute):
            for run_id, run in self.props.items():
                val = run.get(attribute)
                if val is None:
                    continue
                return type(val) in [int, float]
            logging.info("Attribute %s is missing in all runs." % attribute)
            # Include the attribute nonetheless
            return True

        return [attr for attr in self.all_attributes if is_numerical(attr)]

    def get_markup(self):
        """
        If ``get_text()`` is not overwritten, this method can be overwritten in
        subclasses that want to return the report as
        `txt2tags <http://txt2tags.org/>`_ markup. The default ``get_text()``
        method converts that markup into *format*.
        """
        table = Table()
        for run_id, run in self.props.items():
            row = {}
            for key, value in run.items():
                if not key in self.attributes:
                    continue
                if isinstance(value, (list, tuple)):
                    key = '-'.join([str(item) for item in value])
                row[key] = value
            table.add_row(run_id, row)
        return str(table)

    def get_text(self):
        """
        This method should be overwritten in subclasses that want to produce
        e.g. HTML or LaTeX markup or programming code directly instead of
        creating `txt2tags <http://txt2tags.org/>`_ markup.
        """
        name, ext = os.path.splitext(os.path.basename(self.outfile))
        doc = Document(title=name)
        markup = self.get_markup()

        if not markup:
            markup = ('No tables were generated. '
                         'This happens when no significant changes occured or '
                         'if for all attributes and all problems never all '
                         'configs had a value for this attribute in a '
                         'domain-wise report. Therefore no output file is '
                         'created.')

        doc.add_text(markup)
        if len(markup) < 100000:
            print 'REPORT MARKUP:\n'
            print doc
        return doc.render(self.output_format, {'toc': 1})

    def write(self):
        """
        Overwrite this method if you want to write the report directly. You
        should write the report to *outfile*.
        """
        content = self.get_text()
        tools.makedirs(os.path.dirname(self.outfile))
        with open(self.outfile, 'w') as file:
            file.write(content)
            logging.info('Wrote file://%s' % self.outfile)

    def _scan_data(self):
        attributes = set()
        for run_id, run in self.props.items():
            attributes |= set(run.keys())
        self.all_attributes = list(sorted(attributes))

    def _load_data(self):
        combined_props_file = os.path.join(self.eval_dir, 'properties')
        if not os.path.exists(combined_props_file):
            msg = 'Properties file not found at %s'
            logging.critical(msg % combined_props_file)

        logging.info('Reading properties file')
        self.props = tools.Properties(filename=combined_props_file)
        logging.info('Reading properties file finished')

    def _apply_filter(self):
        if not self.filter:
            return
        new_props = tools.Properties()
        for run_id, run in self.props.items():
            result = self.filter(run)
            if not isinstance(result, (dict, bool)):
                logging.critical('Filters must return a dictionary or boolean')
            if not result:
                # Discard runs that returned False or an empty dictionary.
                continue
            # If a dict is returned, use it as the new run,
            # else take the old one.
            if isinstance(result, dict):
                new_props[run_id] = result
            else:
                new_props[run_id] = run
        new_props.filename = self.props.filename
        self.props = new_props


class Table(collections.defaultdict):
    def __init__(self, title='', min_wins=None):
        """
        The *Table* class is realized as a dictionary of dictionaries mapping
        row names to colum names to cell values. To obtain the markup from a
        table, use the ``str()`` function.

        *title* will be printed in the top left cell.

        *min_wins* can be either None, True or False. If it is True (False),
        the cell with the lowest (highest) value in each row will be
        highlighted.

        >>> t = Table(title='expansions')
        >>> t.add_cell('prob1', 'cfg1', 10)
        >>> t.add_cell('prob1', 'cfg2', 20)
        >>> t.add_row('prob2', {'cfg1': 15, 'cfg2': 25})
        >>> print t
        | expansions | cfg1 | cfg2 |
        | prob1      |   10 |   20 |
        | prob2      |   15 |   25 |
        >>> t.rows
        ['prob1', 'prob2']
        >>> t.cols
        ['cfg1', 'cfg2']
        >>> t.get_row('prob2')
        [15, 25]
        >>> t.get_columns()
        {'cfg1': [10, 15], 'cfg2': [20, 25]}
        >>> t.add_summary_function(sum)
        >>> print t
        | expansions | cfg1 | cfg2 |
        | prob1      |   10 |   20 |
        | prob2      |   15 |   25 |
        | SUM        |   25 |   45 |
        """
        collections.defaultdict.__init__(self, dict)

        self.title = title
        self.highlight = min_wins is not None
        self.min_wins = min_wins

        self.summary_funcs = []
        self.info = []
        self.num_values = None

        self._cols = None

    def add_cell(self, row, col, value):
        """Set Table[row][col] = value."""
        self[row][col] = value
        self._cols = None

    def add_row(self, row_name, row):
        """Add a new row called *row_name* to the table.

        *row* must be a mapping from column names to values.
        """
        self[row_name] = row
        self._cols = None

    def add_col(self, col_name, col):
        """Add a new column called *col_name* to the table.

        *col* must be a mapping from row names to values.
        """
        for row_name, value in col.items():
            self[row_name][col_name] = value
        self._cols = None

    @property
    def rows(self):
        """Return all row names in sorted order."""
        # Let the sum, etc. rows be the last ones
        return tools.natural_sort(self.keys())

    @property
    def cols(self):
        """Return all column names in sorted order."""
        if self._cols:
            return self._cols
        col_names = set()
        for row in self.values():
            col_names |= set(row.keys())
        self._cols = tools.natural_sort(col_names)
        return self._cols

    def get_row(self, row):
        """Return a list of the values in *row*."""
        return [self[row].get(col, None) for col in self.cols]

    def get_columns(self):
        """
        Return a mapping from column names to the list of values in that column.
        """
        values = defaultdict(list)
        for row in self.rows:
            for col in self.cols:
                values[col].append(self[row].get(col))
        return values

    def _format_header(self):
        return '|| %-29s | %s |' % (self.title,
               ' | '.join(self._format_column_name(col) for col in self.cols))

    def _format_column_name(self, col):
        """Allow custom sorting of the column names."""
        if ':sort:' in col:
            sorting, col = col.split(':sort:')
        # Allow breaking long configs into multiple lines for html tables.
        col = col.replace('_', '-')
        return ' %15s' % col

    def _format_row_values(self, row_name, row=None):
        """Return a list of formatted values."""
        if row is None:
            row = self[row_name]

        values = [row.get(col) for col in self.cols]
        values = [(round(val, 2) if isinstance(val, float) else val)
                  for val in values]
        only_one_value = len(set(values)) == 1
        real_values = [val for val in values if val is not None]

        if real_values:
            min_value = min(real_values)
            max_value = max(real_values)
        else:
            min_value = max_value = 'undefined'

        parts = ['%-30s' % row_name]
        for value in values:
            if isinstance(value, float):
                value_text = '%.2f' % value
            else:
                value_text = str(value)

            if self.highlight and only_one_value:
                value_text = '{%s|color:Gray}' % value_text
            elif self.highlight and (value == min_value and self.min_wins or
                                     value == max_value and not self.min_wins):
                value_text = '**%s**' % value_text
            parts.append(' %15s' % value_text)
        return parts

    def _get_row_markup(self, row_name, row=None):
        """Return the txt2tags table markup for *row_name*.

        If given, *row* must be a dictionary mapping column names to the value
        in row *row_name*. Otherwise row will be the row named *row_name* (This
        if useful for obtaining markup for rows that are not in the table).
        """
        return '| %s |' % ' | '.join(self._format_row_values(row_name, row))

    def add_summary_function(self, name, func):
        """
        Add a bottom row with the values ``func(column_values)`` for each column.
        *func* can be e.g. ``sum``, ``reports.avg`` or ``reports.gm``.
        """
        self.summary_funcs.append((name, func))

    def __str__(self):
        """Return the txt2tags markup for this table."""
        table_rows = [self._format_header()]
        for row in self.rows:
            table_rows.append(self._get_row_markup(row))
        for name, func in self.summary_funcs:
            summary_row = {}
            for col, content in self.get_columns().items():
                content = [val for val in content if val is not None]
                if content:
                    summary_row[col] = func(content)
                else:
                    summary_row[col] = None
            row_name = '**%s**' % name.capitalize()
            if self.num_values is not None:
                row_name += ' (%d)' % self.num_values
            table_rows.append(self._get_row_markup(row_name, summary_row))
        return '%s\n%s' % ('\n'.join(table_rows), ' '.join(self.info))
