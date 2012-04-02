lab
===
**lab** is a python package for conducting and analyzing experiments that run on
single machines or on computer clusters. It is useful if you want to run your
code on a large set of benchmarks.

downward
========
The **downward** package uses *lab* to run experiments and create custom reports
for the `Fast Downward planning system <http://www.fast-downward.org>`_.


Requirements
============

- Python 2.6 or 2.7
- Only tested on Linux
- downward: `Fast Downward dependencies <http://www.fast-downward.org/ObtainingAndRunningFastDownward>`_


Getting started
===============
The base directory (containing "lab" and "downward") must be on the
PYTHONPATH, so you might want to add "export PYTHONPATH=/path/to/base/dir"
to your .bashrc file.

Change into examples/simple and execute ``./simple-exp.py`` This will print the
help text for this simple experiment. There are multiple ways to run the
experiment steps: ::

    ./simple-exp.py 1
    ./simple-exp.py 2 3
    ./simple-exp.py report

If you want to run a Fast Downward experiment, the best way to start is
looking at ``examples/initial-opt-config.py`` and adapting it to your needs.
Most of the available methods and options can be found in the
``examples/showcase-options.py`` example.


Documentation
=============
Short tutorials and API references can be found at
`readthedocs.org <http://readthedocs.org/docs/lab/>`_.
