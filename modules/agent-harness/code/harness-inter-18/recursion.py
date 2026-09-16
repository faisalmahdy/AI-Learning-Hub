"""Cap the sub-agent recursion depth, or a task that never decides it is done spawns an exponential swarm.

An agent that decomposes a hard task into sub-tasks, each handled by a sub-agent, builds a TREE of agents. If
every task spawns b sub-tasks, there are b agents at depth 1, b*b at depth 2, b^d at depth d -- the count grows
exponentially with depth. As long as the decomposition converges (leaf tasks are simple and stop spawning),
the tree is shallow and fine. The danger is a decomposition that never decides it is done: a task splits into
sub-tasks that are no simpler, each of which splits again, forever. With no depth cap, the harness happily
launches b^d agents at depth d -- hundreds, then thousands -- burning budget and rate limits, a self-inflicted
denial of service from a single request.

A depth cap fixes it. Refuse to spawn a sub-agent beyond a maximum depth; at the cap, a task must solve itself
or fail rather than decompose further. That turns an unbounded tree into a bounded one: the total number of
agents is the geometric sum 1 + b + b^2 + ... + b^D, a fixed number no matter how badly the decomposition
misbehaves. The cap does not make a bad decomposition good, but it converts an exponential blowup into a
bounded, debuggable failure -- the same reason a plain agent loop has an iteration limit, extended to the tree.

On this fixture each task spawns 3 sub-tasks. Capped at depth 3, the whole tree is 1+3+9+27 = 40 agents. An
uncapped run that drifted to depth 8 would be 1+3+...+3^8 = 9841 agents -- 246x more, with 6561 at the last
level alone. This computes both.

  --tree      the agent count at each depth, and where the cap cuts it off
  --totals    the total agents under the cap vs at the runaway depth
  --check     the cap bounds the tree to a geometric sum; uncapped growth is exponential

The branching, cap, and runaway depth are the fixture; every count is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "tree.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def agents_at_depth(b, d):
    """How many agents live at depth d: b^d."""
    return b ** d


def total_agents(b, max_depth):
    """All agents from the root (depth 0) down to max_depth: the geometric sum 1 + b + ... + b^max_depth."""
    return sum(b ** d for d in range(max_depth + 1))


def geometric_sum(b, max_depth):
    """Closed form of the total: (b^(max_depth+1) - 1) / (b - 1)."""
    return (b ** (max_depth + 1) - 1) // (b - 1)


# ----------------------------------------------------------------- printing

def tree_view(data):
    b, cap, run = data["branching"], data["depth_cap"], data["runaway_depth"]
    print("TREE — agents at each depth (branching %d, cap at depth %d)" % (b, cap))
    print("-" * 58)
    for d in range(run + 1):
        marker = "  <- CAP: no spawning past here" if d == cap else ("  (only reached without a cap)" if d > cap else "")
        print("  depth %d:  %6d agents%s" % (d, agents_at_depth(b, d), marker))
    print("-" * 58)
    print("  each level multiplies the count by %d; the cap stops it at depth %d." % (b, cap))


def totals_view(data):
    b, cap, run = data["branching"], data["depth_cap"], data["runaway_depth"]
    tc, tr = total_agents(b, cap), total_agents(b, run)
    print("TOTALS — total agents under the cap vs at the runaway depth")
    print("-" * 58)
    print("  capped at depth %d:   %6d agents" % (cap, tc))
    print("  runaway to depth %d:  %6d agents  (%dx more)" % (run, tr, tr // tc))
    print("-" * 58)
    print("  the cap turns an exponential swarm into a fixed budget.")


def check(data):
    print("SELF-TEST — the cap bounds the tree to a geometric sum; uncapped growth is exponential")
    print("-" * 100)
    b, cap, run = data["branching"], data["depth_cap"], data["runaway_depth"]
    tc, tr = total_agents(b, cap), total_agents(b, run)

    each_level_multiplies = all(agents_at_depth(b, d + 1) == b * agents_at_depth(b, d) for d in range(run))
    print("  each depth has b times the agents of the one above = %s" % each_level_multiplies)

    capped_is_geometric_sum = tc == geometric_sum(b, cap)
    print("  the capped total is the geometric sum = %s (%d = (b^%d-1)/(b-1))" % (capped_is_geometric_sum, tc, cap + 1))

    runaway_far_exceeds_capped = tr > tc * 100
    print("  the runaway tree dwarfs the capped one = %s (%d vs %d, %dx)" % (runaway_far_exceeds_capped, tr, tc, tr // tc))

    growth_is_exponential = agents_at_depth(b, run) == agents_at_depth(b, cap) * b ** (run - cap)
    print("  the per-depth count grows exponentially = %s (depth %d has %d agents)" % (growth_is_exponential, run, agents_at_depth(b, run)))

    whole_cap_tree_below_one_runaway_level = tc < agents_at_depth(b, run)
    print("  the entire capped tree is smaller than one runaway level = %s (%d < %d at depth %d)" % (whole_cap_tree_below_one_runaway_level, tc, agents_at_depth(b, run), run))

    ok = each_level_multiplies and capped_is_geometric_sum and runaway_far_exceeds_capped and growth_is_exponential and whole_cap_tree_below_one_runaway_level
    print("-" * 100)
    print("SELF-TEST %s  each_level_multiplies=%s  capped_is_geometric_sum=%s  runaway_far_exceeds_capped=%s  growth_is_exponential=%s  whole_cap_tree_below_one_runaway_level=%s"
          % ("PASS" if ok else "FAIL", each_level_multiplies, capped_is_geometric_sum, runaway_far_exceeds_capped, growth_is_exponential, whole_cap_tree_below_one_runaway_level))
    return ok


def main():
    p = argparse.ArgumentParser(description="Cap sub-agent recursion depth so a non-converging decomposition cannot spawn an exponential swarm.")
    p.add_argument("--tree", action="store_true")
    p.add_argument("--totals", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("branching=%d  depth_cap=%d  runaway_depth=%d  file=%s  (the tree shape is a fixture)"
          % (data["branching"], data["depth_cap"], data["runaway_depth"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.tree:
        tree_view(data)
    elif args.totals:
        totals_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
