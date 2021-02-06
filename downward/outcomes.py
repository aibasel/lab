"""
Fast Downward exit codes and their meaning. They are documented at
http://www.fast-downward.org/ExitCodes.
"""

import collections
import signal


def get_exit_code(signal_value):
    return 256 - signal_value


Outcome = collections.namedtuple("Outcome", ["value", "msg", "explained", "min_wins"])

LEGACY_OUTCOMES = [
    Outcome(0, "success", explained=True, min_wins=False),
    Outcome(1, "critical-error", explained=False, min_wins=True),
    Outcome(2, "input-error", explained=False, min_wins=True),
    Outcome(3, "unsupported-feature-requested", explained=False, min_wins=True),
    Outcome(4, "unsolvable", explained=True, min_wins=False),
    Outcome(5, "incomplete-search-found-no-plan", explained=True, min_wins=None),
    Outcome(6, "out-of-memory", explained=True, min_wins=True),
    Outcome(7, "timeout", explained=True, min_wins=True),
    Outcome(8, "timeout-and-out-of-memory", explained=True, min_wins=True),
    Outcome(get_exit_code(signal.SIGKILL), "sigkill", explained=False, min_wins=True),
    Outcome(get_exit_code(signal.SIGSEGV), "segfault", explained=False, min_wins=True),
    Outcome(get_exit_code(signal.SIGXCPU), "timeout", explained=True, min_wins=True),
]

EXITCODE_TO_LEGACY_OUTCOME = {outcome.value: outcome for outcome in LEGACY_OUTCOMES}

NEW_OUTCOMES = [
    Outcome(0, "success", explained=True, min_wins=False),
    Outcome(1, "search-plan-found-and-out-of-memory", explained=True, min_wins=None),
    Outcome(2, "search-plan-found-and-out-of-time", explained=True, min_wins=None),
    Outcome(
        3, "search-plan-found-and-out-of-memory-and-time", explained=True, min_wins=None
    ),
    Outcome(10, "translate-unsolvable", explained=True, min_wins=False),
    Outcome(11, "search-unsolvable", explained=True, min_wins=False),
    Outcome(12, "search-unsolvable-incomplete", explained=True, min_wins=None),
    Outcome(20, "translate-out-of-memory", explained=True, min_wins=True),
    Outcome(21, "translate-out-of-time", explained=True, min_wins=True),
    Outcome(22, "search-out-of-memory", explained=True, min_wins=True),
    Outcome(23, "search-out-of-time", explained=True, min_wins=True),
    Outcome(24, "search-out-of-memory-and-time", explained=True, min_wins=True),
    Outcome(30, "translate-critical-error", explained=False, min_wins=True),
    Outcome(31, "translate-input-error", explained=False, min_wins=True),
    Outcome(32, "search-critical-error", explained=False, min_wins=True),
    Outcome(33, "search-input-error", explained=False, min_wins=True),
    Outcome(34, "search-unsupported", explained=False, min_wins=True),
    Outcome(35, "driver-critital-error", explained=False, min_wins=True),
    Outcome(36, "driver-input-error", explained=False, min_wins=True),
    Outcome(37, "driver-unsupported", explained=False, min_wins=True),
    Outcome(get_exit_code(signal.SIGKILL), "sigkill", explained=False, min_wins=True),
    Outcome(get_exit_code(signal.SIGSEGV), "segfault", explained=False, min_wins=True),
]

EXITCODE_TO_OUTCOME = {outcome.value: outcome for outcome in NEW_OUTCOMES}

OUTCOMES = LEGACY_OUTCOMES + NEW_OUTCOMES


def get_outcome(exitcode, use_legacy_exit_codes):
    if use_legacy_exit_codes and exitcode in EXITCODE_TO_LEGACY_OUTCOME:
        return EXITCODE_TO_LEGACY_OUTCOME[exitcode]
    elif not use_legacy_exit_codes and exitcode in EXITCODE_TO_OUTCOME:
        return EXITCODE_TO_OUTCOME[exitcode]
    else:
        msg = f"exitcode-{exitcode}"
        return Outcome(exitcode, msg, explained=False, min_wins=True)
