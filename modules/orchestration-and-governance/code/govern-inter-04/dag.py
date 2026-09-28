#!/usr/bin/env python3
"""Order a multi-agent plan by its dependencies -- or run subagents on stale inputs.

Fan out work to subagents and the tasks are rarely independent: one consumes another's
output. clean_data needs fetch_sources; evaluate needs both build_index and
train_model. A dependency is a promise that the producer finishes before the consumer
starts. Run the tasks in the order they happen to sit in the plan file and you break
that promise: a task reads an input that does not exist yet, or worse, a stale one
from a previous run, and the failure is silent -- the subagent returns something, just
based on the wrong data.

The fix is a topological sort: an ordering in which every task comes after all of its
dependencies. Kahn's algorithm builds one by repeatedly running whatever has no
unfinished dependencies left. It has a second job that matters just as much: if the
plan has a dependency cycle -- a needs c, c needs b, b needs a -- no valid order
exists, and the algorithm must SAY SO rather than deadlock or loop. This measures the
violations a naive order commits, the zero a topological order commits, and the cycle
that must be reported.

  --order       the plan's listed order vs a topological order
  --violations  dependency violations under each order (a task run before its dep)
  --cycle       run the cyclic plan; the scheduler reports the cycle instead of hanging
  --check       topo order is valid (0 violations); listed order is not; the cycle is caught

Stdlib only. Deterministic (ties broken by task id).
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "plan.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- topological sort

def topo_order(tasks):
    """Kahn's algorithm. Returns (order, ok): ok is False if a cycle blocks completion."""
    indeg = {t: len(spec["deps"]) for t, spec in tasks.items()}
    dependents = {t: [] for t in tasks}
    for t, spec in tasks.items():
        for d in spec["deps"]:
            dependents[d].append(t)

    ready = sorted(t for t, n in indeg.items() if n == 0)  # sorted -> deterministic
    order = []
    while ready:
        t = ready.pop(0)
        order.append(t)
        for dep in sorted(dependents[t]):
            indeg[dep] -= 1
            if indeg[dep] == 0:
                ready.append(dep)
        ready.sort()
    ok = len(order) == len(tasks)  # fewer than all -> a cycle stranded the rest
    return order, ok


def stranded_by_cycle(tasks, order):
    """Tasks a topological sort could never schedule -- the ones caught in a cycle."""
    return sorted(set(tasks) - set(order))


# ------------------------------------------------------------- checking an order

def violations(tasks, order):
    """Dependencies broken by running tasks in `order`: a task placed before a dep of it."""
    position = {t: i for i, t in enumerate(order)}
    broken = []
    for t, spec in tasks.items():
        for d in spec["deps"]:
            if position[t] < position[d]:  # consumer runs before producer
                broken.append((t, d))
    return sorted(broken)


# ----------------------------------------------------------------- printing

def order_view(data):
    tasks = data["tasks"]
    order, ok = topo_order(tasks)
    print("ORDER — the plan's listed order vs a dependency-respecting order")
    print("-" * 66)
    print("  listed order (as written): %s" % " -> ".join(data["listed_order"]))
    print("  topological order:         %s" % " -> ".join(order))
    print("-" * 66)
    print("  the topological order runs every producer before its consumer.")


def violations_view(data):
    tasks = data["tasks"]
    listed = data["listed_order"]
    topo, _ = topo_order(tasks)
    vl = violations(tasks, listed)
    vt = violations(tasks, topo)
    print("VIOLATIONS — dependencies broken by each order (consumer before producer)")
    print("-" * 66)
    print("  listed order: %d violation(s)" % len(vl))
    for t, d in vl:
        print("     %-14s ran before its dependency %s" % (t, d))
    print("  topological order: %d violation(s)" % len(vt))
    print("-" * 66)
    print("  each violation is a subagent reading an input that does not exist yet.")


def cycle_view(data):
    tasks = data["cyclic_plan"]["tasks"]
    order, ok = topo_order(tasks)
    print("CYCLE — a plan whose dependencies form a loop cannot be ordered")
    print("-" * 66)
    print("  tasks: %s" % ", ".join("%s->%s" % (t, ",".join(s["deps"])) for t, s in tasks.items()))
    print("  scheduled: %s" % (order or "(nothing -- every task waits on another)"))
    print("  completable: %s" % ok)
    print("  stranded in the cycle: %s" % stranded_by_cycle(tasks, order))
    print("-" * 66)
    print("  the scheduler reports the cycle instead of deadlocking on it.")


def check(data):
    print("SELF-TEST — topo order is valid; listed order is not; the cycle is caught")
    print("-" * 66)
    tasks = data["tasks"]

    order, ok = topo_order(tasks)
    topo_valid = ok and violations(tasks, order) == []
    print("  topological order completes and has 0 violations = %s (%d tasks)" % (topo_valid, len(order)))

    listed_bad = len(violations(tasks, data["listed_order"])) > 0
    print("  the listed order breaks dependencies = %s (%d violations)"
          % (listed_bad, len(violations(tasks, data["listed_order"]))))

    # Every dependency really is respected by position in the topo order.
    pos = {t: i for i, t in enumerate(order)}
    all_after = all(pos[t] > pos[d] for t, spec in tasks.items() for d in spec["deps"])
    print("  every task follows all its dependencies in the topo order = %s" % all_after)

    cyc_tasks = data["cyclic_plan"]["tasks"]
    _, cyc_ok = topo_order(cyc_tasks)
    cycle_caught = not cyc_ok
    print("  the cyclic plan is reported uncompletable (not deadlocked) = %s" % cycle_caught)

    ok_all = topo_valid and listed_bad and all_after and cycle_caught
    print("-" * 66)
    print("SELF-TEST %s  topo_valid=%s  listed_bad=%s  all_after=%s  cycle_caught=%s"
          % ("PASS" if ok_all else "FAIL", topo_valid, listed_bad, all_after, cycle_caught))
    return ok_all


def main():
    p = argparse.ArgumentParser(description="Dependency-ordered scheduling of a multi-agent plan.")
    p.add_argument("--order", action="store_true")
    p.add_argument("--violations", action="store_true")
    p.add_argument("--cycle", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("tasks=%d  file=%s  (plan dependencies are a fixture)" % (len(data["tasks"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.order:
        order_view(data)
    elif args.violations:
        violations_view(data)
    elif args.cycle:
        cycle_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
