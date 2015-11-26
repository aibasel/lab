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

The script below is a simple experiment. It is located
at ``examples/simple/simple-exp.py``. You can see the available steps with ::

    ./simple-exp.py


Select steps by name or index::

    ./simple-exp.py build
    ./simple-exp.py 2
    ./simple-exp.py 3 4


You can use this file as a basis for your own experiments.

.. literalinclude:: ../examples/simple/simple-exp.py

Have a look at another example lab experiment in the ``example/pi`` directory
and the `lab API <lab.experiment.html>`_.
