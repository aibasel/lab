"""
Module that permits generating planner reports by reading properties files.
"""

from collections import defaultdict
from fnmatch import fnmatch
import logging

from lab import reports, tools
from lab.reports import Attribute, geometric_mean, markup, Report


class PlanningReport(Report):
    """Base class for planner reports."""

    #: List of predefined :py:class:`~Attribute` instances. For example, if
    #: PlanningReport receives ``attributes=['coverage']``, it converts
    #: the plain string ``'coverage'`` to the attribute instance
    #: ``Attribute('coverage', absolute=True, min_wins=False, scale='linear')``.
    PREDEFINED_ATTRIBUTES = [
        Attribute("cost", scale="linear"),
        Attribute("coverage", absolute=True, min_wins=False, scale="linear"),
        Attribute("dead_ends", min_wins=False),
        Attribute("evaluations", function=geometric_mean),
        Attribute("expansions", function=geometric_mean),
        Attribute("generated", function=geometric_mean),
        Attribute(
            "initial_h_value",
            min_wins=False,
            scale="linear",
            function=reports.finite_sum,
        ),
        Attribute("plan_length", scale="linear"),
        Attribute("planner_time", function=geometric_mean),
        Attribute("quality", absolute=True, min_wins=False),
        Attribute("score_*", absolute=True, min_wins=False, digits=4),
        Attribute("search_time", function=geometric_mean),
        Attribute("total_time", function=geometric_mean),
        Attribute("unsolvable", absolute=True, min_wins=False),
    ]

    #: Attributes shown in the algorithm info table.
    INFO_ATTRIBUTES = [
        "local_revision",
        "global_revision",
        "build_options",
        "driver_options",
        "component_options",
    ]

    #: Attributes shown in the unexplained-errors table.
    ERROR_ATTRIBUTES = [
        "algorithm",
        "domain",
        "problem",
        "unexplained_errors",
        "error",
        "planner_wall_clock_time",
        "raw_memory",
        "node",
    ]

    ERROR_LOG_MAX_LINES = 100

    def __init__(self, **kwargs):
        """
        See :class:`~lab.reports.Report` for inherited parameters.

        You can filter and modify runs for a report with
        :py:class:`filters <.Report>`. For example, you can include only
        a subset of algorithms or compute new attributes. If you provide
        a list for *filter_algorithm*, it will be used to determine the
        order of algorithms in the report.

        >>> # Use a filter function to select algorithms.
        >>> def only_blind_and_lmcut(run):
        ...     return run["algorithm"] in ["blind", "lmcut"]
        ...
        >>> report = PlanningReport(filter=only_blind_and_lmcut)

        >>> # Use "filter_algorithm" to select and *order* algorithms.
        >>> report = PlanningReport(filter_algorithm=["lmcut", "blind"])

        :py:class:`Filters <.Report>` can be very helpful so we
        recommend reading up on them to use their full potential.

        Subclasses can use the member variable ``problem_runs`` to access the
        experiment data. It is a dictionary mapping from tasks (i.e.,
        ``(domain, problem)`` pairs) to the runs for that task. Each run is a
        dictionary that maps from attribute names to values.

        >>> class MinRuntimePerTask(PlanningReport):
        ...     def get_text(self):
        ...         map = {}
        ...         for (domain, problem), runs in self.problem_runs.items():
        ...             times = [run.get("planner_time") for run in runs]
        ...             times = [t for t in times if t is not None]
        ...             map[(domain, problem)] = min(times) if times else None
        ...         return str(map)
        ...

        """
        # Set non-default options for some attributes.
        attributes = tools.make_list(kwargs.get("attributes"))
        kwargs["attributes"] = [self._prepare_attribute(attr) for attr in attributes]

        # Remember the order of algorithms if it is given as a keyword argument filter.
        self.filter_algorithm = tools.make_list(kwargs.get("filter_algorithm"))

        Report.__init__(self, **kwargs)

    def _prepare_attribute(self, attr):
        predefined = {str(attr): attr for attr in self.PREDEFINED_ATTRIBUTES}
        if not isinstance(attr, Attribute):
            if attr in predefined:
                return predefined[attr]
            for pattern in predefined.values():
                if fnmatch(attr, pattern):
                    return pattern.copy(attr)
        return Report._prepare_attribute(self, attr)

    def _scan_data(self):
        self._scan_planning_data()
        Report._scan_data(self)

    def _scan_planning_data(self):
        problems = set()
        self.domains = defaultdict(list)
        self.problem_runs = defaultdict(list)
        self.domain_algorithm_runs = defaultdict(list)
        self.runs = {}
        for run in self.props.values():
            domain, problem, algo = run["domain"], run["problem"], run["algorithm"]
            problems.add((domain, problem))
            self.problem_runs[(domain, problem)].append(run)
            self.domain_algorithm_runs[(domain, algo)].append(run)
            self.runs[(domain, problem, algo)] = run
        for domain, problem in problems:
            self.domains[domain].append(problem)

        self.algorithms = self._get_algorithm_order()

        num_unexplained_errors = sum(
            int(tools.has_unexplained_error(run)) for run in self.runs.values()
        )
        func = logging.info if num_unexplained_errors == 0 else logging.warning
        func(
            f"Report contains {num_unexplained_errors} runs with unexplained"
            f" errors."
        )

        if len(problems) * len(self.algorithms) != len(self.runs):
            logging.warning(
                f"Not every algorithm has been run on every task. "
                f"However, if you applied a filter this is to be "
                f"expected. If not, there might be old properties in the "
                f"eval-dir that got included in the report. "
                f"Algorithms ({len(self.algorithms)}): {self.algorithms}, "
                f"problems ({len(problems)}), "
                f"domains ({len(self.domains)}): {list(self.domains.keys())}, "
                f"runs ({len(self.runs)})"
            )

        # Sort each entry in problem_runs by algorithm.
        algo_to_index = {
            algorithm: index for index, algorithm in enumerate(self.algorithms)
        }

        def run_key(run):
            return algo_to_index[run["algorithm"]]

        for problem_runs in self.problem_runs.values():
            problem_runs.sort(key=run_key)

        self.algorithm_info = self._scan_algorithm_info()

    def _scan_algorithm_info(self):
        info = {}
        for runs in self.problem_runs.values():
            for run in runs:
                info[run["algorithm"]] = {
                    attr: run.get(attr, "?") for attr in self.INFO_ATTRIBUTES
                }
            # We only need to scan the algorithms for one task.
            break
        return info

    def _get_node_names(self):
        return {
            run.get("node", "<attribute 'node' missing>") for run in self.runs.values()
        }

    def _format_unexplained_errors(self, errors):
        """
        Preserve line breaks and white space. If text has more than
        ERROR_LOG_MAX_LINES lines, omit lines in the middle of the text.
        """
        linebreak = "\\\\"
        text = (
            str(errors).replace("\\n", linebreak).replace(" ", markup.ESCAPE_WHITESPACE)
        )
        lines = text.split(linebreak)
        if len(lines) <= self.ERROR_LOG_MAX_LINES:
            return text
        index = (self.ERROR_LOG_MAX_LINES - 2) // 2
        text = linebreak.join(lines[:index] + ["", "[...]", ""] + lines[-index:])
        return text

    def _get_warnings_text_and_table(self):
        errors = []

        wrote_to_slurm_err = any(
            "output-to-slurm.err" in run.get("unexplained_errors", [])
            for run in self.runs.values()
        )
        if wrote_to_slurm_err:
            src_dir = self.eval_dir.rstrip("/")[: -len("-eval")]
            slurm_err_file = src_dir + "-grid-steps/slurm.err"
            try:
                slurm_err_content = tools.get_slurm_err_content(src_dir)
            except FileNotFoundError:
                slurm_err_file = "*-grid-steps/slurm.err"
                errors.append(
                    f"There was output to {slurm_err_file}, but the file was missing "
                    f"when this report was made."
                )
            else:
                slurm_err_content = tools.filter_slurm_err_content(slurm_err_content)
                errors.append(
                    f"There was output to {slurm_err_file}:\n"
                    f"```\n{slurm_err_content}\n```"
                )
            logging.warning(f"There was output to {slurm_err_file}.")

        unique_error_messages = defaultdict(list)
        for run in self.runs.values():
            if tools.has_unexplained_error(run):
                msg = self._format_unexplained_errors(
                    run.get("unexplained_errors", "?")
                )
                unique_error_messages[msg].append(run)
        if unique_error_messages:
            logging.info(f"Unique unexplained errors: {len(unique_error_messages)}")

        if self.output_format == "html":
            error_atributes = [
                attr for attr in self.ERROR_ATTRIBUTES if attr != "unexplained_errors"
            ]
            if "run_dir" not in self.ERROR_ATTRIBUTES:
                error_atributes.append("run_dir")

            def get_row(run):
                return " ".join(
                    f"<td>{run.get(attr, '?')}</td>" for attr in error_atributes
                )

            table = [
                '<button type="button" class="toggle-table" '
                'onclick="toggle_table(this)">Show table</button><p></p>',
                '<table class="tableborder" style="display:none">',
                "<tr>",
                "<th>Unexplained errors</th> "
                + " ".join(f"<th>{attr}</th>" for attr in error_atributes),
                "</tr>",
            ]
            for msg, runs in sorted(
                unique_error_messages.items(), key=lambda x: len(x[0])
            ):
                runs.sort(
                    key=lambda run: (run["algorithm"], run["domain"], run["problem"])
                )
                table.append("<tr>")
                table.append(f'<td rowspan="{len(runs)}">{msg}</td>')
                table.append(get_row(runs[0]))
                table.append("</tr>")
                for run in runs[1:]:
                    table.append(f"<tr>{get_row(run)}</tr>")
            table.append("</table>")
            errors.append("\n'''\n" + "\n".join(table) + "\n'''")
        elif unique_error_messages:
            errors.append("There were unexplained errors. See HTML report for details.")

        return "\n".join(errors)

    def _get_algorithm_order(self):
        """
        Return a list of algorithms in the order determined by the user.

        If 'filter_algorithm' is given, algorithms are sorted in that
        order. Otherwise, they are sorted alphabetically.

        You can use the order of algorithms in your own custom report
        subclasses by accessing self.algorithms which is calculated in
        self._scan_planning_data.

        """
        all_algos = {run["algorithm"] for run in self.props.values()}
        if self.filter_algorithm:
            # Other filters may have changed the set of available algorithms by either
            # removing all runs for one algorithm or changing run['algorithm'] for a run.
            # Maintain the original order of algorithms and only keep algorithms that
            # still have runs after filtering. Then add all new algorithms
            # sorted naturally at the end.
            algo_order = [
                c for c in self.filter_algorithm if c in all_algos
            ] + tools.natural_sort(all_algos - set(self.filter_algorithm))
        else:
            algo_order = tools.natural_sort(all_algos)
        return algo_order
