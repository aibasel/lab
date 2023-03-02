import logging
import sys

import matplotlib
from matplotlib import figure
from matplotlib import lines as mlines
from matplotlib.backends import backend_agg
from matplotlib.ticker import MaxNLocator


class MatplotlibPlot:
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
            scatterpoints=1, loc="center", bbox_to_anchor=(1.3, 0.5)
        )

    @staticmethod
    def _get_max_supported_value(scale):
        if scale == "linear":
            return 10**12  # Larger values cause numerical problems.
        else:
            assert scale in {"log", "symlog"}, scale
            return sys.maxsize

    def plot_diagonal_line(self):
        """Plot a diagonal black line."""
        assert self.axes.get_xscale() == self.axes.get_yscale()
        M = self._get_max_supported_value(self.axes.get_xscale())
        self.axes.add_line(mlines.Line2D([-M, M], [-M, M], color="k", alpha=0.5))

    def plot_horizontal_line(self):
        """Plot a black line at y=1."""
        M = self._get_max_supported_value(self.axes.get_xscale())
        self.axes.add_line(mlines.Line2D([-M, M], [1, 1], color="k", alpha=0.5))

    def print_figure(self, filename):
        # Save the generated scatter plot to a file.
        # Legend is still bugged in matplotlib, but there is a patch see:
        # http://www.mail-archive.com/matplotlib-users@lists.sourceforge.net/msg20445.html
        extra_artists = []
        if self.legend:
            extra_artists.append(self.legend.legendPatch)
        kwargs = {"bbox_extra_artists": extra_artists}
        # Note: Setting bbox_inches keyword breaks pgf export.
        if not filename.endswith("pgf"):
            kwargs["bbox_inches"] = "tight"
        self.canvas.print_figure(filename, **kwargs)
        logging.info(f"Wrote file://{filename}")


class ScatterMatplotlib:
    XAXIS_LABEL_PADDING = 5
    YAXIS_LABEL_PADDING = 5
    TITLE_PADDING = 10

    @classmethod
    def _plot(cls, report, axes):
        axes.grid(True, linestyle="-", color="0.75")

        for category, coords in sorted(report.categories.items()):
            x_vals, y_vals = zip(*coords)
            axes.scatter(
                x_vals, y_vals, clip_on=False, label=category, **report.styles[category]
            )

        axes.set_xbound(upper=report.x_upper)
        axes.set_ybound(upper=report.y_upper)

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

        if report.plot_horizontal_line:
            plot.plot_horizontal_line()
            # Ask for more ticks on y axis in relative plots.
            plot.axes.yaxis.set_major_locator(MaxNLocator(nbins="auto"))
        if report.plot_diagonal_line:
            plot.plot_diagonal_line()

        if report.has_multiple_categories():
            plot.create_legend()
        plot.print_figure(filename)
