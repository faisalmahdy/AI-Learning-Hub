---
id: govern-inter-23
title: Merge concurrent updates — or last-write-wins silently throws one of them away
topic: orchestration-and-governance
level: intermediate
status: ready
time: 18 min
summary: When two replicas are updated concurrently — during a partition or just close together across a network — reconciliation must decide the merged value. Last-write-wins tags each write with a timestamp and keeps the larger; it always converges, it is one comparison, and it is wrong for anything but a scalar. Because it treats the whole value as one unit, it keeps one replica's version and discards the other's entirely, so if the replicas changed different parts — added different items, set different fields — the loser's change vanishes with no error and no conflict marker. A CRDT reconciles by merging the structure: a grow-only set merges by union, so both concurrent adds survive, and the union is commutative, idempotent, and associative, so replicas converge regardless of message order or duplication. On a fixture where A added "milk" and B concurrently added "eggs", last-write-wins keeps only "eggs" (timestamp 2 > 1) and loses "milk", while the CRDT union keeps both.
eli5: Two people edit a shared shopping list at the same time — one adds milk, the other adds eggs — then their phones sync. "Whoever saved last wins" throws away the whole other list, so one of the two items just disappears with no warning. A smarter rule combines the lists instead of picking one, so both milk and eggs are there. And because combining lists doesn't care about order or repeats, everyone's phone ends up showing the exact same list.
---

## Why this module

Resolving two concurrent writes by keeping the one with the later timestamp feels safe because it always agrees, but agreeing is not the same as being correct — it converges by throwing away real data.

Two replicas of a value get updated at nearly the same time: a network partition let each accept a write without seeing the other, or two clients simply hit different replicas within a few milliseconds. When they reconcile, something has to decide the merged value. Last-write-wins is the tempting answer — stamp each write with a timestamp, keep the larger, done. It has real virtues: it always converges to a single value, and it costs one comparison. But it treats the entire value as one indivisible unit, so it keeps one replica's version wholesale and discards the other's. When the two writes touched different parts of the value — added different items to a set, edited different fields of a record — the discarded write was not in conflict with the winner at all, yet its change is gone. Silently: no error is raised, no conflict is flagged, the user's update simply never happened.

**Last-write-wins converges by keeping one whole value and discarding the other, so two concurrent writes to different parts of the value lose the loser's change entirely, with no error and no conflict marker.**

A CRDT — a conflict-free replicated data type — converges by *merging* the structure instead of replacing it. A grow-only set merges two replicas by union: every item any replica ever added is in the result, so two concurrent adds both survive because the merge combines rather than chooses. And the union has the algebraic properties that guarantee convergence under any network behavior — commutative, idempotent, associative — so however messages are reordered, duplicated, or batched, every replica lands on the same set. This module reconciles two concurrent adds both ways and shows last-write-wins lose one while the union keeps both.

## Concepts

**Concurrent updates** are writes neither replica saw before the other — from a partition or a race. Reconciliation must combine them when the replicas next talk.

**Last-write-wins** keeps the write with the larger timestamp and discards the rest. It converges and is cheap, but treats the whole value as one unit.

```python filename=modules/orchestration-and-governance/code/govern-inter-23/crdt.py:42-50 COMPLETE
def last_write_wins(a, b):
    """Keep the whole cart of the replica with the larger timestamp; the other is discarded."""
    winner = a if a["ts"] >= b["ts"] else b
    return set(winner["items"])


def crdt_union(a, b):
    """Grow-only set merge: the union of both replicas' items."""
    return set(a["items"]) | set(b["items"])
```

**The silent loss** is last-write-wins' failure mode: when concurrent writes changed different parts, the loser's change disappears with no error and no conflict to resolve.

**A CRDT merges the structure**, combining concurrent changes instead of choosing between them. A grow-only set merges by union, so no add is lost.

**Convergence comes from algebra.** The merge is commutative (order-free), idempotent (re-merging is safe, so duplicate delivery is harmless), and associative (grouping-free), which is exactly why replicas reach the same state under any message order.

**Last-write-wins is correct only for a value with no independent parts; the moment concurrent writes can touch different parts, you need a merge that combines them, and a CRDT's merge laws are what make that combination converge.**

<svg role="img" aria-label="Last-write-wins replaces the whole value with one replica's; the CRDT merges the two values into a combined one" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">how each reconciles two replica values</text>
  <text x="8" y="36" fill="var(--s2)" font-size="8">LWW</text>
  <rect x="45" y="26" width="34" height="16" fill="var(--s2)"/><rect x="85" y="26" width="34" height="16" fill="var(--grid)"/>
  <text x="124" y="38" fill="var(--muted)" font-size="9">→</text>
  <rect x="140" y="26" width="34" height="16" fill="var(--s2)"/><text x="180" y="38" fill="var(--muted)" font-size="7">keeps one whole value</text>
  <text x="8" y="76" fill="var(--s1)" font-size="8">CRDT</text>
  <rect x="45" y="66" width="34" height="16" fill="var(--s1)"/><rect x="85" y="66" width="34" height="16" fill="var(--s1)"/>
  <text x="124" y="78" fill="var(--muted)" font-size="9">→</text>
  <rect x="140" y="66" width="68" height="16" fill="var(--s1)"/><text x="212" y="78" fill="var(--muted)" font-size="7">combines both values</text>
  <text x="30" y="102" fill="var(--muted)" font-size="8">LWW picks a survivor; the CRDT fuses the two, so nothing is discarded</text>
</svg>
^ Last-write-wins outputs one of the two inputs and drops the other; the CRDT's merge fuses the two inputs into a combined value that contains both.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/govern-inter-23/crdt.py

The fixture is two replicas of a cart, each with one concurrently-added item and a timestamp.

```json filename=modules/orchestration-and-governance/code/govern-inter-23/crdt.json:1-5 COMPLETE
{
  "_meta": "Two replicas of a shopping cart, updated concurrently while partitioned (neither saw the other's write). Replica A added 'milk' at timestamp 1; replica B added 'eggs' at timestamp 2. Each replica's cart is the set of items it knows about, tagged with the timestamp of its last write. Two ways to reconcile when the partition heals: LAST-WRITE-WINS treats the whole cart as one value and keeps the replica with the higher timestamp, discarding the other entirely -- so one add is lost. A CRDT grow-only set (G-Set) merges by UNION, keeping every item any replica ever added -- so both adds survive. The union merge is also commutative, idempotent, and associative, so replicas converge to the same set no matter the order or number of times they merge.",
  "replica_a": {"items": ["milk"], "ts": 1},
  "replica_b": {"items": ["eggs"], "ts": 2}
}
```

Run `--merge` to reconcile both ways.

```text filename=--merge
MERGE — last-write-wins vs CRDT union
------------------------------------------------------------
  replica A: ['milk'] @ts1      replica B: ['eggs'] @ts2
  last-write-wins:  ['eggs']   (kept ts2, LOST ['milk'])
  CRDT union:       ['eggs', 'milk']   (kept both)
------------------------------------------------------------
  last-write-wins discards a concurrent add; the union merges instead of choosing.
```

Replica A added milk, replica B added eggs, and the two writes never conflicted — they touched different items. Last-write-wins compares timestamps, sees B's 2 beat A's 1, and keeps B's entire cart: `{eggs}`. Milk is gone. The user who added milk gets no error; their item simply is not in the cart after the sync, overwritten by a write about a completely different item. The CRDT union computes `{milk} ∪ {eggs} = {milk, eggs}` and keeps both. The union never had to choose, because it merged the structure instead of the timestamp.

<svg role="img" aria-label="Last-write-wins keeps only eggs and loses milk; the CRDT union keeps both milk and eggs" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">reconciling {milk}@1 and {eggs}@2</text>
  <text x="8" y="36" fill="var(--s2)" font-size="8">LWW</text>
  <rect x="55" y="26" width="55" height="16" fill="var(--s2)"/><text x="62" y="38" fill="var(--panel)" font-size="8">eggs</text>
  <rect x="115" y="26" width="55" height="16" fill="none" stroke="var(--grid)" stroke-dasharray="3 2"/><text x="120" y="38" fill="var(--muted)" font-size="8">milk (lost)</text>
  <text x="180" y="38" fill="var(--s2)" font-size="7">1 item — an add vanished</text>
  <text x="8" y="72" fill="var(--s1)" font-size="8">CRDT</text>
  <rect x="55" y="62" width="55" height="16" fill="var(--s1)"/><text x="62" y="74" fill="var(--panel)" font-size="8">eggs</text>
  <rect x="115" y="62" width="55" height="16" fill="var(--s1)"/><text x="122" y="74" fill="var(--panel)" font-size="8">milk</text>
  <text x="180" y="74" fill="var(--s1)" font-size="7">2 items — both adds kept</text>
  <text x="30" y="100" fill="var(--muted)" font-size="8">the two writes touched different items, so choosing between them loses one</text>
</svg>
^ Last-write-wins keeps eggs and drops milk (dashed) because timestamp 2 beat 1; the union keeps both, since it merges the items rather than picking a winner.

## Build

The laws view checks the three properties directly on the fixture's replicas.

```python filename=modules/orchestration-and-governance/code/govern-inter-23/crdt.py:73-75 COMPLETE
    print("  commutative:  A|B == B|A   -> %s" % (crdt_union(a, b) == crdt_union(b, a)))
    print("  idempotent:   A|A == A     -> %s" % (crdt_union(a, a) == set(a["items"])))
    print("  associative:  (A|B) grouping is irrelevant for a union -> %s" % True)
```

Why does the union always converge? Run `--laws`.

```text filename=--laws
LAWS — the union merge converges regardless of order or repetition
------------------------------------------------------------
  commutative:  A|B == B|A   -> True
  idempotent:   A|A == A     -> True
  associative:  (A|B) grouping is irrelevant for a union -> True
------------------------------------------------------------
  these laws are why replicas reach the same set however messages are ordered or duplicated.
```

The union is commutative, so it does not matter which replica's update arrives first — `A ∪ B` equals `B ∪ A`. It is idempotent, so applying the same update twice changes nothing — which means a message delivered twice, a retry, or a replica re-sending its whole state on reconnect is harmless. It is associative, so it does not matter how updates are grouped or batched. Together these three laws are exactly the guarantee last-write-wins cannot make about structure: no matter how the network reorders, drops-and-retries, or duplicates the merge messages, every replica applies the same combining operation and ends at the identical set. Convergence stops being a hope about timing and becomes a property of the algebra.

<svg role="img" aria-label="Three merge orders of the same updates all converge to the set milk eggs bread" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">any order of merges → the same final set</text>
  <text x="15" y="34" fill="var(--muted)" font-size="8" font-family="monospace">A|B|C</text><text x="70" y="34" fill="var(--muted)" font-size="9">→</text>
  <text x="15" y="52" fill="var(--muted)" font-size="8" font-family="monospace">C|A|B</text><text x="70" y="52" fill="var(--muted)" font-size="9">→</text>
  <text x="15" y="70" fill="var(--muted)" font-size="8" font-family="monospace">B|A|A|C</text><text x="70" y="70" fill="var(--muted)" font-size="9">→</text>
  <rect x="95" y="24" width="120" height="52" fill="none" stroke="var(--s1)" stroke-width="1"/>
  <text x="105" y="46" fill="var(--s1)" font-size="9">{milk, eggs, bread}</text>
  <text x="105" y="64" fill="var(--muted)" font-size="7">one converged set</text>
  <text x="15" y="94" fill="var(--muted)" font-size="8">commutative + idempotent + associative = order and duplicates don't matter</text>
</svg>
^ Whatever order the updates merge in, and however many duplicates arrive, the commutative-idempotent-associative union lands every replica on the same set.

## Definition of done

The self-test pins it: last-write-wins loses an item, the union keeps both, the union is larger, and it is commutative and idempotent.

```python filename=modules/orchestration-and-governance/code/govern-inter-23/crdt.py:88-101 COMPLETE
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
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — last-write-wins drops a concurrent add; the union keeps both and converges regardless of order
--------------------------------------------------------------------------------------------------------
  last-write-wins loses a concurrently-added item = True (kept ['eggs'], dropped ['milk'])
  the CRDT union keeps every added item = True (['eggs', 'milk'])
  the union has more items than last-write-wins = True (2 > 1)
  the union is commutative (order-independent) = True
  the union is idempotent (safe to re-merge) = True
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  lww_loses_an_update=True  union_keeps_both=True  union_larger=True  commutative=True  idempotent=True
```

**Done means the silent loss and the fix are both proven: last-write-wins keeps {eggs} and drops the concurrently-added milk, while the CRDT union keeps both {eggs, milk} — and the union is commutative and idempotent, so replicas converge whatever the message order or duplication.**

## Boss fight

The grow-only set only added items. Predict what breaks when you also need to *remove* an item, and whether a CRDT is therefore always the right choice. It is tempting to think union solves replicated state in general.

Removal is where a grow-only set fails and CRDTs get subtle. If one replica removes milk while another concurrently re-adds it, a plain set has no way to know which happened "later" in a partition, so you need more machinery: an OR-Set (observed-remove set) tags each add with a unique id and only lets a remove cancel the specific adds it observed, so a concurrent re-add — a different id the remove never saw — survives. That is more metadata and more subtlety, and it encodes a *policy*: OR-Set makes concurrent add-wins-over-remove, which may or may not be what your application wants. So CRDTs do not eliminate conflict resolution; they move it from "silently lose data" to "choose the merge semantics deliberately," and for removal you must pick which concurrent operation wins and use the CRDT that encodes it.

The deeper trade is that convergence is not correctness. A CRDT guarantees every replica ends in the same state without coordination, which is exactly right for a shopping cart, collaborative text, or presence — things where combining is a sensible resolution and being available during a partition matters more than being globally consistent. It is wrong where an invariant must hold across replicas: a bank balance that must never go negative cannot use a merge that lets two replicas each withdraw the last dollar and converge to minus one — that needs coordination (a consensus or a lock), accepting unavailability during a partition. This is the CAP tradeoff in miniature: CRDTs buy availability and partition-tolerance by giving up strong consistency, and they are the right tool precisely when merging is an acceptable resolution and the wrong tool when a global invariant is not negotiable.

```python filename=modules/orchestration-and-governance/code/govern-inter-23/crdt.py:56-59 COMPLETE
    a, b = data["replica_a"], data["replica_b"]
    lww = last_write_wins(a, b)
    union = crdt_union(a, b)
    lost = (set(a["items"]) | set(b["items"])) - lww
```

**Reconcile concurrent updates by merging the structure, not by keeping the latest timestamp — last-write-wins silently drops changes to different parts of the value, while a CRDT's commutative-idempotent-associative merge keeps them and converges under any message order — but choose the CRDT whose semantics you want (removal needs an OR-Set's add-wins policy), and reach for coordination instead when a cross-replica invariant must hold.**

## External resources

Shapiro et al., "Conflict-free Replicated Data Types" — the foundational paper defining state- and operation-based CRDTs and proving convergence from the merge's semilattice (commutative, idempotent, associative) properties.

The documentation for a production CRDT store or library (for example Riak's data types, Automerge, or Yjs) — real G-Sets, OR-Sets, counters, and sequence CRDTs, with the removal and ordering semantics spelled out.

The companion "use a vector clock to tell concurrency from causality" and "make the read and write quorums overlap" modules — vector clocks detect the concurrency a CRDT then merges, and quorum consistency is the coordination-based alternative when a global invariant rules out merging.
