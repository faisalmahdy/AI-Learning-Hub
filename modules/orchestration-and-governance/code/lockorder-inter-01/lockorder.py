"""Acquire locks in a single global order and deadlock cannot form -- two transactions that grab the same locks in opposite orders can wait on each other in a cycle, and a canonical acquisition order makes that cycle impossible.

A deadlock over locks is a precise structure: a cycle in the wait-for graph. Transaction t1 holds lock A and wants B; transaction t2 holds B and wants A; each waits for a lock the other holds, so neither proceeds and neither releases. It is not slowness -- no amount of waiting clears it -- and a timeout only papers over it by killing a victim after the damage.

The root cause is order disagreement. The cycle needs t1 to hold A-before-B and t2 to hold B-before-A; the two transactions acquire the shared locks in opposite relative orders, and that opposition is exactly what lets each grab the lock the other needs next. If both transactions always acquired A before B, one of them would take A first and then get B with nothing in its way, while the other waited for A and proceeded once A was free. No two transactions could ever hold locks in the conflicting order a cycle requires.

So the fix is prevention, not detection: impose a canonical global order on all locks and require every transaction to acquire the locks it needs in that order (sort its lock set before locking). A cycle in the wait-for graph would require some transaction holding a higher-ordered lock while waiting for a lower-ordered one, which the discipline forbids -- so the graph is always acyclic and deadlock cannot occur.

This simulates every interleaving of the two transactions' lock acquisitions and counts how many deadlock, under the naive plans (opposite orders) and under the ordered plans (both sorted into the canonical order).

  --race     one interleaving under the naive plans: t1 holds A, t2 holds B, and both block in a wait-for cycle
  --ordered  the same locks acquired in canonical order: every interleaving completes, none deadlocks
  --check    the naive plans deadlock on some interleavings because the two acquire the shared locks in opposite order, and the ordered plans deadlock on none

locks (the canonical order), t1_plan, and t2_plan are the fixture; the deadlocking interleaving and the deadlock counts are computed. Stdlib only.
"""
import argparse
import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "lockorder.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def in_canonical_order(plan, locks):
    """Sort a transaction's lock requests into the global order -- the discipline that prevents deadlock."""
    return sorted(plan, key=lambda lock: locks.index(lock))


def simulate(plan1, plan2, schedule):
    """Run one interleaving; return 'deadlock' if both transactions end up blocked waiting on each other."""
    plans = {"t1": plan1, "t2": plan2}
    pos = {"t1": 0, "t2": 0}                 # how many locks each has acquired
    held = {}                                # lock -> owner
    for txn in schedule:
        if pos[txn] >= len(plans[txn]):
            continue                          # this transaction is already finished
        want = plans[txn][pos[txn]]
        owner = held.get(want)
        if owner is None or owner == txn:
            held[want] = txn                  # acquire it (or already own it)
            pos[txn] += 1
            if pos[txn] == len(plans[txn]):   # finished: release everything it held
                held = {lk: o for lk, o in held.items() if o != txn}
        # else: the lock is held by the other transaction -> this step blocks and makes no progress
    blocked = {t: (pos[t] < len(plans[t]) and held.get(plans[t][pos[t]]) not in (None, t)) for t in plans}
    return "deadlock" if blocked["t1"] and blocked["t2"] else "ok"


def all_interleavings():
    """Every distinct order in which t1's two steps and t2's two steps can be scheduled."""
    return sorted(set(itertools.permutations(["t1", "t1", "t2", "t2"])))


def deadlock_count(plan1, plan2):
    """How many of the interleavings deadlock under these two plans."""
    return sum(1 for s in all_interleavings() if simulate(plan1, plan2, s) == "deadlock")


# ----------------------------------------------------------------- printing

def race_view(data):
    p1, p2 = data["t1_plan"], data["t2_plan"]
    bad = next(s for s in all_interleavings() if simulate(p1, p2, s) == "deadlock")
    print("RACE — the naive plans (t1 wants %s, t2 wants %s)" % (p1, p2))
    print("-" * 60)
    print("  a deadlocking interleaving: %s" % list(bad))
    print("    t1 acquires %s, t2 acquires %s" % (p1[0], p2[0]))
    print("    t1 now waits for %s (held by t2); t2 waits for %s (held by t1)" % (p1[1], p2[1]))
    print("    wait-for graph: t1 -> t2 -> t1  (a cycle: deadlock)")
    print("  deadlocking interleavings: %d of %d" % (deadlock_count(p1, p2), len(all_interleavings())))
    print("-" * 60)
    print("  the two acquire the shared locks in opposite order, so each can hold what the other needs")


def ordered_view(data):
    locks = data["locks"]
    p1 = in_canonical_order(data["t1_plan"], locks)
    p2 = in_canonical_order(data["t2_plan"], locks)
    print("ORDERED — both plans sorted into the canonical order %s" % locks)
    print("-" * 60)
    print("  t1 now acquires %s, t2 now acquires %s  (same order)" % (p1, p2))
    print("  whoever takes %s first gets %s next unobstructed; the other waits for %s, then proceeds" % (locks[0], locks[1], locks[0]))
    print("  deadlocking interleavings: %d of %d" % (deadlock_count(p1, p2), len(all_interleavings())))
    print("-" * 60)
    print("  no interleaving deadlocks: a wait-for cycle would need the forbidden reverse order")


def check(data):
    print("SELF-TEST — the naive plans deadlock on some interleavings because the two acquire the shared locks in opposite order, and the ordered plans deadlock on none")
    print("-" * 112)
    locks = data["locks"]
    p1, p2 = data["t1_plan"], data["t2_plan"]
    o1 = in_canonical_order(p1, locks)
    o2 = in_canonical_order(p2, locks)
    total = len(all_interleavings())

    naive_orders_conflict = [locks.index(x) for x in p1] != [locks.index(x) for x in p2]
    print("  the two naive plans acquire the shared locks in opposite order = %s (%s vs %s)" % (naive_orders_conflict, p1, p2))

    naive_can_deadlock = deadlock_count(p1, p2) > 0
    print("  the naive plans deadlock on some interleaving = %s (%d of %d)" % (naive_can_deadlock, deadlock_count(p1, p2), total))

    ordering_makes_plans_agree = o1 == o2
    print("  sorting into the canonical order makes both acquire in the same order = %s (%s == %s)" % (ordering_makes_plans_agree, o1, o2))

    ordered_never_deadlocks = deadlock_count(o1, o2) == 0
    print("  the ordered plans deadlock on no interleaving = %s (%d of %d)" % (ordered_never_deadlocks, deadlock_count(o1, o2), total))

    prevention_beats_detection = naive_can_deadlock and ordered_never_deadlocks
    print("  imposing the order removed the deadlock entirely rather than recovering from it = %s" % prevention_beats_detection)

    ok = (naive_orders_conflict and naive_can_deadlock and ordering_makes_plans_agree
          and ordered_never_deadlocks and prevention_beats_detection)
    print("-" * 112)
    print("SELF-TEST %s  naive_orders_conflict=%s  naive_can_deadlock=%s  ordering_makes_plans_agree=%s  ordered_never_deadlocks=%s  prevention_beats_detection=%s"
          % ("PASS" if ok else "FAIL", naive_orders_conflict, naive_can_deadlock, ordering_makes_plans_agree,
             ordered_never_deadlocks, prevention_beats_detection))
    return ok


def main():
    p = argparse.ArgumentParser(description="Lock ordering: acquire every lock in a single global (canonical) order, so two transactions can never hold locks in the opposite order a wait-for cycle requires -- preventing deadlock outright instead of detecting and recovering from it.")
    p.add_argument("--race", action="store_true")
    p.add_argument("--ordered", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("locks=%s  t1_plan=%s  t2_plan=%s  file=%s  (these are a fixture)"
          % (data["locks"], data["t1_plan"], data["t2_plan"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.race:
        race_view(data)
    elif args.ordered:
        ordered_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
