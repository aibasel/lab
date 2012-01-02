#! /usr/bin/env python

import os
import sys
sys.path.insert(0, os.path.abspath('labcode'))

from parser import Parser

def wordcount(content, props):
    props['lines'] = len(content.splitlines())

class SimpleParser(Parser):
    def __init__(self):
        Parser.__init__(self)

        self.add_function(wordcount)

if __name__ == '__main__':
    print 'Running simple parser'
    parser = SimpleParser()
    parser.parse()
