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

from lab.tools import Properties

from downward.reports import PlanningReport


class TimeoutReport(PlanningReport):
    def __init__(self, timeouts, *args, **kwargs):
        PlanningReport.__init__(self, *args, **kwargs)
        self.timeouts = timeouts

    def get_text(self):
        if not self.outfile.endswith('properties'):
            raise ValueError('outfile must be a path to a properties file')
        new_props = Properties()
        for old_id, run in self.runs.items():
            domain = run['domain']
            problem = run['problem']
            old_config = run['config']
            total_time = run.get('total_time')
            for timeout in self.timeouts:
                solved = total_time is not None and total_time <= timeout
                new_total_time = total_time if solved else None
                new_config = '%ds-%s' % (timeout, old_config)
                run_id = '-'.join([new_config, domain, problem])
                new_run = {'domain': domain, 'problem': problem,
                           'config': new_config, 'coverage': int(solved),
                           'total_time': new_total_time}
                new_props[run_id] = new_run
        return str(new_props)
