from __future__ import division

import os
import sys
from collections import defaultdict
import itertools

from lab.reports import Report, Table
from lab.reports import gm
from lab.reports.markup import raw
from lab import tools


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
        self.timeout = float(timeout)

    def select_for_problem(self, runs):
        return sorted(runs, key=self.sort)[0]['config']

    def __str__(self):
        return 'oracle-%d' % self.timeout


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


def get_mean_portfolio_time(times, timeout):
    times = [min(time, timeout) for time in times]
    cum_times = []
    for order in itertools.permutations(times):
        cum_time = 0
        for time in order:
            cum_time += time
            if time < timeout:
                break
        cum_times.append(cum_time)
    return gm(cum_times)


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
                #print time_limits[config]
                if run['total_time'] <= time_limits[config]:
                    coverage += 1
                    break
        return coverage

    def get_time(self, config):
        return sum(run['total_time'] for run in self.props.values() if run['config'] == config and
                   run['coverage'] == 1)

    def evaluate(self, selection, selector, remaining_time):
        evaluation = {}
        correct_choices = 0
        false_choices = 0
        coverage = 0
        cum_time = 0
        runtime_factors = []
        for domain, problem in self.problems:
            run_id = '%s-%s-%s' % (selector, domain, problem)
            run = {}
            run['domain'] = domain
            run['problem'] = problem
            run['config'] = str(selector)
            selected_config = selection[(domain, problem)]
            times = self.get_total_times(domain, problem)
            best_configs = [self.configs[i] for i in min_indices(times)]
            correct = selected_config in best_configs
            total_time = self.get_value(selected_config, domain, problem, 'total_time')
            solved_in_presearch = any(t <= selector.timeout for t in times)
            if solved_in_presearch:
                total_time = get_mean_portfolio_time(times, selector.timeout)
            else:
                total_time = len(self.configs) * selector.timeout + total_time
            solved = (total_time <= remaining_time or solved_in_presearch)
            runtime_factors.append(total_time / min(times))
            run['coverage'] = int(solved)
            if solved:
                # TODO: Account for solutions found during presearch
                run['total_time'] = total_time
            elif 'total_time' in run:
                del run['total_time']
            if self.limit_search_time == 1800:
                self.new_props[run_id] = run
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

        self.new_props = tools.Properties()

        self.selectors = []
        self.selectors += [HighestFastestFSelector(t) for t in [1, 10, 15, 20, 30]]
        #self.selectors += [FastestFSelector(10)]
        #self.selectors += [HighestFirstFSelector(10)]
        #self.selectors += [HighestFLeastExpansionsSelector(10)]
        #self.selectors += [HighestFLeastEvaluationsSelector(10)]

        table = Table(title='Timeout', highlight=True, min_wins=False)
        markup = 'Problems: %d\n\n' % len(self.problems)

        for time_limit in [10, 50, 100, 150, 300, 600, 900, 1200, 1500, 1800]:
            self.limit_search_time = float(time_limit) #self.props.values()[0]['limit_search_time']
            self.time_unsolved = self.limit_search_time + 1
            self.uniform_limits = defaultdict(lambda: self.limit_search_time / len(self.configs))
            table.add_row(str(time_limit), self.get_table_row(time_limit))
            if time_limit == 1800:
                self.add_portfolio_values()


        new_props_file = os.path.abspath(os.path.join(self.props.filename, '..', '..', 'progress-oracle-eval', 'properties'))
        print new_props_file
        tools.remove(new_props_file)
        tools.makedirs(os.path.dirname(new_props_file))
        self.props.filename = new_props_file
        self.props.update(self.new_props)
        for run_id, run in self.props.items():
            total_time = run.get('total_time')
            if total_time == self.time_unsolved:
                del self.props[run_id]['total_time']
        self.props.write()
        return markup + str(table)

    def add_portfolio_values(self):
        config = 'uniform_portfolio'
        for domain, problem in self.problems:
            run_id = '%s-%s-%s' % (config, domain, problem)
            run = {}
            run['domain'] = domain
            run['problem'] = problem
            run['config'] = config
            times = self.get_total_times(domain, problem)
            timeout = self.limit_search_time / len(self.configs)
            solved = any(t <= timeout for t in times)
            run['coverage'] = int(solved)
            if solved:
                run['total_time'] = get_mean_portfolio_time(times, timeout)
            self.new_props[run_id] = run

    def get_table_row(self, total_time_limit):
        row = {}

        for config in self.configs:
            row[config] = self.get_coverage(config)

        row['uniform portfolio'] = self.get_portfolio_coverage(self.uniform_limits)
        #markup += '\n\nExpected random success: %.2f\n' % (1 / len(self.configs))

        #TODO: Report times for portfolio by averaging over the times it takes to solve a problem for all possible config orders


        for selector in self.selectors:
            if len(self.configs) * selector.timeout > self.limit_search_time:
                continue
            selection = {}
            for domain, problem in self.problems:
                runs = self.get_runs(domain, problem)
                selection[(domain, problem)] = selector.select_for_problem(runs)

            evaluation, corrects, incorrects, coverage, cum_time, mean_runtime_factor = self.evaluate(selection,
                        selector, self.limit_search_time - (len(self.configs) * selector.timeout))
            #success = corrects / (corrects + incorrects) if corrects + incorrects > 0 else 0
            #markup += ('=== %s ===\nCorrect: %d, False: %d, Success: %.2f, '
            #           'Coverage: %d, Mean runtime factor: %.2f\n%s\n' % (
            #        selector.name, corrects, incorrects, success,
            #        coverage, mean_runtime_factor,
            #        ''#self.get_table(selection, evaluation)
            #        ))
            row[selector.name] = coverage
        return row

    def get_table(self, selection, evaluation):
        table = Table(highlight=False)
        for domain, problem in self.problems:
            for index, config in enumerate(self.configs):
                selected = (config == selection[(domain, problem)])
                correct = evaluation.get((domain, problem))
                run = self.get_run(config, domain, problem)
                text = '%s -> %.2f' % (raw(run['f_values']), run.get('total_time'))
                if selected:
                    color = COLORS[correct]
                    text = '{{%s|color:%s}}' % (text, color)
                table.add_cell(probname(domain, problem), config, text)

        return str(table)
