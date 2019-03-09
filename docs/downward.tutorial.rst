.. _downward.tutorial:

Downward Lab tutorial
=====================

Install Lab and Downward Lab
----------------------------
.. highlight:: bash
.. include:: ../INSTALL.txt


Download benchmarks
-------------------
.. highlight:: bash

::

    DOWNWARD_BENCHMARKS=/path/to/downward-benchmarks
    hg clone https://bitbucket.org/aibasel/downward-benchmarks \
        ${DOWNWARD_BENCHMARKS}

Some example experiments need the ``DOWNWARD_BENCHMARKS`` environment
variable so we recommend adding it to your ``~/.bashrc`` file.


Install Fast Downward
---------------------
(See also http://www.fast-downward.org/ObtainingAndRunningFastDownward
and http://www.fast-downward.org/LPBuildInstructions)

.. highlight:: bash

::

    DOWNWARD_REPO=/path/to/fast-downward-repo
    sudo apt-get install mercurial g++ cmake make python
    hg clone http://hg.fast-downward.org ${DOWNWARD_REPO}
    # Optionally check that Fast Downward works:
    cd ${DOWNWARD_REPO}
    ./build.py
    ./fast-downward.py ${DOWNWARD_BENCHMARKS}/grid/prob01.pddl \
        --search "astar(lmcut())"


Install VAL
-----------
.. highlight:: bash

::

    sudo apt-get install g++ make flex bison
    git clone https://github.com/KCL-Planning/VAL.git
    cd VAL
    make clean  # Remove old object files and binaries.
    sed -i 's/-Werror //g' Makefile  # Ignore warnings.
    make
    sudo cp validate /usr/local/bin  # Add binary to a directory on PATH.

**MacOS**: clone the repo, add ``VAL/bin/MacOSExecutables/validate`` to
your ``PATH`` and make it executable (``chmod + x``).


Run tutorial experiment
-----------------------
.. highlight:: python

The script below is an example Fast Downward experiment. It is located
at ``${LAB}/examples/lmcut.py``. After setting ``REPO`` to
``FAST_DOWNWARD`` and ``BENCHMARKS_DIR`` to ``BENCHMARKS``, you can see
the available steps with ::

    ./lmcut.py

Run all steps with ::

    ./lmcut.py --all


Run individual steps with ::

    ./lmcut.py build
    ./lmcut.py 2
    ./lmcut.py 3 4


You can use this file as a basis for your own experiments.

.. literalinclude:: ../examples/lmcut.py

Have a look at other Fast Downward experiments in the ``examples``
directory and the `downward API <downward.experiment.html>`_.
