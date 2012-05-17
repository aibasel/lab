#! /usr/bin/env python

import sys
import os
import multiprocessing
import subprocess

# make sure we're in the run directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))


dirs = [
"""DIRS"""
]


def process_dir(dir):
    number = dir.split('/')[-1]
    print 'Starting run %s/%s' % (number, str(len(dirs)).zfill(5))
    run = subprocess.Popen(['./run'], cwd=dir, stdout=sys.stdout, stderr=sys.stderr)
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
        pool.map(process_dir, dirs)
    except KeyboardInterrupt:
        print 'Main script interrupted'
        pool.terminate()
    finally:
        pool.close()
        print 'Joining pool processes'
        pool.join()


if __name__ == '__main__':
    main()
