# -*- coding: utf-8 -*-
#
# downward uses the lab package to conduct experiments with the
# Fast Downward planning system.
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

import os
import shutil
import sys
import logging

from lab import tools
from lab.tools import run_command, get_command_output

REV_CACHE_DIR = os.path.join(tools.USER_DIR, 'revision-cache')
tools.makedirs(REV_CACHE_DIR)

ABS_REV_CACHE = {}
PARENT_REV_CACHE = {}


class Checkout(object):
    def __init__(self, part, repo, rev, checkout_dir):
        # Directory name of the planner part (translate, preprocess, search)
        self.part = part
        self.repo = repo
        self.rev = str(rev)

        if not os.path.isabs(checkout_dir):
            checkout_dir = os.path.join(REV_CACHE_DIR, checkout_dir)
        self.checkout_dir = os.path.abspath(checkout_dir)

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
        return os.path.join(self.checkout_dir, *rel_path)

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

        The directory "downward" dir has been renamed to "src", but we still
        want to support older changesets."""
        assert os.path.exists(self.checkout_dir), self.checkout_dir
        src_dir = self.get_path('src')
        if not os.path.exists(src_dir):
            src_dir = self.get_path('downward')
        return src_dir

    @property
    def bin_dir(self):
        return os.path.join(self.src_dir, self.part)

    @property
    def parent_rev(self):
        raise NotImplementedError

    @property
    def shell_name(self):
        return '%s_%s' % (self.part.upper(), self.name)


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

        By default all checkouts will be made to <REVISION_CACHE>/<REVISION>.
        If *dest* is given however, the destination directory will be <dest> if
        dest is absolute or <REVISION_CACHE>/<dest> otherwise. Use this
        parameter if you need to checkout the same revision multiple times and
        want to alter each checkout manually (e.g. for comparing Makefile
        options).
        """
        if dest and rev == 'WORK':
            logging.error('You cannot have multiple copies of the working '
                          'copy. Please specify a specific revision.')
            sys.exit(1)

        # Find proper absolute revision
        rev = self.get_abs_rev(repo, rev)

        if rev.upper() == 'WORK':
            checkout_dir = repo
        else:
            checkout_dir = dest if dest else rev

        Checkout.__init__(self, part, repo, rev, checkout_dir)

    def get_abs_rev(self, repo, rev):
        if str(rev).upper() == 'WORK':
            return 'WORK'
        cmd = ['hg', 'id', '-ir', str(rev).lower(), repo]
        cmd_string = ' '.join(cmd)
        if cmd_string in ABS_REV_CACHE:
            return ABS_REV_CACHE[cmd_string]
        abs_rev = get_command_output(cmd, quiet=True)
        if not abs_rev:
            logging.error('Revision %s not present in repo %s' % (rev, repo))
            sys.exit(1)
        ABS_REV_CACHE[cmd_string] = abs_rev
        return abs_rev

    def checkout(self):
        # We don't need to check out the working copy
        if self.rev == 'WORK':
            return

        path = self.checkout_dir
        if not os.path.exists(path):
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
        # Save space by deleting the benchmarks.
        shutil.rmtree(os.path.join(path, 'benchmarks'), ignore_errors=True)

    @property
    def parent_rev(self):
        rev = 'tip' if self.rev == 'WORK' else self.rev
        if rev in PARENT_REV_CACHE:
            return PARENT_REV_CACHE[rev]
        cmd = ['hg', 'log', '-r', rev, '--template', '{node|short}']
        parent = get_command_output(cmd, cwd=self.checkout_dir)
        PARENT_REV_CACHE[rev] = parent
        return parent


class Translator(HgCheckout):
    def __init__(self, *args, **kwargs):
        HgCheckout.__init__(self, 'translate', *args, **kwargs)


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
