---
id: govern-inter-14
title: Assign keys with a hash ring — or losing one worker reshuffles almost every key at once
topic: orchestration-and-governance
level: intermediate
status: ready
time: 21 min
summary: Sharding keys by hash(key) mod N balances fine until N changes, at which point almost every key is hashed mod a different number and changes owner — a cache-miss storm from one node blip. A consistent-hash ring places workers at hashed positions and gives each key to the next worker clockwise, so removing a worker moves only the keys in its arc. On 24 keys across 4 workers, removing one moves 17 of 24 (71%) under mod-N but only 5 of 24 (21%) under the ring, and every moved key belonged to the departed worker.
eli5: Imagine assigning house numbers by "number mod how-many-mail-carriers." Add one carrier and suddenly almost every house is reassigned — chaos. Instead, put carriers at fixed spots on a big loop and each house goes to the next carrier clockwise. Now if one carrier quits, only the houses in their stretch get handed off; everyone else keeps their carrier.
---

## Why this module

Sharding by hash-mod-N works perfectly until the moment a worker joins or leaves, and then it moves almost everything at once.

A fleet of workers divides up keys — cache entries, user sessions, data partitions — by ownership, and each key needs a home. The obvious rule is hash the key and take it modulo the worker count: `hash(key) % N` picks the owning worker. With N fixed, this balances keys evenly and is trivial to compute. The problem is that N is not fixed. Workers crash, workers get added for capacity, and the instant N changes, every key is suddenly being taken modulo a different number.

Taking a value mod 4 versus mod 3 gives unrelated answers for almost every input, so almost every key changes owner at once. In a distributed cache, that means a near-total miss storm: the moment one node blips and N drops by one, essentially every shard discovers it no longer owns its entries and every entry has to be refetched from the origin. The origin, sized for a trickle of misses, gets hit with the entire keyspace at once, and the resulting load spike frequently knocks over more workers — turning a single-node blip into a cascading outage. The mapping is correct at every instant; it is the transition that is catastrophic, because mod-N couples every key's owner to the exact count N.

Consistent hashing breaks that coupling. Hash the workers onto a ring — the hash space wrapped into a circle — and give each key to the first worker found clockwise from the key's own hashed position. Now a key's owner depends only on which worker is nearest clockwise, not on how many workers there are. Remove a worker and only the keys sitting in its arc move, handed to the next worker clockwise; every other key keeps its owner, because its clockwise-nearest worker did not change. Adding a worker is the mirror image: the newcomer claims one arc and nothing else moves. The fraction of keys that move on a membership change is about 1/N, and they are exactly the departed worker's keys — the minimum any scheme could move.

On the fixture, 24 keys are sharded across 4 workers and then one worker is removed. Under hash-mod-N, 17 of 24 keys (71%) change owner — a near-total reshuffle. Under the ring, 5 of 24 (21%) move, and every one of them belonged to the removed worker; the other 19 keys never move.

**Hash-mod-N couples every key's owner to the exact worker count, so one membership change reshuffles almost all keys and can storm the origin; a consistent-hash ring makes a key's owner its clockwise-nearest worker, so a change moves only that worker's ~1/N keys and leaves the rest untouched.**

## Concepts

The defect in mod-N is that the divisor is global state every key depends on. The owner of a key is `hash(key) % N`, and N is a single number shared by all keys — change it and you change the answer for nearly all of them simultaneously. There is no locality: the keys that move are not concentrated on the failed worker, they are scattered across the entire keyspace, because mod-4 and mod-3 partition the integers into completely different residue classes. So the blast radius of one worker leaving is the whole fleet. The scheme is optimal for a static cluster and pessimal for a dynamic one, and real clusters are always dynamic.

Consistent hashing replaces the shared divisor with local geometry. Every worker and every key gets a position on a ring by hashing; a key belongs to the first worker clockwise. The crucial property is that this ownership is decided by adjacency on the ring, which is a local relationship: a key cares only about the nearest worker in one direction, and it is completely indifferent to workers elsewhere on the ring or to the total count. When a worker vanishes, the arc it covered now falls through to the next worker clockwise, so those keys — and only those — change hands. Every key outside that arc still finds the same clockwise-nearest worker it had before. Locality is the whole trick: a change is felt only in its own neighborhood.

<svg role="img" aria-label="A ring with four workers at positions around it and a key that walks clockwise to the next worker; when that worker is removed, the key falls through to the following one" viewBox="0 0 470 200" width="470" height="200">
  <rect x="0" y="0" width="470" height="200" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">a key goes to the next worker clockwise on the ring</text>
  <circle cx="150" cy="115" r="70" fill="none" stroke="var(--line)"/>
  <g fill="var(--acc-line)"><circle cx="150" cy="45" r="6"/><circle cx="220" cy="115" r="6"/><circle cx="150" cy="185" r="6"/><circle cx="80" cy="115" r="6"/></g>
  <text x="140" y="38" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">w0</text>
  <text x="228" y="118" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">w1</text>
  <text x="140" y="200" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">w2</text>
  <text x="58" y="118" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">w3</text>
  <circle cx="199" cy="66" r="4" fill="var(--s2)"/>
  <text x="205" y="60" font-family="var(--mono)" font-size="8" fill="var(--s2)">key</text>
  <path d="M203,70 A70,70 0 0,1 216,105" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
  <text x="300" y="70" font-family="var(--mono)" font-size="8" fill="var(--ink)">key lands on w1 (next clockwise)</text>
  <text x="300" y="120" font-family="var(--mono)" font-size="8" fill="var(--muted)">remove w1 → key falls to w2;</text>
  <text x="300" y="134" font-family="var(--mono)" font-size="8" fill="var(--muted)">keys past w0, w3 don't notice</text>
</svg>
^ Each key walks clockwise to the nearest worker; if that worker is removed, only the keys in its arc fall through to the next one, and every key whose nearest worker still exists is unaffected.

Virtual nodes fix the one weakness of the basic ring, which is balance. If each worker occupies a single ring position, the arcs between them are random and uneven — one worker might own a huge arc and another a sliver, so load is lumpy, and when a worker leaves, its entire (possibly large) arc dumps onto a single successor. The fix is to place each worker at many hashed positions (virtual nodes), so each worker owns many small arcs scattered around the ring instead of one big one. Now load averages out across the many arcs, and when a worker leaves, its many small arcs are inherited by many different successors rather than all landing on one. More virtual nodes means smoother balance, at the cost of a larger ring to search.

This is why consistent hashing is the standard for sharding anything that must survive membership changes gracefully — distributed caches (memcached clients, the original Akamai use case), partitioned databases and key-value stores (Dynamo, Cassandra, Riak), and load balancers pinning sessions to backends. The property they all need is the same: adding or removing capacity should disturb a 1/N slice of the keyspace, not all of it, so scaling and failure are routine events instead of cluster-wide reshuffles. Any time you see `hash % N` deciding placement across a set of nodes that can change, it is a reshuffle storm waiting for its trigger.

**Mod-N ties every key to a shared divisor, so a count change relocates nearly all keys with no locality; a ring decides ownership by clockwise adjacency, a local relationship, so a change touches only one arc — and virtual nodes spread each worker into many small arcs to keep load balanced and inheritance spread.**

## Worked example

The fixture is a set of keys, a set of workers, and a virtual-node count.

```json filename=modules/orchestration-and-governance/code/govern-inter-14/shard.json:3-4 COMPLETE
  "vnodes": 100,
  "workers": ["w0", "w1", "w2", "w3"]
```

Four workers, each placed at 100 hashed positions on the ring for balance, and 24 keys. Ownership under mod-N is the worker at `hash(key) % 4`; under the ring it is the first worker clockwise from the key's hashed position. The hash is md5 so the results are identical on every machine.

```python filename=modules/orchestration-and-governance/code/govern-inter-14/ring.py:46-53 COMPLETE
def h(s):
    """Deterministic hash into [0, RING) -- md5 so it is stable across runs and machines."""
    return int(hashlib.md5(s.encode("utf-8")).hexdigest(), 16) % RING


def assign_mod(key, workers):
    """hash(key) mod N -- owner is coupled to the exact worker count."""
    return workers[h(key) % len(workers)]
```

The ring is built by hashing each worker at its virtual-node positions and sorting; a key walks clockwise to the first position at or past its own hash.

```python filename=modules/orchestration-and-governance/code/govern-inter-14/ring.py:56-71 COMPLETE
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
```

The count of moved keys is just the keys whose owner differs before and after — one helper comparing two assignment functions.

```python filename=modules/orchestration-and-governance/code/govern-inter-14/ring.py:74-76 COMPLETE
def moved(keys, before, after):
    """Keys whose owner changed between two assignment functions."""
    return [k for k in keys if before(k) != after(k)]
```

Both schemes balance the 24 keys across 4 workers well enough. The difference only appears when a worker leaves. Predict: removing w3 forces every key back through a mod-3 (instead of mod-4) computation, moving most of them, while on the ring only the keys in w3's arcs move. Remove w3 and count.

```text filename=modules/orchestration-and-governance/code/govern-inter-14/ring.py --remove
REMOVE — keys that change owner when w3 is removed (4 -> 3 workers)
----------------------------------------------------
  mod-N:  17 of 24 keys move  (71%)
  ring:    5 of 24 keys move  (21%)
----------------------------------------------------
  ring's moved keys all belonged to w3: True
```

Mod-N moves 17 of 24 keys — 71% of the keyspace changes owner because the divisor went from 4 to 3. Most of those 17 keys did not belong to w3 at all; they were owned by w0, w1, or w2 and got relocated anyway, purely because the modulus changed. That is the reshuffle storm: keys that had a perfectly good, still-alive owner are torn away from it. The ring moves 5 keys — 21% — and the check confirms all 5 belonged to w3. Every key owned by a surviving worker kept its owner. The ring did the minimum work; mod-N did far more, and all the extra was pure churn.

<svg role="img" aria-label="When w3 is removed, mod-N moves 17 of 24 keys scattered across all workers, while the ring moves only 5 keys, all formerly owned by w3" viewBox="0 0 470 195" width="470" height="195">
  <rect x="0" y="0" width="470" height="195" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">keys that change owner when w3 leaves (of 24)</text>
  <text x="30" y="44" font-family="var(--mono)" font-size="9" fill="var(--s2)">mod-N: 17 move</text>
  <g fill="var(--s2)">
    <rect x="30" y="52" width="14" height="14"/><rect x="48" y="52" width="14" height="14"/><rect x="66" y="52" width="14" height="14"/><rect x="84" y="52" width="14" height="14"/><rect x="102" y="52" width="14" height="14"/><rect x="120" y="52" width="14" height="14"/><rect x="138" y="52" width="14" height="14"/><rect x="156" y="52" width="14" height="14"/><rect x="174" y="52" width="14" height="14"/>
    <rect x="30" y="70" width="14" height="14"/><rect x="48" y="70" width="14" height="14"/><rect x="66" y="70" width="14" height="14"/><rect x="84" y="70" width="14" height="14"/><rect x="102" y="70" width="14" height="14"/><rect x="120" y="70" width="14" height="14"/><rect x="138" y="70" width="14" height="14"/><rect x="156" y="70" width="14" height="14"/>
  </g>
  <text x="200" y="66" font-family="var(--mono)" font-size="8" fill="var(--s2)">scattered across all workers — pure churn</text>
  <text x="30" y="118" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">ring: 5 move</text>
  <g fill="var(--acc-line)"><rect x="30" y="126" width="14" height="14"/><rect x="48" y="126" width="14" height="14"/><rect x="66" y="126" width="14" height="14"/><rect x="84" y="126" width="14" height="14"/><rect x="102" y="126" width="14" height="14"/></g>
  <text x="130" y="137" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">all 5 were w3's — the minimum</text>
  <g fill="var(--panel)" stroke="var(--line)"><rect x="30" y="150" width="14" height="14"/><rect x="48" y="150" width="14" height="14"/><rect x="66" y="150" width="14" height="14"/><rect x="84" y="150" width="14" height="14"/><rect x="102" y="150" width="14" height="14"/><rect x="120" y="150" width="14" height="14"/></g>
  <text x="130" y="161" font-family="var(--mono)" font-size="8" fill="var(--muted)">ring: 19 keys never move</text>
</svg>
^ Removing one worker relocates 17 scattered keys under mod-N but only 5 under the ring — and those 5 are exactly w3's, while the other 19 keep their owner.

## Build

Reproduce the reshuffle. Pure standard library — md5 for a deterministic hash — so the 17-of-24 and 5-of-24 counts come out identically everywhere.

Run `--assign` for the per-key owners, `--remove` for the move counts, `--check` for the gate. The self-test pins the whole contrast: mod-N moves most keys, the ring moves far fewer, and the ring's moved keys are exactly the departed worker's while every survivor's key stays put.

```python filename=modules/orchestration-and-governance/code/govern-inter-14/ring.py:120-123 COMPLETE
    mod_reshuffles = len(mod_moved) > len(keys) / 2
    print("  mod-N moves more than half the keys = %s (%d of %d)" % (mod_reshuffles, len(mod_moved), len(keys)))

    ring_moves_few = len(ring_moved) < len(mod_moved) / 2
    print("  the ring moves far fewer keys than mod-N = %s (%d vs %d)" % (ring_moves_few, len(ring_moved), len(mod_moved)))
```

The locality flags are what prove the ring moved the right keys, not just fewer of them — one checks every moved key was the departed worker's, the other checks no survivor's key budged.

```python filename=modules/orchestration-and-governance/code/govern-inter-14/ring.py:126-131 COMPLETE
    ring_moves_only_gone = all(assign_ring(k, ring_before) == gone for k in ring_moved)
    print("  every key the ring moves belonged to the removed worker = %s" % ring_moves_only_gone)

    kept_keys_stay = all(assign_ring(k, ring_before) == assign_ring(k, ring_after)
                         for k in keys if assign_ring(k, ring_before) != gone)
    print("  no key of a surviving worker moves under the ring = %s" % kept_keys_stay)
```

```text filename=modules/orchestration-and-governance/code/govern-inter-14/ring.py --check
SELF-TEST — mod-N reshuffles almost every key; the ring moves only the departed worker's keys
------------------------------------------------------------------------------------------------
  mod-N moves more than half the keys = True (17 of 24)
  the ring moves far fewer keys than mod-N = True (5 vs 17)
  every key the ring moves belonged to the removed worker = True
  no key of a surviving worker moves under the ring = True
  the ring keeps load roughly balanced = True (per-worker [9, 5, 5, 5])
------------------------------------------------------------------------------------------------
SELF-TEST PASS  mod_reshuffles=True  ring_moves_few=True  ring_moves_only_gone=True  kept_keys_stay=True  ring_balances=True
```

<svg role="img" aria-label="Bar chart: mod-N moves 17 of 24 keys, the ring moves 5 of 24; a dashed line marks the 5-key minimum the ring achieves" viewBox="0 0 470 165" width="470" height="165">
  <rect x="0" y="0" width="470" height="165" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">keys relocated when one of four workers leaves (of 24)</text>
  <line x1="60" y1="140" x2="450" y2="140" stroke="var(--line)"/>
  <line x1="60" y1="113" x2="450" y2="113" stroke="var(--acc-line)" stroke-dasharray="3 3"/>
  <text x="330" y="109" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">5 = necessary minimum</text>
  <rect x="90" y="45" width="90" height="95" fill="var(--s2)"/>
  <text x="105" y="38" font-family="var(--mono)" font-size="9" fill="var(--s2)">mod-N: 17</text>
  <text x="100" y="70" font-family="var(--mono)" font-size="8" fill="var(--panel)">~12 wasted</text>
  <rect x="290" y="113" width="90" height="27" fill="var(--acc-line)"/>
  <text x="300" y="106" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">ring: 5</text>
</svg>
^ Mod-N relocates 17 keys against a necessary minimum of 5, so about 12 of its moves are pure churn; the ring hits the minimum exactly.

Five True flags. Mod_reshuffles: mod-N moves 17 of 24, past half. Ring_moves_few: the ring moves 5, less than a third of mod-N's churn. Ring_moves_only_gone: all 5 moved keys were w3's. Kept_keys_stay: no key of a surviving worker moved. Ring_balances: the ring's per-worker load is [9, 5, 5, 5], within the balance bound. The two "only w3's keys move" flags are the ones that show the ring is not just moving fewer keys but the right keys — the minimum a correct rebalance can move.

**The ring's win is not merely a smaller count — every one of its moved keys belonged to the removed worker and every survivor's key stayed, which is the provably minimal amount of movement, while mod-N's extra churn is all keys that had a healthy owner.**

## Definition of done

You are done when you reproduce the move counts and can explain why the ring localizes the change.

Concretely: `--remove` shows mod-N moving 17 of 24 keys and the ring moving 5, all formerly w3's; `--check` prints PASS with five True flags and per-worker load [9, 5, 5, 5]. You can explain that mod-N couples every key to a shared divisor so a count change has no locality and scatters moves across the whole keyspace, that a ring decides ownership by clockwise adjacency so only the departed worker's arc moves, and that virtual nodes place each worker at many positions to keep load balanced and spread inheritance across successors.

The habit to carry: shard with a consistent-hash ring (with virtual nodes) anywhere the set of nodes can change — caches, partitioned stores, session pinning — and treat plain `hash(key) % N` as safe only for a truly fixed N. When a cache or shard cluster suffers a load spike or miss storm every time a node is added or fails, suspect mod-N placement; the cure is to move ownership onto a ring so a membership change disturbs only its own neighborhood.

## Boss fight

The instructive failure is a cache cluster that melts its database every time it autoscales.

A read-heavy service fronts its database with a fleet of cache nodes, sharded by `hash(key) % N`. Under load, autoscaling adds cache nodes — and each time it does, the database load spikes hard enough to trip alarms, because adding one node changes N and remaps almost the entire keyspace, so nearly every cache node misses on nearly every key at once and stampedes the database. Autoscaling, meant to relieve load, causes an outage. The fix is consistent hashing: put the cache nodes on a ring with virtual nodes, so adding a node steals only its ~1/N arc from its neighbors and only that slice of keys has to be refetched. Scaling becomes a gentle, local warm-up instead of a cluster-wide cold cache.

Your turn, two moves. First, quantify the scaling case (adding, not removing). Add a fifth worker and count moves under each scheme; confirm mod-N again reshuffles most keys (4 to 5 is as disruptive as 4 to 3) while the ring moves only about 1/5, all onto the new worker — so both scaling up and scaling down are local on the ring and global under mod-N. Second, study virtual nodes and balance. Drop vnodes from 100 to 1 and look at the per-worker load and at how w3's keys are inherited when it leaves; confirm the load gets lumpy and w3's keys pile onto a single successor, then raise vnodes and watch balance and inheritance-spread both improve — the knob that trades ring size for evenness.

## External resources

The paper that introduced consistent hashing, Karger et al.'s "Consistent Hashing and Random Trees" (1997), motivates it exactly as this module does — distributing cache load so that adding or removing a cache changes only a small fraction of the mapping.

Amazon's Dynamo paper (2007) is the canonical systems application, using a consistent-hash ring with virtual nodes ("tokens") for partitioning and replication, and its discussion of load balance is the production version of the virtual-node argument here.

Any distributed-systems course or the documentation of Cassandra, Riak, or a memcached client library covers the ring, virtual nodes, and the rebalancing behavior, and comparing their choices of virtual-node count shows the balance-versus-cost trade-off in practice.
