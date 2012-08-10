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
import os
from collections import defaultdict

from lab import tools

from downward.reports.plot import PlotReport


class ScatterPlotReport(PlotReport):
    """
    Generate a scatter plot for a specific attribute.
    """
    def __init__(self, get_category=None, category_styles={}, *args, **kwargs):
        """
        ``kwargs['attributes']`` must contain exactly one attribute.

        *get_category* can be a function taking two dictionaries of run
        properties and returning a string that will be used to group the values.
        Runs for which this function returns None are shown in a default category
        and are not contained in the legend.
        For example, to group by domain use::

            def domain_as_category(run1, run2):
                # run2['domain'] has the same value, because we always
                # compare two runs of the same problem
                return run1['domain']

        *category_styles* can be a dictionary that maps category names to tuples
        (marker, color) where marker and color are valid values for pyplot
        (see http://matplotlib.sourceforge.net/api/pyplot_api.html)
        For example to change the default style to blue stars use::

            ScatterPlotReport(attributes=['time'], category_styles={None: ('*','b')})

        *get_category* and *category_styles* are best used together, e.g. to
        highlight a domain or interesting values::

            def my_categories(run1, run2):
                if run1['search_time'] > 10 * run2['search_time']:
                    return 'strong improvement'
                if run1['domain'] == 'gripper':
                    return 'gripper'

            my_styles = {
                'strong improvement': ('x','r'),
                'gripper': ('*','b'),
                None: ('o','y'),
            }

            ScatterPlotReport(attributes=['time'],
                              get_category=my_categories,
                              category_styles=my_styles)
        """
        self.get_category = get_category
        self.category_styles = category_styles
        PlotReport.__init__(self, *args, **kwargs)

    def _fill_categories(self):
        assert len(self.configs) == 2
        # Map category names to value tuples
        categories = defaultdict(list)
        for (domain, problem), (run1, run2) in self.problem_runs.items():
            assert (run1['config'] == self.configs[0] and
                    run2['config'] == self.configs[1])
            val1 = run1.get(self.attribute)
            val2 = run2.get(self.attribute)
            if val1 is None and val2 is None:
                continue
            if val1 is None:
                val1 = self.missing_val
            if val2 is None:
                val2 = self.missing_val
            if self.get_category is None:
                category = None
            else:
                category = self.get_category(run1, run2)
            categories[category].append((val1, val2))
        return categories

    def _plot(self, categories):
        ax = self.axes

        # Display grid
        ax.grid(b=True, linestyle='-', color='0.75')

        # Generate the scatter plots
        for category, coordinates in sorted(categories.items()):
            marker, c = self.category_styles[category]
            ax.scatter(*zip(*coordinates), s=20, marker=marker, c=c, label=category)

        plot_size = self.missing_val * 1.25

        # Plot a diagonal black line. Starting at (0,0) often raises errors.
        ax.plot([0.001, plot_size], [0.001, plot_size], 'k')

        if self.attribute not in self.LINEAR:
            ax.set_xscale('symlog')
            ax.set_yscale('symlog')

        ax.set_xlim(0, plot_size)
        ax.set_ylim(0, plot_size)

        self._change_axis_formatter(ax.xaxis)
        self._change_axis_formatter(ax.yaxis)

        # Make a descriptive title and set axis labels
        self.axes.set_title(self.attribute, fontsize=14)
        self.axes.set_xlabel(self.configs[0], fontsize=12)
        self.axes.set_ylabel(self.configs[1], fontsize=12)

    def write_plot(self, filename):
        self._reset()
        self._calc_max_val(self.runs.values())
        if self.max_value is None or self.max_value <= 0:
            logging.critical('Found no valid datapoints for the plot.')

        categories = self._fill_categories()
        self._fill_category_styles(categories)
        self._plot(categories)
        self._create_legend(categories)
        self._print_figure(filename)

    def write(self):
        if not self.outfile.endswith('.png'):
            self.outfile += '.png'
        tools.makedirs(os.path.dirname(self.outfile))
        self.write_plot(self.outfile)
