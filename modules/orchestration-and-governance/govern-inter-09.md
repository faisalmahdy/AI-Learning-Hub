---
id: govern-inter-09
title: Fence writes with a monotonic epoch — or a stale leader that lost its lease corrupts state
topic: orchestration-and-governance
level: intermediate
status: ready
time: 5-8h
summary: A cluster elects one leader to make changes, but when the leader is partitioned away its lease expires and a new leader is elected — and the old leader, cut off, does not know it has been replaced and keeps issuing writes believing it is still in charge, so two nodes think they are the leader: split-brain. If the resource accepts writes from anyone claiming to be leader, the deposed leader's stale write lands after the new leader's and overwrites correct state with the decisions of a leader that no longer exists. A fencing token stops it: each leadership term gets a monotonically increasing epoch, every write carries its leader's epoch, and the resource remembers the highest epoch it has accepted and rejects any write with a lower one — so once the new leader (epoch 2) has written, the old leader's epoch-1 writes are refused no matter that it still thinks it is in charge. On the fixture nodeA is deposed but issues a late epoch-1 write after nodeB's epoch-2 writes; without fencing that stale write wins and the final state is nodeA's x=99, while with fencing it is rejected and the state stays nodeB's x=3. The lease alone is not enough because a partitioned leader cannot be told to stop, so the guard must live at the resource, which fences every write by epoch.
eli5: Imagine a store where only the manager on duty can approve refunds, and the manager wears a numbered badge that goes up each time the shift changes. The old manager gets locked out back and doesn't realize a new manager (badge 2) took over, so he keeps shouting refund approvals with his old badge 1. If the cashier listens to anyone shouting, the old manager can still mess things up. The fix: the cashier only obeys the highest badge number they've seen, so once badge 2 has spoken, badge 1 is ignored — even though the old manager still thinks he's in charge.
---

## Why this module

Many systems designate a single leader to serialize changes — one node that gets to write, so there are never two conflicting decisions about the same state. The leader holds its position with a lease: a time-limited grant that must be renewed. If the leader stops renewing (it crashed, or it was partitioned off the network), the lease expires and the cluster elects a new leader. This is the standard, correct design, and it has one sharp edge that this module is about.

<svg viewBox="0 0 700 170" role="img" aria-label="A network partition. nodeA is on one side, cut off by a partition line, still believing it is leader with epoch 1. The cluster and nodeB are on the other side; the cluster elected nodeB as the new leader with epoch 2. Both nodeA and nodeB send writes toward the shared resource in the middle.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">a partition makes two leaders at once — both write to the resource</text>
    <rect x="30" y="50" width="130" height="44" fill="var(--panel)" stroke="var(--s2)"></rect><text x="95" y="70" text-anchor="middle" fill="var(--s2)" font-size="8">nodeA (epoch 1)</text><text x="95" y="84" text-anchor="middle" fill="var(--muted)" font-size="7">"still leader" (wrong)</text>
    <line x1="200" y1="30" x2="200" y2="140" stroke="var(--s2)" stroke-dasharray="6 4"></line><text x="200" y="150" text-anchor="middle" fill="var(--s2)" font-size="7">partition</text>
    <rect x="240" y="30" width="130" height="34" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="305" y="50" text-anchor="middle" fill="var(--acc-ink)" font-size="8">cluster elects →</text>
    <rect x="240" y="78" width="130" height="34" fill="var(--panel)" stroke="var(--acc-line)"></rect><text x="305" y="98" text-anchor="middle" fill="var(--acc-ink)" font-size="8">nodeB (epoch 2)</text>
    <rect x="500" y="60" width="120" height="40" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="560" y="84" text-anchor="middle" fill="var(--acc-ink)" font-size="8">resource</text>
    <line x1="160" y1="80" x2="500" y2="78" stroke="var(--s2)" stroke-dasharray="3 2"></line><text x="330" y="128" fill="var(--s2)" font-size="7">nodeA's stale writes ↗</text>
    <line x1="370" y1="95" x2="500" y2="85" stroke="var(--acc-line)"></line>
    <text x="440" y="152" fill="var(--muted)" font-size="8">the resource must decide whose writes to honor — that is where the fence goes</text>
  </g>
</svg>
^ The partition splits nodeA off, but nodeA still thinks it leads (epoch 1) while the cluster elects nodeB (epoch 2). Both stream writes to the resource, which is the only place that can tell the ghost from the real leader.

The edge is that a partitioned leader does not know it has been deposed. From its own point of view nothing is wrong — it just cannot reach the rest of the cluster — so it keeps doing its job, issuing writes as if it were still the leader. Meanwhile the cluster, having not heard from it, has moved on and elected a new leader who is also issuing writes. Now there are two leaders at once: split-brain. The old leader's writes and the new leader's writes both flow toward the shared resource, and if the resource honors both, the old leader — a ghost, a leader that no longer legitimately exists — can overwrite the new leader's correct state with stale decisions. You cannot fix this by telling the old leader to stop, because the whole problem is that you cannot reach it.

So the guard has to live at the resource, and the mechanism is a fencing token. Every leadership term is assigned a monotonically increasing number — an epoch — and every write the leader issues is stamped with its epoch. The resource keeps the highest epoch it has ever accepted and refuses any write stamped with a lower one. Once the new leader (epoch 2) has written, the resource's high-water mark is 2, and the deposed leader's epoch-1 writes are rejected on arrival, no announcement to the old leader required. This module makes it concrete: the same write sequence applied without fencing (the stale leader wins) and with fencing (the stale write is refused). Everything runs offline against a writes fixture, stdlib Python 3, `$0.00`, with every applied state computed. The instinct to unlearn is that a lease prevents two leaders. A lease bounds how long the old leader thinks it is in charge, but only fencing at the resource prevents its stale writes from landing.

## Concepts

Named here so you can find them again; each is built below.

- **Leader and lease** — one node writes, holding a time-limited grant it must renew.
- **Split-brain** — a deposed (partitioned) leader still writing while a new leader also writes.
- **Epoch (fencing token)** — a monotonically increasing number per leadership term, stamped on every write.
- **High-water mark** — the highest epoch the resource has accepted; the fence.
- **Stale write** — a write from a leader whose epoch is below the high-water mark.
- **Resource-side guard** — the fence must live at the resource, because the deposed leader is unreachable.

## Worked example

Source: the write path of a leader-based system during a failover — the moment a deposed leader and a new leader both issue writes. The write sequence stands in for a real split-brain; the epochs are the fencing tokens a lease/consensus layer assigns.

Script and fixture: `modules/orchestration-and-governance/code/govern-inter-09/` — `fencing.py`, and `writes.json`, four writes across a leadership change. Every command runs from there.

### The split-brain write sequence

Two leaders' writes interleave, and the deposed leader's arrives last.

```
# $ python3 fencing.py --writes
#   nodeA    epoch 1  value=x=1
#   nodeB    epoch 2  value=x=2
#   nodeB    epoch 2  value=x=3
#   nodeA    epoch 1  value=x=99
#   nodeA was deposed but keeps writing at its old epoch after nodeB took over.
```

run: 2026-08-27 · deterministic; the write sequence is a fixture · 4 writes · `python3 fencing.py --writes`

Read the sequence. nodeA writes at epoch 1 (it is the leader). Then nodeB writes twice at epoch 2 — nodeB has become the new leader, so its epoch is higher. Then nodeA, still partitioned and still believing it is the leader, issues one more write at its old epoch 1, and it arrives last. The legitimate current leader is simply the one holding the highest epoch:

```
# fencing.py:62-64 — COMPLETE (the current leader is the holder of the highest epoch)
def current_leader(writes):
    """The leader of the highest epoch -- the one legitimately in charge."""
    return max(writes, key=lambda w: w["epoch"])["leader"]
```

The correct final state is nodeB's most recent write, x=3, because nodeB is the legitimate current leader. Whether the system ends up there depends entirely on whether the resource fences by epoch.

### Applying with and without fencing

The two resources differ by one comparison: whether they check the epoch against a high-water mark.

```
# fencing.py:40-60 — COMPLETE (accept everything vs reject writes below the highest epoch)
def apply_without_fencing(writes):
    """Accept every write in arrival order -- a stale leader's write overwrites the current one's."""
    state, log = None, []
    for w in writes:
        state = w["value"]
        log.append((w["leader"], w["epoch"], "applied", state))
    return state, log


def apply_with_fencing(writes):
    """Reject any write whose epoch is below the highest epoch already accepted."""
    state, highest, log = None, 0, []
    for w in writes:
        if w["epoch"] < highest:
            log.append((w["leader"], w["epoch"], "REJECTED (stale)", state))
            continue
        highest = w["epoch"]
        state = w["value"]
        log.append((w["leader"], w["epoch"], "applied", state))
    return state, log
```

`apply_without_fencing` writes whatever it is handed. `apply_with_fencing` tracks `highest` — the high-water mark — and refuses any write whose epoch is below it. That single `if w["epoch"] < highest` is the fence. Run both on the sequence:

```
# $ python3 fencing.py --apply
#   without fencing:
#     nodeA    e1  applied            -> x=1
#     nodeB    e2  applied            -> x=2
#     nodeB    e2  applied            -> x=3
#     nodeA    e1  applied            -> x=99
#     final state: x=99
#   with fencing:
#     nodeA    e1  applied            -> x=1
#     nodeB    e2  applied            -> x=2
#     nodeB    e2  applied            -> x=3
#     nodeA    e1  REJECTED (stale)   -> x=3
#     final state: x=3
```

run: 2026-08-27 · deterministic · `python3 fencing.py --apply`

Without fencing, all four writes apply in order, so nodeA's late epoch-1 write lands last and the final state is x=99 — the decision of a leader that was deposed two writes ago. The system has been corrupted by a ghost. With fencing, the first three writes apply (their epochs are non-decreasing), but nodeA's final epoch-1 write is below the high-water mark of 2, so it is rejected, and the state stays x=3 — nodeB's correct value. Same writes, same order; the fence caught the one that came from the wrong epoch.

<svg viewBox="0 0 700 210" role="img" aria-label="A timeline of four writes. nodeA epoch 1 (x=1), nodeB epoch 2 (x=2), nodeB epoch 2 (x=3), nodeA epoch 1 (x=99, late). Without fencing all apply and the final state is x=99. With fencing, the high-water mark rises to 2 and the last epoch-1 write is rejected, keeping x=3.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the deposed leader's late epoch-1 write: accepted (corrupt) or fenced</text>
    <rect x="40" y="40" width="120" height="26" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="100" y="57" text-anchor="middle" fill="var(--acc-ink)" font-size="8">nodeA e1 → x=1</text>
    <rect x="180" y="40" width="120" height="26" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="240" y="57" text-anchor="middle" fill="var(--acc-ink)" font-size="8">nodeB e2 → x=2</text>
    <rect x="320" y="40" width="120" height="26" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="380" y="57" text-anchor="middle" fill="var(--acc-ink)" font-size="8">nodeB e2 → x=3</text>
    <rect x="460" y="40" width="120" height="26" fill="var(--s2)"></rect><text x="520" y="57" text-anchor="middle" fill="var(--panel)" font-size="8">nodeA e1 → x=99</text>
    <text x="520" y="34" text-anchor="middle" fill="var(--s2)" font-size="7">deposed, late</text>
    <text x="30" y="110" fill="var(--s2)" font-size="8">no fence</text>
    <rect x="460" y="98" width="120" height="22" fill="var(--s2)"></rect><text x="520" y="113" text-anchor="middle" fill="var(--panel)" font-size="8">applied → x=99 ✗</text>
    <text x="600" y="113" fill="var(--s2)" font-size="8">corrupt</text>
    <text x="30" y="160" fill="var(--s1)" font-size="8">fenced</text>
    <text x="40" y="145" fill="var(--muted)" font-size="7">high-water mark = 2</text>
    <rect x="460" y="148" width="120" height="22" fill="var(--panel)" stroke="var(--s1)" stroke-dasharray="3 2"></rect><text x="520" y="163" text-anchor="middle" fill="var(--s1)" font-size="8">e1 &lt; 2 REJECTED</text>
    <text x="600" y="163" fill="var(--s1)" font-size="8">→ x=3 ✓</text>
    <text x="40" y="195" fill="var(--muted)" font-size="8">the fence compares each write's epoch to the highest accepted; a lower one is a ghost</text>
  </g>
</svg>
^ Without a fence the deposed leader's late epoch-1 write applies and the state becomes x=99; with the high-water mark at 2, that write is below it and rejected, so the state stays x=3. The fence is one comparison at the resource.

**A partitioned leader that lost its lease cannot be told it was deposed, so it keeps issuing writes (split-brain), and only a fence at the resource stops them: stamp each leadership term with a monotonic epoch, have the resource reject any write below the highest epoch it has accepted, and the deposed leader's epoch-1 write is refused after the new leader's epoch-2 writes — the difference between a final state of x=99 (the ghost's) and x=3 (the true leader's).**

### The self-test

The `--check` mode plants the bug — a resource with no fence — and proves it: without fencing the final state is the deposed leader's, with fencing it is the current leader's, fencing rejects exactly the deposed leader's stale writes, and epochs are monotonic across the handover.

```
# $ python3 fencing.py --check
#   without fencing, the final state is NOT the current leader's = True (state x=99, should be x=3)
#   with fencing, the final state IS the current leader's = True (state x=3)
#   fencing rejects the deposed leader's stale writes = True (1 rejected)
#   the current leader's epoch exceeds the deposed leader's = True
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 fencing.py --check`

The `monotonic` line is the property that makes the fence sound: because each new leadership term has a strictly higher epoch than the last, "reject anything below the highest seen" is exactly "reject anything from a superseded leader." If epochs could repeat or go backward, the fence would let a stale leader through or block a valid one — which is why the epoch must be issued by the consensus/lease layer that elects leaders, not chosen by the leaders themselves.

The monotonicity is checked directly — the current leader's epoch strictly exceeds the deposed one's:

```
# fencing.py:120-123 — COMPLETE (epochs increase across the handover: current > deposed)
    epochs_by_leader = {}
    for w in writes:
        epochs_by_leader.setdefault(w["leader"], set()).add(w["epoch"])
    monotonic = max(epochs_by_leader[leader]) > max(epochs_by_leader[data["deposed"]])
```

<svg viewBox="0 0 700 160" role="img" aria-label="A high-water-mark timeline. As writes arrive, the resource's highest-accepted epoch rises: 0, then 1 (nodeA), then 2 (nodeB), stays 2. When nodeA's late epoch-1 write arrives, 1 is below the high-water mark of 2, so it is rejected.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the resource's high-water mark only rises; a lower epoch is a ghost</text>
    <line x1="60" y1="120" x2="640" y2="120" stroke="var(--line)"></line>
    <line x1="60" y1="120" x2="60" y2="40" stroke="var(--line)"></line>
    <text x="52" y="60" text-anchor="end" fill="var(--muted)" font-size="7">e2</text><text x="52" y="90" text-anchor="end" fill="var(--muted)" font-size="7">e1</text>
    <polyline points="60,120 160,90 280,60 400,60 520,60" fill="none" stroke="var(--s1)"></polyline>
    <circle cx="160" cy="90" r="4" fill="var(--s1)"></circle><text x="160" y="136" text-anchor="middle" fill="var(--muted)" font-size="7">nodeA e1</text>
    <circle cx="280" cy="60" r="4" fill="var(--s1)"></circle><text x="280" y="136" text-anchor="middle" fill="var(--muted)" font-size="7">nodeB e2</text>
    <circle cx="400" cy="60" r="4" fill="var(--s1)"></circle><text x="400" y="136" text-anchor="middle" fill="var(--muted)" font-size="7">nodeB e2</text>
    <circle cx="520" cy="90" r="5" fill="var(--s2)"></circle><line x1="520" y1="90" x2="520" y2="62" stroke="var(--s2)" stroke-dasharray="2 2"></line><text x="520" y="136" text-anchor="middle" fill="var(--s2)" font-size="7">nodeA e1 ✗</text>
    <text x="560" y="94" fill="var(--s2)" font-size="7">below mark → reject</text>
  </g>
</svg>
^ The high-water mark climbs 1 → 2 and never falls; nodeA's late epoch-1 write sits below the mark of 2, so it is rejected. Monotonic epochs make "below the mark" mean exactly "from a superseded leader."

```
# fencing.py:106-111 — COMPLETE (without fencing the stale leader wins; with fencing the true state holds)
    stale_wins = s_no != true_value
    print("  without fencing, the final state is NOT the current leader's = %s (state %s, should be %s)"
          % (stale_wins, s_no, true_value))

    s_fen, log_fen = apply_with_fencing(writes)
    fencing_correct = s_fen == true_value
```

### The running tally

| write | leader | epoch | without fencing | with fencing |
|---|---|---|---|---|
| x=1 | nodeA | 1 | applied → x=1 | applied → x=1 |
| x=2 | nodeB | 2 | applied → x=2 | applied → x=2 |
| x=3 | nodeB | 2 | applied → x=3 | applied → x=3 |
| x=99 | nodeA | 1 | applied → x=99 | REJECTED → x=3 |

Read the last row across: it is the whole module. The deposed nodeA's epoch-1 write is accepted without a fence (final state x=99, corrupt) and rejected with one (final state x=3, correct). Every other row is identical between the two columns, because fencing only ever rejects writes below the high-water mark, so it is invisible during normal operation and decisive exactly when a stale leader tries to write. That is the signature of a good safety mechanism: no cost when things are fine, and the one thing standing between you and corruption when they are not.

### What we did not settle

This is the fencing token; production leader election builds it in. The epoch must come from the same authority that grants leadership — a consensus system (Raft, ZooKeeper/ZAB) or a lock service that hands out monotonically increasing fencing tokens with each lease — so leaders cannot forge or reuse them. The resource must persist its high-water mark, or a restart would forget it and re-admit stale writes. Fencing assumes the resource can check the token; a resource that cannot (a dumb disk, a third-party API without this notion) needs the fence in front of it (a proxy) or a different safety story. Time-based leases still matter for liveness (how fast a new leader can be elected) and rely on bounded clock drift; fencing is the safety backstop that does not trust clocks. And this shows one stale write — the same fence handles a deposed leader that keeps writing indefinitely. The invariant: a lease bounds belief, a fence bounds action; put a monotonic epoch on every write and reject the stale ones at the resource.

## Build

The build in one paragraph: assign every leadership term a monotonically increasing epoch (fencing token) from the consensus or lock service that grants leadership, stamp it on every write, and have the resource keep the highest epoch it has accepted and reject any write below it — so a partitioned leader that lost its lease but keeps writing has its stale writes refused at the resource, without needing to be reachable or told it was deposed. Persist the high-water mark across restarts, source the epoch from the election authority (never let leaders pick it), put a fencing proxy in front of resources that cannot check tokens themselves, and keep leases for liveness while relying on the fence for safety.

We opened on the split-brain sequence. The number that proves the fix is the final state under each resource:

```
# modules/orchestration-and-governance/code/govern-inter-09/ — COMPLETE, run from that directory
$ python3 fencing.py --apply
  without fencing:  final state: x=99   (the deposed leader's)
  with fencing:     final state: x=3    (the current leader's)
```

Now build your own. Model a leadership change where a deposed leader keeps writing at its old epoch, and apply the writes to a resource with and without an epoch fence. Your number to beat is not throughput; it is **the final state under each: without a fence the stale leader's write should win, with a fence it should be rejected and the current leader's state preserved**. Confirm the fence rejects only the deposed leader's writes. Bring back both final states. Good luck.

## Definition of done

- [ ] A write sequence tagged with leader and monotonic epoch, including a deposed leader's late write
- [ ] A resource that applies every write (no fencing)
- [ ] A resource that rejects writes below the highest epoch accepted (fencing)
- [ ] Confirmation without fencing the final state is the deposed leader's (corruption)
- [ ] Confirmation with fencing the final state is the current leader's
- [ ] Confirmation the fence rejects exactly the deposed leader's stale writes, and epochs are monotonic
- [ ] `python3 fencing.py --check` printing SELF-TEST PASS: stale_wins, fencing_correct, fencing_rejects_stale, monotonic
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why does a partitioned leader keep writing, and why can't you fix split-brain by telling it to stop?
2. What is a fencing token, and where must the check that uses it live?
3. On the fixture, why is the deposed leader's write rejected with fencing but accepted without?
4. Why must the epoch be issued by the election authority rather than chosen by the leader?
5. Your own leadership change was applied both ways. What was the final state under each, and did the fence reject only the stale writes?

## External resources

- Martin Kleppmann, *How to do distributed locking* — my summary: the canonical explanation of why leases alone are unsafe and fencing tokens are required, with the exact stale-leader scenario; read it for the argument this module encodes.
- Raft / ZooKeeper (ZAB) documentation on terms/epochs — my summary: how consensus systems assign monotonically increasing leadership numbers usable as fencing tokens; read it for where the epoch comes from.
- This hub, *govern-inter-07* (quorum before trusting a vote) and *govern-basic-01* (trust the evidence, not the agent's word) — read them for the related governance discipline of not acting on authority that cannot be verified.
