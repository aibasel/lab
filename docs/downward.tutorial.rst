.. _downward.tutorial:

Downward Lab tutorial
=====================

.. highlight:: bash
.. include:: ../INSTALL.txt


Download benchmarks
-------------------
.. highlight:: bash

::

    DOWNWARD_BENCHMARKS=/path/to/downward-benchmarks
    git clone https://github.com/aibasel/downward-benchmarks ${DOWNWARD_BENCHMARKS}

Some example experiments need the ``DOWNWARD_BENCHMARKS`` environment
variable so we recommend exporting it in your ``~/.bashrc`` file.


Install Fast Downward
---------------------
(See also http://www.fast-downward.org/ObtainingAndRunningFastDownward
and http://www.fast-downward.org/LPBuildInstructions.)

Lab supports Git and Mercurial repositories.

.. highlight:: bash

::

    DOWNWARD_REPO=/path/to/fast-downward-repo
    sudo apt install cmake g++ git make python3
    git clone https://github.com/aibasel/downward.git ${DOWNWARD_REPO}
    # Optionally check that Fast Downward works:
    cd ${DOWNWARD_REPO}
    ./build.py
    ./fast-downward.py ${DOWNWARD_BENCHMARKS}/grid/prob01.pddl --search "astar(lmcut())"


Install VAL
-----------
.. highlight:: bash

::

    sudo apt install g++ make flex bison
    git clone https://github.com/KCL-Planning/VAL.git
    cd VAL
    git checkout 8d61593 # newer versions don't accept IPC format plans
    bash ./scripts/linux/build_linux64.sh all release
    sudo cp build/linux64/release/bin/Validate /usr/local/bin/validate  # Add binary to a directory on PATH.


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
