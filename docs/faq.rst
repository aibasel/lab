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

See `report-external-results.py
<https://github.com/aibasel/lab/blob/master/examples/report-external-results.py>`_
for an example.


Which experiment class should I use for which Fast Downward revision?
---------------------------------------------------------------------

* Before CMake: use DownwardExperiment in Lab 1.x
* With CMake and optional validation: use FastDownwardExperiment in Lab 1.x
* With CMake and mandatory validation: use FastDownwardExperiment in Lab 2.x
* New translator exit codes (issue739): use FastDownwardExperiment in Lab >= 3.x


How can I contribute to Lab?
----------------------------

If you'd like to contribute a feature or a bugfix to Lab or Downward Lab,
please see `CONTRIBUTING.md
<https://github.com/aibasel/lab/blob/master/CONTRIBUTING.md>`_.


How can I customize Lab?
------------------------

Lab tries to be easily customizable. That means that you shouldn't have to
make any changes to the Lab code itself, but rather you should be able to
inherit from Lab classes and implement custom behaviour in your
subclasses. If this doesn't work in your case, let's discuss how we can
improve things in a `GitHub issue
<https://github.com/aibasel/lab/issues>`_.

That said, it can sometimes be easiest to quickly patch Lab. In this case,
or when you want to run the latest Lab development version, you can clone
the Lab repo and install it (preferable in a virtual environment)::

    git clone https://github.com/aibasel/lab.git /path/to/lab
    pip install --editable /path/to/lab

The ``--editable`` flag installs the project in "editable mode", which
makes any changes under ``/path/to/lab`` appear immediately in the virtual
environment.
