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
from collections import defaultdict

from lab import tools

from downward.reports import PlanningReport


class PlotReport(PlanningReport):
    """
    Generate a scatter plot for a specific attribute.
    """
    LINEAR = ['cost', 'coverage', 'plan_length']

    def __init__(self, get_x_and_category=None, category_styles={}, *args, **kwargs):
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
        self.get_x_and_category = get_x_and_category or self._default_get_x_and_category
        self.category_styles = category_styles
        PlanningReport.__init__(self, *args, **kwargs)
        assert len(self.attributes) == 1, self.attributes
        self.attribute = self.attributes[0]

    def _default_get_x_and_category(self, run):
        """
        All points are in the same category and we just number them ascendingly.
        """
        return (run['config'], None)

    def _reset(self):
        self.max_value = self.missing_val = None
        self.axes = self.canvas = self.legend = None
        self._create_canvas_and_axes()

    def _create_canvas_and_axes(self):
        # Import in method to be compatible to rtfd.org
        try:
            from matplotlib.backends import backend_agg
            from matplotlib import figure
        except ImportError, err:
            logging.critical('matplotlib could not be found: %s' % err)

        # Create a figure with size 6 x 6 inches
        fig = figure.Figure(figsize=(10, 10))

        # Create a canvas and add the figure to it
        self.canvas = backend_agg.FigureCanvasAgg(fig)
        self.axes = fig.add_subplot(111)

    def _change_axis_formatter(self, axis):
        # We do not want the default formatting that gives zeros a special font
        formatter = axis.get_major_formatter()
        old_format_call = formatter.__call__

        def new_format_call(x, pos):
            if x == 0:
                return 0
            if x == self.missing_val:
                return 'Missing'  # '$\mathdefault{None^{\/}}$' no effect
            return old_format_call(x, pos)

        formatter.__call__ = new_format_call

    def _create_legend(self, categories):
        # Only print a legend if there is at least one non-default category.
        if any(key is not None for key in categories.keys()):
            self.legend = self.axes.legend(scatterpoints=1, loc='center left',
                                      bbox_to_anchor=(1, 0.5))

    def _fill_categories(self, runs):
        categories = defaultdict(list)
        for run in runs:
            x, category = self.get_x_and_category(run)
            y = run.get(self.attribute)
            if y is None:
                y = self.missing_val
            categories[category].append((x, y))
        return categories

    def _fill_category_styles(self, categories):
        # Pick any style for categories for which no style is defined.
        # TODO: add more possible styles.
        possible_styles = [(m, c) for m in 'ox+^v<>' for c in 'rgby']
        missing_category_styles = (set(categories.keys()) -
                                   set(self.category_styles.keys()))
        for i, missing in enumerate(missing_category_styles):
            self.category_styles[missing] = possible_styles[i % len(possible_styles)]

    def _calc_max_val(self, runs):
        # It may be the case that no values are found.
        try:
            self.max_value = max(run.get(self.attribute) for run in runs)
        except ValueError:
            self.max_value = None

        # Separate the missing values by plotting them at (value * 10) rounded
        # to the next power of 10.
        if self.max_value:
            self.missing_val = 10 ** math.ceil(math.log10(self.max_value * 10))

    def _plot(self, categories):
        max_x = 1
        for category, coordinates in sorted(categories.items()):
            marker, c = self.category_styles[category]
            x, y = zip(*coordinates)
            xticks = range(1, len(x) + 1)
            print category, x, xticks, y
            max_x = max(len(x), max_x)
            self.axes.set_xticks(xticks)
            self.axes.set_xticklabels(x)
            self.axes.plot(xticks, y, marker=marker, c=c, label=category)
        self.axes.set_xlim(left=0, right=max_x + 1)
        self.axes.set_ylim(bottom=0, top=self.missing_val * 1.25)
        self._change_axis_formatter(self.axes.yaxis)
        if self.attribute not in self.LINEAR:
            self.axes.set_yscale('symlog')

        # Make a descriptive title and set axis labels.
        self.axes.set_title(self.attribute, fontsize=14)

    def _print_figure(self, filename):
        # Save the generated scatter plot to a PNG file.
        # Legend is still bugged in mathplotlib, but there is a patch see:
        # http://www.mail-archive.com/matplotlib-users@lists.sourceforge.net/msg20445.html
        extra_artists = []
        if self.legend:
            extra_artists.append(self.legend.legendPatch)
        self.canvas.print_figure(filename, dpi=100, bbox_inches='tight',
                                 bbox_extra_artists=extra_artists)
        logging.info('Wrote file://%s' % filename)

    def write_plot(self, domain, problem, runs, filename):
        self._reset()

        self._calc_max_val(runs)
        if self.max_value is None or self.max_value <= 0:
            logging.info('Found no valid datapoints for the plot.')
            return

        # Map category names to value tuples
        categories = self._fill_categories(runs)
        self._fill_category_styles(categories)

        self._plot(categories)
        self._create_legend(categories)
        self._print_figure(filename)

    def write_plots(self, directory):
        for (domain, problem), runs in sorted(self.problem_runs.items()):
            filename = os.path.join(directory, '-'.join([self.attribute, domain,
                                                         problem]) + '.png')
            self.write_plot(domain, problem, runs, filename)

    def write(self):
        if os.path.isfile(self.outfile):
            logging.critical('outfile must be a directory for this report.')
        tools.makedirs(self.outfile)
        self.write_plots(self.outfile)
