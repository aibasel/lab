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

import logging
import math
import os
import sys
from collections import defaultdict

from lab import tools

from downward.reports.absolute import AbsoluteReport


class ScatterPlotReport(AbsoluteReport):
    """
    Generate a scatter plot for a specific attribute.
    """
    def __init__(self, tuple_category=None, category_styles={}, *args, **kwargs):
        """
        ``kwargs['attributes']`` must contain exactly one attribute.

        **tuple_category** can contain a function taking two dictionaries of run
        properties and returning a string that will be used to group the values.
        For example, to group by domain use::

        def domain_tuple_category(run1, run2):
          return run1['domain'] # run2['domain'] will have the same value

        **category_styles** can be a dictionary that maps category names to tuples
        (marker, color) where marker and color are valid values for pyplot
        (see http://matplotlib.sourceforge.net/api/pyplot_api.html)
        For example to change the default style to blue stars use::

        ScatterPlotReport(attributes=['time'], category_styles={'DEFAULT': ('*','b')})
        """
        self.tuple_category = tuple_category
        self.category_styles = category_styles
        AbsoluteReport.__init__(self, 'problem', *args, **kwargs)
        assert len(self.attributes) == 1, self.attributes

    def write_plot(self, attribute, filename):
        # Import in method to be compatible to rtfd.org
        try:
            from matplotlib.backends import backend_agg
            from matplotlib import figure
        except ImportError, err:
            logging.error('matplotlib could not be found: %s' % err)
            sys.exit(1)

        table = self._get_table(attribute)
        cfg1, cfg2 = table.cols
        columns = table.get_columns()
        assert len(columns[cfg1]) == len(columns[cfg2]), columns

        # It may be the case that no values are found
        try:
            max_value = max(columns[cfg1] + columns[cfg2])
        except ValueError:
            pass

        if max_value is None or max_value <= 0:
            logging.info('Found no valid datapoints for the plot.')
            print table
            sys.exit()

        # Separate the missing values by plotting them at (value * 10) rounded
        # to the next power of 10.
        missing_val = 10 ** math.ceil(math.log10(max_value * 10))

        # Map category names to tuples of 2 lists (values1, values2).
        # The lists contain the values for axis 1 and 2 respectively.
        value_groups = defaultdict(lambda: ([], []))
        for row, val1, val2 in zip(table.rows, columns[cfg1], columns[cfg2]):
            if val1 is None and val2 is None:
                continue
            if val1 is None:
                val1 = missing_val
            if val2 is None:
                val2 = missing_val
            if self.tuple_category is None:
                category = 'DEFAULT'
            else:
                domain, problem = row.split(':')
                run1 = self.runs[(domain, problem, cfg1)]
                run2 = self.runs[(domain, problem, cfg2)]
                category = self.tuple_category(run1, run2)
            value_groups[category][0].append(val1)
            value_groups[category][1].append(val2)

        # Pick any style for categories for which no style is defined.
        # TODO add more possible styles
        possible_styles = [(m, c) for m in 'ox*+' for c in 'rgby']
        missing_category_styles = (set(value_groups.keys()) -
                                   set(self.category_styles.keys()))
        for i, missing in enumerate(missing_category_styles):
            self.category_styles[missing] = possible_styles[i % len(possible_styles)]

        plot_size = missing_val * 1.25

        # Create a figure with size 6 x 6 inches
        fig = figure.Figure(figsize=(10, 10))

        # Create a canvas and add the figure to it
        canvas = backend_agg.FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)

        # Make a descriptive title and set axis labels
        title = ' '.join([attribute, 'by', self.resolution])
        ax.set_title(title, fontsize=14)
        ax.set_xlabel(cfg1, fontsize=12)
        ax.set_ylabel(cfg2, fontsize=12)

        # Display grid
        ax.grid(b=True, linestyle='-', color='0.75')

        # Generate the scatter plots
        for category, (values1, values2) in sorted(value_groups.items()):
            marker, c = self.category_styles[category]
            ax.scatter(values1, values2, s=20, marker=marker, c=c, label=category)

        # Generate a legend if there is at least one non-default category
        if value_groups.keys() != ['DEFAULT']:
            ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

        # Plot a diagonal black line. Starting at (0,0) often raises errors.
        ax.plot([0.001, plot_size], [0.001, plot_size], 'k')

        linear_attributes = ['cost', 'coverage', 'plan_length']
        if attribute not in linear_attributes:
            logging.info('Using logarithmic scaling')
            ax.set_xscale('symlog')
            ax.set_yscale('symlog')

        ax.set_xlim(0, plot_size)
        ax.set_ylim(0, plot_size)

        # We do not want the default formatting that gives zeros a special font
        for axis in (ax.xaxis, ax.yaxis):
            formatter = axis.get_major_formatter()
            old_format_call = formatter.__call__

            def new_format_call(x, pos):
                if x == 0:
                    return 0
                if x == missing_val:
                    return 'Missing'  # '$\mathdefault{None^{\/}}$' no effect
                return old_format_call(x, pos)

            formatter.__call__ = new_format_call

        # Save the generated scatter plot to a PNG file
        canvas.print_figure(filename, dpi=100)

    def write(self):
        assert len(self.configs) == 2, self.configs

        if not self.outfile.endswith('.png'):
            self.outfile += '.png'
        tools.makedirs(os.path.dirname(self.outfile))
        self.write_plot(self.attributes[0], self.outfile)
        logging.info('Wrote file://%s' % self.outfile)
