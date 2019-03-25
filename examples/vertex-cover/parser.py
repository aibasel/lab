#! /usr/bin/env python

"""
Solver example output:

Algorithm: 2approx
Cover: set([1, 3, 5, 6, 7, 8, 9])
Cover size: 7
Solve time: 0.000771s
"""

from lab.parser import Parser


def solved(content, props):
    props['solved'] = int('cover' in props)


def error(content, props):
    if props['solved']:
        props['error'] = 'cover-found'
    else:
        props['error'] = 'unsolved'


if __name__ == '__main__':
    parser = Parser()
    parser.add_pattern(
        'node', r'node: (.+)\n', type=str, file='driver.log', required=True)
    parser.add_pattern(
        'solver_exit_code', r'solve exit code: (.+)\n', type=int, file='driver.log')
    parser.add_pattern('cover', r'Cover: set\(\[(.*)\]\)', type=str)
    parser.add_pattern('cover_size', r'Cover size: (\d+)\n', type=int)
    parser.add_pattern('solve_time', r'Solve time: (.+)s', type=float)
    parser.add_function(solved)
    parser.add_function(error)
    parser.parse()
