---
id: hintedhandoff-inter-01
title: Store a hint for a down replica and replay it on recovery — otherwise a write during an outage is a copy lost forever
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: A replicated store keeps N copies of each key so the data survives a node failing, but there is a window the naive version handles badly: a write that arrives while one replica is temporarily down. The coordinator writes to the reachable replicas, but the down one gets nothing, so the write lands on fewer than N nodes. That is not automatically corrected — when the down replica comes back it has no idea it missed a write, so the key stays under-replicated indefinitely, one copy short of its durability target, until some slow background reconciliation notices. During that window the key is more fragile than it should be, tolerating fewer subsequent failures than its replication factor was meant to. Hinted handoff closes the window: when the coordinator cannot reach a replica for a write, it does not drop that copy — it writes the value to a healthy node as a hint, a stored note that says "this belongs to the down replica, deliver it when it comes back." The write is accepted (write availability is preserved even with a replica down), and the missing copy is parked, not lost. When the down replica recovers, the node holding the hint replays it and deletes it, so the key returns to full replication automatically without waiting for a background sweep. This is the write-time complement to read repair. On a fixture where a write of "v1" arrives while replica C is down, no hinted handoff leaves only A and B with it (2 of 3, C still lacking it after recovery), while with hinting A and B get it and A parks a hint for C — replayed on C's recovery so all 3 replicas hold it.
eli5: Imagine three friends are each supposed to get a copy of your new phone number, but one of them is out of town when you send it. If you just send to the two who are around, the third friend never gets your number — even after they're back — because nobody remembers they missed it. Hinted handoff is like handing a sticky note to one of the present friends that says "give this to Sam when Sam gets back." You've still delivered to everyone you can reach right now, but Sam's copy isn't lost — it's waiting. The moment Sam returns, your friend hands over the note, and now all three friends have your number, no extra effort from you.
---

## Why this module

Replication promises N copies, but that promise is only as good as the moment you count. A write that happens while one replica is briefly unreachable quietly lands on N−1 copies, and nothing about the system flags it — the write succeeded, the reachable replicas have it, and the down replica, when it returns, simply does not know it fell behind. So the key sits under-replicated, silently, more fragile than its configuration claims, until an unrelated background process eventually stumbles across the discrepancy. The failure is not that the write was rejected; it is that the write was accepted at a lower durability than intended, and the shortfall is invisible.

The coordinator can reach the other replicas and write the value to them, but the down replica gets nothing, so the write lands on fewer than N nodes. When the down replica comes back it has no idea it missed a write — it just has an old value for that key — so the key stays under-replicated indefinitely, one copy short of its durability target, until a slow background reconciliation notices. During that window it can be lost by fewer subsequent failures than its replication factor was meant to tolerate.

Hinted handoff closes the window: when the coordinator cannot reach a replica, it writes the value to a healthy node as a hint — a note saying "this belongs to the down replica, deliver it on recovery." The write is accepted, the missing copy is parked, and when the replica recovers the hint holder replays it and deletes the hint, restoring full replication automatically. This module runs the write and recovery both ways.

**When a write cannot reach a replica because it is temporarily down, store the value as a hint on a healthy node and replay it to the replica when it recovers (hinted handoff), because otherwise the write lands on fewer than N replicas and stays under-replicated until a background sweep notices — hinted handoff both keeps writes available during the outage and restores full replication automatically on recovery.**

## Concepts

**A write reaches the healthy replicas, and the down replica's copy is either dropped or parked as a hint** on a healthy node.

```python filename=modules/orchestration-and-governance/code/hintedhandoff-inter-01/hintedhandoff.py:53-63 COMPLETE
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
```

**On recovery, hints targeting the returned replica are replayed** — delivered and removed — restoring its missing copy.

```python filename=modules/orchestration-and-governance/code/hintedhandoff-inter-01/hintedhandoff.py:66-79 COMPLETE
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
```

<svg role="img" aria-label="A write with replica C down: A and B store v1; without hinting C gets nothing, with hinting a hint for C is parked on A" viewBox="0 0 300 112" width="300" height="112">
  <text x="6" y="12" fill="var(--muted)" font-size="8">write v1 while C is down — the down copy is dropped or parked</text>
  <rect x="30" y="26" width="50" height="22" fill="var(--s1)"/><text x="42" y="41" fill="var(--panel)" font-size="8">A v1</text>
  <rect x="125" y="26" width="50" height="22" fill="var(--s1)"/><text x="137" y="41" fill="var(--panel)" font-size="8">B v1</text>
  <rect x="220" y="26" width="50" height="22" fill="none" stroke="var(--s2)" stroke-dasharray="2 2"/><text x="232" y="41" fill="var(--s2)" font-size="8">C down</text>
  <text x="30" y="66" fill="var(--muted)" font-size="7">no hint: C's copy is dropped — lost</text>
  <text x="30" y="90" fill="var(--s1)" font-size="7">hinted: A holds a note →</text>
  <rect x="150" y="78" width="120" height="18" fill="none" stroke="var(--s1)"/><text x="156" y="90" fill="var(--s1)" font-size="6">hint: for C, value v1</text>
  <text x="30" y="106" fill="var(--muted)" font-size="6">the write reaches A and B either way; only hinting remembers C's copy</text>
</svg>
^ The write of v1 reaches the healthy replicas A and B in both cases, but C is down: without hinting its copy is simply dropped and lost, while with hinting the coordinator parks a hint for C on the healthy node A, remembering the copy C could not receive.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/hintedhandoff-inter-01/hintedhandoff.py

The fixture is a three-replica set, the replica that is down during the write, the value, and the node that will hold the hint.

```json filename=modules/orchestration-and-governance/code/hintedhandoff-inter-01/hintedhandoff.json:3-6 COMPLETE
  "replicas": ["A", "B", "C"],
  "down_during_write": "C",
  "value": "v1",
  "hint_holder": "A"
```

Run `--write`.

```text filename=--write
WRITE — value 'v1' arrives while replica C is down
--------------------------------------------------------------
  NO HINT:  stored on ['A', 'B'] ; hints: []
            replica C got nothing -- its copy is dropped
  HINTED:   stored on ['A', 'B'] ; hint: [{'holder': 'A', 'target': 'C', 'value': 'v1'}]
            replica C's copy is parked as a hint on A
```

Read the two write outcomes. Both accept the write on the replicas they can reach — A and B each store v1 — so from the client's point of view both writes succeed identically; there is no error, and the healthy replicas are consistent. The difference is entirely in what happens to C's copy. Without hinting, C simply gets nothing: the coordinator could not reach it, so that copy is dropped and there is no record anywhere that C is missing this write. With hinting, the coordinator writes a hint on A — `{holder: A, target: C, value: v1}` — which says "A is temporarily holding v1 on C's behalf; hand it over when C is back." The write is still accepted (this is what preserves write availability during the outage: you do not have to reject writes just because one replica is down), and C's copy is not lost, only deferred. At this instant the two schemes look the same to the client and to A and B; the divergence is a note that either exists or does not.

## Build

The consequence appears when C comes back.

```text filename=--recover
RECOVER — replica C comes back; hints (if any) are replayed
----------------------------------------------------------------
  NO HINT:  after recovery, replicas with 'v1' = ['A', 'B']  (2 of 3)
  HINTED:   after recovery, replicas with 'v1' = ['A', 'B', 'C']  (3 of 3) ; hints left: []
```

<svg role="img" aria-label="On C's recovery, node A replays its parked hint by handing v1 to C, then deletes the hint; C now holds v1 alongside A and B" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">C recovers → A replays the hint → C gets v1, hint deleted</text>
  <rect x="20" y="30" width="60" height="20" fill="var(--s1)"/><text x="34" y="44" fill="var(--panel)" font-size="7">A (v1)</text>
  <rect x="24" y="54" width="52" height="14" fill="none" stroke="var(--s1)"/><text x="28" y="64" fill="var(--s1)" font-size="6">hint→C</text>
  <rect x="220" y="30" width="60" height="20" fill="none" stroke="var(--s2)"/><text x="232" y="44" fill="var(--s2)" font-size="7">C back</text>
  <path d="M80 44 L216 44" fill="none" stroke="var(--s1)"/><text x="110" y="38" fill="var(--s1)" font-size="6">replay v1 →</text>
  <rect x="220" y="72" width="60" height="18" fill="var(--s1)"/><text x="232" y="84" fill="var(--panel)" font-size="7">C = v1 ✓</text>
  <text x="24" y="82" fill="var(--muted)" font-size="6">hint deleted after delivery</text>
</svg>
^ When C recovers, the hint holder A hands v1 across to C and then deletes the hint; C, which had nothing, now holds v1 alongside A and B — the deferred copy delivered the moment the replica could receive it.

C recovers, and the two schemes diverge permanently. Without hints, C comes back with no knowledge that it missed anything — it holds whatever old value it had for the key — so the replicas with v1 are still just A and B: 2 of 3. The key is under-replicated, and it will stay that way until a background anti-entropy sweep (a Merkle comparison, a read repair triggered by a lucky read) happens to notice and fix it, which could be much later or, for a rarely-read key, effectively never. With hints, C's recovery triggers the replay: A hands the parked hint to C, C now holds v1, the hint is deleted, and the replicas with v1 are A, B, and C — 3 of 3, full replication restored, and the hint list is empty because the deferred copy has been delivered. This is the key property: hinted handoff makes recovery *proactive*. The system remembered exactly which write C missed and delivered it the instant C could receive it, rather than leaving the shortfall to be discovered lazily. It is the write-time mirror of read repair — read repair fixes a stale replica when someone reads it, hinted handoff fixes a missed write when the replica returns — and together they keep replication converging without relying solely on a slow full sweep.

```python filename=modules/orchestration-and-governance/code/hintedhandoff-inter-01/hintedhandoff.py:122-133 COMPLETE
    down_missed_write = down not in ns and down not in hs
    print("  the down replica %s received no direct copy = %s" % (down, down_missed_write))

    hint_stored_for_down = any(h["target"] == down for h in hh)
    print("  hinted mode parked a hint for %s = %s (%s)" % (down, hint_stored_for_down, hh))

    ns2, _ = recover(ns, nh, down)
    hs2, hh2 = recover(hs, hh, down)

    nohint_stays_missing = down not in replicas_with_value(ns2, reps, val)
    print("  no-hint: %s still lacks the write after recovery = %s (replicas with it: %s)"
          % (down, nohint_stays_missing, sorted(replicas_with_value(ns2, reps, val))))
```

## Definition of done

The self-test pins the missed write, the parked hint, the persistent no-hint gap, and the hinted recovery to full replication.

```python filename=modules/orchestration-and-governance/code/hintedhandoff-inter-01/hintedhandoff.py:135-139 COMPLETE
    hint_replayed = down in replicas_with_value(hs2, reps, val)
    print("  hinted: %s receives the write on recovery via hint replay = %s" % (down, hint_replayed))

    hinted_full_replication = len(replicas_with_value(hs2, reps, val)) == len(reps) and len(replicas_with_value(ns2, reps, val)) < len(reps)
    print("  hinted reaches full replication, no-hint does not = %s (%d of %d vs %d of %d)"
          % (hinted_full_replication, len(replicas_with_value(hs2, reps, val)), len(reps), len(replicas_with_value(ns2, reps, val)), len(reps)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — without hints the write stays under-replicated after recovery; hinted handoff restores full replication
--------------------------------------------------------------------------------------------------------------------
  the down replica C received no direct copy = True
  hinted mode parked a hint for C = True ([{'holder': 'A', 'target': 'C', 'value': 'v1'}])
  no-hint: C still lacks the write after recovery = True (replicas with it: ['A', 'B'])
  hinted: C receives the write on recovery via hint replay = True
  hinted reaches full replication, no-hint does not = True (3 of 3 vs 2 of 3)
```

<svg role="img" aria-label="Replication after C recovers: no-hint has 2 of 3 replicas holding v1, hinted has 3 of 3" viewBox="0 0 300 92" width="300" height="92">
  <text x="6" y="12" fill="var(--muted)" font-size="8">replicas holding v1 after C recovers</text>
  <text x="10" y="36" fill="var(--muted)" font-size="7">no hint</text>
  <rect x="80" y="26" width="60" height="14" fill="var(--s2)"/><rect x="140" y="26" width="60" height="14" fill="var(--s2)"/><rect x="200" y="26" width="60" height="14" fill="none" stroke="var(--line)" stroke-dasharray="2 2"/>
  <text x="264" y="37" fill="var(--muted)" font-size="7">2 of 3</text>
  <text x="10" y="66" fill="var(--muted)" font-size="7">hinted</text>
  <rect x="80" y="56" width="60" height="14" fill="var(--s1)"/><rect x="140" y="56" width="60" height="14" fill="var(--s1)"/><rect x="200" y="56" width="60" height="14" fill="var(--s1)"/>
  <text x="264" y="67" fill="var(--muted)" font-size="7">3 of 3</text>
  <text x="10" y="86" fill="var(--muted)" font-size="6">the replayed hint fills C's slot; without it, C stays empty (dashed)</text>
</svg>
^ After C recovers, the no-hint scheme still has only A and B holding v1 (C's slot empty, dashed), while the hinted scheme has all three — the replayed hint fills C's slot, restoring the full replication the write was supposed to have.

**Done means the durability window and its fix are proven on real state: a write during C's outage reaches only A and B, and without hinting C still lacks it after recovery (2 of 3, under-replicated), while hinted handoff parks a hint for C on A and replays it on C's recovery so all three replicas hold the value (3 of 3) — so a write that cannot reach a down replica must be stored as a hint and replayed on recovery.**

## Boss fight

Predict two ways hinted handoff is trickier than "park a note and replay it," because the hint holder can fail and the hint can be stale by the time it lands.

The first trap is that a hint is itself un-replicated state on one node, so hinted handoff reduces but does not eliminate the durability gap — and it can be overwhelmed. The hint lives on a single healthy node (A here); if A fails before the down replica recovers and the hint is delivered, the hint is lost and C's copy is gone after all, so the scheme narrows the window rather than closing it absolutely (this is why hinted handoff complements, and does not replace, a background anti-entropy sweep that reconciles from the durable replicas). Worse, hints accumulate: if a replica is down for a long time and a lot of writes target it, the hint holders pile up unbounded hint data for it, which is memory and disk pressure exactly when the cluster is already degraded — so real systems cap hint storage and expire hints after a window (a "hint window"), beyond which they stop hinting and rely on the full anti-entropy repair to catch the node up when it eventually returns. And when the node does return after a long outage, replaying a flood of accumulated hints is itself a load spike that must be throttled. So hinted handoff is a bounded, best-effort optimization for short outages layered on top of a durable repair mechanism, not a standalone durability guarantee.

The second trap is that a hint carries a value from the past, so replaying it must respect the store's conflict-resolution model or it can resurrect stale or even deleted data. Between the moment the hint was parked and the moment C recovers, the key may have been written again (a newer value now on A and B) or deleted; if the hint is replayed blindly, C could end up with the old v1 while A and B hold v2, or a deleted key could come back to life on C (a "zombie" / resurrection), which is the same hazard tombstones and version reconciliation exist to prevent. So hint replay must be version-aware: deliver the hint as a normal versioned write that the resolution logic (last-write-wins with timestamps, vector clocks, CRDT merge) can order against whatever C and the others now hold, and honor tombstones so a delete is not undone by a stale hint. It also interacts with reads during the window: while C is down and hinted, a read quorum must be sized and routed so it still sees the latest value from the healthy replicas, not conclude the key is absent because it happened to ask the not-yet-recovered C. Hinted handoff, read repair, quorum sizing, and anti-entropy are one system, and the hint is only safe when its replay obeys the same versioning and tombstone rules as every other write.

**A hint is un-replicated state on one node, so hinted handoff narrows the durability gap rather than closing it: if the hint holder fails before delivery the copy is still lost, and hints accumulate unbounded for a long-down replica, so cap hint storage, expire hints after a window, throttle the replay flood on recovery, and keep a background anti-entropy sweep as the real durability backstop. And a hint carries a past value, so replay it as a versioned write, not a blind overwrite — honor timestamps/vector clocks and tombstones so a stale hint cannot resurrect a deleted key or clobber a newer value, and size read quorums so a not-yet-recovered replica cannot make a present key look absent.**

## External resources

The Dynamo paper and Cassandra/Riak documentation on hinted handoff — how hints are stored, the hint window and storage caps, replay on recovery, and how hinted handoff combines with read repair and Merkle-tree anti-entropy.

Documentation on tombstones, versioning, and conflict resolution in eventually-consistent stores — why a replayed hint must be version-aware to avoid resurrecting deleted data or overwriting a newer value.

The companion read-repair, quorum, and Merkle-reconciliation modules in this topic — hinted handoff is the write-time counterpart to read-repair's read-time convergence, sits alongside the quorum sizing that keeps reads correct during the outage, and hands off to background anti-entropy when the hint window is exceeded.
