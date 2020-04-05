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

import hashlib
import logging
import os.path
import shutil
import subprocess
import tarfile

from lab import tools


GIT = "git"
MERCURIAL = "hg"
VERSION_CONTROL_SYSTEMS = [GIT, MERCURIAL]


_ID_CACHE = {}


def _get_id(cmd):
    cmd = tuple(cmd)
    if cmd not in _ID_CACHE:
        try:
            result = tools.get_string(subprocess.check_output(cmd).strip())
        except subprocess.CalledProcessError:
            logging.critical(
                'Call failed: "{}". Please check path and revision.'.format(
                    " ".join(cmd)
                )
            )
        else:
            assert result
            _ID_CACHE[cmd] = result
    return _ID_CACHE[cmd]


def hg_id(repo, args=None, rev=None):
    args = args or []
    if rev:
        args.extend(["-r", str(rev)])
    cmd = ["hg", "id", "--repository", repo] + args
    return _get_id(cmd)


def git_id(repo, args=None, rev=None):
    args = args or []
    if rev:
        args.append(rev)
    cmd = [
        "git",
        "--git-dir",
        os.path.join(repo, ".git"),
        "rev-parse",
        "--short",
    ] + args
    return _get_id(cmd)


def _raise_unknown_vcs_error(vcs):
    raise AssertionError(f'Unknown version control system "{vcs}".')


def get_version_control_system(repo):
    vcs = [
        x
        for x in VERSION_CONTROL_SYSTEMS
        if os.path.exists(os.path.join(repo, f".{x}"))
    ]
    if len(vcs) == 1:
        return vcs[0]
    else:
        logging.critical(
            "Repo {} must contain exactly one of the following subdirectories: {}".format(
                repo, ", ".join(f".{x}" for x in VERSION_CONTROL_SYSTEMS)
            )
        )


def get_global_rev(repo, rev=None):
    vcs = get_version_control_system(repo)
    if vcs == MERCURIAL:
        return hg_id(repo, args=["-i"], rev=rev)
    elif vcs == GIT:
        return git_id(repo, rev=rev)
    else:
        _raise_unknown_vcs_error(vcs)


def get_rev_id(repo, rev=None):
    vcs = get_version_control_system(repo)
    if vcs == MERCURIAL:
        return hg_id(repo, rev=rev)
    elif vcs == GIT:
        return git_id(repo, rev=rev)
    else:
        _raise_unknown_vcs_error(vcs)


def _compute_md5_hash(mylist):
    m = hashlib.md5()
    for s in mylist:
        m.update(tools.get_bytes(s))
    return m.hexdigest()[:8]


class CachedRevision:
    """This class represents checkouts of a solver.

    It provides methods for compiling and caching given revisions.

    .. warning::

        The API for this class is experimental and subject to change.
        Feedback is welcome!
    """

    def __init__(self, repo, rev, build_cmd, exclude=None):
        """
        * *repo*: path to solver repository.
        * *rev*: solver revision.
        * *build_cmd*: list with build script and any build options
          (e.g., ``["./build.py", "release"]``, ``["make"]``).
        * *exclude*: list of paths in repo that are not needed for building
          and running the solver.

        The following example caches a Fast Downward revision. When you
        use the :class:`FastDownwardExperiment
        <downward.experiment.FastDownwardExperiment>` class, you don't
        need to cache revisions yourself since the class will do it
        transparently for you.

        >>> import os
        >>> from lab.cached_revision import get_version_control_system, MERCURIAL
        >>> repo = os.environ["DOWNWARD_REPO"]
        >>> revision_cache = os.environ.get("DOWNWARD_REVISION_CACHE")
        >>> vcs = get_version_control_system(repo)
        >>> rev = "default" if vcs == MERCURIAL else "master"
        >>> cr = CachedRevision(repo, rev, ["./build.py"], exclude=["experiments"])
        >>> cr.cache(revision_cache)

        You can now copy the cached repo to your experiment:

        >>> from lab.experiment import Experiment
        >>> exp = Experiment()
        >>> cache_path = os.path.join(revision_cache, cr.name)
        >>> dest_path = os.path.join(exp.path, "code-" + cr.name)
        >>> exp.add_resource("solver_" +  cr.name, cache_path, dest_path)

        """
        if not os.path.isdir(repo):
            logging.critical(f"{repo} is not a local solver repository.")
        self.repo = repo
        self.build_cmd = build_cmd
        self.local_rev = rev
        self.global_rev = get_global_rev(repo, rev)
        self.summary = get_rev_id(self.repo, rev)
        self.path = None
        self.exclude = exclude or []
        self.name = self._compute_hashed_name()

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def _compute_hashed_name(self):
        return "{}_{}".format(
            self.global_rev, _compute_md5_hash(self.build_cmd + self.exclude)
        )

    def cache(self, revision_cache):
        self.path = os.path.join(revision_cache, self.name)
        if os.path.exists(self.path):
            logging.info('Revision is already cached: "%s"' % self.path)
            if not os.path.exists(self._get_sentinel_file()):
                logging.critical(
                    "The build for the cached revision at {} is corrupted. "
                    "Please delete it and try again.".format(self.path)
                )
        else:
            tools.makedirs(self.path)
            vcs = get_version_control_system(self.repo)
            if vcs == MERCURIAL:
                retcode = tools.run_command(
                    ["hg", "archive", "-r", self.global_rev]
                    + [f"-X{d}" for d in self.exclude]
                    + [self.path],
                    cwd=self.repo,
                )
            elif vcs == GIT:
                tar_archive = os.path.join(self.path, "solver.tgz")
                cmd = ["git", "archive", "--format", "tar", self.global_rev]
                with open(tar_archive, "w") as f:
                    retcode = tools.run_command(cmd, stdout=f, cwd=self.repo)

                if retcode == 0:
                    with tarfile.open(tar_archive) as tf:
                        tf.extractall(self.path)
                    tools.remove_path(tar_archive)

                    for exclude_dir in self.exclude:
                        path = os.path.join(self.path, exclude_dir)
                        if os.path.exists(path):
                            tools.remove_path(path)
            else:
                _raise_unknown_vcs_error(vcs)

            if retcode != 0:
                shutil.rmtree(self.path)
                logging.critical("Failed to make checkout.")
            self._compile()
            self._cleanup()

    def _get_sentinel_file(self):
        return os.path.join(self.path, "build_successful")

    def _compile(self):
        retcode = tools.run_command(self.build_cmd, cwd=self.path)
        if retcode == 0:
            tools.write_file(self._get_sentinel_file(), "")
        else:
            logging.critical(f"Build failed in {self.path}")

    def _cleanup(self):
        pass
