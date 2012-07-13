#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

# make sure we're in the run directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from lab.calls.call import Call

try:
    from lab.calls.log import driver_log, driver_err
except IOError:
    # Cannot open log files
    sys.exit(1)

sys.stdout = driver_log
sys.stderr = driver_err
# All errors that occur from here on out will be written to the log file

from lab.calls.log import print_, redirects, save_returncode
from lab.calls.log import set_property

set_property('queue', os.environ.get('QUEUE'))


"""VARIABLES"""

"""CALLS"""
