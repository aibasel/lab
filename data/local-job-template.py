#! /usr/bin/env python

import sys
import os
import multiprocessing
import subprocess

# make sure we're in the run directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def process_dir(dir):
    try:
        number = dir.split('/')[-1]
        print 'Starting run %s/%s' % (number, str(len(dirs)).zfill(5))
        run = subprocess.Popen(['./run'], cwd=dir, stdout=sys.stdout, stderr=sys.stderr)
        run.wait()
    except KeyboardInterrupt:
        print 'Call to run interrupted'
        run.terminate()
    except OSError, err:
        print err

dirs = [
"""DIRS"""
]

pool = multiprocessing.Pool(processes="""PROCESSES""")
res = pool.map_async(process_dir, dirs)
pool.close()

try:
    pool.join()
except KeyboardInterrupt:
    print 'Main script interrupted'
    pool.terminate()
