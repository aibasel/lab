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

import fnmatch
import os
import logging
import collections
import math
from collections import defaultdict

from lab import tools
from markup import Document
from lab.external import txt2tags


@tools.remove_none_values
def prod(values):
    """Computes the product of a list of numbers.

    >>> print prod([2, 3, 7])
    42.0
    """
    prod = 1
    for value in values:
        prod *= value
    return prod


@tools.remove_none_values
def avg(values):
    """Compute the arithmetic mean of a list of numbers.

    >>> avg([20, 30, 70])
    40.0
    """
    return round(math.fsum(values) / len(values), 4)


@tools.remove_none_values
def gm(values):
    """Compute the geometric mean of a list of numbers.

    >>> gm([2, 8])
    4.0
    """
    values = [val if val > 0 else 0.1 for val in values]
    exp = 1.0 / len(values)
    return round(prod([val ** exp for val in values]), 4)


@tools.remove_none_values
def minimum(values):
    """Filter out None values and return the minimum.

    If there are only None values, return None.
    """
    return min(values)


@tools.remove_none_values
def maximum(values):
    """Filter out None values and return the maximum.

    If there are only None values, return None.
    """
    return max(values)


@tools.remove_none_values
def stddev(values):
    """Compute the standard deviation of a list of numbers.

    >>> stddev([2, 4, 4, 4, 5, 5, 7, 9])
    2.0
    """
    n = len(values)
    mu = avg(values)
    return math.sqrt((sum((v - mu) ** 2 for v in values) / n))


class Attribute(str):
    """A string subclass for attributes in reports."""
    def __new__(cls, name, **kwargs):
        return str.__new__(cls, name)

    def __init__(self, name, absolute=False, min_wins=True, function=sum):
        """Use this class if your **own** attribute needs a non-default value for:

        * *absolute*: If False, only include tasks for which all task runs have
          values in a domain-wise table (e.g. ``coverage`` is absolute, whereas
          ``expansions`` is not, because we can't compare configurations A and B
          for task X if B has no value for ``expansions``).
        * *min_wins*: Set to True if a smaller value for this attribute is
          better and to False otherwise (e.g. for ``coverage`` *min_wins* is
          False, whereas it is True for ``expansions``).
        * *function*: Set the function that aggregates the values for this
          attribute over multiple runs (e.g. for ``coverage`` this is
          :py:func:`sum`, whereas ``expansions`` uses :py:func:`gm`).

        """
        self.absolute = absolute
        self.min_wins = min_wins
        self.function = function

    def copy(self, name):
        return Attribute(name, absolute=self.absolute, min_wins=self.min_wins,
                         function=self.function)


class Report(object):
    """
    Base class for all reports.
    """
    def __init__(self, attributes=None, format='html', filter=None, **kwargs):
        """
        *attributes* is a list of the attributes you want to include in your
        report. If omitted, use all found numerical attributes. Globbing
        characters * and ? are allowed. Example: ::

            Report(attributes=['translator_time_*'])

        When a report is made, both the available and the selected attributes
        are printed on the commandline.

        *format* can be one of e.g. html, tex, wiki (MediaWiki),
        gwiki (Google Code Wiki), doku (DokuWiki), pmw (PmWiki),
        moin (MoinMoin), txt (Plain text) and art (ASCII art). Subclasses may
        allow additional formats.

        If given, *filter* must be a function or a list of functions that
        are passed a dictionary of a run's keys and values and return
        True or False. Depending on the returned value, the run is included
        or excluded from the report.
        Alternatively, the function can return a dictionary that will overwrite
        the old run's dictionary for the report.

        Filters for properties can be given in shorter form without defining a function
        To include only runs where property p has value v, use *filter_p=v*.
        To include only runs where property p has value v1, v2 or v3, use
        *filter_p=[v1, v2, v3]*.

        Examples:

        Include only *coverage* and *expansions* in the report and write a
        LaTeX file at ``myreport.tex``::

            report = Report(attributes=['coverage', 'expansions'], format='tex')
            report(path_to_eval_dir, 'myreport.tex')

        Only include successful runs in the report::

            report = Report(filter_coverage=1)
            report(path_to_eval_dir, 'myreport.html')

        Only include runs in the report where the time score is better than the
        memory score::

            def better_time_than_memory_score(run):
                return run['score_search_time'] > run['score_memory']
            report = Report(filter=better_time_than_memory_score)
            report(path_to_eval_dir, 'myreport.html')

        Filter function that filters and renames configs with additional sorting::

            def rename_configs(run):
                config = run['config'].replace('WORK-', '')
                paper_names = {'lama11': 'LAMA 2011', 'fdss_sat1': 'FDSS 1',
                               'fdss_sat2': 'FDSS 2'}
                run['config'] = paper_names.get(config, 'unknown')
                return run

            # We want LAMA 2011 to be the leftmost column.
            # Filters defined with key word arguments are evaluated last,
            # so we use the updated config names here.
            configs = ['LAMA 2011', 'FDSS 1', 'FDSS 2']
            Report(filter=rename_configs, filter_config=configs)

        Filter function that only allows runs with a timeout in one of two domains::

            report = Report(attributes=['coverage'],
                            filter_domain=['blocks', 'barman'],
                            filter_search_timeout=1)
        """
        if isinstance(attributes, basestring):
            attributes = [attributes]
        self.attributes = attributes or []
        assert format in txt2tags.TARGETS + ['eps', 'pdf', 'pgf', 'png']
        self.output_format = format
        self.toc = True
        self.run_filter = tools.RunFilter(filter, **kwargs)

    def __call__(self, eval_dir, outfile):
        """Make the report.

        *eval_dir* must be a path to an evaluation directory containing a
        ``properties`` file.

        The report will be written to *outfile*.
        """
        if not eval_dir.endswith('-eval'):
            logging.info('The source directory does not end with "-eval". '
                         'Are you sure this is an evaluation directory?')
        self.eval_dir = os.path.abspath(eval_dir)
        self.outfile = os.path.abspath(outfile)

        # Map from attribute to type.
        self._all_attributes = {}
        self._load_data()
        self._apply_filter()
        self._scan_data()

        # Turn string attributes into instances of Attribute.
        self.attributes = [attr if isinstance(attr, Attribute) else Attribute(attr)
                           for attr in self.attributes]

        # Expand glob characters.
        self.attributes = self._glob_attributes(self.attributes)

        if not self.attributes:
            logging.info('Available attributes: %s' % ', '.join(self.all_attributes))
            logging.info('Using all numerical attributes.')
            self.attributes = self._get_numerical_attributes()

        self.attributes.sort()
        self.write()

    def _glob_attributes(self, attributes):
        expanded_attrs = []
        for attr in attributes:
            matches = fnmatch.filter(self.all_attributes, attr)
            if not matches:
                logging.warning('Attribute %s is not present in the dataset.' %
                                attr)
            # Use the attribute options from the pattern for all matches.
            expanded_attrs.extend([attr.copy(match) for match in matches])
        if attributes and not expanded_attrs:
            logging.critical('No attributes match your patterns.')
        return expanded_attrs

    @property
    def all_attributes(self):
        return sorted(self._all_attributes.keys())

    def _get_numerical_attributes(self):
        return [attr for attr in self._all_attributes.keys()
                if self.attribute_is_numeric(attr)]

    def attribute_is_numeric(self, attribute):
        """Return true if the values for *attribute* are ints or floats.

        If the attribute is None in all runs it may be numeric.

        """
        return self._all_attributes[attribute] in [int, float, None]

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
        return doc.render(self.output_format, {'toc': self.toc})

    def write(self):
        """
        Overwrite this method if you want to write the report directly. You
        should write the report to *self.outfile*.
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
        self._all_attributes = self._get_type_map(attributes)

    def _get_type(self, attribute):
        for run_id, run in self.props.items():
            val = run.get(attribute)
            if val is None:
                continue
            return type(val)
        # Attribute is None in all runs.
        return None

    def _get_type_map(self, attributes):
        return dict(((attr, self._get_type(attr)) for attr in attributes))

    def _load_data(self):
        props_file = os.path.join(self.eval_dir, 'properties')
        if not os.path.exists(props_file):
            logging.critical('Properties file not found at %s' % props_file)

        logging.info('Reading properties file')
        self.props = tools.Properties(filename=props_file)
        logging.info('Reading properties file finished')
        if not self.props:
            logging.critical('properties file in evaluation dir is empty.')

    def _apply_filter(self):
        self.props = self.run_filter.apply(self.props)
        if not self.props:
            logging.critical('All runs have been filtered -> Nothing to report.')


class Table(collections.defaultdict):
    def __init__(self, title='', min_wins=None, colored=False):
        """
        The *Table* class can be useful for `Report` subclasses that want to
        return a table as txt2tags markup. It is realized as a dictionary of
        dictionaries mapping row names to colum names to cell values. To obtain
        the markup from a table, use the ``str()`` function.

        *title* will be printed in the top left cell.

        *min_wins* can be either None, True or False. If it is True (False),
        the cell with the lowest (highest) value in each row will be
        highlighted.

        If *colored* is True, the values of each row will be given colors from a
        colormap.

        >>> t = Table(title='expansions')
        >>> t.add_cell('prob1', 'cfg1', 10)
        >>> t.add_cell('prob1', 'cfg2', 20)
        >>> t.add_row('prob2', {'cfg1': 15, 'cfg2': 25})
        >>> print t
        || expansions |  cfg1 |  cfg2 |
         | prob1      |    10 |    20 |
         | prob2      |    15 |    25 |
        >>> t.rows
        ['prob1', 'prob2']
        >>> t.cols
        ['cfg1', 'cfg2']
        >>> t.get_row('prob2')
        [15, 25]
        >>> t.get_columns() == {'cfg1': [10, 15], 'cfg2': [20, 25]}
        True
        >>> t.add_summary_function('SUM', sum)
        >>> print t
        || expansions |  cfg1 |  cfg2 |
         | prob1      |    10 |    20 |
         | prob2      |    15 |    25 |
         | **SUM**    |    25 |    45 |
        >>> t.set_column_order(['cfg2', 'cfg1'])
        >>> print t
        || expansions |  cfg2 |  cfg1 |
         | prob1      |    20 |    10 |
         | prob2      |    25 |    15 |
         | **SUM**    |    45 |    25 |
        """
        collections.defaultdict.__init__(self, dict)

        self.title = title
        self.min_wins = min_wins
        self.colored = colored

        self.summary_funcs = []
        self.info = []
        self.num_values = None

        self._cols = None

        # For printing.
        self.headers = None
        self.first_col_size = None
        self.column_order = None

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
        # Let the sum, etc. rows be the last ones.
        return tools.natural_sort(self.keys())

    @property
    def cols(self):
        """Return all column names in sorted order."""
        if self._cols:
            return self._cols
        col_names = set()
        for row in self.values():
            col_names |= set(row.keys())
        self._cols = []
        if self.column_order:
            # First use all elements for which we know an order.
            # All remaining elements will be sorted alphabetically.
            self._cols = [c for c in self.column_order if c in col_names]
            col_names -= set(self._cols)
        self._cols += tools.natural_sort(col_names)
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

    def _format_header(self, col_name):
        """Allow custom sorting of the column names."""
        if ':sort:' in col_name:
            sorting, col_name = col_name.split(':sort:')
        # Allow breaking long configs into multiple lines for html tables.
        col_name = col_name.replace('_', '-')
        return col_name

    def _get_headers(self):
        return [self.title] + [self._format_header(col) for col in self.cols]

    def _format_row_values(self, row_name, row=None):
        """Return a list of formatted values."""
        if row is None:
            row = self[row_name]

        values = [row.get(col) for col in self.cols]
        values = [(round(val, 2) if isinstance(val, float) else val)
                  for val in values]
        try:
            only_one_value = len(set(values)) == 1
        except TypeError:
            # values may e.g. contain the unhashable type list.
            only_one_value = False

        real_values = [val for val in values if val is not None]
        if real_values:
            min_value = min(real_values)
            max_value = max(real_values)
        else:
            min_value = max_value = 'undefined'

        highlight = self.min_wins is not None
        colors = tools.get_colors(values, self.min_wins) if self.colored else None
        parts = [row_name]
        for col, value in enumerate(values):
            if isinstance(value, float):
                value_text = '%.2f' % value
            elif isinstance(value, list):
                # Avoid involuntary link markup due to the list brackets.
                value_text = "''%s''" % value
            else:
                value_text = str(value)

            if self.colored:
                color = tools.rgb_fractions_to_html_color(*colors[col])
                value_text = '{%s|color:%s}' % (value_text, color)
            elif highlight and only_one_value:
                value_text = '{%s|color:Gray}' % value_text
            elif highlight and (value == min_value and self.min_wins or
                                value == max_value and not self.min_wins):
                value_text = '**%s**' % value_text
            parts.append(value_text)
        return parts

    def _format_cell(self, col_index, value):
        """Let all columns have minimal but equal width.

        We assume that the contents of the cells are smaller than the widths of
        the columns."""
        if col_index == 0:
            return str(value).ljust(self.first_col_size)
        return ' ' + str(value).rjust(len(self.headers[col_index]))

    def _get_header_markup(self):
        """Return the txt2tags table markup for the headers."""
        return self._get_row_markup(self.headers, template='|| %s |')

    def _get_row_markup(self, cells, template=' | %s |'):
        """Return the txt2tags table markup for one row."""
        return template % ' | '.join(self._format_cell(col, val)
                                     for col, val in enumerate(cells))

    def add_summary_function(self, name, func):
        """
        Add a bottom row with the values ``func(column_values)`` for each column.
        *func* can be e.g. ``sum``, ``reports.avg`` or ``reports.gm``.
        """
        self.summary_funcs.append((name, func))

    def set_column_order(self, order):
        self.column_order = order
        self._cols = None

    def __str__(self):
        """Return the txt2tags markup for this table."""
        self.headers = self._get_headers()
        self.first_col_size = max(len(x) for x in self.rows + [self.title])

        table_rows = [self._format_row_values(row) for row in self.rows]
        for name, func in self.summary_funcs:
            summary_row = {}
            for col, content in self.get_columns().items():
                content = [val for val in content if val is not None]
                if content:
                    summary_row[col] = func(content)
                else:
                    summary_row[col] = None
            row_name = '**%s**' % name
            if self.num_values is not None:
                row_name += ' (%d)' % self.num_values
            table_rows.append(self._format_row_values(row_name, summary_row))
        table_rows = [self._get_row_markup(row) for row in table_rows]
        parts = [self._get_header_markup(), '\n'.join(table_rows)]
        if self.info:
            parts.append(' '.join(self.info))
        return '\n'.join(parts)
