from lab.reports import Report


class FilterReport(Report):
    """Use this report class to filter properties files.

    This report only applies the given filter and writes a new properties file
    to the output destination.

    >>> def remove_openstacks(run):
    >>>     return not 'openstacks' in run['domain']
    >>>
    >>> exp.add_step(Step('filter-openstacks-runs',
                          TransformReport(filter=remove_openstacks),
                          exp.eval_dir, 'path/to/new/properties'))
    """
    def __init__(self, *args, **kwargs):
        Report.__init__(self, *args, **kwargs)

    def get_text(self):
        return str(self.props)
