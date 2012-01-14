#! /usr/bin/env python
"""
Regular expressions and functions for parsing planning experiments
"""

from __future__ import division

import re
import math
from collections import defaultdict

# The lab directory is added automatically in the Experiment constructor
from lab.parser import Parser
from lab import tools


def check(props):
    if props.get('translate_error') == 1:
        msg = 'Translator error without preprocessor error'
        assert props.get('preprocess_error') == 1, msg

    if props.get('cost') is not None:
        assert props.get('search_time') is not None, 'cost without search_time'


# Search functions ------------------------------------------------------------

def _get_states_pattern(attribute, name):
    return (attribute, re.compile(r'%s (\d+) state\(s\)\.' % name), int)


ITERATIVE_PATTERNS = [
    ('cost', re.compile(r'Plan cost: (.+)'), int),
    _get_states_pattern('dead_ends', 'Dead ends:'),
    _get_states_pattern('evaluations', 'Evaluated'),
    _get_states_pattern('expansions', 'Expanded'),
    _get_states_pattern('generated', 'Generated'),
    # We exclude lines like "Initial state h value: 1147184/1703241." that stem
    # from multi-heuristic search.
    ('initial_h_value', re.compile(r'Initial state h value: (\d+)\.'), int),
    ('plan_length', re.compile(r'Plan length: (\d+)'), int),
    # We cannot include " \[t=.+s\]" in the regex, because older versions don't
    # have this information in the log.
    ('search_time', re.compile(r'Actual search time: (.+?)s'), float)
    ]


CUMULATIVE_PATTERNS = [
    # This time we parse the cumulative values
    _get_states_pattern('dead_ends', 'Dead ends:'),
    _get_states_pattern('evaluations', 'Evaluated'),
    _get_states_pattern('expansions', 'Expanded'),
    _get_states_pattern('generated', 'Generated'),
    ('search_time', re.compile(r'^Search time: (.+)s$'), float),
    ('total_time', re.compile(r'^Total time: (.+)s$'), float),
    ('memory', re.compile(r'Peak memory: (.+) KB'), int),
    # For iterated searches we discard any h values. Here we will not find
    # anything before the "cumulative" line and stop the search. For single
    # searches we will find the h value if it isn't a multi-heuristic search.
    ('initial_h_value', re.compile(r'Initial state h value: (\d+)\.'), int),
    ]


def get_iterative_results(content, props):
    """
    In iterative search some attributes like plan cost can have multiple
    values, i.e. one value for each iterative search. We save those values in
    lists.
    """
    values = defaultdict(list)

    for line in content.splitlines():
        # At the end of iterative search some statistics are printed and we do
        # not want to parse those here.
        if line == 'Cumulative statistics:':
            break
        for name, pattern, cast in ITERATIVE_PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            values[name].append(cast(match.group(1)))
            # We can break here, because each line contains only one value
            break

    # After iterative search completes there is another line starting with
    # "Actual search time" that just states the cumulative search time.
    # In order to let all lists have the same length, we omit that value here.
    if len(values['search_time']) > len(values['expansions']):
        values['search_time'].pop()

    # Check that some lists have the same length
    def same_length(group):
        return len(set(len(x) for x in group)) == 1

    group1 = ('cost', 'plan_length')
    group2 = ('expansions', 'generated', 'search_time')
    assert same_length(values[x] for x in group1), values
    assert same_length(values[x] for x in group2), values

    for name, items in values.items():
        props[name + '_all'] = items

    for attr in ['cost', 'plan_length']:
        if values[attr]:
            props[attr] = min(values[attr])


def get_cumulative_results(content, props):
    """
    Some cumulative results are printed at the end of the logfile. We revert
    the content to make a search for those values much faster. We would have to
    convert the content anyways, because there's no real telling if those
    values talk about a single or a cumulative result. If we start parsing at
    the bottom of the file we know that the values are the cumulative ones.
    """
    reverse_content = list(reversed(content.splitlines()))
    for name, pattern, cast in CUMULATIVE_PATTERNS:
        for line in reverse_content:
            # There will be no cumulative values above this line
            if line == 'Cumulative statistics:':
                break
            match = pattern.search(line)
            if not match:
                continue
            props[name] = cast(match.group(1))


def set_search_time(content, props):
    """
    If iterative search has accumulated single search times, but the total
    search time was not written (due to a possible timeout for example), we
    set search_time to be the sum of the single search times.
    """
    if 'search_time' in props:
        return
    search_time_all = props.get('search_time_all', [])
    # Do not write search_time if no iterative search_time has been found.
    if search_time_all:
        props['search_time'] = math.fsum(search_time_all)


def completely_explored(content, props):
    props['completely_explored'] = ('Completely explored state space -- '
                                    'no solution!' in content)


def get_status(content, props):
    if 'plan_length' in props or 'cost' in props:
        props['status'] = 'ok'
    elif props.get('completely_explored', False):
        props['status'] = 'failure'
    elif 'does not support' in content:
        props['status'] = 'unsupported'
    else:
        props['status'] = 'unsolved'


def coverage(content, props):
    props['coverage'] = int('plan_length' in props or 'cost' in props)


def check_memory(content, props):
    """
    Set "memory" to the max value if it was exceeded and "-1 KB" was reported
    """
    memory = props.get('memory')
    memory_limit = props.get('limit_search_memory', None)
    if memory == -1:
        if memory_limit is not None:
            # Turn into KB
            memory_limit *= 1024
        props['memory'] = memory_limit


def scores(content, props):
    """
    Some reported results are measured via scores from the
    range 0-1, where best possible performance in a task is
    counted as 1, while failure to solve a task and worst
    performance are counted as 0
    """
    def log_score(value, min_bound, max_bound, min_score):
        if value is None:
            return 0
        if value < min_bound:
            value = min_bound
        if value > max_bound:
            value = max_bound
        raw_score = math.log(value) - math.log(max_bound)
        best_raw_score = math.log(min_bound) - math.log(max_bound)
        score = min_score + (1 - min_score) * (raw_score / best_raw_score)
        return round(score * 100, 2)

    # Maximum memory in KB
    max_memory = (props.get('limit_search_memory') or 2048) * 1024

    props.update({'score_expansions': log_score(props.get('expansions'),
                    min_bound=100, max_bound=1000000, min_score=0.0),
            'score_evaluations': log_score(props.get('evaluations'),
                    min_bound=100, max_bound=1000000, min_score=0.0),
            'score_memory': log_score(props.get('memory'),
                    min_bound=2000, max_bound=max_memory, min_score=0.0),
            'score_total_time': log_score(props.get('total_time'),
                    min_bound=1.0, max_bound=1800.0, min_score=0.0),
            'score_search_time': log_score(props.get('search_time'),
                    min_bound=1.0, max_bound=1800.0, min_score=0.0),
           })


def check_min_values(content, props):
    """
    Ensure that times are at least 0.1s if they are present in log
    """
    for time in ['search_time', 'total_time']:
        sec = props.get(time, None)
        if sec is not None:
            sec = max(sec, 0.1)
            props[time] = sec

# -----------------------------------------------------------------------------


def quality(problem_runs):
    min_cost = tools.minimum(run.get('cost') for run in problem_runs)
    for run in problem_runs:
        cost = run.get('cost')
        if cost is None:
            quality = 0.0
        elif cost == 0:
            assert min_cost == 0
            quality = 1.0
        else:
            quality = min_cost / cost
        run['quality'] = round(quality, 4)


def get_bisimulation_results(content, props):
    # Sets "mas_complete" to 1 if a M&S heuristic was computed completely
    # and resulted in an abstraction with finite goal distance for the
    # initial state; to 0 otherwise.
    #
    # If the abstraction computation already shows unsolvability, then
    # we stop the process prematurely, so it is a bit hard to compare
    # this to other abstraction methods in a clean fashion. Hence, in
    # that case, we don't gather complete statistics but merely set
    # "mas_unsolvable" to 1. These two variables are always set; all
    # other variables are only set if mas_complete == 1 (which implies
    # mas_unsolvable == 0).

    # The code below assumes that complete M&S computations perform at
    # least one merge step -- this is not necessarily true since we
    # could have a problem with only have 1 state variable. However,
    # in our benchmark collection, all such problems are unsolvable ones,
    # so we don't need to implement this case.

    # All following variables here are only set if mas_complete == 1.
    # The code assumes implicitly that only a single abstraction is
    # computed. Otherwise, it will probably raise an assertion.

    # Explanation of variables:
    # - mas_max_states, mas_max_arcs: number of abstract states and
    #   transitions in the largest abstraction that is computed during
    #   M&S construction (parallel arcs with different labels are counted
    #   multiple times)
    # - mas_max_states_vars: the number of represented variables (in
    #   the range 1..preprocessor_variables) in the merged abstraction
    #   which has the maximum number of states; ties broken in favour
    #   of lower values. For example, value of "3" means that the
    #   second merged abstraction (which includes info from the first
    #   three variables) had the maximal number of states among all
    #   composites. (The idea of this variable is to check whether the
    #   largest abstractions are encountered at the end of the M&S
    #   process, closer to the middle, or somewhere else.)
    # - mas_max_arcs_vars: same, but for arcs instead of states
    # - mas_max_intermediate_states, mas_max_intermediate_arcs,
    #   mas_max_intermediate_states_vars, mas_max_intermediate_arcs_vars:
    #   Like the previous four variables, but includes "intermediate"
    #   abstractions, i.e. ones that are not yet bisimulated. This gives
    #   a better measure for peak memory consumption *during construction*.
    # - mas_final_states, mas_final_arcs: like mas_max_states and
    #   mas_max_arcs, but for the final abstraction in the chain.
    #   NOTE THE "HACK" COMMENTS BELOW -- the arc counts for the final
    #   abstraction are *unnormalized*. (Also affects mas_max_arcs and
    #   mas_max_arcs_vars!)
    # - mas_total_size: total number of table entries in the M&S lookup
    #   tables. This does not include the final "distance" lookup table,
    #   since that one is in principle redundant.
    # - mas_pdb_size: the size that a PDB for all variables would have
    #   (in other words, the number of syntactically correct states)
    #
    # Note: All the mas_max_... variables only maximize over all composite
    # abstractions, not the initial atomic abstractions (which should
    # be smaller except in really degenerate cases).

    variable_count = props["preprocessor_variables"]
    states = []
    intermediate_states = []
    arcs = []
    intermediate_arcs = []
    total_size = 0
    skip_next = False
    last_states = None
    last_arcs = None
    atomic_vars_seen = set()
    pdb_size = 1
    for line in content.splitlines():
        parts = line.split()
        if parts == ["Abstract", "problem", "is", "unsolvable!"]:
            # Task shown unsolvable during abstraction computation.
            # HACK: Treat these -- somewhat arbitrarily -- as if the M&S
            # heuristic could not be computed.
            props["mas_complete"] = int(False)
            props["mas_unsolvable"] = int(True)
            return
        if parts[:4] == ["Done", "initializing", "merge-and-shrink",
                         "heuristic"]:
            break
        if parts[:2] == ["Atomic", "abstraction"] and parts[4:5] == ["states,"]:
            var_desc = parts[2]
            if var_desc not in atomic_vars_seen:
                var_range = int(parts[3])
                total_size += var_range
                pdb_size *= var_range
                atomic_vars_seen.add(var_desc)
        if parts[:1] == ["Abstraction"] and parts[4:5] == ["states,"]:
            # print "***", parts
            num_vars = int(parts[1].lstrip("(").partition("/")[0])
            num_states = int(parts[3])
            num_arcs = int(parts[5].partition("/")[2])
            # There are three occurrences of abstraction statistics for
            # each composite. We determine which one we're at based on
            # the size of "intermediate_states", the size of "states",
            # and the number of variables mentioned.

            is_last_variable = num_vars == variable_count
            # HACK! The last composite is not normalized, so we treat it
            # a bit differently. Note that this messes up the final arc
            # numbers (and hence potentially also the maximum arc numbers!).

            if num_vars == len(intermediate_states) + 2:
                # First occurrence: update intermediate states
                # and representation size, since the number of states
                # here is also the size of the 2D look-up table for
                # this composite.
                assert num_vars == len(states) + 2
                total_size += num_states
                intermediate_states.append(num_states)
                intermediate_arcs.append(num_arcs)
                skip_next = True
            elif skip_next and not is_last_variable:
                # Second occurrence: this is already bisimulated, but
                # not yet normalized. Skip this, but remember
                # last_states and last_arcs below for assertions.
                skip_next = False
                assert num_states <= last_states
                assert num_arcs <= last_arcs
            else:
                # Third occurrence: this contains the results after
                # bisimulation and normalization
                assert num_vars == len(states) + 2
                if is_last_variable:
                    assert num_states <= last_states
                else:
                    assert num_states == last_states
                assert num_arcs <= last_arcs
                states.append(num_states)
                arcs.append(num_arcs)
            last_states = num_states
            last_arcs = num_arcs
    else:
        props["mas_complete"] = int(False)
        props["mas_unsolvable"] = int(False)
        return # incomplete run -- don't set variables

    assert len(states) == variable_count - 1
    assert len(arcs) == variable_count - 1
    assert len(intermediate_states) == variable_count - 1
    assert len(intermediate_arcs) == variable_count - 1

    max_states = max(states)
    max_arcs = max(arcs)
    props["mas_complete"] = int(True)
    props["mas_unsolvable"] = int(False)
    props["mas_max_states"] = max(states)
    props["mas_max_arcs"] = max(arcs)
    props["mas_max_states_vars"] = states.index(max(states)) + 2
    props["mas_max_arcs_vars"] = arcs.index(max(arcs)) + 2

    props["mas_max_intermediate_states"] = max(intermediate_states)
    props["mas_max_intermediate_arcs"] = max(intermediate_arcs)
    props["mas_max_intermediate_states_vars"] = intermediate_states.index(
        max(intermediate_states)) + 2
    props["mas_max_intermediate_arcs_vars"] = intermediate_arcs.index(
        max(intermediate_arcs)) + 2
    props["mas_final_states"] = states[-1]
    props["mas_final_arcs"] = arcs[-1]
    props["mas_total_size"] = total_size
    props["mas_pdb_size"] = pdb_size
    # print "+++", sorted((k, v) for k, v in props.iteritems()
    #                     if k.startswith("mas_"))


def get_error(content, props):
    if not content.strip():
        props["error"] = "none"
    elif "bad_alloc" in content:
        props["error"] = "memory"
    else:
        props["error"] = "unknown"


class SearchParser(Parser):
    def __init__(self):
        Parser.__init__(self)

        self.add_search_parsing()
        self.add_search_functions()

        self.set_check(check)
        self.postprocess_functions.append(quality)

    def add_search_parsing(self):
        self.add_pattern('landmarks', r'Discovered (\d+?) landmarks', type=int,
                         required=False)
        self.add_pattern('landmarks_generation_time',
                         r'Landmarks generation time: (.+)s', type=float,
                         required=False)

    def add_search_functions(self):
        #self.add_function(completely_explored)
        self.add_function(get_iterative_results)
        self.add_function(get_cumulative_results)
        self.add_function(check_memory)
        self.add_function(set_search_time)
        self.add_function(coverage)
        self.add_function(get_status)
        self.add_function(scores)
        #self.add_function(get_bisimulation_results)
        self.add_function(get_error, "run.err")
        self.add_function(check_min_values)


if __name__ == '__main__':
    parser = SearchParser()
    parser.parse()
