#! /usr/bin/env python

import argparse
import subprocess

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
    print 'Starting run {:>5}'.format(task_id)
    task_id = get_shuffled_task_id(num_tasks, task_id)
    subprocess.check_call(['./run'], cwd=get_run_dir(task_id))


def main():
    args = parse_args()
    run(args.num_tasks, args.task_id)


if __name__ == '__main__':
    main()
