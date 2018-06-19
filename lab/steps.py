# -*- coding: utf-8 -*-
#
# Lab is a Python package for evaluating algorithms.
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

import logging
import traceback

from lab import tools


class Step(object):
    """
    When the step is executed *args* and *kwargs* will be passed to the
    callable *func*. ::

        exp.add_step('show-disk-usage', subprocess.call, ['df'])

    """
    def __init__(self, name, func, *args, **kwargs):
        assert func is not None
        self.name = name
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._funcname = (
            getattr(func, '__name__', None) or
            func.__class__.__name__.lower())

    def __call__(self):
        if self.func is None:
            logging.critical('You cannot run the same step more than once')
        logging.info('Running step %s: %s' % (self.name, self))
        try:
            retval = self.func(*self.args, **self.kwargs)
            # Free memory
            self.func = None
            if retval:
                logging.critical(
                    'An error occured in step {}.'.format(self.name))
            return retval
        except (ValueError, TypeError):
            traceback.print_exc()
            logging.critical('Could not run step {}'.format(self))

    def __str__(self):
        return '{name}({args}{sep}{kwargs})'.format(
            name=self._funcname,
            args=', '.join(repr(arg) for arg in self.args),
            sep=', ' if self.args and self.kwargs else '',
            kwargs=', '.join([
                '{}={!r}'.format(k, v)
                for (k, v) in sorted(self.kwargs.items())]))


def _get_step_index(steps, step_name):
    for index, step in enumerate(steps):
        if step.name == step_name:
            return index
    logging.critical('There is no step called "{}"'.format(step_name))


def get_step(steps, step_name):
    """*step_name* can be a step's name or number."""
    if step_name.isdigit():
        try:
            return steps[int(step_name) - 1]
        except IndexError:
            logging.critical('There is no step number {}'.format(step_name))
    return steps[_get_step_index(steps, step_name)]


def get_steps_text(steps):
    # Use width 0 if no steps have been added.
    name_width = min(max([len(step.name) for step in steps] + [0]), 50)
    terminal_width, _terminal_height = tools.get_terminal_size()
    terminal_width = terminal_width or 80
    lines = ['Available steps:', '================']
    for number, step in enumerate(steps, start=1):
        line = ' '.join([str(number).rjust(2), step.name.ljust(name_width)])
        step_text = str(step)
        if len(line) + len(step_text) < terminal_width:
            lines.append(line + ' ' + step_text)
        else:
            lines.extend(['', line, step_text, ''])
    return '\n'.join(lines)
