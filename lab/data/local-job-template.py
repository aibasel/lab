#! /usr/bin/env python

import os
import multiprocessing
import subprocess
import sys


# make sure we're in the run directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))


num_tasks = """NUM_TASKS"""


def process_dir(task_id):
    print 'Started {:>5}/{} runs'.format(task_id, num_tasks)
    subprocess.check_call(['./run-dispatcher.py', str(task_id)])


def main():
    pool = multiprocessing.Pool(processes="""PROCESSES""")
    result = pool.map_async(process_dir, range(1, num_tasks + 1))
    try:
        # Use "timeout" to fix passing KeyboardInterrupts from children
        # (see https://stackoverflow.com/questions/1408356).
        result.wait(timeout=sys.maxint)
    except KeyboardInterrupt:
        print 'Main script interrupted'
        pool.terminate()
    finally:
        pool.close()
        print 'Joining pool processes'
        pool.join()


if __name__ == '__main__':
    main()
