"""Store an experiment directory in a single uncompressed tar file.

An experiment created with ``Experiment(archive=True)`` lives in the file
``<path>.tar`` instead of the directory ``<path>``. Each member name is
the path of the file relative to the experiment directory.

The archive is append-only: runs and parsers append the files they create
or change, and a later member overrides an earlier member with the same
name. Writers hold an exclusive ``flock`` on the archive and readers a
shared one, so runs on different cluster nodes can share the archive.

The archive always ends with exactly two zero blocks. Appending therefore
starts at a known offset and never scans the archive.
"""

import collections
import contextlib
import fcntl
import io
import logging
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

from lab import tools

END_OF_ARCHIVE = tarfile.NUL * (2 * tarfile.BLOCKSIZE)

# Matches members inside run directories and captures the run directory.
_RUN_MEMBER = re.compile(r"(runs-\d+-\d+/[^/]+)(/|$)")


def get_archive_path(exp_path):
    return f"{os.fspath(exp_path).rstrip('/')}.tar"


def get_run_dir_of_member(name):
    """Return the run directory containing member *name*, or None."""
    match = _RUN_MEMBER.match(name)
    return match.group(1) if match else None


class ExperimentArchive:
    def __init__(self, path):
        self.path = Path(path)

    def create(self):
        """Create an empty archive."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "xb") as f:
            f.write(END_OF_ARCHIVE)

    @contextlib.contextmanager
    def reader(self):
        """Yield a TarFile for reading while holding a shared lock."""
        with open(self.path, "rb") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            with tarfile.open(fileobj=f, mode="r:") as tar:
                yield tar

    @contextlib.contextmanager
    def writer(self, dereference=False):
        """Yield a TarFile that appends members while holding an exclusive lock.

        If the block raises an exception, the archive is restored to its
        previous state.
        """
        with open(self.path, "r+b") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            start = f.seek(-len(END_OF_ARCHIVE), os.SEEK_END)
            tar = tarfile.TarFile(fileobj=f, mode="w", dereference=dereference)
            try:
                yield tar
            except BaseException:
                f.seek(start)
                f.write(END_OF_ARCHIVE)
                f.truncate()
                raise
            # TarFile.close() would pad the archive to a full record, so we
            # write the end-of-archive marker ourselves.
            f.seek(tar.offset)
            f.write(END_OF_ARCHIVE)
            f.truncate()

    def members(self):
        """Return a dict from member names to their latest TarInfo."""
        with self.reader() as tar:
            return {member.name: member for member in tar}

    @staticmethod
    def group_by_run_dir(members):
        """Map each run directory to its members. Key None holds the others."""
        groups = collections.defaultdict(list)
        for name, member in members.items():
            groups[get_run_dir_of_member(name)].append(member)
        return groups

    def extract(self, members, dest):
        with self.reader() as tar:
            for member in members:
                # We trust the archive since lab wrote it.
                tar.extract(member, dest, filter="fully_trusted")

    def append(self, root, names):
        """Append the files *names* (relative to *root*) to the archive."""
        with self.writer() as tar:
            for name in names:
                tar.add(Path(root) / name, arcname=name, recursive=False)


class ArchiveBuilder:
    """Write the files of an experiment into its archive during the build step."""

    def __init__(self, tar, exp_path):
        self.tar = tar
        self.exp_path = exp_path
        self.dirs = {"."}

    def _name(self, path):
        return os.path.relpath(path, self.exp_path)

    def _info(self, path, type, mode):
        info = tarfile.TarInfo(self._name(path))
        info.type = type
        info.mode = mode
        info.mtime = int(time.time())
        return info

    def makedirs(self, path):
        if self._name(path) not in self.dirs:
            self.dirs.add(self._name(path))
            self.tar.addfile(self._info(path, tarfile.DIRTYPE, 0o755))

    def write_file(self, path, content, permissions=None):
        data = content.encode()
        info = self._info(path, tarfile.REGTYPE, permissions or 0o644)
        info.size = len(data)
        self.tar.addfile(info, io.BytesIO(data))

    def copy(self, source, path):
        self.tar.add(source, arcname=self._name(path))

    def symlink(self, source, path, start):
        # Runs are executed in temporary directories, so relative links to
        # files outside of the experiment would break.
        info = self._info(path, tarfile.SYMTYPE, 0o777)
        info.linkname = os.path.abspath(source)
        self.tar.addfile(info)


def _changed_files(exp_dir, run_dir, members):
    """Return the files in *run_dir* that are new or differ from the archive."""
    changed = []
    for root, _, files in os.walk(exp_dir / run_dir):
        for filename in files:
            path = Path(root) / filename
            name = str(path.relative_to(exp_dir))
            member = members.get(name)
            stat = path.lstat()
            if (
                member is None
                or (member.isfile() and member.size != stat.st_size)
                or (member.isfile() and int(member.mtime) != int(stat.st_mtime))
                or (member.issym() and member.linkname != os.readlink(path))
            ):
                changed.append(name)
    return sorted(changed)


def _execute_run(archive, members, run_members, exp_dir, run_dir):
    """Execute a run in *exp_dir* and append its new files to the archive.

    Return True iff the run wrote to driver.err.
    """
    if f"{run_dir}/driver.log" in members:
        logging.info(f"The run in {run_dir} has already been started --> skip it")
        return False

    archive.extract(run_members, exp_dir)
    path = exp_dir / run_dir
    with (
        open(path / "driver.log", "w") as driver_log,
        open(path / "driver.err", "w") as driver_err,
    ):
        retcode = subprocess.call(
            [tools.get_python_executable(), "run"],
            cwd=path,
            stdout=driver_log,
            stderr=driver_err,
        )
        if retcode != 0:
            driver_err.write(f"The run script finished with exit code {retcode}\n")

    # driver.log always has content for a started run, so we never delete it.
    driver_err_path = path / "driver.err"
    failed = driver_err_path.stat().st_size > 0
    if not failed:
        driver_err_path.unlink()

    archive.append(exp_dir, _changed_files(exp_dir, run_dir, members))
    shutil.rmtree(path)
    return failed


def execute_runs(archive_path, run_dirs):
    """Execute the given runs of an archived experiment one after another.

    The experiment files outside of run directories are extracted once
    into a temporary directory, each run directory right before its run.
    Return True iff at least one run wrote to driver.err.
    """
    archive = ExperimentArchive(archive_path)
    members = archive.members()
    groups = archive.group_by_run_dir(members)
    failed = False
    with tempfile.TemporaryDirectory(prefix="lab-") as scratch:
        exp_dir = Path(scratch)
        archive.extract(groups[None], exp_dir)
        for run_dir in run_dirs:
            logging.info(f"Starting run in {run_dir}")
            failed |= _execute_run(archive, members, groups[run_dir], exp_dir, run_dir)
    return failed


def main():
    """Execute runs of an archived experiment: ARCHIVE RUN_ID [RUN_ID ...]"""
    from lab.experiment import get_run_dir

    tools.configure_logging()
    archive_path, *run_ids = sys.argv[1:]
    execute_runs(archive_path, [get_run_dir(int(run_id)) for run_id in run_ids])


if __name__ == "__main__":
    main()
