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
import os.path

from lab import tools


class ScatterPgfplots(object):
    @classmethod
    def _get_plot(cls, report):
        lines = []
        options = cls._get_axis_options(report)
        if report.x_upper is not None:
            options['xmax'] = report.x_upper
        if report.y_upper is not None:
            options['ymax'] = report.y_upper
        lines.append('\\begin{axis}[%s]' % cls._format_options(options))
        for category, coords in sorted(report.categories.items()):
            plot = {'only marks': True}
            lines.append(
                '\\addplot+[{}] coordinates {{\n{}\n}};'.format(
                    cls._format_options(plot),
                    ' '.join(str(c) for c in coords)))
            if category:
                lines.append('\\addlegendentry{%s}' % category)
            elif report.has_multiple_categories():
                # None is treated as the default category if using multiple
                # categories. Add a corresponding entry to the legend.
                lines.append('\\addlegendentry{default}')

        if report.plot_horizontal_line:
            # Add black line at y=1.
            lines.append('\\draw[color=black] (axis cs:0,1) -- (axis cs:800000000,1);')
        if report.plot_diagonal_line:
            # Add black diagonal line.
            lines.append('\\draw[color=black] (rel axis cs:0,0) -- (rel axis cs:1,1);')

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
        axis['xlabel'] = report.xlabel
        axis['ylabel'] = report.ylabel
        axis['title'] = report.title
        axis['legend cell align'] = 'left'

        convert_scale = {'log': 'log', 'symlog': 'log', 'linear': 'normal'}
        axis['xmode'] = convert_scale[report.xscale]
        axis['ymode'] = convert_scale[report.yscale]

        # Plot size is set in inches.
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
                opts.append("{}={}".format(key, value.replace("_", "-")))
            else:
                opts.append("{}={}".format(key, value))
        return ", ".join(opts)
