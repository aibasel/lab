# -*- coding: utf-8 -*-
#
# downward uses the lab package to conduct experiments with the
# Fast Downward planning system.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" Preliminary module for working with Fast Downward portfolios.

Since the mechanism for loading portfolios in Fast Downward is
subject to change, this part of the downward package is not
considered stable and is therefore not part of the HTML
documentation. """

import inspect
import json
import re
import tempfile

from lab import tools


TEMPLATE = '''\
#! /usr/bin/env python
# -*- coding: utf-8 -*-

import portfolio
{notes}
num_configs = {num_configs}
total_time = {total_time}

CONFIGS = {portfolio}
{final_config_source}
{final_config_builder_source}
portfolio.run(CONFIGS, {kwargs_string})
'''


def set_bound(config, bound):
    assert bound in ['BOUND', 'infinity'] or isinstance(bound, int), bound
    config = [i.strip() for i in config]

    for i, entry in enumerate(config):
        if entry == '--search':
            search = config[i + 1]
            search, num_subs = re.subn(
                r'bound=(?:\d+|BOUND|infinity)', 'bound=%s' % bound, search)
            assert num_subs <= 1, config
            if num_subs == 0:
                search = search[:-1] + ',bound=%s)' % bound
            config[i + 1] = search
    return config


def _pad_if_not_empty(string):
    if string:
        return '\n{0}\n'.format(string)
    return ''


def _get_name_and_source(func):
    if func:
        return (func.__name__, _pad_if_not_empty(inspect.getsource(func)))
    return (None, '')


def create_portfolio_script(portfolio, optimal, final_config=None,
                            final_config_builder=None, notes=''):
    total_time = sum(time for time, config in portfolio)
    num_configs = len(portfolio)
    if not optimal:
        portfolio = [(t, set_bound(config, 'BOUND')) for t, config in portfolio]
    portfolio = json.dumps(portfolio, indent=4, separators=(',', ': '))
    final_config_name, final_config_source = _get_name_and_source(final_config)
    (final_config_builder_name,
        final_config_builder_source) = _get_name_and_source(final_config_builder)
    notes = _pad_if_not_empty(notes)
    kwargs = {'optimal': optimal}
    if final_config_name is not None:
        kwargs['final_config'] = final_config_name
    if final_config_builder_name is not None:
        kwargs['final_config_builder'] = final_config_builder_name
    kwargs_string = ', '.join('%s=%s' % pair for pair in kwargs.items())
    return TEMPLATE.format(**locals())


def import_portfolio(path):
    with open(path) as src:
        content = src.read()
        # Remove everything before and after the configs.
        content = content[content.find('CONFIGS'):]
        content = content[:content.find('portfolio.run')] + 'pass'
        content = content.replace(',bound=BOUND', '')

    with tempfile.NamedTemporaryFile(suffix='.py') as dest:
        dest.write(content)
        dest.flush()
        return tools.import_python_file(dest.name).CONFIGS
