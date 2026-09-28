#!/usr/bin/env python3
"""Recommend from the ready-to-learn frontier -- not the next module in the list.

A curriculum is a prerequisite graph: each module assumes the ones before it are already
mastered. The only modules worth recommending to a learner right now are those on the
READY-TO-LEARN FRONTIER -- prerequisites all mastered, module itself not yet mastered.
Recommend one of those and the learner can actually absorb it; recommend a module whose
prerequisites are unmet and they bounce off it, because the material silently assumes
knowledge they do not have.

The bug is to recommend by list order (or id): pick the first not-yet-mastered module and
send the learner there. That ignores the graph, so it will happily recommend a module deep
in the dependency chain whose prerequisites are missing. Here it recommends 'attention',
which needs 'vectors' the learner has not done -- a guaranteed bounce. The fix is to
compute the frontier from the prerequisites and recommend only from it. This measures both.

  --frontier    the ready-to-learn set, the locked set, and why each is locked
  --recommend   frontier-based recommendation vs by-order; who gets sent to a locked module
  --check       the frontier's prereqs are all met; by-order recommends a locked module

Stdlib only. Deterministic.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "curriculum.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------- the frontier

def prereqs_met(module, mastered):
    """Are all of a module's prerequisites in the mastered set?"""
    return all(p in mastered for p in module["prereqs"])


def is_unlocked(module, mastered):
    """Ready to learn now: prereqs met AND not already mastered."""
    return module["id"] not in mastered and prereqs_met(module, mastered)


def frontier(modules, mastered):
    return [m for m in modules if is_unlocked(m, mastered)]


def locked(modules, mastered):
    return [m for m in modules if m["id"] not in mastered and not prereqs_met(m, mastered)]


def missing_prereqs(module, mastered):
    return [p for p in module["prereqs"] if p not in mastered]


# ------------------------------------------------------- the two recommenders

def recommend_frontier(modules, mastered):
    """Correct: pick from the ready-to-learn frontier (first by id for determinism)."""
    ready = sorted(frontier(modules, mastered), key=lambda m: m["id"])
    return ready[0]["id"] if ready else None


def recommend_by_order(modules, mastered):
    """The bug: pick the first not-yet-mastered module by id, ignoring prerequisites."""
    todo = sorted((m for m in modules if m["id"] not in mastered), key=lambda m: m["id"])
    return todo[0]["id"] if todo else None


# ----------------------------------------------------------------- printing

def frontier_view(data):
    mods, mastered = data["modules"], set(data["mastered"])
    print("FRONTIER — ready to learn now (prereqs met, not yet mastered)")
    print("-" * 66)
    print("  mastered: %s" % sorted(mastered))
    print("  UNLOCKED (recommend from here): %s" % [m["id"] for m in frontier(mods, mastered)])
    print("  LOCKED:")
    for m in locked(mods, mastered):
        print("     %-10s waiting on: %s" % (m["id"], missing_prereqs(m, mastered)))
    print("-" * 66)
    print("  only the unlocked set can be absorbed right now.")


def recommend_view(data):
    mods, mastered = data["modules"], set(data["mastered"])
    fr = recommend_frontier(mods, mastered)
    bo = recommend_by_order(mods, mastered)
    bo_module = next(m for m in mods if m["id"] == bo)
    print("RECOMMEND — frontier-based vs by-order")
    print("-" * 66)
    print("  frontier recommends: %s  (prereqs met: %s)" % (fr, prereqs_met(next(m for m in mods if m['id']==fr), mastered)))
    print("  by-order recommends: %s  (prereqs met: %s, missing %s)"
          % (bo, prereqs_met(bo_module, mastered), missing_prereqs(bo_module, mastered)))
    print("-" * 66)
    print("  by-order sends the learner to a module whose prerequisites are unmet.")


def check(data):
    print("SELF-TEST — the frontier's prereqs are all met; by-order recommends a locked module")
    print("-" * 66)
    mods, mastered = data["modules"], set(data["mastered"])

    fr = frontier(mods, mastered)
    frontier_ready = all(prereqs_met(m, mastered) for m in fr)
    print("  every module on the frontier has its prereqs met = %s (%s)"
          % (frontier_ready, [m["id"] for m in fr]))

    none_mastered = all(m["id"] not in mastered for m in fr)
    print("  the frontier excludes already-mastered modules = %s" % none_mastered)

    frontier_nonempty = len(fr) > 0
    print("  the frontier is non-empty (there is something to learn) = %s" % frontier_nonempty)

    bo = recommend_by_order(mods, mastered)
    bo_module = next(m for m in mods if m["id"] == bo)
    by_order_locked = not prereqs_met(bo_module, mastered)
    print("  by-order recommends a LOCKED module = %s (%s needs %s)"
          % (by_order_locked, bo, missing_prereqs(bo_module, mastered)))

    fr_rec = recommend_frontier(mods, mastered)
    frontier_safe = prereqs_met(next(m for m in mods if m["id"] == fr_rec), mastered)
    print("  frontier recommends a module the learner is ready for = %s (%s)" % (frontier_safe, fr_rec))

    ok = frontier_ready and none_mastered and frontier_nonempty and by_order_locked and frontier_safe
    print("-" * 66)
    print("SELF-TEST %s  frontier_ready=%s  none_mastered=%s  nonempty=%s  by_order_locked=%s  frontier_safe=%s"
          % ("PASS" if ok else "FAIL", frontier_ready, none_mastered, frontier_nonempty, by_order_locked, frontier_safe))
    return ok


def main():
    p = argparse.ArgumentParser(description="Ready-to-learn frontier vs by-order recommendation.")
    p.add_argument("--frontier", action="store_true")
    p.add_argument("--recommend", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("modules=%d  mastered=%d  file=%s  (curriculum is a fixture)"
          % (len(data["modules"]), len(data["mastered"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.frontier:
        frontier_view(data)
    elif args.recommend:
        recommend_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
