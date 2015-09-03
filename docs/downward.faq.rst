Frequently Asked Questions
==========================

How can I parse and report my own attributes?
---------------------------------------------

You will have to write a parser that is executed at the end of run
and manipulates the ``properties`` file in the run directory. The
simplest way for this is to write a Python script that uses the
:py:class:`Parser <lab.parser.Parser>` class. Here is the example
parser from ``examples/simple/simple-parser.py``:

.. literalinclude:: ../examples/simple/simple-parser.py

You can add your parser to all experiment runs with::

    exp.add_search_parser('path/to/myparser.py')


How can I combine the results from multiple experiments?
--------------------------------------------------------
::

    exp = Experiment('/new/path/to/combined-results')
    exp.add_fetcher('path/to/first/eval/dir')
    exp.add_fetcher('path/to/second/eval/dir')
    exp.add_fetcher('path/to/experiment/dir')
    exp.add_report(AbsoluteReport())


How can I run multiple steps sequentially on a computer grid?
-------------------------------------------------------------

Previously, you had to use the ``--all`` commandline option for this.
Since version 1.8 lab will automatically run steps sequentially on the
grid engine if one of the steps itself submits runs to the grid engine.


I forgot to parse something. How can I run only the parser again?
-----------------------------------------------------------------

See above for writing a parser. Once you have it, add a new fetcher
with :py:func:`add_fetcher <lab.experiment.Experiment.add_fetcher>` and
let it use your parser::

    exp = Experiment('my-path')
    exp.add_fetcher(name='parse-again', parsers=['path/to/my-parser'])

Call the fetcher by invoking the new experiment step::

    ./my-exp.py parse-again


How can I make reports and plots for results obtained without lab?
------------------------------------------------------------------

See ``examples/plot-external-results.py`` for an example.
