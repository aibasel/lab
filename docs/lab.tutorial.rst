.. _lab.tutorial:

Lab tutorial
============

.. highlight:: bash
.. include:: ../INSTALL.rst


Run tutorial experiment
-----------------------
.. highlight:: python

The following script shows a simple experiment that runs a naive vertex
cover solver on a set of benchmarks.

.. literalinclude:: ../examples/vertex-cover/exp.py
   :caption:

You can see the available steps with ::

    ./exp.py


Select steps by name or index::

    ./exp.py build
    ./exp.py 2
    ./exp.py 3 4

Here is the parser that the experiment uses:

.. literalinclude:: ../examples/vertex-cover/parser.py
   :caption:

Find out how to create your own experiments by browsing the `Lab API
<lab.experiment.html>`_.
