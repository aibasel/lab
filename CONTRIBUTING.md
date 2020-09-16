First off, thanks for taking the time to contribute to Lab!

# Setting up a development environment

Follow the installation instructions for the [Downward Lab
tutorial](https://lab.readthedocs.io/en/latest/downward.tutorial.html), in
particular, you'll need to make VAL available under the name `validate` on
your PATH and define the `DOWNWARD_BENCHMARKS` and `DOWNWARD_REPO`
environment variables. Also, make sure to install the latest Lab revision
from GitHub in editable mode:

    git clone https://github.com/aibasel/lab.git
    cd lab
    python3 -m venv --prompt lab-dev .venv
    source .venv/bin/activate
    pip install -U pip wheel
    pip install --editable .

For details on how to set everything up, please see the [GitHub actions
file](.github/workflows/ubuntu.yml).

# Running tests

    cd lab
    # Activate virtual environment.
    source .venv/bin/activate
    # Install tox.
    pip install -U tox
    # Run the core tests.
    tox -e py,style,docs

The above `tox` command runs the most important tests. To test the FF and
Singularity experiments, you need some additional setup steps, which we
describe next. However, unless you modify these two experiments, it is ok
to skip their tests locally.

## Test FF experiment

    sudo apt-get -y install g++ make flex bison
    wget http://fai.cs.uni-saarland.de/hoffmann/ff/FF-v2.3.tgz
    tar -xzvf FF-v2.3.tgz
    cd FF-v2.3/
    make -j

and add the resulting `ff` binary to your `PATH`. Now you can run the example FF experiment with `tox -e ff`.

## Test Singularity experiment

    mkdir -p new/path/for/Singularity-images
    cd new/path/for/Singularity-images
    wget --no-verbose https://ai.dmi.unibas.ch/_tmp_files/seipp/lama-first.img
    export SINGULARITY_IMAGES=`realpath .`

Now you can run the example Singularity experiment with `tox -e singularity`.

## Run all tests

Once you have installed all dependecies, you can run all tests by executing `tox` without any options.

# Fixing the code style

    tox -e fix-style
