Frequently asked questions
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


I forgot to parse something. How can I run only the parsers again?
------------------------------------------------------------------

See the `parsing documentation <lab.parser.html>`_ for how to write
parsers. Once you have fixed your existing parsers or added new parsers,
add ``exp.add_parse_again_step()`` to your experiment script
``my-exp.py`` and then call ::

    ./my-exp.py parse-again


How can I make reports and plots for results obtained without Lab?
------------------------------------------------------------------

See ``examples/report-external-results.py`` for an example.


Which experiment class should I use for which Fast Downward revision?
---------------------------------------------------------------------

* Before CMake: use DownwardExperiment in Lab 1.x
* With CMake and optional validation: use FastDownwardExperiment in Lab 1.x
* With CMake and mandatory validation: use FastDownwardExperiment in Lab 2.x
* New translator exit codes (issue739): use FastDownwardExperiment in Lab 3.x
