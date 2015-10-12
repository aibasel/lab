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
    def _get_table(self, domain, runs):
        table = Table(title=domain)
        for run in runs:
            for attr in self.attributes:
                table.add_cell(run['problem'], attr, run.get(attr))
        return table

    def get_markup(self):
        if len(self.configs) != 1:
            logging.critical('Taskwise reports need exactly one config.')
        tables = [
            self._get_table(domain, runs)
            for (domain, config), runs in sorted(self.domain_config_runs.items())]
        return '\n'.join(str(table) for table in tables)
