:mod:`downward.experiment` --- Fast Downward experiment
=======================================================
.. autoclass:: downward.experiment.FastDownwardExperiment
   :members: add_algorithm, add_suite

.. autoclass:: downward.experiment.FastDownwardAlgorithm
   :members:
   :undoc-members:
   :inherited-members:

.. autoclass:: downward.cached_revision.CachedFastDownwardRevision
   :members:
   :undoc-members:
   :inherited-members:

.. _downward-parsers:

Built-in parsers
----------------

The following constants are paths to built-in parsers that can be passed
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
