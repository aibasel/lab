# Instructions

Install `uv`:

    curl -LsSf https://astral.sh/uv/install.sh | sh

## Create a new project (pyproject.toml, .python-version, uv.lock)

Initialize a new `uv` project in the current directory:

    uv init --bare --no-workspace --pin-python

Install dependencies:

    uv add lab

## Run a script in an existing project

    uv run 2020-09-11-B-bounded-cost.py
