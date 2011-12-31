#! /usr/bin/env python

import re
import sys
sys.path.insert(0, '../../lab')

from parser import Parser


regex = re.compile(r'^f = (\d+) \[\d+ evaluated, \d+ expanded, t=(.+)s\]$')

def f_values(content, props):
    values = []
    for line in content.splitlines():
        match = regex.match(line)
        if match:
            print 'MATCH'
            values.append((float(match.group(2)), int(match.group(1))))
    props['f_values'] = values


class ProgressParser(Parser):
    def __init__(self):
        Parser.__init__(self)

        self.add_function(f_values)


if __name__ == '__main__':
    print 'Parsing progress'
    ProgressParser().parse()
