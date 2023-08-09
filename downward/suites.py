from pathlib import Path

from lab import tools


def find_domain_file(benchmarks_dir, domain: str, problem: str):
    """Search for domain file in the directory *benchmarks_dir*/*domain*.

    For a given problem filename "<taskname>.<ext>", check the following
    domain filenames: "domain.pddl", "<taskname>-domain.<ext>",
    "domain_<taskname>.<ext>" and "domain-<taskname>.<ext>", where
    ".<ext>" is optional. Also check "<xyz>-domain.pddl" where <xyz> are
    the first three characters of the task file name, to cover the airport
    and psr-small domains, where problem file names are p01-xxx.pddl and
    domain file names are p01-domain.pddl.
    """
    problem_root = Path(problem).stem
    ext = Path(problem).suffix
    domain_basenames = [
        "domain.pddl",
        problem_root + "-domain" + ext,
        problem_root[:3] + "-domain.pddl",  # for airport and psr-small
        "domain_" + problem,
        "domain-" + problem,
    ]
    domain_dir = Path(benchmarks_dir) / domain
    return tools.find_file(domain_basenames, domain_dir)


def get_task(benchmarks_dir, domain: str, problem: str):
    problem_file = Path(benchmarks_dir) / domain / problem
    domain_file = None
    if problem_file.suffix == ".pddl":
        domain_file = find_domain_file(benchmarks_dir, domain, problem)
    return Task(domain, problem, problem_file=problem_file, domain_file=domain_file)


class Domain:
    def __init__(self, benchmarks_dir, domain: str):
        self.domain = domain
        directory = Path(benchmarks_dir) / domain
        problem_files = tools.natural_sort(
            [
                p.name
                for p in directory.iterdir()
                if "domain" not in p.name and p.suffix in {".pddl", ".sas"}
            ]
        )
        self.problems = [
            get_task(benchmarks_dir, domain, problem) for problem in problem_files
        ]

    def __str__(self):
        return self.domain

    def __repr__(self):
        return f"<Domain {self.domain}>"

    def __hash__(self):
        return hash(self.domain)

    def __eq__(self, other):
        return self.domain == other.domain

    def __iter__(self):
        return iter(self.problems)


class Task:
    def __init__(
        self, domain: str, problem: str, problem_file, domain_file=None, properties=None
    ):
        """
        *domain* and *problem* are the display names of the domain and
        problem, *domain_file* and *problem_file* are paths to the
        respective files on the disk. If *domain_file* is not given,
        assume that *problem_file* is a SAS task.

        *properties* may be a dictionary of entries that should be
        added to the properties file of each run that uses this
        problem. ::

            >>> task = Task(
            ...     "gripper",
            ...     "p01.pddl",
            ...     problem_file="/path/to/prob01.pddl",
            ...     domain_file="/path/to/domain.pddl",
            ...     properties={"relaxed": False},
            ... )
        """
        self.domain = domain
        self.problem = problem
        self.problem_file = problem_file
        self.domain_file = domain_file

        self.properties = properties or {}
        self.properties.setdefault("domain", self.domain)
        self.properties.setdefault("problem", self.problem)

    def __str__(self):
        return (
            f"<Task {self.domain}({self.domain_file}):{self.problem}"
            f"({self.problem_file}) {self.properties}>"
        )


def _generate_problems(benchmarks_dir, description):
    """
    Descriptions are either domains (e.g., "gripper") or problems
    (e.g., "gripper:prob01.pddl").
    """
    if isinstance(description, Task):
        yield description
    elif isinstance(description, Domain):
        yield from description
    elif ":" in description:
        domain_name, problem_name = description.split(":", 1)
        yield get_task(benchmarks_dir, domain_name, problem_name)
    else:
        yield from Domain(benchmarks_dir, description)


def build_suite(benchmarks_dir, descriptions):
    """Compute a list of :class:`Task <downward.suites.Task>` objects.

    The path *benchmarks_dir* must contain a subdir for each domain.

    *descriptions* must be a list of domain or problem descriptions::

        build_suite(benchmarks_dir, ["gripper", "grid:prob01.pddl"])

    """
    result = []
    for description in descriptions:
        result.extend(_generate_problems(benchmarks_dir, description))
    return result
