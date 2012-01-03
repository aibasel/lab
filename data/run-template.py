#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

# make sure we're in the run directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from lab.calls.call import Call
from lab.calls.log import print_, redirects, save_returncode, driver_log, driver_err
from lab.calls.log import set_property

sys.stdout = driver_log
sys.stderr = driver_err

set_property('queue', os.environ.get('QUEUE'))


"""VARIABLES"""

"""CALLS"""
