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

import os
from collections import defaultdict

from lab import tools

from downward.reports.plot import Plot, PlotReport


class ScatterPlotReport(PlotReport):
    """
    Generate a scatter plot for a specific attribute.
    """
    def __init__(self, get_category=None, **kwargs):
        """
        ``kwargs['attributes']`` must contain exactly one attribute.

        *get_category* can be a function that takes **two** runs (dictionaries of
        properties) and returns a category name. This name is used to group the
        points in the plot.
        Runs for which this function returns None are shown in a default category
        and are not contained in the legend.
        For example, to group by domain use::

            def domain_as_category(run1, run2):
                # run2['domain'] has the same value, because we always
                # compare two runs of the same problem
                return run1['domain']

        *get_category* and *category_styles*
        (see :py:class:`PlotReport <downward.reports.plot.PlotReport>`) are best
        used together, e.g. to distinguish between different levels of difficulty::

            def improvement(run1, run2):
                time1 = run1.get('search_time', 1800)
                time2 = run2.get('search_time', 1800)
                if time1 > 10 * time2:
                    return 'strong'
                if time1 >= time2:
                    return 'small'
                return 'worse'

            styles = {
                'strong': ('x','r'),
                'small':  ('*','b'),
                'worse':  ('o','y'),
            }

            PlotReport(attributes=['search_time'],
                       get_category=improvement,
                       category_styles=styles)

        """
        PlotReport.__init__(self, **kwargs)
        assert self.attribute, 'ScatterPlotReport needs exactly one attribute'
        # By default all values are in the same category.
        self.get_category = get_category or (lambda run1, run2: None)

    def _set_scales(self, xscale, yscale):
        # ScatterPlots use symlog scaling on the x-axis by default.
        default_xscale = 'symlog'
        if self.attribute and self.attribute in self.LINEAR:
            default_xscale = 'linear'
        PlotReport._set_scales(self, xscale or default_xscale, yscale)

    def _fill_categories(self, runs):
        # We discard the *runs* parameter.
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
            category = self.get_category(run1, run2)
            categories[category].append((val1, val2))
        return categories

    def _plot(self, axes, categories, styles):
        # Display grid
        axes.grid(b=True, linestyle='-', color='0.75')

        # Find max-value to fit plot and to draw missing values.
        max_value = -1
        for category, coordinates in sorted(categories.items()):
            for x, y in coordinates:
                max_value = max(max_value, x, y)
        missing_val = self._get_missing_val(max_value)

        # Generate the scatter plots
        for category, coordinates in sorted(categories.items()):
            marker, c = styles[category]
            X, Y = zip(*coordinates)
            X = self._replace_none_values(X, missing_val)
            Y = self._replace_none_values(Y, missing_val)
            axes.scatter(X, Y, s=20, marker=marker, c=c, label=category)

        plot_size = missing_val * 1.25

        # Plot a diagonal black line. Starting at (0,0) often raises errors.
        axes.plot([0.001, plot_size], [0.001, plot_size], 'k')

        axes.set_xlim(0, plot_size)
        axes.set_ylim(0, plot_size)

        for axis in [axes.xaxis, axes.yaxis]:
            Plot.change_axis_formatter(axis, missing_val)

        axes.set_xlabel(self.configs[0], fontsize=12)
        axes.set_ylabel(self.configs[1], fontsize=12)

    def write(self):
        if not self.outfile.endswith('.png'):
            self.outfile += '.png'
        tools.makedirs(os.path.dirname(self.outfile))
        self._write_plot(self.runs.values(), self.outfile)
