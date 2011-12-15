#! /usr/bin/env python
"""
Module that permits generating reports by reading properties files
"""

from __future__ import with_statement, division

import os
import sys
import logging
import collections
import cPickle
import hashlib
import subprocess
import operator
import math
from collections import defaultdict

from lab import tools
from markup import Document
from lab.external import txt2tags
from lab.external.datasets import missing


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


class ReportArgParser(tools.ArgParser):
    def __init__(self, *args, **kwargs):
        tools.ArgParser.__init__(self, *args, add_help=True, **kwargs)

        self.add_argument('--open', default=False, action='store_true',
                    dest='open_report',
                    help='open the report file after writing it')


class Report(object):
    """
    Base class for all reports
    """
    def __init__(self, attributes=None, format='html', filters=None):
        """
        attributes: the analyzed attributes (e.g. coverage). If omitted, use
                    all found numerical attributes
        filters:    list of functions that are given a run and return True or False
        """
        self.attributes = attributes or []
        assert format in txt2tags.TARGETS
        self.output_format = format
        self.filters = filters or []

        self.report_type = 'report'

    def __call__(self, eval_dir, outfile):
        """
        eval_dir: path to results directory
        """
        if not eval_dir.endswith('eval'):
            msg = ('The source directory does not end with eval. '
                   'Are you sure you this is an evaluation directory? (Y/N): ')
            answer = raw_input(msg)
            if not answer.upper() == 'Y':
                sys.exit()
        self.eval_dir = os.path.abspath(eval_dir)
        self.outfile = outfile

        self.data = self._load_data()
        self.all_attributes = sorted(self.data.get_attributes())
        logging.info('Available attributes: %s' % self.all_attributes)

        if not self.attributes:
            self.attributes = self._get_numerical_attributes()
        else:
            # Make sure that all selected attributes are present in the dataset
            not_found = set(self.attributes) - set(self.all_attributes)
            if not_found:
                logging.error('The following attributes are not present in '
                              'the dataset: %s' % sorted(not_found))
                sys.exit(1)
        self.attributes.sort()
        logging.info('Selected Attributes: %s' % self.attributes)

        self._apply_filters()

        self.infos = []
        self.write()

    def _get_numerical_attributes(self):
        def is_numerical(attribute):
            for val in self.data.key(attribute)[0]:
                if val is missing:
                    continue
                return type(val) in [int, float]
            logging.info("Attribute %s is missing in all runs." % attribute)
            # Include the attribute nonetheless
            return True

        return [attr for attr in self.all_attributes if is_numerical(attr)]

    def add_info(self, info):
        """
        Add strings of additional info to the report
        """
        self.infos.append(info)

    def get_filename(self):
        return os.path.abspath(self.outfile)

    def get_markup(self):
        """
        If get_text() is not overwritten this method can be overwritten in
        subclasses that want to return markup that is converted to text in the
        get_text() method.
        """
        table = Table(highlight=False)
        for run_id, run_group in sorted(self.data.groups('id-string')):
            assert len(run_group) == 1, run_group
            run = run_group.items[0]
            del run['id']
            for key, value in run.items():
                if type(value) is list:
                    run[key] = '-'.join([str(item) for item in value])
            table.add_row(run_id, run)
        return str(table)

    def get_text(self):
        """
        This method should be overwritten in subclasses if the sublass does NOT
        want to return markup text.
        """
        name, ext = os.path.splitext(os.path.basename(self.outfile))
        doc = Document(title=name)
        for info in self.infos:
            doc.add_text('- %s' % info)
        if self.infos:
            doc.add_text('\n\n====================\n')

        markup = self.get_markup()

        if not markup:
            markup = ('No tables were generated. '
                         'This happens when no significant changes occured or '
                         'if for all attributes and all problems never all '
                         'configs had a value for this attribute in a '
                         'domain-wise report. Therefore no output file is '
                         'created.')

        doc.add_text(markup)
        print 'REPORT MARKUP:\n'
        print doc
        return doc.render(self.output_format, {'toc': 1})

    def write(self):
        content = self.get_text()
        filename = self.get_filename()
        tools.makedirs(os.path.dirname(filename))
        with open(filename, 'w') as file:
            file.write(content)
            logging.info('Wrote file://%s' % filename)

    def open(self):
        """
        If the --open parameter is set, tries to open the report
        """
        filename = self.get_filename()
        if not self.open_report or not os.path.exists(filename):
            return

        dir, filename = os.path.split(filename)
        os.chdir(dir)
        if self.output_format == 'tex':
            subprocess.call(['pdflatex', filename])
            filename = filename.replace('tex', 'pdf')
        subprocess.call(['xdg-open', filename])

        # Remove unnecessary files
        extensions = ['aux', 'log']
        filename_prefix, old_ext = os.path.splitext(os.path.basename(filename))
        for ext in extensions:
            tools.remove(filename_prefix + '.' + ext)

    def _load_data(self):
        """
        The data is reloaded for every attribute, but read only once from disk
        """
        combined_props_file = os.path.join(self.eval_dir, 'properties')
        if not os.path.exists(combined_props_file):
            msg = 'Properties file not found at %s'
            logging.error(msg % combined_props_file)
            sys.exit(1)
        dump_path = os.path.join(self.eval_dir, 'data_dump')
        logging.info('Reading properties file without parsing')
        properties_contents = open(combined_props_file).read()
        logging.info('Calculating properties hash')
        new_checksum = hashlib.md5(properties_contents).digest()
        # Reload when the properties file changed or when no dump exists
        reload = True
        if os.path.exists(dump_path):
            logging.info('Reading data dump')
            old_checksum, data = cPickle.load(open(dump_path, 'rb'))
            logging.info('Reading data dump finished')
            reload = (not old_checksum == new_checksum)
            logging.info('Reloading: %s' % reload)
        if reload:
            logging.info('Reading properties file')
            combined_props = tools.Properties(combined_props_file)
            logging.info('Reading properties file finished')
            data = combined_props.get_dataset()
            logging.info('Finished turning properties into dataset')
            # Pickle data for faster future use
            cPickle.dump((new_checksum, data), open(dump_path, 'wb'),
                         cPickle.HIGHEST_PROTOCOL)
            logging.info('Wrote data dump')
        return data

    def _apply_filters(self):
        if self.filters:
            self.data.filter(*self.filters)


class Table(collections.defaultdict):
    def __init__(self, title='', highlight=True, min_wins=True,
                 numeric_rows=False):
        """
        If numeric_rows is True, we do not make the first column bold.
        """
        collections.defaultdict.__init__(self, dict)

        self.title = title
        self.highlight = highlight
        self.min_wins = min_wins
        self.numeric_rows = numeric_rows

        self.summary_funcs = []
        self.column_order = {}
        self.info = []

        self._cols = None

    def add_cell(self, row, col, value):
        self[row][col] = value
        self._cols = None

    def add_row(self, row_name, row):
        """row must map column names to the value in row "row_name"."""
        self[row_name] = row
        self._cols = None

    def add_col(self, col_name, col):
        """col must map row names to values."""
        for row_name, value in col.items():
            self[row_name][col_name] = value
        self._cols = None

    @property
    def rows(self):
        # Let the sum, etc. rows be the last ones
        return tools.natural_sort(self.keys())

    @property
    def cols(self):
        if self._cols:
            return self._cols
        col_names = set()
        for row in self.values():
            col_names |= set(row.keys())
        self._cols = tools.natural_sort(col_names)
        return self._cols

    def get_row(self, row):
        return [self[row].get(col, None) for col in self.cols]

    def get_rows(self):
        return [(row, self.get_row(row)) for row in self.rows]

    def get_columns(self):
        """
        Returns a mapping from column name to the list of values in that column.
        """
        values = defaultdict(list)
        for row in self.rows:
            for col in self.cols:
                values[col].append(self[row].get(col))
        return values

    def get_row_markup(self, row_name, row=None):
        """
        If given, row must be a dictionary mapping column names to the value in
        row "row_name".
        """
        if row is None:
            row = self[row_name]

        values = []
        for col in self.cols:
            values.append(row.get(col))

        only_one_value = len(set(values)) == 1

        # Filter out None values
        real_values = filter(bool, values)

        if real_values:
            min_value = min(real_values)
            max_value = max(real_values)
        else:
            min_value = max_value = 'undefined'

        min_wins = self.min_wins

        text = ''
        if self.numeric_rows:
            text += '| %-30s ' % (row_name)
        else:
            text += '| %-30s ' % ('**' + row_name + '**')
        for value in values:
            is_min = (value == min_value)
            is_max = (value == max_value)
            if self.highlight and only_one_value:
                value_text = '{{%s|color:Gray}}' % value
            elif self.highlight and (min_wins and is_min or
                                        not min_wins and is_max):
                value_text = '**%s**' % value
            else:
                value_text = str(value)
            text += '| %-16s ' % value_text
        text += '|\n'
        return text

    def add_summary_function(self, name, func):
        """
        This function adds a bottom row with the values func(column_values) for
        each column. Func can be e.g. sum, reports.avg, reports.gm
        """
        self.summary_funcs.append((name, func))

    def __str__(self):
        """
        {'zenotravel': {'yY': 17, 'fF': 21}, 'gripper': {'yY': 72, 'fF': 118}}
        ->
        || expanded        | fF               | yY               |
        | **gripper     ** | 118              | 72               |
        | **zenotravel  ** | 21               | 17               |
        """
        text = '|| %-29s | ' % self.title

        def get_col_markup(col):
            # Allow custom sorting of the column names
            if '-SORT:' in col:
                sorting, col = col.split('-SORT:')
            # Escape config names to prevent unvoluntary markup
            return '%-16s' % ('""%s""' % col)

        text += ' | '.join(get_col_markup(col) for col in self.cols) + ' |\n'
        for row in self.rows:
            text += self.get_row_markup(row)
        for name, func in self.summary_funcs:
            summary_row = {}
            for col, content in self.get_columns().items():
                content = [val for val in content if val is not None]
                if content:
                    summary_row[col] = func(content)
                else:
                    summary_row[col] = None
            text += self.get_row_markup(name, summary_row)
        text += ' '.join(self.info)
        return text


if __name__ == "__main__":
    report = Report()
    report.write()
