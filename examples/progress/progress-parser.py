#! /usr/bin/env python

import re
import sys

from lab.parser import Parser


regex = re.compile(r'^f = (\d+) \[(\d+) evaluated, (\d+) expanded, t=(.+)s\]$')

def f_values(content, props):
    values = []
    for line in content.splitlines():
        match = regex.match(line)
        if match:
            values.append([int(match.group(1)), int(match.group(2)),
                           int(match.group(3)), float(match.group(4))])
    props['f_values'] = values


class ProgressParser(Parser):
    def __init__(self):
        Parser.__init__(self)

        self.add_function(f_values)


if __name__ == '__main__':
    print 'Parsing progress'
    ProgressParser().parse()
