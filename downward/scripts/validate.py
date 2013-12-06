#! /usr/bin/env python
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

"""
Checks all found plans in the current directory for correctness.

Returns 0 if all of the plans are valid, 1 otherwise.
"""

import sys
import glob
from subprocess import Popen


VALIDATE, DOMAIN, PROBLEM = sys.argv[1:4]


retcodes = []
for plan_file in sorted(glob.glob("sas_plan*")):
    retcodes.append(Popen([VALIDATE, DOMAIN, PROBLEM, plan_file]).wait())

if any(val != 0 for val in retcodes):
    print 'VAL returncodes:', retcodes
    sys.exit(1)

sys.exit(0)
