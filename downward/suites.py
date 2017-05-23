# -*- coding: utf-8 -*-
#
# downward uses the lab package to conduct experiments with the
# Fast Downward planning system.
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

from lab import tools


class Domain(object):
    def __init__(self, benchmarks_dir, domain):
        self.domain = domain
        directory = os.path.join(benchmarks_dir, domain)
        problem_files = tools.natural_sort([
            p for p in os.listdir(directory)
            if 'domain' not in p and not p.endswith('.py')])
        self.problems = [
            Problem(benchmarks_dir, domain, problem)
            for problem in problem_files]

    def __str__(self):
        return self.domain

    def __repr__(self):
        return '<Domain %s>' % self.domain

    def __hash__(self):
        return hash(self.domain)

    def __cmp__(self, other):
        return cmp(self.domain, other.domain)

    def __iter__(self):
        return iter(self.problems)


class Problem(object):
    def __init__(self, benchmarks_dir, domain, problem,
            domain_file=None, problem_file=None, properties=None):
        """
        *domain* and *problem* are the display names of the domain and
        problem, *domain_file* and *problem_file* are paths to the
        respective files on the disk. If the latter are not specified,
        they will be automatically generated according to the following
        naming conventions: both files are searched in the directory
        *benchmarks_dir*/*domain*. The default filename of the problem
        is *problem* and the domain file is search for under the names
        'domain.pddl', the base problem name followed by '-domain.pddl'
        or the full problem name preceeded by 'domain_'.

        *properties* may be a dictionary of entries that should be
        added to the properties file of each run that uses this
        problem. ::

        suite = [
            Problem(None, 'gripper-original', 'prob01.pddl',
                '/path/to/original/domain.pddl', '/path/to/original/problem.pddl',
                properties={'relaxed': False}),
            Problem(None, 'gripper-relaxed', 'prob01.pddl',
                '/path/to/relaxed/domain.pddl', '/path/to/relaxed/problem.pddl',
                properties={'relaxed': True}),
        ]
        """
        self.domain = domain
        self.problem = problem

        self.domain_file = domain_file
        if self.domain_file is None:
            domain_basenames = [
                'domain.pddl',
                self.problem[:3] + '-domain.pddl',
                'domain_' + self.problem,
            ]
            domain_dir = os.path.join(benchmarks_dir, self.domain)
            self.domain_file = tools.find_file(domain_basenames, domain_dir)

        self.problem_file = problem_file or os.path.join(
                benchmarks_dir, self.domain, self.problem)

        self.properties = properties or {}
        self.properties.set_default('domain', self.domain)
        self.properties.set_default('problem', self.problem)

    def __str__(self):
        return '%s:%s' % (self.domain, self.problem)

    def __repr__(self):
        return '<Problem %s:%s>' % (self.domain_file, self.problem_file)

    def __hash__(self):
        return hash((self.domain_file, self.problem_file))

    def __cmp__(self, other):
        return cmp((self.domain_file, self.problem_file),
                   (other.domain_file, other.problem_file))


def _generate_problems(benchmarks_dir, description):
    """
    Descriptions are either domains (e.g., "gripper") or problems
    (e.g., "gripper:prob01.pddl").
    """
    if isinstance(description, Problem):
        yield description
    elif isinstance(description, Domain):
        for problem in description:
            yield problem
    elif ':' in description:
        domain_name, problem_name = description.split(':', 1)
        yield Problem(benchmarks_dir, domain_name, problem_name)
    else:
        for problem in Domain(benchmarks_dir, description):
            yield problem


def build_suite(benchmarks_dir, descriptions):
    """
    *descriptions* must be a list of domain or problem descriptions::

        build_suite(benchmarks_dir, ["gripper", "grid:prob01.pddl"])

    """
    result = []
    for description in descriptions:
        result.extend(_generate_problems(benchmarks_dir, description))
    return result
