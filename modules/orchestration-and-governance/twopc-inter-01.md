---
id: twopc-inter-01
title: Two-phase commit makes a distributed transaction atomic — and blocks when the coordinator dies mid-decision
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: A transaction that touches several independent databases has to be all-or-nothing — a half-committed transaction (money debited from one account, never credited to the other) is corruption — but each database can only commit its own part, and any of them can fail at any moment, so you need a protocol that reaches one agreed outcome across all of them. Two-phase commit (2PC) is the classic answer, and it means understanding exactly one guarantee it provides and one weakness it cannot escape. The protocol has two phases run by a coordinator. In prepare, the coordinator asks every participant "can you commit?"; each does the work up to the final commit and, if it can, votes yes and locks its resources, promising it will be able to commit if told to, else votes no. In commit/abort, the coordinator decides — commit only if every vote was yes, abort if any single vote was no — then broadcasts, and everyone carries it out. That rule is the atomicity guarantee: one no forces everyone to abort, including yes-voters, so participants never diverge. The weakness is the gap between phases: a participant that voted yes has locked its resources and is in doubt, unable to resolve alone (it may not commit — someone might have voted no — and may not abort — the decision might be commit), so if the coordinator crashes after the votes but before the decision, every yes-voter is blocked, holding locks, until the coordinator recovers. On a fixture, all three voting yes commits and one voting no aborts everyone (including the yes-voters A and C), while a coordinator crash after the vote leaves all three yes-voters in doubt and blocked.
eli5: Imagine three friends deciding whether to all chip in for a group gift — it only works if everyone pays, so nobody hands over money until everyone has agreed. First, a organizer goes around and asks each friend "are you in, and do you have your share ready?" Each friend who says yes sets their money aside and waits. If even one friend says no, the whole thing is off and everyone keeps their money. That's the fair, all-or-nothing part. But here's the trap: suppose everyone said yes and set their money aside, and then the organizer — the only one who knows everyone said yes — disappears before telling anyone to actually pay. Now each friend is stuck: they promised to pay and set the money aside, but they don't dare hand it over (maybe someone secretly backed out) and they don't dare take it back (maybe the gift is happening). They're frozen, money tied up, until the organizer comes back.
---

## Why this module

The moment a transaction spans more than one database, "commit" stops being a local act and becomes an agreement problem. Each participant can commit or roll back its own part, but nothing forces them to agree, and a transaction where one participant commits and another rolls back is exactly the corruption transactions exist to prevent. Two-phase commit is the protocol most systems reach for, and it is worth studying not because it is perfect — it is not — but because it teaches the shape of the tradeoff every distributed-agreement mechanism makes: you can have atomicity, and you pay for it with availability under a specific failure.

The atomicity is the easy half to appreciate. A coordinator runs a vote: it asks every participant whether it can commit, and only if the answer is unanimously yes does it tell everyone to commit; a single no aborts the whole transaction. Because the decision is made in one place from all the votes and then applied uniformly, participants never end up in different states. That is the guarantee, and it is real.

The cost is subtler and lives in the gap between voting and deciding. This module runs the vote both ways — unanimous and with one dissent — and then crashes the coordinator at the worst moment to show the blocking.

**Two-phase commit guarantees atomicity — a prepare phase where each participant votes and locks, then a decision that commits only if all voted yes and otherwise aborts, applied uniformly — but it blocks: a participant that has voted yes is in doubt and cannot decide alone, so a coordinator crash after the vote leaves the prepared participants stuck holding locks until it recovers.**

## Concepts

The fixture is a transaction across three participants, A, B, and C, with two vote sets. In `all_prepared` everyone votes yes; in `one_aborts` B votes no while A and C vote yes.

```json filename=modules/orchestration-and-governance/code/twopc-inter-01/twopc.json:3-6 COMPLETE
  "scenarios": {
    "all_prepared": {"votes": {"A": "yes", "B": "yes", "C": "yes"}},
    "one_aborts": {"votes": {"A": "yes", "B": "no", "C": "yes"}}
  }
```

The decision rule is the whole of phase two: commit only if every vote is yes, otherwise abort.

```python filename=modules/orchestration-and-governance/code/twopc-inter-01/twopc.py:32-34 COMPLETE
def decide(votes):
    """Commit only if every participant voted yes; otherwise abort."""
    return "commit" if all(v == "yes" for v in votes.values()) else "abort"
```

The decision is applied uniformly to every participant, and the in-doubt set — the participants stuck if the coordinator crashes after the vote — is exactly the yes-voters, because they locked their resources and promised to commit but have not yet heard the outcome.

```python filename=modules/orchestration-and-governance/code/twopc-inter-01/twopc.py:37-45 COMPLETE
def outcome_per_participant(votes):
    """The decision applied uniformly to every participant."""
    d = decide(votes)
    return {p: d for p in votes}


def in_doubt_on_crash(votes):
    """If the coordinator crashes after votes but before the decision, the yes-voters are in doubt (blocked)."""
    return [p for p, v in votes.items() if v == "yes"]
```

<svg role="img" aria-label="Two-phase commit timeline: coordinator sends prepare to A B C, they vote and lock, coordinator decides commit or abort and broadcasts; a crash marker sits in the gap between vote and decision" viewBox="0 0 320 140">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">phase 1: prepare / vote+lock</text>
  <rect x="14" y="24" width="70" height="18" fill="var(--s1)"/><text x="20" y="37" font-size="8" fill="var(--panel)">coordinator</text>
  <line x1="84" y1="33" x2="140" y2="33" stroke="var(--ink)" stroke-width="1"/><text x="90" y="30" font-size="7" fill="var(--muted)">"can you commit?"</text>
  <rect x="150" y="20" width="26" height="14" fill="var(--s2)"/><text x="158" y="31" font-size="7" fill="var(--panel)">A</text>
  <rect x="150" y="36" width="26" height="14" fill="var(--s2)"/><text x="158" y="47" font-size="7" fill="var(--panel)">B</text>
  <rect x="150" y="52" width="26" height="14" fill="var(--s2)"/><text x="158" y="63" font-size="7" fill="var(--panel)">C</text>
  <text x="182" y="45" font-size="7" fill="var(--muted)">vote yes, lock</text>
  <line x1="120" y1="78" x2="120" y2="110" stroke="var(--s2)" stroke-width="2" stroke-dasharray="3 2"/>
  <text x="124" y="90" font-size="7.5" fill="var(--s2)">coordinator crash here</text>
  <text x="124" y="101" font-size="7.5" fill="var(--s2)">→ A,B,C blocked (in doubt)</text>
  <text x="10" y="128" font-size="8.5" fill="var(--muted)">phase 2: decide (all yes→commit, any no→abort) + broadcast</text>
</svg>
^ The coordinator collects votes in phase one, then decides and broadcasts in phase two. The dashed line is the fatal window: a crash after the votes but before the broadcast leaves every yes-voter locked and waiting, unable to decide for itself.

**The atomicity comes from deciding in one place and applying it uniformly; the blocking comes from the same single point — the participants depend on the coordinator's decision and cannot substitute their own.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the distributed-commit step of a multi-database transaction, reduced to three participants so every vote and outcome is checkable by hand.

Run `--decide` to see both vote sets and the atomic decision.

```text filename=twopc.py --decide
  all_prepared   votes={'A': 'yes', 'B': 'yes', 'C': 'yes'} -> COMMIT
                 per participant: {'A': 'commit', 'B': 'commit', 'C': 'commit'}
  one_aborts     votes={'A': 'yes', 'B': 'no', 'C': 'yes'} -> ABORT
                 per participant: {'A': 'abort', 'B': 'abort', 'C': 'abort'}
  commit requires ALL yes; a single no aborts everyone (atomicity)
```

When all three vote yes, the decision is commit and every participant commits. When B alone votes no, the decision is abort — and crucially, A and C abort too, even though they voted yes and were ready to commit. That is atomicity in action: the single no overrides the two yeses, and the per-participant outcomes are identical, so there is no world where A commits while B rolls back. All-or-nothing, enforced by making one decision from all the votes.

Now `--block` crashes the coordinator at the worst moment.

```text filename=twopc.py --block
  all participants voted: {'A': 'yes', 'B': 'yes', 'C': 'yes'}
  coordinator crashes before broadcasting the decision
  in doubt (voted yes, locked, awaiting decision): ['A', 'B', 'C']
  these 3 participants are BLOCKED -- they cannot commit or abort alone, and hold their locks
```

All three voted yes, locked their resources, and are waiting for the decision — and the coordinator dies before sending it. Now A, B, and C are in doubt: each has promised it can commit, so it cannot abort (the decision might be commit), and it has not been told to commit, so it cannot commit (someone might have voted no). They are frozen, holding their locks, and no participant can break the tie because none of them knows what the others voted or what the coordinator would have decided. They stay blocked until the coordinator recovers and tells them.

<svg role="img" aria-label="A prepared participant stuck between two forbidden doors: cannot commit (someone might have voted no) and cannot abort (the decision might be commit), so it waits" viewBox="0 0 320 120">
  <rect x="120" y="14" width="80" height="24" fill="var(--s2)"/><text x="128" y="30" font-size="8.5" fill="var(--panel)">voted yes, locked</text>
  <line x1="140" y1="38" x2="70" y2="62" stroke="var(--muted)" stroke-width="1"/>
  <line x1="180" y1="38" x2="250" y2="62" stroke="var(--muted)" stroke-width="1"/>
  <rect x="20" y="64" width="110" height="22" fill="none" stroke="var(--line)"/><text x="26" y="79" font-size="7.5" fill="var(--ink)">commit? ✗ maybe a no</text>
  <rect x="190" y="64" width="110" height="22" fill="none" stroke="var(--line)"/><text x="196" y="79" font-size="7.5" fill="var(--ink)">abort? ✗ maybe commit</text>
  <text x="110" y="108" font-size="8.5" fill="var(--s2)">both doors forbidden → wait for the coordinator (blocked)</text>
</svg>
^ An in-doubt participant is trapped between two illegal moves: committing risks disagreeing with a no it did not see, aborting risks disagreeing with a commit decision. The only safe action is to wait — which is the block.

**The same design that guarantees no participant diverges — one decision, applied to all — is what freezes them when the decider vanishes: they cannot proceed without the coordinator, so its crash is their deadlock.**

## Build

The self-test asserts the atomicity guarantee first: unanimous yes commits, any no aborts, the decision is uniform, and the yes-voters are overridden by the single no.

```python filename=modules/orchestration-and-governance/code/twopc-inter-01/twopc.py:80-90 COMPLETE
    all_yes_commits = decide(allp) == "commit"
    print("  unanimous yes -> commit = %s (%s)" % (all_yes_commits, decide(allp)))

    any_no_aborts = decide(onen) == "abort"
    print("  any no -> abort = %s (%s, votes %s)" % (any_no_aborts, decide(onen), onen))

    decision_uniform = len(set(outcome_per_participant(onen).values())) == 1
    print("  the decision is uniform across all participants = %s (%s)" % (decision_uniform, outcome_per_participant(onen)))

    yes_voters_overridden = decide(onen) == "abort" and any(v == "yes" for v in onen.values())
    print("  yes-voters are overridden by the single no (all-or-nothing) = %s (A,C voted yes, still abort)" % yes_voters_overridden)
```

<svg role="img" aria-label="Two vote rows: all yes leads to a uniform commit for A B C; one no leads to a uniform abort for A B C including the yes-voters" viewBox="0 0 320 120">
  <text x="10" y="18" font-size="8.5" fill="var(--muted)">all yes → COMMIT</text>
  <rect x="14" y="26" width="26" height="16" fill="var(--s1)"/><text x="20" y="38" font-size="7" fill="var(--panel)">A✓</text>
  <rect x="42" y="26" width="26" height="16" fill="var(--s1)"/><text x="48" y="38" font-size="7" fill="var(--panel)">B✓</text>
  <rect x="70" y="26" width="26" height="16" fill="var(--s1)"/><text x="76" y="38" font-size="7" fill="var(--panel)">C✓</text>
  <text x="104" y="38" font-size="8" fill="var(--s1)">→ all commit</text>
  <text x="10" y="70" font-size="8.5" fill="var(--muted)">one no → ABORT (uniform)</text>
  <rect x="14" y="78" width="26" height="16" fill="var(--muted)"/><text x="20" y="90" font-size="7" fill="var(--panel)">A✓</text>
  <rect x="42" y="78" width="26" height="16" fill="var(--s2)"/><text x="48" y="90" font-size="7" fill="var(--panel)">B✗</text>
  <rect x="70" y="78" width="26" height="16" fill="var(--muted)"/><text x="76" y="90" font-size="7" fill="var(--panel)">C✓</text>
  <text x="104" y="90" font-size="8" fill="var(--s2)">→ all abort (A,C too)</text>
  <text x="10" y="112" font-size="7.5" fill="var(--muted)">a single no overrides the yeses — the atomicity guarantee</text>
</svg>
^ Unanimous yes commits everyone; a single no aborts everyone, overriding the yes-voters A and C. The outcome is uniform in both rows — participants never split, which is the guarantee 2PC exists to provide.

Running the check confirms the guarantee and the cost.

```text filename=twopc.py --check
  unanimous yes -> commit = True (commit)
  any no -> abort = True (abort, votes {'A': 'yes', 'B': 'no', 'C': 'yes'})
  the decision is uniform across all participants = True ({'A': 'abort', 'B': 'abort', 'C': 'abort'})
  yes-voters are overridden by the single no (all-or-nothing) = True (A,C voted yes, still abort)
  a coordinator crash after the vote leaves participants in doubt = True (['A', 'B', 'C'] blocked)
  every yes-voter is blocked holding locks until the coordinator recovers = True
```

**The check shows both halves at once: the decision is uniform (atomicity holds) and a coordinator crash blocks every yes-voter (availability does not) — the guarantee and its price in the same run.**

## Definition of done

Two properties close it, one for each face of 2PC. The decision must be uniform and driven by unanimity — the atomicity guarantee — and a coordinator crash after the vote must leave the yes-voters blocked — the honest cost. Asserting both keeps the module from selling 2PC as free.

```python filename=modules/orchestration-and-governance/code/twopc-inter-01/twopc.py:92-97 COMPLETE
    doubt = in_doubt_on_crash(allp)
    coordinator_crash_blocks = len(doubt) > 0
    print("  a coordinator crash after the vote leaves participants in doubt = %s (%s blocked)" % (coordinator_crash_blocks, doubt))

    all_yes_voters_blocked = set(doubt) == {p for p, v in allp.items() if v == "yes"}
    print("  every yes-voter is blocked holding locks until the coordinator recovers = %s" % all_yes_voters_blocked)
```

Two clarifications place 2PC in context. First, the blocking is not a bug to patch but a fundamental property: any protocol that guarantees atomic commit with a single coordinator has a window where a coordinator failure blocks the participants — you can shrink the window and speed recovery (a persistent coordinator log so it resumes the decision after restart, timeouts that let participants query each other), but you cannot make a synchronous single-coordinator protocol non-blocking. Three-phase commit (3PC) adds a round to reduce blocking under some failures at the cost of more messages and new failure modes, and consensus protocols like Paxos and Raft sidestep the single-coordinator weakness by replicating the decision across a quorum, so the "coordinator" survives failures — which is why modern systems often layer 2PC over a consensus-replicated coordinator rather than a single one. Second, the locks matter: because yes-voters hold their resources locked while in doubt, a long coordinator outage does not just stall the one transaction, it can stall everything contending for those locked rows, so the blocking window is a real availability and throughput risk, not a theoretical one. The takeaway is not to avoid 2PC but to know what you bought: atomicity, paid for with a blocking window you must minimize.

**Done means the decision is uniform and unanimity-driven (atomic) and a coordinator crash blocks every yes-voter holding locks (the cost) — 2PC's guarantee and its fundamental blocking weakness, both demonstrated, not one hidden.**

## Boss fight

A team uses 2PC to keep an orders database and an inventory database consistent. It works, but once a month the coordinator process restarts during a deploy, and every time it does, a wave of transactions "hangs" — orders stuck, inventory rows locked, customers seeing errors — until an engineer manually intervenes. They ask whether they should abandon 2PC. What is actually happening, and what would you change before giving up the atomicity 2PC provides?

What is happening is the 2PC blocking problem triggered by the coordinator restart: when the coordinator goes down during a deploy, any transaction that has passed the prepare phase — participants voted yes and locked their rows — is in doubt, and those participants cannot commit or abort on their own, so they block, holding locks, and everything contending for those locked rows backs up behind them. It is not that 2PC is broken; it is behaving exactly as designed, and the deploy is hitting the one window where a coordinator failure freezes participants. Before abandoning 2PC (and the atomicity that prevents an order committing without the inventory decrement), make the coordinator recoverable and the outage shorter: give the coordinator a persistent transaction log so that when it restarts it reads its log and resumes broadcasting the pending decisions instead of leaving participants in doubt — this turns a manual rescue into automatic recovery on restart. Add participant timeouts and a status-query path so prepared participants can ask a recovered coordinator (or each other) for the outcome rather than waiting indefinitely. And, most importantly for a monthly deploy, stop treating the coordinator as a single process that dies on deploy: run it on a consensus-replicated (Raft/Paxos) group or a managed transaction manager so a deploy or crash of one node does not take the decider offline at all — the participants' dependence on "the coordinator" is safe when the coordinator is itself fault-tolerant. Only if atomicity is genuinely not required would you drop 2PC for a looser pattern like sagas with compensating actions; if it is required, fix the coordinator's durability and availability rather than the protocol.

## External resources

Gray and Reuter, *Transaction Processing: Concepts and Techniques*, and the standard 2PC treatment in any distributed-systems course — the canonical description of the prepare/commit phases, the atomicity guarantee, and the in-doubt/blocking window modeled here.

Martin Kleppmann, *Designing Data-Intensive Applications*, the chapter on distributed transactions and consensus — why 2PC blocks on coordinator failure, how three-phase commit and consensus-replicated coordinators address it, and when to prefer sagas over distributed transactions.
