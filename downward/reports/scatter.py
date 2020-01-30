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

from collections import defaultdict
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

from lab import tools

from downward.reports import PlanningReport
from downward.reports.scatter_matplotlib import ScatterMatplotlib
from downward.reports.scatter_pgfplots import ScatterPgfplots


class ScatterPlotReport(PlanningReport):
    """
    Generate a scatter plot for an attribute.
    """
    def __init__(
            self, relative=False, show_missing=True, get_category=None,
            title=None, scale=None, xlabel='', ylabel='',
            matplotlib_options=None, **kwargs):
        """
        If *relative* is False, create a "standard" scatter plot with a
        diagonal line. If *relative* is True, create a relative scatter
        plot where each point *(x, y)* corresponds to a task for which
        the first algorithm yields a value of *x* and the second
        algorithm yields *x * y*. Relative scatter plots are less common
        in the literature, but often show small differences between
        algorithms better than "standard" scatter plots.

        The keyword argument *attributes* must contain exactly one
        attribute.

        Use the *filter_algorithm* keyword argument to select exactly
        two algorithms (see example below).

        If *show_missing* is False, we only draw a point for an
        algorithm pair if both algorithms have a value.

        *get_category* can be a function that takes **two** runs
        (dictionaries of properties) and returns a category name. This
        name is used to group the points in the plot. If there is more
        than one group, a legend is automatically added. Runs for which
        this function returns None are shown in a default category and
        are not contained in the legend. For example, to group by
        domain:

        >>> def domain_as_category(run1, run2):
        ...     # run2['domain'] has the same value, because we always
        ...     # compare two runs of the same problem.
        ...     return run1['domain']

        Example grouping by difficulty:

        >>> def improvement(run1, run2):
        ...     time1 = run1.get('search_time', 1800)
        ...     time2 = run2.get('search_time', 1800)
        ...     if time1 > time2:
        ...         return 'better'
        ...     if time1 == time2:
        ...         return 'equal'
        ...     return 'worse'

        >>> from downward.experiment import FastDownwardExperiment
        >>> exp = FastDownwardExperiment()
        >>> exp.add_report(ScatterPlotReport(
        ...     attributes=['search_time'],
        ...     get_category=improvement))

        Example comparing the number of expanded states for two
        algorithms:

        >>> exp.add_report(ScatterPlotReport(
        ...         attributes=["expansions_until_last_jump"],
        ...         filter_algorithm=["algorithm-1", "algorithm-2"],
        ...         get_category=domain_as_category,
        ...         format="png",  # Use "tex" for pgfplots output.
        ...         ),
        ...     name="scatterplot-expansions")

        The inherited *format* parameter can be set to 'png' (default),
        'eps', 'pdf', 'pgf' (needs matplotlib 1.2) or 'tex'. For the
        latter a pgfplots plot is created.

        If *title* is given it will be used for the name of the plot.
        Otherwise, the only given attribute will be the title. If none
        is given, there will be no title.

        *scale* can have the values 'linear', 'log' or 'symlog'. If
        omitted, a sensible default will be used for some standard
        attributes and 'log' otherwise. Relative scatter plots always
        use a logarithmic scaling for the *y* axis.

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

        # Backwards compatibility.
        xscale = kwargs.pop('xscale', None)
        yscale = kwargs.pop('yscale', None)
        if xscale or yscale:
            logging.warning('Use "scale" parameter instead of "xscale" and "yscale".')
        scale = scale or xscale or yscale

        PlanningReport.__init__(self, **kwargs)
        self.relative = relative
        if len(self.attributes) != 1:
            logging.critical('ScatterPlotReport needs exactly one attribute')
        self.attribute = self.attributes[0]
        # By default all values are in the same category "None".
        self.get_category = get_category or (lambda run1, run2: None)
        self.show_missing = show_missing
        if self.output_format == 'tex':
            self.writer = ScatterPgfplots
        else:
            self.writer = ScatterMatplotlib
        self.title = title if title is not None else (self.attribute or '')
        self._set_scales(scale)
        self.xlabel = xlabel
        self.ylabel = ylabel
        # If the size has not been set explicitly, make it a square.
        self.matplotlib_options = matplotlib_options or {'figure.figsize': [8, 8]}
        if 'legend.loc' in self.matplotlib_options:
            logging.warning('The "legend.loc" parameter is ignored.')

    def _set_scales(self, scale):
        self.xscale = scale or self.attribute.scale or 'log'
        self.yscale = 'log' if self.relative else self.xscale
        scales = ['linear', 'log', 'symlog']
        for scale in [self.xscale, self.yscale]:
            if scale not in scales:
                logging.critical("Scale {} not in {}".format(scale, scales))

    def has_multiple_categories(self):
        return any(key is not None for key in self.categories.keys())

    def _fill_categories(self):
        """Map category names to coordinate lists."""
        categories = defaultdict(list)
        for runs in self.problem_runs.values():
            try:
                run1, run2 = runs
            except ValueError:
                logging.critical(
                    'Scatter plot needs exactly two runs for {domain}:{problem}. '
                    'Instead of filtering a whole run, try setting only some of its '
                    'attribute values to None in a filter.'.format(**runs[0]))
            category = self.get_category(run1, run2)
            coord = (run1.get(self.attribute), run2.get(self.attribute))
            if self.show_missing or None not in coord:
                categories[category].append(coord)
        return categories

    def _turn_into_relative_coords(self, categories):
        assert self.relative
        y_rel_max = 0
        for coords in categories.values():
            for x, y in coords:
                if (x is not None and x <= 0) or (y is not None and y <= 0):
                    logging.critical("Relative scatter plots need values > 0.")
                if x is not None and y is not None:
                    y_rel_max = max(y_rel_max, y / float(x))
        y_rel_missing = y_rel_max * 1.5 if y_rel_max != 0 else None
        x_missing = self._compute_missing_value(categories, 0, self.xscale)
        self.x_upper = x_missing
        self.y_upper = y_rel_missing

        new_categories = {}
        for category, coords in categories.items():
            new_coords = []
            for coord in coords:
                x, y = coord
                if x is None and y is None:
                    x, y = x_missing, y_rel_missing
                elif x is None and y is not None:
                    x, y = x_missing, 1
                elif x is not None and y is None:
                    x, y = x, y_rel_missing
                elif x is not None and y is not None:
                    x, y = x, y / float(x)
                new_coords.append((x, y))
            if new_coords:
                new_categories[category] = new_coords
        return new_categories

    def _compute_missing_value(self, categories, axis, scale):
        if not self.show_missing:
            return None
        if not any(
            coord[axis] is None for coords in categories.values() for coord in coords):
            return None
        max_value = max(
            coord[axis] for coords in categories.values() for coord in coords
            if coord[axis] is not None)
        if max_value is None:
            return 1
        if scale == 'linear':
            return max_value * 1.1
        return int(10 ** math.ceil(math.log10(max_value)))

    def _handle_non_positive_values(self, categories):
        """Plot integer 0 values at 0.1 in log plots and abort if any value is < 0."""
        assert not self.relative
        assert self.xscale == self.yscale == 'log'
        new_categories = {}
        for category, coords in categories.items():
            new_coords = []
            for x, y in coords:
                if x == 0 and isinstance(x, int):
                    x = 0.1
                if y == 0 and isinstance(y, int):
                    y = 0.1

                if (x is not None and x <= 0) or (y is not None and y <= 0):
                    logging.critical(
                        'Logarithmic axes can only show positive values. '
                        'Use a symlog or linear scale instead.')
                else:
                    new_coords.append((x, y))
            new_categories[category] = new_coords
        return new_categories

    def _handle_missing_values(self, categories):
        assert not self.relative
        x_missing = self._compute_missing_value(categories, 0, self.xscale)
        y_missing = self._compute_missing_value(categories, 1, self.yscale)
        if x_missing is None:
            missing_value = y_missing
        elif y_missing is None:
            missing_value = x_missing
        else:
            missing_value = max(x_missing, y_missing)
        self.x_upper = missing_value
        self.y_upper = missing_value

        if not self.show_missing:
            # Coords with None values have already been filtered.
            return categories

        new_categories = {}
        for category, coords in categories.items():
            coords = [
                (x if x is not None else missing_value,
                 y if y is not None else missing_value) for x, y in coords]
            if coords:
                new_categories[category] = coords
        return new_categories

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

    def _write_plot(self, runs, filename):
        # Map category names to coord tuples.
        self.categories = self._fill_categories()
        if self.relative:
            self.plot_diagonal_line = False
            self.plot_horizontal_line = True
            self.categories = self._turn_into_relative_coords(self.categories)
        else:
            self.plot_diagonal_line = True
            self.plot_horizontal_line = False
            if self.xscale == 'log':
                assert self.yscale == 'log'
                self.categories = self._handle_non_positive_values(self.categories)
            self.categories = self._handle_missing_values(self.categories)
        if not self.categories:
            logging.critical("Plot contains no points.")
        self.styles = self._get_category_styles(self.categories)
        self.writer.write(self, filename)

    def write(self):
        if not len(self.algorithms) == 2:
            logging.critical(
                'Scatter plots need exactly 2 algorithms: %s' % self.algorithms)
        self.xlabel = self.xlabel or self.algorithms[0]
        self.ylabel = self.ylabel or self.algorithms[1]

        suffix = '.' + self.output_format
        if not self.outfile.endswith(suffix):
            self.outfile += suffix
        tools.makedirs(os.path.dirname(self.outfile))
        self._write_plot(self.runs.values(), self.outfile)
