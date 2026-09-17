---
id: conshash-inter-01
title: Place keys on a ring, not with hash % N — adding one node under modulo hashing moves almost every key at once
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: Sharding keys across N nodes needs a rule mapping each key to a node, and the obvious one is modulo hashing — node = hash(key) % N. It spreads keys evenly and is one line, and it has a catastrophic property: the answer depends on N, so the moment N changes (add a node to scale out, or one dies) almost every key's hash % N lands on a different node. For a cache that is a near-total miss storm (every key refetched from the origin at once); for a stateful store it is moving almost all the data across the network. A single node joining a 4-node cluster invalidates roughly 80% of placements, so the cheap rule turns scaling — the very operation you add nodes for — into a self-inflicted outage. Consistent hashing breaks the coupling to N: put both the nodes and the keys on a ring, and each key is owned by the first node clockwise. Now a node owns a contiguous arc, and adding a node splits only one arc — the new node takes the keys between it and the previous node, stealing them from the single node that owned that span, while every other arc is untouched. So adding one node moves only about K/N keys, all to the new node, never between two existing nodes. On a fixture of four nodes on a 0–99 ring and ten keys, going from N=4 to N=5 moves 8 of 10 keys (80%) under modulo hashing but only 2 of 10 (20%) under the ring, both to the new node, with no key moving between two old nodes.
eli5: Imagine assigning students to study rooms by "student number mod number-of-rooms." It works until you open one more room — now the divisor changes, and nearly every student is reassigned to a different room, a huge shuffle for one new room. A smarter way: arrange the rooms around a circle and send each student to the next room clockwise from where their number lands. Now opening a new room only pulls in the students sitting in the slice just before it; everyone else stays exactly where they were. One new room, one small slice of students moved — not a whole reshuffle.
---

## Why this module

Sharding is easy to get working and easy to make un-scalable in the same line of code. `hash(key) % N` distributes keys beautifully — until the day you add the node you provisioned to handle growth, and the placement rule reshuffles nearly the entire cluster at once. The scheme that made sharding trivial is the scheme that makes scaling an outage.

Sharding keys across N nodes — cache servers, database partitions — needs a rule mapping each key to a node. The obvious rule is modulo hashing: node = hash(key) % N. It spreads keys evenly and is one line, and it has a catastrophic property: the answer depends on N, so the moment N changes — you add a node to scale out, or one dies — almost every key's hash % N lands on a different node than before. For a cache that means a near-total miss storm, every key refetched from the origin at once; for a stateful store it means moving almost all the data across the network to rebalance. A single node joining a 4-node cluster can invalidate roughly 80% of the placements, so the cheap rule makes scaling the cluster — the exact operation you add nodes to perform — a self-inflicted outage.

Consistent hashing fixes the coupling between the placement and N. Put both the nodes and the keys on a ring (a circular hash space); each key is owned by the first node clockwise from it. Now a node owns a contiguous arc of the ring — the span from the previous node up to itself — and adding a node only splits *one* arc: the new node inserts at its position and takes over the keys between it and the previous node, stealing them from the single node that used to own that arc. Every other key is untouched, because every other arc is unchanged. So adding one node to N moves only about K/N keys (the new node's fair share), each moved key goes to the new node, and no key bounces between two existing nodes. This module shards ten keys both ways and counts the moves.

**Modulo hashing couples key placement to N, so adding or removing a node remaps almost every key at once (a cache-miss storm or mass data move); a hash ring makes each node own a contiguous arc, so a node add moves only the keys in the one arc it splits (~K/N), all to the new node, leaving every other key in place.**

## Concepts

**Modulo hashing** maps a key by `hash % N`, so the node it lands on is a function of N — change N and the map changes for nearly every key.

```python filename=modules/orchestration-and-governance/code/conshash-inter-01/conshash.py:43-46 COMPLETE
def mod_assign(keys, node_names):
    """Modulo hashing: key -> node index hash % N, mapped to a node name by that index."""
    n = len(node_names)
    return {k["id"]: node_names[k["hash"] % n] for k in keys}
```

**Ring assignment** places nodes on a circular hash space and sends each key to the first node clockwise. A node's identity, not N, determines ownership, so adding a node only changes the keys near it.

```python filename=modules/orchestration-and-governance/code/conshash-inter-01/conshash.py:49-55 COMPLETE
def ring_assign(keys, node_positions):
    """Consistent hashing: each key goes to the first node clockwise on the ring (wrapping past the top)."""
    ring = sorted((pos, name) for name, pos in node_positions.items())
    out = {}
    for k in keys:
        out[k["id"]] = next((name for pos, name in ring if pos >= k["pos"]), ring[0][1])
    return out
```

<svg role="img" aria-label="A hash ring with four nodes at positions around a circle, each owning the arc of keys leading up to it clockwise; a new node inserted splits only one arc" viewBox="0 0 300 128" width="300" height="128">
  <text x="6" y="12" fill="var(--muted)" font-size="8">nodes on a ring; a key goes to the next node clockwise</text>
  <circle cx="110" cy="72" r="44" fill="none" stroke="var(--line)"/>
  <circle cx="110" cy="28" r="4" fill="var(--s1)"/><text x="104" y="22" fill="var(--muted)" font-size="7">n1</text>
  <circle cx="150" cy="88" r="4" fill="var(--s1)"/><text x="156" y="92" fill="var(--muted)" font-size="7">n2</text>
  <circle cx="88" cy="112" r="4" fill="var(--s1)"/><text x="72" y="118" fill="var(--muted)" font-size="7">n3</text>
  <circle cx="66" cy="72" r="4" fill="var(--s1)"/><text x="48" y="75" fill="var(--muted)" font-size="7">n4</text>
  <circle cx="145" cy="52" r="3" fill="var(--s2)"/><text x="150" y="50" fill="var(--muted)" font-size="7">n5 (new)</text>
  <circle cx="130" cy="40" r="2" fill="var(--ink)"/><text x="134" y="38" fill="var(--muted)" font-size="6">key</text>
  <path d="M130,40 A44,44 0 0,1 145,52" fill="none" stroke="var(--ink)" stroke-dasharray="2 2"/>
  <text x="190" y="60" fill="var(--muted)" font-size="7">key → next node</text>
  <text x="190" y="72" fill="var(--muted)" font-size="7">clockwise (n5)</text>
  <text x="190" y="92" fill="var(--muted)" font-size="7">n5 splits only</text>
  <text x="190" y="104" fill="var(--muted)" font-size="7">n4's old arc</text>
</svg>
^ Each node owns the arc of ring positions leading clockwise into it; inserting n5 between two nodes captures only the keys in the slice just before it, leaving every other node's arc — and its keys — unchanged.

**Modulo placement is a function of N, so it changes everywhere when N changes; ring placement is a function of node identity, so adding a node perturbs only the single arc that node splits.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/conshash-inter-01/conshash.py

The fixture is four nodes on a 0–99 ring, a fifth node to add, and ten keys.

```json filename=modules/orchestration-and-governance/code/conshash-inter-01/conshash.json:3-4 COMPLETE
  "nodes": {"n1": 10, "n2": 35, "n3": 60, "n4": 85},
  "new_node": {"n5": 72},
```

Run `--remap` to add the node under both schemes.

```text filename=--remap
REMAP — keys moved when adding a node (10 keys, 4 -> 5 nodes)
--------------------------------------------------------------
  modulo hashing (hash % N): 8 of 10 keys move  (80%)
  consistent hashing (ring): 2 of 10 keys move  (20%)  -> ['k5', 'k6']
--------------------------------------------------------------
  every moved key goes to the new node n5; the other 8 keys never move.
```

Adding one node moves 8 of the 10 keys under modulo hashing and only 2 under the ring. Under modulo hashing, every key's assignment was `hash % 4`, and now it is `hash % 5` — a different function, so 80% of the keys compute a new node and must move. That 80% is not bad luck; it is the expected `(N−1)/N` for a modulo change, so the effect only worsens as clusters grow: adding a 10th node to a 9-node cluster still reshuffles about 90% of keys. Under consistent hashing, only k5 and k6 move, and both go to the new node n5 — because n5 was inserted at ring position 72, between n3 (60) and n4 (85), so it steals exactly the keys whose ring position falls in (60, 72], which were previously owned by n4. Every key outside that little arc keeps its owner. This is the difference between a rebalance that touches the whole cluster and one that touches a single node's neighborhood.

## Build

The ring view shows *why* only two keys moved: only one arc changed hands. Run `--ring`.

```text filename=--ring
RING — node arcs and key ownership before/after adding n5@72
------------------------------------------------------------------
  node positions (before): {'n1': 10, 'n2': 35, 'n3': 60, 'n4': 85}
  key k0  @pos 5    owner n1 -> n1
  key k1  @pos 15   owner n2 -> n2
  key k2  @pos 28   owner n2 -> n2
  key k3  @pos 42   owner n3 -> n3
  key k4  @pos 50   owner n3 -> n3
  key k5  @pos 65   owner n4 -> n5  <- moved to n5
  key k6  @pos 70   owner n4 -> n5  <- moved to n5
  key k7  @pos 78   owner n4 -> n4
  key k8  @pos 88   owner n1 -> n1
  key k9  @pos 95   owner n1 -> n1
```

Read the owner columns. Every key keeps its owner except k5 (position 65) and k6 (position 70), which move from n4 to n5. Those two sit in the arc (60, 72] — after n3 at 60 and before the newly inserted n5 at 72 — so they are exactly the keys n5 steals from n4. Notice what does *not* happen: k7 at position 78 is still owned by n4 (it is in the remaining (72, 85] arc), and no key anywhere moves from one old node to another old node. That is the structural guarantee — a node add only ever transfers keys from one existing node to the new node, never disturbs unrelated nodes — and it is what makes the operation cheap and safe: only n4 and n5 do any work, and only for the keys in the split arc. The move set is just the keys whose owner differs between the two assignments.

```python filename=modules/orchestration-and-governance/code/conshash-inter-01/conshash.py:58-60 COMPLETE
def moved(before, after):
    """Keys whose owning node changed between two assignments."""
    return [kid for kid in before if before[kid] != after[kid]]
```

<svg role="img" aria-label="Bars comparing keys moved on one node add: modulo hashing moves 8 of 10, consistent hashing moves 2 of 10" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">keys moved when adding one node: 8/10 vs 2/10</text>
  <line x1="30" y1="86" x2="290" y2="86" stroke="var(--line)"/>
  <g transform="translate(70,0)">
  <rect x="0" y="24" width="46" height="62" fill="var(--s2)"/><text x="4" y="98" fill="var(--muted)" font-size="7">modulo</text><text x="14" y="20" fill="var(--muted)" font-size="7">8/10</text>
  </g>
  <g transform="translate(190,0)">
  <rect x="0" y="70" width="46" height="16" fill="var(--s1)"/><text x="0" y="98" fill="var(--muted)" font-size="7">ring</text><text x="14" y="66" fill="var(--muted)" font-size="7">2/10</text>
  </g>
  <text x="30" y="102" fill="var(--muted)" font-size="7"></text>
</svg>
^ Modulo hashing reshuffles 8 of the 10 keys on a single node add, while the ring moves only 2 — the fair share of one new node — a four-fold reduction that grows with cluster size.

## Definition of done

The self-test pins the modulo blowup, the ring's small move set, and the two structural guarantees.

```python filename=modules/orchestration-and-governance/code/conshash-inter-01/conshash.py:109-119 COMPLETE
    mod_moved = moved(mod_assign(keys, names4), mod_assign(keys, names5))
    mod_remaps_most = len(mod_moved) >= 0.7 * len(keys)
    print("  modulo hashing moves most keys on one node add = %s (%d of %d)" % (mod_remaps_most, len(mod_moved), len(keys)))

    before = ring_assign(keys, nodes4)
    after = ring_assign(keys, nodes5)
    ring_moved = moved(before, after)
    ring_remaps_few = len(ring_moved) <= 0.3 * len(keys)
    print("  consistent hashing moves few keys = %s (%d of %d)" % (ring_remaps_few, len(ring_moved), len(keys)))

    ring_fewer = len(ring_moved) < len(mod_moved)
    print("  the ring moves strictly fewer keys than modulo = %s (%d < %d)" % (ring_fewer, len(ring_moved), len(mod_moved)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — modulo hashing remaps most keys; the ring remaps few, all to the new node, with no moves between two old nodes
----------------------------------------------------------------------------------------------------------------------------
  modulo hashing moves most keys on one node add = True (8 of 10)
  consistent hashing moves few keys = True (2 of 10)
  the ring moves strictly fewer keys than modulo = True (2 < 8)
  every moved key goes to the new node = True (['k5', 'k6'])
  no key moves between two existing nodes = True
```

**Done means the rehashing cost and its fix are proven on real assignments: modulo hashing moves 8 of 10 keys on one node add while the ring moves only 2, and those two both go to the new node with no key moving between two existing nodes — so scaling a ring-sharded cluster disturbs one node's neighborhood, not the whole cluster.**

## Boss fight

Predict two ways the plain ring is not yet production-ready, because uniform placement and stateful movement each need more than the basic construction.

The first trap is that a ring with one point per node is badly *unbalanced*, so consistent hashing in practice means virtual nodes. With N random points on the ring, the arc lengths vary a lot — some nodes own a big span and others a sliver — so load is uneven, and when a node leaves, its entire arc dumps onto the single next node clockwise rather than spreading across the cluster. The fix is to place each physical node at many positions on the ring (virtual nodes / vnodes — often 100–200 per node), so each physical node owns many small arcs scattered around the ring. Now arc lengths average out (balanced load), and when a node is removed its many small arcs are inherited by many different successors (its load spreads evenly instead of crushing one neighbor). This is also the knob for heterogeneous hardware: give a bigger machine more vnodes so it owns a proportionally larger share. The bare "one point per node" ring shows the *idea* — minimal remapping — but real systems always use vnodes to also get *balance*, which is why my fixture's 20% is higher than the ideal K/N would predict at scale.

<svg role="img" aria-label="A ring where each physical node appears at many scattered positions as virtual nodes, so arcs are small and even and each physical node owns many little slices around the ring" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">virtual nodes: each machine sits at many ring points → balance</text>
  <circle cx="80" cy="60" r="38" fill="none" stroke="var(--line)"/>
  <g fill="var(--s1)">
  <circle cx="80" cy="22" r="3"/><circle cx="108" cy="38" r="3"/><circle cx="118" cy="72" r="3"/><circle cx="92" cy="96" r="3"/><circle cx="56" cy="92" r="3"/><circle cx="44" cy="60" r="3"/>
  </g>
  <g fill="var(--s2)">
  <circle cx="98" cy="28" r="3"/><circle cx="116" cy="55" r="3"/><circle cx="104" cy="86" r="3"/><circle cx="64" cy="97" r="3"/><circle cx="45" cy="74" r="3"/><circle cx="50" cy="42" r="3"/>
  </g>
  <text x="140" y="44" fill="var(--s1)" font-size="7">● node A (6 vnodes)</text>
  <text x="140" y="60" fill="var(--s2)" font-size="7">● node B (6 vnodes)</text>
  <text x="140" y="80" fill="var(--muted)" font-size="7">each machine owns many small</text>
  <text x="140" y="92" fill="var(--muted)" font-size="7">arcs → even load, even failover</text>
</svg>
^ Giving each physical machine many virtual positions on the ring breaks its ownership into many small scattered arcs, so load is even and — when a machine leaves — its many arcs are inherited by many different successors rather than dumped on one neighbor.

The second trap is that consistent hashing minimizes *which* keys move, but moving them is still a real, non-atomic operation that has to be made safe. For a cache the movement is free — the moved keys just miss once and refetch — but for a stateful store the data in the transferred arc must actually be copied to the new node, and during that copy the key exists in two places, so reads and writes must be routed correctly (often served by the old owner until handoff completes) to avoid losing writes or reading staleness. Consistent hashing tells you the transfer is *small and local* (one arc between two nodes), which is exactly what makes the copy feasible without a cluster-wide freeze, but it does not make the transfer atomic — that needs a handoff protocol, and it composes with the replication and quorum rules from the companion modules (a key is usually stored on the next R nodes clockwise, not just one, so a membership change reshuffles replica sets too). And the ring must be agreed upon: every client and node needs a consistent view of the current membership and vnode layout, so the ring itself is shared cluster state that a coordination layer (a gossip protocol, or a coordination service) must keep in sync, or two clients will disagree about who owns a key. So consistent hashing is the placement primitive, and a real system wraps it in vnodes for balance, a handoff protocol for safe movement, replication across successive nodes, and an agreed membership view.

**The bare ring gives minimal remapping but not balance, so production consistent hashing uses many virtual nodes per physical node (for even load, even redistribution on removal, and weighting by capacity); and because minimal-but-real key movement still has to be executed safely, it must be paired with a handoff protocol, replication across the next R nodes clockwise (composing with quorum), and an agreed cluster membership view — the ring places keys, but the surrounding machinery makes the placement balanced, movable, and consistent.**

## External resources

The original consistent hashing paper (Karger et al.) and Amazon's Dynamo paper — the hash ring, the minimal-remapping property, and virtual nodes for load balancing and heterogeneous capacity.

Any distributed-caching or sharding documentation (Cassandra's token ring, memcached client hashing, Ketama) — how vnodes are configured, how membership changes redistribute keys, and why modulo hashing is avoided for elastic clusters.

The companion quorum and anti-entropy modules in this topic — a ring usually replicates each key across the next R nodes clockwise, so consistent hashing composes with quorum sizing for consistency and anti-entropy for repairing the replicas a membership change moves.
