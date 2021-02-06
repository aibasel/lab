import glob
import os.path
import subprocess

from lab import tools
from lab.cached_revision import CachedRevision


class CachedFastDownwardRevision(CachedRevision):
    """This class represents Fast Downward checkouts.

    It provides methods for caching and compiling given revisions.
    """

    def __init__(self, repo, rev, build_options):
        """
        * *repo*: Path to Fast Downward repository.
        * *rev*: Fast Downward revision.
        * *build_options*: List of build.py options.
        """
        CachedRevision.__init__(
            self, repo, rev, ["./build.py"] + build_options, ["experiments", "misc"]
        )
        self.build_options = build_options

    def _cleanup(self):
        # Only keep the bin directories in "builds" dir.
        for path in glob.glob(os.path.join(self.path, "builds", "*", "*")):
            if os.path.basename(path) != "bin":
                tools.remove_path(path)

        # Remove unneeded files.
        tools.remove_path(os.path.join(self.path, "build.py"))

        # Strip binaries.
        binaries = []
        for path in glob.glob(os.path.join(self.path, "builds", "*", "bin", "*")):
            if os.path.basename(path) in ["downward", "preprocess"]:
                binaries.append(path)
        subprocess.call(["strip"] + binaries)

        # Compress src directory.
        subprocess.call(
            ["tar", "-cf", "src.tar", "--remove-files", "src"], cwd=self.path
        )
        subprocess.call(["xz", "src.tar"], cwd=self.path)
