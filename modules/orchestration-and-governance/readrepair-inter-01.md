---
id: readrepair-inter-01
title: Write the latest version back to a stale replica during the read — a quorum read alone returns right but leaves it stale
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: A quorum-replicated store keeps N copies of each key and, on a read, contacts a read quorum and returns the newest version it sees; sized correctly (R+W>N) this guarantees the read observes the latest write. But "the read returns the right value" is not the same as "the replicas are consistent." A replica that missed a write — briefly unreachable, or the message dropped — holds a stale version, and a correct quorum read papers over that staleness rather than fixing it: as long as enough fresh replicas are in the quorum, the read returns the latest version and the stale replica is simply outvoted. The stale copy stays stale on the next read, and the next, until something writes the key again or a slow background process reconciles it — and until then the set is divergent, one bad node away from serving old data. Read repair closes this gap using the read traffic you already pay for: when a read finds a replica returned an older version, the coordinator returns the newest to the client and also writes that newest version back to the replicas that were behind, so the read heals the replicas it touched. It does not change what the read returns — a correct quorum read already returns the latest — it changes the state left behind. On a fixture where a write reached A and B (version 2) but C missed it (version 1), a read of A and C returns version 2 both ways, but without repair C stays at version 1 (one stale replica) while with repair C is written up to version 2 during the read (zero stale).
eli5: Imagine three copies of a class handout, and the teacher updates two of them but misses the third, which still has last week's version. When you need the handout you grab any two copies and go with whichever is newer — so you always get the up-to-date one, even if one of the two you grabbed was the old third copy. That works for you, but the old copy is still sitting there wrong, and the next person might grab it. Read repair is the teacher saying: whenever you notice a copy is out of date while you're comparing them, quietly fix it right then — so the copies slowly heal themselves just from people reading them, instead of staying wrong until the next big update.
---

## Why this module

A correctly sized quorum has a comforting property — every read sees the latest write — and a hidden weakness that the property disguises: it makes the right answer come out even when the replicas underneath are inconsistent. Because a read only needs enough fresh copies to outvote the stale ones, a replica that fell behind never has to be right for reads to be right, so nothing about normal quorum reads ever forces it to catch up. The divergence is invisible in the results and permanent in the data, which is exactly the kind of problem that surfaces at the worst time — when the fresh replicas are the ones that fail.

A replica that missed a write holds a stale version, and a correct quorum read papers over that staleness rather than fixing it: as long as enough fresh replicas are in the quorum, the read returns the latest version and the stale replica is simply outvoted. The stale copy stays stale — on the next read, and the next — until something writes the key again or a slow background process reconciles it, and until then the replica set is divergent.

Read repair closes this gap using the read traffic you are already paying for. When a read contacts several replicas and finds some returned an older version than the newest, the coordinator returns the newest version to the client (as always) and also writes that newest version back to the replicas that were behind. The read heals the replicas it touched, so popular keys stay converged almost for free. This module runs a read both with and without repair.

**On a quorum read that contacts a replica holding an older version than the newest observed, write the newest version back to that replica during the read (read repair), because a correct quorum read returns the latest value but leaves a stale replica stale — so the read traffic itself should converge the replicas rather than letting divergence persist until the next write.**

## Concepts

**One read function, one flag:** it always returns the newest version seen; with repair on, it also writes that version back to any contacted replica that was behind.

```python filename=modules/orchestration-and-governance/code/readrepair-inter-01/readrepair.py:53-64 COMPLETE
def do_read(replicas, contacts, repair):
    """Return (returned_version, new_replica_state, repaired). Reads a copy; does not mutate the input."""
    state = dict(replicas)
    seen = {r: state[r] for r in contacts}
    latest = max(seen.values())
    repaired = []
    if repair:
        for r in contacts:
            if state[r] < latest:
                state[r] = latest        # write the newest version back to the behind replica
                repaired.append(r)
    return latest, state, repaired
```

**We measure divergence as the count of replicas behind the newest version anywhere in the set** — the thing read repair drives to zero.

```python filename=modules/orchestration-and-governance/code/readrepair-inter-01/readrepair.py:67-70 COMPLETE
def stale_count(replicas):
    """How many replicas hold a version behind the newest one anywhere in the set."""
    latest = max(replicas.values())
    return sum(1 for v in replicas.values() if v < latest)
```

<svg role="img" aria-label="Three replicas: A and B at version 2, C at version 1; a read contacts A and C, sees A is newer, and read repair writes version 2 back to C" viewBox="0 0 300 116" width="300" height="116">
  <text x="6" y="12" fill="var(--muted)" font-size="8">read contacts A and C; C is behind — repair writes v2 back to C</text>
  <rect x="30" y="26" width="50" height="24" fill="var(--s1)"/><text x="42" y="42" fill="var(--panel)" font-size="8">A v2</text>
  <rect x="125" y="26" width="50" height="24" fill="var(--s1)"/><text x="137" y="42" fill="var(--panel)" font-size="8">B v2</text>
  <rect x="220" y="26" width="50" height="24" fill="var(--s2)"/><text x="232" y="42" fill="var(--panel)" font-size="8">C v1</text>
  <text x="220" y="62" fill="var(--s2)" font-size="6">stale (missed the write)</text>
  <text x="30" y="80" fill="var(--muted)" font-size="7">read → sees A=2, C=1; newest = 2</text>
  <path d="M55 52 L55 92 L245 92 L245 52" fill="none" stroke="var(--s2)" stroke-dasharray="2 2"/>
  <text x="90" y="104" fill="var(--s2)" font-size="7">read repair: write v2 → C  (C becomes v2)</text>
</svg>
^ A read contacts A (version 2) and C (version 1); the coordinator returns 2 and, under read repair, writes 2 back to the behind replica C — so the read both answers correctly and heals C, without touching B, which it did not contact.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/readrepair-inter-01/readrepair.py

The fixture is three replicas — A and B fresh at version 2, C stale at version 1 — and a read that contacts A and C.

```json filename=modules/orchestration-and-governance/code/readrepair-inter-01/readrepair.json:3-4 COMPLETE
  "replicas": {"A": 2, "B": 2, "C": 1},
  "read_contacts": ["A", "C"]
```

Run `--read`.

```text filename=--read
READ — contacting ['A', 'C']; newest version among them is 2
------------------------------------------------------------------
    A returns version 2
    C returns version 1  <- behind
------------------------------------------------------------------
  returned to client: 2 (no-repair) / 2 (read-repair) -- same correct value
  C afterwards: version 1 (no-repair) / version 2 (read-repair, repaired ['C'])
```

Read the two outcomes. The read contacts A and C; A returns version 2 and C returns version 1, so the coordinator sees that 2 is the newest and returns 2 to the client. This is true in both modes — the client gets the correct, latest value whether or not read repair is on, because the fresh replica A was in the quorum and outvoted the stale C. The difference is entirely in the last line: without repair, C is left at version 1, still stale; with repair, the coordinator, having noticed C returned an older version, writes version 2 back to C, so C is now at version 2. The read did not need C to be correct in order to return the right answer — but it used the fact that it had already contacted C, and already knew C was behind, to fix C at essentially no extra cost. The client's experience is identical; the replica set's health is not.

## Build

The consequence shows up when you count how divergent the replica set is before and after the read.

```text filename=--converge
CONVERGE — stale replicas (behind the newest) before and after the read
------------------------------------------------------------
  before read:               {'A': 2, 'B': 2, 'C': 1}  -> 1 stale
  after read, no repair:     {'A': 2, 'B': 2, 'C': 1}  -> 1 stale
  after read, read repair:   {'A': 2, 'B': 2, 'C': 2}  -> 0 stale (repaired ['C'])
```

<svg role="img" aria-label="Stale replica count over successive reads: without repair it stays flat at 1, with read repair it drops to 0 at the first read that contacts the stale replica" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">stale replicas across reads: no-repair stays 1, repair drops to 0</text>
  <line x1="30" y1="74" x2="285" y2="74" stroke="var(--grid)"/>
  <line x1="30" y1="74" x2="30" y2="26" stroke="var(--grid)"/>
  <text x="12" y="40" fill="var(--muted)" font-size="6">1</text><text x="12" y="72" fill="var(--muted)" font-size="6">0</text>
  <polyline points="45,38 105,38 165,38 225,38 275,38" fill="none" stroke="var(--s2)"/>
  <text x="200" y="34" fill="var(--s2)" font-size="6">no-repair: stays 1</text>
  <polyline points="45,38 105,72 165,72 225,72 275,72" fill="none" stroke="var(--s1)"/>
  <circle cx="105" cy="72" r="3" fill="var(--s1)"/><text x="110" y="68" fill="var(--s1)" font-size="6">repair heals at first contact</text>
  <text x="34" y="88" fill="var(--muted)" font-size="6">reads →</text>
</svg>
^ Without repair the stale count never falls — every read reports a value and leaves C at version 1; with read repair the first read that contacts C drops the stale count to 0 and it stays there, the divergence drained by the read itself.

Before the read, one replica (C) is behind. After a no-repair read, one replica is still behind — the read changed nothing about the replicas' state, it only reported a value. After a read-repair read, zero replicas are behind: the read converged the set. This is the whole point stated as a number. A quorum read without repair is stateless with respect to convergence — it can run a million times and C stays stale until a write touches the key or a background anti-entropy sweep gets to it, and every one of those million reads was an opportunity to fix C that was thrown away. Read repair turns each read into a small convergence step, so the more a key is read, the healthier its replicas stay — which is a good match for real workloads, where the hot keys that most need consistency are exactly the ones read often. The divergence does not accumulate silently between writes; it is continuously drained by the reads themselves.

```python filename=modules/orchestration-and-governance/code/readrepair-inter-01/readrepair.py:112-117 COMPLETE
    both_return_latest = nr_v == latest and rr_v == latest
    print("  both modes return the latest version = %s (no-repair %d, repair %d)" % (both_return_latest, nr_v, rr_v))

    norepair_leaves_stale = stale_count(nr_state) == stale_count(replicas) and stale_count(nr_state) > 0
    print("  without repair the stale replica stays stale = %s (%d stale before and after)"
          % (norepair_leaves_stale, stale_count(nr_state)))
```

## Definition of done

The self-test pins the identical returned value, the persistent staleness without repair, and the full heal with it.

```python filename=modules/orchestration-and-governance/code/readrepair-inter-01/readrepair.py:119-126 COMPLETE
    repair_heals = stale_count(rr_state) == 0
    print("  read repair leaves zero stale replicas = %s (%s)" % (repair_heals, rr_state))

    repair_targeted_behind = repaired == ["C"]
    print("  read repair wrote back only to the behind, contacted replica = %s (repaired %s)" % (repair_targeted_behind, repaired))

    convergence_differs = stale_count(nr_state) != stale_count(rr_state)
    print("  the two modes leave the replica set in different states = %s (%d vs %d stale)"
          % (convergence_differs, stale_count(nr_state), stale_count(rr_state)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — both modes return the latest version; only read repair heals the stale replica during the read
------------------------------------------------------------------------------------------------------------
  both modes return the latest version = True (no-repair 2, repair 2)
  without repair the stale replica stays stale = True (1 stale before and after)
  read repair leaves zero stale replicas = True ({'A': 2, 'B': 2, 'C': 2})
  read repair wrote back only to the behind, contacted replica = True (repaired ['C'])
  the two modes leave the replica set in different states = True (1 vs 0 stale)
```

<svg role="img" aria-label="Two outcomes of the same read: both return version 2 to the client, but no-repair leaves one stale replica while read repair leaves zero" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">same returned value (v2); different replica health</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">no repair</text>
  <rect x="90" y="24" width="40" height="14" fill="var(--s1)"/><text x="94" y="35" fill="var(--panel)" font-size="7">returns v2</text>
  <rect x="140" y="24" width="46" height="14" fill="var(--s2)"/><text x="144" y="35" fill="var(--panel)" font-size="7">1 stale</text>
  <text x="192" y="35" fill="var(--muted)" font-size="6">C still v1</text>
  <text x="10" y="62" fill="var(--muted)" font-size="7">read repair</text>
  <rect x="90" y="52" width="40" height="14" fill="var(--s1)"/><text x="94" y="63" fill="var(--panel)" font-size="7">returns v2</text>
  <rect x="140" y="52" width="46" height="14" fill="none" stroke="var(--s1)"/><text x="144" y="63" fill="var(--s1)" font-size="7">0 stale</text>
  <text x="192" y="63" fill="var(--muted)" font-size="6">C healed to v2</text>
  <text x="10" y="88" fill="var(--muted)" font-size="6">the read that observed the divergence also erased it</text>
</svg>
^ Both reads return version 2 to the client, so the client cannot tell them apart; the difference is behind the scenes — no-repair leaves one stale replica (C still at v1), while read repair leaves none (C healed to v2) using the same read.

**Done means the gap and its fix are proven on real state: a quorum read of A and C returns the latest version 2 in both modes, but the no-repair read leaves C stale (1 stale replica, unchanged), while the read-repair read writes version 2 back to the behind replica C and leaves the set fully converged (0 stale) — so a read that observes a replica behind the newest should repair it during the read.**

## Boss fight

Predict two limits of read repair, because it is opportunistic and it writes during a read, which each carry a catch.

The first trap is that read repair only heals what a read happens to touch, so it is a complement to background anti-entropy, not a replacement. It fixes a stale replica only if that replica is contacted by a read while it is behind — so a hot key read constantly stays converged, but a cold key that is written once and rarely read can keep a stale (or missing) replica indefinitely, because no read ever compares the copies. Worse is the durability angle: if a write landed on only one replica and that replica dies before anyone reads the key, read repair never had a chance to propagate it and the write is simply lost. This is why real systems pair read repair with a scheduled background process — a Merkle-tree anti-entropy sweep or hinted handoff — that walks all keys and reconciles replicas regardless of read traffic, and often with a probabilistic full read repair (occasionally read all replicas, not just a quorum) so that even rarely-read keys get checked. Read repair is the cheap, continuous layer for popular data; the background sweep is the thorough, eventual layer for everything, and you need both because "eventually consistent" is only true if *something* eventually visits every replica.

The second trap is that read repair turns reads into writes, which has correctness and cost consequences that must be handled carefully. A read now issues write-backs, so a read-heavy workload generates extra write traffic to lagging replicas, which can be significant during a repair storm right after a node rejoins with many stale keys — systems throttle or sample read repair to avoid amplifying load exactly when the cluster is already stressed. And "write the newest version back" is only well-defined when versions are totally ordered; with concurrent, conflicting writes (two clients updated the same key on different partitions), there is no single "newest" — comparing a plain counter would pick a winner arbitrarily and *lose* the other update. Correct read repair in that setting must use the same conflict model as the store's writes: reconcile with vector clocks or version vectors, and when it finds genuinely concurrent versions, either surface both (siblings) to the application or apply the store's merge function (a CRDT merge, last-write-wins with care), never silently overwrite one concurrent value with another. So read repair is safe only inside the store's consistency model — it must repair toward the correctly-merged value, not just the numerically largest version, or it becomes a mechanism for quietly dropping writes.

**Read repair is opportunistic, so pair it with background anti-entropy (Merkle sweeps, hinted handoff, occasional full read repair): it only heals replicas a read contacts, so cold keys can stay divergent and a write that reached one soon-dead replica is lost without it. And it turns reads into writes, so throttle the write-back to avoid a repair storm when a stale node rejoins, and repair only within the store's consistency model — reconcile concurrent versions with vector clocks or the store's merge (surfacing siblings or CRDT-merging), never overwrite one concurrent value with another, or read repair silently drops writes it was meant to preserve.**

## External resources

The Dynamo paper and the Cassandra/Riak documentation on read repair — how read repair, hinted handoff, and Merkle-tree anti-entropy combine, the read-repair chance / probabilistic full repair, and the interaction with tunable consistency (R, W, N).

Documentation on version vectors, vector clocks, and CRDTs for conflict resolution — why read repair must reconcile concurrent versions rather than picking the largest counter, and how siblings or merges are surfaced.

The companion quorum, Merkle-reconciliation, and last-write-wins/merge modules in this topic — read repair is the read-time counterpart to background Merkle anti-entropy, sits on top of the quorum sizing that makes reads correct, and must obey the same conflict-merge rules as concurrent writes.
