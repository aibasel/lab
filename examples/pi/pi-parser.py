#! /usr/bin/env python

from lab.parser import Parser


def error(content, props):
    props.add_error('none')


parser = Parser()
parser.add_pattern('pi', 'Pi: (.+)', type=float)
parser.add_function(error)
parser.parse()
