---
id: fencing-inter-01
title: Give the lock a fencing token and let storage reject stale ones — a lock alone cannot stop a paused client's late write
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: A distributed lock is supposed to guarantee that only one client at a time writes to a shared resource, and by itself it does not, because a lock is held under a lease — a time-limited grant — and a client can lose the lease without knowing. The classic failure: client A holds the lock, suffers a long stall (a stop-the-world GC pause, a scheduling delay, a partition) that outlasts the lease, the lock service grants the lock to client B who does its work, then A resumes believing no time has passed and performs the write it was about to do. Two clients have now written believing they had exclusive access, and A's write can corrupt B's. The lock did its job at every instant; the stall broke mutual exclusion, and no self-checking by A can help because A cannot know it was paused. A fencing token fixes this at the resource: every lock grant issues a strictly increasing token (A gets 33, B gets 34), the client includes it with every write, and the storage remembers the highest token it accepted and refuses any write not strictly greater — so once B's token-34 write lands, A's later token-33 write is rejected. On a fixture where writes reach storage as A(33)="x", B(34)="y", A(33)="z", the unfenced storage accepts all and ends at "z" (A's stale write corrupted B's), while the fenced storage rejects the second 33 and ends at "y".
eli5: A key to a shared room only works if you actually have the key when you go in — but imagine you froze in time holding the key, someone else was given a new key and used the room, and then you unfroze and walked in as if the room were still yours. A plain lock can't catch this, because you never noticed you froze. The fix: every key is numbered higher than the last, and the room's door checks the number — once it has seen key #34, it refuses key #33. So your stale, lower-numbered key is turned away at the door even though you still think it's valid.
---

## Why this module

Reaching for a distributed lock feels like it settles the question of who may write. It does not, because the lock is leased and a client can be paused past its lease without noticing — and then two clients each believe they hold exclusive access. The dangerous part is that the lock is behaving correctly the whole time; the safety hole is that the client cannot detect its own stall, so the protection has to live somewhere the client's confusion cannot reach.

A distributed lock is supposed to guarantee that only one client at a time may write to a shared resource. It does not, by itself, deliver that guarantee, because a lock is held under a lease — a time-limited grant — and a client can lose the lease without knowing it. The classic way: client A holds the lock, then suffers a long stall (a stop-the-world garbage-collection pause, a scheduling delay, a network partition) that outlasts the lease. The lock service, seeing the lease expire, grants the lock to client B, who does its work. Then A resumes — from A's own point of view no time has passed and it still holds the lock — and performs the write it was about to do. Now two clients have written to the resource believing they had exclusive access, and A's write, based on a lease it no longer holds, can corrupt or overwrite B's. The lock did its job at every instant; the stall is what broke mutual exclusion, and no amount of lock-checking by A can help, because A cannot know it was paused.

A fencing token fixes this at the *resource*, not the client. Every time the lock is granted, the lock service issues a token that strictly increases — A gets 33, B gets 34 — and the client must include its token with every write. The storage service remembers the highest token it has accepted and refuses any write whose token is not greater. So once B's token-34 write lands, the storage's high-water mark is 34, and A's later write carrying the stale token 33 is rejected — the resource itself enforces the ordering the lease intended. The client cannot be trusted to notice its own stall, but the resource can be trusted to reject an out-of-date token. This module runs the writes with and without fencing.

**A leased distributed lock cannot stop a stalled holder from writing after its lease expired, so the lock must issue monotonically increasing tokens and the protected resource must reject any write whose token is not greater than the last it accepted — fencing out the stale writer at the resource, where the client's own confusion cannot reach.**

## Concepts

**Unfenced storage** accepts every write in arrival order — it has no way to tell a current writer from a stalled one that woke up late, so the last write always wins.

```python filename=modules/orchestration-and-governance/code/fencing-inter-01/fencing.py:49-56 COMPLETE
def run_unfenced(attempts):
    """No token check: storage accepts every write in order; the last write wins."""
    value = None
    log = []
    for a in attempts:
        value = a["value"]
        log.append((a["client"], a["token"], "accept", value))
    return value, log
```

**Fenced storage** tracks the highest token it has accepted and rejects any write not strictly greater — the check that turns away a stale writer.

```python filename=modules/orchestration-and-governance/code/fencing-inter-01/fencing.py:59-71 COMPLETE
def run_fenced(attempts):
    """Storage tracks the highest accepted token and rejects any write not strictly greater."""
    high_water = 0
    value = None
    log = []
    for a in attempts:
        if a["token"] > high_water:
            high_water = a["token"]
            value = a["value"]
            log.append((a["client"], a["token"], "accept", value))
        else:
            log.append((a["client"], a["token"], "REJECT (stale)", value))
    return value, log
```

<svg role="img" aria-label="A timeline: client A holds the lock with token 33, then pauses; the lease expires and client B gets token 34 and writes; A wakes and writes with the stale token 33" viewBox="0 0 300 118" width="300" height="118">
  <text x="6" y="12" fill="var(--muted)" font-size="8">A stalls past its lease; B takes over; A wakes with a stale token</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">A</text>
  <line x1="30" y1="30" x2="70" y2="30" stroke="var(--s1)"/><text x="30" y="26" fill="var(--muted)" font-size="6">lock, token 33</text>
  <line x1="70" y1="30" x2="200" y2="30" stroke="var(--s1)" stroke-dasharray="2 2"/><text x="100" y="26" fill="var(--muted)" font-size="6">GC pause (lease expires)</text>
  <circle cx="230" cy="30" r="3" fill="var(--s2)"/><text x="210" y="24" fill="var(--muted)" font-size="6">A writes 'z' (token 33!)</text>
  <text x="10" y="68" fill="var(--muted)" font-size="7">B</text>
  <line x1="120" y1="64" x2="180" y2="64" stroke="var(--s1)"/><text x="120" y="60" fill="var(--muted)" font-size="6">lock, token 34</text>
  <circle cx="160" cy="64" r="3" fill="var(--s2)"/><text x="150" y="80" fill="var(--muted)" font-size="6">B writes 'y'</text>
  <line x1="90" y1="94" x2="90" y2="20" stroke="var(--line)" stroke-dasharray="1 2"/><text x="72" y="106" fill="var(--muted)" font-size="6">lease line</text>
  <text x="10" y="112" fill="var(--muted)" font-size="7">both A and B believe they hold the lock — fencing rejects A's token 33 at storage</text>
</svg>
^ A holds the lock (token 33) but stalls past its lease; B is granted the lock (token 34) and writes; A wakes still believing it holds the lock and writes with the stale token 33 — a lock alone permits this overlap, and only a token check at the resource stops it.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/fencing-inter-01/fencing.py

The fixture is the three writes reaching storage in order.

```json filename=modules/orchestration-and-governance/code/fencing-inter-01/fencing.json:3-7 COMPLETE
  "attempts": [
    {"client": "A", "token": 33, "value": "x"},
    {"client": "B", "token": 34, "value": "y"},
    {"client": "A", "token": 33, "value": "z"}
  ]
```

Run `--writes`.

```text filename=--writes
WRITES — the stalled client A's late token-33 write, with and without fencing
------------------------------------------------------------------
  order of writes reaching storage: [('A', 33, 'x'), ('B', 34, 'y'), ('A', 33, 'z')]
------------------------------------------------------------------
  UNFENCED:
    A token 33 -> accept         (value now 'x')
    B token 34 -> accept         (value now 'y')
    A token 33 -> accept         (value now 'z')
  final value = 'z'  <- A's stale write corrupted B's
  FENCED:
    A token 33 -> accept         (value now 'x')
    B token 34 -> accept         (value now 'y')
    A token 33 -> REJECT (stale) (value now 'y')
  final value = 'y'  <- the stale token 33 was rejected
```

Read the two runs. Unfenced, storage accepts all three writes: A's 'x', then B's 'y', then A's stale 'z', so the final value is 'z' — A, which lost its lease during the GC pause, overwrote B's legitimate work, and the resource had no way to know. This is the silent corruption a lock is supposed to prevent and does not. Fenced, the first two writes are accepted (tokens 33 then 34 each raise the high-water mark), but A's third write carries token 33, which is not greater than the current high-water mark of 34, so storage rejects it and the value stays 'y'. The difference is one comparison at the resource: `token > high_water`. That comparison encodes the fact that B's grant (34) came after A's (33), so any write still carrying 33 is provably from before B took over and must be stale. The client could not detect its own stall, but the token makes the staleness visible to the resource, which can.

## Build

The token works because it only ever moves forward, so a stale token can never sneak back in. Run `--tokens`.

```text filename=--tokens
TOKENS — the storage high-water mark only moves forward
----------------------------------------------------------
  attempt      token   high-water before   decision
  A writes 'x'  33      0                   accept (raises HW)
  B writes 'y'  34      33                  accept (raises HW)
  A writes 'z'  33      34                  reject (<= HW)
----------------------------------------------------------
  once the high-water mark reaches 34, no token <= 34 is ever accepted again.
```

The high-water mark is monotonic: it starts at 0, rises to 33 when A's first write is accepted, rises to 34 when B's write is accepted, and then never decreases. So the moment token 34 has been honored, every token less than or equal to 34 is permanently refused — the past cannot be replayed. This is why the lock service must issue *strictly increasing* tokens: the ordering of the tokens mirrors the ordering of the lock grants, so a higher token always means "granted more recently," and the resource's "reject anything not greater" rule is exactly "reject anything from an older grant." If the tokens did not increase (say the lock reused numbers, or issued them out of order), the resource could not distinguish a stale writer from a current one, and the guarantee would collapse. The token is a version number for the right to write, and storage enforces it like an optimistic-concurrency check.

<svg role="img" aria-label="A staircase of the high-water mark: 0, then up to 33 on A's write, then up to 34 on B's write, then flat when A's stale token 33 is rejected" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">high-water mark: only ever steps up, never accepts a lower token again</text>
  <line x1="30" y1="90" x2="290" y2="90" stroke="var(--grid)"/>
  <line x1="30" y1="90" x2="30" y2="24" stroke="var(--grid)"/>
  <text x="8" y="92" fill="var(--muted)" font-size="6">0</text>
  <text x="6" y="60" fill="var(--muted)" font-size="6">33</text>
  <text x="6" y="46" fill="var(--muted)" font-size="6">34</text>
  <line x1="30" y1="90" x2="110" y2="90" stroke="var(--s1)"/>
  <line x1="110" y1="90" x2="110" y2="58" stroke="var(--s1)" stroke-dasharray="1 2"/>
  <line x1="110" y1="58" x2="180" y2="58" stroke="var(--s1)"/><text x="120" y="54" fill="var(--muted)" font-size="6">A token 33 accepted</text>
  <line x1="180" y1="58" x2="180" y2="44" stroke="var(--s1)" stroke-dasharray="1 2"/>
  <line x1="180" y1="44" x2="270" y2="44" stroke="var(--s1)"/><text x="190" y="40" fill="var(--muted)" font-size="6">B token 34 accepted</text>
  <circle cx="250" cy="58" r="3" fill="var(--s2)"/><text x="196" y="72" fill="var(--muted)" font-size="6">A's stale token 33 → rejected (below the mark)</text>
</svg>
^ The high-water mark steps from 0 to 33 to 34 and then holds — A's late token-33 write lands below the current mark of 34, so the staircase never steps back down and the stale write is refused.

```python filename=modules/orchestration-and-governance/code/fencing-inter-01/fencing.py:127-131 COMPLETE
    tokens_monotonic = attempts[1]["token"] > attempts[0]["token"]
    print("  the fencing tokens increase on each grant = %s (%d < %d)" % (tokens_monotonic, attempts[0]["token"], attempts[1]["token"]))

    outcomes_differ = uv != fv
    print("  fencing changes the outcome (lock alone was unsafe) = %s (%r vs %r)" % (outcomes_differ, uv, fv))
```

<svg role="img" aria-label="Two final values: unfenced ends at z, the stale corrupt write, fenced ends at y, the correct write" viewBox="0 0 300 92" width="300" height="92">
  <text x="6" y="12" fill="var(--muted)" font-size="8">same writes, opposite outcomes</text>
  <text x="10" y="38" fill="var(--muted)" font-size="7">unfenced</text>
  <rect x="80" y="26" width="80" height="18" fill="var(--s2)"/><text x="108" y="39" fill="var(--panel)" font-size="8">'z'</text>
  <text x="170" y="39" fill="var(--muted)" font-size="7">stale write wins — corrupt</text>
  <text x="10" y="70" fill="var(--muted)" font-size="7">fenced</text>
  <rect x="80" y="58" width="80" height="18" fill="var(--s1)"/><text x="108" y="71" fill="var(--panel)" font-size="8">'y'</text>
  <text x="170" y="71" fill="var(--muted)" font-size="7">stale token rejected — correct</text>
</svg>
^ The identical sequence of writes ends at 'z' (A's stale write) without fencing and at 'y' (B's legitimate write) with it — the token check at the resource is the whole difference between corruption and correctness.

## Definition of done

The self-test pins the unfenced corruption, the fenced rejection, and the corrected outcome.

```python filename=modules/orchestration-and-governance/code/fencing-inter-01/fencing.py:117-125 COMPLETE
    unfenced_accepts_stale = uv == attempts[-1]["value"]
    print("  unfenced: A's stale last write wins = %s (final %r)" % (unfenced_accepts_stale, uv))

    stale = attempts[-1]
    stale_rejected = any(res.startswith("REJECT") and c == stale["client"] and t == stale["token"] for c, t, res, v in flog)
    print("  fenced: the stale token-%d write is rejected = %s" % (stale["token"], stale_rejected))

    fenced_correct = fv == attempts[1]["value"]
    print("  fenced: the final value is B's write = %s (%r)" % (fenced_correct, fv))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — without fencing the stale write wins; with fencing the stale token is rejected and the correct value stands
--------------------------------------------------------------------------------------------------------------------------
  unfenced: A's stale last write wins = True (final 'z')
  fenced: the stale token-33 write is rejected = True
  fenced: the final value is B's write = True ('y')
  the fencing tokens increase on each grant = True (33 < 34)
  fencing changes the outcome (lock alone was unsafe) = True ('z' vs 'y')
```

**Done means the lock's insufficiency and the token's fix are proven on real writes: unfenced storage accepts the stalled A's stale token-33 write and ends at 'z' (corrupting B's 'y'), while fenced storage rejects that write because 33 is not greater than the high-water mark of 34 and ends at 'y' — so mutual exclusion requires monotonically increasing tokens checked at the resource, not a lock alone.**

## Boss fight

Predict two things the fencing token needs to actually be safe, because the token only helps if it is issued correctly and the resource actually enforces it.

The first trap is that the resource *must* check the token, and many resources cannot or do not — which is the real reason distributed locking is so error-prone. Fencing only works if the protected service (the database, the object store, the file server) is fencing-aware: it must store the high-water token and reject stale writes atomically with the write itself. If the resource is a plain filesystem, a legacy service, or an API with no version/precondition support, there is nowhere to put the token check, and the lock provides no safety against a stalled writer at all — you either need conditional writes (compare-and-swap on a version, an if-match precondition, a conditional put), or you accept that the lock is only advisory. This is why "use a distributed lock" is not a complete answer: the safety lives in the resource's ability to reject stale tokens, so you must design the write path around a fencing check, not just acquire a lock and trust it. Idempotent, versioned writes (the token is essentially a version) are what make the whole scheme work, connecting fencing to optimistic concurrency control and to the idempotency-key module.

The second trap is that the token must come from a correct, monotonic source, and the lock service that issues it is itself a distributed system that can fail. The tokens must be strictly increasing across *all* grants globally, which requires the lock service to have consensus on the counter — if two nodes of a partitioned lock service both hand out token 34, fencing breaks, so the token generator needs a single source of truth (a consensus system like ZooKeeper/etcd, whose zxid or version serves as the fencing token, or a database sequence). And the lease/timeout tuning still matters even with fencing: fencing prevents *corruption* from a stalled writer, but a too-short lease that expires during normal operation causes unnecessary failovers and rejected writes (a liveness problem), while a too-long lease delays legitimate takeover after a real failure — fencing makes the system *safe* under bad timing but does not make the timing choices go away. And clocks are not to be trusted for any of this: the lease expiry is best treated as a logical event (the lock service decides the lease lapsed and issues a new token) rather than each client trusting its own clock, because clock skew and pauses are exactly the failures fencing exists to survive. So a correct design is: a consensus-backed lock service issuing monotonic tokens, a fencing-aware resource that rejects stale ones with an atomic conditional write, and leases tuned for liveness on top of that safety floor.

**Fencing is safe only if the protected resource actually rejects stale tokens with an atomic conditional/versioned write (many resources cannot, so the lock is merely advisory), and only if the tokens come from a consensus-backed source that guarantees a single, globally monotonic sequence — with lease timeouts tuned for liveness on top, and clocks distrusted throughout, because a stalled writer with a valid-looking lease is exactly the failure the whole scheme exists to survive.**

## External resources

Martin Kleppmann's "How to do distributed locking" and "Designing Data-Intensive Applications" — the fencing-token pattern, why a leased lock alone is unsafe under process pauses, and why the resource must reject stale tokens.

Documentation for ZooKeeper, etcd, and Redis distributed locks (and the Redlock debate) — how a consensus-backed lock service issues monotonic tokens (zxid/version) and why the protected resource needs conditional writes to enforce them.

The companion idempotency and quorum modules in this topic — a fencing token is a version the resource checks like an idempotency key or an optimistic-concurrency check, and the lock service that issues monotonic tokens needs the same consensus/quorum machinery those modules rely on.
