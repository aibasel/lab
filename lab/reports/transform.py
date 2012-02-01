import json

from lab.reports import Report


class TransformReport(Report):
    def __init__(self, *args, **kwargs):
        Report.__init__(self, *args, **kwargs)

    def get_text(self):
        return str(self.props)
