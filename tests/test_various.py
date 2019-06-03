import os
import datetime
import logging


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)-s %(levelname)-8s %(message)s',)


from lab.reports import geometric_mean
from lab import tools


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
    tools.copy(src_file, dest_file)
    assert os.path.isfile(os.path.join(base, 'dest1', 'dest_file'))


def test_copy_file_to_ex_dir():
    tools.copy(src_file, dest_dir1)
    assert os.path.isfile(os.path.join(base, 'dest_dir_existing', 'src_file'))


def test_copy_file_to_not_ex_dir():
    tools.copy(src_file, dest_dir2)
    assert os.path.isfile(os.path.join(base, 'dest_dir_not_existing'))


def test_copy_dir_to_dir():
    tools.copy(src_dir, dest_dir3)
    assert os.path.isdir(os.path.join(base, 'dest_dir_also_not_existing'))
    assert os.path.isfile(os.path.join(base, 'dest_dir_also_not_existing',
                                       'nested_src_file'))


def geometric_mean_old(values):
    return tools.product(values) ** (1. / len(values))


def test_geometric_mean1():
    lists = [1, 2, 4, 5], [0.4, 0.8], [2, 8], [10 ** (-5), 5000]
    for l in lists:
        assert round(geometric_mean_old(l), 2) == round(geometric_mean(l), 2)


def test_colors():
    row = {'col 1' : 0, 'col 2' : 0.5, 'col 3' : 1}
    expected_min_wins = {'col 1' : (0.0, 0.7, 0.0), 'col 2' : (0.0, 0.7, 0.7), 'col 3' : (0.0, 0.0, 0.7)}
    expected_max_wins = {'col 1' : (0.0, 0.0, 0.7), 'col 2' : (0.0, 0.7, 0.7), 'col 3' : (0.0, 0.7, 0.0)}
    assert tools.get_colors(row, True) == expected_min_wins
    assert tools.get_colors(row, False) == expected_max_wins
    assert tools.rgb_fractions_to_html_color(1, 0, 0.5) == 'rgb(255,0,127)'
