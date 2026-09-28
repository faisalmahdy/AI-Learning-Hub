---
id: keypart-inter-01
title: Partition a work stream by key, not round-robin, when a key's events must stay in order
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: The obvious way to spread a stream of events across a worker pool is round-robin — event i to worker i mod N — which balances load perfectly and is correct whenever the events are independent. It is wrong the moment two events for the same entity must be applied in order. Consider an account balance and two operations that do not commute: a bonus that adds 100 and a promo that doubles, so bonus-then-double and double-then-bonus give different balances, and the correct answer needs the account's operations applied in sequence order. Round-robin puts the account's first operation on one worker and its second on another; the two workers run concurrently with different backlogs, so the second operation can complete before the first, and the balance is computed in the wrong order — no error is raised, both events ran exactly once, the number is just wrong. On the fixture two accounts each get a bonus (seq 1, cost 3) then a double (seq 2, cost 1) on a base of 50, so each correct balance is (50+100)×2 = 300; round-robin sends every seq-1 op to worker 0 and every seq-2 op to worker 1, the light worker 1 finishes its doubles first, and each account is computed double-then-bonus = (50×2)+100 = 200. The fix is to make the assignment a function of the key: worker = hash(key) mod N, so every event for one account lands on the same worker and is processed sequentially in order, while different accounts still hash to different workers so the pool runs in parallel across keys. Partitioned, both accounts come out 300 and two workers stay busy. The rule: round-robin trades ordering for balance, and any per-key ordering requirement forbids that trade — partition by the key instead.
eli5: Imagine two clerks stamping forms, and a rule that form A's "add a bonus" stamp must go on before its "double it" stamp. If you just hand the next form to whichever clerk is free, the two stamps for form A can land with different clerks, and the faster clerk stamps "double" before the slower one stamps "add" — so the form is doubled first and comes out with the wrong total, even though both stamps happened. Nobody notices, because no stamp was skipped. The fix is to send every form for account A to the same clerk, always: that clerk does A's stamps one after another in the right order. Account B goes to the other clerk, so both clerks still work at once — you just never split one account's forms between them.
---

## Why this module

Parallelism is how a queue keeps up with load: put N workers on the stream and you process N times as fast. The standard way to feed them is round-robin, and it is the right default for most work — independent jobs, no relationship between one event and the next.

The trap is that a lot of real work is not independent. Events carry a key — an account, an order, a document, a user — and events for the same key often have to be applied in the order they arrived. A deposit before a withdrawal. A "created" before an "updated". Round-robin does not know about keys, so it happily sends two events for the same key to two different workers, and two different workers finish at two different times.

**Round-robin optimizes for balanced load and will reorder a key's events to get it; any per-key ordering requirement makes that the wrong default.**

## Concepts

Two operations commute when their order does not change the result: adding 5 then adding 3 is the same as adding 3 then adding 5. Most order bugs hide because the operations happen to commute and the wrong order gives the right answer anyway. The bug shows itself only with operations that do not commute — add then multiply is not multiply then add.

An account balance is full of non-commuting operations. A bonus that adds a fixed amount and a promo that doubles the balance give one answer applied bonus-first and a different answer applied promo-first. So "process this account's events in order" is a real correctness requirement, not a nicety.

Round-robin assignment sends event i to worker i mod N. It looks only at the position in the stream, never at the key, so an account whose two events sit at positions 0 and 1 has them sent to worker 0 and worker 1. Those workers run concurrently. Whichever finishes its copy first applies its operation first, and if that is the later-sequence event, the account is updated out of order. Nothing errors — every event is processed exactly once — the folded result is simply computed in the wrong order.

Partitioned assignment sends event to worker hash(key) mod N. Every event with the same key hashes to the same worker, so all of an account's events land in one worker's queue and are processed sequentially, in arrival order. Ordering per key is preserved by construction. And because different keys hash to different workers, the pool still runs in parallel across keys — you keep the throughput, you just stop splitting a single key.

**Partition-by-key keeps each key on one sequential worker (ordering) while spreading keys across workers (throughput); round-robin gives up the first for the second.**

<svg role="img" aria-label="Two assignment rules. Round-robin maps event index to worker, so account A's two events go to different workers. Partition maps hash of the key to worker, so both of account A's events go to the same worker." viewBox="0 0 520 170">
<rect x="0" y="0" width="520" height="170" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">round-robin: index &#8594; worker</text>
<text x="12" y="44" fill="var(--s1)" font-size="10">A#1 (idx 0)</text>
<text x="12" y="64" fill="var(--s1)" font-size="10">A#2 (idx 1)</text>
<line x1="90" y1="40" x2="170" y2="40" stroke="var(--line)"></line>
<line x1="90" y1="60" x2="170" y2="80" stroke="var(--line)"></line>
<text x="176" y="44" fill="var(--muted)" font-size="10">worker 0</text>
<text x="176" y="84" fill="var(--muted)" font-size="10">worker 1</text>
<text x="230" y="64" fill="var(--s1)" font-size="10">split &#8594; reorder</text>
<text x="12" y="118" fill="var(--ink)" font-size="12">partition: hash(key) &#8594; worker</text>
<text x="12" y="142" fill="var(--s2)" font-size="10">A#1 (key A)</text>
<text x="12" y="162" fill="var(--s2)" font-size="10">A#2 (key A)</text>
<line x1="90" y1="138" x2="170" y2="150" stroke="var(--line)"></line>
<line x1="90" y1="158" x2="170" y2="150" stroke="var(--line)"></line>
<text x="176" y="153" fill="var(--muted)" font-size="10">worker 0</text>
<text x="230" y="153" fill="var(--s2)" font-size="10">together &#8594; in order</text>
</svg>
^ Round-robin keys off the position in the stream, so one account's two events land on different workers; partition keys off the account, so they land on the same worker and stay ordered.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/orchestration-and-governance/code/keypart-inter-01/keypart.py

The fixture is two accounts, each with a bonus then a double, on a base of 50.

```json filename=modules/orchestration-and-governance/code/keypart-inter-01/keypart.json:3-11 COMPLETE
  "base": 50,
  "num_workers": 2,
  "keys": ["acct-A", "acct-D"],
  "events": [
    {"key": "acct-A", "seq": 1, "kind": "add", "by": 100, "cost": 3},
    {"key": "acct-A", "seq": 2, "kind": "double", "cost": 1},
    {"key": "acct-D", "seq": 1, "kind": "add", "by": 100, "cost": 1},
    {"key": "acct-D", "seq": 2, "kind": "double", "cost": 1}
  ]
```

The correct balance for each account is bonus first, then double: (50 + 100) × 2 = 300. Round-robin balances by event index, ignoring the key.

```python filename=modules/orchestration-and-governance/code/keypart-inter-01/keypart.py:31-36 COMPLETE
def round_robin(events, n):
    """Balance by event index: event i goes to worker i mod n, regardless of its key."""
    queues = {w: [] for w in range(n)}
    for i, e in enumerate(events):
        queues[i % n].append(e)
    return queues
```

A worker completes each queued event at its running cumulative cost, and the global apply order is the order events finish.

```python filename=modules/orchestration-and-governance/code/keypart-inter-01/keypart.py:48-57 COMPLETE
def completion_order(queues):
    """Each event completes at its worker's cumulative cost; the global apply order is the order events complete."""
    timed = []
    for w, q in queues.items():
        t = 0
        for pos, e in enumerate(q):
            t += e["cost"]
            timed.append((t, w, pos, e))
    timed.sort(key=lambda x: (x[0], x[1], x[2]))
    return [e for (_t, _w, _pos, e) in timed]
```

Run it and both balances come out wrong.

```text filename=keypart.py --roundrobin
ROUND-ROBIN — balance by event index (i mod 2), ignoring the key
----------------------------------------------------------------
  worker 0 queue: ['acct-A#1 add 100 c3', 'acct-D#1 add 100 c1']
  worker 1 queue: ['acct-A#2 double c1', 'acct-D#2 double c1']
  global apply order: ['acct-A#2', 'acct-D#2', 'acct-A#1', 'acct-D#1']
  acct-A applied in seq order [2, 1]  ->  balance 200   (correct 300)
  acct-D applied in seq order [2, 1]  ->  balance 200   (correct 300)
----------------------------------------------------------------
  a key's ops split across workers; the double finishes first, so the balance is wrong
```

Both seq-1 bonuses landed on worker 0 and both seq-2 doubles on worker 1. Worker 1's doubles are cheap (cost 1) and worker 0's first bonus is expensive (cost 3), so every double completes before its own account's bonus. Each account is folded seq 2 then seq 1 — double then bonus — giving (50 × 2) + 100 = 200 instead of 300.

<svg role="img" aria-label="Round-robin: account A's two events split across worker 0 and worker 1. Worker 1's cheap double finishes at time 1, worker 0's expensive bonus at time 3, so the double is applied before the bonus and the balance comes out 200 instead of 300." viewBox="0 0 520 170">
<rect x="0" y="0" width="520" height="170" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">round-robin scatters acct-A's ops across workers</text>
<text x="12" y="46" fill="var(--muted)" font-size="11">worker 0</text>
<rect x="70" y="34" width="120" height="18" fill="none" stroke="var(--line)"></rect>
<text x="76" y="47" fill="var(--s1)" font-size="10">A#1 bonus (cost 3)</text>
<text x="200" y="47" fill="var(--muted)" font-size="10">done t=3</text>
<text x="12" y="76" fill="var(--muted)" font-size="11">worker 1</text>
<rect x="70" y="64" width="70" height="18" fill="none" stroke="var(--line)"></rect>
<text x="76" y="77" fill="var(--s2)" font-size="10">A#2 double (1)</text>
<text x="200" y="77" fill="var(--muted)" font-size="10">done t=1</text>
<text x="12" y="112" fill="var(--ink)" font-size="11">apply order by finish time: double (t1) &#8594; bonus (t3)</text>
<text x="12" y="136" fill="var(--s1)" font-size="11">50 &#215;2 = 100, +100 = 200   (wrong; correct 300)</text>
</svg>
^ The later event (double, seq 2) sits on the lightly loaded worker and finishes first, so it is applied before the earlier event (bonus, seq 1) — the reorder that corrupts the balance.

Partitioned assignment hashes the key instead.

```python filename=modules/orchestration-and-governance/code/keypart-inter-01/keypart.py:39-45 COMPLETE
def partitioned(events, n):
    """Assign by key: every event for a key goes to worker hash(key) mod n, so one key stays on one worker."""
    queues = {w: [] for w in range(n)}
    for e in events:
        w = int(hashlib.sha256(e["key"].encode()).hexdigest(), 16) % n
        queues[w].append(e)
    return queues
```

```text filename=keypart.py --partition
PARTITION — assign by hash(key) mod 2, so a key stays on one worker
----------------------------------------------------------------
  worker 0 queue: ['acct-A#1 add 100 c3', 'acct-A#2 double c1']
  worker 1 queue: ['acct-D#1 add 100 c1', 'acct-D#2 double c1']
  global apply order: ['acct-D#1', 'acct-D#2', 'acct-A#1', 'acct-A#2']
  acct-A applied in seq order [1, 2]  ->  balance 300   (correct 300)
  acct-D applied in seq order [1, 2]  ->  balance 300   (correct 300)
----------------------------------------------------------------
  each key's ops stay on one worker in sequence order, so every balance is correct
```

acct-A hashes to worker 0 and acct-D to worker 1, so each account's bonus and double sit together on one worker, processed in queue order — seq 1 then seq 2. Both balances are 300, and both workers are busy, one account each. The reorder is gone because no account was ever split.

## Build

<svg role="img" aria-label="A bar comparison of the final balance for each account: round-robin gives 200 for both accounts, partition gives the correct 300 for both, against a correct line at 300." viewBox="0 0 460 180">
<rect x="0" y="0" width="460" height="180" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">final balance per account (correct = 300)</text>
<line x1="60" y1="40" x2="440" y2="40" stroke="var(--grid)" stroke-dasharray="3 3"></line>
<text x="444" y="43" fill="var(--muted)" font-size="9">300</text>
<line x1="60" y1="150" x2="440" y2="150" stroke="var(--line)"></line>
<rect x="90" y="77" width="40" height="73" fill="var(--s1)"></rect>
<text x="86" y="166" fill="var(--muted)" font-size="9">RR A</text>
<text x="94" y="72" fill="var(--s1)" font-size="9">200</text>
<rect x="150" y="77" width="40" height="73" fill="var(--s1)"></rect>
<text x="146" y="166" fill="var(--muted)" font-size="9">RR D</text>
<text x="154" y="72" fill="var(--s1)" font-size="9">200</text>
<rect x="290" y="40" width="40" height="110" fill="var(--s2)"></rect>
<text x="282" y="166" fill="var(--muted)" font-size="9">part A</text>
<text x="294" y="35" fill="var(--s2)" font-size="9">300</text>
<rect x="350" y="40" width="40" height="110" fill="var(--s2)"></rect>
<text x="342" y="166" fill="var(--muted)" font-size="9">part D</text>
<text x="354" y="35" fill="var(--s2)" font-size="9">300</text>
</svg>
^ Round-robin lands both accounts at 200 (double-then-bonus); partition lands both at the correct 300 (bonus-then-double), and no event was dropped in either case.

The self-test asserts the whole contrast: round-robin reorders a key and gets a balance wrong, while partition keeps every key in order, gets every balance right, and still uses more than one worker.

```python filename=modules/orchestration-and-governance/code/keypart-inter-01/keypart.py:148-153 COMPLETE
    pt_in_order = all(applied_seqs(pt_order, k) == sorted(applied_seqs(pt_order, k)) for k in keys)
    print("  partition applies every key's ops in sequence order = %s" % pt_in_order)
    pt_correct = all(pt_final[k] == correct[k] for k in keys)
    print("  partition gets every balance right = %s (got %s)" % (pt_correct, {k: pt_final[k] for k in keys}))
    pt_parallel = sum(1 for w in pt if pt[w]) > 1
    print("  partition still spreads keys across more than one worker = %s (%d workers busy)" % (pt_parallel, sum(1 for w in pt if pt[w])))
```

```text filename=keypart.py --check
SELF-TEST — round-robin reorders at least one key and gets the balance wrong, while partitioning preserves every key's order, gets every balance right, and still spreads keys across workers
----------------------------------------------------------------------------------------------------------------
  round-robin applies some key's ops out of sequence order = True
  round-robin gets some balance wrong = True (got {'acct-A': 200, 'acct-D': 200}, correct {'acct-A': 300, 'acct-D': 300})
  partition applies every key's ops in sequence order = True
  partition gets every balance right = True (got {'acct-A': 300, 'acct-D': 300})
  partition still spreads keys across more than one worker = True (2 workers busy)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  rr_reorders=True  rr_wrong=True  pt_in_order=True  pt_correct=True  pt_parallel=True
```

**pt_parallel is the clause that stops the cheap wrong fix: one worker for everything would also preserve order, but partition keeps every key in order with the pool still busy.**

## Definition of done

You can say why the bug needs non-commuting operations to appear at all: if bonus and double commuted, the reorder would still happen and the balance would still be right, and you would never see it — which is exactly why these bugs survive testing on commutative workloads.

You can trace the round-robin assignment by hand: which worker each event goes to, when each completes given the costs, and why the seq-2 double finishes before the seq-1 bonus.

You can state the partition rule and why it fixes ordering without serializing everything — hash(key) mod N keeps a key on one worker (order) while different keys spread (throughput).

You can name the check that would have caught this in review: assert each key's events are applied in ascending sequence order, not merely that every event was processed.

## Boss fight

Your ledger service consumes an event stream with a pool of 8 workers assigned round-robin, and once in a while an account ends with a balance that is off — always an account that had two events close together in the stream. The on-call fix that keeps getting proposed is "add a sequence check and reprocess out-of-order events."

First: explain why the balances are only sometimes wrong, and why it is always accounts with events close together in the stream. What has to be true about the two events' worker assignment and completion times for the reorder to happen?

Then: repartition by hash(account_id) mod 8. Two questions the repartition raises that round-robin never had to answer — what happens to load balance if one account is far hotter than all the others (a whale), and what happens to an account's in-flight ordering at the instant you change N from 8 to 9 during a scale-up. Name the failure in each case.

Finally: there is a reason you cannot just "reprocess out-of-order events" as the on-call proposes. Given only the corrupted final balance and no per-event log, can you recover the correct balance by reprocessing? State what you would need to have kept to make reprocessing possible, and why partitioning up front is cheaper than reconstructing order after the fact.

## External resources

Kafka's partitioning model is this module in production: a topic is split into partitions, a record's key is hashed to choose its partition, and ordering is guaranteed only within a partition — the documentation's "messages with the same key go to the same partition" is exactly the fix here.

Any actor framework (Akka, Orleans, Erlang) reaches the same place from the other side: one actor per key processes that key's messages sequentially, so per-key order is free and cross-key work is parallel — the mailbox is the per-key queue this module builds by hand.
