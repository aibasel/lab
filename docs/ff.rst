.. _ff:

Run other planners
==================
.. highlight:: python

The script below shows how to run the `FF planner
<http://fai.cs.uni-saarland.de/hoffmann/ff.html>`_ on a number of
classical planning benchmarks. You can see the available steps with ::

    ./ff.py


Select steps by name or index::

    ./ff.py build
    ./ff.py 2
    ./ff.py 3 4


You can use this file as a basis for your own experiments. For Fast
Downward experiments, we recommend taking a look at the
`<downward.tutorial>`_.

.. literalinclude:: ../examples/ff/ff.py
   :caption:

Here is a simple parser for FF:

.. literalinclude:: ../examples/ff/ff_parser.py
   :caption:
