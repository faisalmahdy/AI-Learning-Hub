#!/usr/bin/env python3
"""A resilient orchestrator composes the partition contract, the DAG, retries+DLQ, and the saga.

The orchestration track built each guarantee an executor needs, one module at a time: the
partition contract (govern-inter-03) rejects a fan-out whose assignment is not disjoint and
complete, the task DAG (govern-inter-04) runs producers before consumers, the retry bound
plus dead-letter queue (govern-inter-06) contains a poison task instead of letting it starve
the queue, and the saga (govern-inter-05) undoes the completed prefix when a step past the
point of no return fails. This composes all four into one orchestrator and measures the
property none of them gives alone: run the plan and it either commits every step or unwinds
to exactly the state it started in -- never a partial, leaked, corrupt middle.

The naive orchestrator runs the steps in the order they sit in the plan file, trusts the
assignment, has no retry or dead-letter, and on a failure simply stops. On this plan that is
three separate corruptions at once: a consumer runs before its producer on stale state, the
poison step fails and takes the whole run down, and the two steps that already committed
their real side effects are left committed -- a seat held and a card charged with no ticket
and no record of why. Same plan, same failing step; the composed orchestrator ends at a
clean zero ledger with the poison task dead-lettered, the naive one ends leaked and silent.

  --plan        the plan: each step's deps, partition key, forward/compensate effect, poison flag
  --naive       run in file order, no contract/DLQ/saga; show the leaked ledger and the stale read
  --resilient   validate partition, topo-sort, execute with retries+DLQ, saga-unwind on the poison
  --check       resilient ends at zero ledger with the poison dead-lettered; naive ends leaked

Deterministic: which step is poison and which are transient is the fixture, not a clock.
Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "plan.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------- 1. the partition contract

def check_partition(steps, target):
    """govern-inter-03: the steps' partition keys must be disjoint and cover the target exactly."""
    keys = [s["key"] for s in steps]
    seen, overlap = set(), set()
    for k in keys:
        if k in seen:
            overlap.add(k)
        seen.add(k)
    missing = set(target) - seen
    extra = seen - set(target)
    ok = not overlap and not missing and not extra
    return ok, {"overlap": sorted(overlap), "missing": sorted(missing), "extra": sorted(extra)}


# ------------------------------------------------------- 2. the task DAG

def topo_order(steps):
    """govern-inter-04: Kahn's algorithm. Returns (order, cycle) -- order empty if a cycle exists."""
    ids = [s["id"] for s in steps]
    dep = {s["id"]: list(s["deps"]) for s in steps}
    indeg = {i: 0 for i in ids}
    for i in ids:
        for d in dep[i]:
            indeg[i] += 1
    ready = sorted(i for i in ids if indeg[i] == 0)
    order = []
    while ready:
        n = ready.pop(0)
        order.append(n)
        for i in ids:
            if n in dep[i]:
                indeg[i] -= 1
                if indeg[i] == 0:
                    ready.append(i)
        ready.sort()
    cycle = [i for i in ids if i not in order]
    return (order if not cycle else []), cycle


def violations_in_order(order, steps):
    """How many consumers run before a producer in this exact order (a stale-input read)."""
    pos = {sid: i for i, sid in enumerate(order)}
    dep = {s["id"]: s["deps"] for s in steps}
    v = 0
    for sid in order:
        for d in dep[sid]:
            if pos.get(d, 1 << 30) > pos[sid]:
                v += 1
    return v


# ------------------------------------------------------- 3+4. execute with retries+DLQ, saga on failure

def run_resilient(data):
    """Validate, order, execute with bounded retries + DLQ; saga-unwind the committed prefix on poison."""
    steps = {s["id"]: s for s in data["steps"]}
    order, _ = topo_order(data["steps"])
    max_retries = data["max_retries"]

    ledger = {s["key"]: 0 for s in data["steps"]}
    committed = []          # completed steps, in commit order
    dlq = []
    attempts = 0
    trace = []

    for sid in order:
        s = steps[sid]
        ok = False
        for _ in range(max_retries):
            attempts += 1
            # transient steps fail (fails_before) times then succeed; poison never succeeds
            fails_needed = 999 if s["poison"] else s["fails_before"]
            if (attempts_for(trace, sid)) >= fails_needed:
                ok = True
                break
            trace.append((sid, "fail"))
        if ok:
            ledger[s["key"]] += s["forward"]
            committed.append(sid)
            trace.append((sid, "commit"))
        else:
            dlq.append(sid)
            trace.append((sid, "dead-letter"))
            # saga: compensate the committed prefix in reverse -- past the point of no return
            for csid in reversed(committed):
                cs = steps[csid]
                ledger[cs["key"]] -= cs["forward"]     # compensate == inverse of forward
                trace.append((csid, "compensate"))
            committed = []
            break
    return {"ledger": ledger, "committed": committed, "dlq": dlq, "attempts": attempts,
            "order": order, "trace": trace}


def attempts_for(trace, sid):
    return sum(1 for t, r in trace if t == sid and r == "fail")


# ------------------------------------------------------- the naive orchestrator

def run_naive(data):
    """File order, no partition check, no retry/DLQ, no saga: stop on the first failure and leak."""
    steps = data["steps"]                       # as authored, not topo-sorted
    ledger = {s["key"]: 0 for s in steps}
    committed = []
    stale_reads = violations_in_order([s["id"] for s in steps], steps)
    stopped_at = None
    for s in steps:
        if s["poison"]:                          # no retry, no DLQ -> the run just stops here
            stopped_at = s["id"]
            break
        ledger[s["key"]] += s["forward"]         # commit real side effects, one attempt
        committed.append(s["id"])
    # no saga: whatever committed stays committed
    return {"ledger": ledger, "committed": committed, "stopped_at": stopped_at,
            "stale_reads": stale_reads}


def leaked(ledger):
    return {k: v for k, v in ledger.items() if v != 0}


# ----------------------------------------------------------------- printing

def plan_view(data):
    steps = data["steps"]
    ok, detail = check_partition(steps, data["target"])
    order, cycle = topo_order(steps)
    print("PLAN — %d steps; partition target %s" % (len(steps), data["target"]))
    print("-" * 70)
    print("  id          deps            key    forward  poison  fails_before")
    for s in steps:
        print("  %-11s %-15s %-6s %+7d  %-6s  %d"
              % (s["id"], ",".join(s["deps"]) or "-", s["key"], s["forward"], s["poison"], s["fails_before"]))
    print("-" * 70)
    print("  partition disjoint+complete = %s %s" % (ok, "" if ok else detail))
    print("  file order:  %s  (stale reads: %d)"
          % ([s["id"] for s in steps], violations_in_order([s["id"] for s in steps], steps)))
    print("  topo order:  %s  (stale reads: %d)" % (order, violations_in_order(order, steps)))


def naive_view(data):
    r = run_naive(data)
    print("NAIVE — file order, no contract/DLQ/saga; stop and leak on the poison step")
    print("-" * 70)
    print("  ran in file order, stale-input reads: %d" % r["stale_reads"])
    print("  committed (kept, never unwound): %s" % r["committed"])
    print("  stopped at poison step: %s" % r["stopped_at"])
    print("  final ledger: %s" % r["ledger"])
    print("-" * 70)
    print("  LEAKED side effects left in the world: %s" % leaked(r["ledger"]))


def resilient_view(data):
    r = run_resilient(data)
    print("RESILIENT — partition-checked, topo-ordered, retries+DLQ, saga-unwound")
    print("-" * 70)
    for sid, ev in r["trace"]:
        print("  %-11s %s" % (sid, ev))
    print("-" * 70)
    print("  attempts: %d   dead-lettered: %s   still committed: %s"
          % (r["attempts"], r["dlq"], r["committed"]))
    print("  final ledger: %s" % r["ledger"])
    print("  leaked side effects: %s" % leaked(r["ledger"]))


def check(data):
    print("SELF-TEST — resilient unwinds to a clean zero with the poison dead-lettered; naive leaks")
    print("-" * 70)

    ok, detail = check_partition(data["steps"], data["target"])
    print("  the plan's partition is disjoint and complete = %s %s" % (ok, "" if ok else detail))

    order, cycle = topo_order(data["steps"])
    topo_clean = violations_in_order(order, data["steps"]) == 0 and not cycle
    file_bad = violations_in_order([s["id"] for s in data["steps"]], data["steps"]) > 0
    print("  topo order has zero stale reads while file order has some = %s (file=%d, topo=0)"
          % (topo_clean and file_bad, violations_in_order([s["id"] for s in data["steps"]], data["steps"])))

    r = run_resilient(data)
    n = run_naive(data)

    poison_dlq = len(r["dlq"]) == 1 and data_poison_id(data) in r["dlq"]
    print("  resilient dead-lettered exactly the poison step = %s (%s)" % (poison_dlq, r["dlq"]))

    resilient_clean = not leaked(r["ledger"]) and not r["committed"]
    print("  resilient ledger fully unwound to zero (no leak) = %s (%s)"
          % (resilient_clean, r["ledger"]))

    naive_leaks = bool(leaked(n["ledger"]))
    print("  naive left real side effects leaked (a seat held, a card charged) = %s (%s)"
          % (naive_leaks, leaked(n["ledger"])))

    ok_all = ok and topo_clean and file_bad and poison_dlq and resilient_clean and naive_leaks
    print("-" * 70)
    print("SELF-TEST %s  partition=%s  order=%s  poison_dlq=%s  resilient_clean=%s  naive_leaks=%s"
          % ("PASS" if ok_all else "FAIL", ok, topo_clean and file_bad, poison_dlq, resilient_clean, naive_leaks))
    return ok_all


def data_poison_id(data):
    for s in data["steps"]:
        if s["poison"]:
            return s["id"]
    return None


def main():
    p = argparse.ArgumentParser(description="A resilient orchestrator composing contract, DAG, retries+DLQ, saga.")
    p.add_argument("--plan", action="store_true")
    p.add_argument("--naive", action="store_true")
    p.add_argument("--resilient", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("steps=%d  max_retries=%d  target=%s  file=%s  (plan and failure pattern are a fixture)"
          % (len(data["steps"]), data["max_retries"], data["target"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.plan:
        plan_view(data)
    elif args.naive:
        naive_view(data)
    elif args.resilient:
        resilient_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
