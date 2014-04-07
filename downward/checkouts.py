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
import shutil

from lab import tools


_HG_ID_CACHE = {}


def hg_id(repo, args=None, rev=None):
    args = args or []
    if rev:
        args.extend(['-r', str(rev)])
    cmd = ('hg', 'id', '--repository', repo) + tuple(args)
    if cmd not in _HG_ID_CACHE:
        result = tools.get_command_output(cmd, quiet=True)
        if not result:
            logging.critical('Call failed: "%s". Check path and revision.' %
                             ' '.join(cmd))
        _HG_ID_CACHE[cmd] = result
    return _HG_ID_CACHE[cmd]


def get_global_rev(repo, rev=None):
    return hg_id(repo, args=['-i'], rev=rev)


def get_rev_id(repo, rev=None):
    return hg_id(repo, rev=rev)


def get_common_ancestor(repo, rev1, rev2='default'):
    """
    Return the global changeset id of the greatest common ancestor of revisions
    *rev1* and *rev2* in *repo*. If *rev2* is omitted return the revision at
    which *rev1* was branched off the default branch. Note that if *rev1* has
    been merged into the default branch, this method returns *rev1*.
    """
    long_rev = tools.get_command_output(
        ['hg', '-R', repo, 'debugancestor', str(rev1), str(rev2)])
    if not long_rev:
        logging.critical('%s or %s is not part of the repo at %s.' %
                         (rev1, rev2, repo))
    number, hexcode = long_rev.split(':')
    return get_global_rev(repo, rev=hexcode)


class Checkout(object):
    REV_CACHE_DIR = None  # Set by DownwardExperiment.

    def __init__(self, part, repo, rev, nick, summary, dest):
        """
        * *part*: Planner part (translate, preprocess or search).
        * *repo*: Path to Fast Downward repository.
        * *rev*: Global Fast Downward revision.
        * *nick*: Nickname for this checkout.
        * *summary*: Summary (revision, branch, tags) for this checkout.
        * *dest*: Checkout destination.
        """
        self.part = part
        self.repo = repo
        self.rev = rev
        self.nick = nick
        self.summary = summary
        self.dest = dest

    def __eq__(self, other):
        return self.rev == other.rev

    def __hash__(self):
        return hash(self.rev)

    def checkout(self):
        raise NotImplementedError

    def compile(self, options=None):
        raise NotImplementedError

    def get_path(self, *rel_path):
        return os.path.join(Checkout.REV_CACHE_DIR, self.dest, *rel_path)

    def get_bin(self, *bin_path):
        """Return the absolute path to one of this part's executables."""
        return os.path.join(self.bin_dir, *bin_path)

    def get_path_dest(self, *rel_path):
        return os.path.join('code-' + self.rev, *rel_path)

    def get_bin_dest(self):
        return self.get_path_dest(self.part, self.BIN_NAME)

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
        # The only non-alphanumeric char in global revisions is the plus sign.
        return '%s_%s' % (self.part.upper(), self.rev.replace('+', 'PLUS'))

    def __repr__(self):
        return '%s:%s:%s' % (self.repo, self.rev, self.part)


class HgCheckout(Checkout):
    """
    Base class for the three checkout classes Translator, Preprocessor,
    Planner.
    """
    DEFAULT_REV = 'WORK'

    def __init__(self, part, repo, rev=None, nick=None):
        """
        *part* must be one of translate, preprocess or search. It is set by the
        child classes.

        *repo* must be a path to a **local** Fast Downward Mercurial repository.

        *rev* can be any any valid hg revision specifier (e.g. 209,
        0d748429632d, tip, issue324) or "WORK". By default the working copy
        found at *repo* will be used.

        In the reports the planner part will be called *nick*. It defaults to
        *rev*.

        If *rev* is not 'WORK' the checkout will be made to
        ``cache_dir``/revision-cache/``hash_id`` where ``cache_dir`` is
        the cache directory set in the Experiment constructor and
        ``hash_id`` is the global revision id corresponding to the
        local revision id *rev*.

        .. versionchanged :: 1.6

            Removed *dest* keyword argument.
            Removed support for remote repositories.

        """
        local_rev = str(rev or self.DEFAULT_REV)

        if local_rev == 'WORK':
            global_rev = 'WORK'
            nick = nick or 'WORK'
            summary = 'WORK ' + get_rev_id(repo)
            dest = repo
        else:
            global_rev = get_global_rev(repo, local_rev)
            nick = nick or local_rev
            summary = get_rev_id(repo, local_rev)
            dest = global_rev
        Checkout.__init__(self, part, repo, global_rev, nick, summary, dest)

    def checkout(self, compilation_options=None):
        path = self.get_path()
        if self.rev == 'WORK':
            self._compile(compilation_options)
            return

        if not os.path.exists(path):
            # Old mercurial versions need the clone's parent directory to exist.
            tools.makedirs(path)
            retcode = tools.run_command(
                ['hg', 'archive', '-r', self.rev, '-I', 'src', path], cwd=self.repo)
            if retcode != 0:
                shutil.rmtree(path)
                logging.critical('Failed to make checkout.')
            self._compile(compilation_options)
            self._cleanup()
        else:
            logging.info('Checkout "%s" already exists' % path)

    def _compile(self, options=None):
        options = options or []
        retcode = tools.run_command(['./build_all'] + options, cwd=self.src_dir)
        if retcode != 0:
            logging.critical('Build failed in: %s' % self.src_dir)

    def _cleanup(self):
        assert self.rev != 'WORK'
        tools.run_command(['./build_all', 'clean'], cwd=self.src_dir)
        # Strip binaries.
        downward_bin = os.path.join(self.src_dir, 'search', 'downward-release')
        preprocess_bin = os.path.join(self.src_dir, 'preprocess', 'preprocess')
        assert os.path.exists(preprocess_bin), preprocess_bin
        binaries = [preprocess_bin]
        if os.path.exists(downward_bin):
            binaries.append(downward_bin)
        tools.run_command(['strip'] + binaries)
        # Remove unneeded files from "src" dir if they exist.
        # TODO: Remove "lp" and "ext" dirs?
        for name in ['dist', 'VAL', 'validate']:
            path = os.path.join(self.src_dir, name)
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)


class Translator(HgCheckout):
    BIN_NAME = 'translate.py'

    def __init__(self, *args, **kwargs):
        HgCheckout.__init__(self, 'translate', *args, **kwargs)


class Preprocessor(HgCheckout):
    BIN_NAME = 'preprocess'

    def __init__(self, *args, **kwargs):
        HgCheckout.__init__(self, 'preprocess', *args, **kwargs)


class Planner(HgCheckout):
    BIN_NAME = 'downward'

    def __init__(self, *args, **kwargs):
        HgCheckout.__init__(self, 'search', *args, **kwargs)
