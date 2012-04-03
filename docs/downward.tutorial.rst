.. _downward.tutorial:

Tutorial
========

The script below is an example Fast Downward experiment. It is located
at ``examples/lmcut.py``. You can see the available steps with ::

    $ ./lmcut.py
    usage: lmcut.py [-h] [-l {DEBUG,INFO,WARNING}] [steps [steps ...]]

    positional arguments:
      steps

    optional arguments:
      -h, --help            show this help message and exit
      -l {DEBUG,INFO,WARNING}, --log-level {DEBUG,INFO,WARNING}

    Available steps:
    ================
     1 build-preprocess-exp     build(stage='preprocess')
     2 run-preprocess-exp       run(stage='preprocess')
     3 fetch-preprocess-results fetcher('/home/jendrik/lab/experiments/lmcut-p', write_combined_props=False, eval_dir='/home/jendrik/lab/preprocessed-tasks', copy_all=True)
     4 build-search-exp         build(stage='search')
     5 run-search-exp           run(stage='search')
     6 fetch-search-results     fetcher('/home/jendrik/lab/experiments/lmcut')
     7 report-abs-p             absolutereport('/home/jendrik/lab/experiments/lmcut-eval', '/home/jendrik/lab/experiments/lmcut-eval/lmcut-abs-p.html')
     8 zip-exp-dir              call(['tar', '-czf', 'lmcut.tar.gz', 'lmcut'], cwd='/home/jendrik/lab/experiments')
     9 remove-exp-dir           rmtree('/home/jendrik/lab/experiments/lmcut')


You can run the individual steps with ::

    ./lmcut.py 1
    ./lmcut.py {2..4}
    ./lmcut.py run-search-exp


The comments should help you understand how to use this file as a basis for your
own experiments.

.. literalinclude:: ../examples/lmcut.py
