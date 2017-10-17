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
Fast Downward exit codes and their meaning.
"""

import collections
import signal


def get_exit_code(signal_value):
    return 256 - signal_value


Outcome = collections.namedtuple('Outcome', ['value', 'msg', 'explained', 'min_wins'])

OUTCOMES = [
    Outcome(0, 'none', explained=True, min_wins=False),
    Outcome(1, 'critical-error', explained=False, min_wins=True),
    Outcome(2, 'input-error', explained=False, min_wins=True),
    Outcome(3, 'unsupported-feature-requested', explained=False, min_wins=True),
    Outcome(4, 'unsolvable', explained=True, min_wins=False),
    Outcome(5, 'incomplete-search-found-no-plan', explained=True, min_wins=None),
    Outcome(6, 'out-of-memory', explained=True, min_wins=True),
    Outcome(7, 'timeout', explained=True, min_wins=True),
    Outcome(8, 'timeout-and-out-of-memory', explained=True, min_wins=True),
    Outcome(get_exit_code(signal.SIGKILL), 'sigkill', explained=False, min_wins=True),
    Outcome(get_exit_code(signal.SIGSEGV), 'segfault', explained=False, min_wins=True),
    Outcome(get_exit_code(signal.SIGXCPU), 'timeout', explained=True, min_wins=True),
]

EXITCODE_TO_OUTCOME = dict((outcome.value, outcome) for outcome in OUTCOMES)


def get_outcome(exitcode):
    if exitcode in EXITCODE_TO_OUTCOME:
        return EXITCODE_TO_OUTCOME[exitcode]
    else:
        msg = 'exitcode-{exitcode}'.format(**locals())
        return Outcome(exitcode, msg, explained=False, min_wins=True)
