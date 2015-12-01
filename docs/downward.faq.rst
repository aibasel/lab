Frequently Asked Questions
==========================

How can I parse and report my own attributes?
---------------------------------------------

See the `parsing documentation <lab.parser.html>`_.


How can I combine the results from multiple experiments?
--------------------------------------------------------
::

    exp = Experiment('/new/path/to/combined-results')
    exp.add_fetcher('path/to/first/eval/dir')
    exp.add_fetcher('path/to/second/eval/dir')
    exp.add_fetcher('path/to/experiment/dir')
    exp.add_report(AbsoluteReport())


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

See ``examples/report-external-results.py`` for an example.
