Frequently Asked Questions
==========================

How can I parse and report my own attributes?
---------------------------------------------

You will have to subclass DownwardExperiment and add a new parsing command to
each run. Here are the relevant bits from the example script
(``examples/custom-attributes.py``):

.. literalinclude:: ../examples/custom-attributes.py
   :pyobject: CustomDownwardExperiment
