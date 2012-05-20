from __future__ import division

import os
import datetime
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)-s %(levelname)-8s %(message)s',)

from lab.tools import copy
from lab import tools
from lab import reports
from lab.reports import gm
from lab import tools
from downward.scripts.preprocess_parser import parse_statistics


base = os.path.join('/tmp', str(datetime.datetime.now()))
os.mkdir(base)

src_file = os.path.join(base, 'src_file')
src_dir = os.path.join(base, 'src_dir')
nested_src_file = os.path.join(src_dir, 'nested_src_file')

dest_file = os.path.join(base, 'dest1', 'dest_file')
dest_dir1 = os.path.join(base, 'dest_dir_existing')
dest_dir2 = os.path.join(base, 'dest_dir_not_existing')
dest_dir3 = os.path.join(base, 'dest_dir_also_not_existing')

open(src_file, 'w').close()
os.mkdir(src_dir)
open(nested_src_file, 'w').close()
os.mkdir(dest_dir1)


def test_copy_file_to_file():
    copy(src_file, dest_file)
    assert os.path.isfile(os.path.join(base, 'dest1', 'dest_file'))


def test_copy_file_to_ex_dir():
    copy(src_file, dest_dir1)
    assert os.path.isfile(os.path.join(base, 'dest_dir_existing', 'src_file'))


def test_copy_file_to_not_ex_dir():
    copy(src_file, dest_dir2)
    assert os.path.isfile(os.path.join(base, 'dest_dir_not_existing'))


def test_copy_dir_to_dir():
    copy(src_dir, dest_dir3)
    assert os.path.isdir(os.path.join(base, 'dest_dir_also_not_existing'))
    assert os.path.isfile(os.path.join(base, 'dest_dir_also_not_existing',
                                       'nested_src_file'))


def gm_old(values):
    return round(reports.prod(values) ** (1 / len(values)), 2)


def test_gm1():
    lists = [1, 2, 4, 5], [0.4, 0.8], [2, 8], [10 ** (-5), 5000]
    for l in lists:
        assert round(gm_old(l), 2) == round(gm(l), 2)


def test_statistics():
    props = {}
    parse_statistics('Translator peak memory: 12345 KB\n'
                      'Preprocessor facts: 123\n'
                      'Translator facts: 543\n', props)
    assert props == {'translator_peak_memory': 12345, 'preprocessor_facts': 123,
                     'translator_facts': 543}

def test_none_removal():
    @tools.remove_none_values
    def minimum(values):
        return min(values)

    assert minimum([1, 2]) == 1
    assert minimum([1, 2, None]) == 1
    assert minimum([None, None]) == None
