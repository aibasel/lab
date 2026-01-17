#! /usr/bin/env python3

import re
import sys

_, VERSION, CHANGELOG, LIST = sys.argv


def extract_release_block(content: str, version: str) -> tuple[str, str]:
    """Return (version_line, block_text) for exactly one release.

    The block is identified by a header line like:
        v8.8 (2026-01-17)
    and extends until the next such header (or end of file).
    """
    header_re = re.compile(
        rf"^v{re.escape(version)} \(\d{{4}}-\d{{2}}-\d{{2}}\)\s*$",
        flags=re.MULTILINE,
    )
    m = header_re.search(content)
    if not m:
        raise ValueError(f"Could not find release header for v{version} in {CHANGELOG}")

    version_line = m.group(0).strip()

    any_header_re = re.compile(
        r"^v\d+(?:\.\d+)* \(\d{4}-\d{2}-\d{2}\)\s*$",
        flags=re.MULTILINE,
    )
    n = any_header_re.search(content, m.end())
    end = n.start() if n else len(content)
    block_text = content[m.start() : end].strip()
    return version_line, block_text


def extract_subsection(block_text: str, title: str) -> str:
    """Extract subsection body for a title underlined with '^' characters."""
    # Matches e.g.
    # Lab
    # ^^^
    # <body>
    subsection_re = re.compile(
        rf"^{re.escape(title)}\n\^+\n(?P<body>.*?)(?=\n\S.*\n\^+\n|\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    m = subsection_re.search(block_text)
    return m.group("body").strip() if m else ""


with open(CHANGELOG) as f:
    content = f.read()

version_line, release_block = extract_release_block(content, VERSION)
lab_changes = extract_subsection(release_block, "Lab")
downward_changes = extract_subsection(release_block, "Downward Lab")

changes = [version_line]
if lab_changes:
    changes += ["", "## Lab", lab_changes]
if downward_changes:
    changes += ["", "## Downward Lab", downward_changes]
changelog = "\n".join(changes) + "\n"


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
