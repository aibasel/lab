"""
Detailed syntax explanations are available at
http://alfons.informatik.uni-freiburg.de/downward/PlannerUsage
"""

# Eager A* search with landmark-cut heuristic (previously configuration ou)
lmcut = ["--search", "astar(lmcut())"]

fF = ["--heuristic", "hff=ff()", "--search", "lazy_greedy(hff, preferred=hff)"]

yY = ["--heuristic", "hcea=cea()", "--search", "lazy_greedy(hcea, preferred=hcea)"]

lama = ["--heuristic",
"hlm,hff=lm_ff_syn(lm_rhw(reasonable_orders=true,lm_cost_type=2,cost_type=2))",
"--search",
"iterated([lazy_greedy([hff,hlm],preferred=[hff,hlm]),"
"lazy_wastar([hff,hlm],preferred=[hff,hlm],w=5),"
"lazy_wastar([hff,hlm],preferred=[hff,hlm],w=3),"
"lazy_wastar([hff,hlm],preferred=[hff,hlm],w=2),"
"lazy_wastar([hff,hlm],preferred=[hff,hlm],w=1)],"
"repeat_last=true)"]

blind = ["--search", "astar(blind())"]

def pdb_max_states(max_states):
    return ('pdb%d' % max_states,
            ['--search', 'astar(pdb(max_states=%d))' % max_states])

def ipdbi(imp):
    return ("ipdbi%d" % imp, ["--search", "astar(ipdb(min_improvement=%d))" % imp])

seq_opt_fdss_1 = ["ipc", "seq-opt-fdss-1", "--plan-file", "sas_plan"]
lama11 = ["ipc", "seq-sat-lama-2011", "--plan-file", "sas_plan"]

def ipc_optimal_subset():
    return [
        ("blind", ["--search", "astar(blind())"]),
        ("hmax",  ["--search", "astar(hmax())"]),
        ("lmcut", ["--search", "astar(lmcut())"]),
        ]

# Used for debugging purposes
multiple_plans = [
"--heuristic", "hlm,hff=lm_ff_syn(lm_rhw(reasonable_orders=false,lm_cost_type=2,cost_type=2))",
"--heuristic", "hadd=add()",
"--search", "iterated([lazy_greedy([hadd]),lazy_wastar([hff,hlm],preferred=[hff,hlm],w=2)],"
"repeat_last=false)"]

# Used for debugging purposes
iterated_search = [
"--heuristic", "hadd=add()",
"--search", "iterated([lazy_greedy([hadd]),lazy_wastar([hadd])],repeat_last=false)"]
