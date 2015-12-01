.. _downward.tutorial:

Downward Tutorial
=================

Install lab and downward
------------------------
.. include:: ../INSTALL.txt

Install Fast Downward
---------------------
http://www.fast-downward.org/ObtainingAndRunningFastDownward

Run tutorial experiment
-----------------------
.. highlight:: python

The script below is an example Fast Downward experiment. It is located
at ``examples/lmcut.py``. After you have adapted the ``REPO`` variable
to point to your clone of the Fast Downward repository, you can see the
available steps with ::

    ./lmcut.py


Run the individual steps with ::

    ./lmcut.py build
    ./lmcut.py 2
    ./lmcut.py 3 4


You can use this file as a basis for your own experiments.

.. literalinclude:: ../examples/lmcut.py

Have a look at other Fast Downward experiments in the ``examples``
directory and the `downward API <downward.experiment.html>`_.
