.. _downward.tutorial:

Tutorial
========

The script below is an example Fast Downward experiment. It is located
at ``examples/lmcut.py``. After you have adapted the ``EXPPATH`` and ``REPO``
variables to your system, you can see the available steps with ::

    $ ./lmcut.py


You can run the individual steps with ::

    ./lmcut.py 1
    ./lmcut.py {2..4}
    ./lmcut.py run-search-exp


The comments should help you understand how to use this file as a basis for your
own experiments.

.. literalinclude:: ../examples/lmcut.py

The ``examples`` directory includes further downward experiments.
