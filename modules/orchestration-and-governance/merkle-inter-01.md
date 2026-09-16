---
id: merkle-inter-01
title: Reconcile replicas by a Merkle tree, not key by key — or every sync costs a full scan just to learn nothing changed
topic: orchestration-and-governance
level: intermediate
status: ready
time: 18 min
summary: Two replicas of a store drift apart during a partition, and anti-entropy is finding which keys differ so only those get repaired. Comparing every key — or shipping every key's hash and diffing the lists — costs O(N) work and transfer on every sync, even when the replicas are already identical, which is almost always. A Merkle tree makes the comparison scale with the differences instead of the data: hash each key-value pair into a leaf, hash pairs upward into a binary tree, and compare roots first. Equal roots prove the whole store matches in one comparison and zero transfer; unequal roots are walked downward, descending only the subtrees whose digests differ and pruning the ones that match, so each differing key is isolated in about tree-depth comparisons. On a fixture of 64 keys where two diverge (k27, k29), the Merkle walk finds exactly those two in 17 node comparisons against a 64-key full scan, and settles in a single root comparison when the replicas are identical.
eli5: Two friends each have a copy of the same long list and want to find the few lines that don't match, without reading both lists all the way through. So each folds the list in half and writes one summary number for each half, then a summary of the summaries, up to a single number for the whole list. If their top numbers match, the lists are identical — done, one check. If not, they only open the halves whose summaries disagree, and keep zooming in, ignoring every half that already matches. They reach the differing lines by checking a handful of summaries instead of every line.
---

## Why this module

Reconciling two replicas is mostly the work of confirming they already agree, so a method that costs a full scan every time pays for the whole dataset to discover that nothing changed — and that bill comes due on every sync, forever.

Replicas drift. A network partition, a dropped message, a node that was down for a write — afterward two copies of the same store hold mostly the same data with a few keys out of step, and they have to find and repair exactly those keys. The obvious approach compares them directly: line up the two key sets and check each value, or ship every key's hash across the link and diff the lists. Both are O(N) in work and, worse, O(N) in network transfer, and both cost the same whether a thousand keys differ or none do. Replicas that sync continuously and diverge rarely — the normal case — spend nearly all of that bandwidth to reconfirm agreement they already had. The cost is attached to the size of the data, when it should be attached to the size of the disagreement.

**Comparing replicas key by key costs O(N) work and transfer on every sync regardless of how much actually differs, so the common case — replicas that already agree — pays full price to learn there was nothing to do.**

A Merkle tree fixes the attachment point. Hash every key-value pair into a leaf digest, then hash adjacent digests together, level by level, until a single root digest summarizes the entire store. Two replicas compare roots first: if the roots are equal, every leaf beneath them is equal, so the stores are identical and the sync finishes in one comparison and zero data transfer. If the roots differ, the replicas walk down together, descending only into child subtrees whose digests disagree and pruning every subtree whose digest matches — because a matching digest certifies its whole key range is already in sync. The differing keys fall out in about tree-depth comparisons each, so the cost tracks the differences, not the dataset. This module builds the trees, walks them, and counts the comparisons.

## Concepts

**A leaf digest** is a hash of one key-value pair. Any change to a value changes its leaf digest, and a change to a leaf changes every digest on the path from that leaf to the root.

**The Merkle tree** hashes adjacent digests together, level by level, into a binary tree topped by a single root digest that summarizes the whole store.

```python filename=modules/orchestration-and-governance/code/merkle-inter-01/merkle.py:58-66 COMPLETE
def build_tree(store):
    """Build the Merkle tree over the sorted keys: a list of levels, level 0 the leaves, last level the root."""
    keys = sorted(store)
    level = [h("%s=%s" % (k, store[k])) for k in keys]  # leaf digest per key-value pair
    levels = [level]
    while len(level) > 1:
        level = [h(level[i] + level[i + 1]) for i in range(0, len(level), 2)]
        levels.append(level)
    return keys, levels
```

**The walk** compares the two trees from the root down. A matching digest prunes an entire subtree; a mismatching one is descended into; a mismatching leaf is a differing key.

```python filename=modules/orchestration-and-governance/code/merkle-inter-01/merkle.py:69-82 COMPLETE
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
```

<svg role="img" aria-label="A Merkle tree with a differing leaf: the path from that leaf to the root is marked as differing, while the sibling subtrees whose digests match are pruned" viewBox="0 0 300 120" width="300" height="120">
  <circle cx="150" cy="18" r="6" fill="var(--s2)"/><text x="160" y="21" fill="var(--muted)" font-size="7">root (differs)</text>
  <line x1="146" y1="23" x2="96" y2="43" stroke="var(--s2)"/><line x1="154" y1="23" x2="204" y2="43" stroke="var(--line)"/>
  <circle cx="92" cy="46" r="6" fill="var(--s2)"/><circle cx="208" cy="46" r="6" fill="none" stroke="var(--line)"/><text x="216" y="49" fill="var(--muted)" font-size="7">match → pruned</text>
  <line x1="88" y1="51" x2="66" y2="71" stroke="var(--s2)"/><line x1="96" y1="51" x2="118" y2="71" stroke="var(--line)"/>
  <circle cx="64" cy="74" r="6" fill="var(--s2)"/><circle cx="120" cy="74" r="6" fill="none" stroke="var(--line)"/><text x="128" y="77" fill="var(--muted)" font-size="7">match → pruned</text>
  <line x1="61" y1="79" x2="50" y2="99" stroke="var(--s2)"/><line x1="67" y1="79" x2="78" y2="99" stroke="var(--line)"/>
  <rect x="44" y="99" width="12" height="12" fill="var(--s2)"/><rect x="72" y="99" width="12" height="12" fill="none" stroke="var(--line)"/>
  <text x="30" y="118" fill="var(--muted)" font-size="7">differing leaf</text><text x="90" y="118" fill="var(--muted)" font-size="7">matching leaves (never opened)</text>
</svg>
^ A single differing leaf turns every digest on its root path red; at each level the matching sibling subtree is pruned, so the walk descends one path and ignores the rest of the tree.

**A matching subtree digest certifies its entire key range is in sync, so the walk prunes it — turning reconciliation from a scan of N keys into a descent toward only the keys that actually differ.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/merkle-inter-01/merkle.py

The fixture is two replicas of the same 64 keys, identical except that replica B holds a stale value for two of them.

```json filename=modules/orchestration-and-governance/code/merkle-inter-01/merkle.json:3-4 COMPLETE
  "n_keys": 64,
  "diverged": ["k27", "k29"]
```

Run `--compare` to walk the two trees and report what it finds and what it cost.

```text filename=--compare
COMPARE — the Merkle walk finds the differing keys without scanning all of them
--------------------------------------------------------------------
  keys per replica:        64
  root digest A / B:       00b88702 / f48442d9   (differ)
  differing keys found:    ['k27', 'k29']
  node comparisons:        17   (comparing all keys would be 64)
```

The two root digests differ — 00b88702 against f48442d9 — which is the one-line proof that *something* is out of sync, before a single key has been examined. From there the walk descends, and it finds exactly k27 and k29, the two keys the fixture diverged, with no false positives and no misses. The price was 17 node comparisons against the 64 a full scan would spend. That gap is the whole point: the two differing keys sit near each other, so they share most of their root paths, and every subtree that did not contain them — more than three-quarters of the tree — was pruned on a single matching-digest check. The walk spent its comparisons where the disagreement was and nowhere else, which is precisely the behavior a full scan cannot have, because a full scan does not know where the disagreement is until it has looked everywhere.

<svg role="img" aria-label="Of the 64 leaves, the walk descends only the paths to k27 and k29 and prunes the rest, touching 17 nodes" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">64 leaves; the walk descends only toward k27 and k29</text>
  <line x1="10" y1="86" x2="290" y2="86" stroke="var(--grid)"/>
  <rect x="10" y="76" width="110" height="10" fill="none" stroke="var(--line)"/><text x="30" y="72" fill="var(--muted)" font-size="7">pruned range</text>
  <rect x="120" y="76" width="8" height="10" fill="var(--s2)"/><rect x="136" y="76" width="8" height="10" fill="var(--s2)"/><text x="118" y="72" fill="var(--s2)" font-size="7">k27 k29</text>
  <rect x="152" y="76" width="138" height="10" fill="none" stroke="var(--line)"/><text x="200" y="72" fill="var(--muted)" font-size="7">pruned range</text>
  <path d="M150 20 L124 76" stroke="var(--s2)"/><path d="M150 20 L140 76" stroke="var(--s2)"/>
  <path d="M150 20 L60 70" stroke="var(--line)" stroke-dasharray="2 2"/><path d="M150 20 L230 70" stroke="var(--line)" stroke-dasharray="2 2"/>
  <circle cx="150" cy="18" r="4" fill="var(--s2)"/>
  <text x="6" y="98" fill="var(--muted)" font-size="8">17 node comparisons instead of 64 — cost tracks the two differences, not the dataset</text>
</svg>
^ Only the paths to the two divergent keys are descended; the matching ranges on either side are pruned at a single digest check, so 17 comparisons suffice where a scan needs 64.

## Build

The savings grow with the ratio of data to differences, and they are largest in the case that happens most. Run `--cost`.

```text filename=--cost
COST — Merkle comparisons vs a full key scan
----------------------------------------------------------
  full scan (compare every key):     64 comparisons
  Merkle walk, replicas differ:      17 comparisons
  Merkle walk, replicas identical:   1 comparison  (roots match, done)
```

Three numbers, one lesson. A full scan is 64 comparisons no matter what. The Merkle walk with two differences is 17. And the Merkle walk when the replicas are already identical is 1 — a single root comparison that matches, proving the entire store is in sync and ending the reconciliation with no descent and no data sent. That last row is the one that matters at scale, because replicas that gossip constantly are identical the overwhelming majority of the time, and the full scan pays 64 for every one of those no-op syncs while the tree pays 1. The tree converts the common case from "re-examine everything to confirm nothing changed" into "check one hash." When they do differ, the cost rises only toward the differences — d keys cost roughly d × log(N) — so the method is cheap when there is nothing to do and proportionate when there is. The one bill it never sends is the full-dataset bill for a store that barely moved.

<svg role="img" aria-label="Comparisons: full scan 64, Merkle walk with two differences 17, Merkle walk when identical 1" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">node comparisons per sync (64-key store)</text>
  <line x1="86" y1="18" x2="86" y2="86" stroke="var(--grid)"/>
  <text x="6" y="30" fill="var(--muted)" font-size="8">full scan</text>
  <rect x="86" y="22" width="200" height="12" fill="var(--s2)"/><text x="252" y="32" fill="var(--panel)" font-size="7">64</text>
  <text x="6" y="52" fill="var(--muted)" font-size="8">Merkle diff</text>
  <rect x="86" y="44" width="53" height="12" fill="var(--s1)"/><text x="143" y="54" fill="var(--muted)" font-size="7">17</text>
  <text x="6" y="74" fill="var(--muted)" font-size="8">Merkle same</text>
  <rect x="86" y="66" width="3" height="12" fill="var(--s1)"/><text x="93" y="76" fill="var(--muted)" font-size="7">1 (root matches)</text>
  <text x="6" y="92" fill="var(--muted)" font-size="8">the common case (already in sync) costs one hash instead of a full scan</text>
</svg>
^ A full scan costs 64 comparisons every sync; the Merkle walk costs 17 when two keys differ and just 1 when the replicas already agree — the case that dominates real traffic.

## Definition of done

The self-test pins correctness and cost together: the walk finds exactly the truly-differing keys, costs fewer comparisons than a scan, short-circuits to one comparison when the replicas match, and prunes matching subtrees instead of descending the full tree.

```python filename=modules/orchestration-and-governance/code/merkle-inter-01/merkle.py:131-145 COMPLETE
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
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the walk finds exactly the differing keys, costs fewer comparisons than N, and short-circuits when equal
----------------------------------------------------------------------------------------------------------------------
  the walk finds exactly the keys that truly differ = True (['k27', 'k29'] vs truth ['k27', 'k29'])
  it costs fewer node comparisons than scanning all N keys = True (17 < 64)
  identical replicas settle in a single root comparison = True (1)
  a real difference makes the root digests differ = True (00b88702 vs f48442d9)
  matching subtrees are pruned rather than fully descended = True (17 < full-tree 127)
```

**Done means the tree is proven correct and cheap: the walk finds exactly the two divergent keys (k27, k29) with no false positives or misses, in 17 node comparisons against a 64-key full scan, collapses to a single root comparison when the replicas are identical, and prunes matching subtrees rather than descending all 127 nodes of the full tree.**

## Boss fight

Predict the two ways the tree quietly lies — the mismatch it cannot even start on, and the "match" that is not one. It is tempting to treat equal root digests as absolute proof that two replicas are identical.

The first crack is that the tree only lines up if both replicas partition their keys the same way. The walk compares node at depth d, index i against the *same* position in the other tree, which is only meaningful when both trees put the same keys in the same leaves. Sort the keys differently, use a different branching factor, or — the common real bug — let the two replicas hold *different key sets* (B is missing a key A has), and the leaf positions shift, so every digest above the shift mismatches and the walk reports huge swaths of the tree as different when only one key was actually added. Real anti-entropy systems avoid this by partitioning keys into fixed ranges (hash buckets) rather than into leaves-per-key, so inserting or deleting a key changes one bucket's digest without renumbering the others. The tree compares apples to apples only if both sides built it from the same ranges; otherwise its answer is noise.

```python filename=modules/orchestration-and-governance/code/merkle-inter-01/merkle.py:53-55 COMPLETE
def h(s):
    """A short sha256 hex digest of a string -- the hash a Merkle node stores."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]
```

The second crack is in that digest itself: "equal digests" means "equal hashes," not "equal data," and the gap between them is a hash collision. If two different subtrees hash to the same digest, the walk prunes a range that actually differs and silently declares it in sync — a missed repair that leaves the replicas permanently inconsistent with no error raised. With a full-width cryptographic hash this is astronomically unlikely, but this fixture truncates sha256 to 8 hex digits (32 bits) for readable output, and at 32 bits the birthday bound makes a collision plausible across a large enough store — a demonstration convenience that would be a real bug in production. The lesson is that a Merkle tree trades exact comparison for hash comparison, so its correctness rests entirely on the collision resistance of the hash and the width you keep: use a strong hash, keep enough bits, and remember that the tree proves equality only up to the vanishing probability that two different things hashed the same. Cheap reconciliation is bought with a hash assumption, and the assumption has to hold.

**A Merkle tree makes reconciliation scale with the differences instead of the dataset — one comparison when replicas agree, about depth per difference when they do not — but it compares positions, so both replicas must build the tree over identical key ranges (partition into fixed buckets, not leaves-per-key, or a single insertion renumbers everything), and it compares hashes, so an equal digest proves equality only up to the hash's collision resistance: use a wide, strong hash, because a collision prunes a differing range and leaves it un-repaired.**

## External resources

The Dynamo paper (DeCandia et al., "Dynamo: Amazon's Highly Available Key-value Store") and Cassandra's anti-entropy repair documentation — the canonical uses of Merkle trees over key ranges for replica reconciliation, including the bucket-per-range partitioning that keeps the trees aligned.

Ralph Merkle's original work on hash trees, and any reference on hash collision resistance and the birthday bound — the foundation for why a root digest can stand in for a whole dataset and how wide it must be to do so safely.

The companion "make the read and write quorums overlap" and "merge concurrent updates" modules — Merkle anti-entropy is the background repair that restores consistency between the foreground quorum reads/writes, and it feeds the same merge logic once it has found which keys diverged.
