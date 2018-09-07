# -*- coding: utf-8 -*-
#
# Lab is a Python package for evaluating algorithms.
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

from lab.reports import Report


class FilterReport(Report):
    """Filter properties files.

    This report only applies the given filter and writes a new
    properties file to the output destination.

    >>> def remove_openstacks(run):
    ...     return 'openstacks' not in run['domain']

    >>> from lab.experiment import Experiment
    >>> report = FilterReport(filter=remove_openstacks)
    >>> exp = Experiment()
    >>> exp.add_report(report, outfile='path/to/new/properties')

    """
    def __init__(self, **kwargs):
        Report.__init__(self, **kwargs)

    def get_text(self):
        if not self.outfile.endswith('properties'):
            raise ValueError('outfile must be a path to a properties file')
        return str(self.props)
