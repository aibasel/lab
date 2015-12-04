#! /usr/bin/env python

import sys
import os
import multiprocessing
import subprocess

from lab.experiment import get_run_dir


# make sure we're in the run directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))


num_tasks = """NUM_TASKS"""


def process_dir(task_id):
    print 'Starting run {:>5}/{}'.format(task_id, num_tasks)
    run = subprocess.Popen(
        ['./run'],
        cwd=get_run_dir(task_id),
        stdout=sys.stdout, stderr=sys.stderr)  # TODO: Remove redirections?
    try:
        run.wait()
    except KeyboardInterrupt:
        print 'Call to run %s interrupted' % number
        run.terminate()
    except OSError, err:
        print err


def main():
    pool = multiprocessing.Pool(processes="""PROCESSES""")
    try:
        pool.map(process_dir, range(1, num_tasks + 1))
    except KeyboardInterrupt:
        print 'Main script interrupted'
        pool.terminate()
    finally:
        pool.close()
        print 'Joining pool processes'
        pool.join()


if __name__ == '__main__':
    main()
