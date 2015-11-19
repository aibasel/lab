# -*- coding: utf-8 -*-
#
# lab is a Python API for running and evaluating algorithms.
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
import os
import shutil
from subprocess import call

import tools


class Step(object):
    """
    When the step is executed *args* and *kwargs* will be passed to the
    callable *func*. ::

        exp.add_step(Step('show-disk-usage', subprocess.call, ['df']))
        exp.add_step(Step('combine-results', Fetcher(), 'path/to/eval-dir',
                          'path/to/new-eval-dir'))

    """
    def __init__(self, name, func, *args, **kwargs):
        self.name = name
        self.func = func
        self.args = list(args)
        self.kwargs = kwargs

    def __call__(self):
        if self.func is None:
            logging.critical('You cannot run the same step more than once')
        logging.info('Running %s: %s' % (self.name, self))
        try:
            retval = self.func(*self.args, **self.kwargs)
            # Free memory
            self.func = None
            if retval:
                logging.critical('An error occured in %s, the return value was %s' %
                                 (self.name, retval))
            return retval
        except (ValueError, TypeError):
            import traceback
            traceback.print_exc()
            logging.critical('Could not run step: %s' % self)

    @property
    def _funcname(self):
        return (getattr(self.func, '__name__', None) or
                self.func.__class__.__name__.lower())

    # TODO: Can we remove this after cleaning up the environments module?
    def copy(self):
        """Return a copy of this Step."""
        return Step(self.name, self.func, *self.args[:], **self.kwargs.copy())

    def __str__(self):
        return '%s(%s%s%s)' % (self._funcname,
                               ', '.join([repr(arg) for arg in self.args]),
                               ', ' if self.args and self.kwargs else '',
                               ', '.join(['%s=%s' % (k, repr(v))
                                          for (k, v) in self.kwargs.items()]))

    _predefined_steps_warning = (
        'Predefined steps have been deprecated in version 1.8. '
        'Please define your extra experiment steps manually.')

    @classmethod
    @tools.deprecated(_predefined_steps_warning)
    def zip_exp_dir(cls, exp):
        """
        Return a Step that creates a compressed tarball containing the
        experiment directory. For symbolic links this step stores the
        referenced files, not the links themselves. ::

            exp.add_step(Step.zip_exp_dir(exp))

        .. deprecated:: 1.8

            Please define your extra experiment steps manually.

        """
        return cls('zip-exp-dir', call,
                   ['tar', '-cjf', exp.name + '.tar.bz2', exp.name],
                   cwd=os.path.dirname(exp.path))

    @classmethod
    @tools.deprecated(_predefined_steps_warning)
    def unzip_exp_dir(cls, exp):
        """
        Return a Step that unzips a compressed tarball containing the
        experiment directory. ::

            exp.add_step(Step.unzip_exp_dir(exp))

        .. deprecated:: 1.8

            Please define your extra experiment steps manually.

        """
        return cls('unzip-exp-dir', call,
                   ['tar', '-xjf', exp.name + '.tar.bz2'],
                   cwd=os.path.dirname(exp.path))

    @classmethod
    @tools.deprecated(_predefined_steps_warning)
    def remove_exp_dir(cls, exp):
        """Return a Step that removes the experiment directory.

        ::

            exp.add_step(Step.remove_exp_dir(exp))

        .. deprecated:: 1.8

            Please define your extra experiment steps manually.

        """
        return cls('remove-exp-dir', shutil.rmtree, exp.path)


class Sequence(list):
    """This class holds all steps of an experiment."""
    def _get_step_index(self, step_name):
        for index, step in enumerate(self):
            if step.name == step_name:
                return index
        logging.critical('There is no step called %s' % step_name)

    def get_step(self, step_name):
        """*step_name* can be a step's name or number."""
        if step_name.isdigit():
            try:
                return self[int(step_name) - 1]
            except IndexError:
                logging.critical('There is no step number %s' % step_name)
        return self[self._get_step_index(step_name)]

    def get_steps_text(self):
        # Use width 0 if no steps have been added.
        name_width = min(max([len(step.name) for step in self] + [0]), 50)
        terminal_width, terminal_height = tools.get_terminal_size()
        terminal_width = terminal_width or 80
        lines = ['Available steps:', '================']
        for number, step in enumerate(self, start=1):
            line = ' '.join([str(number).rjust(2), step.name.ljust(name_width)])
            step_text = str(step)
            if len(line) + len(step_text) < terminal_width:
                lines.append(line + ' ' + step_text)
            else:
                lines.extend(['', line, step_text, ''])
        return '\n'.join(lines)
