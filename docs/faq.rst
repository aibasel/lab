.. _faq:

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


Some runs failed. How can I rerun them?
---------------------------------------

If the failed runs were never started, for example, due to grid node
failures, you can simply run the "start" experiment step again. It will
skip all runs that have already been started. Afterwards, run "fetch" and
make reports as usual.

Lab detects which runs have already been started by checking if the
``driver.log`` file exists. So if you have failed runs that were already
started, but you want to rerun them anyway, go to their run directories,
remove the ``driver.log`` files and then run the "start" experiment step
again as above.


I forgot to parse something. How can I run only the parsers again?
------------------------------------------------------------------

Now that parsing is done in its own experiment step, simply consult the `parsing
documentation <lab.parser.html>`_ for how to amend your parsers and then run the
"parse" experiment step again with ::

    ./my-exp.py parse


.. _portparsers:

How do I port my parsers to version 8.x?
----------------------------------------

Since version 8.0, Lab has a dedicated "parse" experiment step. First of all,
what are the benefits of this?

* No need to write parsers in separate files.
* Log output from solvers and parsers remains separate.
* No need for ``exp.add_parse_again_step()``. Parsing and re-parsing is now
  exactly the same.
* Parsers are checked for syntax errors before the experiment is run.
* Parsing runs much faster (for an experiment with 3 algorithms and 5 parsers
  the parsing time went down from 51 minutes to 5 minutes, both measured on
  cold file system caches).
* As before, you can let the Slurm environment do the parsing for you and get
  notified when the report is finished: ``./myexp.py build start parse fetch
  report``

To adapt your parsers to this new API, you need to make the following changes:

* Your parser module (e.g., "custom_parser.py") does not have to be executable
  anymore, but it must be importable and expose a :class:`Parser
  <lab.parser.Parser>` instance (see the changes to the `translator parser
  <https://github.com/aibasel/lab/pull/117/files#diff-0a679939eb576c6b402a00ab9b08a3339ecefe3713dc96f9ac6b0e05de9ff4f2>`_
  for an example). Then, instead of ``exp.add_parser("custom_parser.py")`` use
  ``from custom_parser import MyParser`` and ``exp.add_parser(MyParser())``.
* Remove ``exp.add_parse_again_step()`` and insert ``exp.add_step("parse",
  exp.parse)`` after ``exp.add_step("start", exp.start_runs)``.


How can I compute a new attribute from multiple runs?
-----------------------------------------------------

Consider for example the IPC quality score. It is often computed over the
list of runs for each task. Since filters only work on individual runs, we
can't compute the score with a single filter, but it is possible by using
two filters as shown below: *store_costs* saves the list of costs per task
in a dictionary whereas *add_quality* uses the stored costs to compute IPC
quality scores and adds them to the runs.

.. literalinclude:: ../examples/showcase-options.py
   :pyobject: QualityFilters


How can I make reports and plots for results obtained without Lab?
------------------------------------------------------------------

See `report-external-results.py
<https://github.com/aibasel/lab/blob/main/examples/report-external-results.py>`_
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
<https://github.com/aibasel/lab/blob/main/CONTRIBUTING.md>`_.


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


Which best practices do you recommend for working with Lab?
-----------------------------------------------------------

* automate as much as possible but not too much
* use fixed solver revisions ("3a27ea77f" instead of "main")
* use Python virtual environments
* pin versions of all Python dependencies in ``requirements.txt``
* collect common experiment code in project module
* copy experiment scripts for new experiments, don't change them
* make evaluation locally rather than on remote cluster
* collect exploratory results from multiple experiments
* rerun experiments for camera-ready copy in single experiment and
  with single code revision
