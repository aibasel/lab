#!/usr/bin/env python

import json
import timeit
import sys

sys.path.insert(0, '/home/jendrik/projects/Downward/lab/lab')
import tools

CONFIGOBJ_FILE = 'configobj.txt'
JSON_FILE = 'json.txt'

PROPFILE = sys.argv[1]
PROPS = dict(tools.Properties(PROPFILE))
print 'DONE READING'


DIC      = {}
NB_ITERS = 10


def configobj_print():
    p = tools.Properties(PROPS)
    p.filename = CONFIGOBJ_FILE
    p.write()

def json_print():
    with open(JSON_FILE, 'w') as f:
        json.dump(PROPS, f, indent=0)


def configobj_read():
    tools.Properties(CONFIGOBJ_FILE)

def json_read():
    with open(JSON_FILE) as f:
        json.load(f)


timers = [(func, timeit.Timer('%s()' % func, 'from __main__ import %s' % func))
          for func in ['configobj_print', 'json_print', 'configobj_read', 'json_read']]

for i, (func, timer) in enumerate(timers, 1):
    print ' * %s:' % func.ljust(15), timer.timeit(NB_ITERS)
