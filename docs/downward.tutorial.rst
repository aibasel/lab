.. _downward.tutorial:

Downward Tutorial
=================

Install lab and downward
------------------------
.. include:: ../INSTALL.txt

Install Fast Downward
---------------------
.. highlight:: bash

::

    FAST_DOWNWARD=/path/to/fast-downward/repo
    sudo apt-get install mercurial g++ make python flex bison gawk
    sudo apt-get install g++-multilib  # 64-bit
    hg clone http://hg.fast-downward.org ${FAST_DOWNWARD}

Run tutorial experiment
-----------------------
.. highlight:: python

The script below is an example Fast Downward experiment. It is located at
``examples/lmcut.py``. After you have adapted the ``REPO`` variable to point to
``FAST_DOWNWARD``, you can see the available steps with ::

    ./lmcut.py


Run the individual steps with ::

    ./lmcut.py 1
    ./lmcut.py {2..4}
    ./lmcut.py run-search-exp


You can use this file as a basis for your own experiments.

.. literalinclude:: ../examples/lmcut.py

Have a look at other Fast Downward experiments in the ``examples`` directory
and the `downward API <downward.experiment.html>`_.
