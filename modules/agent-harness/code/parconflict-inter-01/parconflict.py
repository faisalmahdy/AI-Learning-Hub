"""Serialize conflicting parallel tool calls -- run independent calls at once, but two calls on the same resource where at least one writes are not independent, and batching them concurrently is a data race.

Running the model's tool calls in parallel is a genuine speedup when the calls are independent: calls on different resources, or calls that only read the same resource, cannot interfere, so firing them all at once costs the slowest one instead of the sum. The mistake is to treat every parallel batch as if it were independent. It is not, and the harness has to check.

Two calls conflict when they touch the SAME resource and at least one of them writes it. Write-write is a conflict because both change the same thing and the final state depends on which finishes last -- a race. Read-write is a conflict because the reader may observe the value before, during, or after the writer, so it can read a stale value or a half-applied one, again depending on timing. Only read-read on a shared resource is safe, because neither call changes anything.

Run conflicting calls concurrently and you have a data race: the batch's result depends on timing, so the same calls can produce different outcomes on different runs, and a read can return a value that never coherently existed. That is exactly the class of bug that is invisible in testing (the race usually resolves one way) and corrupts state in production (occasionally it resolves the other).

The fix is to schedule the batch into groups so that no group contains a conflicting pair. Independent calls -- different resources, or read-read -- still share a group and run in parallel; conflicting calls are split into separate groups that run one after another in a defined order. The parallelism is preserved wherever it is safe and removed only where it is not.

The rule: run independent tool calls in parallel, but serialize any two that touch the same resource when at least one writes -- schedule the batch so no parallel group contains a conflicting pair -- because concurrent conflicting calls are a data race whose result depends on timing.

On this fixture five calls are issued: two reads of A (safe together) and three calls on B (two writes and a read, all mutually conflicting). The naive schedule runs all five in one parallel batch that contains conflicts; the safe schedule keeps the two A-reads parallel and serializes the three B-calls. This computes both.

  --conflicts   the pairs of calls that conflict (same resource, at least one write)
  --schedule    the naive one-batch schedule vs a safe grouped schedule, and whether each has a conflicting group
  --check       the naive batch races on the shared resource; the safe schedule serializes the conflicts and keeps the rest parallel

calls is the fixture; the conflict pairs and the two schedules are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "parconflict.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def conflict(a, b):
    """Two calls conflict if they touch the same resource and at least one writes it."""
    return a["resource"] == b["resource"] and (a["mode"] == "write" or b["mode"] == "write")


def conflict_pairs(calls):
    return [(a["id"], b["id"]) for i, a in enumerate(calls) for b in calls[i + 1:] if conflict(a, b)]


def has_conflict_within(group):
    """Does any pair inside this parallel group conflict?"""
    return any(conflict(group[i], group[j])
               for i in range(len(group)) for j in range(i + 1, len(group)))


def safe_schedule(calls):
    """Greedily place each call in the first group that holds no call it conflicts with."""
    groups = []
    for c in calls:
        placed = False
        for g in groups:
            if all(not conflict(c, other) for other in g):
                g.append(c)
                placed = True
                break
        if not placed:
            groups.append([c])
    return groups


# ----------------------------------------------------------------- printing

def ids(group):
    return [c["id"] for c in group]


def conflicts_view(data):
    calls = data["calls"]
    print("CONFLICTS — pairs on the same resource with at least one write")
    print("-" * 56)
    for c in calls:
        print("  %s  resource=%s  mode=%s" % (c["id"], c["resource"], c["mode"]))
    print("  conflicting pairs: %s" % conflict_pairs(calls))
    print("-" * 56)
    print("  read-read on a shared resource is safe; any write makes it a conflict")


def schedule_view(data):
    calls = data["calls"]
    naive = [calls]
    safe = safe_schedule(calls)
    print("SCHEDULE — naive one parallel batch vs a safe grouped schedule")
    print("-" * 60)
    print("  naive batches: %s  conflict inside? %s"
          % ([ids(g) for g in naive], any(has_conflict_within(g) for g in naive)))
    print("  safe  batches: %s  conflict inside? %s"
          % ([ids(g) for g in safe], any(has_conflict_within(g) for g in safe)))
    print("-" * 60)
    print("  the safe schedule keeps the reads of A parallel and serializes the calls on B")


def check(data):
    print("SELF-TEST — the naive batch races on the shared resource; the safe schedule serializes the conflicts and keeps the rest parallel")
    print("-" * 128)
    calls = data["calls"]
    pairs = conflict_pairs(calls)
    naive = [calls]
    safe = safe_schedule(calls)

    conflicts_exist = len(pairs) > 0
    print("  some calls conflict (same resource, a write) = %s (%s)" % (conflicts_exist, pairs))

    read_read_not_conflict = ("c1", "c2") not in pairs
    print("  two reads of the same resource are not a conflict = %s" % read_read_not_conflict)

    naive_batch_races = any(has_conflict_within(g) for g in naive)
    print("  naive: the single parallel batch contains a conflicting pair = %s" % naive_batch_races)

    safe_no_conflict = not any(has_conflict_within(g) for g in safe)
    print("  safe: no parallel group contains a conflicting pair = %s (%s)" % (safe_no_conflict, [ids(g) for g in safe]))

    safe_keeps_independent_parallel = any(set(ids(g)) >= {"c1", "c2"} for g in safe)
    print("  safe: the two independent reads still run in parallel = %s" % safe_keeps_independent_parallel)

    ok = (conflicts_exist and read_read_not_conflict and naive_batch_races
          and safe_no_conflict and safe_keeps_independent_parallel)
    print("-" * 128)
    print("SELF-TEST %s  conflicts_exist=%s  read_read_not_conflict=%s  naive_batch_races=%s  safe_no_conflict=%s  safe_keeps_independent_parallel=%s"
          % ("PASS" if ok else "FAIL", conflicts_exist, read_read_not_conflict,
             naive_batch_races, safe_no_conflict, safe_keeps_independent_parallel))
    return ok


def main():
    p = argparse.ArgumentParser(description="Parallel conflict: run independent tool calls in parallel, but serialize any two that touch the same resource when at least one writes -- schedule the batch so no parallel group contains a conflicting pair -- because concurrent conflicting calls are a data race whose result depends on timing.")
    p.add_argument("--conflicts", action="store_true")
    p.add_argument("--schedule", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("calls=%d  file=%s  (the tool calls are a fixture)" % (len(data["calls"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.conflicts:
        conflicts_view(data)
    elif args.schedule:
        schedule_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
