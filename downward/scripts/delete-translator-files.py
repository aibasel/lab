#! /usr/bin/env python

import os
import sys

from lab.external import argparse


HELP = "Remove the files domain.pddl, problem.pddl and output.sas from all subdirs."

argparser = argparse.ArgumentParser(description=HELP)
argparser.add_argument('dir', help='Traverse all folders under this directory.')

args = argparser.parse_args()

if not os.path.isdir(args.dir):
    sys.exit('Error: %s is no valid directory' % args.dir)

for root, dirs, files in os.walk(args.dir):
    for file in files:
        if file in ['domain.pddl', 'problem.pddl', 'output.sas']:
            path = os.path.join(root, file)
            print 'Removing', path
            os.remove(path)
