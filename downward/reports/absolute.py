# -*- coding: utf-8 -*-
#
# Downward Lab uses the Lab package to conduct experiments with the
# Fast Downward planning system.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from collections import defaultdict
import logging
import re

from lab import reports

from downward import outcomes
from downward.reports import PlanningReport


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
            abbrev_nodes.extend([sequence_buffer[0], '...', sequence_buffer[-1]])
        del sequence_buffer[:]

    for node in sorted(nodes):
        node = node.replace('.cluster.bc2.ch', '')
        match = re.match(r'ase(\d{2})', node)
        if match:
            infai_node_id = int(match.group(1))
            if sequence_buffer:
                if sequence_buffer[-1] == 'ase{:02d}'.format(infai_node_id - 1):
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
    >>> exp.add_report(
    ...     AbsoluteReport(attributes=["expansions"]),
    ...     outfile='report.html')

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
        self.colored = 'html' in self.output_format
        self.use_domain_links = 'html' in self.output_format
        self.toc = False

    def get_markup(self):
        sections = []
        toc_lines = []

        warnings = self._get_warnings_text_and_table()
        if warnings:
            toc_lines.append('- **[''Unexplained Errors'' #unexplained-errors]**')
            sections.append(('unexplained-errors', warnings))

        toc_lines.append('- **[Info #info]**')
        sections.append(('info', self._get_general_info()))

        # Index of summary section.
        summary_index = len(sections)

        # Build a table containing summary functions of all other tables.
        # The actual section is added at position summary_index after creating
        # all other tables.
        summary = self._get_empty_table(title='Summary')
        summary.colored = self.colored
        toc_lines.append('- **[Summary #summary]**')

        for attribute in self.attributes:
            logging.info('Creating table(s) for %s' % attribute)
            tables = []
            if attribute == 'error':
                seen_errors = set()
                error_counter = defaultdict(int)

                for run in self.runs.values():
                    error = run.get('error', 'attribute-error-missing')
                    seen_errors.add(error)
                    error_counter[(run["algorithm"], run["domain"], error)] += 1

                error_to_min_wins = dict(
                    (outcome.msg, outcome.min_wins) for outcome in outcomes.OUTCOMES)

                for error in sorted(seen_errors):
                    # Txt2tags seems to only allow letters, "-" and "_" in anchors.
                    pseudo_attribute = 'error-' + error
                    table = self._get_empty_table(title=pseudo_attribute)
                    min_wins = error_to_min_wins.get(error, None)
                    table.min_wins = min_wins
                    table.colored = min_wins is not None
                    for domain in self.domains:
                        if self.use_domain_links:
                            table.cell_formatters[domain][table.header_column] = (
                                reports.CellFormatter(
                                    link='#error-{domain}'.format(**locals())))
                        for algorithm in self.algorithms:
                            count = error_counter.get((algorithm, domain, error), 0)
                            table.add_cell(domain, algorithm, count)
                    table.add_summary_function('Sum', sum)
                    reports.extract_summary_rows(
                        table, summary, link='#' + 'error-' + pseudo_attribute)
                    tables.append((pseudo_attribute, table))
            elif self.attribute_is_numeric(attribute):
                domain_table = self._get_table(attribute)
                tables.append(('', domain_table))
                reports.extract_summary_rows(
                    domain_table, summary, link='#' + attribute)
            else:
                tables.append((
                    '',
                    'Domain-wise reports only support numeric '
                    'attributes, but %s has type %s.' %
                    (attribute, self._all_attributes[attribute].__name__)))
            for domain in sorted(self.domains.keys()):
                tables.append((domain, self._get_table(attribute, domain)))

            parts = []
            toc_line = []
            for (domain, table) in tables:
                if domain:
                    assert table
                    toc_line.append("[''%(domain)s'' #%(attribute)s-%(domain)s]" %
                                    locals())
                    parts.append('== %(domain)s ==[%(attribute)s-%(domain)s]\n'
                                 '%(table)s\n' % locals())
                else:
                    if table:
                        parts.append('%(table)s\n' % locals())
                    else:
                        parts.append('No task was found where all algorithms '
                                     'have a value for "%s". Therefore no '
                                     'domain-wise table can be generated.\n' %
                                     attribute)

            toc_lines.append("- **[''%s'' #%s]**" % (attribute, attribute))
            toc_lines.append('  - ' + ' '.join(toc_line))
            sections.append((attribute, '\n'.join(parts)))

        # Add summary before main content. This is done after creating the main content
        # because the summary table is extracted from all other tables.
        sections.insert(summary_index, ('summary', summary))

        toc = '\n'.join(toc_lines)

        content = '\n'.join('= %s =[%s]\n\n%s' % (attr, attr, section)
                            for (attr, section) in sections)
        return '%s\n\n\n%s' % (toc, content)

    def _get_general_info(self):
        table = reports.Table(title='algorithm')
        for algo, info in self.algorithm_info.items():
            for attr in self.INFO_ATTRIBUTES:
                if info[attr]:
                    table.add_cell(algo, attr, info[attr])
        table.set_column_order(self.INFO_ATTRIBUTES)

        node_info = "Used nodes: {{{}}}".format(
            ", ".join(_abbreviate_node_names(self._get_node_names())))

        if table:
            return str(table) + "\n" + node_info
        else:
            logging.warning('Table containing algorithm information is empty.')
            return node_info

    def _get_group_functions(self, attribute):
        """Decide on a list of group functions for this attribute."""
        return [(reports.function_name(f), f) for f in attribute.functions]

    def _add_table_info(self, attribute, func_name, table):
        """
        Add some information to the table for attributes where data is missing.
        """
        if not attribute.absolute:
            table.info.append('Only instances where all algorithms have a '
                              'value for "%s" are considered.' % attribute)
            table.info.append('Each table entry gives the %s of "%s" for that '
                              'domain.' % (func_name, attribute))

        summary_names = [name.lower() for name, _ in table.summary_funcs.items()]
        if len(summary_names) == 1:
            table.info.append('The last row reports the %s across all domains.' %
                              summary_names[0])
        elif len(summary_names) > 1:
            table.info.append('The last rows report the %s across all domains.' %
                              ' and '.join(summary_names))

    def _get_suite_table(self, attribute):
        assert self.attribute_is_numeric(attribute), attribute
        table = self._get_empty_table(attribute)
        self._add_summary_functions(table, attribute)
        # The first group function is used for aggregation.
        func_name, func = self._get_group_functions(attribute)[0]
        num_probs = 0
        self._add_table_info(attribute, func_name, table)
        domain_algo_values = defaultdict(list)
        for (domain, problem), runs in self.problem_runs.items():
            if (not attribute.absolute and
                    any(run.get(attribute) is None for run in runs)):
                continue
            num_probs += 1
            for run in runs:
                value = run.get(attribute)
                if value is not None:
                    domain_algo_values[(domain, run['algorithm'])].append(value)

        # If the attribute is absolute (e.g. coverage) we may have
        # added problems for which not all algorithms have a value. Therefore, we
        # can only print the number of instances (in brackets after the domain
        # name) if that number is the same for all algorithms. If not all algorithms
        # have values for the same number of problems, we write the full list of
        # different problem numbers.
        num_values_lists = defaultdict(list)
        for domain in self.domains:
            for algo in self.algorithms:
                values = domain_algo_values.get((domain, algo), [])
                num_values_lists[domain].append(str(len(values)))
        for domain, num_values_list in num_values_lists.items():
            if len(set(num_values_list)) == 1:
                count = num_values_list[0]
            else:
                count = ','.join(num_values_list)
            link = None
            if self.use_domain_links:
                link = '#%s-%s' % (attribute, domain)
            formatter = reports.CellFormatter(link=link, count=count)
            table.cell_formatters[domain][table.header_column] = formatter

        for (domain, algo), values in domain_algo_values.items():
            table.add_cell(domain, algo, func(values))

        table.num_values = num_probs
        return table

    def _get_domain_table(self, attribute, domain):
        table = self._get_empty_table(attribute)

        for algo in self.algorithms:
            for run in self.domain_algorithm_runs[domain, algo]:
                table.add_cell(run['problem'], algo, run.get(attribute))
        return table

    def _get_table(self, attribute, domain=None):
        if domain:
            return self._get_domain_table(attribute, domain)
        return self._get_suite_table(attribute)

    def _get_empty_table(self, attribute=None, title=None, columns=None):
        """Return an empty table."""
        if title is None:
            assert attribute is not None
            title = attribute
            if self.output_format == 'tex':
                title = title.capitalize().replace('_', ' ')
        if columns is None:
            columns = self.algorithms

        if attribute is not None and self.attribute_is_numeric(attribute):
            # Decide whether we want to highlight minima or maxima.
            kwargs = dict(
                min_wins=attribute.min_wins,
                colored=self.colored and attribute.min_wins is not None,
                digits=attribute.digits)
        else:
            # Do not highlight anything.
            kwargs = {}
        table = reports.Table(title=title, **kwargs)
        table.set_column_order(columns)
        link = '#%s' % title
        formatter = reports.CellFormatter(link=link)
        table.cell_formatters[table.header_row][table.header_column] = formatter
        return table

    def _add_summary_functions(self, table, attribute):
        for funcname, func in self._get_group_functions(attribute):
            table.add_summary_function(funcname.capitalize(), func)
