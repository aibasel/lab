Installation
============

.. highlight:: bash

lab + downward
--------------
Choose a destination for the lab package, install the dependencies and clone the
repository::

    LAB=/path/to/lab
    sudo apt-get install mercurial python2.7 python-matplotlib
    hg clone https://bitbucket.org/jendrikseipp/lab ${LAB}

Append to your ``.bashrc`` to make lab available on the ``PYTHONPATH``::

    LAB=~/path/to/lab
    if [ -z "$PYTHONPATH" ]; then
        export PYTHONPATH=${LAB}
    else
        export PYTHONPATH=${PYTHONPATH}:${LAB}
    fi

Check that everything works::

    source ~/.bashrc
    cd ${LAB}/examples/simple
    ./simple-exp.py --help

Fast Downward planning system
-----------------------------
::

    FAST_DOWNWARD=/path/to/fast-downward/repo
    sudo apt-get install mercurial g++ make python flex bison gawk
    sudo apt-get install g++-multilib  # 64-bit
    hg clone http://hg.fast-downward.org ${FAST_DOWNWARD}

After you have adapted the ``EXPPATH`` and ``REPO``
variables in ``LAB/examples/lmcut.py``, you can run a ``downward`` experiment::

    cd ${LAB}/examples/
    ./lmcut.py --help
    ./lmcut.py --all
