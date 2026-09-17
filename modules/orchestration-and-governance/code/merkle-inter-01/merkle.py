"""Compare replicas by a Merkle tree, not key by key -- or reconciling two copies costs a full scan every time they sync.

Two replicas of a store drift apart during a partition: one misses a few writes, and afterward they must agree again.
Anti-entropy is finding which keys differ so only those get repaired. The obvious way is to line the two key sets up
and compare every key -- or ship every key's hash across the network and diff the lists. That costs O(N) work and O(N)
transfer every single time two replicas sync, even when they are already identical, which for replicas that sync
constantly and differ rarely is almost all of the time. You pay for the whole dataset to discover that nothing
changed.

A Merkle tree turns that into a comparison that scales with the DIFFERENCES, not the data. Hash each key-value pair
into a leaf digest, then hash pairs of digests up into a binary tree until a single root digest summarizes the whole
store. Two replicas first compare just their roots: if the roots match, every leaf underneath matches, so the replicas
are identical and the sync is done in ONE comparison and no data transfer. If the roots differ, walk downward,
descending only into the child subtrees whose digests disagree and pruning the ones that match -- because a matching
subtree digest certifies that its entire range is already in sync. Each differing key is isolated in about tree-depth
comparisons, so d differences cost roughly d x log(N), not N.

On this fixture two replicas hold the same 64 keys but disagree on two of them (k27 and k29, one replica missed those
writes). Comparing all 64 keys is 64 comparisons whether or not anything differs. The Merkle walk finds exactly k27
and k29, touching far fewer nodes; and when the two replicas are identical, it settles in a single root comparison.
This computes both.

  --compare   the differing keys the Merkle walk finds, and the node comparisons it costs vs comparing all N keys
  --cost      the walk cost when the replicas differ, and the single-comparison cost when they are identical
  --check     the walk finds exactly the truly-differing keys, costs fewer comparisons than N, and short-circuits when equal

The two replicas are the fixture; every digest is a real sha256 and every count is measured. Stdlib only.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "merkle.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def stores(data):
    """Build the two replicas from the fixture: B equals A except on the diverged keys, where B is stale."""
    keys = ["k%02d" % i for i in range(data["n_keys"])]
    a = {k: "v%d" % i for i, k in enumerate(keys)}
    b = dict(a)
    for k in data["diverged"]:
        b[k] = b[k] + "-STALE"
    return a, b


def h(s):
    """A short sha256 hex digest of a string -- the hash a Merkle node stores."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


def build_tree(store):
    """Build the Merkle tree over the sorted keys: a list of levels, level 0 the leaves, last level the root."""
    keys = sorted(store)
    level = [h("%s=%s" % (k, store[k])) for k in keys]  # leaf digest per key-value pair
    levels = [level]
    while len(level) > 1:
        level = [h(level[i] + level[i + 1]) for i in range(0, len(level), 2)]
        levels.append(level)
    return keys, levels


def diff(keys, a_levels, b_levels):
    """Walk both trees from the root, descending only mismatched subtrees; return (differing_keys, comparisons)."""
    comparisons = [0]

    def descend(depth, idx):
        comparisons[0] += 1
        if a_levels[depth][idx] == b_levels[depth][idx]:
            return []                       # this subtree's digest matches: whole range already in sync
        if depth == 0:
            return [keys[idx]]              # a differing leaf: this exact key diverged
        return descend(depth - 1, 2 * idx) + descend(depth - 1, 2 * idx + 1)

    top = len(a_levels) - 1
    return descend(top, 0), comparisons[0]


def true_diff(a, b):
    """The keys that actually differ between the two stores -- the ground truth to check the walk against."""
    return sorted(k for k in a if a[k] != b.get(k))


# ----------------------------------------------------------------- printing

def compare_view(data):
    a, b = stores(data)
    keys, a_lv = build_tree(a)
    _, b_lv = build_tree(b)
    found, comps = diff(keys, a_lv, b_lv)
    print("COMPARE — the Merkle walk finds the differing keys without scanning all of them")
    print("-" * 68)
    print("  keys per replica:        %d" % len(keys))
    print("  root digest A / B:       %s / %s   (%s)" % (a_lv[-1][0], b_lv[-1][0], "differ" if a_lv[-1][0] != b_lv[-1][0] else "match"))
    print("  differing keys found:    %s" % found)
    print("  node comparisons:        %d   (comparing all keys would be %d)" % (comps, len(keys)))
    print("-" * 68)
    print("  matching subtree digests are pruned, so the walk only descends toward the two real differences.")


def cost_view(data):
    a, b = stores(data)
    keys, a_lv = build_tree(a)
    _, b_lv = build_tree(b)
    _, comps_diff = diff(keys, a_lv, b_lv)
    _, comps_same = diff(keys, a_lv, a_lv)
    print("COST — Merkle comparisons vs a full key scan")
    print("-" * 58)
    print("  full scan (compare every key):     %d comparisons" % len(keys))
    print("  Merkle walk, replicas differ:      %d comparisons" % comps_diff)
    print("  Merkle walk, replicas identical:   %d comparison  (roots match, done)" % comps_same)
    print("-" * 58)
    print("  identical replicas cost one root check; differing ones cost about depth per difference, not N.")


def check(data):
    print("SELF-TEST — the walk finds exactly the differing keys, costs fewer comparisons than N, and short-circuits when equal")
    print("-" * 118)
    a, b = stores(data)
    keys, a_lv = build_tree(a)
    _, b_lv = build_tree(b)
    found, comps = diff(keys, a_lv, b_lv)
    truth = true_diff(a, b)

    finds_exactly = found == truth
    print("  the walk finds exactly the keys that truly differ = %s (%s vs truth %s)" % (finds_exactly, found, truth))

    cheaper_than_scan = comps < len(keys)
    print("  it costs fewer node comparisons than scanning all N keys = %s (%d < %d)" % (cheaper_than_scan, comps, len(keys)))

    _, comps_same = diff(keys, a_lv, a_lv)
    short_circuits = comps_same == 1
    print("  identical replicas settle in a single root comparison = %s (%d)" % (short_circuits, comps_same))

    roots_differ = a_lv[-1][0] != b_lv[-1][0]
    print("  a real difference makes the root digests differ = %s (%s vs %s)" % (roots_differ, a_lv[-1][0], b_lv[-1][0]))

    matching_subtree_pruned = comps < 2 * len(keys) - 1
    print("  matching subtrees are pruned rather than fully descended = %s (%d < full-tree %d)" % (matching_subtree_pruned, comps, 2 * len(keys) - 1))

    ok = finds_exactly and cheaper_than_scan and short_circuits and roots_differ and matching_subtree_pruned
    print("-" * 118)
    print("SELF-TEST %s  finds_exactly=%s  cheaper_than_scan=%s  short_circuits=%s  roots_differ=%s  matching_subtree_pruned=%s"
          % ("PASS" if ok else "FAIL", finds_exactly, cheaper_than_scan, short_circuits, roots_differ, matching_subtree_pruned))
    return ok


def main():
    p = argparse.ArgumentParser(description="Merkle-tree anti-entropy: compare replica root digests and descend only mismatched subtrees, so reconciliation scales with the number of differences instead of the dataset size.")
    p.add_argument("--compare", action="store_true")
    p.add_argument("--cost", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("keys=%d  diverged=%s  file=%s  (the two replicas are a fixture)" % (data["n_keys"], data["diverged"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.compare:
        compare_view(data)
    elif args.cost:
        cost_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
