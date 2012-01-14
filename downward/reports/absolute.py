from collections import defaultdict
import logging

from lab.reports import avg, gm

from downward.reports import PlanningReport


class AbsoluteReport(PlanningReport):
    """
    Write an absolute report about the attribute attribute, e.g.

    || expanded        | fF               | yY               |
    | **gripper     ** | 118              | 72               |
    | **zenotravel  ** | 21               | 17               |
    """
    def __init__(self, resolution, *args, **kwargs):
        """
        resolution: One of "domain" or "problem".
        """
        self.resolution = resolution
        PlanningReport.__init__(self, *args, **kwargs)

    def _load_data(self):
        PlanningReport._load_data(self)
        self.process_data()

    def process_data(self):
        # Use local variables first to save lookups
        problems = set()
        domains = defaultdict(list)
        configs = set()
        problem_runs = defaultdict(list)
        runs = {}
        for run_name, run in self.props.items():
            configs.add(run['config'])
            domain, problem, config = run['domain'], run['problem'], run['config']
            problems.add((domain, problem))
            problem_runs[(domain, problem)].append(run)
            # TODO: Remove once props keys are lists
            runs[(domain, problem, config)] = run
        for domain, problem in problems:
            domains[domain].append(problem)
        self.configs = list(sorted(configs))
        self.problems = list(sorted(problems))
        self.domains = domains
        self.problem_runs = problem_runs
        self.runs = runs

    def _attribute_is_absolute(self, attribute):
        """
        The domain-wise sum of the values for coverage and *_error even makes
        sense if not all configs have values for those attributes.
        """
        return attribute == 'coverage' or attribute.endswith('_error')

    def _get_group_func(self, attribute):
        """Decide on a group function for this attribute."""
        if 'score' in attribute:
            return 'average', avg
        elif attribute in ['search_time', 'total_time']:
            return 'geometric mean', gm
        return 'sum', sum

    def _add_table_info(self, attribute, func_name, table):
        # Add some information to the table for attributes where data is missing
        if self._attribute_is_absolute(attribute):
            return

        table.info.append('Only instances where all configurations have a '
                          'value for "%s" are considered.' % attribute)
        table.info.append('Each table entry gives the %s of "%s" for that '
                          'domain.' % (func_name, attribute))
        summary_names = [name.lower() for name, sum_func in table.summary_funcs]
        if len(summary_names) == 1:
            table.info.append('The last row gives the %s across all domains.' %
                              summary_names[0])
        elif len(summary_names) > 1:
            table.info.append('The last rows give the %s across all domains.' %
                              ' and '.join(summary_names))

    def _get_table(self, attribute):
        table = PlanningReport._get_empty_table(self, attribute)
        func_name, func = self._get_group_func(attribute)

        if self.resolution == 'domain':
            self._add_table_info(attribute, func_name, table)
            domain_config_values = defaultdict(list)
            for domain, problems in self.domains.items():
                for problem in problems:
                    runs = self.problem_runs[(domain, problem)]
                    if any(run.get(attribute) is None for run in runs):
                        continue
                    for config in self.configs:
                        value = self.runs[(domain, problem, config)].get(attribute)
                        if value is not None:
                            domain_config_values[(domain, config)].append(value)
            for (domain, config), values in domain_config_values.items():
                table.add_cell('%s (%s)' % (domain, len(values)), config, func(values))
        elif self.resolution == 'problem':
            for (domain, problem, config), run in self.runs.items():
                table.add_cell(domain + ':' + problem, config, run.get(attribute))
        return table
