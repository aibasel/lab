#! /usr/bin/env python

import argparse
import subprocess
import sys

from lab.experiment import get_run_dir


SHUFFLED_TASK_IDS = """TASK_ORDER"""


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('num_tasks', metavar='NUM_TASKS', type=int)
    parser.add_argument('task_id', metavar='TASK_ID', type=int)
    return parser.parse_args()


def get_shuffled_task_id(num_tasks, task_id):
    return SHUFFLED_TASK_IDS[task_id - 1]


def run(num_tasks, task_id):
    shuffled_task_id = get_shuffled_task_id(num_tasks, task_id)
    print 'Starting task {} ({}/{})'.format(
        shuffled_task_id, task_id, num_tasks)
    try:
        subprocess.check_call(['./run'], cwd=get_run_dir(shuffled_task_id))
    except subprocess.CalledProcessError as err:
        sys.exit(
            'Error: Run {shuffled_task_id} failed. Please inspect '
            'the corresponding directory.'.format(**locals()))


def main():
    args = parse_args()
    run(args.num_tasks, args.task_id)


if __name__ == '__main__':
    main()
