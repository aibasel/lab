# -*- coding: utf-8 -*-
#
# downward uses the lab package to conduct experiments with the
# Fast Downward planning system.
#
# Copyright (C) 2012  Jendrik Seipp (jendrikseipp@web.de)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import re

from lab import tools


class Repository(object):
    def __init__(self, benchmarks_dir):
        domains = [d for d in os.listdir(benchmarks_dir)
                   if not d.startswith(".")]
        domains.sort()
        self.domains = [Domain(domain) for domain in domains]

    def __iter__(self):
        return iter(self.domains)


class Domain(object):
    def __init__(self, benchmarks_dir, domain):
        self.domain = domain
        self.directory = os.path.join(benchmarks_dir, domain)
        problems = os.listdir(self.directory)
        problems = tools.natural_sort([p for p in problems
                                       if "domain" not in p and
                                       not p.startswith(".")])
        tools.natural_sort(problems)
        self.problems = [Problem(benchmarks_dir, domain, problem)
                         for problem in problems]

    def __str__(self):
        return self.domain

    def __repr__(self):
        return "<Domain %s>" % self.domain

    def __hash__(self):
        return hash(self.domain)

    def __cmp__(self, other):
        return cmp(self.domain, other.domain)

    def __iter__(self):
        return iter(self.problems)


class Problem(object):
    def __init__(self, benchmarks_dir, domain, problem):
        self.benchmarks_dir = benchmarks_dir
        self.domain = domain
        self.problem = problem

    def __str__(self):
        return "%s:%s" % (self.domain, self.problem)

    def __repr__(self):
        return "<Problem %s:%s>" % (self.domain, self.problem)

    def __hash__(self):
        return hash((self.domain, self.problem))

    def __cmp__(self, other):
        return cmp((self.domain, self.problem), (other.domain, other.problem))

    def problem_file(self):
        return os.path.join(self.benchmarks_dir, self.domain, self.problem)

    def domain_file(self):
        domain_basenames = ["domain.pddl",
                            self.problem[:4] + "domain.pddl",
                            self.problem[:3] + "-domain.pddl",
                            "domain_" + self.problem]
        domain_dir = os.path.join(self.benchmarks_dir, self.domain)
        return tools.find_file(domain_basenames, domain_dir)


def generate_problems(benchmarks_dir, description):
    """
    Descriptions have the form:

    gripper:prob01.pddl
    gripper
    TEST
    """
    # Allow writing SUITE_NAME_FIRST
    if description.endswith('_FIRST'):
        description = description.replace('_FIRST', '_1TO1')
    range_expr = re.compile(r'.+_([-]?\d+)TO([-]?\d+)', re.IGNORECASE)
    range_result = range_expr.search(description)

    if '.py:' in description:
        filename, rest = description.split(':', 1)
        description = rest
    else:
        filename = __file__

    module = tools.import_python_file(filename)
    module_dict = module.__dict__

    if range_result:
        # Allow writing SUITE_NAME_<NUMBER>TO<NUMBER>
        # This will work for all suites that only list domains and will
        # return the problems in that range of each domain
        start = int(range_result.group(1))
        end = int(range_result.group(2))
        #assert start >= 1, start
        #assert end >= start, (start, end)
        suite_name, numbers = description.rsplit('_', 1)
        suite_func = module_dict.get(suite_name, None)
        func_name = "suite_%s" % suite_name.lower()
        if suite_func is None:
            suite_func = module_dict.get(func_name, None)
        if not suite_func:
            raise SystemExit("unknown suite: %s" % func_name)
        for domain_name in suite_func():
            domain = Domain(benchmarks_dir, domain_name)
            for problem in domain.problems[start - 1:end]:
                yield problem
    elif isinstance(description, Problem):
        yield description
    elif isinstance(description, Domain):
        for problem in description:
            yield problem
    elif description.isupper() or description in module_dict:
        suite_func = module_dict.get(description, None)
        func_name = "suite_%s" % description.lower()
        if suite_func is None:
            suite_func = module_dict.get(func_name, None)
        if suite_func is None:
            raise SystemExit("unknown suite: %s" % func_name)
        for element in suite_func():
            for problem in generate_problems(benchmarks_dir, element):
                yield problem
    elif ":" in description:
        domain_name, problem_name = description.split(":", 1)
        yield Problem(benchmarks_dir, domain_name, problem_name)
    else:
        for problem in Domain(benchmarks_dir, description):
            yield problem


def build_suite(benchmarks_dir, descriptions):
    result = []
    for description in descriptions:
        result.extend(generate_problems(benchmarks_dir, description))
    return result


def suite_ipc_one_to_five():
    # All IPC1-5 domains, including the trivial Movie.
    return [
        "airport", "assembly", "blocks", "depot", "driverlog",
        "freecell", "grid", "gripper", "logistics00", "logistics98",
        "miconic", "miconic-fulladl", "miconic-simpleadl", "movie", "mprime",
        "mystery", "openstacks", "optical-telegraphs", "pathways",
        "philosophers", "pipesworld-notankage", "pipesworld-tankage",
        "psr-large", "psr-middle", "psr-small", "rovers", "satellite",
        "schedule", "storage", "tpp", "trucks", "zenotravel",
    ]

def suite_ipc08_common():
    return [
        "parcprinter-08-strips",
        "pegsol-08-strips",
        "scanalyzer-08-strips",
    ]

def suite_ipc08_opt_only():
    return [
        'elevators-opt08-strips',
        'openstacks-opt08-adl',
        'openstacks-opt08-strips',
        'sokoban-opt08-strips',
        'transport-opt08-strips',
        'woodworking-opt08-strips',
    ]

def suite_ipc08_opt_only_strips():
    return [
        'elevators-opt08-strips',
        'openstacks-opt08-strips',
        'sokoban-opt08-strips',
        'transport-opt08-strips',
        'woodworking-opt08-strips',
    ]

def suite_ipc08_sat_only():
    return [
        'elevators-sat08-strips',
        'openstacks-sat08-strips',
        'openstacks-sat08-adl',
        'sokoban-sat08-strips',
        'transport-sat08-strips',
        'woodworking-sat08-strips',
        # TODO: cyber-security is missing
    ]

def suite_ipc08_sat_only_strips():
    return [
        'elevators-sat08-strips',
        'openstacks-sat08-strips',
        'sokoban-sat08-strips',
        'transport-sat08-strips',
        'woodworking-sat08-strips',
        # TODO: cyber-security is missing
    ]

def suite_ipc08_opt():
    return suite_ipc08_common() + suite_ipc08_opt_only()

def suite_ipc08_opt_strips():
    return suite_ipc08_common() + suite_ipc08_opt_only_strips()

def suite_ipc08_sat():
    return suite_ipc08_common() + suite_ipc08_sat_only()

def suite_ipc08_sat_strips():
    return suite_ipc08_common() + suite_ipc08_sat_only_strips()

def suite_ipc08_all():
    return (suite_ipc08_common() +
            suite_ipc08_opt_only() +
            suite_ipc08_sat_only())

def suite_ipc08_all_strips():
    return (suite_ipc08_common() +
            suite_ipc08_opt_only_strips() +
            suite_ipc08_sat_only_strips())

def suite_ipc11_opt():
    return [
        "barman-opt11-strips",
        "elevators-opt11-strips",
        "floortile-opt11-strips",
        "nomystery-opt11-strips",
        "openstacks-opt11-strips",
        "parcprinter-opt11-strips",
        "parking-opt11-strips",
        "pegsol-opt11-strips",
        "scanalyzer-opt11-strips",
        "sokoban-opt11-strips",
        "tidybot-opt11-strips",
        "transport-opt11-strips",
        "visitall-opt11-strips",
        "woodworking-opt11-strips",
    ]

def suite_ipc11_sat():
    return [
        "barman-sat11-strips",
        "elevators-sat11-strips",
        "floortile-sat11-strips",
        "nomystery-sat11-strips",
        "openstacks-sat11-strips",
        "parcprinter-sat11-strips",
        "parking-sat11-strips",
        "pegsol-sat11-strips",
        "scanalyzer-sat11-strips",
        "sokoban-sat11-strips",
        "tidybot-sat11-strips",
        "transport-sat11-strips",
        "visitall-sat11-strips",
        "woodworking-sat11-strips",
    ]

def suite_ipc11_all():
    return suite_ipc11_opt() + suite_ipc11_sat()

def suite_interesting():
    # A domain is boring if all planners solve all tasks in < 1 sec.
    # We include logistics00 even though it has that property because
    # we merge its results with logistics98 (which doesn't).
    boring = set(["gripper", "miconic", "miconic-simpleadl", "movie"])
    return [domain for domain in suite_all() if domain not in boring]

def suite_unsolvable():
    # TODO: Add other unsolvable problems (Miconic-FullADL).
    return ["mystery:prob%02d.pddl" % index
            for index in [4, 5, 7, 8, 12, 16, 18, 21, 22, 23, 24]]

def suite_test():
    # Three smallish domains for quick tests.
    return ["grid", "gripper", "blocks"]

def suite_minitest():
    return ["gripper:prob01.pddl", "gripper:prob02.pddl",
            "gripper:prob03.pddl", "zenotravel:pfile1",
            "zenotravel:pfile2", "zenotravel:pfile3", ]

def suite_tinytest():
    return ["gripper:prob01.pddl", "trucks-strips:p01.pddl",
            "trucks:p01.pddl", "psr-middle:p01-s17-n2-l2-f30.pddl"]


def suite_lmcut_domains():
    return [
        "airport",
        "blocks",
        "depot",
        "driverlog",
        "freecell",
        "grid",
        "gripper",
        "logistics00",
        "logistics98",
        "miconic",
        "mprime",
        "mystery",
        "openstacks-strips",
        "pathways-noneg",
        "pipesworld-notankage",
        "pipesworld-tankage",
        "psr-small",
        "rovers",
        "satellite",
        "tpp",
        "trucks-strips",
        "zenotravel",
    ]

def suite_strips():
    return suite_lmcut_domains() + suite_ipc08_all_strips()

def suite_strips_ipc12345():
    ipc08 = set(suite_ipc08_all())
    return [domain for domain in suite_strips() if domain not in ipc08]

def suite_optimal():
    return suite_lmcut_domains() + suite_ipc08_opt_strips()

def suite_optimal_with_ipc11():
    return suite_optimal() + suite_ipc11_opt()

def suite_satisficing_with_ipc11():
    domains = suite_ipc_one_to_five() + suite_lmcut_domains()
    domains += suite_ipc08_sat() + suite_ipc11_sat()
    return list(sorted(set(domains)))

def suite_all():
    domains = suite_ipc_one_to_five() + suite_lmcut_domains()
    domains += suite_ipc08_all() + suite_ipc11_all()
    return list(sorted(set(domains)))


def suite_five_per_domain(benchmarks_dir):
    for domain in Repository(benchmarks_dir):
        problems = list(domain)
        for item in select_evenly_spread(problems, 5):
            yield item


def select_evenly_spread(seq, num_items):
    """Return num_items many items of seq, spread evenly.
    If seq is shorter than num_items, include all items.
    Otherwise, include first and last items and spread evenly in between.
    (If num_items is 1, only include first item.)

    >>> select_evenly_spread("abcdef", 3)
    ['a', 'd', 'f']
    """
    if len(seq) <= num_items:
        return seq
    if num_items == 1:
        return [seq[0]]
    step_size = (len(seq) - 1) / float(num_items - 1)
    float_indices = [i * step_size for i in range(num_items)]
    return [seq[int(round(index))] for index in float_indices]


# ------- Configs ------------------------------------------------------

def config_suite_core_optimal():
    return {
        # A*
        'astar_blind': [
            '--search',
            'astar(blind)'],
        'astar_h2': [
            '--search',
            'astar(hm(2))'],
        'astar_ipdb': [
            '--search',
            'astar(ipdb)'],
        'astar_lmcount_lm_merged_rhw_hm': [
            '--search',
            'astar(lmcount(lm_merged([lm_rhw(),lm_hm(m=1)]),admissible=true),mpd=true)'],
        'astar_lmcut': [
            '--search',
            'astar(lmcut)'],
        'astar_hmax': [
            '--search',
            'astar(hmax)'],
        'astar_merge_and_shrink_bisim': [
            '--search',
            'astar(merge_and_shrink(merge_strategy=merge_linear_reverse_level,'
            + 'shrink_strategy=shrink_bisimulation(max_states=200000,greedy=false,'
            + 'group_by_h=true)))'],
        'astar_merge_and_shrink_greedy_bisim': [
            '--search',
            'astar(merge_and_shrink(merge_strategy=merge_linear_reverse_level,'
            + 'shrink_strategy=shrink_bisimulation(max_states=infinity,threshold=1,'
            + 'greedy=true,group_by_h=false)))'],
        'astar_selmax_lmcut_lmcount': [
            '--search',
            'astar(selmax([lmcut(),lmcount(lm_merged([lm_hm(m=1),lm_rhw()]),'
            + 'admissible=true)],training_set=1000),mpd=true)'],
    }

def config_suite_core_satisficing():
    return {
        # A*
        'astar_goalcount': [
            '--search',
            'astar(goalcount)'],
        # eager greedy
        'eager_greedy_ff': [
            '--heuristic',
            'h=ff()',
            '--search',
            'eager_greedy(h, preferred=h)'],
        'eager_greedy_add': [
            '--heuristic',
            'h=add()',
            '--search',
            'eager_greedy(h, preferred=h)'],
        'eager_greedy_cg': [
            '--heuristic',
            'h=cg()',
            '--search',
            'eager_greedy(h, preferred=h)'],
        'eager_greedy_cea': [
            '--heuristic',
            'h=cea()',
            '--search',
            'eager_greedy(h, preferred=h)'],
        # lazy greedy
        'lazy_greedy_ff': [
            '--heuristic',
            'h=ff()',
            '--search',
            'lazy_greedy(h, preferred=h)'],
        'lazy_greedy_add': [
            '--heuristic',
            'h=add()',
            '--search',
            'lazy_greedy(h, preferred=h)'],
        'lazy_greedy_cg': [
            '--heuristic',
            'h=cg()',
            '--search',
            'lazy_greedy(h, preferred=h)'],
    }

def config_suite_ipc_optimal():
    return {
        'seq_opt_merge_and_shrink': ['ipc', 'seq-opt-merge-and-shrink'],
        'seq_opt_fdss_1': ['ipc', 'seq-opt-fdss-1'],
        'seq_opt_fdss_2': ['ipc', 'seq-opt-fdss-2'],
    }

def config_suite_ipc_satisficing():
    return {
        'seq_sat_lama_2011': ['ipc', 'seq-sat-lama-2011'],
        'seq_sat_fdss_1': ['ipc', 'seq-sat-fdss-1'],
        'seq_sat_fdss_2': ['ipc', 'seq-sat-fdss-2'],
    }

def config_suite_extended_optimal():
    return {
        # A*
        'astar_lmcount_lm_merged_rhw_hm_no_order': [
            '--search',
            'astar(lmcount(lm_merged([lm_rhw(),lm_hm(m=1)]),admissible=true),mpd=true)'],
        # pareto open list
        'pareto_lmcut': [
            '--heuristic',
            'h=lmcut()',
            '--search',
            'eager(pareto([sum([g(), h]), h]), reopen_closed=true, pathmax=false,'
            + 'progress_evaluator=sum([g(), h]))'],
        # bucket-based open list
        'bucket_lmcut': [
            '--heuristic',
            'h=lmcut()',
            '--search',
            'eager(single_buckets(h), reopen_closed=true, pathmax=false)'],
    }

def config_suite_extended_satisficing():
    return {
        # eager greedy
        'eager_greedy_alt_ff_cg': [
            '--heuristic',
            'hff=ff()',
            '--heuristic',
            'hcg=cg()',
            '--search',
            'eager_greedy(hff,hcg,preferred=[hff,hcg])'],
        'eager_greedy_ff_no_pref': [
            '--search',
            'eager_greedy(ff())'],
        # lazy greedy
        'lazy_greedy_alt_cea_cg': [
            '--heuristic',
            'hcea=cea()',
            '--heuristic',
            'hcg=cg()',
            '--search',
            'lazy_greedy(hcea,hcg,preferred=[hcea,hcg])'],
        'lazy_greedy_ff_no_pref': [
            '--search',
            'lazy_greedy(ff())'],
        'lazy_greedy_cea': [
            '--heuristic',
            'h=cea()',
            '--search',
            'lazy_greedy(h, preferred=h)'],
        # lazy wA*
        'lazy_wa3_ff': [
            '--heuristic',
            'h=ff()',
            '--search',
            'lazy_wastar(h,w=3,preferred=h)'],
        # eager wA*
        'eager_wa3_cg': [
            '--heuristic',
            'h=cg()',
            '--search',
            'eager(single(sum([g(),weight(h,3)])),preferred=h)'],
        # ehc
        'ehc_ff': [
            '--search',
            'ehc(ff())'],
        # iterated
        'iterated_wa_merge_and_shrink': [
            '--heuristic',
            'h=merge_and_shrink()',
            '--search',
            'iterated([lazy_wastar(h,w=10), lazy_wastar(h,w=5), lazy_wastar(h,w=3),'
            + 'lazy_wastar(h,w=2), lazy_wastar(h,w=1)])'],
    }

def config_suite_optimal(use_core_configs=True, use_ipc_configs=True,
                         use_extended_configs=False):
    configs = {}
    if use_core_configs:
        configs.update(config_suite_core_optimal())
    if use_ipc_configs:
        configs.update(config_suite_ipc_optimal())
    if use_extended_configs:
        configs.update(config_suite_extended_optimal())
    return configs

def config_suite_satisficing(use_core_configs=True, use_ipc_configs=True,
                             use_extended_configs=False):
    configs = {}
    if use_core_configs:
        configs.update(config_suite_core_satisficing())
    if use_ipc_configs:
        configs.update(config_suite_ipc_satisficing())
    if use_extended_configs:
        configs.update(config_suite_extended_satisficing())
    return configs
