# Instructions

Install `uv`:

First, check if `uv` is currently installed:

    which uv

If the previous command did not return a path, then install `uv` by using the package from your Linux distribution.
If `uv` is not packaged for your distribution, you do not have superuser rights or you are in a non-Linux OS, you
can install it for your user with pip:

    pip install --user uv

You can also check that the official installation script is safe and install it mamnually. Take into account that
blindly executing a script is a potential security issue easy to avoid, and that official URLs can also be hacked.

    wget https://astral.sh/uv/install.sh
    sh install.sh

## Create a new project (pyproject.toml, .python-version, uv.lock)

Initialize a new `uv` project in the current directory:

    uv init --bare --no-workspace --pin-python

Install dependencies:

    uv add lab

## Run a script in an existing project

    uv run 2020-09-11-B-bounded-cost.py
