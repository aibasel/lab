#! /usr/bin/env python

from lab.parser import Parser

parser = Parser()
parser.add_pattern('pi', 'Pi: (.+)', type=float)
parser.parse()
