#! /usr/bin/env python

import re

from lab.parser import Parser


def coverage(content, props):
    props['coverage'] = int(props['run-planner_returncode'] == 0)


def get_plan(content, props):
    # All patterns are parsed before functions are called.
    if props.get('evaluations') is not None:
        props['plan'] = re.findall(r'^(?:step)?\s*\d+: (.+)$', content, re.M)


def get_times(content, props):
    props['times'] = re.findall(r'(\d+\.\d+) seconds', content, re.M)


def trivially_unsolvable(content, props):
    props['trivially_unsolvable'] = int(
        'ff: goal can be simplified to FALSE. No plan will solve it' in content)


parser = Parser()
parser.add_pattern('evaluations', r'evaluating (\d+) states')
parser.add_function(coverage)
parser.add_function(get_plan)
parser.add_function(get_times)
parser.add_function(trivially_unsolvable)
parser.parse()
