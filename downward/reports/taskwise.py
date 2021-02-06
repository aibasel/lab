import logging

from downward.reports import PlanningReport
from lab.reports import Table


class TaskwiseReport(PlanningReport):
    """
    For each task report all selected attributes in a single row.

    If the experiment contains more than one algorithm, use
    ``filter_algorithm=["my_algorithm"]`` to select exactly one algorithm
    for the report.

    >>> from downward.experiment import FastDownwardExperiment
    >>> exp = FastDownwardExperiment()
    >>> exp.add_report(
    ...     TaskwiseReport(
    ...         attributes=["expansions", "search_time"], filter_algorithm=["lmcut"]
    ...     )
    ... )

    Example output:

        +---------------------+------------+-------------+
        |                     | expansions | search_time |
        +=====================+============+=============+
        | grid:prob01.pddl    | 118234     |       20.02 |
        +---------------------+------------+-------------+
        | gripper:prob01.pddl |  21938     |       17.58 |
        +---------------------+------------+-------------+

    """

    def __init__(self, **kwargs):
        PlanningReport.__init__(self, **kwargs)

    def _get_table(self, domain, runs):
        table = Table(title=domain)
        for run in runs:
            for attr in self.attributes:
                table.add_cell(run["problem"], attr, run.get(attr))
        return table

    def get_markup(self):
        if len(self.algorithms) != 1:
            logging.critical("Taskwise reports need exactly one algorithm.")
        tables = [
            self._get_table(domain, runs)
            for (domain, _), runs in sorted(self.domain_algorithm_runs.items())
        ]
        return "\n".join(str(table) for table in tables)
