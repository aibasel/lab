:mod:`downward.experiment` --- Fast Downward experiment
=======================================================
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
