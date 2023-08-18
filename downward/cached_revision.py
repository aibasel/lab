import subprocess

from lab import tools
from lab.cached_revision import CachedRevision


class CachedFastDownwardRevision(CachedRevision):
    """This class represents Fast Downward checkouts.

    It provides methods for caching compiled revisions, so they can be reused
    quickly in different experiments.

    """

    def __init__(self, revision_cache, repo, rev, build_options, subdir=""):
        """
        * *revision_cache*: Path to revision cache.
        * *repo*: Path to Fast Downward repository.
        * *rev*: Fast Downward revision.
        * *build_options*: List of build.py options.
        * *subdir*: relative path from *repo* to Fast Downward subdir.
        """
        CachedRevision.__init__(
            self,
            revision_cache,
            repo,
            rev,
            ["./build.py"] + build_options,
            exclude=["experiments", "misc"],
            subdir=subdir,
        )
        # Store for easy retrieval by class users.
        self.build_options = build_options

    def _cleanup(self):
        # Only keep the bin directories in "builds" dir.
        for path in self.path.glob("builds/*/*"):
            if path.name != "bin":
                tools.remove_path(path)

        # Remove unneeded files.
        tools.remove_path(self.path / "build.py")

        # Strip binaries.
        binaries = []
        for path in self.path.glob("builds/*/bin/*"):
            if path.name in ["downward", "preprocess"]:
                binaries.append(path)
        subprocess.check_call(["strip"] + binaries)

        # Compress src directory.
        subprocess.check_call(
            ["tar", "--remove-files", "--xz", "-cf", "src.tar.xz", "src"], cwd=self.path
        )
