.. _lab.tutorial:

Tutorial
========

The script below is a simple experiment. It is located
at ``examples/simple/simple-exp.py``. You can see the available steps with ::

    $ ./simple-exp.py
    usage: simple-exp.py [-h] [-l {DEBUG,INFO,WARNING}] [steps [steps ...]]

    positional arguments:
      steps

    optional arguments:
      -h, --help            show this help message and exit
      -l {DEBUG,INFO,WARNING}, --log-level {DEBUG,INFO,WARNING}

    Available steps:
    ================
     1 build           build()
     2 start           run()
     3 fetch           fetcher('/tmp/simple-exp')
     4 report          report('/tmp/simple-exp-eval', '/tmp/simple-exp-eval/simple-exp.html')
     5 zip-exp-dir     call(['tar', '-cjf', 'simple-exp.tar.bz2', 'simple-exp'], cwd='/tmp')
     6 publish_reports publish_reports()
     7 remove-exp-dir  rmtree('/tmp/simple-exp')


You can run the individual steps with ::

    ./simple-exp.py 1
    ./simple-exp.py {2..4}
    ./simple-exp.py zip-exp-dir


The comments should help you understand how to use this file as a basis for your
own experiments.

.. literalinclude:: ../examples/simple/simple-exp.py

In the ``examples\pi`` you can find another example ``lab`` experiment.
