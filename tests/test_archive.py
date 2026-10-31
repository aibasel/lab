"""Test that archived experiments produce the same results as directory ones."""

import json
import sys
import tarfile

import pytest

from lab.archive import ExperimentArchive
from lab.environments import LocalEnvironment
from lab.experiment import Experiment
from lab.fetcher import Fetcher
from lab.parser import Parser


def _run_experiment(path, input_file, archive):
    exp = Experiment(path, environment=LocalEnvironment(processes=2), archive=archive)
    exp.add_resource("script", input_file.parent / "script.py", "script.py")
    parser = Parser()
    parser.add_pattern("square", r"square: (\d+)", type=int)
    exp.add_parser(parser)
    for number in range(1, 6):
        run = exp.add_run()
        run.add_resource("input", input_file, "input.txt", symlink=True)
        run.add_command("square", [sys.executable, "{script}", str(number), "{input}"])
        run.set_property("id", [f"run-{number}"])
    exp.build()
    exp.start_runs()
    exp.parse()
    exp.parse()  # Parsing twice must not change the results.
    Fetcher()(exp._data_path, merge=False)
    with open(exp.eval_dir + "/properties") as f:
        return json.load(f)


@pytest.fixture
def inputs(tmp_path):
    (tmp_path / "script.py").write_text(
        "import sys\n"
        "number = int(sys.argv[1])\n"
        "# Run 3 writes to stderr, which the fetcher reports as an error.\n"
        "stream = sys.stderr if number == 3 else sys.stdout\n"
        "print(open(sys.argv[2]).read().strip(), file=stream)\n"
        "print(f'square: {number * number}')\n"
    )
    input_file = tmp_path / "input.txt"
    input_file.write_text("input")
    return input_file


def test_archived_experiment_matches_directory_experiment(tmp_path, inputs):
    dir_props = _run_experiment(tmp_path / "dir-exp", inputs, archive=False)
    archive_props = _run_experiment(tmp_path / "archive-exp", inputs, archive=True)

    assert not (tmp_path / "archive-exp").exists()
    assert (tmp_path / "archive-exp.tar").is_file()
    assert (tmp_path / "archive-exp-eval" / "properties").is_file()
    assert dir_props == archive_props
    assert [archive_props[f"run-{n}"]["square"] for n in range(1, 6)] == [
        1,
        4,
        9,
        16,
        25,
    ]
    assert "unexplained_errors" in archive_props["run-3"]


def test_archive_ends_with_end_of_archive_marker(tmp_path, inputs):
    _run_experiment(tmp_path / "exp", inputs, archive=True)
    archive = tmp_path / "exp.tar"
    data = archive.read_bytes()
    assert data.endswith(tarfile.NUL * 2 * tarfile.BLOCKSIZE)
    assert not data[: -2 * tarfile.BLOCKSIZE].endswith(tarfile.NUL * tarfile.BLOCKSIZE)
    with tarfile.open(archive) as tar:
        assert "runs-00001-00100/00001/driver.log" in tar.getnames()


def test_failed_append_leaves_archive_unchanged(tmp_path):
    archive = ExperimentArchive(tmp_path / "exp.tar")
    archive.create()
    (tmp_path / "file").write_text("content")
    archive.append(tmp_path, ["file"])
    before = archive.path.read_bytes()
    with pytest.raises(FileNotFoundError):
        archive.append(tmp_path, ["file", "missing"])
    assert archive.path.read_bytes() == before
    assert list(archive.members()) == ["file"]
