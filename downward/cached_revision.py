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

import glob
import hashlib
import logging
import os.path
import shutil
import subprocess

from lab import tools

from downward.checkouts import get_global_rev, get_rev_id


def _get_options_relevant_for_cache_name(options):
    """
    Remove "-j", "-j4" and "-j 4" options.

    These options do not influence the result of the build and a build
    shouldn't be done again just because we build with a different
    number of jobs.

    This behaviour is important on the grid, where the compute and the
    job submission nodes have different numbers of cores. If we made
    these options part of the directory name, lab would try to
    recompile the planner on a compute node, which is undesirable.
    """
    relevant_options = options[:]
    for index, option in enumerate(relevant_options):
        if option and option.startswith('-j'):
            jobs = option[2:]
            if not jobs or jobs.isdigit():
                relevant_options[index] = None
            if not jobs and len(relevant_options) > index + 1:
                next_option = relevant_options[index + 1]
                if next_option.isdigit():
                    relevant_options[index + 1] = None
    return [x for x in relevant_options if x is not None]


def _compute_md5_hash(mylist):
    m = hashlib.md5()
    for s in mylist:
        m.update(s)
    return m.hexdigest()[:8]


class CachedRevision(object):
    """This class represents Fast Downward checkouts.

    It provides methods for caching and compiling given revisions.
    """
    def __init__(self, repo, local_rev, build_options):
        """
        * *repo*: Path to Fast Downward repository.
        * *local_rev*: Fast Downward revision.
        * *build_options*: List of build.py options.
        """
        if not os.path.isdir(repo):
            logging.critical(
                '{} is not a local Fast Downward repository.'.format(repo))
        self.repo = repo
        self.build_options = build_options
        self.local_rev = local_rev
        self.global_rev = get_global_rev(repo, local_rev)
        self.summary = get_rev_id(self.repo, local_rev)
        self._path = None
        self._hashed_name = self._compute_hashed_name()

    @property
    def path(self):
        assert self._path is not None
        return self._path

    def _compute_hashed_name(self):
        relevant_options = _get_options_relevant_for_cache_name(self.build_options)
        if relevant_options:
            return self.global_rev + '_' + _compute_md5_hash(relevant_options)
        else:
            return self.global_rev

    def cache(self, revision_cache_dir):
        self._path = os.path.join(revision_cache_dir, self._hashed_name)
        if os.path.exists(self.path):
            logging.info('Revision is already cached: "%s"' % self.path)
            if not os.path.exists(self._get_sentinel_file()):
                logging.critical(
                    'The build for the cached revision at {} is corrupted '
                    'or was made with an older lab version. Please delete '
                    'it and try again.'.format(self.path))
        else:
            tools.makedirs(self.path)
            excludes = ['-X{}'.format(d) for d in ['benchmarks', 'experiments', 'misc']]
            retcode = tools.run_command(
                ['hg', 'archive', '-r', self.global_rev] + excludes + [self.path],
                cwd=self.repo)
            if retcode != 0:
                shutil.rmtree(self.path)
                logging.critical('Failed to make checkout.')
            self._compile()
            self._cleanup()

    def get_cached_path(self, *rel_path):
        return os.path.join(self.path, *rel_path)

    def get_exp_path(self, *rel_path):
        return os.path.join('code-' + self._hashed_name, *rel_path)

    def get_planner_resource_name(self):
        return 'FAST_DOWNWARD_' + self._hashed_name

    def _get_sentinel_file(self):
        return self.get_cached_path('build_successful')

    def _compile(self):
        if not os.path.exists(os.path.join(self.path, 'build.py')):
            logging.critical('build.py not found. Please merge with master.')
        retcode = tools.run_command(
            ['./build.py'] + self.build_options, cwd=self.path)
        if retcode == 0:
            tools.touch(self._get_sentinel_file())
        else:
            logging.critical('Build failed in {}'.format(self.path))

    def _cleanup(self):
        # Only keep the bin directories in "builds" dir.
        for path in glob.glob(os.path.join(self.path, "builds", "*", "*")):
            if os.path.basename(path) != 'bin':
                tools.remove_path(path)

        # Remove unneeded files.
        tools.remove_path(self.get_cached_path('build.py'))

        # Strip binaries.
        binaries = []
        for path in glob.glob(os.path.join(self.path, "builds", "*", "bin", "*")):
            if os.path.basename(path) in ['downward', 'preprocess']:
                binaries.append(path)
        subprocess.call(['strip'] + binaries)

        # Compress src directory.
        subprocess.call(
            ['tar', '-cf', 'src.tar', '--remove-files', 'src'],
            cwd=self.path)
        subprocess.call(['xz', 'src.tar'], cwd=self.path)
