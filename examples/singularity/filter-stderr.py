#! /usr/bin/env python

"""Filter lines from run.err that stem from "expected errors"."""

import shutil
from pathlib import Path

IGNORE_PATTERNS = [
    "CPU time limit exceeded",
    "std::bad_alloc",
    "WARNING: will ignore action costs",
    "differs from the one in the portfolio file",
    "Terminated",
    "Killed",
    "underlay of /etc/localtime required more than",
]


def main():
    print("Running filter-stderr.py")
    stderr = Path("run.err")
    if stderr.is_file():
        need_to_filter = False
        filtered_content = []
        with open(stderr) as f:
            for line in f:
                if any(pattern in line for pattern in IGNORE_PATTERNS):
                    need_to_filter = True
                else:
                    filtered_content.append(line)

        if need_to_filter:
            shutil.move(stderr, "run.err.bak")
            # We write an empty file if everything has been filtered. Lab
            # will remove empty run.err files later.
            with open(stderr, "w") as f:
                f.writelines(filtered_content)


if __name__ == "__main__":
    main()
