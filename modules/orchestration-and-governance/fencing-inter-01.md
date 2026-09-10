---
id: fencing-inter-01
title: Fence distributed-lock writes with a monotonic token storage checks — a lease-based lock cannot stop a paused holder from waking and clobbering data
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: A distributed lock with a lease has a gap that the lock alone cannot close. A client acquires the lock, then stalls — a long garbage-collection pause, a network partition, a descheduled process — for longer than the lease. The lease expires; a second client legitimately acquires the lock and does its work; then the first client wakes up, still believing it holds the lock, and issues the write it was about to make. That write is stale, but the client does not know the world moved on while it was frozen. If storage accepts it, it overwrites the second client's work and the lock protected nothing. You cannot fix this by having the client re-check the lock before writing, because it can pass the check, stall, and then write, with the loss of the lock happening in the gap between check and write — the two are not atomic across a pause. The protection must live at storage, the one party that sees writes actually land. The fix is a fencing token: the lock service hands out a strictly increasing number with each acquisition (A gets 1, B gets 2), every client attaches its token to every write, and storage remembers the highest token it has accepted and rejects any write whose token is not strictly greater. The paused client's write carries its old, smaller token, so storage rejects it — the fence holds even though the client still thinks it owns the lock, because the token, not the client's belief, is what storage trusts. On a fixture where writes arrive as A(token 1), B(token 2), then A again with its stale token 1, no fencing applies all three and ends on the corrupt 'a-stale', while fencing rejects the stale token-1 write and ends on the legitimate 'b2'.
eli5: Imagine a shared whiteboard that only one person may write on at a time, and you get a numbered ticket each time it's your turn. You take ticket 1, start writing, but then you freeze for a long time. While you're frozen your turn runs out, the next person takes ticket 2, and they write their answer. Then you unfreeze — you don't realize your turn ended — and you go to write your old answer over theirs. The trick that saves the board: it remembers the highest ticket number it has seen, and it only accepts writing from a higher ticket. You show up with ticket 1, but the board has already seen ticket 2, so it says "no, that ticket is old" and refuses you. Your stale answer never lands, even though you still thought it was your turn.
---

## Why this module

A distributed lock feels like it should be airtight: one holder at a time, everyone else waits. The gap opens because locks in a distributed system have leases — a timeout after which the lock is presumed abandoned, because the holder might have crashed and there is no other way to reclaim it. The lease is necessary (without it a crashed holder freezes the resource forever) and it is also the hole: a holder that has not crashed but merely paused will have its lease expire out from under it, and it has no idea.

Picture the sequence. Client A takes the lock and begins its operation. Mid-operation, A's process suffers a multi-second garbage-collection pause — or is descheduled, or partitioned from the network. The lease expires. Client B, seeing the lock free, acquires it and completes its own write. Then A's pause ends. A resumes exactly where it left off, still holding what it believes is a valid lock, and issues its write. Nothing in A's code is wrong; A simply never learned that time passed and the lock changed hands.

The instinct is to have A re-check the lock right before writing. It does not help: A can check, see it still holds the lock, then stall, then write — and the lease can expire inside that gap. Check-then-write is not atomic across an arbitrary pause. This module shows the failure and the one fix that actually closes it: a token, checked at storage.

**A lease-based lock cannot stop a paused holder from waking and issuing a stale write, because the loss of the lock happens where the client cannot see it — only a monotonic fencing token, checked at the storage that sees writes land, can reject the stale write.**

## Concepts

The fixture is the sequence of writes as they arrive at storage. A acquires the lock (token 1) and writes; A pauses and the lease expires; B acquires (token 2) and writes; A resumes and writes again, still carrying its old token 1.

```json filename=modules/orchestration-and-governance/code/fencing-inter-01/fencing.json:3-7 COMPLETE
  "writes": [
    {"client": "A", "token": 1, "value": "a1"},
    {"client": "B", "token": 2, "value": "b2"},
    {"client": "A", "token": 1, "value": "a-stale"}
  ]
```

Without fencing, storage is a plain last-writer-wins store: it accepts every write in arrival order and keeps the last value. The token is carried but never consulted.

```python filename=modules/orchestration-and-governance/code/fencing-inter-01/fencing.py:32-38 COMPLETE
def apply_no_fencing(writes):
    """Storage accepts every write in arrival order -- a lock with no fencing."""
    stored, log = None, []
    for w in writes:
        stored = w["value"]
        log.append((w, "accept", stored))
    return stored, log
```

With fencing, storage keeps the highest token it has ever accepted and rejects any write whose token is not strictly greater. This is the entire mechanism — one remembered number and one comparison.

```python filename=modules/orchestration-and-governance/code/fencing-inter-01/fencing.py:41-50 COMPLETE
def apply_fencing(writes):
    """Storage rejects any write whose token is not strictly greater than the highest accepted."""
    stored, highest, log = None, 0, []
    for w in writes:
        if w["token"] > highest:
            highest, stored = w["token"], w["value"]
            log.append((w, "accept", stored))
        else:
            log.append((w, "reject (stale token)", stored))
    return stored, log
```

The difference is whether storage trusts the arrival order or the token. The stale write arrives last, so last-writer-wins keeps it; the token says otherwise.

<svg role="img" aria-label="A timeline: client A holds the lock then pauses, the lease expires, client B acquires and writes, then A resumes and writes stale; fencing rejects A's late write because its token 1 is below B's token 2" viewBox="0 0 320 150">
  <text x="10" y="14" font-size="8" fill="var(--muted)">time →</text>
  <line x1="20" y1="40" x2="300" y2="40" stroke="var(--s1)" stroke-width="1"/>
  <text x="10" y="34" font-size="7.5" fill="var(--s1)">A</text>
  <rect x="24" y="34" width="40" height="12" fill="var(--s1)"/><text x="26" y="43" font-size="6.5" fill="var(--panel)">acq t1</text>
  <line x1="64" y1="40" x2="230" y2="40" stroke="var(--s1)" stroke-width="1" stroke-dasharray="2 2"/>
  <text x="120" y="36" font-size="6.5" fill="var(--muted)">paused (lease expires)</text>
  <rect x="230" y="34" width="46" height="12" fill="var(--s1)"/><text x="232" y="43" font-size="6.5" fill="var(--panel)">write t1</text>
  <line x1="20" y1="80" x2="300" y2="80" stroke="var(--s2)" stroke-width="1"/>
  <text x="10" y="74" font-size="7.5" fill="var(--s2)">B</text>
  <rect x="120" y="74" width="40" height="12" fill="var(--s2)"/><text x="122" y="83" font-size="6.5" fill="var(--panel)">acq t2</text>
  <rect x="164" y="74" width="46" height="12" fill="var(--s2)"/><text x="166" y="83" font-size="6.5" fill="var(--panel)">write t2</text>
  <text x="20" y="108" font-size="7.5" fill="var(--ink)">storage sees: t2 then t1 — fencing rejects t1 (1 is not &gt; 2)</text>
  <text x="20" y="128" font-size="7.5" fill="var(--muted)">A's late write carries its OLD token, so the fence catches it</text>
</svg>
^ A acquires token 1 and pauses; its lease expires; B acquires token 2 and writes. A resumes and writes with its stale token 1, arriving after B. Fencing rejects it because 1 is not strictly greater than the 2 storage already accepted — the old token betrays the stale write.

**Without fencing, storage trusts arrival order and keeps the last write; with fencing, storage keeps one number — the highest token accepted — and rejects anything not strictly above it.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the write path of a lock-guarded resource, reduced to three writes so every decision is checkable by hand.

Run `--replay` to see each write and how each policy decides.

```text filename=fencing.py --replay
  client  token  value      no-fencing        fencing
  A       1      a1         accept            accept
  B       2      b2         accept            accept
  A       1      a-stale    accept            reject (stale token)
```

The first two writes are accepted by both policies — A's token 1, then B's token 2, each strictly higher than what came before. The third write is where they part. It carries token 1, but storage under fencing has already accepted token 2, and 1 is not greater than 2, so fencing rejects it while no-fencing accepts it as just another write.

Now `--final` shows what is left in storage.

```text filename=fencing.py --final
  latest legitimate value (highest token) = 'b2'
  no-fencing final                         = 'a-stale'
  fencing final                            = 'b2'
```

The legitimate final value is B's — B held the highest token, so B is the true current lock-holder. No-fencing ends on 'a-stale': A's resurrected write overwrote B's work, exactly the corruption the lock was supposed to prevent. Fencing ends on 'b2': the stale write was rejected and B's value survived. Same three writes, same arrival order — the only difference is whether storage checked the token.

<svg role="img" aria-label="Two storage outcomes: no-fencing ends on a-stale (B's work overwritten), fencing ends on b2 (B's work preserved)" viewBox="0 0 320 110">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">final value in storage (legitimate = 'b2')</text>
  <text x="10" y="42" font-size="8.5" fill="var(--s2)">no-fencing</text>
  <rect x="95" y="32" width="90" height="16" fill="var(--s2)"/><text x="112" y="44" font-size="8" fill="var(--panel)">a-stale</text>
  <text x="192" y="44" font-size="8" fill="var(--ink)">B's work clobbered</text>
  <text x="10" y="72" font-size="8.5" fill="var(--s1)">fencing</text>
  <rect x="95" y="62" width="90" height="16" fill="var(--s1)"/><text x="120" y="74" font-size="8" fill="var(--panel)">b2</text>
  <text x="192" y="74" font-size="8" fill="var(--ink)">B's work preserved</text>
  <text x="10" y="98" font-size="7.5" fill="var(--muted)">same writes, same order — only the token check differs</text>
</svg>
^ No-fencing leaves the stale 'a-stale' in storage, overwriting B; fencing leaves the legitimate 'b2'. The lock was identical in both runs — the token check at storage is what turned corruption into correctness.

**No-fencing ends on the stale write and loses B's legitimate work; fencing rejects the stale token and preserves it — the same lock, saved only by storage checking the token.**

## Build

The self-test first establishes the premise: the write stream really does contain a write arriving with a token no higher than one already seen — a stale write — otherwise there is nothing to catch.

```python filename=modules/orchestration-and-governance/code/fencing-inter-01/fencing.py:94-102 COMPLETE
    seen, stale = 0, []
    for w in writes:
        if w["token"] > seen:
            seen = w["token"]
        else:
            stale.append(w)
    has_stale_write = len(stale) > 0
    print("  a write arrives with a token no higher than one already seen = %s (%s)"
          % (has_stale_write, [(w["client"], w["token"]) for w in stale]))
```

Then the payload clauses: without fencing the final value is not the legitimate one (corruption), fencing rejects exactly the stale writes, and with fencing the final value is the legitimate one (the fix).

```python filename=modules/orchestration-and-governance/code/fencing-inter-01/fencing.py:104-112 COMPLETE
    nofence_corrupted = nf_final != legit
    print("  without fencing the final value is NOT the legitimate one = %s (%r != %r)" % (nofence_corrupted, nf_final, legit))

    rejects = [w for (w, decision, _s) in fn_log if decision.startswith("reject")]
    fencing_rejects_stale = len(rejects) == len(stale) and len(rejects) > 0
    print("  fencing rejects exactly the stale write(s) = %s (%d rejected)" % (fencing_rejects_stale, len(rejects)))

    fencing_final_correct = fn_final == legit
    print("  with fencing the final value IS the legitimate one = %s (%r)" % (fencing_final_correct, fn_final))
```

Running the check confirms every clause.

```text filename=fencing.py --check
  a write arrives with a token no higher than one already seen = True ([('A', 1)])
  without fencing the final value is NOT the legitimate one = True ('a-stale' != 'b2')
  fencing rejects exactly the stale write(s) = True (1 rejected)
  with fencing the final value IS the legitimate one = True ('b2')
  the two policies leave different values in storage = True ('a-stale' vs 'b2')
```

**The check ties the corruption to a stale write that a lock would not catch, and shows fencing rejecting exactly that write and preserving the legitimate value — the premise, the failure, and the fix in one run.**

## Definition of done

Done means the stale write corrupts storage without fencing and is rejected with it, leaving the legitimate value. The "legitimate value" is defined by the highest token, not by arrival order — that is the whole point: the token, issued monotonically by the lock service, is the ground truth of who currently holds the lock, and storage defers to it rather than to whoever wrote last.

Two clarifications sharpen the scope. First, the token must come from the lock service and increase strictly with every acquisition — that is a real constraint on the lock provider, and a common source of tokens is a consensus system's log index or a lease generation number, both naturally monotonic. Second, fencing protects the specific resource whose writes carry and check the token; it does not magically protect side effects the paused client performs elsewhere. If A, while it believes it holds the lock, sends an email or calls an external API that has no notion of the token, fencing cannot un-send that — fencing works only where the downstream service participates by rejecting stale tokens. This is why the durable, correct place to enforce it is the storage or service that actually holds the protected state.

<svg role="img" aria-label="Fencing works only where the downstream checks the token: the token-aware store rejects the stale write, but an external service with no token check accepts the stale side effect" viewBox="0 0 320 120">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">stale write from paused holder reaches two downstreams</text>
  <rect x="20" y="30" width="130" height="34" fill="none" stroke="var(--s1)"/>
  <text x="30" y="44" font-size="7.5" fill="var(--s1)">token-aware storage</text>
  <text x="30" y="57" font-size="7.5" fill="var(--ink)">rejects (1 not &gt; 2)</text>
  <rect x="170" y="30" width="130" height="34" fill="none" stroke="var(--s2)"/>
  <text x="180" y="44" font-size="7.5" fill="var(--s2)">external API, no token</text>
  <text x="180" y="57" font-size="7.5" fill="var(--ink)">accepts stale effect</text>
  <text x="10" y="90" font-size="7.5" fill="var(--muted)">fencing only protects downstreams that check the token</text>
  <text x="10" y="106" font-size="7.5" fill="var(--ink)">put the protected state behind a token-checking service</text>
</svg>
^ The fence holds only where the downstream participates. The token-aware store rejects the stale write; an external service that ignores the token accepts the stale side effect. Fencing is a property of the storage, not of the client.

**Done means fencing rejects the stale write and preserves the highest-token value, with the token — not arrival order — defining who legitimately holds the lock, enforced at the service that holds the protected state.**

## Boss fight

A job scheduler uses a distributed lock so that only one worker processes a given task at a time. Occasionally two workers both mark the same task "done" with conflicting results, and it correlates with worker hosts that had brief CPU or GC pauses. The lock library is well-tested and the lease timeout was even lowered to reduce contention. Why does lowering the lease make it worse, and how would you fix it?

It is the paused-holder gap, and lowering the lease made it more likely, not less. A worker acquires the lock and starts the task; a GC or CPU pause freezes it past the lease; a second worker acquires the lock and finishes the task; the first worker wakes and writes its own conflicting result — two "done" marks for one task. Shortening the lease shrinks exactly the pause needed to expire it, so more of the ordinary GC hiccups now outlast the lease and trigger the race; the lease timeout trades off crash-recovery speed against this window and cannot eliminate it, because the paused worker never observes losing the lock. The fix is fencing. Have the lock service issue a strictly increasing token per acquisition and have the result store record the task result only if the write's token is greater than the highest already recorded for that task. Then when the paused worker wakes and tries to write, its old token is below the second worker's, the store rejects it, and only one result — the current holder's — is ever recorded. A natural token source is the lock service's own monotonic counter or, if the lock is built on a consensus store, its log index or lease generation. Re-checking the lock inside the worker before writing does not fix it, because the pause can fall between the check and the write; the token has to be validated at the store, which is the only place that observes the writes in the order they truly land. Keep a sensible lease for crash recovery, but stop relying on it for correctness — that is the token's job.

## External resources

Martin Kleppmann's "How to do distributed locking" and the fencing-token discussion in Designing Data-Intensive Applications — the canonical treatment of why a lease-based lock is unsafe without a fencing token, with the same paused-client timeline modeled here.

Documentation for lock services and their generation/fencing numbers (ZooKeeper's zxid and ephemeral-node sequence, etcd and Consul lease generations, Chubby) and how to plumb the token through to a token-checking store — the production mechanics of issuing monotonic tokens and rejecting stale writes at the resource.
