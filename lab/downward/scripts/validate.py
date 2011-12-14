#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Checks all found plans in the current directory for correctness.
The path to the validator has to be given as the only command-line argument.

Returns 0 if all of the plans are valid, 1 otherwise.
"""

import sys
import glob
from subprocess import Popen


VALIDATE, DOMAIN, PROBLEM = sys.argv[1:4]


retcodes = []
for plan_file in sorted(glob.glob("sas_plan*")):
    retcodes.append(Popen([VALIDATE, DOMAIN, PROBLEM, plan_file]).wait())

if any(val != 0 for val in retcodes):
    print 'VAL returncodes:', retcodes
    sys.exit(1)

sys.exit(0)
