"""Cap tool calls per tool, not just total steps -- or one runaway tool eats the whole run and starves the ones the task needs.

An agent loop needs a budget or it runs forever, and the obvious budget is a total cap on tool calls: stop after N. That
bounds the run, but it does not bound WHERE the budget goes. Agents get stuck in single-tool loops -- searching again and
again for something they never find, retrying a failing call, re-reading the same file -- and a runaway tool, issued
greedily up front, can consume the entire total budget before the agent ever reaches the tools the task actually
requires. The run stops at its cap, having done nothing but search, and the read and write the task needed never
happened. The total budget was spent; it was just spent entirely in one place.

A per-tool cap fixes the distribution. Give each tool its own ceiling, so no single tool can monopolize the run: once
search hits its cap, further search calls are refused (returned as an observation, so the agent moves on), and the
budget it would have burned is preserved for the other tools. The total cap still bounds the whole run; the per-tool
caps bound each tool within it, which is what keeps a loop in one tool from starving the rest. The two budgets are
complementary -- the total limits the run, the per-tool limits guarantee the run can spread across the tools a task
needs -- and a run that only has the total cap has no defense against a single tool eating all of it.

On this fixture the agent wants 12 searches plus one read and one write, the total budget is 10, and search is capped at
5. Allocated greedily against the total budget alone, search takes all 10 and read and write get 0 -- the task fails
because its required tools never ran. Allocated with the per-tool cap, search is bounded to 5, leaving room for read and
write to run once each (7 calls total, under budget), so both required tools execute and the task can succeed. This
computes both.

  --allocate   how the total-only budget vs the per-tool budget distributes calls across the tools
  --coverage   which tools actually run under each policy, and whether the required tools are covered
  --check      the total-only budget lets one tool consume it and starves the required tools; per-tool caps prevent it

The intended calls, budgets, and caps are the fixture; every allocation is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "toolbudget.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def allocate_total_only(intended, order, budget):
    """Greedy allocation against a single total budget: serve tools in request order until the budget runs out."""
    alloc, remaining = {}, budget
    for tool in order:
        take = min(intended.get(tool, 0), remaining)
        alloc[tool] = take
        remaining -= take
    return alloc


def allocate_per_tool(intended, order, caps, budget):
    """Allocation with a per-tool cap: each tool is limited to its cap, then the total budget, in request order."""
    alloc, remaining = {}, budget
    for tool in order:
        want = min(intended.get(tool, 0), caps.get(tool, budget))
        take = min(want, remaining)
        alloc[tool] = take
        remaining -= take
    return alloc


def tools_run(alloc):
    """The set of tools that actually got at least one call."""
    return {t for t, n in alloc.items() if n > 0}


def required_covered(alloc, required):
    """Did every required tool get to run at least once?"""
    return all(alloc.get(t, 0) > 0 for t in required)


# ----------------------------------------------------------------- printing

def allocate_view(data):
    intended, order = data["intended_calls"], data["request_order"]
    budget, caps = data["total_budget"], data["per_tool_caps"]
    to = allocate_total_only(intended, order, budget)
    pt = allocate_per_tool(intended, order, caps, budget)
    print("ALLOCATE — total-only budget vs per-tool caps (total budget = %d)" % budget)
    print("-" * 62)
    print("  tool      intended   total-only   per-tool (cap)")
    for tool in order:
        print("  %-8s  %-8d   %-10d   %d (%d)" % (tool, intended[tool], to[tool], pt[tool], caps[tool]))
    print("  %-8s  %-8s   %-10d   %d" % ("TOTAL", sum(intended.values()), sum(to.values()), sum(pt.values())))
    print("-" * 62)
    print("  total-only pours the whole budget into search; per-tool caps leave room for read and write.")


def coverage_view(data):
    intended, order = data["intended_calls"], data["request_order"]
    budget, caps, req = data["total_budget"], data["per_tool_caps"], data["required"]
    to = allocate_total_only(intended, order, budget)
    pt = allocate_per_tool(intended, order, caps, budget)
    print("COVERAGE — which tools run, and whether the required tools are covered")
    print("-" * 62)
    print("  required tools: %s" % req)
    print("  total-only:  ran %s   required covered? %s" % (sorted(tools_run(to)), required_covered(to, req)))
    print("  per-tool:    ran %s   required covered? %s" % (sorted(tools_run(pt)), required_covered(pt, req)))
    print("-" * 62)
    print("  the task needs read and write; only the per-tool policy lets them run.")


def check(data):
    print("SELF-TEST — the total-only budget lets one tool consume it and starves the required tools; per-tool caps prevent it")
    print("-" * 118)
    intended, order = data["intended_calls"], data["request_order"]
    budget, caps, req = data["total_budget"], data["per_tool_caps"], data["required"]
    to = allocate_total_only(intended, order, budget)
    pt = allocate_per_tool(intended, order, caps, budget)

    one_tool_hogs = max(to.values()) == budget
    print("  total-only lets one tool consume the entire budget = %s (search=%d of %d)" % (one_tool_hogs, to["search"], budget))

    required_starved = not required_covered(to, req)
    print("  the required tools are starved under total-only = %s (ran %s)" % (required_starved, sorted(tools_run(to))))

    caps_bound_each = all(pt[t] <= caps[t] for t in pt)
    print("  per-tool caps bound every tool = %s (search=%d <= cap %d)" % (caps_bound_each, pt["search"], caps["search"]))

    required_covered_pt = required_covered(pt, req)
    print("  the required tools all run under per-tool caps = %s (ran %s)" % (required_covered_pt, sorted(tools_run(pt))))

    within_budget = sum(pt.values()) <= budget
    print("  per-tool allocation still respects the total budget = %s (%d <= %d)" % (within_budget, sum(pt.values()), budget))

    ok = one_tool_hogs and required_starved and caps_bound_each and required_covered_pt and within_budget
    print("-" * 118)
    print("SELF-TEST %s  one_tool_hogs=%s  required_starved=%s  caps_bound_each=%s  required_covered_pt=%s  within_budget=%s"
          % ("PASS" if ok else "FAIL", one_tool_hogs, required_starved, caps_bound_each, required_covered_pt, within_budget))
    return ok


def main():
    p = argparse.ArgumentParser(description="Per-tool call budgets: cap how many times each tool may be called, not just the total, so a runaway single-tool loop cannot consume the whole run and starve the tools the task needs.")
    p.add_argument("--allocate", action="store_true")
    p.add_argument("--coverage", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("total_budget=%d  per_tool_caps=%s  required=%s  file=%s  (the run's demand is a fixture)"
          % (data["total_budget"], data["per_tool_caps"], data["required"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.allocate:
        allocate_view(data)
    elif args.coverage:
        coverage_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
