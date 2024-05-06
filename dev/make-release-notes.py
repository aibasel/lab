#! /usr/bin/env python3

import re
import sys


_, VERSION, CHANGELOG, LIST = sys.argv

REGEX = rf"""
Changelog\n
=========\n
\n
(v{VERSION}\ \(\d\d\d\d-\d\d-\d\d\))\n
-----------------\n
\n
Lab\n
\^\^\^\n
(.+?)\n
\n
Downward\ Lab\n
\^\^\^\^\^\^\^\^\^\^\^\^\n
(.+?)\n
\n
\n
"""


with open(CHANGELOG) as f:
    content = f.read()

match = re.search(REGEX, content, flags=re.VERBOSE | re.DOTALL)
version, lab_changes, downward_changes = match.groups()
changes = [version, "", "## Lab", lab_changes, "", "## Downward Lab", downward_changes]
changelog = "\n".join(changes)


def check(name, text):
    print("*" * 60)
    print(text)
    print("*" * 60)
    response = input(f"Accept this {name} (Y/n)? ").strip().lower()
    if response and response != "y":
        sys.exit(1)


check("changelog", changelog)

with open(LIST, "w") as f:
    f.write(changelog)
