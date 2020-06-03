First off, thanks for taking the time to contribute to Lab!

# Setting up a development environment

    git clone https://github.com/aibasel/lab.git
    cd lab
    # Create and activate a virtual environment.
    python3 -m venv --prompt lab-dev .venv
    source .venv/bin/activate
    # Get the latest pip version.
    pip install -U pip
    # Install Lab in development mode.
    pip install --editable .
    # Check that Lab can be imported.
    cd examples
    ./lmcut.py --help

# Running tests

    cd lab
    # Activate virtual environment.
    source .venv/bin/activate
    # Install tox.
    pip install -U tox
    # Run all tests.
    tox
    # Run subset of tests.
    tox -e py,style

Running all tests requires a lot of setup steps. They can be found under .github/workflows/ubuntu.yml. Unless you modify the FF or Singularity example experiments, it is ok to have the tests for these two fail locally. The GitHub actions will execute all tests remotely.

