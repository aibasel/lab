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

Downward Lab uses VAL to validate the plans that Fast Downward finds.

.. highlight:: bash

::

    sudo apt-get install bash bison cmake flex g++ git make
    git clone https://github.com/KCL-Planning/VAL.git
    cd VAL
    git checkout 09b9a1ea0d9de56bd6a0cd2180b0d2af378e0cc7
    # Make sure that CXXFLAGS does not contain -Werror, then run:
    bash scripts/linux/build_linux64.sh Validate Release
    # Add binary to a directory on your PATH.
    sudo cp build/linux64/Release/bin/Validate /usr/local/bin/validate

**MacOS**: use the instructions above, but execute the MacOS build
script instead of the Linux script (untested).


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
