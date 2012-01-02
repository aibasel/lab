import logging
import sys

from lab.reports import Report, Table
from lab.downward.reports import PlanningReport
from lab.reports import avg, gm
from lab.external.datasets import missing, not_missing


def index(iterable, func):
    return func(range(len(iterable)), key=lambda i: iterable[i])

def max_index(iterable):
    return index(iterable, max)

def min_index(iterable):
    return index(iterable, min)

def min_indices(iterable):
    min_indices = []
    for i, x in enumerate(iterable):
        if not min_indices or x < iterable[min_indices[0]]:
            min_indices = [i]
    return min_indices


class ProgressReport(Report):
    def __init__(self, *args, **kwargs):
        Report.__init__(self, *args, **kwargs)

    def _load_data(self):
        self.data = Report._load_data(self)
        return self.data

    def get_run(self, config, domain, problem):
        return self.props['-'.join([config, domain, problem])]

    def get_value(self, config, domain, problem, prop):
        return self.props['-'.join([config, domain, problem])].get(prop)

    def get_markup(self):
        problems = set()
        configs = set()
        for run_name, run in self.props.items():
            configs.add(run['config'])
            problems.add((run['domain'], run['problem']))
        self.configs = list(sorted(configs))
        self.problems = list(sorted(problems))

        markup = ''
        for timeout in [0.0, 0.1, 0.5, 1, 5, 10, 20, 30, 60, 100]:
            markup += '===%.1f===\n%s\n' % (timeout, self.get_table(timeout))
        return markup

    def get_highest_f_value(self, run, timeout):
        """Return highest f value that was reached under timeout seconds."""
        values = run.get('f_values', [])
        if values is None:
            print 'ERROR:', run

        f_max = -1
        for time, f in values:
            if time > timeout:
                break
            f_max = f
        return f_max

    def get_table(self, timeout):
        table = Table(title='f-values -> time', highlight=False)
        for domain, problem in self.problems:
            prob = domain + ':' + problem
            f_values = []
            times = []
            for config in self.configs:
                run = self.get_run(config, domain, problem)
                total_time = run.get('total_time')
                if total_time is None:
                    time_limit = run.get('limit_search_time')
                    assert time_limit is not None
                    total_time = time_limit + 1
                f_max = self.get_highest_f_value(run, timeout)
                f_values.append(f_max)
                times.append(total_time)
            f_max_index = max_index(f_values)
            times_min_indices = min_indices(times)
            correct_choice = (f_max_index in times_min_indices)
            same_results = len(set(times)) == 1
            if same_results:
                continue
            for index, config in enumerate(self.configs):
                text = '%d -> %.2f' % (f_values[index], times[index])
                if index == f_max_index:
                    if not same_results:
                        color = 'green' if correct_choice else 'red'
                        text = '{{%s|color:%s}}' % (text, color)
                table.add_cell(prob, config, text)

        return str(table)
