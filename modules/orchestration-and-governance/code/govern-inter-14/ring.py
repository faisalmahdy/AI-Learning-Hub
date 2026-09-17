"""Assign keys with a hash ring, or losing one worker reshuffles almost every key at once.

A fleet of workers shards keys -- cache entries, sessions, partitions -- by ownership. The obvious rule is
hash(key) modulo N: hash the key, take it mod the worker count, that worker owns it. It balances fine while
N is fixed. The disaster is that N is not fixed. A worker crashes or one is added, and now every key is
hashed mod a different number, so almost every key changes owner at once. In a cache that means a near-total
miss storm -- every shard refetches its whole contents the instant one node blips -- and the resulting load
spike often knocks over more workers, turning a one-node blip into a cascade. The mapping is correct at every
instant; it is the transition that is catastrophic, because mod N couples every key's owner to the exact
count N.

Consistent hashing decouples them. Place the workers at hashed positions on a ring (the hash space wrapped
into a circle), and a key goes to the first worker clockwise from the key's own hashed position. Remove a
worker and only the keys that were sitting in its arc move -- to the next worker clockwise; every other key
keeps its owner, because its clockwise-nearest worker did not change. Adding a worker is the mirror image:
it takes over one arc and nothing else moves. The fraction of keys that move on a membership change is about
1/N, not nearly all of them, and the keys that move are exactly the departed worker's -- the minimum
possible.

On this fixture 24 keys are sharded across 4 workers and then one worker is removed. Under hash-mod-N, 17 of
24 keys (71%) change owner -- a near-total reshuffle. Under the ring, 5 of 24 (21%) move, and every one of
them belonged to the removed worker; the other 19 keys never move. This computes both.

  --assign     where each key lands under mod-N and under the ring, with 4 workers
  --remove     how many keys change owner when one worker is removed, mod-N vs ring
  --check      mod-N reshuffles almost every key; the ring moves only the departed worker's keys

The keys, workers, and virtual-node count are the fixture; every assignment is computed. Stdlib only.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "shard.json"

RING = 1 << 32


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def h(s):
    """Deterministic hash into [0, RING) -- md5 so it is stable across runs and machines."""
    return int(hashlib.md5(s.encode("utf-8")).hexdigest(), 16) % RING


def assign_mod(key, workers):
    """hash(key) mod N -- owner is coupled to the exact worker count."""
    return workers[h(key) % len(workers)]


def build_ring(workers, vnodes):
    """Each worker placed at vnodes hashed positions on the ring; return sorted (pos, worker)."""
    points = []
    for w in workers:
        for v in range(vnodes):
            points.append((h("%s:%d" % (w, v)), w))
    return sorted(points)


def assign_ring(key, ring):
    """First worker clockwise from the key's hashed position (wrapping around)."""
    p = h(key)
    for pos, w in ring:
        if pos >= p:
            return w
    return ring[0][1]


def moved(keys, before, after):
    """Keys whose owner changed between two assignment functions."""
    return [k for k in keys if before(k) != after(k)]


# ----------------------------------------------------------------- printing

def assign_view(data):
    keys, workers, vn = data["keys"], data["workers"], data["vnodes"]
    ring = build_ring(workers, vn)
    print("ASSIGN — owner of each key under mod-N vs the ring (%d workers)" % len(workers))
    print("-" * 52)
    print("  key        mod-N    ring")
    for k in keys:
        print("  %-8s   %-6s   %-6s" % (k, assign_mod(k, workers), assign_ring(k, ring)))
    print("-" * 52)
    counts = {w: sum(1 for k in keys if assign_ring(k, ring) == w) for w in workers}
    print("  ring load per worker: %s" % counts)


def remove_view(data):
    keys, workers, vn = data["keys"], data["workers"], data["vnodes"]
    gone = workers[-1]
    kept = workers[:-1]
    ring_before, ring_after = build_ring(workers, vn), build_ring(kept, vn)
    mod_moved = moved(keys, lambda k: assign_mod(k, workers), lambda k: assign_mod(k, kept))
    ring_moved = moved(keys, lambda k: assign_ring(k, ring_before), lambda k: assign_ring(k, ring_after))
    print("REMOVE — keys that change owner when %s is removed (%d -> %d workers)" % (gone, len(workers), len(kept)))
    print("-" * 52)
    print("  mod-N:  %2d of %d keys move  (%.0f%%)" % (len(mod_moved), len(keys), 100 * len(mod_moved) / len(keys)))
    print("  ring:   %2d of %d keys move  (%.0f%%)" % (len(ring_moved), len(keys), 100 * len(ring_moved) / len(keys)))
    print("-" * 52)
    owned_by_gone = [k for k in ring_moved if assign_ring(k, ring_before) == gone]
    print("  ring's moved keys all belonged to %s: %s" % (gone, len(owned_by_gone) == len(ring_moved)))


def check(data):
    print("SELF-TEST — mod-N reshuffles almost every key; the ring moves only the departed worker's keys")
    print("-" * 96)
    keys, workers, vn = data["keys"], data["workers"], data["vnodes"]
    gone = workers[-1]
    kept = workers[:-1]
    ring_before, ring_after = build_ring(workers, vn), build_ring(kept, vn)
    mod_moved = moved(keys, lambda k: assign_mod(k, workers), lambda k: assign_mod(k, kept))
    ring_moved = moved(keys, lambda k: assign_ring(k, ring_before), lambda k: assign_ring(k, ring_after))

    mod_reshuffles = len(mod_moved) > len(keys) / 2
    print("  mod-N moves more than half the keys = %s (%d of %d)" % (mod_reshuffles, len(mod_moved), len(keys)))

    ring_moves_few = len(ring_moved) < len(mod_moved) / 2
    print("  the ring moves far fewer keys than mod-N = %s (%d vs %d)" % (ring_moves_few, len(ring_moved), len(mod_moved)))

    ring_moves_only_gone = all(assign_ring(k, ring_before) == gone for k in ring_moved)
    print("  every key the ring moves belonged to the removed worker = %s" % ring_moves_only_gone)

    kept_keys_stay = all(assign_ring(k, ring_before) == assign_ring(k, ring_after)
                         for k in keys if assign_ring(k, ring_before) != gone)
    print("  no key of a surviving worker moves under the ring = %s" % kept_keys_stay)

    counts = [sum(1 for k in keys if assign_ring(k, ring_before) == w) for w in workers]
    ring_balances = max(counts) <= 2 * (len(keys) / len(workers))
    print("  the ring keeps load roughly balanced = %s (per-worker %s)" % (ring_balances, counts))

    ok = mod_reshuffles and ring_moves_few and ring_moves_only_gone and kept_keys_stay and ring_balances
    print("-" * 96)
    print("SELF-TEST %s  mod_reshuffles=%s  ring_moves_few=%s  ring_moves_only_gone=%s  kept_keys_stay=%s  ring_balances=%s"
          % ("PASS" if ok else "FAIL", mod_reshuffles, ring_moves_few, ring_moves_only_gone, kept_keys_stay, ring_balances))
    return ok


def main():
    p = argparse.ArgumentParser(description="Assign keys with a hash ring so a membership change moves only ~1/N keys.")
    p.add_argument("--assign", action="store_true")
    p.add_argument("--remove", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("keys=%d  workers=%d  vnodes=%d  file=%s  (the keys and workers are a fixture)"
          % (len(data["keys"]), len(data["workers"]), data["vnodes"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.assign:
        assign_view(data)
    elif args.remove:
        remove_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
