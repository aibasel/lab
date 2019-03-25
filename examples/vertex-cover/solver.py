#! /usr/bin/env python

"""
Example program that finds vertex covers.
"""

import argparse
import collections
import random
import re
import time


def get_edges(input_file):
    edges = []
    with open(input_file) as f:
        header = f.readline().strip()
        match = re.match(r"\S+ \S+ (\d+) (\d+)", header)
        num_edges = int(match.group(2))
        for _ in range(num_edges):
            line = f.readline().strip()
            parts = line.split()
            edge = set([int(v) for v in parts[1:]])
            assert len(edge) == 2
            edges.append(edge)
    return edges


def find_two_approximation(edges):
    cover = set()
    remaining_edges = edges[:]
    while remaining_edges:
        u, v = random.choice(edges)
        selected_edge = set([u, v])
        cover |= set([u, v])
        remaining_edges = [
            edge for edge in remaining_edges if not (edge & selected_edge)]
    return cover


def find_greedy_cover(edges):
    def find_vertex_greedily(remaining_edges):
        num_incident_edges = collections.defaultdict(int)
        for edge in remaining_edges:
            u, v, = edge
            num_incident_edges[u] += 1
            num_incident_edges[v] += 1
        return max(num_incident_edges, key=lambda v: num_incident_edges[v])

    cover = set()
    remaining_edges = edges[:]
    while remaining_edges:
        v = find_vertex_greedily(remaining_edges)
        cover.add(v)
        remaining_edges = [
            edge for edge in remaining_edges if v not in edge]
    return cover


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", help="path to DIMACS graph file")
    parser.add_argument("algorithm", choices=["2approx", "greedy"])
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args()


def main():
    args = parse_args()
    random.seed(args.seed)
    edges = get_edges(args.input_file)
    print("Algorithm: {}".format(args.algorithm))
    start_time = time.clock()
    if args.algorithm == "2approx":
        cover = find_two_approximation(edges)
    elif args.algorithm == "greedy":
        cover = find_greedy_cover(edges)
    else:
        raise ValueError("Unknown algorithm selected")
    solve_time = time.clock() - start_time
    print("Cover: {}".format(cover))
    print("Cover size: {}".format(len(cover)))
    print("Solve time: {}s".format(solve_time))


if __name__ == "__main__":
    main()
