.. _lab.tutorial:

Lab tutorial
============

.. note::

    During `ICAPS 2020 <https://icaps20.icaps-conference.org/>`_, we gave an `online talk about Lab and Downward Lab <https://icaps20subpages.icaps-conference.org/tutorials/evaluating-planners-with-downward-lab/>`_ (version 6.2). The first half of the presentation shows how to use Lab to run experiments for a solver. You can find the recording `here <https://www.youtube.com/watch?v=39tIUsxbh9w>`_.

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
