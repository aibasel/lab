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

See the `parsing documentation <lab.parser.html>`_ for how to write
parsers. Once you have fixed your existing parsers or added new parsers,
add ``exp.add_parse_again_step()`` to your experiment script
``my-exp.py`` and then call ::

    ./my-exp.py parse-again


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
