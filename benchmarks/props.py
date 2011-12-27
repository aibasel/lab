#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import json
import cjson
import cPickle as pickle
import yaml
from yaml import CLoader as Loader
from yaml import CSafeDumper
from yaml import SafeDumper
import timeit
import sys

#BENCHMARKS_DIR = os.path.dirname(os.path.abspath(__file__))
#LABS_DIR = os.path.dirname(BENCHMARKS_DIR)
#sys.path.insert(0, LABS_DIR)
from lab import tools

CONFIGOBJ_FILE = '/tmp/configobj.txt'
JSON_FILE = '/tmp/json.txt'
CJSON_FILE = '/tmp/cjson.txt'
PICKLE_FILE = '/tmp/pickle.txt'
YAML_FILE = '/tmp/yaml.txt'
CYAML_FILE = '/tmp/cyaml.txt'

PROPFILE = sys.argv[1]
PROPS = dict(tools.Properties(PROPFILE))
print 'DONE READING'


DIC      = {}
NB_ITERS = int(sys.argv[2])


def configobj_print():
    p = tools.Properties(PROPS)
    p.filename = CONFIGOBJ_FILE
    p.write()

def json_print():
    with open(JSON_FILE, 'w') as f:
        json.dump(PROPS, f, indent=2, ensure_ascii=False)

def cjson_print():
    with open(CJSON_FILE, 'w') as f:
        f.write(cjson.encode(PROPS))

def pickle_print():
    with open(PICKLE_FILE, 'wb') as f:
        pickle.dump(PROPS, f, pickle.HIGHEST_PROTOCOL)

def yaml_print():
    with open(YAML_FILE, 'wb') as f:
        yaml.dump(PROPS, f, Dumper=SafeDumper, allow_unicode=True)

def cyaml_print():
    with open(CYAML_FILE, 'wb') as f:
        yaml.dump(PROPS, f, Dumper=CSafeDumper, allow_unicode=True)

def configobj_read():
    tools.Properties(CONFIGOBJ_FILE)

def json_read():
    with open(JSON_FILE) as f:
        json.load(f)

def cjson_read():
    with open(CJSON_FILE) as f:
        cjson.decode(f.read(), all_unicode=True)

def pickle_read():
    with open(PICKLE_FILE, 'rb') as f:
        pickle.load(f)

def yaml_read():
    with open(YAML_FILE, 'rb') as f:
        yaml.load(f, Loader=Loader)


timers = [(func, timeit.Timer('%s()' % func, 'from __main__ import %s' % func))
          for func in ['json_print',
                       #'cjson_print',
                       'pickle_print',
                       'yaml_print',
                       'cyaml_print',
                       'json_read',
                       #'cjson_read',
                       'pickle_read',
                       'yaml_read'
                       ]]

for i, (func, timer) in enumerate(timers, 1):
    print ' * %s' % func.ljust(15), timer.timeit(NB_ITERS)
