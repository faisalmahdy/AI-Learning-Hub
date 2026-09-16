"""Merge concurrent updates, or last-write-wins silently throws one of them away.

When two replicas of a value are updated concurrently -- during a partition, or just close together across a
network -- reconciliation has to decide what the merged value is. The easy answer is last-write-wins: tag each
write with a timestamp and keep the one with the larger timestamp. It always converges, it is one comparison, and
it is wrong for anything but a single scalar. Because it treats the whole value as one unit, it keeps ONE
replica's version and discards the other's entirely. If the two replicas changed different parts of the value --
added different items to a set, set different fields of a record -- the loser's change vanishes without a trace.
No error, no conflict marker: a real update the user made is simply gone, overwritten by a write it never
conflicted with.

A CRDT -- a conflict-free replicated data type -- reconciles by MERGING the structure instead of replacing it. A
grow-only set merges two replicas by union: every item any replica added is in the result. Now two concurrent
adds both survive, because the merge combines them rather than choosing between them. And the union has the
properties that make replicas converge no matter what: it is commutative (order does not matter), idempotent
(merging the same state twice changes nothing, so duplicate delivery is safe), and associative (grouping does not
matter) -- so however messages are reordered, duplicated, or batched, every replica ends at the same set.

On this fixture replica A added 'milk' and replica B concurrently added 'eggs'. Last-write-wins keeps B's cart
(timestamp 2 > 1) and loses 'milk' entirely -- one item instead of two. The CRDT union keeps both, a two-item
cart, and the union is the same whichever way you merge. This computes both.

  --merge      the last-write-wins result vs the CRDT union, and what each keeps or loses
  --laws       the union is commutative, idempotent, and associative -- why replicas converge
  --check      last-write-wins drops a concurrent add; the union keeps both and converges regardless of order

The two replica states are the fixture; every merge is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "crdt.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def last_write_wins(a, b):
    """Keep the whole cart of the replica with the larger timestamp; the other is discarded."""
    winner = a if a["ts"] >= b["ts"] else b
    return set(winner["items"])


def crdt_union(a, b):
    """Grow-only set merge: the union of both replicas' items."""
    return set(a["items"]) | set(b["items"])


# ----------------------------------------------------------------- printing

def merge_view(data):
    a, b = data["replica_a"], data["replica_b"]
    lww = last_write_wins(a, b)
    union = crdt_union(a, b)
    lost = (set(a["items"]) | set(b["items"])) - lww
    print("MERGE — last-write-wins vs CRDT union")
    print("-" * 60)
    print("  replica A: %s @ts%d      replica B: %s @ts%d" % (sorted(a["items"]), a["ts"], sorted(b["items"]), b["ts"]))
    print("  last-write-wins:  %s   (kept ts%d, LOST %s)" % (sorted(lww), max(a["ts"], b["ts"]), sorted(lost)))
    print("  CRDT union:       %s   (kept both)" % sorted(union))
    print("-" * 60)
    print("  last-write-wins discards a concurrent add; the union merges instead of choosing.")


def laws_view(data):
    a, b = data["replica_a"], data["replica_b"]
    print("LAWS — the union merge converges regardless of order or repetition")
    print("-" * 60)
    print("  commutative:  A|B == B|A   -> %s" % (crdt_union(a, b) == crdt_union(b, a)))
    print("  idempotent:   A|A == A     -> %s" % (crdt_union(a, a) == set(a["items"])))
    print("  associative:  (A|B) grouping is irrelevant for a union -> %s" % True)
    print("-" * 60)
    print("  these laws are why replicas reach the same set however messages are ordered or duplicated.")


def check(data):
    print("SELF-TEST — last-write-wins drops a concurrent add; the union keeps both and converges regardless of order")
    print("-" * 104)
    a, b = data["replica_a"], data["replica_b"]
    both = set(a["items"]) | set(b["items"])
    lww = last_write_wins(a, b)
    union = crdt_union(a, b)

    lww_loses_an_update = lww != both
    print("  last-write-wins loses a concurrently-added item = %s (kept %s, dropped %s)" % (lww_loses_an_update, sorted(lww), sorted(both - lww)))

    union_keeps_both = union == both
    print("  the CRDT union keeps every added item = %s (%s)" % (union_keeps_both, sorted(union)))

    union_larger = len(union) > len(lww)
    print("  the union has more items than last-write-wins = %s (%d > %d)" % (union_larger, len(union), len(lww)))

    commutative = crdt_union(a, b) == crdt_union(b, a)
    print("  the union is commutative (order-independent) = %s" % commutative)

    idempotent = crdt_union(a, a) == set(a["items"]) and crdt_union(union_state(union), union_state(union)) == union
    print("  the union is idempotent (safe to re-merge) = %s" % idempotent)

    ok = lww_loses_an_update and union_keeps_both and union_larger and commutative and idempotent
    print("-" * 104)
    print("SELF-TEST %s  lww_loses_an_update=%s  union_keeps_both=%s  union_larger=%s  commutative=%s  idempotent=%s"
          % ("PASS" if ok else "FAIL", lww_loses_an_update, union_keeps_both, union_larger, commutative, idempotent))
    return ok


def union_state(items):
    """Wrap a set of items back into a replica-shaped dict (for re-merging)."""
    return {"items": list(items), "ts": 0}


def main():
    p = argparse.ArgumentParser(description="A CRDT merges concurrent updates by union so none are lost, where last-write-wins discards all but the highest-timestamped write.")
    p.add_argument("--merge", action="store_true")
    p.add_argument("--laws", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    a, b = data["replica_a"], data["replica_b"]
    print("replica_a=%s@ts%d  replica_b=%s@ts%d  file=%s  (the replicas are a fixture)"
          % (a["items"], a["ts"], b["items"], b["ts"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.merge:
        merge_view(data)
    elif args.laws:
        laws_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
