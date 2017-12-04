#! /usr/bin/env python

import math

from lab.parser import Parser


def diff(content, props):
    pi = props.get('pi')
    props['diff'] = abs(math.pi - pi)


parser = Parser()
parser.add_pattern('pi', '^Pi: (.+)$', type=float, flags='M')
parser.add_pattern('time', '^Time: (.+)$', type=float, flags='M')
parser.add_function(diff)
parser.parse()
