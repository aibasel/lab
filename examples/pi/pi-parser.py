#! /usr/bin/env python

from lab.parser import Parser


def error(content, props):
    props['error'] = 'none'


parser = Parser()
parser.add_pattern('pi', '^Pi: (.+)$', type=float, flags='M')
parser.add_function(error)
parser.parse()
