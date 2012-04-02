.. _downward.tutorial:

Tutorial
========

The script below is an example Fast Downward experiment. It is located
at ``examples/initial-opt-config.py``. You can see the available steps with ::

    $ ./initial-opt-config.py
    usage: initial-opt-config.py [-h] [-l {DEBUG,INFO,WARNING}] [steps [steps ...]]

    positional arguments:
      steps

    optional arguments:
      -h, --help            show this help message and exit
      -l {DEBUG,INFO,WARNING}, --log-level {DEBUG,INFO,WARNING}

    Available steps:
    ================
     1 build-preprocess-exp           build(stage='preprocess')
     2 run-preprocess-exp             run(stage='preprocess')
     3 fetch-preprocess-results       fetcher('/home/jendrik/lab/experiments/js-initial-opt-config-p', write_combined_props=False, eval_dir='/home/jendrik/lab/preprocessed-tasks', copy_all=True)
     4 build-search-exp               build(stage='search')
     5 run-search-exp                 run(stage='search')
     6 fetch-search-results           fetcher('/home/jendrik/lab/experiments/js-initial-opt-config')
     7 report-abs-d                   absolutereport('/home/jendrik/lab/experiments/js-initial-opt-config-eval', '/home/jendrik/lab/experiments/js-initial-opt-config-eval/js-initial-opt-config-abs-d.html')
     8 report-abs-p                   absolutereport('/home/jendrik/lab/experiments/js-initial-opt-config-eval', '/home/jendrik/lab/experiments/js-initial-opt-config-eval/js-initial-opt-config-abs-p.html')
     9 report-suite                   suitereport('/home/jendrik/lab/experiments/js-initial-opt-config-eval', '/home/jendrik/lab/experiments/js-initial-opt-config-eval/js-initial-opt-config_solved_suite.py')
    10 publish_reports                publish_reports()
    11 zip-exp-dir                    call(['tar', '-czf', 'js-initial-opt-config.tar.gz', 'js-initial-opt-config'], cwd='/home/jendrik/lab/experiments')
    12 remove-exp-dir                 rmtree('/home/jendrik/lab/experiments/js-initial-opt-config')


You can run the individual steps with ::

    ./initial-opt-config.py 1
    ./initial-opt-config.py {2..4}
    ./initial-opt-config.py run-search-exp


The comments should help you understand how to use this file as a basis for your
own experiments.

.. literalinclude:: ../examples/initial-opt-config.py
