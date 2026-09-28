"""Prune the tool menu, or every unused tool's schema is a token tax paid on every single call.

An agent's tool definitions -- each tool's name, description, and parameter schema -- are sent to the model on
EVERY request, because the model is stateless and has to be told its tools each time. Register fifty tools and
all fifty schemas ride along on every call, whether the task uses them or not. That is a fixed tax on the
context window: tokens spent before the model reads a word of the actual task, spent again on the next call,
and again, for the whole loop. A task that needs two tools but is handed a menu of fifty pays for forty-eight
it never touches, over and over. The tools are not doing anything wrong; the mistake is exposing all of them
when the task needs a handful.

Pruning the menu fixes it. Expose only the tools this task actually needs -- selected up front, or retrieved
per step from a larger catalog -- so the per-call token cost is the sum of the relevant schemas, not the whole
registry. The reclaimed budget goes to what matters: more room for the task, the context, the reasoning. The
saving is not a one-time trim; it multiplies by the number of calls in the loop, because the menu is re-sent
each time. A smaller menu also helps the model choose correctly, but the cost alone justifies the prune.

On this fixture eight tools cost 250 tokens each, and the task needs two. The full menu spends 2000 tokens per
call -- 25% of an 8000-token budget -- of which 1500 is tools the task never uses. Over a 10-call loop that is
15000 wasted tokens. The pruned menu spends 500 per call. This computes both.

  --cost       the per-call menu cost, full vs pruned, and the share of the context budget
  --waste      the tokens wasted on unused tools, per call and across the whole loop
  --check      the full menu is re-sent every call; most of it is unused; pruning reclaims the budget

The tool token costs and task are the fixture; every total is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "tools.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def menu_cost(tool_tokens, tools):
    """Tokens the given set of tool schemas occupies -- paid on every call."""
    return sum(tool_tokens[t] for t in tools)


def unused(tool_tokens, needed):
    return [t for t in tool_tokens if t not in needed]


# ----------------------------------------------------------------- printing

def cost_view(data):
    tt, needed, budget = data["tool_tokens"], data["needed"], data["context_budget"]
    full = menu_cost(tt, tt)
    pruned = menu_cost(tt, needed)
    print("COST — per-call menu cost, full vs pruned (budget %d tokens)" % budget)
    print("-" * 62)
    print("  full menu (%d tools):   %5d tokens/call   %4.1f%% of budget" % (len(tt), full, 100 * full / budget))
    print("  pruned  (%d tools):     %5d tokens/call   %4.1f%% of budget" % (len(needed), pruned, 100 * pruned / budget))
    print("-" * 62)
    print("  the menu is spent before the task is even read -- every call.")


def waste_view(data):
    tt, needed, calls = data["tool_tokens"], data["needed"], data["calls"]
    waste_per_call = menu_cost(tt, unused(tt, needed))
    print("WASTE — tokens spent on tools the task never uses")
    print("-" * 62)
    print("  unused tools: %d of %d" % (len(unused(tt, needed)), len(tt)))
    print("  wasted per call:      %5d tokens" % waste_per_call)
    print("  calls in the loop:    %5d" % calls)
    print("  wasted over the loop: %5d tokens" % (waste_per_call * calls))
    print("-" * 62)
    print("  the waste multiplies by the number of calls, because the menu re-ships each time.")


def check(data):
    print("SELF-TEST — the full menu is re-sent every call; most of it is unused; pruning reclaims the budget")
    print("-" * 104)
    tt, needed, calls, budget = data["tool_tokens"], data["needed"], data["calls"], data["context_budget"]
    full = menu_cost(tt, tt)
    pruned = menu_cost(tt, needed)
    waste_per_call = menu_cost(tt, unused(tt, needed))

    full_menu_costs_more = full > pruned
    print("  the full menu costs more per call than the pruned one = %s (%d vs %d)" % (full_menu_costs_more, full, pruned))

    waste_equals_unused = waste_per_call == full - pruned
    print("  the waste equals the unused tools' schemas = %s (%d = %d - %d)" % (waste_equals_unused, waste_per_call, full, pruned))

    total_waste = waste_per_call * calls
    waste_compounds = total_waste > waste_per_call and calls > 1
    print("  the waste multiplies over the loop = %s (%d over %d calls)" % (waste_compounds, total_waste, calls))

    unused_are_majority = len(unused(tt, needed)) > len(needed)
    print("  most registered tools go unused = %s (%d unused vs %d needed)" % (unused_are_majority, len(unused(tt, needed)), len(needed)))

    pruning_frees_budget = pruned < full and (full - pruned) / budget > 0.1
    print("  pruning reclaims a real share of the budget = %s (%.1f%% freed per call)" % (pruning_frees_budget, 100 * (full - pruned) / budget))

    ok = full_menu_costs_more and waste_equals_unused and waste_compounds and unused_are_majority and pruning_frees_budget
    print("-" * 104)
    print("SELF-TEST %s  full_menu_costs_more=%s  waste_equals_unused=%s  waste_compounds=%s  unused_are_majority=%s  pruning_frees_budget=%s"
          % ("PASS" if ok else "FAIL", full_menu_costs_more, waste_equals_unused, waste_compounds, unused_are_majority, pruning_frees_budget))
    return ok


def main():
    p = argparse.ArgumentParser(description="Prune the tool menu so unused tool schemas are not re-sent on every call.")
    p.add_argument("--cost", action="store_true")
    p.add_argument("--waste", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("tools=%d  needed=%d  calls=%d  budget=%d  file=%s  (the tool menu is a fixture)"
          % (len(data["tool_tokens"]), len(data["needed"]), data["calls"], data["context_budget"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.cost:
        cost_view(data)
    elif args.waste:
        waste_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
