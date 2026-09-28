---
id: snapshot-inter-01
title: Snapshot a distributed system by capturing the in-flight messages too, not just each node's state — a node-only snapshot loses or double-counts what was in transit
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: To snapshot the global state of a running distributed system — for a consistent backup, a restart checkpoint, a distributed debugger, or a deadlock/termination check — the obvious approach is to ask every node for its current state and staple the answers together. It does not work, because there is no shared instant at which all nodes are recorded: each reports at a slightly different real time, and while you collect, messages are traveling on the channels between nodes. Take two accounts, A holding 100 and B holding 0, and a transfer of 30 from A to B. For a window of real time the 30 has left A (A now holds 70) but has not reached B (B still holds 0); it sits on the channel A→B. Snapshot naively by recording A after it sent (70) and B before it received (0), ignoring the channel, and the snapshot totals 70 — the 30 in transit is simply gone, money the real system never lost. Record A before the send (100) and B after the receive (30), still ignoring the channel, and the total is 130 — the same 30 counted twice. Both snapshots show a global state that never existed and break the conservation the real system always obeys. The Chandy-Lamport consistent-snapshot algorithm fixes this with one key idea: a snapshot is the nodes plus the messages in flight on the channels at the cut. Record A at the cut (70), B at the cut (0), and the message on the channel (30), and the snapshot totals 100 — a real, reachable global state that conserves the money. On this fixture the true total is always 100; a node-only snapshot totals 70 (loses the transfer) or 130 (double-counts it), and the consistent snapshot that records the channel totals 100.
eli5: Imagine you want to count all the money two friends have, but one is in the middle of mailing the other some cash. If you check the sender's wallet after they mailed it and the receiver's wallet before the envelope arrives, the mailed money is in neither wallet and you'll think it vanished. If you check the sender before mailing and the receiver after the envelope lands, you'll count that money twice. The only way to get the right total is to also count the envelope that's still in the mail. In a computer system, the "envelopes in the mail" are messages traveling between machines, and a correct snapshot has to record those too — not just what each machine is holding right now.
---

## Why this module

Sometimes you need a photograph of an entire distributed system at once: to take a consistent backup, to checkpoint so you can restart after a crash, to feed a distributed debugger, or to test whether the system has deadlocked or finished. The trouble is that a distributed system has no single clock and no single instant. You cannot freeze every machine at the same moment, so you record them one at a time — and in the gaps between your recordings, the system keeps running and messages keep moving.

Those in-flight messages are where the naive approach breaks. A message that has been sent but not yet received is not in the sender's state anymore, and not in the receiver's state yet. It lives on the channel between them. If your snapshot only records node states, that message falls into a crack: depending on exactly when you record each end, you either miss it entirely or count it on both ends. Either way you have manufactured a global state the system was never actually in — and if the quantity you are snapshotting is conserved, like money or a token count, the snapshot will visibly fail to conserve it.

This module takes the smallest system that shows the problem — two accounts and one transfer — and snapshots it three ways: two naive node-only snapshots and one consistent snapshot that records the channel.

**A distributed snapshot has no shared instant, so a node-only snapshot taken at inconsistent moments loses a sent-but-unreceived message or double-counts it — a consistent snapshot must record each node's state AND the messages in flight on the channels.**

## Concepts

The fixture is two account balances and a single transfer between them.

```json filename=modules/orchestration-and-governance/code/snapshot-inter-01/snapshot.json:3-4 COMPLETE
  "accounts": {"A": 100, "B": 0},
  "transfer": {"from": "A", "to": "B", "amount": 30}
```

The transfer passes through three moments. Before the send, A holds 100 and B holds 0. In flight, the 30 has left A (A holds 70) but not reached B (B holds 0), so it sits on the channel. After the receive, A holds 70 and B holds 30, and the channel is empty.

```python filename=modules/orchestration-and-governance/code/snapshot-inter-01/snapshot.py:32-40 COMPLETE
def states(accounts, transfer):
    """The three moments: before the send, message in flight, after the receive."""
    a0, b0 = accounts["A"], accounts["B"]
    amt = transfer["amount"]
    return {
        "before_send": {"A": a0, "B": b0, "channel": 0},
        "in_flight": {"A": a0 - amt, "B": b0, "channel": amt},
        "after_receive": {"A": a0 - amt, "B": b0 + amt, "channel": 0},
    }
```

Two ways to snapshot. The naive snapshot records A's balance and B's balance and ignores the channel. The consistent snapshot records A, B, and the message in flight on the channel — the Chandy-Lamport cut.

```python filename=modules/orchestration-and-governance/code/snapshot-inter-01/snapshot.py:47-55 COMPLETE
def naive_snapshot(a_state, b_state):
    """Record A's balance and B's balance, ignore the channel entirely."""
    return {"A": a_state["A"], "B": b_state["B"], "total": a_state["A"] + b_state["B"]}


def consistent_snapshot(cut):
    """Record A, B, AND the message in flight on the channel -- a Chandy-Lamport cut."""
    return {"A": cut["A"], "B": cut["B"], "channel": cut["channel"],
            "total": cut["A"] + cut["B"] + cut["channel"]}
```

The difference is one term: whether the channel's contents are part of the snapshot. That single term is what makes the total come out right.

<svg role="img" aria-label="A timeline of a 30-unit transfer from A to B: before send A=100 B=0, in flight A=70 channel=30 B=0, after receive A=70 B=30; a node-only snapshot misses the channel box" viewBox="0 0 320 150">
  <text x="10" y="14" font-size="8" fill="var(--muted)">the 30 moves A → channel → B over time</text>
  <g font-size="7">
  <text x="10" y="40" fill="var(--muted)">before</text>
  <rect x="52" y="30" width="30" height="14" fill="var(--s1)"/><text x="58" y="40" fill="var(--panel)">A100</text>
  <rect x="140" y="30" width="30" height="14" fill="none" stroke="var(--line)"/><text x="146" y="40" fill="var(--muted)">ch 0</text>
  <rect x="230" y="30" width="30" height="14" fill="var(--s2)"/><text x="238" y="40" fill="var(--panel)">B0</text>
  <text x="10" y="72" fill="var(--muted)">in flight</text>
  <rect x="52" y="62" width="30" height="14" fill="var(--s1)"/><text x="60" y="72" fill="var(--panel)">A70</text>
  <rect x="140" y="62" width="30" height="14" fill="var(--ink)"/><text x="144" y="72" fill="var(--panel)">ch 30</text>
  <rect x="230" y="62" width="30" height="14" fill="var(--s2)"/><text x="238" y="72" fill="var(--panel)">B0</text>
  <text x="10" y="104" fill="var(--muted)">after</text>
  <rect x="52" y="94" width="30" height="14" fill="var(--s1)"/><text x="60" y="104" fill="var(--panel)">A70</text>
  <rect x="140" y="94" width="30" height="14" fill="none" stroke="var(--line)"/><text x="146" y="104" fill="var(--muted)">ch 0</text>
  <rect x="230" y="94" width="30" height="14" fill="var(--s2)"/><text x="236" y="104" fill="var(--panel)">B30</text>
  </g>
  <text x="10" y="132" font-size="7.5" fill="var(--ink)">a node-only snapshot records the A and B boxes but never the channel box</text>
</svg>
^ The 30 units travel from A's box, onto the channel, into B's box. In flight it is only in the channel box — a snapshot that records A and B but not the channel simply drops it, or, recorded at the wrong ends, counts it in both A and B.

**The naive snapshot records only the node balances; the consistent snapshot adds the one term that holds the in-flight message — the channel's contents.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the checkpoint step of a distributed workflow, reduced to two nodes and one message so the conservation is checkable by hand.

Run `--states` to see where the 30 is at each moment.

```text filename=snapshot.py --states
  moment          A     B     channel A->B
  before_send     100   0     0
  in_flight       70    0     30
  after_receive   70    30    0
```

Read the middle row: in flight, A has already dropped to 70 and B is still 0, so the 30 is accounted for nowhere in the node balances — it is on the channel. In every row the three numbers sum to 100, the conserved total, but only if you include the channel column. Drop that column and the in-flight row sums to 70.

Now `--snapshots` takes the picture three ways.

```text filename=snapshot.py --snapshots
  naive, record A after send + B before recv, no channel  = 70  (-30)
  naive, record A before send + B after recv, no channel  = 130  (+30)
  consistent, record A + B + channel (Chandy-Lamport)     = 100  (+0)
```

The first naive snapshot records A in its in-flight state (70) and B before the transfer (0) and ignores the channel: total 70, thirty short — the transfer was lost. The second records A before the send (100) and B after the receive (30): total 130, thirty over — the transfer was counted twice. Neither 70 nor 130 is a state the system was ever in; both are artifacts of recording the two nodes at inconsistent points and forgetting the channel. The consistent snapshot records A and B at the cut and the 30 on the channel: total 100, exactly conserved.

<svg role="img" aria-label="Three snapshot totals against the true total of 100: naive-early 70 is short, naive-late 130 is over, consistent 100 is exact" viewBox="0 0 320 130">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">snapshot total vs true total (100)</text>
  <line x1="150" y1="24" x2="150" y2="112" stroke="var(--ink)" stroke-width="1" stroke-dasharray="3 3"/>
  <text x="132" y="124" font-size="7" fill="var(--ink)">true 100</text>
  <text x="10" y="42" font-size="8" fill="var(--s2)">naive early</text>
  <rect x="80" y="34" width="49" height="12" fill="var(--s2)"/><text x="132" y="44" font-size="7.5" fill="var(--ink)">70 (lost 30)</text>
  <text x="10" y="66" font-size="8" fill="var(--s2)">naive late</text>
  <rect x="80" y="58" width="91" height="12" fill="var(--s2)"/><text x="174" y="68" font-size="7.5" fill="var(--ink)">130 (double 30)</text>
  <text x="10" y="90" font-size="8" fill="var(--s1)">consistent</text>
  <rect x="80" y="82" width="70" height="12" fill="var(--s1)"/><text x="154" y="92" font-size="7.5" fill="var(--ink)">100 (exact)</text>
</svg>
^ The two naive snapshots land on either side of the true total — 70 (the transfer lost) and 130 (the transfer double-counted) — while the consistent snapshot that records the channel lands exactly on 100. The error is the in-flight amount, in one direction or the other.

**The two node-only snapshots total 70 and 130, both impossible states, while the consistent snapshot totals exactly 100 — the difference is entirely whether the in-flight 30 on the channel was recorded.**

## Build

The self-test asserts the real system conserves the total, then pins both naive failures: one snapshot comes in under the true total (loses the transfer), the other over it (double-counts).

```python filename=modules/orchestration-and-governance/code/snapshot-inter-01/snapshot.py:98-105 COMPLETE
    true_total_conserved = total == accounts["A"] + accounts["B"]
    print("  the real system conserves the total = %s (%d)" % (true_total_conserved, total))

    naive_loses_money = naive_lose < total
    print("  a naive snapshot LOSES the in-flight transfer = %s (%d < %d)" % (naive_loses_money, naive_lose, total))

    naive_double_counts = naive_double > total
    print("  a naive snapshot DOUBLE-COUNTS the in-flight transfer = %s (%d > %d)" % (naive_double_counts, naive_double, total))
```

Then the fix: the consistent snapshot records the in-flight message on the channel, and its total conserves.

```python filename=modules/orchestration-and-governance/code/snapshot-inter-01/snapshot.py:107-111 COMPLETE
    channel_captured = consistent["channel"] == transfer["amount"]
    print("  the consistent snapshot records the in-flight message on the channel = %s (%d)" % (channel_captured, consistent["channel"]))

    consistent_conserves = consistent["total"] == total
    print("  the consistent snapshot conserves the total = %s (%d)" % (consistent_conserves, consistent["total"]))
```

Running the check confirms every clause.

```text filename=snapshot.py --check
  the real system conserves the total = True (100)
  a naive snapshot LOSES the in-flight transfer = True (70 < 100)
  a naive snapshot DOUBLE-COUNTS the in-flight transfer = True (130 > 100)
  the consistent snapshot records the in-flight message on the channel = True (30)
  the consistent snapshot conserves the total = True (100)
```

**The check shows the naive snapshot failing conservation in both directions and the consistent snapshot conserving — with the fix pinned to the one recorded quantity that differs, the 30 on the channel.**

## Definition of done

Done means the naive snapshot provably breaks conservation — under-counting in one recording order and over-counting in the other — and the consistent snapshot conserves by recording the channel. Showing both directions of the naive error matters: it proves the problem is not a fixable "record the nodes in the right order" but is intrinsic to ignoring the channel, since no node-only ordering gets it right.

This fixture is the shrunk-down core of the Chandy-Lamport algorithm, and two of its real mechanics are worth naming even though the fixture abstracts them away. First, how a real snapshot actually captures channel contents: a node initiates by recording its own state and sending a special marker message on each outgoing channel; when a node first sees a marker on a channel it records its own state and treats that channel as empty, and for every other channel it records exactly the messages that arrive after it started but before the marker on that channel — those are the in-flight messages. The marker cleanly separates "belongs in the snapshot" from "belongs after it." Second, the guarantee: the resulting snapshot is a consistent cut — a global state that is reachable from the true initial state and from which the true current state is reachable — so even though it may never have existed at one real instant, it is a legitimate state for reasoning, backup, or deadlock detection. The property this fixture demonstrates, conservation, is exactly the kind of invariant a consistent cut preserves and an inconsistent one violates.

<svg role="img" aria-label="A consistent cut across two process timelines: the cut line crosses a message arrow, and the crossed message is recorded as channel state so the cut stays consistent" viewBox="0 0 320 130">
  <line x1="20" y1="40" x2="300" y2="40" stroke="var(--s1)" stroke-width="1"/><text x="6" y="43" font-size="7.5" fill="var(--s1)">A</text>
  <line x1="20" y1="95" x2="300" y2="95" stroke="var(--s2)" stroke-width="1"/><text x="6" y="98" font-size="7.5" fill="var(--s2)">B</text>
  <line x1="90" y1="40" x2="220" y2="95" stroke="var(--ink)" stroke-width="1.5"/>
  <text x="120" y="60" font-size="7" fill="var(--ink)">msg (30)</text>
  <line x1="150" y1="20" x2="150" y2="115" stroke="var(--muted)" stroke-width="1.5" stroke-dasharray="4 3"/>
  <text x="156" y="28" font-size="7.5" fill="var(--muted)">the cut</text>
  <circle cx="171" cy="72" r="3" fill="var(--ink)"/>
  <text x="176" y="112" font-size="7" fill="var(--ink)">cut crosses the message → record it as channel state</text>
</svg>
^ A consistent cut is a line across all process timelines. Where it crosses a message arrow — sent before the cut, received after — that message is in flight at the cut and must be recorded as channel state, which is exactly what keeps the cut consistent.

**Done means the naive snapshot breaks conservation in both directions and the consistent snapshot conserves by recording the in-flight message — the snapshot is a consistent cut only when the channel state is captured alongside the nodes.**

## Boss fight

A team runs a distributed job system and wants a "total work units in the system" metric for capacity planning. They compute it by polling every worker for its in-progress count and summing. The number is noisy and sometimes exceeds the total work that was ever submitted, which makes no sense to them. Assuming no bug in the counters themselves, what is happening, and how would you get a trustworthy total?

It is the inconsistent-snapshot problem. Polling the workers one at a time is a node-only snapshot taken at different instants, and work units are constantly moving between components — off a queue and onto a worker, from one stage to the next — on the channels between them. If a unit has left the queue's count but the worker that took it is polled a moment later, after it also finished and handed the unit onward, the same unit can be counted in two places, which is why the sum can exceed the true total; symmetrically, a unit in transit at the wrong moment is counted nowhere and the sum dips low. The counters are all correct; the sum across inconsistent moments is not a real global state. To get a trustworthy total, take a consistent snapshot instead of an independent poll: record not just each component's in-progress count but the work in flight on the channels between them — the units dequeued-but-not-yet-started, the results emitted-but-not-yet-consumed — so that every unit is counted exactly once. The clean way is a Chandy-Lamport-style snapshot with marker messages that separate what belongs in the snapshot from what comes after; a cheaper approximation, if the exact instant matters less, is to assign each unit a single owner at all times (a unit is always attributed to exactly one component, and hand-off is an atomic transfer of ownership) so that no cut can double-count or drop it. Either way, the fix is to stop treating an independent poll of nodes as a global snapshot and to account for what is on the channels.

## External resources

The Chandy-Lamport paper "Distributed Snapshots: Determining Global States of Distributed Systems" and its textbook treatments — the marker-message algorithm, the definition of a consistent cut, and the proof that the recorded state is reachable, all of which this fixture reduces to a single transfer.

Documentation for consistent-snapshot and checkpointing mechanisms in real systems (Apache Flink's asynchronous barrier snapshotting for exactly-once state, and distributed-database and stream-processor checkpoint designs) — the production descendants of Chandy-Lamport that record in-flight data along with operator state to get a globally consistent checkpoint.
