:mod:`downward.reports` --- Fast Downward reports
=================================================

Tables
------

.. autoclass:: downward.reports.PlanningReport

  You may want to override the following class attributes in subclasses:

  .. autoattribute:: downward.reports.PlanningReport.PREDEFINED_ATTRIBUTES
  .. autoattribute:: downward.reports.PlanningReport.ERROR_ATTRIBUTES
  .. autoattribute:: downward.reports.PlanningReport.INFO_ATTRIBUTES

.. autoclass:: downward.reports.absolute.AbsoluteReport
.. autoclass:: downward.reports.taskwise.TaskwiseReport
.. autoclass:: downward.reports.compare.ComparativeReport


Plots
-----

.. autoclass:: downward.reports.scatter.ScatterPlotReport

.. image:: images/example-scatter-plot.png
   :scale: 60 %
