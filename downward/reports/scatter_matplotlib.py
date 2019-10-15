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

try:
    import matplotlib
    from matplotlib import figure
    from matplotlib.backends import backend_agg
    import matplotlib.lines as mlines
except ImportError as err:
    logging.warning('matplotlib not found: {}'.format(err))


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
        # Reset options from rc file.
        matplotlib.rc_file_defaults()
        if matplotlib_options:
            matplotlib.rcParams.update(matplotlib_options)

    def create_legend(self):
        self.legend = self.axes.legend(
            scatterpoints=1, loc='center', bbox_to_anchor=(1.3, 0.5))

    def plot_diagonal_line(self):
        """Plot a diagonal black line."""
        xmin, xmax = self.axes.get_xbound()
        ymin, ymax = self.axes.get_ybound()
        self.axes.add_line(mlines.Line2D([xmin, xmax], [ymin, ymax], color='k', alpha=0.5))

    def plot_horizontal_line(self):
        """Plot a black line at y=1."""
        xmin, xmax = self.axes.get_xbound()
        ymin, ymax = self.axes.get_ybound()
        self.axes.add_line(mlines.Line2D([xmin, xmax], [1, 1], color='k', alpha=0.5))

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
        logging.info('Wrote file://{}'.format(filename))


class ScatterMatplotlib(object):
    XAXIS_LABEL_PADDING = 5
    YAXIS_LABEL_PADDING = 5
    TITLE_PADDING = 10

    @classmethod
    def _plot(cls, report, axes):
        axes.grid(b=True, linestyle='-', color='0.75')

        for category, coords in sorted(report.categories.items()):
            x_vals, y_vals = zip(*coords)
            axes.scatter(
                x_vals, y_vals, clip_on=False, label=category, **report.styles[category])

        if report.missing_value is not None:
            axes.set_xbound(upper=report.missing_value)
            axes.set_ybound(upper=report.missing_value)

    @classmethod
    def write(cls, report, filename):
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
        cls._plot(report, plot.axes)

        if report.relative:
            plot.plot_horizontal_line()
        else:
            plot.plot_diagonal_line()

        if report.has_multiple_categories():
            plot.create_legend()
        plot.print_figure(filename)
