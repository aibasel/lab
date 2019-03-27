# -*- coding: utf-8 -*-
#
# Downward Lab uses the Lab package to conduct experiments with the
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


MIN_AXIS = 0.05
MIN_VALUE = 0.1


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
    def set_rc_params(matplotlib_options):
        # Reset options from rc file if matplotlib installation supports it.
        if hasattr(matplotlib, 'rc_file_defaults'):
            matplotlib.rc_file_defaults()
        if matplotlib_options:
            matplotlib.rcParams.update(matplotlib_options)

    @staticmethod
    def change_axis_formatter(axis, missing_val=None):
        formatter = axis.get_major_formatter()
        old_format_call = formatter.__call__

        def new_format_call(x, pos):
            if x == missing_val:
                return 'Missing'
            return old_format_call(x, pos)

        formatter.__call__ = new_format_call

    def create_legend(self):
        self.legend = self.axes.legend(
            scatterpoints=1, loc='center', bbox_to_anchor=(1.3, 0.5))

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
        MatplotlibPlot.set_rc_params(report.matplotlib_options)
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

        if report.has_multiple_categories():
            plot.create_legend()
        plot.print_figure(filename)


class PgfPlots(object):
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
    def write(cls, report, filename):
        lines = ([
            r'\documentclass[tikz]{standalone}',
            r'\usepackage{pgfplots}',
            r'\begin{document}',
            r'\begin{tikzpicture}'] +
            cls._get_plot(report) + [
            r'\end{tikzpicture}',
            r'\end{document}'])
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
        figsize = report.matplotlib_options.get('figure.figsize')
        if figsize:
            width, height = figsize
            axis['width'] = '%.2fin' % width
            axis['height'] = '%.2fin' % height

        if report.has_multiple_categories():
            axis['legend style'] = cls._format_options(
                {'legend pos': 'outer north east'})

        return axis

    @classmethod
    def _format_options(cls, options):
        opts = []
        for key, value in sorted(options.items()):
            if value is None or value is False:
                continue
            if isinstance(value, bool) or value is None:
                opts.append(key)
            elif isinstance(value, tools.string_type):
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
    def __init__(
            self, title=None, xscale=None, yscale=None, xlabel='',
            ylabel='', matplotlib_options=None, **kwargs):
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

        *matplotlib_options* may be a dictionary of matplotlib rc
        parameters (see http://matplotlib.org/users/customizing.html):

        >>> from downward.reports.scatter import ScatterPlotReport
        >>> matplotlib_options = {
        ...     'font.family': 'serif',
        ...     'font.weight': 'normal',
        ...     # Used if more specific sizes not set.
        ...     'font.size': 20,
        ...     'axes.labelsize': 20,
        ...     'axes.titlesize': 30,
        ...     'legend.fontsize': 22,
        ...     'xtick.labelsize': 10,
        ...     'ytick.labelsize': 10,
        ...     'lines.markersize': 10,
        ...     'lines.markeredgewidth': 0.25,
        ...     'lines.linewidth': 1,
        ...     # Width and height in inches.
        ...     'figure.figsize': [8, 8],
        ...     'savefig.dpi': 100,
        ... }
        >>> report = ScatterPlotReport(
        ...     attributes=['initial_h_value'],
        ...     matplotlib_options=matplotlib_options)

        You can see the full list of matplotlib options and their
        defaults by executing ::

            import matplotlib
            print matplotlib.rcParamsDefault

        """
        kwargs.setdefault('format', 'png')
        PlanningReport.__init__(self, **kwargs)
        assert len(self.attributes) <= 1, self.attributes
        self.attribute = None
        if self.attributes:
            self.attribute = self.attributes[0]
        self.title = title if title is not None else (self.attribute or '')

        self.category_styles = {}
        self._set_scales(xscale, yscale)
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.xlim_left = None
        self.xlim_right = None
        self.ylim_bottom = None
        self.ylim_top = None
        self.matplotlib_options = matplotlib_options or {}
        if 'legend.loc' in self.matplotlib_options:
            logging.warning('The "legend.loc" parameter is ignored.')
        if self.output_format == 'tex':
            self.writer = PgfPlots
        else:
            self.writer = Matplotlib

    def _set_scales(self, xscale, yscale):
        attribute_scale = self.attribute.scale if self.attribute else None
        self.xscale = xscale or attribute_scale or 'linear'
        self.yscale = yscale or attribute_scale or 'log'
        scales = ['linear', 'log', 'symlog']
        for scale in [self.xscale, self.yscale]:
            if scale not in scales:
                raise ValueError("{} not in {}".format(scale, scales))

    def _get_category_styles(self, categories):
        """
        Create dictionary mapping from category name to marker style.
        Pick random style for categories for which no style is defined.

        Note: Matplotlib 2.0 will gain the option to automatically
        cycle through marker styles. We might want to use that feature
        in the future.

        """
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
            # Logarithmic axes cannot handle values <= 0.
            if self.xscale != 'linear':
                coords = [(handle_zero(x), y) for x, y in coords]
            if self.yscale != 'linear':
                coords = [(x, handle_zero(y)) for x, y in coords]
            new_categories[category] = coords
        return new_categories

    def set_min_max_values(self, categories):
        min_x = sys.maxsize
        min_y = sys.maxsize
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

    def has_multiple_categories(self):
        return any(key is not None for key in self.categories.keys())

    def _write_plot(self, runs, filename):
        # Map category names to coord tuples
        categories = self._fill_categories(runs)
        self.set_min_max_values(categories)
        self.categories = self._prepare_categories(categories)
        self.styles = self._get_category_styles(self.categories)
        self.writer.write(self, filename)

    def write(self):
        raise NotImplementedError
