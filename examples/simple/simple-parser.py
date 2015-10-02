#! /usr/bin/env python

from lab.parser import Parser


def wordcount(content, props):
    props['number_of_files'] = len(content.splitlines())

parser = Parser()
parser.add_function(wordcount)
parser.add_pattern('first_number', '(\d+)')
parser.parse()
