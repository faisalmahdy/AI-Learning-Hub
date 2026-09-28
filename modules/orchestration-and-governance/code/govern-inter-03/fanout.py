#!/usr/bin/env python3
"""Fan-out needs a partition contract: overlapping owners clobber, gaps drop work.

Fanning a job out to parallel workers is the easy part; the correctness lives in
who owns what. If two workers are handed the same file, both write it and the
last one wins -- the other's work is silently lost. If a file is handed to no
worker, it is never written at all. Both bugs pass every "the workers ran"
check, because every worker did run; the damage is in the assignment, not the
execution. The fix is a contract checked BEFORE dispatch: the assignment must be
a true partition of the work -- disjoint (no file owned twice) and complete
(no file owned zero times).

  --plan          the worker assignments, and which files overlap or fall in a gap
  --dispatch      run the naive fan-out and count lost writes and never-written files
  --contract      the partition check that rejects the plan before any work is lost
  --check         the naive plan loses writes and drops a file; the contract catches both

Stdlib only. No network, no real subprocesses -- workers are simulated as writes
to a dict. Deterministic. Point the contract at your own fan-out assignment.
"""
import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "plan.json"


def load():
    data = json.loads(PLAN.read_text(encoding="utf-8"))
    return data["files"], data["workers"]


# ------------------------------------------------------------- the contract

def overlaps(workers):
    """Files handed to more than one worker -> {file: [owners]}. These get clobbered."""
    owners = {}
    for w, files in workers.items():
        for f in files:
            owners.setdefault(f, []).append(w)
    return {f: ws for f, ws in owners.items() if len(ws) > 1}


def gaps(files, workers):
    """Files handed to no worker -> never written."""
    owned = set()
    for fs in workers.values():
        owned |= set(fs)
    return [f for f in files if f not in owned]


def is_partition(files, workers):
    """The contract: the assignment is a true partition -- disjoint and complete."""
    return not overlaps(workers) and not gaps(files, workers)


# ------------------------------------------------------------- the (simulated) run

def dispatch(files, workers):
    """Simulate the fan-out: each worker writes its files in a fixed order. A later
    write to the same file overwrites an earlier one -- last writer wins. Returns
    the final store, the lost writes, and the files nobody wrote."""
    store = {}
    lost = []
    for w in sorted(workers):                       # deterministic dispatch order
        for f in workers[w]:
            if f in store:
                lost.append((f, store[f], w))       # (file, clobbered owner, winner)
            store[f] = w
    never = [f for f in files if f not in store]
    return store, lost, never


# ------------------------------------------------------------------- printing

def plan_view(files, workers):
    print("PLAN — %d files across %d workers" % (len(files), len(workers)))
    print("-" * 62)
    for w in sorted(workers):
        print("  %-9s owns %s" % (w, workers[w]))
    ov, gp = overlaps(workers), gaps(files, workers)
    print("-" * 62)
    print("  overlaps (owned twice): %s" % (ov or "none"))
    print("  gaps (owned zero times): %s" % (gp or "none"))
    print("  a valid fan-out plan has neither; this one has both.")


def dispatch_view(files, workers):
    store, lost, never = dispatch(files, workers)
    print("NAIVE DISPATCH — run the workers, count the damage")
    print("-" * 62)
    for f, loser, winner in lost:
        print("  LOST WRITE  %-8s  %s's work overwritten by %s" % (f, loser, winner))
    for f in never:
        print("  NEVER WRITTEN  %-8s  (no worker owned it)" % f)
    print("-" * 62)
    print("  %d lost write(s), %d file(s) never written. Every worker ran; the plan"
          % (len(lost), len(never)))
    print("  was the bug, so nothing errored -- the work just quietly vanished.")


def contract_view(files, workers):
    print("CONTRACT — check the partition BEFORE dispatch")
    print("-" * 62)
    ok = is_partition(files, workers)
    if ok:
        print("  plan is a valid partition: dispatch is safe.")
    else:
        print("  REJECTED: not a partition.")
        for f, ws in overlaps(workers).items():
            print("    overlap: %s owned by %s" % (f, ws))
        for f in gaps(files, workers):
            print("    gap: %s owned by nobody" % f)
        print("  fix the assignment and re-check; no work is dispatched until it passes.")
    return ok


def check(files, workers):
    print("SELF-TEST — the naive plan loses work; the contract catches it first")
    print("-" * 62)
    store, lost, never = dispatch(files, workers)

    loses_writes = len(lost) > 0
    print("  naive dispatch loses at least one write = %s (%d lost)" % (loses_writes, len(lost)))
    drops_file = len(never) > 0
    print("  naive dispatch never writes at least one file = %s (%s)" % (drops_file, never))

    rejected = not is_partition(files, workers)
    print("  the contract rejects this plan before dispatch = %s" % rejected)

    # a repaired plan (disjoint + complete) dispatches with zero loss.
    fixed = {"alpha": ["f1", "f2", "f3"], "beta": ["f4", "f5"], "gamma": ["f6", "f7", "f8"]}
    _, lost2, never2 = dispatch(files, fixed)
    fixed_clean = is_partition(files, fixed) and not lost2 and not never2
    print("  a repaired partition dispatches with no loss = %s" % fixed_clean)

    # every lost write corresponds to an overlap the contract named.
    ov_files = set(overlaps(workers))
    lost_files = {f for f, _, _ in lost}
    consistent = lost_files <= ov_files
    print("  every lost write was a file the contract flagged as an overlap = %s" % consistent)

    det = dispatch(files, workers)[1] == dispatch(files, workers)[1]
    ok = loses_writes and drops_file and rejected and fixed_clean and consistent and det
    print("-" * 62)
    print("SELF-TEST %s  loses=%s  drops=%s  rejected=%s  repaired_clean=%s  consistent=%s"
          % ("PASS" if ok else "FAIL", loses_writes, drops_file, rejected, fixed_clean, consistent))
    return ok


def main():
    p = argparse.ArgumentParser(description="A partition contract for a worker fan-out.")
    p.add_argument("--plan", action="store_true")
    p.add_argument("--dispatch", action="store_true")
    p.add_argument("--contract", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    files, workers = load()
    print("files=%d  workers=%d  file=%s  (plan is a fixture)" % (len(files), len(workers), PLAN.name))
    print("")

    if args.check:
        return 0 if check(files, workers) else 1
    if args.plan:
        plan_view(files, workers)
    elif args.dispatch:
        dispatch_view(files, workers)
    elif args.contract:
        contract_view(files, workers)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
