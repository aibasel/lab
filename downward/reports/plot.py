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

try:
    import matplotlib
    from matplotlib import figure
    from matplotlib.backends import backend_agg
except ImportError, err:
    logging.critical('matplotlib could not be found: %s' % err)

from lab import tools

from downward.reports import PlanningReport


class Plot(object):
    def __init__(self):
        self.legend = None
        self.create_canvas_and_axes()

    def create_canvas_and_axes(self):
        # Create a figure.
        fig = figure.Figure()

        # Create a canvas and add the figure to it
        self.canvas = backend_agg.FigureCanvasAgg(fig)
        self.axes = fig.add_subplot(111)

    @staticmethod
    def set_rc_params(params):
        # Reset params from rc file.
        matplotlib.rc_file_defaults()
        if params:
            matplotlib.rcParams.update(params)

    @staticmethod
    def change_axis_formatter(axis, missing_val=None):
        formatter = axis.get_major_formatter()
        old_format_call = formatter.__call__

        def new_format_call(x, pos):
            if x == missing_val:
                return 'Missing'
            return old_format_call(x, pos)

        formatter.__call__ = new_format_call

    def create_legend(self, categories, location):
        # Only print a legend if there is at least one non-default category.
        if any(key is not None for key in categories.keys()):
            kwargs = {}
            if isinstance(location, (int, basestring)):
                kwargs['loc'] = location
            else:
                if not isinstance(location, (tuple, list)):
                    logging.critical('location must be a string or a (x, y) pair')
                kwargs['bbox_to_anchor'] = location
                kwargs['loc'] = 'center'
            self.legend = self.axes.legend(scatterpoints=1, **kwargs)

    def print_figure(self, filename):
        # Save the generated scatter plot to a file.
        # Legend is still bugged in mathplotlib, but there is a patch see:
        # http://www.mail-archive.com/matplotlib-users@lists.sourceforge.net/msg20445.html
        extra_artists = []
        if self.legend:
            extra_artists.append(self.legend.legendPatch)
        kwargs = dict(bbox_extra_artists=extra_artists)
        # Note: Setting bbox_inches keyword breaks pgf export.
        if not filename.endswith('pgf'):
            kwargs['bbox_inches'] = 'tight'
        self.canvas.print_figure(filename, **kwargs)
        logging.info('Wrote file://%s' % filename)


class PlotReport(PlanningReport):
    """
    Abstract base class for Plot classes.
    """
    LINEAR = ['cost', 'coverage', 'plan_length', 'initial_h_value']
    LEGEND_POSITIONS = ['upper right', 'upper left', 'lower left', 'lower right',
                        'right', 'center left', 'center right', 'lower center',
                        'upper center', 'center']
    XAXIS_LABEL_PADDING = 5
    YAXIS_LABEL_PADDING = 5

    def __init__(self, title=None, xscale=None, yscale=None, xlabel='', ylabel='',
                 xlim_left=None, xlim_right=None, ylim_bottom=None, ylim_top=None,
                 legend_location='upper right', category_styles=None, params=None,
                 **kwargs):
        """
        If **title** is given it will be used for the name of the plot.
        Otherwise, the only given attribute will be the title. If none is given,
        there will be no title.

        **xscale** and **yscale** can have the values ``linear`` or ``symlog``.
        If omitted sensible defaults will be used.

        **legend_location** must be a (x, y) pair or one of the following strings:
        'upper right', 'upper left', 'lower left', 'lower right', 'right',
        'center left', 'center right', 'lower center', 'upper center', 'center'. ::

            # Some example positions.
            legend_location='lower_left'  # Lower left corner *inside* the plot
            legend_location=(1.1, 0.5)    # Right of the plot
            legend_location=(0.5, 1.1)    # Above the plot
            legend_location=(0.5, -0.1)   # Below the plot

        Subclasses may group the data points into categories. These categories
        are separated visually by drawing them with different styles. You can
        set the styles manually by providing a dictionary *category_styles* that
        maps category names to dictionaries of matplotlib drawing parameters
        (see http://matplotlib.org/api/axes_api.html#matplotlib.axes.Axes.plot).
        For example to change the default style to blue stars use::

            ScatterPlotReport(attributes=['expansions'],
                              category_styles={None: {'marker': '*', 'c': 'b'}})

        **params** may be a dictionary of matplotlib rc parameters
        (see http://matplotlib.org/users/customizing.html)::

            params = {
                'font.family': 'serif',
                'font.weight': 'normal',
                'font.size': 20,  # Used if the more specific sizes are not set.
                'axes.labelsize': 20,
                'axes.titlesize': 30,
                'legend.fontsize': 22,
                'xtick.labelsize': 10,
                'ytick.labelsize': 10,
                'lines.markersize': 10,
                'lines.markeredgewidth': 0.25,
                'lines.linewidth': 1,
                'figure.figsize': [8, 8],  # Width and height in inches.
                'savefig.dpi': 100,
            }
            ScatterPlotReport(attributes=['initial_h_value'], params=params)
        """
        kwargs.setdefault('format', 'png')
        PlanningReport.__init__(self, **kwargs)
        assert len(self.attributes) <= 1, self.attributes
        self.attribute = None
        if self.attributes:
            self.attribute = self.attributes[0]
        self.title = title if title is not None else (self.attribute or '')
        self.legend_location = legend_location

        # Convert the old (marker, color) tuples to the new dict format.
        category_styles = category_styles or {}
        used_old_format = False
        for cat, style in category_styles.items():
            if not isinstance(style, dict):
                assert isinstance(style, (tuple, list)), style
                used_old_format = True
                marker, color = style
                category_styles[cat] = {'marker': marker, 'c': color}
                logging.info('Converted %s to %s' % (style, category_styles[cat]))
        if used_old_format:
            logging.warning('The old category_styles tuple format has been '
                            'deprecated. You should use a dictionary mapping '
                            'category names to dictionaries of matplotlib params '
                            'instead: %s' % category_styles[cat])

        self.category_styles = category_styles
        self._set_scales(xscale, yscale)
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.xlim_left = xlim_left
        self.xlim_right = xlim_right
        self.ylim_bottom = ylim_bottom
        self.ylim_top = ylim_top
        self.params = params

    def _set_scales(self, xscale, yscale):
        self.xscale = xscale or 'linear'
        if yscale:
            self.yscale = yscale
        elif self.attribute and self.attribute in self.LINEAR:
            self.yscale = 'linear'
        else:
            self.yscale = 'symlog'
        scales = ['linear', 'symlog']
        assert self.yscale in scales, self.yscale
        assert self.yscale in scales, self.yscale

    def _get_category_styles(self, categories):
        # Pick any style for categories for which no style is defined.
        styles = self.category_styles.copy()
        unused_styles = [{'marker': m, 'c': c} for m in 'ox+^v<>' for c in 'rgbcmyk'
                         if not any(s.get('marker') == m and
                                    s.get('c') == c for s in styles.values())]
        missing_category_styles = (set(categories.keys()) - set(styles.keys()))
        for i, missing in enumerate(missing_category_styles):
            styles[missing] = unused_styles[i % len(unused_styles)]
        return styles

    def _fill_categories(self, runs):
        raise NotImplementedError

    def _plot(self, axes, categories):
        raise NotImplementedError

    def _write_plot(self, runs, filename):
        Plot.set_rc_params(self.params)
        plot = Plot()
        self.has_points = False
        if self.title:
            plot.axes.set_title(self.title)
        if self.xlabel:
            plot.axes.set_xlabel(self.xlabel, labelpad=self.XAXIS_LABEL_PADDING)
        if self.ylabel:
            plot.axes.set_ylabel(self.ylabel, labelpad=self.YAXIS_LABEL_PADDING)

        # Map category names to value tuples
        categories = self._fill_categories(runs)
        styles = self._get_category_styles(categories)

        plot.axes.set_xscale(self.xscale)
        plot.axes.set_yscale(self.yscale)
        self._plot(plot.axes, categories, styles)

        if not self.has_points:
            logging.info('Found no valid points for plot %s' % filename)
            return

        plot.create_legend(categories, self.legend_location)
        plot.print_figure(filename)

    def write(self):
        raise NotImplementedError


class ProblemPlotReport(PlotReport):
    """
    For each problem generate a plot for a specific attribute.
    """
    def __init__(self, get_points=None, **kwargs):
        """
        *get_points* can be a function that takes a **single** run (dictionary
        of properties) and returns the points that should be drawn for this run.
        The return value can be a list of (x,y) coordinates or a dictionary
        mapping category names to lists of (x,y) coordinates, i.e.::

            get_points(run) == [(1, 1), (2, 4), (3, 9)]
            or
            get_points(run) == {'x^2': [(1, 1), (2, 4), (3, 9)],
                                'x^3': [(1, 1), (2, 8), (3, 27)]}

        Internally all coordinates of a category are combined and drawn in the
        same style (e.g. red circles). Returned lists without a category are
        assigned to a default category that does not appear in the legend.

        If get_points is None **attributes** must contain exactly one attribute.
        Then we will plot the config names on the x-axis and the corresponding
        values for **attribute** on the y-axis. Otherwise **attributes** will be
        ignored and it's up to you to retrieve the y-values from the runs.

        Examples::

            # Plot number of node expansions for all configs.
            ProblemPlotReport(attributes=['expansions'])

            # Compare different ipdb and m&s configurations.
            # configs: 'ipdb-1000', 'ipdb-2000', 'mas-1000', 'mas-2000'
            def config_and_states(run):
                nick, states = run['config_nick'].split('-')
                return {'nick': [(states, run.get('expansions'))]}

            PlotReport(attributes=['expansions'], get_points=config_and_states)

        """
        PlotReport.__init__(self, **kwargs)
        if get_points:
            if self.attribute:
                logging.critical('If get_points() is given, attributes are ignored.')
            self.get_points = get_points
        elif not self.attribute:
            logging.critical('Need exactly one attribute without get_points().')

    def get_points(self, run):
        """
        By default plot the configs on the x-axis and the attribute values on
        the y-axis. All values are in the same category.
        """
        return [(run.get('config'), run.get(self.attribute))]

    def _fill_categories(self, runs):
        categories = defaultdict(list)
        for run in runs:
            new_categories = self.get_points(run)
            if isinstance(new_categories, dict):
                for category, points in new_categories.items():
                    categories[category].extend(points)
            elif isinstance(new_categories, (list, tuple)):
                # Implicitly check that this is a list of pairs.
                for x, y in new_categories:
                    categories[None].append((x, y))
            elif new_categories is not None:
                # Allow returning None.
                logging.critical('get_points() returned the wrong format.')
        return categories

    def _plot(self, axes, categories, styles):
        # Find all x-values.
        all_x = set()
        max_y = -1
        for coordinates in categories.values():
            X, Y = zip(*coordinates)
            all_x |= set(X)
            max_y = max(list(Y) + [max_y])
        all_x = sorted(all_x)

        # Map all x-values to positions on the x-axis.
        indices = dict((val, i) for i, val in enumerate(all_x, start=1))

        # Only use xticks for non-numeric values.
        all_x_numeric = all(isinstance(x, (int, float)) for x in all_x)
        if not all_x_numeric:
            # Reserve space on the x-axis for all x-values and the labels.
            axes.set_xticks(range(1, len(all_x) + 1))
            axes.set_xticklabels(all_x)

        # Plot all categories.
        for category, coords in sorted(categories.items()):
            # The same coordinate may have been added multiple times. To avoid
            # drawing it more than once which results in a bolder spot, we
            # filter duplicate items.
            coords = tools.uniq(coords)
            # Do not include missing values in plot, but reserve spot on x-axis.
            coords = [(x, y) for (x, y) in coords if y is not None]
            if not coords:
                continue
            # Make sure that values are sorted by x, otherwise the wrong points
            # may be connected.
            coords.sort(key=lambda (x, y): x)

            X, Y = zip(*coords)
            if not all_x_numeric:
                X = [indices[val] for val in X]
            axes.plot(X, Y, label=category, **styles[category])
            if X and Y:
                self.has_points = True

        if self.xlim_right:
            xlim_right = self.xlim_right
        elif all_x_numeric:
            xlim_right = max(all_x) * 1.25 if all_x else None
        else:
            xlim_right = len(all_x) + 1
        axes.set_xlim(self.xlim_left or 0, xlim_right)
        axes.set_ylim(self.ylim_bottom or 0, self.ylim_top or max_y * 1.1)
        Plot.change_axis_formatter(axes.yaxis)

    def _write_plots(self, directory):
        for (domain, problem), runs in sorted(self.problem_runs.items()):
            parts = [self.title.lower().replace(' ', '-')] if self.title else []
            parts += [domain, problem]
            path = os.path.join(directory, '-'.join(parts) + '.' + self.output_format)
            self._write_plot(runs, path)

    def write(self):
        if os.path.isfile(self.outfile):
            logging.critical('outfile must be a directory for this report.')
        tools.makedirs(self.outfile)
        self._write_plots(self.outfile)
