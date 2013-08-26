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

import logging
import os
import sys

from lab import tools
from lab.tools import run_command, get_command_output


ABS_REV_CACHE = {}


def _escape_char(c):
    if c.isalnum() or c == '_':
        return c
    return '_%d_' % ord(c)


def escape_revision_name(name):
    return ''.join(_escape_char(c) for c in name).upper()


def get_global_rev(repo, rev=None):
    cmd = ['hg', 'id', '-i']
    if rev:
        cmd.extend(['-r', str(rev)])
    return tools.get_command_output(cmd, cwd=repo, quiet=True)


def greatest_common_ancestor(repo, rev1, rev2):
    long_rev = tools.get_command_output(['hg', 'debugancestor', str(rev1), str(rev2)],
                                        cwd=repo, quiet=True)
    number, hexcode = long_rev.split(':')
    return get_global_rev(repo, rev=hexcode)


def get_combinations(repo, rev, base_rev=None):
    """
    Return combinations that compare *rev* with *base_rev*. If *base_rev* is
    None, use the newest common revision of *rev* and the *default* branch.
    """
    if not base_rev:
        base_rev = greatest_common_ancestor(repo, rev, 'default')
    if not base_rev:
        logging.critical('Base revision for branch \'%s\' could not be determined. '
                         'Please provide it manually.' % rev)
    return [(Translator(repo, rev=r),
             Preprocessor(repo, rev=r),
             Planner(repo, rev=r))
            for r in (rev, base_rev)]


class Checkout(object):
    REV_CACHE_DIR = os.path.join(tools.DEFAULT_USER_DIR, 'revision-cache')

    def __init__(self, part, repo, rev, checkout_dir):
        # Directory name of the planner part (translate, preprocess, search)
        self.part = part
        self.repo = repo
        self.rev = str(rev)
        self.checkout_dir = checkout_dir

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    @property
    def name(self):
        """
        Nickname for the checkout that is used for the reports and comparisons.
        """
        if self.rev == 'WORK':
            return 'WORK'
        return os.path.basename(self.checkout_dir)

    def checkout(self):
        raise NotImplementedError

    def compile(self, options=None):
        raise NotImplementedError

    def get_path(self, *rel_path):
        #assert os.path.isabs(self.checkout_dir), self.checkout_dir
        return os.path.join(Checkout.REV_CACHE_DIR, self.checkout_dir, *rel_path)

    def get_bin(self, *bin_path):
        """Return the absolute path to one of this part's executables."""
        return os.path.join(self.bin_dir, *bin_path)

    def get_path_dest(self, *rel_path):
        return os.path.join('code-' + self.name, *rel_path)

    def get_bin_dest(self):
        return self.get_path_dest(self.part, self.part)

    @property
    def src_dir(self):
        """Return the path to the global Fast Downward source directory.

        The directory "downward" dir has been renamed to "src", so this code
        doesn't work for older changesets. We can't check for the dir's
        existence here though, because the directory might not have been created
        yet."""
        return self.get_path('src')

    @property
    def bin_dir(self):
        return os.path.join(self.src_dir, self.part)

    @property
    def shell_name(self):
        return '%s_%s' % (self.part.upper(), escape_revision_name(self.name))


# ---------- Mercurial --------------------------------------------------------

class HgCheckout(Checkout):
    """
    Base class for the three checkout classes Translator, Preprocessor,
    Planner.
    """
    def __init__(self, part, repo, rev='WORK', dest=None):
        """
        *part* must be one of translate, preprocess, search. It is set by the
        child classes.

        *repo* must be a path to a Fast Downward mercurial repository. The
        path can be either local or remote.

        *rev* can be any any valid hg revision specifier (e.g. 209,
        0d748429632d, tip, issue324) or "WORK". If *rev* is "WORK" (default),
        the working copy found at *repo* will be used.

        The destination of a checkout is determined as follows:

        - *dest* is absolute: <dest>
        - *dest* is relative: ~/lab/revision-cache/<dest>
        - *dest* is None: ~/lab/revision-cache/<rev>

        You have to use the *dest* parameter if you need to checkout the same
        revision multiple times and want to alter each checkout manually
        (e.g. for comparing Makefile options).
        """
        if dest and rev == 'WORK':
            logging.error('You cannot have multiple copies of the working '
                          'copy. Please specify a specific revision.')
            sys.exit(1)

        # Find proper absolute revision
        abs_rev = self.get_abs_rev(repo, rev)

        if abs_rev.upper() == 'WORK':
            checkout_dir = repo
        else:
            checkout_dir = str(dest or rev)

        Checkout.__init__(self, part, repo, abs_rev, checkout_dir)

    def get_abs_rev(self, repo, rev):
        rev = str(rev)
        if rev.upper() == 'WORK':
            return 'WORK'
        if (repo, rev) in ABS_REV_CACHE:
            return ABS_REV_CACHE[(repo, rev)]
        abs_rev = get_global_rev(repo, rev=rev)
        if not abs_rev:
            logging.critical('Revision %s not present in repo %s' % (rev, repo))
        ABS_REV_CACHE[(repo, rev)] = abs_rev
        return abs_rev

    def checkout(self):
        # We don't need to check out the working copy
        if self.rev == 'WORK':
            return

        path = os.path.abspath(os.path.join(Checkout.REV_CACHE_DIR, self.checkout_dir))
        if not os.path.exists(path):
            # Old mercurial versions need the clone's parent directory to exist.
            tools.makedirs(path)
            run_command(['hg', 'clone', '-r', self.rev, self.repo, path])
        else:
            logging.info('Checkout "%s" already exists' % path)
            run_command(['hg', 'pull', self.repo], cwd=path)

        retcode = run_command(['hg', 'update', '-r', self.rev], cwd=path)
        if not retcode == 0:
            # Unknown revision or update crossing branches.
            logging.critical('Repo at %s could not be updated to revision %s. '
                             'Please delete the cached repo and try again.' %
                             (path, self.rev))


class Translator(HgCheckout):
    def __init__(self, *args, **kwargs):
        HgCheckout.__init__(self, 'translate', *args, **kwargs)

    def get_bin_dest(self):
        return self.get_path_dest('translate', 'translate.py')


class Preprocessor(HgCheckout):
    def __init__(self, *args, **kwargs):
        HgCheckout.__init__(self, 'preprocess', *args, **kwargs)

    def compile(self, options=None):
        options = options or []
        retcode = run_command(['make'] + options, cwd=self.bin_dir)
        if not retcode == 0:
            logging.critical('Build failed in: %s' % self.bin_dir)


class Planner(HgCheckout):
    def __init__(self, *args, **kwargs):
        HgCheckout.__init__(self, 'search', *args, **kwargs)

    def compile(self, options=None):
        options = options or []
        for size in [1, 2, 4]:
            retcode = run_command(['make', 'STATE_VAR_BYTES=%d' % size] + options,
                                  cwd=self.bin_dir)
            if not retcode == 0:
                logging.critical('Build failed in: %s' % self.bin_dir)

# -----------------------------------------------------------------------------
