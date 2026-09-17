---
id: ryow-inter-01
title: Give a client read-your-writes with a session token — route its reads only to a replica caught up to its last write
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: In an eventually-consistent store a write lands on one replica and spreads to the rest over time, so at any moment the replicas hold different versions of the data. That is fine until a client writes and then immediately reads: if the read is routed to a replica that has not yet received the write, the client gets back a value older than the one it just wrote — it reads its own stale data, and from the client's point of view its update vanished. One fix is to make every read strongly consistent with a quorum (R + W > N), but that is a heavy system-wide hammer that makes every read for every client touch a quorum. Read-your-writes is a per-client property and can be bought per client, far more cheaply, with a session token: when a client writes it remembers the version that write produced, and on each subsequent read the router only considers replicas whose version is at least the client's last-write version, so the client is never served a value older than its own write while other clients keep reading cheaply from any replica. The guarantee is scoped and precise — this client always sees its own writes while the system stays eventually consistent. On a fixture where the client last wrote version 5 and the replicas are at versions 5, 3, and 6, a naive read can land on the version-3 replica and return stale, while a session-pinned read is eligible only for the version-5 and version-6 replicas and never returns stale.
eli5: Imagine you drop off a letter at one post-office window, then walk to another window and ask "did my letter arrive?" The second window hasn't gotten it yet, so the clerk says "no letter here" — and you panic, thinking your letter was lost, even though it's sitting safely at the first window and will be filed everywhere soon. The fix isn't to make every window instantly share everything (slow and expensive for everyone); it's to give you a little claim ticket that says "your letter is number 5." Now when you ask a window, it checks: "have I filed up to number 5 yet?" If not, it sends you to a window that has, so you always see your own letter. Other people who don't care about your letter still get served by any window, fast. The ticket makes just your view consistent, cheaply, without slowing everyone down.
---

## Why this module

Eventual consistency is a deliberate trade: by letting a write acknowledge before it has reached every replica, the system gets low latency and high availability, at the price of replicas being briefly out of sync. For most reads this is invisible and fine — a value that is a few hundred milliseconds stale is usually harmless. The one case where it is not fine is a client reading data it just wrote itself.

That case is special because the client knows what the value should be — it just set it — so staleness is not a small imperfection but a visible contradiction. The user updates their profile and the page reloads showing the old profile; they post a comment and it is not there; they log in and are bounced back to the login screen. The write succeeded and will propagate, but the immediate read hit a replica that had not caught up, and the client experiences its own action as having failed.

The blunt fix is to make all reads quorum reads so every read sees the latest write, but that overpays: it imposes strong consistency on every read for every client when the actual requirement is only that each client see its own writes. This module shows the cheaper, targeted fix — a per-client session token that pins the client's last-write version and routes its reads to a replica that has it — and contrasts it with a naive any-replica read.

**Eventual consistency is fine until a client reads its own recent write and a lagging replica returns the old value; the targeted fix is a per-client session token, not strong consistency on every read.**

## Concepts

The key reframing is that read-your-writes is a session property, not a storage property. The storage can remain eventually consistent; what must hold is a relationship between one client's write and that same client's later reads. Recognizing this scopes the problem down from "make the whole system consistent" to "make this one client's reads consistent with this one client's writes," which is a much cheaper thing to guarantee.

The token is what carries the scope. A write produces a version, and the client keeps that version in its session — a small piece of state that says "I have seen up to version 5." The read then becomes conditional: not "read from any replica" but "read from a replica whose version is at least 5." The token turns a global freshness requirement into a local routing constraint, and routing is cheap compared to coordinating a quorum on every read.

It is worth being precise about what this guarantees and what it does not. It guarantees monotonic, self-consistent reads for the token-holder: the client never moves backward in time relative to its own writes. It does not make the client see other clients' latest writes, and it does not make the system linearizable. It is causal consistency for one session — exactly the guarantee the "my own update vanished" bug requires, and no more. Buying only the guarantee you need is why it is cheaper than the quorum hammer, which buys freshness for everyone on every read whether they needed it or not.

<svg role="img" aria-label="A client writes and receives a version-5 token, then a later read carries that token to a router which sends it only to a replica whose version is at least 5" viewBox="0 0 440 130">
<rect x="20" y="30" width="70" height="28" fill="var(--panel)" stroke="var(--line)"/>
<text x="55" y="48" fill="var(--ink)" font-size="9" text-anchor="middle">client</text>
<line x1="90" y1="44" x2="150" y2="44" stroke="var(--muted)"/>
<text x="120" y="38" fill="var(--muted)" font-size="8" text-anchor="middle">write</text>
<rect x="150" y="30" width="70" height="28" fill="var(--panel)" stroke="var(--s1)"/>
<text x="185" y="48" fill="var(--ink)" font-size="9" text-anchor="middle">token v5</text>
<line x1="55" y1="58" x2="55" y2="90" stroke="var(--muted)"/>
<text x="55" y="104" fill="var(--muted)" font-size="8" text-anchor="middle">read + token</text>
<rect x="150" y="82" width="70" height="28" fill="var(--panel)" stroke="var(--line)"/>
<text x="185" y="100" fill="var(--ink)" font-size="9" text-anchor="middle">router</text>
<line x1="220" y1="96" x2="280" y2="96" stroke="var(--s1)"/>
<text x="250" y="90" fill="var(--s1)" font-size="8" text-anchor="middle">v &gt;= 5</text>
<rect x="280" y="82" width="140" height="28" fill="var(--panel)" stroke="var(--s1)"/>
<text x="350" y="100" fill="var(--ink)" font-size="9" text-anchor="middle">caught-up replica</text>
</svg>
^ The write hands back a version token; the client carries it on reads, and the router uses it to pick only a replica caught up to that version.

**Read-your-writes is a per-session relationship between a client's write and its later reads, so a token that pins the last-write version turns global freshness into a local routing constraint — the exact guarantee needed, and no more.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/ryow-inter-01. The fixture is the client's last-write version and the replicas at their current replication versions.

```json filename=modules/orchestration-and-governance/code/ryow-inter-01/ryow.json:3-5 COMPLETE
  "client_write_version": 5,
  "replicas": [
    {"id": "R1", "version": 5},
```

A replica is stale for this client if it is behind the client's last write.

```python filename=modules/orchestration-and-governance/code/ryow-inter-01/ryow.py:34-36 COMPLETE
def is_stale(replica, cwv):
    """A replica is stale for this client if its version is behind the client's last write."""
    return replica["version"] < cwv
```

A session-pinned read may use only the replicas caught up to that version.

```python filename=modules/orchestration-and-governance/code/ryow-inter-01/ryow.py:39-41 COMPLETE
def session_eligible(replicas, cwv):
    """Replicas a session-pinned read may use: those caught up to the client's last write."""
    return [r for r in replicas if r["version"] >= cwv]
```

Before running it, predict: the version-3 replica (R2) is behind the client's write of 5 and so is stale and ineligible, while R1 (5) and R3 (6) are eligible. Run `--replicas`:

```text filename=ryow.py --replicas
REPLICAS — client last wrote version 5
----------------------------------------------------
  replica   version   stale?   session may use?
  R1        5         False    True
  R2        3         True     False
  R3        6         False    True
----------------------------------------------------
  a session read uses only replicas at or ahead of the client's write
```

The prediction holds. R2 at version 3 is stale for this client and excluded from its reads; R1 and R3, at or ahead of version 5, are eligible. The token has turned the replica set into a filtered set the client may safely read from.

<svg role="img" aria-label="Three replicas at versions 5, 3, and 6 against the client's write line at 5; R2 falls below the line and is excluded, R1 and R3 are at or above and eligible" viewBox="0 0 440 150">
<line x1="40" y1="120" x2="410" y2="120" stroke="var(--line)"/>
<line x1="40" y1="70" x2="410" y2="70" stroke="var(--s2)" stroke-dasharray="4 3"/>
<text x="405" y="64" fill="var(--s2)" font-size="8" text-anchor="end">client wrote v5</text>
<rect x="90" y="70" width="40" height="50" fill="var(--s1)"/>
<text x="110" y="135" fill="var(--ink)" font-size="9" text-anchor="middle">R1 v5</text>
<text x="110" y="64" fill="var(--s1)" font-size="8" text-anchor="middle">eligible</text>
<rect x="210" y="90" width="40" height="30" fill="var(--s2)"/>
<text x="230" y="135" fill="var(--ink)" font-size="9" text-anchor="middle">R2 v3</text>
<text x="230" y="84" fill="var(--s2)" font-size="8" text-anchor="middle">stale — excluded</text>
<rect x="330" y="60" width="40" height="60" fill="var(--s1)"/>
<text x="350" y="135" fill="var(--ink)" font-size="9" text-anchor="middle">R3 v6</text>
<text x="350" y="54" fill="var(--s1)" font-size="8" text-anchor="middle">eligible</text>
</svg>
^ The client's write line at 5 splits the replicas: R2 below it is excluded, R1 and R3 at or above it are eligible.

Now the versions each read strategy could actually return. Run `--reads`:

```text filename=ryow.py --reads
READS — versions each strategy could return (client wrote 5)
------------------------------------------------------
  naive any-replica read could return:  [5, 3, 6]
    of which stale (< 5):              [3]
  session-pinned read could return:     [5, 6]
    of which stale (< 5):              []
```

The naive read could return version 3 — older than the client's own write of 5 — because it is willing to read from any replica. The session-pinned read can only return 5 or 6, never anything below the client's write, so it can never serve the client its own stale data. The bug is possible under naive routing and impossible under the token.

<svg role="img" aria-label="Two sets of returnable versions: naive returns 3, 5, or 6 with 3 marked stale; session returns only 5 or 6, none stale" viewBox="0 0 440 130">
<text x="110" y="22" fill="var(--ink)" font-size="10" text-anchor="middle">naive read may return</text>
<rect x="55" y="34" width="36" height="26" fill="var(--s2)" stroke="var(--line)"/>
<text x="73" y="52" fill="var(--ink)" font-size="9" text-anchor="middle">3</text>
<rect x="95" y="34" width="36" height="26" fill="var(--s1)" stroke="var(--line)"/>
<text x="113" y="52" fill="var(--ink)" font-size="9" text-anchor="middle">5</text>
<rect x="135" y="34" width="36" height="26" fill="var(--s1)" stroke="var(--line)"/>
<text x="153" y="52" fill="var(--ink)" font-size="9" text-anchor="middle">6</text>
<text x="113" y="78" fill="var(--s2)" font-size="9" text-anchor="middle">3 is stale (&lt; 5)</text>
<text x="330" y="22" fill="var(--ink)" font-size="10" text-anchor="middle">session read may return</text>
<rect x="295" y="34" width="36" height="26" fill="var(--s1)" stroke="var(--line)"/>
<text x="313" y="52" fill="var(--ink)" font-size="9" text-anchor="middle">5</text>
<rect x="335" y="34" width="36" height="26" fill="var(--s1)" stroke="var(--line)"/>
<text x="353" y="52" fill="var(--ink)" font-size="9" text-anchor="middle">6</text>
<text x="330" y="78" fill="var(--s1)" font-size="9" text-anchor="middle">none below 5</text>
</svg>
^ The naive read can serve version 3, older than the client's own write; the session read is confined to versions at or above it.

## Build

The self-test plants the failure and names each claim as a boolean flag. It first computes the session-eligible replica set from the client's write version.

```python filename=modules/orchestration-and-governance/code/ryow-inter-01/ryow.py:75-76 COMPLETE
    cwv, reps = data["client_write_version"], data["replicas"]
    eligible = session_eligible(reps, cwv)
```

Then it checks that some replica lags, that a naive read can return a stale value, that every session-eligible replica is at or ahead of the write, that the policy excludes exactly the laggards, and that at least one replica can still serve the read.

```python filename=modules/orchestration-and-governance/code/ryow-inter-01/ryow.py:78-91 COMPLETE
    some_replica_lags = any(is_stale(r, cwv) for r in reps)
    print("  some replica is behind the client's last write = %s" % some_replica_lags)

    naive_can_read_stale = any(r["version"] < cwv for r in reps)
    print("  a naive any-replica read can return a stale value = %s (%s)"
          % (naive_can_read_stale, [r["id"] for r in reps if r["version"] < cwv]))

    session_never_stale = all(r["version"] >= cwv for r in eligible)
    print("  every session-eligible replica is at or ahead of the write = %s" % session_never_stale)

    session_excludes_laggards = all(is_stale(r, cwv) == (r not in eligible) for r in reps)
    print("  the session policy excludes exactly the lagging replicas = %s" % session_excludes_laggards)

    session_has_a_replica = len(eligible) > 0
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the session policy ever admits a stale replica or excludes a fresh one:

```text filename=ryow.py --check
SELF-TEST — a naive read can return the client's own stale data; a session token routes only to caught-up replicas
------------------------------------------------------------------------------------------------------------------------
  some replica is behind the client's last write = True
  a naive any-replica read can return a stale value = True (['R2'])
  every session-eligible replica is at or ahead of the write = True
  the session policy excludes exactly the lagging replicas = True
  at least one replica can serve the session read = True (['R1', 'R3'])
```

**The self-test checks that the eligible set is at or ahead of the write AND non-empty — proving the token both blocks stale reads and still leaves a replica to serve, so the guarantee is not bought by making the read impossible.**

## Definition of done

You can explain why reading your own recent write is the case where staleness becomes a visible contradiction, not a harmless lag.
You can state read-your-writes as a per-session relationship and explain why that makes it cheaper to guarantee than global strong consistency.
You can describe the session-token mechanism — pin the last-write version, route reads to a replica at or ahead of it — and why routing is cheaper than a quorum on every read.
You can say precisely what the token guarantees (the client sees its own writes, monotonically) and what it does not (other clients' latest writes, linearizability).
You can contrast this fix with the quorum (R + W > N) fix and say when each is appropriate.

## Boss fight

Consider what happens when no replica is eligible — suppose every replica is still behind the client's last write because propagation is slow. The eligible set is empty, and the session read has no replica to serve it. The policy now faces a choice it must make deliberately: wait until a replica catches up (favoring consistency, at the cost of latency) or fall back to a stale read (favoring availability, breaking the guarantee). This is the read-your-writes local echo of the CAP trade-off: under a partition or heavy lag, the token cannot both stay consistent and stay available, and the system must pick. A good implementation waits with a timeout, then surfaces the choice rather than silently serving stale data.

Now consider a subtler failure: the client keeps its token but is load-balanced to a fresh replica that then fails, and the retry lands on a laggard. If the retry does not re-apply the token's version constraint, the guarantee is silently broken on exactly the retry path — the place least tested. The lesson generalizes: the token is only as good as the routing that enforces it, so the version check must live at every read path, including retries, failovers, and cache layers, not just the happy path. A session guarantee is an invariant, and an invariant that holds only on the common path is not an invariant.

**When no replica is caught up the token forces a CAP choice — wait or serve stale — which the system must make deliberately; and the version check must be enforced on every read path including retries and failover, or the guarantee breaks silently where it is least tested.**

## External resources

Werner Vogels's "Eventually Consistent" article defines the client-centric session guarantees — read-your-writes, monotonic reads — that this module implements with a token.
Documentation for MongoDB causal consistency (afterClusterTime tokens) and DynamoDB / Cassandra session-style reads shows the last-write-version token carried in a session in production systems.
The topic's own modules on quorum sizing (R + W > N) cover the alternative, system-wide route to freshness that this per-client mechanism is contrasted against.
