# -*- coding: utf-8 -*-
#
# downward uses the lab package to conduct experiments with the
# Fast Downward planning system.
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
import sys

try:
    import matplotlib
    from matplotlib import figure
    from matplotlib.backends import backend_agg
except ImportError as err:
    logging.warning('matplotlib could not be found: %s' % err)
    logging.warning('You can\'t create any plots on this machine.')

from lab import tools

from downward.reports import PlanningReport


MIN_AXIS = 0.005
MIN_VALUE = 0.01


def handle_zero(number):
    if number == 0:
        return MIN_VALUE
    return number


class MatplotlibPlot(object):
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
        # Reset params from rc file if matplotlib installation supports it.
        if hasattr(matplotlib, 'rc_file_defaults'):
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
        if location is not None and any(key is not None for key in categories.keys()):
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
        # Legend is still bugged in matplotlib, but there is a patch see:
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


class Matplotlib(object):
    XAXIS_LABEL_PADDING = 5
    YAXIS_LABEL_PADDING = 5

    @classmethod
    def _plot(cls, report, axes, categories, styles):
        # Find all x-values.
        all_x = set()
        for coordinates in categories.values():
            X, Y = zip(*coordinates)
            all_x |= set(X)
        all_x = sorted(all_x)

        # Map all x-values to positions on the x-axis.
        indices = dict((val, i) for i, val in enumerate(all_x, start=1))

        # Only use xticks for non-numeric values.
        all_x_numeric = all(isinstance(x, (int, float)) for x in all_x)
        if not all_x_numeric:
            # Reserve space on the x-axis for all x-values and the labels.
            axes.set_xticks(range(1, len(all_x) + 1))
            axes.set_xticklabels(all_x)

        has_points = False
        # Plot all categories.
        for category, coords in sorted(categories.items()):
            if not coords:
                continue

            X, Y = zip(*coords)
            if not all_x_numeric:
                X = [indices[value] for value in X]
            axes.plot(X, Y, label=category, **styles[category])
            if X and Y:
                has_points = True

        if report.xlim_right:
            xlim_right = report.xlim_right
        elif all_x_numeric:
            xlim_right = max(all_x) * 1.25 if all_x else None
        else:
            xlim_right = len(all_x) + 1
        axes.set_xlim(report.xlim_left or 0, xlim_right)
        axes.set_ylim(report.ylim_bottom or 0, report.ylim_top or report.max_y * 1.1)
        MatplotlibPlot.change_axis_formatter(axes.yaxis)
        return has_points

    @classmethod
    def write(cls, report, filename, scatter=False):
        MatplotlibPlot.set_rc_params(report.params)
        plot = MatplotlibPlot()
        if report.title:
            plot.axes.set_title(report.title)
        if report.xlabel:
            plot.axes.set_xlabel(report.xlabel, labelpad=cls.XAXIS_LABEL_PADDING)
        if report.ylabel:
            plot.axes.set_ylabel(report.ylabel, labelpad=cls.YAXIS_LABEL_PADDING)

        plot.axes.set_xscale(report.xscale)
        plot.axes.set_yscale(report.yscale)
        has_points = cls._plot(report, plot.axes, report.categories, report.styles)

        if not has_points:
            logging.info('Found no valid points for plot %s' % filename)
            return

        plot.create_legend(report.categories, report.legend_location)
        plot.print_figure(filename)


class PgfPlots(object):
    COLORS = dict((color[0], color) for color in
                  ['red', 'green', 'blue', 'cyan', 'magenta', 'yellow'])
    COLORS['k'] = 'black'
    MARKERS = {'o': '*', 'x': 'x', '+': '+', 's': 'square*',
               '^': 'triangle*', 'v': 'halfsquare*', '<': 'halfsquare left*',
               '>': 'halfsquare right*', 'D': 'diamond*'}
    LOCATIONS = {'upper left': 'north west', 'upper right': 'north east',
                 'lower left': 'south west', 'lower right': 'south east',
                 'right': 'outer north east'}

    @classmethod
    def _get_plot(cls, report):
        lines = []
        opts = cls._format_options(cls._get_axis_options(report))
        lines.append('\\begin{axis}[%s]' % opts)
        for category, coords in sorted(report.categories.items()):
            lines.append('\\addplot coordinates {%s};' % ' '.join(str(c) for c in coords))
            lines.append('\\addlegendentry{%s}' % category)
        lines.append('\\end{axis}')
        return lines

    @classmethod
    def write(cls, report, filename, scatter=False):
        lines = []
        lines.append('\\begin{tikzpicture}')
        lines.extend(cls._get_plot(report))
        lines.append('\\end{tikzpicture}')
        tools.makedirs(os.path.dirname(filename))
        tools.write_file(filename, '\n'.join(lines))
        logging.info('Wrote file://%s' % filename)

    @classmethod
    def _get_axis_options(cls, report):
        axis = {}
        axis['xmin'] = report.xlim_left
        axis['xmax'] = report.xlim_right
        axis['ymin'] = report.ylim_bottom
        axis['ymax'] = report.ylim_top
        axis['xlabel'] = report.xlabel
        axis['ylabel'] = report.ylabel
        axis['title'] = report.title
        axis['legend cell align'] = 'left'

        convert_scale = {'log': 'log', 'symlog': 'log', 'linear': 'normal'}
        axis['xmode'] = convert_scale[report.xscale]
        axis['ymode'] = convert_scale[report.yscale]

        # Height is set in inches.
        figsize = report.params.get('figure.figsize')
        if figsize:
            width, height = figsize
            axis['width'] = '%.2fin' % width
            axis['height'] = '%.2fin' % height

        if report.legend_location:
            axis['legend style'] = cls._format_options(
                cls._get_legend_options(report.legend_location))

        return axis

    @classmethod
    def _get_legend_options(cls, location):
        if location in cls.LOCATIONS.values():
            # Found valid pgfplots location.
            return {'legend pos': location}
        elif location in cls.LOCATIONS:
            # Convert matplotlib location to pgfplots location.
            return {'legend pos': cls.LOCATIONS[location]}
        elif isinstance(location, (list, tuple)):
            return {'at': location}
        else:
            logging.critical(
                'Legend location "{}" is unavailable in pgfplots'.format(
                    location))

    @classmethod
    def _format_options(cls, options):
        opts = []
        for key, value in sorted(options.items()):
            if value is None or value is False:
                continue
            if isinstance(value, bool) or value is None:
                opts.append(key)
            elif isinstance(value, basestring):
                if ' ' in value or '=' in value:
                    value = '{%s}' % value
                opts.append("%s=%s" % (key, value.replace("_", "-")))
            else:
                opts.append("%s=%s" % (key, value))
        return ", ".join(opts)


class PlotReport(PlanningReport):
    """
    Abstract base class for Plot classes.
    """
    # TODO: Move this info to downward.reports.PlanningReport.
    LINEAR = ['cost', 'coverage', 'plan_length', 'initial_h_value']
    LOCATIONS = ['upper right', 'upper left', 'lower left', 'lower right',
                 'right', 'center left', 'center right', 'lower center',
                 'upper center', 'center']

    def __init__(
            self, title=None, xscale=None, yscale=None, xlabel='',
            ylabel='', category_styles=None, params=None, **kwargs):
        """
        The inherited *format* parameter can be set to 'png' (default),
        'eps', 'pdf', 'pgf' (needs matplotlib 1.2) or 'tex'. For the
        latter a pgfplots plot is created.

        If *title* is given it will be used for the name of the plot.
        Otherwise, the only given attribute will be the title. If none
        is given, there will be no title.

        *xscale* and *yscale* can have the values 'linear', 'log' or
        'symlog'. If omitted sensible defaults will be used.

        *xlabel* and *ylabel* are the axis labels.

        Subclasses may group the data points into categories. These
        categories are separated visually by drawing them with
        different styles. You can set the styles manually by providing
        a dictionary *category_styles* that maps category names to
        dictionaries of matplotlib drawing parameters (see
        http://matplotlib.org/api/axes_api.html#matplotlib.axes.Axes.plot).
        For example, to change the default style to blue stars use::

            ScatterPlotReport(
                attributes=['expansions'],
                category_styles={None: {'marker': '*', 'c': 'b'}})

        *params* may be a dictionary of matplotlib rc parameters
        (see http://matplotlib.org/users/customizing.html)::

            params = {
                'font.family': 'serif',
                'font.weight': 'normal',
                'font.size': 20,  # Used if more specific sizes not set.
                'axes.labelsize': 20,
                'axes.titlesize': 30,
                'legend.loc': 'upper right',
                'legend.fontsize': 22,
                'xtick.labelsize': 10,
                'ytick.labelsize': 10,
                'lines.markersize': 10,
                'lines.markeredgewidth': 0.25,
                'lines.linewidth': 1,
                'figure.figsize': [8, 8],  # Width and height in inches.
                'savefig.dpi': 100,
            }
            ScatterPlotReport(
                attributes=['initial_h_value'], params=params)

        You can see the full list of matplotlib rc parameters and their
        defaults by executing ::

            import matplotlib
            print matplotlib.rcParamsDefault

        The rc parameter *legend.loc* can be an (x, y) tuple or one of
        the following strings: 'upper right' (default), 'upper left',
        'lower left', 'lower right', 'right', 'center left', 'center
        right', 'lower center', 'upper center', 'center'. If it is
        None, no legend will be added. ::

            # Some example legend locations.
            'lower left'  # Lower left corner *inside* the plot
            (1.1, 0.5)    # Right of the plot
            (0.5, 1.1)    # Above the plot
            (0.5, -0.1)   # Below the plot

        """
        kwargs.setdefault('format', 'png')
        PlanningReport.__init__(self, **kwargs)
        assert len(self.attributes) <= 1, self.attributes
        self.attribute = None
        if self.attributes:
            self.attribute = self.attributes[0]
        self.title = title if title is not None else (self.attribute or '')

        self.category_styles = category_styles or {}
        self._set_scales(xscale, yscale)
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.xlim_left = None
        self.xlim_right = None
        self.ylim_bottom = None
        self.ylim_top = None
        self.params = params or {}
        self.params.setdefault('legend.loc', 'upper right')
        self.legend_location = self.params.get('legend.loc')
        if self.output_format == 'tex':
            self.writer = PgfPlots
        else:
            self.writer = Matplotlib

    def _set_scales(self, xscale, yscale):
        self.xscale = xscale or 'linear'
        if yscale:
            self.yscale = yscale
        elif self.attribute and self.attribute in self.LINEAR:
            self.yscale = 'linear'
        else:
            self.yscale = 'log'
        scales = ['linear', 'log', 'symlog']
        assert self.xscale in scales, self.xscale
        assert self.yscale in scales, self.yscale

    def _get_category_styles(self, categories):
        # Pick any style for categories for which no style is defined.
        styles = self.category_styles.copy()
        unused_styles = [{'marker': m, 'c': c} for m in 'ox+s^v<>D' for c in 'rgbcmyk'
                         if not any(s.get('marker') == m and
                                    s.get('c') == c for s in styles.values())]
        missing_category_styles = (set(categories.keys()) - set(styles.keys()))
        for i, missing in enumerate(missing_category_styles):
            styles[missing] = unused_styles[i % len(unused_styles)]
        return styles

    def _fill_categories(self, runs):
        raise NotImplementedError

    def _prepare_categories(self, categories):
        new_categories = {}
        for category, coords in categories.items():
            # The same coordinate may have been added multiple times. To avoid
            # drawing it more than once which results in a bolder spot, we
            # filter duplicate items.
            coords = list(set(coords))
            # Logarithmic axes cannot handle values <= 0.
            if self.xscale != 'linear':
                coords = [(handle_zero(x), y) for x, y in coords]
            if self.yscale != 'linear':
                coords = [(x, handle_zero(y)) for x, y in coords]
            new_categories[category] = coords
        return new_categories

    def set_min_max_values(self, categories):
        min_x = sys.maxint
        min_y = sys.maxint
        max_x = MIN_VALUE
        max_y = MIN_VALUE
        for coordinates in categories.values():
            for x, y in coordinates:
                if x is not None:
                    min_x = min(min_x, x)
                    max_x = max(max_x, x)
                if y is not None:
                    min_y = min(min_y, y)
                    max_y = max(max_y, y)
        # Make sure we don't get too low for log plots.
        min_x = max(min_x, MIN_VALUE)
        min_y = max(min_y, MIN_VALUE)
        self.min_x, self.min_y, self.max_x, self.max_y = min_x, min_y, max_x, max_y

    def _write_plot(self, runs, filename):
        # Map category names to coord tuples
        categories = self._fill_categories(runs)
        self.set_min_max_values(categories)
        self.categories = self._prepare_categories(categories)
        self.styles = self._get_category_styles(self.categories)
        self.writer.write(self, filename)

    def write(self):
        raise NotImplementedError
