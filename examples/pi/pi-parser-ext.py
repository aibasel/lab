#! /usr/bin/env python

import math

from lab.parser import Parser

def diff(content, props):
    pi = props.get('pi')
    props['diff'] = abs(math.pi - pi)

parser = Parser()
parser.add_pattern('pi', 'Pi: (.+)', type=float)
parser.add_function(diff)
parser.parse()
