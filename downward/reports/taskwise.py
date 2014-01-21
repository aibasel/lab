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

from lab.reports import Table

from downward.reports import PlanningReport


class TaskwiseReport(PlanningReport):
    def get_markup(self):
        if not len(self.configs) == 1:
            logging.critical('The number of configs has to be one for taskwise reports.')
        table = Table()
        for (domain, problem), runs in self.problem_runs.items():
            assert len(runs) == 1, len(runs)
            run = runs[0]
            for attr in self.attributes:
                table.add_cell('%s:%s' % (domain, problem), attr, run.get(attr))
        return str(table)
