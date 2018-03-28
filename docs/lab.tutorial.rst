.. _lab.tutorial:

Lab tutorial
============

Install lab
-----------
.. highlight:: bash
.. include:: ../INSTALL.txt


Run tutorial experiment
-----------------------
.. highlight:: python

The script below shows how to run the `FF planner
<http://fai.cs.uni-saarland.de/hoffmann/ff.html>`_ on a number of
classical planning benchmarks. It is located at ``examples/ff/ff.py``.
You can see the available steps with ::

    ./ff.py


Select steps by name or index::

    ./ff.py build
    ./ff.py 2
    ./ff.py 3 4


You can use this file as a basis for your own experiments.

.. literalinclude:: ../examples/ff/ff.py

Have a look at other example experiments under ``examples/`` or go
directly to the `lab API <lab.experiment.html>`_.
