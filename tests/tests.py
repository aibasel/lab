from __future__ import division

import os
import datetime
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)-s %(levelname)-8s %(message)s',)

from tools import copy, prod
from reports import gm
import tools

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
    return round(prod(values) ** (1 / len(values)), 2)


def test_gm1():
    lists = [1, 2, 4, 5], [0.4, 0.8], [2, 8], [10 ** (-5), 5000]
    for l in lists:
        assert gm_old(l) == gm(l)


def test_rounding():
    assert tools.round_to_next_power_of_ten(1) == 1
    assert tools.round_to_next_power_of_ten(2) == 10
    assert tools.round_to_next_power_of_ten(10) == 10
    assert tools.round_to_next_power_of_ten(11) == 100


if __name__ == '__main__':
    test_copy_file_to_file()
    test_copy_file_to_ex_dir()
    test_copy_file_to_not_ex_dir()
    test_copy_dir_to_dir()
    test_gm1()
