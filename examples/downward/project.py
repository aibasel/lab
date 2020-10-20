from collections import namedtuple
import getpass
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from lab.environments import BaselSlurmEnvironment, LocalEnvironment
from lab.experiment import ARGPARSER
from lab.reports import Attribute, geometric_mean
from lab import tools


from downward.experiment import FastDownwardExperiment
from downward.reports.absolute import AbsoluteReport
from downward.reports.scatter import ScatterPlotReport


DIR = Path(__file__).resolve().parent
NODE = platform.node()
REMOTE = NODE.endswith(".scicore.unibas.ch") or NODE.endswith(".cluster.bc2.ch")

User = namedtuple("User", ["scp_login", "remote_repos"])
USERS = {
    "jendrik": User(
        scp_login="seipp@login.scicore.unibas.ch",
        remote_repos="/infai/seipp/projects",
    ),
}
USER = USERS[getpass.getuser()]


def parse_args():
    ARGPARSER.add_argument("--tex", action="store_true", help="produce LaTeX output")
    ARGPARSER.add_argument(
        "--relative", action="store_true", help="make relative scatter plots")
    return ARGPARSER.parse_args()


ARGS = parse_args()
TEX = ARGS.tex
RELATIVE = ARGS.relative

EVALUATIONS_PER_TIME = Attribute(
    "evaluations_per_time", min_wins=False, function=geometric_mean, digits=1)

# Generated with "./suites.py satisficing" in aibasel/downward-benchmarks repo.
SUITE_SATISFICING = [
    "agricola-sat18-strips", "airport", "assembly", "barman-sat11-strips",
    "barman-sat14-strips", "blocks", "caldera-sat18-adl",
    "caldera-split-sat18-adl", "cavediving-14-adl", "childsnack-sat14-strips",
    "citycar-sat14-adl", "data-network-sat18-strips", "depot", "driverlog",
    "elevators-sat08-strips", "elevators-sat11-strips", "flashfill-sat18-adl",
    "floortile-sat11-strips", "floortile-sat14-strips", "freecell",
    "ged-sat14-strips", "grid", "gripper", "hiking-sat14-strips",
    "logistics00", "logistics98", "maintenance-sat14-adl", "miconic",
    "miconic-fulladl", "miconic-simpleadl", "movie", "mprime", "mystery",
    "nomystery-sat11-strips", "nurikabe-sat18-adl", "openstacks",
    "openstacks-sat08-adl", "openstacks-sat08-strips",
    "openstacks-sat11-strips", "openstacks-sat14-strips", "openstacks-strips",
    "optical-telegraphs", "organic-synthesis-sat18-strips",
    "organic-synthesis-split-sat18-strips", "parcprinter-08-strips",
    "parcprinter-sat11-strips", "parking-sat11-strips", "parking-sat14-strips",
    "pathways", "pegsol-08-strips", "pegsol-sat11-strips", "philosophers",
    "pipesworld-notankage", "pipesworld-tankage", "psr-large", "psr-middle",
    "psr-small", "rovers", "satellite", "scanalyzer-08-strips",
    "scanalyzer-sat11-strips", "schedule", "settlers-sat18-adl",
    "snake-sat18-strips", "sokoban-sat08-strips", "sokoban-sat11-strips",
    "spider-sat18-strips", "storage", "termes-sat18-strips",
    "tetris-sat14-strips", "thoughtful-sat14-strips", "tidybot-sat11-strips",
    "tpp", "transport-sat08-strips", "transport-sat11-strips",
    "transport-sat14-strips", "trucks", "trucks-strips",
    "visitall-sat11-strips", "visitall-sat14-strips",
    "woodworking-sat08-strips", "woodworking-sat11-strips", "zenotravel",
]


def get_repo_base() -> Path:
    """Get base directory of the repository, as an absolute path.

    Search upwards in the directory tree from the main script until a
    directory with a subdirectory named ".git" or ".hg" is found.

    Abort if the repo base cannot be found."""
    path = Path(tools.get_script_path())
    while path.parent != path:
        if any((path / d).is_dir() for d in [".git", ".hg"]):
            return path
        path = path.parent
    sys.exit("repo base could not be found")


def remove_file(path : Path):
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def add_evaluations_per_time(run):
    evaluations = run.get("evaluations")
    time = run.get("search_time")
    if evaluations is not None and evaluations >= 100 and time:
        run["evaluations_per_time"] = evaluations / time
    return run


def _get_exp_dir_relative_to_repos_dir():
    repo_name = get_repo_base().name
    script = Path(tools.get_script_path())
    project = script.parent.name
    expname = script.stem
    return Path(repo_name) / "experiments" / project / "data" / expname


def add_scp_step(exp):
    remote_exp = Path(USER.remote_repos) / _get_exp_dir_relative_to_repos_dir()
    exp.add_step("scp-eval-dir", subprocess.call, [
        "scp",
        "-r",  # Copy recursively.
        "-C",  # Compress files.
        f"{USER.scp_login}:{remote_exp}-eval",
        f"{exp.path}-eval"])


def fetch_algorithm(exp, expname, algo, *, new_algo=None):
    """Fetch (and possibly rename) a single algorithm."""
    new_algo = new_algo or algo

    def rename_and_filter(run):
        if run["algorithm"] == algo:
            run["algorithm"] = new_algo
            run["id"][0] = run["id"][0].replace(algo, new_algo)
            return run
        return False

    exp.add_fetcher(
        f"data/{expname}-eval",
        filter=rename_and_filter,
        name=f"fetch-{new_algo}-from-{expname}",
        merge=True,
    )


def fetch_algorithms(exp, expname, *, algos=None, name=None, filters=None):
    """Fetch multiple or all algorithms."""
    algos = set(algos or [])
    filters = filters or []
    if algos:
        def algo_filter(run):
            return run["algorithm"] in algos
        filters.append(algo_filter)

    exp.add_fetcher(
        f"data/{expname}-eval",
        filter=filters,
        name=name or f"fetch-from-{expname}",
        merge=True,
    )


def add_absolute_report(exp, *, name=None, outfile=None, **kwargs):
    report = AbsoluteReport(**kwargs)
    if name and not outfile:
        outfile = f"{name}.{report.output_format}"
    elif outfile and not name:
        name = Path(outfile).name
    elif not name and not outfile:
        name = f"{exp.name}-abs"
        outfile = f"{name}.{report.output_format}"

    if not Path(outfile).is_absolute():
        outfile = Path(exp.eval_dir) / outfile

    exp.add_report(report, name=name, outfile=outfile)
    if not REMOTE:
        exp.add_step(f"open-{name}", subprocess.call, ["xdg-open", outfile])
    exp.add_step(f"publish-{name}", subprocess.call, ["publish", outfile])


class CommonExperiment(FastDownwardExperiment):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.add_step("build", self.build)
        self.add_step("start", self.start_runs)
        self.add_fetcher(name="fetch")

        if not REMOTE:
            self.add_step("remove-eval-dir", shutil.rmtree, self.eval_dir, ignore_errors=True)
            add_scp_step(self)

        self.add_parser(self.EXITCODE_PARSER)
        self.add_parser(self.TRANSLATOR_PARSER)
        self.add_parser(self.SINGLE_SEARCH_PARSER)
        self.add_parser(self.PLANNER_PARSER)
        self.add_parser(DIR / "parser.py")

    def _add_runs(self):
        """
        Example showing how to modify the automatically generated runs.

        This uses private members, so it might break between different
        versions of Lab.

        """
        FastDownwardExperiment._add_runs(self)
        for run in self.runs:
            command = run.commands["planner"]
            # Slightly raise soft limit for output to stdout.
            command[1]["soft_stdout_limit"] = 1.5 * 1024
