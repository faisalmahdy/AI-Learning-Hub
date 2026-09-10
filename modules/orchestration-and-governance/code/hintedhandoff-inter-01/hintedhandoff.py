"""Store a hint for a down replica and replay it on recovery -- otherwise a write during an outage is a copy lost forever.

A replicated store keeps N copies of each key so that the data survives a node failing. But there is a window the naive
version handles badly: a write that ARRIVES while one of the replicas is temporarily down. The coordinator can reach the
other replicas and write the value to them, but the down replica gets nothing, so the write lands on fewer than N nodes.
That is not automatically corrected: when the down replica comes back, it has no idea it missed a write -- it just has an
old value (or no value) for that key -- so the key stays under-replicated indefinitely, one copy short of its durability
target, until some slow background reconciliation happens to notice. During that window the key is more fragile than it
should be: it now has fewer live copies, so it can be lost by fewer subsequent failures than its replication factor was
meant to tolerate.

HINTED HANDOFF closes this window. When the coordinator cannot reach a replica for a write, it does not drop that replica's
copy -- it writes the value to a healthy node as a HINT: a stored note that says 'this value belongs to the down replica,
deliver it when it comes back.' The write is accepted (so write availability is preserved even with a replica down), and
the missing copy is not lost, just parked. When the down replica recovers, the node holding the hint replays it -- hands the
value over to the now-healthy replica -- and deletes the hint. The key is back to full replication automatically, without
waiting for a background repair sweep, because the system remembered exactly which write which replica missed and delivered
it the moment it could.

This is the write-time complement to read repair (which fixes staleness when a stale replica is read): hinted handoff fixes
it at WRITE time by remembering the miss, so recovery restores replication proactively rather than lazily. It is what lets
a store stay available for writes during a partial outage (accept the write, hint the down node) while still converging to
full replication once the outage ends.

The rule: when a write cannot reach a replica because it is temporarily down, store the value as a hint on a healthy node
and replay it to the replica when it recovers (hinted handoff), because otherwise the write lands on fewer than N replicas
and stays under-replicated until a background sweep notices -- hinted handoff both keeps writes available during the outage
and restores full replication automatically on recovery.

On this fixture a write of 'v1' arrives while replica C is down. Without hinted handoff, only A and B get it (2 of 3), and C
still lacks it even after recovery. With hinted handoff, A and B get it and A stores a hint for C; when C recovers, A
replays the hint and C receives 'v1', so all 3 replicas hold it. This computes both.

  --write     the write with C down: which replicas get the value, and (with hinting) the hint stored for C
  --recover   after C comes back: no-hint leaves C missing the write; hinted replays the hint so C gets it
  --check     without hints the write stays under-replicated after recovery; hinted handoff restores full replication

replicas, the down replica, the value, and the hint holder are the fixture; every stored copy, hint, and recovery is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "hintedhandoff.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def do_write(data, use_hints):
    """Write the value to every reachable replica; the down replica is dropped, or hinted if use_hints."""
    stored = {}
    hints = []
    for r in data["replicas"]:
        if r == data["down_during_write"]:
            if use_hints:
                hints.append({"holder": data["hint_holder"], "target": r, "value": data["value"]})
        else:
            stored[r] = data["value"]
    return stored, hints


def recover(stored, hints, recovered):
    """The recovered replica comes back; any hints targeting it are replayed (delivered) and removed."""
    stored = dict(stored)
    remaining = []
    for h in hints:
        if h["target"] == recovered:
            stored[h["target"]] = h["value"]  # replay the hint to the now-healthy replica
        else:
            remaining.append(h)
    return stored, remaining


def replicas_with_value(stored, replicas, value):
    return [r for r in replicas if stored.get(r) == value]


# ----------------------------------------------------------------- printing

def write_view(data):
    down = data["down_during_write"]
    ns, nh = do_write(data, use_hints=False)
    hs, hh = do_write(data, use_hints=True)
    print("WRITE — value %r arrives while replica %s is down" % (data["value"], down))
    print("-" * 62)
    print("  NO HINT:  stored on %s ; hints: %s" % (sorted(ns), nh))
    print("            replica %s got nothing -- its copy is dropped" % down)
    print("  HINTED:   stored on %s ; hint: %s" % (sorted(hs), hh))
    print("            replica %s's copy is parked as a hint on %s" % (down, data["hint_holder"]))
    print("-" * 62)
    print("  both accept the write on the reachable replicas; only hinting remembers %s's copy." % down)


def recover_view(data):
    down = data["down_during_write"]
    val, reps = data["value"], data["replicas"]
    ns, nh = do_write(data, use_hints=False)
    hs, hh = do_write(data, use_hints=True)
    ns2, _ = recover(ns, nh, down)
    hs2, hh2 = recover(hs, hh, down)
    print("RECOVER — replica %s comes back; hints (if any) are replayed" % down)
    print("-" * 64)
    print("  NO HINT:  after recovery, replicas with %r = %s  (%d of %d)"
          % (val, sorted(replicas_with_value(ns2, reps, val)), len(replicas_with_value(ns2, reps, val)), len(reps)))
    print("  HINTED:   after recovery, replicas with %r = %s  (%d of %d) ; hints left: %s"
          % (val, sorted(replicas_with_value(hs2, reps, val)), len(replicas_with_value(hs2, reps, val)), len(reps), hh2))
    print("-" * 64)
    print("  the hint replay hands %s its missed write; without hints, %s stays short a copy." % (down, down))


def check(data):
    print("SELF-TEST — without hints the write stays under-replicated after recovery; hinted handoff restores full replication")
    print("-" * 116)
    down, val, reps = data["down_during_write"], data["value"], data["replicas"]
    ns, nh = do_write(data, use_hints=False)
    hs, hh = do_write(data, use_hints=True)

    down_missed_write = down not in ns and down not in hs
    print("  the down replica %s received no direct copy = %s" % (down, down_missed_write))

    hint_stored_for_down = any(h["target"] == down for h in hh)
    print("  hinted mode parked a hint for %s = %s (%s)" % (down, hint_stored_for_down, hh))

    ns2, _ = recover(ns, nh, down)
    hs2, hh2 = recover(hs, hh, down)

    nohint_stays_missing = down not in replicas_with_value(ns2, reps, val)
    print("  no-hint: %s still lacks the write after recovery = %s (replicas with it: %s)"
          % (down, nohint_stays_missing, sorted(replicas_with_value(ns2, reps, val))))

    hint_replayed = down in replicas_with_value(hs2, reps, val)
    print("  hinted: %s receives the write on recovery via hint replay = %s" % (down, hint_replayed))

    hinted_full_replication = len(replicas_with_value(hs2, reps, val)) == len(reps) and len(replicas_with_value(ns2, reps, val)) < len(reps)
    print("  hinted reaches full replication, no-hint does not = %s (%d of %d vs %d of %d)"
          % (hinted_full_replication, len(replicas_with_value(hs2, reps, val)), len(reps), len(replicas_with_value(ns2, reps, val)), len(reps)))

    ok = down_missed_write and hint_stored_for_down and nohint_stays_missing and hint_replayed and hinted_full_replication
    print("-" * 116)
    print("SELF-TEST %s  down_missed_write=%s  hint_stored_for_down=%s  nohint_stays_missing=%s  hint_replayed=%s  hinted_full_replication=%s"
          % ("PASS" if ok else "FAIL", down_missed_write, hint_stored_for_down, nohint_stays_missing, hint_replayed, hinted_full_replication))
    return ok


def main():
    p = argparse.ArgumentParser(description="Hinted handoff: when a write cannot reach a replica because it is temporarily down, store the value as a hint on a healthy node and replay it to the replica when it recovers, because otherwise the write lands on fewer than N replicas and stays under-replicated until a background sweep notices -- hinted handoff both keeps writes available during the outage and restores full replication automatically on recovery.")
    p.add_argument("--write", action="store_true")
    p.add_argument("--recover", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("replicas=%s  down_during_write=%s  value=%r  hint_holder=%s  file=%s  (the replica set and outage are a fixture)"
          % (data["replicas"], data["down_during_write"], data["value"], data["hint_holder"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.write:
        write_view(data)
    elif args.recover:
        recover_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
