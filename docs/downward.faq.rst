Frequently Asked Questions
==========================

How can I parse and report my own attributes?
---------------------------------------------

You will have to write a parser that is executed at the end of run
and manipulates the ``properties`` file in the run directory. The
simplest way for this is to write a Python script that uses the
Parser class. Here is the example parser from
``examples/simple/simple-parser.py``:

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

If your experiment is named ``exp.py``, you can use the command
``./exp.py --all build-search-exp run-search-exp fetch-search-results`` or
``./exp.py --all 4 5 6`` to let the grid run each of those three steps when the
previous one is finished. ``./exp.py --help`` has more infos about the ``--all``
parameter.
