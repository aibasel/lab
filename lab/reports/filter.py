from lab.reports import Report


class FilterReport(Report):
    """Filter properties files.

    This report only applies the given filter and writes a new
    properties file to the given output destination.

    >>> def remove_openstacks(run):
    ...     return "openstacks" not in run["domain"]
    ...

    >>> from lab.experiment import Experiment
    >>> report = FilterReport(filter=remove_openstacks)
    >>> exp = Experiment()
    >>> exp.add_report(report, outfile="path/to/new/properties")

    """

    # Without the docstring Sphinx reuses docstring from parent class.
    def __init__(self, **kwargs):
        """"""
        super().__init__(**kwargs)

    def get_text(self):
        return str(self.props)
