#! /usr/bin/env python

"""
Parse Fast Downward exit code and store a message describing the outcome
in the "error" attribute.
"""

from downward import outcomes
from lab.parser import Parser


def parse_exit_code(content, props):
    """
    Convert the exitcode of the planner to a human-readable message and store
    it in props['error']. Additionally, if there was an unexplained error, add
    its source to the list at props['unexplained_errors'].

    For unexplained errors please check the files run.log, run.err,
    driver.log and driver.err to find the reason for the error.

    """
    assert "error" not in props

    # Check if Fast Downward uses the latest exit codes.
    use_legacy_exit_codes = True
    for line in content.splitlines():
        if line.startswith("translate exit code:") or line.startswith(
            "search exit code:"
        ):
            use_legacy_exit_codes = False
            break

    exitcode = props["planner_exit_code"]
    outcome = outcomes.get_outcome(exitcode, use_legacy_exit_codes)
    props["error"] = outcome.msg
    if use_legacy_exit_codes:
        props["unsolvable"] = int(outcome.msg == "unsolvable")
    else:
        props["unsolvable"] = int(
            outcome.msg in ["translate-unsolvable", "search-unsolvable"]
        )
    if not outcome.explained:
        props.add_unexplained_error(outcome.msg)


class ExitCodeParser(Parser):
    def __init__(self):
        Parser.__init__(self)
        self.add_pattern(
            "planner_exit_code",
            r"planner exit code: (.+)\n",
            type=int,
            file="driver.log",
            required=True,
        )
        self.add_function(parse_exit_code)


def main():
    parser = ExitCodeParser()
    parser.parse()


main()
