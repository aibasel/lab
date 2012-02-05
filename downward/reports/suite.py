import sys

from downward.reports import PlanningReport


class SuiteReport(PlanningReport):
    """
    Write a list of problems to a file

    We do not need any markup processing or loop over attributes here,
    so the get_text() method is implemented right here.

    The data can be filtered by the filter functions passed to the constructor,
    all the runs are checked whether they pass the filters and the remaining
    runs are sorted, the duplicates are removed and the resulting list of
    problems is written to an output file.
    """
    def __init__(self, *args, **kwargs):
        PlanningReport.__init__(self, *args, **kwargs)

    def get_text(self):
        if not self.props:
            sys.exit('No problems match this filter')
        problems = [domain + ':' + problem for domain, problem in self.problems]
        problems = ['        "%s",\n' % problem for problem in problems]
        output = ('def suite():\n    return [\n%s    ]\n' % ''.join(problems))
        print '\nSUITE:'
        print output
        return output
