from __future__ import division

import logging
import sys
from collections import defaultdict

from lab.reports import Report, Table
from lab.reports import avg, gm
from lab.external.datasets import missing, not_missing
from lab.reports.markup import raw

from downward.reports import PlanningReport


COLORS = {True: 'green', False: 'red', None: 'gray'}


def probname(domain, problem):
    return '%s:%s' % (domain, problem)

def index(iterable, func):
    return func(range(len(iterable)), key=lambda i: iterable[i])

def max_index(iterable):
    return index(iterable, max)

def min_index(iterable):
    return index(iterable, min)

def min_indices(iterable):
    min_indices = []
    for i, x in enumerate(iterable):
        if not min_indices or x == iterable[min_indices[0]]:
            min_indices.append(i)
        elif x < iterable[min_indices[0]]:
            min_indices = [i]
    return min_indices


class ConfigSelector(object):
    def __init__(self, name, timeout):
        self.name = name
        self.timeout = timeout

    def select_for_problem(self, runs):
        return sorted(runs, key=self.sort)[0]['config']


class HighestFastestFSelector(ConfigSelector):
    def __init__(self, timeout):
        name = 'Highest fastest F-Value, timeout %d' % timeout
        ConfigSelector.__init__(self, name, timeout)

    def sort(self, run):
        f_max, time = self.get_highest_f_value(run, self.timeout)
        return -f_max, time

    def get_highest_f_value(self, run, timeout):
        """Return highest f value that was reached under timeout seconds."""
        f_max = -1
        needed_time = -1
        for f, evaluations, expansions, time in run['f_values']:
            if time > timeout:
                break
            f_max = f
            needed_time = time
        return f_max, needed_time


class FastestFSelector(ConfigSelector):
    """
    0.65 success in 10s
    """
    def __init__(self, timeout):
        name = 'Fastest F-Value, timeout %d' % timeout
        ConfigSelector.__init__(self, name, timeout)

    def sort(self, run):
        values = run['f_values']
        if not values:
            return sys.maxint
        f, evaluations, expansions, time = values[0]
        return time


class HighestFirstFSelector(ConfigSelector):
    """
    Without time: 0.50 success in 10s
    With time:    0.65 success in 10s
    """
    def __init__(self, timeout):
        name = 'Highest First F-Value, timeout %d' % timeout
        ConfigSelector.__init__(self, name, timeout)

    def sort(self, run):
        values = run['f_values']
        if not values:
            return sys.maxint, sys.maxint
        f, evaluations, expansions, time = values[0]
        return -f, time


class HighestFLeastExpansionsSelector(ConfigSelector):
    def __init__(self, timeout):
        name = 'Highest F-Value, least expansions, timeout %d' % timeout
        ConfigSelector.__init__(self, name, timeout)

    def sort(self, run):
        f_max, expansions = self.get_highest_f_value(run, self.timeout)
        return -f_max, expansions

    def get_highest_f_value(self, run, timeout):
        """Return highest f value that was reached under timeout seconds."""
        f_max = -1
        needed_expansions = -1
        for f, evaluations, expansions, time in run['f_values']:
            if time > timeout:
                break
            f_max = f
            needed_expansions = expansions
        return f_max, needed_expansions


class HighestFLeastEvaluationsSelector(ConfigSelector):
    def __init__(self, timeout):
        name = 'Highest F-Value, least evaluations, timeout %d' % timeout
        ConfigSelector.__init__(self, name, timeout)

    def sort(self, run):
        f_max, evaluations = self.get_highest_f_value(run, self.timeout)
        return -f_max, evaluations

    def get_highest_f_value(self, run, timeout):
        """Return highest f value that was reached under timeout seconds."""
        f_max = -1
        needed_evaluations = -1
        for f, evaluations, expansions, time in run['f_values']:
            if time > timeout:
                break
            f_max = f
            needed_evaluations = evaluations
        return f_max, needed_evaluations


class ProgressReport(Report):
    def __init__(self, *args, **kwargs):
        Report.__init__(self, *args, **kwargs)

    def get_run(self, config, domain, problem):
        return self.props['-'.join([config, domain, problem])]

    def get_runs(self, domain, problem):
        return [run for run in self.props.values() if run['domain'] == domain and
                                                      run['problem'] == problem]

    def select(self, props):
        selection = {}
        for domain, problem in self.problems:
            selection[(domain, problem)] = self.select_for_problem(self.get_runs(domain, problem))
        return selection

    def get_value(self, config, domain, problem, prop):
        return self.props['-'.join([config, domain, problem])].get(prop)

    def get_total_time(self, config, domain, problem):
        run = self.get_run(config, domain, problem)
        total_time = run.get('total_time')
        return total_time

    def get_total_times(self, domain, problem):
        orig_times = [self.get_total_time(config, domain, problem) for config in self.configs]
        return [t if t <= self.limit_search_time else self.time_unsolved for t in orig_times]

    def get_coverage(self, config):
        return sum(run['coverage'] for run in self.props.values()
                   if run['config'] == config and run['total_time'] <= self.limit_search_time)

    def get_portfolio_coverage(self, time_limits):
        coverage = 0
        for domain, problem in self.problems:
            for config in self.configs:
                run = self.get_run(config, domain, problem)
                if run['total_time'] <= time_limits[config]:
                    coverage += 1
                    break
        return coverage

    def get_time(self, config):
        return sum(run['total_time'] for run in self.props.values() if run['config'] == config and
                   run['coverage'] == 1)

    def evaluate(self, selection, presearch_timeout, remaining_time):
        evaluation = {}
        correct_choices = 0
        false_choices = 0
        coverage = 0
        cum_time = 0
        runtime_factors = []
        for domain, problem in self.problems:
            selected_config = selection[(domain, problem)]
            times = self.get_total_times(domain, problem)
            best_configs = [self.configs[i] for i in min_indices(times)]
            correct = selected_config in best_configs
            total_time = self.get_value(selected_config, domain, problem, 'total_time')
            solved = (total_time <= remaining_time)# or total_time <= presearch_timeout) # TODO: Add
            runtime_factors.append(total_time / min(times))
            if solved:
                coverage += 1
                cum_time += total_time
            if len(best_configs) == len(times):
                # Choice doesn't matter
                continue
            evaluation[(domain, problem)] = correct
            if correct:
                correct_choices += 1
            else:
                false_choices += 1
        return evaluation, correct_choices, false_choices, coverage, cum_time, gm(runtime_factors)

    def get_markup(self):
        problems = set()
        configs = set()
        for run_name, run in self.props.items():
            configs.add(run['config'])
            problems.add((run['domain'], run['problem']))
        self.configs = list(sorted(configs))
        self.problems = list(sorted(problems))

        for run_id, run in self.props.items():
            total_time = run.get('total_time')
            if total_time is None:
                time_limit = run.get('limit_search_time')
                assert time_limit is not None
                total_time = time_limit + 1
                self.props[run_id]['total_time'] = total_time
            values = run.get('f_values')
            if values is None:
                print 'ERROR:', run
                self.props[run_id]['f_values'] = []
            if run.get('coverage') is None:
                self.props[run_id]['coverage'] = 0

        self.limit_search_time = 900#self.props.values()[0]['limit_search_time']
        self.time_unsolved = self.limit_search_time + 1

        uniform_limits = defaultdict(lambda: self.limit_search_time / len(self.configs))

        markup = 'Problems: %d\n\n' % len(self.problems)
        markup += 'Coverage:\n' + ''.join(['- %s: %d\n' %
                (config, self.get_coverage(config))
                                          for config in self.configs]) + '\n\n'
        markup += 'Coverage uniform portfolio: %d\n\n' % self.get_portfolio_coverage(uniform_limits)
        markup += '\n\nExpected random success: %.2f\n' % (1 / len(self.configs))

        #TODO: Report times for portfolio by averaging over the times it takes to solve a problem for all possible config orders

        selectors = []
        selectors += [HighestFastestFSelector(t) for t in [10, 15, 20, 30, 40, 50, 60]]
        #selectors += [FastestFSelector(10)]
        #selectors += [HighestFirstFSelector(10)]
        #selectors += [HighestFLeastExpansionsSelector(10)]
        #selectors += [HighestFLeastEvaluationsSelector(10)]
        for selector in selectors:
            assert len(self.configs) * selector.timeout <= self.limit_search_time
            selection = {}
            for domain, problem in self.problems:
                runs = self.get_runs(domain, problem)
                selection[(domain, problem)] = selector.select_for_problem(runs)

            evaluation, corrects, incorrects, coverage, cum_time, mean_runtime_factor = self.evaluate(selection,
                        selector.timeout, self.limit_search_time - (len(self.configs) * selector.timeout))
            success = corrects / (corrects + incorrects) if corrects + incorrects > 0 else 0
            markup += ('=== %s ===\nCorrect: %d, False: %d, Success: %.2f, '
                       'Coverage: %d, Time: %.2f, Mean runtime factor: %.2f\n%s\n' % (
                    selector.name, corrects, incorrects, success,
                    coverage, cum_time, mean_runtime_factor,
                    ''#self.get_table(selection, evaluation)
                    ))

        return markup

    def get_table(self, selection, evaluation):
        table = Table(highlight=False)
        for domain, problem in self.problems:
            for index, config in enumerate(self.configs):
                selected = (config == selection[(domain, problem)])
                correct = evaluation.get((domain, problem))
                run = self.get_run(config, domain, problem)
                text = '%s -> %.2f' % (raw(run['f_values']), run['total_time'])
                if selected:
                    color = COLORS[correct]
                    text = '{{%s|color:%s}}' % (text, color)
                table.add_cell(probname(domain, problem), config, text)

        return str(table)
