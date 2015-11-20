:mod:`lab` --- Create experiments
=================================

.. module:: lab.experiment

:class:`Experiment`
-------------------

.. autoclass:: Experiment
   :members:
   :undoc-members:
   :inherited-members:

.. data:: ARGPARSER

   `ArgumentParser <http://docs.python.org/library/argparse.html>`_
   instance that can be used to add custom command line arguments.
   You can import it, add your arguments and call its ``parse_args()``
   method to retrieve the argument values. To avoid confusion with step
   names you shouldn't use positional arguments. ::

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


.. _environments:

:class:`Environment`
--------------------

.. autoclass:: lab.environments.LocalEnvironment
.. autoclass:: lab.environments.GkiGridEnvironment
.. autoclass:: lab.environments.MaiaEnvironment


.. _parser:

:class:`Parser` -- Parse log output
-----------------------------------

.. autoclass:: lab.parser.Parser
   :members:
   :undoc-members:


Various
-------

.. autodata:: lab.__version__
   :annotation:
