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

import inspect
import json
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


def _prepare_config(config, optimal):
    config = [i.strip() for i in config]
    # Don't use bounds for optimal planning.
    if optimal:
        return config

    for i, entry in enumerate(config):
        if entry == '--search':
            search = config[i + 1]
            if 'bound=infinity' in search:
                search = search.replace('bound=infinity', 'bound=BOUND')
            elif 'bound=BOUND' not in search:
                search = search[:-1] + ',bound=BOUND)'
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
    portfolio = [(t, _prepare_config(config, optimal)) for t, config in portfolio]
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
        content = content.replace(',bound=BOUND', '')
        content = content.replace('import portfolio', '')
        content = content.replace('portfolio.run', 'pass #portfolio.run')

    with tempfile.NamedTemporaryFile(suffix='.py') as dest:
        dest.write(content)
        dest.flush()
        return tools.import_python_file(dest.name).CONFIGS


def print_config(config):
    for part in config:
        if part.startswith('--'):
            print part,
        else:
            print '"%s"' % part,
    print
