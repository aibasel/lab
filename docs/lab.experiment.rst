:mod:`lab.experiment` --- Create experiments
============================================

.. module:: lab.experiment

:class:`Experiment`
-------------------

.. autoclass:: Experiment
   :members:
   :undoc-members:
   :inherited-members:



Custom command line arguments
.............................

.. data:: ARGPARSER

   `ArgumentParser <http://docs.python.org/library/argparse.html>`_
   instance that can be used to add custom command line arguments.
   You can import it, add your arguments and call its ``parse_args()``
   method to retrieve the argument values. To avoid confusion with step
   names you shouldn't use positional arguments.

   .. note::

        Custom command line arguments are only passed to locally
        executed steps.

   ::

        from lab.experiment import ARGPARSER

        ARGPARSER.add_argument(
            "--test",
            choices=["yes", "no"],
            required=True,
            dest="test_run",
            help="run experiment on small suite locally")

        args = ARGPARSER.parse_args()
        if args.test_run:
            print "perform test run"
        else:
            print "run real experiment"


:class:`Run`
-------------------

.. autoclass:: Run
   :members:
   :undoc-members:
   :inherited-members:
   :exclude-members: build


.. _environments:

:class:`Environment`
--------------------

.. autoclass:: lab.environments.Environment
.. autoclass:: lab.environments.LocalEnvironment
.. autoclass:: lab.environments.GridEnvironment
.. autoclass:: lab.environments.BaselSlurmEnvironment


Various
-------

.. autodata:: lab.__version__
   :annotation:
