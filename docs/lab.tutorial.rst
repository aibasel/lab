.. _lab.tutorial:

Lab tutorial
============

Install Lab
-----------
.. highlight:: bash
.. include:: ../INSTALL.txt


Run tutorial experiment
-----------------------
.. highlight:: python

The following script shows a simple experiment that runs a naive vertex
cover solver on a set of benchmarks. You can find the whole experiment
under ``examples/vertex-cover/``.

.. literalinclude:: ../examples/vertex-cover/exp.py

You can see the available steps with ::

    ./exp.py


Select steps by name or index::

    ./exp.py build
    ./exp.py 2
    ./exp.py 3 4

Here is the parser that the experiment uses:

.. literalinclude:: ../examples/vertex-cover/parser.py

Have a look at other example experiments under ``examples/`` or go
directly to the `Lab API <lab.experiment.html>`_.
