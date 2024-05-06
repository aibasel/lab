import logging
import re
from collections import defaultdict

from downward import outcomes
from downward.reports import PlanningReport
from lab import reports


def _abbreviate_node_names(nodes):
    """
    ase05.cluster.bc2.ch -> ase05
    {ase10, ase11, ase12, ase13, ase14} -> {ase10, ..., ase14}
    """
    abbrev_nodes = []
    sequence_buffer = []

    def flush_buffer():
        if len(sequence_buffer) <= 2:
            abbrev_nodes.extend(sequence_buffer)
        else:
            abbrev_nodes.extend([sequence_buffer[0], "...", sequence_buffer[-1]])
        del sequence_buffer[:]

    for node in sorted(nodes):
        node = node.replace(".cluster.bc2.ch", "")
        match = re.match(r"ase(\d{2})", node)
        if match:
            infai_node_id = int(match.group(1))
            if sequence_buffer:
                if sequence_buffer[-1] == f"ase{infai_node_id - 1:02d}":
                    sequence_buffer.append(node)
                elif len(sequence_buffer) in [1, 2]:
                    flush_buffer()
                    sequence_buffer = [node]
                else:
                    flush_buffer()
                    sequence_buffer = [node]
            else:
                sequence_buffer.append(node)
        else:
            flush_buffer()
            abbrev_nodes.append(node)
    flush_buffer()
    return abbrev_nodes


class AbsoluteReport(PlanningReport):
    """
    Report absolute values for the selected attributes.

    This report should be part of all your Fast Downward experiments as
    it includes a table of unexplained errors, e.g. invalid solutions,
    segmentation faults, etc.

    >>> from downward.experiment import FastDownwardExperiment
    >>> exp = FastDownwardExperiment()
    >>> exp.add_report(AbsoluteReport(attributes=["expansions"]), outfile="report.html")

    Example output:

        +------------+--------+--------+
        | expansions | hFF    | hCEA   |
        +============+========+========+
        | gripper    | 118    | 72     |
        +------------+--------+--------+
        | zenotravel | 21     | 17     |
        +------------+--------+--------+

    """

    def __init__(self, **kwargs):
        PlanningReport.__init__(self, **kwargs)
        self.colored = "html" in self.output_format
        self.use_domain_links = "html" in self.output_format
        self.toc = False

    def get_markup(self):
        sections = []
        toc_lines = []

        warnings = self._get_warnings_text_and_table()
        if warnings:
            toc_lines.append("- **[" "Unexplained Errors" " #unexplained-errors]**")
            sections.append(("unexplained-errors", warnings))

        toc_lines.append("- **[Info #info]**")
        sections.append(("info", self._get_general_info()))

        # Index of summary section.
        summary_index = len(sections)

        # Build a table containing summary functions of all other tables.
        # The actual section is added at position summary_index after creating
        # all other tables.
        summary = self._get_empty_table(title="Summary")
        summary.colored = self.colored
        toc_lines.append("- **[Summary #summary]**")

        for attribute in self.attributes:
            logging.info(f"Creating table(s) for {attribute}")
            tables = []
            if attribute == "error":
                seen_errors = set()
                error_counter = defaultdict(int)

                for run in self.runs.values():
                    error = run.get("error", "attribute-error-missing")
                    seen_errors.add(error)
                    error_counter[(run["algorithm"], run["domain"], error)] += 1

                error_to_min_wins = {
                    outcome.msg: outcome.min_wins for outcome in outcomes.OUTCOMES
                }

                for error in sorted(seen_errors):
                    # Txt2tags seems to only allow letters, "-" and "_" in anchors.
                    pseudo_attribute = "error-" + error
                    table = self._get_empty_table(title=pseudo_attribute)
                    min_wins = error_to_min_wins.get(error)
                    table.min_wins = min_wins
                    table.colored = min_wins is not None
                    for domain in self.domains:
                        if self.use_domain_links:
                            table.cell_formatters[domain][table.header_column] = (
                                reports.CellFormatter(link=f"#error-{domain}")
                            )
                        for algorithm in self.algorithms:
                            count = error_counter.get((algorithm, domain, error), 0)
                            table.add_cell(domain, algorithm, count)
                    table.add_summary_function("Sum", sum)
                    reports.extract_summary_rows(
                        table, summary, link="#" + "error-" + pseudo_attribute
                    )
                    tables.append((pseudo_attribute, table))
            elif self.attribute_is_numeric(attribute):
                domain_table = self._get_suite_table(attribute)
                tables.append(("", domain_table))
                reports.extract_summary_rows(
                    domain_table, summary, link="#" + attribute
                )
            else:
                tables.append(
                    (
                        "",
                        f"Per-domain reports only support numeric "
                        f"attributes, but {attribute} has type "
                        f"{self._all_attributes[attribute].__name__}.",
                    )
                )
            for domain in sorted(self.domains.keys()):
                tables.append((domain, self._get_domain_table(attribute, domain)))

            parts = []
            toc_line = []
            for domain, table in tables:
                if domain:
                    assert table
                    toc_line.append(f"[''{domain}'' #{attribute}-{domain}]")
                    parts.append(f"=== {domain} ===[{attribute}-{domain}]\n{table}\n")
                else:
                    if table:
                        parts.append(f"{table}\n")
                    else:
                        parts.append(
                            f"No task was found where all algorithms "
                            f'have a value for "{attribute}". Therefore no '
                            f"per-domain table can be generated.\n"
                        )

            toc_lines.append(f"- **[''{attribute}'' #{attribute}]**")
            toc_lines.append("  - " + " ".join(toc_line))
            sections.append((attribute, "\n".join(parts)))

        # Add summary before main content. This is done after creating the main content
        # because the summary table is extracted from all other tables.
        sections.insert(summary_index, ("summary", summary))

        toc = "\n".join(toc_lines)

        content = "\n".join(
            f"== {attr} ==[{attr}]\n\n{section}" for (attr, section) in sections
        )
        return f"{toc}\n\n\n{content}"

    def _get_general_info(self):
        table = reports.Table(title="algorithm")
        for algo, info in self.algorithm_info.items():
            for attr in self.INFO_ATTRIBUTES:
                if info[attr]:
                    table.add_cell(algo, attr, info[attr])
        table.set_column_order(self.INFO_ATTRIBUTES)

        used_nodes = ", ".join(_abbreviate_node_names(self._get_node_names()))
        node_info = f"Used nodes: {{{used_nodes}}}"

        if table:
            return str(table) + "\n" + node_info
        else:
            logging.warning("Table containing algorithm information is empty.")
            return node_info

    def _get_aggregation_function(self, attribute):
        """Decide on a list of group functions for this attribute."""
        func = attribute.function
        return (reports.function_name(func), func)

    def _add_table_info(self, attribute, func_name, table):
        """
        Add some information to the table for attributes where data is missing.
        """
        if not attribute.absolute:
            table.info.append(
                f"Only tasks where all algorithms have a "
                f'value for "{attribute}" are considered.'
            )
            table.info.append(
                f'Each table entry gives the {func_name} of "{attribute}" for that '
                f"domain."
            )

        summary_names = [name.lower() for name, _ in table.summary_funcs.items()]
        if len(summary_names) == 1:
            table.info.append(
                f"The bottom row reports the {summary_names[0]} across all domains."
            )
        elif len(summary_names) > 1:
            names = " and ".join(summary_names)
            table.info.append(f"The bottom rows report the {names} across all domains.")

    def _get_suite_table(self, attribute):
        assert self.attribute_is_numeric(attribute), attribute
        table = self._get_empty_table(attribute)
        self._add_summary_functions(table, attribute)
        func_name, func = self._get_aggregation_function(attribute)
        num_probs = 0
        self._add_table_info(attribute, func_name, table)
        domain_algo_values = {}
        for domain in self.domains:
            for algorithm in self.algorithms:
                domain_algo_values[(domain, algorithm)] = []
        for (domain, _), runs in self.problem_runs.items():
            # If the attribute is absolute, no runs must have been filtered and
            # no values must be missing.
            if not attribute.absolute and (
                len(runs) < len(self.algorithms)
                or any(run.get(attribute) is None for run in runs)
            ):
                continue
            num_probs += 1
            for run in runs:
                value = run.get(attribute)
                if value is not None:
                    domain_algo_values[(domain, run["algorithm"])].append(value)

        # If the attribute is absolute (e.g. coverage) we may have
        # added problems for which not all algorithms have a value. Therefore, we
        # can only print the number of instances (in brackets after the domain
        # name) if that number is the same for all algorithms. If not all algorithms
        # have values for the same number of problems, we write the full list of
        # different problem numbers.
        for domain in self.domains:
            task_counts = [
                str(len(domain_algo_values[(domain, algo)])) for algo in self.algorithms
            ]
            if len(set(task_counts)) == 1:
                count = task_counts[0]
            else:
                count = ", ".join(task_counts)
            link = None
            if self.use_domain_links:
                link = f"#{attribute}-{domain}"
            formatter = reports.CellFormatter(link=link, count=count)
            table.cell_formatters[domain][table.header_column] = formatter

        for (domain, algo), values in domain_algo_values.items():
            domain_value = func(values) if values else None
            table.add_cell(domain, algo, domain_value)

        table.num_values = num_probs
        return table

    def _get_domain_table(self, attribute, domain):
        table = self._get_empty_table(attribute)

        for algo in self.algorithms:
            for run in self.domain_algorithm_runs[domain, algo]:
                table.add_cell(run["problem"], algo, run.get(attribute))
        return table

    def _get_empty_table(self, attribute=None, title=None, columns=None):
        """Return an empty table."""
        if title is None:
            assert attribute is not None
            title = attribute
            if self.output_format == "tex":
                title = title.capitalize().replace("_", " ")
        if columns is None:
            columns = self.algorithms

        if attribute is not None and self.attribute_is_numeric(attribute):
            # Decide whether we want to highlight minima or maxima.
            kwargs = {
                "min_wins": attribute.min_wins,
                "colored": self.colored and attribute.min_wins is not None,
                "digits": attribute.digits,
            }
        else:
            # Do not highlight anything.
            kwargs = {}
        table = reports.Table(title=title, **kwargs)
        table.set_column_order(columns)
        link = f"#{title}"
        formatter = reports.CellFormatter(link=link)
        table.cell_formatters[table.header_row][table.header_column] = formatter
        return table

    def _add_summary_functions(self, table, attribute):
        funcname, func = self._get_aggregation_function(attribute)
        table.add_summary_function(funcname.capitalize(), func)
