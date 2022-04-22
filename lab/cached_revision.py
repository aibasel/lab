import functools
import hashlib
import logging
import os.path
import shutil
import subprocess
import tarfile

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
          and running the solver. Instead of this parameter, you can also
          use a ``.gitattributes`` file for Git repositories.

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
        ...     cr = CachedRevision(repo, rev, ["./build.py"], exclude=["experiments"])
        ...     # cr.cache(revision_cache)  # Uncomment to actually cache the code.
        ...

        You can now copy the cached repo to your experiment:

        ...     from lab.experiment import Experiment
        ...     exp = Experiment()
        ...     cache_path = os.path.join(revision_cache, cr.name)
        ...     dest_path = os.path.join(exp.path, "code-" + cr.name)
        ...     exp.add_resource("solver_" +  cr.name, cache_path, dest_path)

        """
        if not os.path.isdir(repo):
            logging.critical(f"{repo} is not a local solver repository.")
        self.repo = repo
        self.build_cmd = build_cmd
        self.local_rev = rev
        self.global_rev = get_global_rev(repo, rev)
        self.path = None
        self.exclude = exclude or []
        self.name = self._compute_hashed_name()

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def _compute_hashed_name(self):
        return f"{self.global_rev}_{_compute_md5_hash(self.build_cmd + self.exclude)}"

    def cache(self, revision_cache):
        self.path = os.path.join(revision_cache, self.name)
        if os.path.exists(self.path):
            logging.info(f'Revision is already cached: "{self.path}"')
            if not os.path.exists(self._get_sentinel_file()):
                logging.critical(
                    f"The build for the cached revision at {self.path} is corrupted. "
                    f"Please delete it and try again."
                )
        else:
            tools.makedirs(self.path)
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
