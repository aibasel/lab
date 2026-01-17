# Instructions

Install [uv](https://docs.astral.sh/uv/). Then initialize a new `uv` project in the current directory:

    uv init --bare --no-workspace --pin-python

Install dependencies:

    uv add lab

Add project files to version control:

    git add pyproject.toml .python-version uv.lock

Run your script by prepending `uv run`:

    uv run 2020-09-11-B-bounded-cost.py
