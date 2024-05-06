import functools
import hashlib
import logging
import os.path
import shutil
import subprocess
import tarfile
from pathlib import Path

from lab import tools


@functools.lru_cache(maxsize=None)
def _get_id(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE)
    try:
        p.check_returncode()
    except subprocess.CalledProcessError as err:
        logging.critical(f"{err} Please check path and revision.")
    else:
        return tools.get_string(p.stdout).strip()


def git_id(repo, args=None, rev=None):
    args = args or []
    if rev:
        args.append(rev)
    cmd = [
        "git",
        "--git-dir",
        os.path.join(repo, ".git"),
        "rev-parse",
    ] + args
    return _get_id(tuple(cmd))


def get_global_rev(repo, rev=None):
    return git_id(repo, rev=rev)


def _compute_md5_hash(mylist):
    m = hashlib.md5()
    for s in mylist:
        m.update(tools.get_bytes(s))
    return m.hexdigest()[:8]


class CachedRevision:
    """Cache compiled revisions of a solver for quick reuse."""

    def __init__(self, revision_cache, repo, rev, build_cmd, exclude=None, subdir=""):
        """
        * *revision_cache*: path to revision cache directory.
        * *repo*: path to solver repository.
        * *rev*: solver revision.
        * *build_cmd*: list with build script and any build options
          (e.g., ``["./build.py", "release"]``, ``["make"]``). Will be executed under
          *subdir*.
        * *exclude*: list of relative paths under *subdir* that are not needed for
          building and running the solver. Instead of this parameter, you can also
          use a ``.gitattributes`` file for Git repositories.
        * *subdir*: relative path from *repo* to solver subdir.

        The following example caches a Fast Downward revision. When you
        use the :class:`FastDownwardExperiment
        <downward.experiment.FastDownwardExperiment>` class, you don't
        need to cache revisions yourself since the class will do it
        transparently for you.

        >>> import os
        >>> repo = os.environ["DOWNWARD_REPO"]
        >>> revision_cache = os.environ.get("DOWNWARD_REVISION_CACHE")
        >>> if revision_cache:
        ...     rev = "main"
        ...     cr = CachedRevision(
        ...         revision_cache, repo, rev, ["./build.py"], exclude=["experiments"]
        ...     )
        ...     # cr.cache()  # Uncomment to actually cache the code.
        ...

        You can now copy the cached repo to your experiment::

        ...     from lab.experiment import Experiment
        ...     exp = Experiment()
        ...     dest_path = os.path.join(exp.path, f"code-{cr.name}")
        ...     exp.add_resource(f"solver_{cr.name}", cr.path, dest_path)

        """
        if not os.path.isdir(repo):
            logging.critical(f"{repo} is not a local solver repository.")
        self.revision_cache = Path(revision_cache)
        self.repo = repo
        self.subdir = subdir
        self.build_cmd = build_cmd
        self.local_rev = rev
        self.global_rev = get_global_rev(repo, rev)
        self.exclude = exclude or []
        self.name = self._compute_hashed_name()
        self.path = self.revision_cache / self.name
        # Temporary directory for preparing the checkout.
        self._tmp_path = self.revision_cache / f"{self.name}-tmp"

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def _compute_hashed_name(self):
        options_hash = _compute_md5_hash(self.build_cmd + self.exclude + [self.subdir])
        return f"{self.global_rev}_{options_hash}"

    def cache(self):
        """Check out the solver revision to *self.path* and compile the solver."""
        if os.path.exists(self.path):
            logging.info(f'Revision is already cached: "{self.path}"')
            if not os.path.exists(self._get_sentinel_file()):
                logging.critical(
                    f"The build for the cached revision at {self.path} is corrupted. "
                    f"Please delete it and try again."
                )
        else:
            tools.remove_path(self._tmp_path)
            tools.makedirs(self._tmp_path)
            tar_archive = os.path.join(self._tmp_path, "solver.tgz")
            cmd = ["git", "archive", "--format", "tar", self.global_rev]
            with open(tar_archive, "w") as f:
                retcode = tools.run_command(cmd, stdout=f, cwd=self.repo)

            if retcode != 0:
                logging.critical("Failed to make checkout.")

            # Extract only the subdir.
            with tarfile.open(tar_archive) as tf:

                def members():
                    for tarinfo in tf.getmembers():
                        if tarinfo.name.startswith(self.subdir):
                            yield tarinfo

                tf.extractall(self._tmp_path, members=members())
            shutil.move(self._tmp_path / self.subdir, self.path)
            tools.remove_path(tar_archive)

            for exclude_path in self.exclude:
                path = self.path / exclude_path
                if path.exists():
                    tools.remove_path(path)

            retcode = tools.run_command(self.build_cmd, cwd=self.path)
            if retcode == 0:
                tools.write_file(self._get_sentinel_file(), "")
            else:
                logging.critical(f"Build failed in {self.path}")

            self._cleanup()

    def _get_sentinel_file(self):
        return os.path.join(self.path, "build_successful")

    def _cleanup(self):
        pass

    def get_relative_exp_path(self, relpath=""):
        """Return a path relative to the experiment directory.

        Use this function to find out where files from the cache will be put in
        the experiment directory.

        """
        return os.path.join(f"code-{self.name}", relpath)
