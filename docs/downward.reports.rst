:mod:`downward.reports` --- Fast Downward reports
=================================================

.. autoclass:: downward.reports.PlanningReport
.. autoclass:: downward.reports.absolute.AbsoluteReport
.. autoclass:: downward.reports.relative.RelativeReport
.. autoclass:: downward.reports.ipc.IpcReport
.. autoclass:: downward.reports.suite.SuiteReport
.. autoclass:: downward.reports.timeout.TimeoutReport


Comparative reports
-------------------

.. autoclass:: downward.reports.compare.CompareConfigsReport
.. autoclass:: downward.reports.compare.CompareRevisionsReport


Plots
-----

.. autoclass:: downward.reports.plot.PlotReport

.. autoclass:: downward.reports.plot.ProblemPlotReport

Example ProblemPlot comparing the expansions of two abstraction heuristics with
changing values for the number of maximum abstract states (x-axis):

.. image:: images/example-problem-plot.png
   :scale: 40 %

.. autoclass:: downward.reports.scatter.ScatterPlotReport

Example ScatterPlot comparing the translator time of two different revisions for
a big suite of problems:

.. image:: images/example-scatter-plot.png
   :scale: 40 %
