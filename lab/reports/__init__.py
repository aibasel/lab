"""
Module that permits generating reports by reading properties files
"""

import collections
from collections import defaultdict
import fnmatch
import logging
import math
import numbers
import os
import sys

import txt2tags

from lab import tools
from lab.reports import markup
from lab.reports.markup import Document, ESCAPE_WORDBREAK


def arithmetic_mean(values):
    """Compute the arithmetic mean of a sequence of numbers.

    >>> arithmetic_mean([20, 30, 70])
    40.0
    """
    assert None not in values
    return math.fsum(values) / len(values)


def geometric_mean(values):
    """Compute the geometric mean of a sequence of numbers.

    >>> round(geometric_mean([2, 8]), 2)
    4.0
    """
    assert None not in values
    exp = 1.0 / len(values)
    return tools.product([val**exp for val in values])


def finite_sum(values):
    """Compute the sum of a list of numbers, excluding values of
    None and 'infinity'.
    """
    return sum(x for x in values if x is not None and x != sys.maxsize)


def function_name(f):
    names = {
        "arithmetic_mean": "arithmetic mean",
        "finite_sum": "finite sum",
        "geometric_mean": "geometric mean",
    }
    return names.get(f.__name__, f.__name__)


def get_aggregation_function(function, functions):
    """
    Code for backwards compatibility.
    """
    if function and functions:
        logging.critical(
            'You cannot use "function" and "functions" kwargs for '
            "Attribute at the same time."
        )
    elif functions:
        tools.show_deprecation_warning(
            '"functions" kwarg for Attribute is deprecated. Use ' '"function" instead.'
        )
        if len(functions) > 1:
            logging.critical("Using multiple aggregation functions is unsupported.")
        return functions[0]
    else:
        return function


class Attribute(str):
    """A string subclass for attributes in reports."""

    def __new__(cls, name, **kwargs):
        return str.__new__(cls, name)

    def __init__(
        self,
        name,
        absolute=False,
        min_wins=True,
        function=None,
        functions=None,
        scale=None,
        digits=2,
    ):
        """
        Use this class if your **custom** attribute needs a non-default
        value for:

        * *absolute*: if False, only include tasks for which all task
          runs have values in a per-domain table (e.g. ``coverage`` is
          absolute, whereas ``expansions`` is not, because we can't
          compare algorithms A and B for task X if B has no value for
          ``expansions``).
        * *min_wins*: set to True if a smaller value for this attribute
          is better, to False if a higher value is better and to None
          if values can't be compared. (E.g., *min_wins* is False for
          ``coverage``, but it is True for ``expansions``).
        * *function*: the function used to aggregate
          values of multiple runs for this attribute, for example, in
          domain reports. Defaults to :py:func:`sum`.
        * *functions*: deprecated. Pass a single *function* instead.
        * *scale*: default scaling. Can be one of "linear", "log" and
          "symlog". If *scale* is None (default), the reports will
          choose the scaling.
        * *digits*: number of digits after the decimal point.

        The ``downward`` package automatically uses appropriate
        settings for most attributes.

        >>> avg_h = Attribute("avg_h", min_wins=False)
        >>> abstraction_done = Attribute(
        ...     "abstraction_done", absolute=True, min_wins=False
        ... )

        """
        self.absolute = absolute
        self.min_wins = min_wins
        self.function = (
            get_aggregation_function(function, tools.make_list(functions)) or sum
        )
        self.scale = scale
        self.digits = digits

    def copy(self, name):
        return Attribute(
            name,
            absolute=self.absolute,
            min_wins=self.min_wins,
            function=self.function,
            scale=self.scale,
            digits=self.digits,
        )


class Report:
    """
    Base class for all reports.
    """

    def __init__(self, attributes=None, format="html", filter=None, **kwargs):
        """
        Inherit from this or a child class to implement a custom report.

        Depending on the type of output you want to make, you will have
        to overwrite the :meth:`.write`, :meth:`.get_text` or
        :meth:`.get_markup` method.

        *attributes* is the list of attributes you want to include in
        your report. If omitted, use all numerical attributes. Globbing
        characters * and ? are allowed. Example:

        >>> report = Report(attributes=["coverage", "translator_*"])

        When a report is made, both the available and the selected
        attributes are printed on the commandline.

        *format* can be one of e.g. html, tex, wiki (MediaWiki), doku
        (DokuWiki), pmw (PmWiki), moin (MoinMoin) and txt (Plain text).
        Subclasses may allow additional formats.

        If given, *filter* must be a function or a list of functions
        that are passed a dictionary of a run's attribute keys and
        values. Filters must return True, False or a new dictionary.
        Depending on the returned value, the run is included or excluded
        from the report, or replaced by the new dictionary,
        respectively.

        Filters for properties can be given in shorter form without
        defining a function. To include only runs where attribute
        ``foo`` has value v, use ``filter_foo=v``. To include only runs
        where attribute ``foo`` has value v1, v2 or v3, use
        ``filter_foo=[v1, v2, v3]``.

        Filters are applied sequentially, i.e., the first filter is
        applied to all runs before the second filter is executed.
        Filters given as ``filter_*`` kwargs are applied *after* all
        filters passed via the ``filter`` kwarg.

        Examples:

        Include only the "cost" attribute in a LaTeX report:

        >>> report = Report(attributes=["cost"], format="tex")

        Only include successful runs in the report:

        >>> report = Report(filter_coverage=1)

        Only include runs in the report where the initial h value is
        at most 100:

        >>> def low_init_h(run):
        ...     return run["initial_h_value"] <= 100
        ...
        >>> report = Report(filter=low_init_h)

        Only include runs from "blocks" and "barman" with a timeout:

        >>> report = Report(filter_domain=["blocks", "barman"], filter_search_timeout=1)

        Add a new attribute:

        >>> def add_expansions_per_time(run):
        ...     expansions = run.get("expansions")
        ...     time = run.get("search_time")
        ...     if expansions is not None and time:
        ...         run["expansions_per_time"] = expansions / time
        ...     return run
        ...
        >>> report = Report(
        ...     attributes=["expansions_per_time"], filter=[add_expansions_per_time]
        ... )

        Rename, filter and sort algorithms:

        >>> def rename_algorithms(run):
        ...     name = run["algorithm"]
        ...     paper_names = {"lama11": "LAMA 2011", "fdss_sat1": "FDSS 1"}
        ...     run["algorithm"] = paper_names[name]
        ...     return run
        ...

        >>> # We want LAMA 2011 to be the leftmost column.
        >>> # filter_* filters are evaluated last, so we use the updated
        >>> # algorithm names here.
        >>> algorithms = ["LAMA 2011", "FDSS 1"]
        >>> report = Report(filter=rename_algorithms, filter_algorithm=algorithms)

        """
        self.attributes = tools.make_list(attributes)
        if format not in txt2tags.TARGETS + ["eps", "pdf", "pgf", "png", "py"]:
            raise ValueError(f"invalid format: {format}")
        self.output_format = format
        self.toc = True
        self.run_filter = tools.RunFilter(filter, **kwargs)

    def __call__(self, eval_dir, outfile):
        """Make the report.

        This method is called automatically when the report step is
        executed. It loads the data and calls :meth:`.write`.

        *eval_dir* must be a path to an evaluation directory containing
        a ``properties`` file.

        The report will be written to *outfile*.
        """
        if not eval_dir.endswith("-eval"):
            logging.info(
                'The source directory does not end with "-eval". '
                "Are you sure this is an evaluation directory?"
            )
        self.eval_dir = os.path.abspath(eval_dir)
        # It would be nice if we could infer "format" from "outfile", but the
        # former is needed before the latter is available.
        # Also we can't add the extension ".format" to "outfile" in case it's
        # missing, because "outfile" might be a directory.
        self.outfile = os.path.abspath(outfile)

        # Map from attribute to type.
        self._all_attributes = {}
        self._load_data()
        self._apply_filter()
        self._scan_data()

        # Turn string attributes into instances of Attribute.
        self.attributes = [self._prepare_attribute(attr) for attr in self.attributes]

        # Expand glob characters.
        self.attributes = self._glob_attributes(self.attributes)

        if not self.attributes:
            logging.info(f"Available attributes: {', '.join(self.all_attributes)}")
            logging.info("Using all numerical attributes.")
            self.attributes = self._get_numerical_attributes()

        self.attributes = sorted(self.attributes)

        # Check for duplicate attributes to avoid "coverage" overwriting
        # Attribute("coverage") by accident.
        counter = collections.Counter(self.attributes)
        duplicates = [name for name, count in sorted(counter.items()) if count > 1]
        if duplicates:
            logging.critical(f"Duplicate attributes detected: {duplicates}")

        self.write()

    def _prepare_attribute(self, attr):
        if isinstance(attr, Attribute):
            return attr
        return Attribute(attr)

    def _glob_attributes(self, attributes):
        expanded_attrs = []
        for attr in attributes:
            # Attribute without wildcards. Filtering would reset its options.
            if attr in self.all_attributes:
                expanded_attrs.append(attr)
                continue
            matches = fnmatch.filter(self.all_attributes, attr)
            if not matches:
                logging.warning(
                    f'There is no attribute "{attr}" in the properties file.'
                )
            # Use the attribute options from the pattern for all matches, but
            # don't try to guess options for attributes that appear in the list.
            expanded_attrs.extend(
                [attr.copy(match) for match in matches if match not in attributes]
            )
        if attributes and not expanded_attrs:
            logging.critical("No attributes match your patterns.")
        return expanded_attrs

    @property
    def all_attributes(self):
        return sorted(self._all_attributes.keys())

    def _get_numerical_attributes(self):
        return [
            attr
            for attr in self._all_attributes.keys()
            if self.attribute_is_numeric(attr)
        ]

    def attribute_is_numeric(self, attribute):
        """Return true if the values for *attribute* are ints or floats.

        If the attribute is None in all runs it may be numeric.

        """
        return self._all_attributes[attribute] is None or issubclass(
            self._all_attributes[attribute], numbers.Number
        )

    def get_markup(self):
        """
        Return `txt2tags <http://txt2tags.org/>`_ markup for the report.

        """
        table = Table()
        for run_id, run in self.props.items():
            row = {}
            for key, value in run.items():
                if key not in self.attributes:
                    continue
                if isinstance(value, (list, tuple)):
                    key = "-".join(str(item) for item in value)
                row[key] = value
            table.add_row(run_id, row)
        return str(table)

    def get_text(self):
        """
        Return text (e.g., HTML, LaTeX, etc.) for the report.

        By default this method calls :meth:`.get_markup` and converts
        the markup to the desired output *format*.

        """
        name, _ = os.path.splitext(os.path.basename(self.outfile))
        doc = Document(title=name)
        doc.add_text(
            self.get_markup()
            or "No tables were generated. "
            "This happens when no significant changes occured or "
            "if for all attributes and all problems never all "
            "algorithms had a value for this attribute in a "
            "per-domain report."
        )
        return doc.render(self.output_format, {"toc": self.toc})

    def write(self):
        """
        Write the report files.

        By default this method calls :meth:`.get_text` and writes the
        obtained text to *outfile*.

        Overwrite this method if you want to write the report file(s)
        directly. You should write them to *self.outfile*.

        """
        content = self.get_text()
        tools.makedirs(os.path.dirname(self.outfile))
        tools.write_file(self.outfile, content)
        logging.info(f"Wrote file://{self.outfile}")

    def _get_type(self, attribute):
        for run in self.props.values():
            val = run.get(attribute)
            if val is not None:
                return type(val)
        # Attribute is None in all runs.
        return None

    def _get_type_map(self, attributes):
        return {
            self._prepare_attribute(attr): self._get_type(attr) for attr in attributes
        }

    def _scan_data(self):
        attributes = set()
        for run in self.props.values():
            attributes |= set(run.keys())
        self._all_attributes = self._get_type_map(attributes)

    def _load_data(self):
        props_file = os.path.join(self.eval_dir, "properties")
        logging.info("Reading properties file")
        self.props = tools.Properties(filename=props_file)
        if not self.props:
            logging.critical(f"No properties found in {self.eval_dir}")
        logging.info("Reading properties file finished")

    def _apply_filter(self):
        self.run_filter.apply(self.props)
        if not self.props:
            logging.critical("All runs have been filtered -> Nothing to report.")


class CellFormatter:
    """Formating information for one cell in a table."""

    def __init__(
        self, bold=False, count=None, link=None, color=None, align_right=False
    ):
        self.bold = bold
        self.count = count
        self.link = link
        self.color = color
        self.align_right = align_right

    def format_value(self, value):
        result = str(value)
        if self.link:
            result = f"[''{result}'' {self.link}]"
        if self.count:
            result = f"{result} ({self.count})"
        if self.bold:
            result = f"**{result}**"
        if self.color:
            result = f"{{{result}|color:{self.color}}}"

        if self.align_right:
            result = " " + result
        else:
            result += " "

        return result


class Table(collections.defaultdict):
    def __init__(self, title="", min_wins=None, colored=False, digits=2):
        """
        The *Table* class can be useful for `Report` subclasses that want to
        return a table as txt2tags markup. It is realized as a dictionary of
        dictionaries mapping row names to colum names to cell values. To obtain
        the markup from a table, use the ``str()`` function.

        *title* will be printed in the top left cell.

        *min_wins* can be either None, True or False. If it is True (False),
        the cell with the lowest (highest) value in each row will be
        highlighted.

        If *colored* is True, the values of each row will be given colors from a
        colormap.

        Numbers are rounded to *digits* positions after the decimal point.

        >>> t = Table(title="expansions")
        >>> t.add_cell("prob1", "cfg1", 10)
        >>> t.add_cell("prob1", "cfg2", 20)
        >>> t.add_row("prob2", {"cfg1": 15, "cfg2": 25})
        >>> def remove_quotes(s):
        ...     return s.replace('""', "")
        ...
        >>> print(remove_quotes(str(t)))
        || expansions |  cfg1 |  cfg2 |
         | prob1  |  10 |  20 |
         | prob2  |  15 |  25 |
        >>> t.row_names
        ['prob1', 'prob2']
        >>> t.col_names
        ['cfg1', 'cfg2']
        >>> t.get_row("prob2")
        [15, 25]
        >>> t.get_columns() == {"cfg1": [10, 15], "cfg2": [20, 25]}
        True
        >>> t.add_summary_function("SUM", sum)
        >>> print(remove_quotes(str(t)))
        || expansions |  cfg1 |  cfg2 |
         | prob1  |  10 |  20 |
         | prob2  |  15 |  25 |
         | **SUM**  |  25 |  45 |
        >>> t.set_column_order(["cfg2", "cfg1"])
        >>> print(remove_quotes(str(t)))
        || expansions |  cfg2 |  cfg1 |
         | prob1  |  20 |  10 |
         | prob2  |  25 |  15 |
         | **SUM**  |  45 |  25 |
        """
        collections.defaultdict.__init__(self, dict)

        self.title = title
        self.min_wins = min_wins
        self.row_min_wins = {}
        self.colored = colored
        self.digits = digits

        self.summary_funcs = {}
        self.info = []
        self.num_values = None
        self.dynamic_data_modules = []

        self._cols = None

        # For printing.
        self.header_row = "column names (never printed)"
        self.header_column = "row names (never printed)"
        self.cell_formatters = collections.defaultdict(dict)
        self.row_order = None
        self.column_order = None
        self.summary_row_order = []

    def add_cell(self, row, col, value):
        """Set Table[row][col] = value."""
        self[row][col] = value
        self._cols = None

    def add_row(self, row_name, row):
        """Add a new data row called *row_name* to the table.

        *row* must be a mapping from column names to values.
        """
        self[row_name] = row
        self._cols = None

    def add_col(self, col_name, col):
        """Add a new data column called *col_name* to the table.

        *col* must be a mapping from row names to values.
        """
        for row_name, value in col.items():
            self[row_name][col_name] = value
        self._cols = None

    @property
    def row_names(self):
        """Return all data row names in sorted order."""
        return self.row_order or tools.natural_sort(self.keys())

    @property
    def col_names(self):
        """Return all data column names in sorted order."""
        if self._cols:
            return self._cols
        col_names = set()
        for row in self.values():
            col_names |= set(row.keys())
        self._cols = []
        if self.column_order:
            # First use all elements for which we know an order.
            # All remaining elements will be sorted alphabetically.
            self._cols = [c for c in self.column_order if c in col_names]
            col_names -= set(self._cols)
        self._cols += tools.natural_sort(col_names)
        return self._cols

    def get_row(self, row_name):
        """Return a list of the values in *row*."""
        return [self[row_name].get(col_name, None) for col_name in self.col_names]

    def get_columns(self):
        """
        Return a mapping from column names to the list of values in that column.
        """
        values = defaultdict(list)
        for row_name in self.row_names:
            for col_name in self.col_names:
                values[col_name].append(self[row_name].get(col_name))
        return values

    def add_summary_function(self, name, func):
        """
        Add a bottom row with the values ``func(column_values)`` for
        each column. *func* can be e.g. :func:`sum`,
        :func:`arithmetic_mean` or :func:`geometric_mean`.

        """
        self.summary_funcs[name] = func
        self.summary_row_order.append(name)

    def set_row_order(self, order):
        self.row_order = order

    def set_column_order(self, order):
        self.column_order = order
        self._cols = None

    def get_min_wins(self, row_name=None):
        """
        The table class can store information on whether higher or
        lower values are better for each row or globally. If no row
        specific setting for *row_name* is found, the global setting is
        returned.

        """
        return self.row_min_wins.get(row_name, self.min_wins)

    def get_summary_rows(self):
        """
        Returns a dictionary mapping names of summary rows to dictionaries
        mapping column names to values.
        """
        summary_rows = {}
        for row_name in self.summary_row_order:
            func = self.summary_funcs[row_name]
            summary_row = {}
            for col_name, column in self.get_columns().items():
                values = [val for val in column if val is not None]
                if values:
                    summary_row[col_name] = func(values)
                else:
                    summary_row[col_name] = None
            summary_row[self.header_column] = row_name
            summary_rows[row_name] = summary_row
            formatter = CellFormatter(bold=True, count=self.num_values)
            self.cell_formatters[row_name][self.header_column] = formatter
        return summary_rows

    def _get_printable_row_order(self):
        """
        Return a list of all rows (including non-data rows) in the order
        they should be printed.
        """
        row_order = [self.header_row]
        for row_name in self.row_names + self.summary_row_order:
            row_order.append(row_name)
        for module in self.dynamic_data_modules:
            row_order = module.modify_printable_row_order(self, row_order) or row_order
        return row_order

    def _get_printable_column_order(self):
        """
        Return a list of all columns (including non-data columns) in the order
        they should be printed.
        """
        col_order = [self.header_column]
        for col_name in self.col_names:
            col_order.append(col_name)
        for module in self.dynamic_data_modules:
            col_order = (
                module.modify_printable_column_order(self, col_order) or col_order
            )
        return col_order

    def _collect_cells(self):
        """
        Collect all cells that should be printed including table headers,
        row names, summary rows, etc. Returns a dictionary mapping row names
        to dictionaries mapping column names to values.
        """
        cells = collections.defaultdict(dict)
        cells[self.header_row][self.header_column] = self.title
        for col_name in self.col_names:
            cells[self.header_row][col_name] = str(col_name)
        # Add data rows and summary rows.
        for row_name, row in list(self.items()) + list(self.get_summary_rows().items()):
            cells[row_name][self.header_column] = str(row_name)
            for col_name in self.col_names:
                cells[row_name][col_name] = row.get(col_name)
        for dynamic_data_module in self.dynamic_data_modules:
            cells = dynamic_data_module.collect(self, cells) or cells
        return cells

    def _format(self, cells):
        """Format all entries in **cells** (in place)."""
        for row_name, row in cells.items():
            self._format_row(row_name, row)
        for dynamic_data_module in self.dynamic_data_modules:
            dynamic_data_module.format(self, cells)

    def _format_value(self, value):
        if isinstance(value, float):
            return f"{value:.{self.digits}f}"
        else:
            result = str(value)

        # Only escape text if it doesn't contain LaTeX or HTML markup.
        if "''" in result:
            return result
        else:
            return markup.escape(result)

    def _format_row(self, row_name, row):
        """Format all entries in **row** (in place)."""
        if row_name == self.header_row:
            for col_name, value in row.items():
                # Allow breaking after underlines.
                value = value.replace("_", "_" + ESCAPE_WORDBREAK)
                # Right-align headers (except the left-most one).
                if col_name != self.header_column:
                    value = " " + value
                row[col_name] = value
            return

        # Get the slice of the row that should be formatted (i.e., the data columns).
        # Note that there might be other columns (e.g., added by dynamic data
        # modules) that should not be formatted.
        row_slice = {col_name: row.get(col_name) for col_name in self.col_names}

        min_wins = self.get_min_wins(row_name)
        highlight = min_wins is not None
        colored = self.colored and highlight
        if colored:

            def try_to_round(v):
                try:
                    return round(v, self.digits)
                except TypeError:
                    return v

            rounded_row_slice = {
                col: try_to_round(val) for col, val in row_slice.items()
            }
            colors = tools.get_colors(rounded_row_slice, min_wins)

        if highlight:
            min_value, max_value = tools.get_min_max(row_slice.values())
        else:
            min_value, max_value = None, None

        def is_close(a, b):
            # Highlight based on precision visible in table, not actual values.
            return self._format_value(a) == self._format_value(b)

        for col_name, value in row.items():
            color = None
            bold = False
            # Format data columns
            if col_name in row_slice:
                if colored:
                    color = tools.rgb_fractions_to_html_color(*colors[col_name])
                elif (
                    highlight
                    and value is not None
                    and (
                        (is_close(value, min_value) and min_wins)
                        or (is_close(value, max_value) and not min_wins)
                    )
                ):
                    bold = True
            row[col_name] = self._format_cell(
                row_name, col_name, value, color=color, bold=bold
            )

    def _format_cell(self, row_name, col_name, value, color=None, bold=False):
        """
        Return the formatted value for a single cell in the table.
        *row_name* and *col_name* specify the position of the cell and *value* is the
        unformatted value.
        Floats are rounded to two decimal places and lists are quoted. The *color* to
        render the result in can be given as a string and setting *bold* to true
        renders the value in bold.

        If a custom formatter is specified for this cell, it is used instead of this
        default format.
        """
        formatter = self.cell_formatters.get(row_name, {}).get(col_name)
        if not formatter:
            align_right = (
                isinstance(value, (float, int)) or value is None or value == "?"
            )
            value = self._format_value(value)
            formatter = CellFormatter(bold=bold, color=color, align_right=align_right)
        return formatter.format_value(value)

    def _get_markup(self, cells):
        """
        Return a string cotaining all printable cells (see
        **_get_printable_column_order** and **_get_printable_row_order**)
        as correctly formatted markup.
        """
        parts = []
        for row_name in self._get_printable_row_order():
            if row_name == self.header_row:
                parts.append(self._get_header_markup(row_name, cells[row_name]))
            else:
                parts.append(self._get_row_markup(row_name, cells[row_name]))
        if self.info:
            parts.append(" ".join(self.info))
        return "\n".join(parts)

    def _get_header_markup(self, row_name, row):
        """Return the txt2tags table markup for the headers."""
        return self._get_row_markup(row_name, row, template="|| {} |")

    def _get_row_markup(self, row_name, row, template=" | {} |"):
        """Return the txt2tags table markup for one row."""
        formatted_cells = []
        for col_name in self._get_printable_column_order():
            formatted_cells.append(row.get(col_name, ""))
        return template.format(" | ".join(formatted_cells))

    def __str__(self):
        """Return the txt2tags markup for this table."""
        cells = self._collect_cells()
        self._format(cells)
        return self._get_markup(cells)


def extract_summary_rows(from_table, to_table, link=None):
    """
    Extract all summary rows of **from_table** and add them as data rows
    to **to_table**.
    """
    for name, row in from_table.get_summary_rows().items():
        row_name = f"{from_table.title} - {name}"
        if link is not None:
            formatter = CellFormatter(link=link)
            to_table.cell_formatters[row_name][to_table.header_column] = formatter
        to_table.row_min_wins[row_name] = from_table.min_wins
        for col_name, value in row.items():
            if col_name == from_table.header_column:
                continue
            to_table.add_cell(row_name, col_name, value)


class DynamicDataModule:
    """Interface for modules that dynamically add or modify data in a table."""

    def collect(self, table, cells):
        """
        Called after the data collection in the table. Subclasses can
        add new values to **cells** or modify existing values.
        """
        return cells

    def format(self, table, formatted_cells):
        """
        Called after the formatting in the table. Subclasses can
        (re-)format all values in **formatted_cells**. Specifically all new
        values added by the **collect** method should be formatted.
        """
        pass

    def modify_printable_row_order(self, table, row_order):
        """
        Called after retrieving a row order in the table. Subclasses can
        modify the order or add new rows. Specifically all rows that were
        added by the **collect** method should be appended or
        inserted.
        """
        return row_order

    def modify_printable_column_order(self, table, column_order):
        """
        Called after retrieving a column order in the table. Subclassed can
        modify the order or add new columns. Specifically all columns that were
        values added by the **collect** method should be appended or
        inserted.
        """
        return column_order
