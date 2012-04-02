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

import sys

from downward.reports import PlanningReport


class SuiteReport(PlanningReport):
    """Write a list of problems to a python file.

    The data can be filtered by the filter functions passed to the constructor.
    All the runs are checked whether they pass the filters and the remaining
    runs are sorted, the duplicates are removed and the resulting list of
    problems is written to the output file.

    Write a suite with solved problems: ::

        def solved(run):
            return run['coverage'] == 1

        suite_file = os.path.join(exp.eval_dir, '%s_solved_suite.py' % EXPNAME)
        exp.add_step(Step('report-suite', SuiteReport(filter=solved),
                          exp.eval_dir, suite_file))
    """
    def __init__(self, *args, **kwargs):
        PlanningReport.__init__(self, *args, **kwargs)

    def get_text(self):
        """
        We do not need any markup processing or loop over attributes here,
        so the get_text() method is implemented right here.
        """
        if not self.props:
            sys.exit('No problems match this filter')
        problems = [domain + ':' + problem for domain, problem in self.problems]
        problems = ['        "%s",\n' % problem for problem in problems]
        output = ('def suite():\n    return [\n%s    ]\n' % ''.join(problems))
        print '\nSUITE:'
        print output
        return output
