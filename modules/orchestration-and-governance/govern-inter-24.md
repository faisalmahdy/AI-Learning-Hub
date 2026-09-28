---
id: govern-inter-24
title: Require a majority to elect a leader — or a network partition elects two and they both accept writes
topic: orchestration-and-governance
level: intermediate
status: ready
time: 17 min
summary: A cluster elects one leader so there is a single authority for writes. The danger is the network partition: nodes split into groups that cannot see each other, and each group, unable to reach the others, may elect a new leader. If the election rule lets any group elect its own side, a partition produces one leader per group — split-brain, where two leaders each accept writes and the state diverges with no principled way to merge afterward. The fix is to require a majority: a candidate must be backed by more than half the whole cluster, and since two disjoint groups cannot both hold more than half, at most one leader is ever elected across any partition. The price is availability: a split that leaves no group with a majority elects nobody and refuses writes until it heals — unavailable but consistent, the correct trade. On a 5-node cluster (majority 3), a 3-vs-2 split elects exactly 1 leader under the majority rule but 2 under the any-group rule; a 2-2-1 three-way split elects 0 under majority but 3 under any-group.
eli5: A club can only have one president at a time. If the members get separated into two rooms during a storm and each room just picks its own president, you end up with two presidents giving conflicting orders. The rule that prevents this: to become president you need votes from more than half of ALL members — and since more than half can only be in one room, only one room can crown a president. If the members split so evenly that no room has more than half, nobody becomes president until they're back together, which is annoying but safer than two.
---

## Why this module

Electing a leader is supposed to give the cluster a single authority, but a partition can turn one election into several simultaneous ones, and unless the rule forbids it, each isolated group crowns its own leader.

A cluster runs a leader election so that exactly one node is the authority for writes at any time. The hard case is the network partition: the nodes split into groups that cannot communicate, and from inside each group the other nodes look dead — indistinguishable from a crashed leader. So each group is tempted to do the natural thing and elect a fresh leader to keep serving. If the election rule permits it — "a candidate wins if it can gather votes from its own reachable nodes" — then a partition into two groups produces two leaders. Both believe they are the sole authority, both accept writes, and the two copies of the state diverge. This is split-brain, and it is the worst kind of failure because nothing looks broken from inside either group; each side is happily serving, and the damage only surfaces when the partition heals and you have two conflicting histories with no correct way to reconcile them.

**If the election rule lets any isolated group elect its own leader, a network partition produces one leader per group — split-brain, where multiple leaders each accept writes and the state diverges irreconcilably.**

The fix is a majority quorum: a candidate must be backed by more than half of the *whole* cluster, not just its own group. This one rule makes split-brain impossible, by counting. Two disjoint groups cannot both contain more than half the nodes, because their sizes would then sum to more than the cluster's total — so at most one group can ever hold a majority, and at most one leader is ever elected, across any partition however the nodes split. The cost is availability: if the partition leaves no group with a majority, nobody is elected and the cluster refuses writes until it heals. This module elects leaders both ways across several partitions and shows the majority rule cap the count at one while the any-group rule splits the brain.

## Concepts

**A leader election** chooses one node as the write authority. The invariant it must preserve is *at most one leader at a time*.

**A network partition** splits the cluster into groups that cannot see each other. From inside a group, the unreachable nodes are indistinguishable from crashed ones, so each group may try to elect.

**The any-group rule** lets a group elect a leader from its own votes alone. Under a partition this elects one leader per group — split-brain.

**The majority rule** requires more than half the whole cluster's votes to elect.

```python filename=modules/orchestration-and-governance/code/govern-inter-24/quorum.py:42-50 COMPLETE
def majority_threshold(nodes):
    """Votes needed for a majority of the whole cluster: more than half."""
    return nodes // 2 + 1


def leaders(groups, nodes, majority):
    """The group sizes that manage to elect a leader under the chosen rule."""
    threshold = majority_threshold(nodes) if majority else 1
    return [g for g in groups if g >= threshold]
```

**At most one majority exists.** Two disjoint groups cannot both exceed half the cluster, so the majority rule guarantees at most one leader — the counting argument is the whole safety proof.

**The cost is availability.** If no group has a majority (a close or three-way split), no leader is elected and writes stop until the partition heals — unavailable but consistent.

**A majority quorum makes split-brain impossible because two disjoint groups cannot both hold more than half the cluster — you trade availability during a bad partition for the guarantee that there is never more than one leader.**

<svg role="img" aria-label="Two partition groups sized 3 and 2 out of 5; only the group of 3 exceeds the half line, so only it can hold a majority" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">5 nodes; a majority needs more than half (2.5)</text>
  <line x1="150" y1="22" x2="150" y2="82" stroke="var(--ink)" stroke-width="1" stroke-dasharray="3 2"/><text x="120" y="20" fill="var(--muted)" font-size="7">half = 2.5</text>
  <text x="8" y="42" fill="var(--muted)" font-size="8">grp A</text>
  <rect x="45" y="34" width="120" height="14" fill="var(--s1)"/><text x="168" y="45" fill="var(--s1)" font-size="7">3 &gt; 2.5 → majority</text>
  <text x="8" y="66" fill="var(--muted)" font-size="8">grp B</text>
  <rect x="45" y="58" width="80" height="14" fill="var(--s2)"/><text x="128" y="69" fill="var(--muted)" font-size="7">2 &lt; 2.5 → no majority</text>
  <text x="20" y="92" fill="var(--muted)" font-size="8">both bars can't cross the line — their sizes would exceed 5 — so at most one is a majority</text>
</svg>
^ Only the group of 3 crosses the half line, so only it holds a majority; two groups can't both cross it because their sizes would sum past the cluster total — the reason at most one leader can be elected.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/govern-inter-24/quorum.py

The fixture is a 5-node cluster and a 3-vs-2 partition (with a three-way split held for later).

```json filename=modules/orchestration-and-governance/code/govern-inter-24/quorum.json:1-5 COMPLETE
{
  "_meta": "A cluster of `nodes` machines that must elect a single leader. A network partition splits them into groups that cannot see each other; each group tries to elect its own leader. Two election rules: MAJORITY requires a candidate to be backed by more than half the whole cluster (floor(nodes/2)+1 votes), so a group can only elect if it holds a majority of ALL nodes -- and since two disjoint groups cannot both hold a majority, at most one leader is ever elected. ANY (no majority) lets any non-empty group elect its own leader, so a partition produces one leader per group -- split-brain, multiple leaders each accepting writes, diverging state. partitions lists example splits (group sizes); [3,2] splits a 5-node cluster 3-vs-2, [2,2,1] is a three-way split where no group holds a majority.",
  "nodes": 5,
  "partition": [3, 2],
  "three_way": [2, 2, 1]
}
```

The election counts the leaders each rule elects on the partition.

```python filename=modules/orchestration-and-governance/code/govern-inter-24/quorum.py:56-58 COMPLETE
    part, n = data["partition"], data["nodes"]
    maj = leaders(part, n, majority=True)
    any_ = leaders(part, n, majority=False)
```

Run `--elect` on the 3-vs-2 partition.

```text filename=--elect
ELECT — 5-node cluster split [3, 2] (majority needs 3 votes)
------------------------------------------------------------
  majority rule:   1 leader(s)   (groups that reach 3: [3])
  any-group rule:  2 leader(s)   (every non-empty group: [3, 2])
------------------------------------------------------------
  the any-group rule elects one leader per side -- split-brain; majority elects at most one.
```

The 5-node cluster needs 3 votes for a majority. Split 3-vs-2, the majority rule lets only the group of 3 elect — it has 3 votes, meeting the threshold — while the group of 2 cannot, having only 2. So exactly one leader emerges, and the minority side, correctly, refuses to elect and waits. The any-group rule lets both sides elect: the group of 3 crowns a leader and the group of 2 crowns its own, giving two leaders that will each accept writes. When the partition heals, the majority cluster has one consistent history to catch the minority up on; the any-group cluster has two histories and a conflict. The only difference was whether a candidate had to clear half the whole cluster or just gather its own side.

<svg role="img" aria-label="Under the majority rule only the group of 3 elects a leader; under the any-group rule both the group of 3 and the group of 2 elect, giving two leaders" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">5 nodes split 3 | 2 (majority = 3)</text>
  <text x="8" y="36" fill="var(--s1)" font-size="8">majority</text>
  <rect x="60" y="26" width="60" height="16" fill="var(--s1)"/><text x="66" y="38" fill="var(--panel)" font-size="8">group 3 → LEADER</text>
  <rect x="126" y="26" width="40" height="16" fill="none" stroke="var(--grid)"/><text x="132" y="38" fill="var(--muted)" font-size="7">group 2: no</text>
  <text x="172" y="38" fill="var(--s1)" font-size="7">1 leader — safe</text>
  <text x="8" y="72" fill="var(--s2)" font-size="8">any-group</text>
  <rect x="60" y="62" width="60" height="16" fill="var(--s2)"/><text x="66" y="74" fill="var(--panel)" font-size="8">group 3 → LEADER</text>
  <rect x="126" y="62" width="40" height="16" fill="var(--s2)"/><text x="130" y="74" fill="var(--panel)" font-size="7">2 → LEADER</text>
  <text x="172" y="74" fill="var(--s2)" font-size="7">2 leaders — split-brain</text>
  <text x="30" y="98" fill="var(--muted)" font-size="8">only the majority side can elect; requiring your own side alone crowns two</text>
</svg>
^ The majority rule lets only the group of 3 elect, leaving one leader; the any-group rule lets both groups elect, producing two leaders and a split brain.

## Build

Does the guarantee hold across every partition? Run `--splits`.

```text filename=--splits
SPLITS — leaders elected per rule across partitions (5 nodes, majority 3)
------------------------------------------------------------
  partition     majority   any-group
  [3, 2]        1          2
  [2, 2, 1]     0          3
  [5]           1          1
```

Across all three partitions the majority rule never elects more than one leader. On 3-vs-2 it elects one; on the healthy unpartitioned cluster [5] it elects one; and on the three-way 2-2-1 split it elects *zero* — no group has 3 votes, so nobody wins and the cluster refuses writes until it heals. That zero is the availability cost, and it is the correct behavior: with the nodes split so evenly that no side has a majority, there is no group that can safely be the sole authority, so the safe answer is to have none rather than risk several. The any-group rule, by contrast, elects one leader per group every time — 2 on the first split, 3 on the three-way — turning every partition into a split-brain. The majority column is bounded by one by the counting argument; the any-group column grows with the number of groups.

<svg role="img" aria-label="The majority rule elects 1, 0, and 1 leaders across three partitions; the any-group rule elects 2, 3, and 1" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">leaders elected (majority = solid, any-group = light)</text>
  <line x1="30" y1="90" x2="285" y2="90" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="40" x2="285" y2="40" stroke="var(--line)" stroke-width="1" stroke-dasharray="2 3"/><text x="245" y="38" fill="var(--muted)" font-size="7">1 = safe max</text>
  <text x="45" y="102" fill="var(--muted)" font-size="7">[3,2]</text>
  <rect x="45" y="65" width="16" height="25" fill="var(--s1)"/><rect x="63" y="40" width="16" height="50" fill="var(--s2)"/>
  <text x="130" y="102" fill="var(--muted)" font-size="7">[2,2,1]</text>
  <rect x="130" y="90" width="16" height="0" fill="var(--s1)"/><text x="128" y="88" fill="var(--s1)" font-size="7">0</text><rect x="148" y="15" width="16" height="75" fill="var(--s2)"/>
  <text x="215" y="102" fill="var(--muted)" font-size="7">[5]</text>
  <rect x="215" y="65" width="16" height="25" fill="var(--s1)"/><rect x="233" y="65" width="16" height="25" fill="var(--s2)"/>
</svg>
^ The solid majority bars never exceed the dashed one-leader line (and drop to zero on the even split); the light any-group bars rise to two and three — one leader per group, split-brain.

## Definition of done

The self-test pins it: the majority rule elects one on 3-vs-2, the any-group rule elects two, the majority rule never exceeds one on any partition, the three-way split is safe-but-unavailable, and the threshold is more than half.

```python filename=modules/orchestration-and-governance/code/govern-inter-24/quorum.py:83-96 COMPLETE
    majority_one_leader = len(leaders(part, n, True)) == 1
    print("  on the 3-vs-2 split the majority rule elects exactly one leader = %s (%s)" % (majority_one_leader, leaders(part, n, True)))

    any_group_split_brain = len(leaders(part, n, False)) == 2
    print("  on the same split the any-group rule elects two (split-brain) = %s (%s)" % (any_group_split_brain, leaders(part, n, False)))

    majority_never_two = all(len(leaders(p, n, True)) <= 1 for p in (part, three, [n], [4, 1]))
    print("  the majority rule elects at most one leader on every partition = %s" % majority_never_two)

    three_way_safe_unavailable = len(leaders(three, n, True)) == 0 and len(leaders(three, n, False)) == 3
    print("  a three-way split elects 0 under majority (safe, unavailable) but 3 under any-group = %s" % three_way_safe_unavailable)

    majority_more_than_half = majority_threshold(n) > n / 2
    print("  the majority threshold is more than half the cluster = %s (%d > %.1f)" % (majority_more_than_half, majority_threshold(n), n / 2))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the majority rule elects at most one leader on every partition; the any-group rule splits the brain
----------------------------------------------------------------------------------------------------------------
  on the 3-vs-2 split the majority rule elects exactly one leader = True ([3])
  on the same split the any-group rule elects two (split-brain) = True ([3, 2])
  the majority rule elects at most one leader on every partition = True
  a three-way split elects 0 under majority (safe, unavailable) but 3 under any-group = True
  the majority threshold is more than half the cluster = True (3 > 2.5)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  majority_one_leader=True  any_group_split_brain=True  majority_never_two=True  three_way_safe_unavailable=True  majority_more_than_half=True
```

**Done means split-brain is provably prevented: the majority rule elects exactly one leader on the 3-vs-2 split and zero on the 2-2-1 split (never more than one on any partition), while the any-group rule elects two and three respectively — the guarantee bought with the availability of the even-split case.**

## Boss fight

The majority rule capped leaders at one. Predict why clusters are sized with an odd number of nodes, and the failure the leader-count guarantee still does not cover. It is tempting to think a quorum makes the cluster fault-tolerant with no further thought.

Odd sizing maximizes fault tolerance per node and avoids a wasteful tie. A 5-node cluster tolerates 2 failures (3 remain, still a majority); adding a sixth node does not help — a 6-node cluster still only tolerates 2 failures (4 remain a majority, but 3 is a tie that elects nobody), so you paid for a node and bought no extra resilience, only a larger chance of an even split that stalls. Odd counts also make the majority unambiguous: there is no way to split an odd cluster into two equal halves, so a majority always exists on one side of any two-way partition. This is why quorum systems are almost always 3, 5, or 7 nodes — enough to tolerate 1, 2, or 3 failures, and never so even that a symmetric split leaves nobody in charge.

The guarantee has a sharp boundary: it ensures at most one leader is *elected*, not that a node which was leader *stops believing it is one*. A node can be elected leader, get partitioned into the minority, and keep acting as leader — accepting writes — because from inside the minority it cannot tell it lost the majority. The quorum rule prevents the minority from electing a NEW leader, but the OLD leader is still there. So majority election must be paired with a mechanism that stops a deposed leader from acting: a lease it must renew against the quorum (and lets expire when it cannot reach them), or an epoch/fencing token that the storage layer checks so a stale leader's writes are rejected. Election safety and leader-liveness are two separate guarantees — the quorum gives you the first, and you need fencing or leases for the second, which is why real consensus systems combine them.

```python filename=modules/orchestration-and-governance/code/govern-inter-24/quorum.py:72-73 COMPLETE
    for part in (data["partition"], data["three_way"], [n]):
        print("  %-12s  %d          %d" % (str(part), len(leaders(part, n, True)), len(leaders(part, n, False))))
```

**Require a majority of the whole cluster to elect a leader, so that two disjoint partition groups can never both elect and split-brain is impossible — accept that a majority-less split elects nobody (unavailable but consistent), size the cluster odd for the best fault tolerance, and pair the election with a lease or fencing token, because the quorum stops a new leader being elected but not an old one from still acting.**

## External resources

The Raft paper ("In Search of an Understandable Consensus Algorithm") — its leader election requires a candidate to win votes from a majority, with the term and log-completeness rules that make the single-leader guarantee hold.

Documentation for ZooKeeper, etcd, or Consul on quorum and cluster sizing — the practical guidance on odd node counts, fault tolerance per size, and why an even cluster buys no extra resilience.

The companion "fence writes with a monotonic epoch" and "require a quorum before trusting a vote" modules — fencing is the second guarantee this module's boss fight points to (stopping a deposed leader), and quorum voting is the same majority principle applied to reads and writes rather than election.
