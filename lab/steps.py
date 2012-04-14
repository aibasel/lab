# -*- coding: utf-8 -*-
#
# lab is a Python API for running and evaluating algorithms.
#
# Copyright (C) 2012  Jendrik Seipp (jendrikseipp@web.de)
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

import getpass
import os
import logging
import shutil
from subprocess import call


class Step(object):
    """
    When the step is executed *args* and *kwargs* will be passed to the
    callable *func*.

    >>> exp.add_step(Step('show-disk-usage', subprocess.call, ['df']))
    >>> exp.add_step(Step('combine-results', Fetcher(), 'path/to/eval-dir',
                          'path/to/new-eval-dir'))

    """
    def __init__(self, name, func, *args, **kwargs):
        self.name = name
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        if self.func is None:
            logging.critical('You cannot run the same step more than once')
        try:
            retval = self.func(*self.args, **self.kwargs)
            # Free memory
            self.func = None
            return retval
        except (ValueError, TypeError):
            import traceback
            traceback.print_exc()
            logging.critical('Could not run step: %s' % self)

    def __str__(self):
        funcname = getattr(self.func, '__name__', None) or self.func.__class__.__name__.lower()
        return '%s(%s%s%s)' % (funcname,
                               ', '.join([repr(arg) for arg in self.args]),
                               ', ' if self.args and self.kwargs else '',
                               ', '.join(['%s=%s' % (k, repr(v)) for (k, v) in self.kwargs.items()]))

    @classmethod
    def publish_reports(cls, *report_files):
        """Return a step that copies all *report_files* to $HOME/.public_html.

        >>> exp.add_step(Step.publish_reports(file1, file2)

        """
        user = getpass.getuser()

        def publish_reports():
            for path in report_files:
                name = os.path.basename(path)
                dest = os.path.join(os.path.expanduser('~'), '.public_html/', name)
                shutil.copy2(path, dest)
                print 'Copied report to file://%s' % dest
                print '-> http://www.informatik.uni-freiburg.de/~%s/%s' % (user, name)

        return cls('publish_reports', publish_reports)

    @classmethod
    def zip_exp_dir(cls, exp):
        """
        Return a Step that creates a compressed tarball containing the
        experiment directory. For symbolic links this step stores the
        referenced files, not the links themselves.

        >>> exp.add_step(Step.zip_exp_dir(exp))

        """
        return cls('zip-exp-dir', call,
                   ['tar', '--dereference', '-czf', exp.name + '.tar.gz', exp.name],
                   cwd=os.path.dirname(exp.path))

    @classmethod
    def unzip_exp_dir(cls, exp):
        """
        Return a Step that unzips a compressed tarball containing the
        experiment directory.

        >>> exp.add_step(Step.unzip_exp_dir(exp))

        """
        return cls('unzip-exp-dir', call,
                   ['tar', '-xzf', exp.name + '.tar.gz'],
                   cwd=os.path.dirname(exp.path))

    @classmethod
    def remove_exp_dir(cls, exp):
        """Return a Step that removes the experiment directory.

        >>> exp.add_step(Step.remove_exp_dir(exp))

        """
        return cls('remove-exp-dir', shutil.rmtree, exp.path)


class Sequence(list):
    """This class holds all steps of an experiment."""
    def _get_step_index(self, step_name):
        for index, step in enumerate(self):
            if step.name == step_name:
                return index
        logging.critical('There is no step called %s' % step_name)

    def process_step_names(self, names):
        for step_name in names:
            self.process_step_name(step_name)

    def process_step_name(self, step_name):
        """*step_name* can be a step's name or number."""
        if step_name.isdigit():
            try:
                step = self[int(step_name) - 1]
            except IndexError:
                logging.critical('There is no step number %s' % step_name)
            self.run_step(step)
        elif step_name == 'next':
            raise NotImplementedError
        elif step_name == 'all':
            # Run all steps
            for step in self:
                self.run_step(step)
        else:
            step_index = self._get_step_index(step_name)
            if step_index >= 0:
                self.run_step(self[step_index])

    def run_step(self, step):
        logging.info('Running %s: %s' % (step.name, step))
        returnval = step()
        if returnval:
            logging.critical('An error occured in %s, the return value was %s' % (step, returnval))

    def remove_step(self, step_name):
        """Delete the step with the name *step_name*."""
        index = self._get_step_index(step_name)
        del self[index]

    def get_steps_text(self):
        name_width = min(max(len(step.name) for step in self), 50)
        lines = ['Available steps:', '================']
        for number, step in enumerate(self, start=1):
            lines.append(' '.join([str(number).rjust(2), step.name.ljust(name_width), str(step)]))
        return '\n'.join(lines)
