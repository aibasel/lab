:mod:`downward.experiment` --- Fast Downward experiment
=======================================================

.. note::

   The :class:`FastDownwardExperiment
   <downward.experiment.FastDownwardExperiment>` class makes it simply to write
   "standard" experiments, but it assumes a rigid experiment structure: it only
   allows you to run each added algorithm on each added task, and individual
   runs cannot easily be customized. If you need more flexibility, you can use
   the :class:`lab.experiment.Experiment` class instead and fill it by using
   :class:`FastDownwardAlgorithm <downward.experiment.FastDownwardAlgorithm>`,
   :class:`FastDownwardRun <downward.experiment.FastDownwardRun>`,
   :class:`CachedFastDownwardRevision
   <downward.cached_revision.CachedFastDownwardRevision>`, and :class:`Task
   <downward.suites.Task>` objects. The `2020-09-11-A-cg-vs-ff.py
   <https://github.com/aibasel/lab/tree/main/examples/downward/2020-09-11-A-cg-vs-ff.py>`_
   script shows an example. All classes are documented below.

.. autoclass:: downward.experiment.FastDownwardExperiment
   :members: add_algorithm, add_suite

.. _downward-parsers:

Bundled parsers
---------------

The following constants are paths to default parsers that can be passed
to :meth:`exp.add_parser() <lab.experiment.Experiment.add_parser>`. The
"Used attributes" and "Parsed attributes" lists describe the
dependencies between the parsers.

.. autoattribute:: downward.experiment.FastDownwardExperiment.EXITCODE_PARSER
   :annotation:

.. autoattribute:: downward.experiment.FastDownwardExperiment.TRANSLATOR_PARSER
   :annotation:

.. autoattribute:: downward.experiment.FastDownwardExperiment.SINGLE_SEARCH_PARSER
   :annotation:

.. autoattribute:: downward.experiment.FastDownwardExperiment.ANYTIME_SEARCH_PARSER
   :annotation:

.. autoattribute:: downward.experiment.FastDownwardExperiment.PLANNER_PARSER
   :annotation:

.. autoclass:: downward.experiment.FastDownwardAlgorithm
   :members:
   :undoc-members:
   :inherited-members:

.. autoclass:: downward.experiment.FastDownwardRun
   :members:
   :undoc-members:

.. autoclass:: downward.cached_revision.CachedFastDownwardRevision
   :members:
   :undoc-members:
   :inherited-members:

:mod:`downward.suites` --- Select benchmarks
--------------------------------------------

.. autoclass:: downward.suites.Task
   :members:
   :undoc-members:

.. autofunction:: downward.suites.build_suite
