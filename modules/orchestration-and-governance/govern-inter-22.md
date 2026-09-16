---
id: govern-inter-22
title: A participant that voted yes but hasn't heard the decision cannot resolve alone — two-phase commit blocks
topic: orchestration-and-governance
level: intermediate
status: ready
time: 18 min
summary: Two-phase commit makes participants agree to commit-or-abort atomically, and it is correct — it never commits on one node and aborts on another. But between voting YES in phase one and hearing the decision in phase two, a participant is in a window of uncertainty: it cannot abort (it promised it could commit, and the coordinator may have told the others to commit) and cannot commit (it does not know whether everyone else voted yes). Its only legal move is to wait for the coordinator. So if the coordinator crashes while any participant is in that window, the participant blocks — frozen, holding its locks — until the coordinator recovers. On a fixture where two participants vote yes at ticks 1 and 2 and learn the decision at ticks 4 and 5, a coordinator crash at tick 0 blocks nobody, a crash at tick 2 blocks both, a crash at tick 4 still blocks the participant that hasn't heard, and even a crash after the decision is logged (tick 3) blocks whoever hasn't yet received it.
eli5: Imagine three friends agreeing to all buy tickets to the same show only if everyone's in. Each texts back "yes, I'm in" and then waits for the organizer to say "okay, buy them." If the organizer's phone dies right after everyone said yes, no single friend can decide alone: they can't back out (they promised) and can't buy (they don't know if the others are really in). They're stuck waiting for the organizer to come back. That stuck-waiting is exactly why this way of agreeing can freeze.
---

## Why this module

Two-phase commit is correct but not live: it guarantees the participants never disagree, and pays for that with a window where a participant can do nothing but wait for a coordinator that may be gone.

The protocol has two phases. In phase one the coordinator asks every participant to PREPARE, and each one that can commit votes YES and enters the prepared state — a promise that it *will* commit if told to, which it keeps by holding its locks and refusing to abort on its own. In phase two, once all votes are in, the coordinator records the decision and tells everyone, and they commit. Nothing here ever commits on one node while aborting on another; the safety is airtight. But look at a single participant between the two phases: it has voted yes and is waiting. It cannot abort, because it promised it could commit and the coordinator may already have told the others to do so. It cannot commit, because it does not know whether every other participant also voted yes. It can only wait for the coordinator to speak.

**Between voting yes and hearing the decision, a participant is in a window of uncertainty where it can neither abort nor commit on its own — its only legal move is to wait for the coordinator.**

That window is the whole problem. If the coordinator crashes while any participant is inside it, that participant blocks: it sits holding its locks, unable to progress, until the coordinator recovers and tells it the outcome. The decision is not lost — a recovered coordinator resolves it from its log — but until recovery the participant is frozen, and so is every transaction waiting on those locks. This is why two-phase commit is called a *blocking* protocol, and why sagas and consensus-based commit exist. This module walks the timeline and shows exactly which coordinator-crash moments freeze which participants.

## Concepts

**Phase one (prepare/vote)** asks each participant to promise it can commit; a YES vote moves it to the prepared state, holding locks.

**Phase two (decision)** happens after all votes: the coordinator logs commit-or-abort and delivers it, and participants finish.

The **window of uncertainty** is the interval from a participant voting YES to it learning the decision. Inside it the participant is prepared but undecided — bound by its promise, ignorant of the outcome.

**Blocking** is what happens when the coordinator crashes and a participant is in its window: it cannot resolve alone, so it waits, holding locks, until recovery. The outcome is safe but the system is stalled.

**The decision being logged does not unblock anyone who hasn't heard it.** Once the coordinator records commit, the outcome is determined and recoverable — but a participant that has not yet received the message is still frozen until it does, so logging the decision ends the risk of *losing* it, not the risk of *blocking* on it.

```python filename=modules/orchestration-and-governance/code/govern-inter-22/twopc.py:41-43 COMPLETE
def window(data, p):
    """A participant's uncertainty window [voted YES, decision delivered): prepared, holding locks, undecided."""
    return data["votes_yes"][p], data["decision_delivered"][p]
```

**Two-phase commit trades liveness for safety: it never lets participants disagree, but its window of uncertainty means a coordinator crash can block a prepared participant indefinitely, holding locks, until recovery.**

<svg role="img" aria-label="Phase one collects votes; the participant enters the uncertainty window after voting yes; phase two delivers the decision and ends the window" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">one participant's path through 2PC</text>
  <rect x="15" y="26" width="52" height="18" fill="var(--grid)"/><text x="22" y="39" fill="var(--muted)" font-size="7">get PREPARE</text>
  <text x="69" y="39" fill="var(--muted)" font-size="10">→</text>
  <rect x="82" y="26" width="44" height="18" fill="var(--s2)"/><text x="88" y="39" fill="var(--panel)" font-size="7">vote YES</text>
  <text x="128" y="39" fill="var(--muted)" font-size="10">→</text>
  <rect x="143" y="26" width="70" height="18" fill="var(--s2)"/><text x="150" y="39" fill="var(--panel)" font-size="7">WAIT (locked)</text>
  <text x="215" y="39" fill="var(--muted)" font-size="10">→</text>
  <rect x="230" y="26" width="55" height="18" fill="var(--s1)"/><text x="236" y="39" fill="var(--panel)" font-size="7">commit</text>
  <line x1="82" y1="48" x2="230" y2="48" stroke="var(--s2)" stroke-width="1.5"/><text x="110" y="62" fill="var(--s2)" font-size="8">window of uncertainty — coordinator crash here = BLOCK</text>
  <text x="15" y="86" fill="var(--muted)" font-size="8">can't abort (promised) and can't commit (doesn't know) — only wait</text>
</svg>
^ The participant is free to abort before it votes and free to commit once told, but across the shaded middle span it can only wait — and a coordinator crash there freezes it.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/govern-inter-22/twopc.py

The fixture is a timeline: when each participant votes yes, when the coordinator logs the decision, and when each learns it.

```json filename=modules/orchestration-and-governance/code/govern-inter-22/twopc.json:3-9 COMPLETE
  "participants": ["p1", "p2"],
  "prepare_sent": 0,
  "votes_yes": {"p1": 1, "p2": 2},
  "decision_logged": 3,
  "decision_delivered": {"p1": 4, "p2": 5},
  "crash_times": [0, 2, 4, 6]
}
```

A participant blocks on a crash at time t exactly when t falls inside its uncertainty window — voted yes, not yet told the outcome.

```python filename=modules/orchestration-and-governance/code/govern-inter-22/twopc.py:46-53 COMPLETE
def blocked_at(data, t):
    """Participants that block if the coordinator crashes at time t: those inside their uncertainty window."""
    out = []
    for p in data["participants"]:
        lo, hi = window(data, p)
        if lo <= t < hi:
            out.append(p)
    return out
```

Run `--timeline` to see each window.

```text filename=--timeline
TIMELINE — each participant's window of uncertainty (prepared, holding locks, undecided)
------------------------------------------------------------------
  prepare sent at tick 0; coordinator logs COMMIT at tick 3
  p1   votes YES at 1, learns decision at 4  ->  uncertain during [1, 4)
  p2   votes YES at 2, learns decision at 5  ->  uncertain during [2, 5)
------------------------------------------------------------------
  inside its window a participant can neither abort (it promised) nor commit (it doesn't know).
```

Participant p1 is exposed from tick 1 to tick 4, p2 from tick 2 to tick 5. Note the coordinator logs the decision at tick 3 — inside both windows — so even after the outcome is decided and safe from loss, both participants are still uncertain, because neither has been told yet. The window closes only when the message arrives, not when the decision is made.

<svg role="img" aria-label="p1 is uncertain from tick 1 to 4 and p2 from tick 2 to 5; the decision is logged at tick 3, inside both windows" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">ticks 0–6; bars = window of uncertainty</text>
  <line x1="20" y1="95" x2="290" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <text x="20" y="105" fill="var(--muted)" font-size="7">0</text><text x="132" y="105" fill="var(--muted)" font-size="7">3</text><text x="245" y="105" fill="var(--muted)" font-size="7">6</text>
  <line x1="133" y1="24" x2="133" y2="95" stroke="var(--s1)" stroke-width="1" stroke-dasharray="3 2"/><text x="118" y="22" fill="var(--s1)" font-size="7">logged @3</text>
  <text x="4" y="45" fill="var(--muted)" font-size="8">p1</text><rect x="57" y="38" width="113" height="12" fill="var(--s2)"/><text x="172" y="47" fill="var(--muted)" font-size="7">[1,4)</text>
  <text x="4" y="70" fill="var(--muted)" font-size="8">p2</text><rect x="95" y="63" width="113" height="12" fill="var(--s2)"/><text x="210" y="72" fill="var(--muted)" font-size="7">[2,5)</text>
  <text x="20" y="90" fill="var(--muted)" font-size="8">the logged line falls inside both bars — decided but not yet delivered</text>
</svg>
^ Both windows straddle the tick-3 decision line: the outcome is settled there, but each participant stays uncertain until its own bar ends, when the message finally arrives.

## Build

Now crash the coordinator at each moment and see who freezes. Run `--crash`.

```text filename=--crash
CRASH — coordinator crashes at each time; who blocks holding locks
------------------------------------------------------------------
  crash at tick 0  ->  SAFE (no one prepared-and-undecided)
  crash at tick 2  ->  BLOCKS ['p1', 'p2']
  crash at tick 4  ->  BLOCKS ['p2']
  crash at tick 6  ->  SAFE (no one prepared-and-undecided)
```

At tick 0 nobody has voted yet, so a crash is safe — every participant can simply abort on timeout, and no promise is broken. At tick 2 both participants have voted yes and neither has heard back, so a crash blocks both: they hold their locks and wait. At tick 4 p1 has learned the decision and moved on, but p2 has not, so a crash still blocks p2 — one straggler is enough to stall. Only at tick 6, after both have the decision, is a crash harmless again. The dangerous interval is precisely the union of the windows, and it exists no matter how fast the coordinator is: shrinking it reduces the odds of a crash landing inside, but never removes the interval.

<svg role="img" aria-label="A coordinator crash blocks nobody at tick 0, both participants at tick 2, only p2 at tick 4, and nobody at tick 6" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">participants blocked by a coordinator crash at each tick</text>
  <text x="30" y="34" fill="var(--muted)" font-size="8">tick 0</text><rect x="80" y="24" width="6" height="12" fill="var(--grid)"/><text x="92" y="34" fill="var(--muted)" font-size="8">safe — 0 blocked</text>
  <text x="30" y="54" fill="var(--muted)" font-size="8">tick 2</text><rect x="80" y="44" width="60" height="12" fill="var(--s2)"/><text x="146" y="54" fill="var(--s2)" font-size="8">blocks p1 + p2</text>
  <text x="30" y="74" fill="var(--muted)" font-size="8">tick 4</text><rect x="80" y="64" width="30" height="12" fill="var(--s2)"/><text x="116" y="74" fill="var(--muted)" font-size="8">blocks p2 (straggler)</text>
  <text x="30" y="94" fill="var(--muted)" font-size="8">tick 6</text><rect x="80" y="84" width="6" height="12" fill="var(--grid)"/><text x="92" y="94" fill="var(--muted)" font-size="8">safe — 0 blocked</text>
  <text x="30" y="108" fill="var(--muted)" font-size="7">the danger is the whole span from first vote to last delivery, not a single instant</text>
</svg>
^ A crash is harmless at the ends and blocks inside — both participants at the peak, a lone straggler as deliveries trickle in — so the exposure is the entire span between the first yes and the last delivery.

## Definition of done

The self-test pins the shape: safe before any vote, everyone blocked once all have voted, safe after all deliveries, still blocking after the decision is logged, and the window running from vote to delivery.

```python filename=modules/orchestration-and-governance/code/govern-inter-22/twopc.py:85-101 COMPLETE
    crash_before_prepare_safe = blocked_at(data, data["prepare_sent"]) == []
    print("  a crash at prepare-time (no yes votes yet) blocks no one = %s" % crash_before_prepare_safe)

    peak = max(data["votes_yes"].values())
    all_prepared_block = set(blocked_at(data, peak)) == set(parts)
    print("  a crash once all have voted yes blocks every participant = %s (%s)" % (all_prepared_block, blocked_at(data, peak)))

    last_delivery = max(data["decision_delivered"].values())
    crash_after_delivery_safe = blocked_at(data, last_delivery) == []
    print("  a crash after every participant has the decision blocks no one = %s" % crash_after_delivery_safe)

    p_last = max(parts, key=lambda p: window(data, p)[1])
    lo, hi = window(data, p_last)
    still_blocks_after_decision_logged = data["decision_logged"] < hi and p_last in blocked_at(data, data["decision_logged"])
    print("  a crash even AFTER the decision is logged still blocks a participant that hasn't heard = %s (%s uncertain until %d)" % (still_blocks_after_decision_logged, p_last, hi))

    window_is_vote_to_delivery = window(data, p_last) == (data["votes_yes"][p_last], data["decision_delivered"][p_last])
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — a crash before any vote is safe; a crash inside the window blocks; after all deliveries it is safe
----------------------------------------------------------------------------------------------------------------
  a crash at prepare-time (no yes votes yet) blocks no one = True
  a crash once all have voted yes blocks every participant = True (['p1', 'p2'])
  a crash after every participant has the decision blocks no one = True
  a crash even AFTER the decision is logged still blocks a participant that hasn't heard = True (p2 uncertain until 5)
  the window runs exactly from voting yes to learning the decision = True (2, 5)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  crash_before_prepare_safe=True  all_prepared_block=True  crash_after_delivery_safe=True  still_blocks_after_decision_logged=True  window_is_vote_to_delivery=True
```

**Done means the blocking window is pinned exactly: a crash at prepare-time blocks no one, a crash once both have voted blocks both, a crash after the decision is logged (tick 3) still blocks p2 until it hears at tick 5, and safety returns only after the last delivery.**

## Boss fight

Two-phase commit blocks in the window. Predict what three-phase commit adds to reduce it, and whether that makes 2PC the wrong choice. It is tempting to conclude 2PC is simply broken and should never be used.

Three-phase commit inserts a pre-commit phase between the vote and the commit, so a participant that crashed-coordinator can look at whether its peers reached pre-commit and infer the decision without the coordinator — turning the blocking window into a recoverable one under a fail-stop model. But 3PC buys that with an extra network round trip on every transaction and it still fails under network partitions, which is why production systems that truly need non-blocking atomic commit use consensus (Paxos Commit, Raft-backed transactions) where a *majority* replaces the single coordinator, so no one node's crash can stall the group. The lesson is not that 2PC is broken — it is correct, and its window is small when the coordinator is fast and reliable — but that its liveness depends entirely on the coordinator, and you escape that dependency only by replacing the single coordinator with a quorum.

The practical escape hatch is often to not require distributed atomic commit at all. A saga replaces the all-or-nothing transaction with a sequence of local commits plus compensating actions: each step commits independently and, on failure, earlier steps are undone by explicit compensation. There is no prepared-and-waiting window because there is no global prepare — the trade is that you give up isolation (other transactions can see the intermediate states) and must write a correct compensator for every step. So the real decision is upstream of 2PC versus 3PC: if you can tolerate eventual consistency and write compensations, a saga sidesteps the blocking problem entirely; if you genuinely need atomic isolation across nodes, pay for consensus rather than trusting a lone coordinator not to crash in the window.

```python filename=modules/orchestration-and-governance/code/govern-inter-22/twopc.py:72-75 COMPLETE
    for t in data["crash_times"]:
        b = blocked_at(data, t)
        verdict = "SAFE (no one prepared-and-undecided)" if not b else "BLOCKS %s" % b
        print("  crash at tick %d  ->  %s" % (t, verdict))
```

**Two-phase commit is safe but blocking: a participant prepared and awaiting the decision cannot resolve alone, so a coordinator crash in that window freezes it holding locks until recovery — shrink the window with a fast coordinator, escape it with consensus (a quorum replaces the single coordinator), or sidestep it with a saga that trades isolation for local commits and compensation.**

## External resources

Any distributed-systems text's treatment of atomic commit (for example the chapters in *Designing Data-Intensive Applications*) — the two-phase protocol, its blocking window, and the three-phase and Paxos-Commit alternatives.

Gray and Lamport's "Consensus on Transaction Commit" — the paper that frames non-blocking atomic commit as a consensus problem and shows how a quorum removes the single-coordinator dependency.

The companion "a saga compensates the completed steps in reverse" and "require a quorum before trusting a vote" modules — the saga is the isolation-for-liveness trade that avoids the prepare window, and quorum is the mechanism that replaces the lone coordinator.
