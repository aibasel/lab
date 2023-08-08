Downward Lab tutorial
=====================

.. highlight:: bash

This tutorial shows you how to install Downward Lab and how to create a
simple experiment for Fast Downward that compares two heuristics, the
causal graph (CG) heuristic and the FF heuristic. There are many ways for
setting up your experiments. This tutorial gives you an opinionated
alternative that has proven to work well in practice.

.. note::

    During `ICAPS 2020 <https://icaps20.icaps-conference.org/>`_, we gave
    an online `Downward Lab presentation
    <https://icaps20subpages.icaps-conference.org/tutorials/evaluating-planners-with-downward-lab/>`_
    (version 6.2). The second half of the presentation covers this
    tutorial and you can find the recording `here
    <https://www.youtube.com/watch?v=39tIUsxbh9w>`_.


Installation
------------

Lab requires **Python 3.7+** and **Linux**. To run Fast Downward
experiments, you'll need a **Fast Downward** repository, planning
**benchmarks** and a plan **validator**. ::

    # Install required packages.
    sudo apt install bison cmake flex g++ git make python3 python3-venv

    # Create directory for holding binaries and scripts.
    mkdir --parents ~/bin

    # Make directory for all projects related to Fast Downward.
    mkdir downward-projects
    cd downward-projects

    # Install the plan validator VAL.
    git clone https://github.com/KCL-Planning/VAL.git
    cd VAL
    # Newer VAL versions need time stamps, so we use an old version
    # (https://github.com/KCL-Planning/VAL/issues/46).
    git checkout a556539
    make clean  # Remove old binaries.
    sed -i 's/-Werror //g' Makefile  # Ignore warnings.
    make
    cp validate ~/bin/  # Add binary to a directory on your ``$PATH``.
    # Return to projects directory.
    cd ../

    # Download planning tasks.
    git clone https://github.com/aibasel/downward-benchmarks.git benchmarks

    # Clone Fast Downward and let it solve an example task.
    git clone https://github.com/aibasel/downward.git
    cd downward
    ./build.py
    ./fast-downward.py ../benchmarks/grid/prob01.pddl --search "astar(lmcut())"

If Fast Downward doesn't compile, see
http://www.fast-downward.org/ObtainingAndRunningFastDownward and
http://www.fast-downward.org/LPBuildInstructions. We now create a new
directory for our CG-vs-FF project. By putting it into the Fast Downward
repo under ``experiments/``, it's easy to share both the code and
experiment scripts with your collaborators. ::

    # Create new branch.
    git checkout -b cg-vs-ff main
    # Create a new directory for your experiments in Fast Downward repo.
    cd experiments
    mkdir cg-vs-ff
    cd cg-vs-ff

Now it's time to install Lab. We install it in a `Python virtual
environment <https://docs.python.org/3/tutorial/venv.html>`_ specific to
the cg-vs-ff project. This has the advantage that there are no
modifications to the system-wide configuration, and that you can have
multiple projects with different Lab versions (e.g., for different
papers). ::

    # Create and activate a Python 3 virtual environment for Lab.
    python3 -m venv --prompt cg-vs-ff .venv
    source .venv/bin/activate

    # Install Lab in the virtual environment.
    pip install -U pip wheel  # It's good to have new versions of these.
    pip install lab  # or preferably a specific version with lab==x.y

    # Store installed packages and exact versions for reproducibility.
    # Ignore pkg-resources package (https://github.com/pypa/pip/issues/4022).
    pip freeze | grep -v "pkg-resources" > requirements.txt
    git add requirements.txt
    git commit -m "Store requirements for experiments."

To use the same versions of your requirements on a different computer, use
``pip install -r requirements.txt`` instead of the ``pip install``
commands above.

Add to your ``~/.bashrc`` file::

    # Make executables in ~/bin directory available globally.
    export PATH="${PATH}:${HOME}/bin"
    # Some example experiments need these two environment variables.
    export DOWNWARD_BENCHMARKS=/path/to/downward-projects/benchmarks  # Adapt path
    export DOWNWARD_REPO=/path/to/downward-projects/downward  # Adapt path

Add to your ``~/.bash_aliases`` file::

    # Activate virtualenv and unset PYTHONPATH to obtain isolated virtual environments.
    alias venv="unset PYTHONPATH; source .venv/bin/activate"

Finally, reload ``.bashrc`` (which usually also reloads ``~/.bash_aliases``)::

    source ~/.bashrc

You can activate virtual environments now by running ``venv`` in
directories containing a ``.venv`` subdirectory.


Run tutorial experiment
-----------------------

The files below are an experiment script for the example experiment, a
``project.py`` module that bundles common functionality for all
experiments related to the project, a parser module, and a script for
collecting results and making reports. You can use the files as a basis
for your own experiments. They are available in the `Lab repo
<https://github.com/aibasel/lab/tree/main/examples/downward>`_. Copy the
files into ``experiments/cg-vs-ff``.

.. highlight:: bash

Make sure the experiment script is executable. Then you can see the available
steps with ::

    ./2020-09-11-A-cg-vs-ff.py

Run all steps with ::

    ./2020-09-11-A-cg-vs-ff.py --all


Run individual steps with ::

    ./2020-09-11-A-cg-vs-ff.py build
    ./2020-09-11-A-cg-vs-ff.py 2
    ./2020-09-11-A-cg-vs-ff.py 3 6 7

.. highlight:: python

.. literalinclude:: ../examples/downward/2020-09-11-A-cg-vs-ff.py
   :caption:

.. literalinclude:: ../examples/downward/project.py
   :caption:

.. literalinclude:: ../examples/downward/custom_parser.py
   :caption:

.. literalinclude:: ../examples/downward/01-evaluation.py
   :caption:

The `Downward Lab API <downward.experiment.html>`_ shows you how to adjust
this example to your needs. You may also find the `other example
experiments <https://github.com/aibasel/lab/tree/main/examples/>`_
useful.
