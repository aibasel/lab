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

import itertools
import logging
import math
import os

try:
    # Python 2
    from itertools import izip
except ImportError:
    # Python 3+
    izip = zip

try:
    import matplotlib
    from matplotlib import figure
    from matplotlib.backends import backend_agg
except ImportError as err:
    logging.warning('matplotlib could not be found: %s' % err)
    logging.warning('You can\'t create any plots on this machine.')

from lab import tools

from downward.reports import PlanningReport


class MatplotlibPlot(object):
    def __init__(self):
        self.legend = None
        self.create_canvas_and_axes()

    def create_canvas_and_axes(self):
        fig = figure.Figure()
        self.canvas = backend_agg.FigureCanvasAgg(fig)
        self.axes = fig.add_subplot(111)

    @staticmethod
    def set_rc_params(matplotlib_options):
        # Reset options from rc file if matplotlib installation supports it.
        if hasattr(matplotlib, 'rc_file_defaults'):
            matplotlib.rc_file_defaults()
        if matplotlib_options:
            matplotlib.rcParams.update(matplotlib_options)

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
        kwargs = {'bbox_extra_artists': extra_artists}
        # Note: Setting bbox_inches keyword breaks pgf export.
        if not filename.endswith('pgf'):
            kwargs['bbox_inches'] = 'tight'
        self.canvas.print_figure(filename, **kwargs)
        logging.info('Wrote file://%s' % filename)


class Matplotlib(object):
    XAXIS_LABEL_PADDING = 5
    YAXIS_LABEL_PADDING = 5
    TITLE_PADDING = 10

    @classmethod
    def _plot(cls, report, axes, categories, styles):
        raise NotImplementedError

    @classmethod
    def write(cls, report, filename, scatter=False):
        MatplotlibPlot.set_rc_params(report.matplotlib_options)
        plot = MatplotlibPlot()
        if report.title:
            plot.axes.set_title(report.title, pad=cls.TITLE_PADDING)
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
        raise NotImplementedError

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
            print(matplotlib.rcParamsDefault)

        """
        kwargs.setdefault('format', 'png')
        PlanningReport.__init__(self, **kwargs)
        assert len(self.attributes) <= 1, self.attributes
        self.attribute = None
        if self.attributes:
            self.attribute = self.attributes[0]
        self.title = title if title is not None else (self.attribute or '')

        self._set_scales(xscale, yscale)
        self.xlabel = xlabel
        self.ylabel = ylabel
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
        """
        shapes = 'x+os^v<>D'
        colors = ['C{}'.format(c) for c in range(10)]

        num_styles = len(shapes) * len(colors)
        styles = [
            {'marker': shape, 'c': color}
            for shape, color in itertools.islice(izip(
                itertools.cycle(shapes), itertools.cycle(colors)), num_styles)]
        assert len({(s['marker'], s['c']) for s in styles}) == num_styles, (
            "The number of shapes and the number of colors must be coprime.")

        category_styles = {}
        for i, category in enumerate(sorted(categories)):
            category_styles[category] = styles[i % len(styles)]
        return category_styles

    def _fill_categories(self):
        raise NotImplementedError

    def _prepare_categories(self, categories):
        new_categories = {}
        for category, coords in categories.items():
            new_coords = []
            for x, y in coords:
                # Plot integer 0 values at 0.1 in log plots.
                if self.xscale == 'log' and x == 0 and isinstance(x, int):
                    x = 0.1
                if self.yscale == 'log' and y == 0 and isinstance(y, int):
                    y = 0.1

                if (self.xscale == 'log' and x is not None and x <= 0) or (
                    self.yscale == 'log' and y is not None and y <= 0):
                    logging.critical(
                        'Logarithmic axes can only show positive values. '
                        'Use a symlog or linear scale instead.')
                else:
                    new_coords.append((x, y))
            new_categories[category] = new_coords
        return new_categories

    def has_multiple_categories(self):
        return any(key is not None for key in self.categories.keys())

    def _compute_missing_value(self, categories):
        if not self.show_missing:
            return None
        if not any(None in coord for coords in categories.values() for coord in coords):
            return None
        max_value = max(max(coord) for coords in categories.values() for coord in coords)
        if self.xscale == 'linear':
            return max_value * 1.1
        return int(10 ** math.ceil(math.log10(max_value)))

    def _write_plot(self, runs, filename):
        # Map category names to coord tuples.
        categories = self._fill_categories()
        self.missing_value = self._compute_missing_value(categories)
        self.categories = self._prepare_categories(categories)
        self.styles = self._get_category_styles(self.categories)
        self.writer.write(self, filename)

    def write(self):
        raise NotImplementedError
