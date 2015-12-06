#! /usr/bin/env python

import argparse
import subprocess

from lab.experiment import get_run_dir


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('task_id', metavar='TASK_ID')
    return parser.parse_args()


def run(task_id):
    print 'Starting run {:>5}'.format(task_id)
    subprocess.check_call(['./run'], cwd=get_run_dir(task_id))


def main():
    args = parse_args()
    run(int(args.task_id))


if __name__ == '__main__':
    main()
