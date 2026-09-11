---
id: quorum-inter-01
title: Size the quorums so R + W > N — otherwise a read can contact only replicas that never saw the write, and go stale
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: A replicated store keeps N copies of each key to survive failures. A write need not reach all N; it reaches W of them (the write quorum) and returns. A read need not consult all N; it consults R of them (the read quorum) and returns the newest version it finds. Choosing W and R below N buys availability and low latency, but it puts a correctness condition on the two numbers: a read sees a write only if the read set and the write set share at least one replica — that shared replica carries the new version into the read — and any W-subset and any R-subset of N nodes are guaranteed to intersect exactly when R + W > N (pigeonhole). If R + W ≤ N there is room for a disjoint read and write, so a read can contact only replicas that never received the write and confidently return the old value — intermittent, unreproducible staleness. On a fixture with N = 3, the config W = 1, R = 1 has R + W = 2 (not > 3) and a minimum read/write overlap of 0: writing replica 0 and reading replica 1 returns the stale version 1. The config W = 2, R = 2 has R + W = 4 > 3 and a minimum overlap of 1: writing replicas 0 and 1 then reading replicas 1 and 2 finds version 2 on replica 1, and the enumerated worst-case overlaps match max(0, W + R − N).
eli5: Imagine a class where the teacher's announcement is written on some of the students' notebooks, and later you ask some students what the announcement was. If the teacher wrote it in only one notebook and you ask only one student, you might ask a student who never got it, and hear the old news. But if the teacher writes it in a big enough group and you ask a big enough group, the two groups are guaranteed to share at least one student — and that student tells you the new announcement. The rule for the guarantee is simple: the number written plus the number asked has to be bigger than the whole class. Make the groups too small and you'll sometimes get stale news, seemingly at random.
---

## Why this module

Replicating data for safety creates a new question that a single copy never had: when you read, which copies do you ask, and are you sure one of them has the latest write? Skimp on the quorum sizes to go faster and the answer becomes "not sure" — a read that silently misses a recent write and returns old data, only sometimes, only for some reads, which is the worst way for a storage system to be wrong.

A replicated store keeps N copies of each key so it survives node failures. A write does not have to reach all N copies to be considered done; it reaches W of them (the write quorum) and returns. A read does not have to consult all N either; it consults R of them (the read quorum) and returns the newest version it finds. Choosing W and R smaller than N is what buys availability and low latency — you can write while some replicas are down, and read from whichever are nearby. But it puts a correctness condition on the two numbers, because a read only sees a write if the read set and the write set share at least one replica: that shared replica is the one carrying the new version into the read. If the read set and the write set are disjoint, the read contacts only replicas that never received the write and confidently returns the old value.

The condition for the sets to be guaranteed to overlap is exactly R + W > N. It is pigeonhole: the write touched W of N replicas, the read touches R of N, and if R + W exceeds N the two subsets cannot fit into N slots without colliding. If R + W ≤ N, there is room for a disjoint read and write, and a stale read is possible — not on every read, but on the ones whose read set happens to miss the written replicas, which is precisely the kind of intermittent, unreproducible staleness that is miserable to debug. This is the tuning knob behind eventual versus strong read-your-writes consistency. This module enumerates the overlaps and shows a concrete stale read.

**A replicated read sees the latest write only if the read set overlaps the write set, guaranteed exactly when R + W > N; sizing the quorums below that (R + W ≤ N) leaves room for a disjoint read that contacts only replicas which never received the write, returning stale data intermittently.**

## Concepts

**The minimum overlap** between a write set and a read set is what decides staleness. Computed honestly by enumerating every W-subset against every R-subset, it is 0 when a disjoint pair exists and ≥1 when every pair must intersect.

```python filename=modules/orchestration-and-governance/code/quorum-inter-01/quorum.py:47-49 COMPLETE
def min_overlap(n, w, r):
    """The smallest possible intersection between any W-subset and any R-subset of N replicas -- enumerated, not assumed."""
    return min(len(set(ws) & set(rs)) for ws in combinations(range(n), w) for rs in combinations(range(n), r))
```

**A read** returns the newest version among the replicas it actually contacts — so if none of them holds the write, the newest it can see is the old version.

```python filename=modules/orchestration-and-governance/code/quorum-inter-01/quorum.py:52-54 COMPLETE
def read_version(replicas, read_set):
    """A read returns the newest version among the replicas it contacted."""
    return max(replicas[i] for i in read_set)
```

<svg role="img" aria-label="Three replica slots: with W=1 and R=1 the write set and read set can occupy different slots and not overlap, but with W=2 and R=2 they cannot both fit in three slots without sharing one" viewBox="0 0 300 128" width="300" height="128">
  <text x="6" y="12" fill="var(--muted)" font-size="8">W+R must exceed N to force the sets to share a replica</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">W1R1 (2 ≤ 3): can be disjoint</text>
  <g transform="translate(30,40)">
  <rect x="0" y="0" width="26" height="26" fill="var(--s2)"/><text x="6" y="17" fill="var(--panel)" font-size="7">W</text>
  <rect x="34" y="0" width="26" height="26" fill="var(--s1)"/><text x="42" y="17" fill="var(--panel)" font-size="7">R</text>
  <rect x="68" y="0" width="26" height="26" fill="none" stroke="var(--line)"/>
  <text x="100" y="17" fill="var(--muted)" font-size="7">no shared slot → stale possible</text>
  </g>
  <text x="10" y="90" fill="var(--muted)" font-size="7">W2R2 (4 &gt; 3): must overlap</text>
  <g transform="translate(30,96)">
  <rect x="0" y="0" width="26" height="26" fill="var(--s2)"/><text x="6" y="17" fill="var(--panel)" font-size="7">W</text>
  <rect x="34" y="0" width="26" height="26" fill="var(--ink)"/><text x="38" y="17" fill="var(--panel)" font-size="6">W+R</text>
  <rect x="68" y="0" width="26" height="26" fill="var(--s1)"/><text x="76" y="17" fill="var(--panel)" font-size="7">R</text>
  <text x="100" y="17" fill="var(--muted)" font-size="7">middle slot shared → always fresh</text>
  </g>
</svg>
^ With W=1 and R=1 the write and read can land on different replicas and never meet; with W=2 and R=2 there are not enough of the three slots to keep them apart, so they must share one — the replica that carries the write into the read.

**Overlap is guaranteed exactly when R + W > N, so the read and write quorums must be sized together — the guarantee is a property of the two numbers, not of either one alone.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/quorum-inter-01/quorum.py

The fixture is N = 3 and several quorum configurations to test.

```json filename=modules/orchestration-and-governance/code/quorum-inter-01/quorum.json:4-9 COMPLETE
  "configs": [
    {"name": "W1R1", "w": 1, "r": 1},
    {"name": "W2R2", "w": 2, "r": 2},
    {"name": "W3R1", "w": 3, "r": 1},
    {"name": "W1R3", "w": 1, "r": 3}
  ]
```

Run `--quorum` to compute each config's overlap.

```text filename=--quorum
QUORUM — does the read set always overlap the write set? (N=3)
------------------------------------------------------------------
  config   W    R    R+W    R+W>N    min overlap    stale read?
  W1R1     1    1    2      False    0              YES -- possible
  W2R2     2    2    4      True     1              no
  W3R1     3    1    4      True     1              no
  W1R3     1    3    4      True     1              no
------------------------------------------------------------------
  overlap is guaranteed exactly when R + W > N.
```

Only W1R1 fails: R + W = 2 is not greater than 3, and the enumerated minimum overlap is 0, so a stale read is possible. Every other config has R + W = 4 > 3 and a minimum overlap of at least 1 — no stale read. Notice the three passing configs are three different strategies for the same guarantee. W2R2 is the majority quorum (write a majority, read a majority), the balanced default. W3R1 is write-all/read-one: writes must reach every replica (slow, fragile to a down node) but reads are cheap and hit only one. W1R3 is write-one/read-all: writes are cheap but reads must consult everyone. All three satisfy R + W > 3, so all three guarantee a read sees the latest write; they differ only in whether they make writes or reads pay for it. That is the real content of quorum tuning — the overlap guarantee is non-negotiable if you want consistency, but where you spend the cost to get it is a choice about your read/write mix.

<svg role="img" aria-label="Three quorum strategies over N=3 that all satisfy R+W>N: write-one read-all, majority two-two, and write-all read-one, shown as where the cost falls on writes versus reads" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">three ways to satisfy R+W&gt;3, differing in who pays</text>
  <g font-size="7">
  <text x="10" y="34" fill="var(--muted)">W1R3</text>
  <rect x="60" y="24" width="18" height="12" fill="var(--s2)"/><text x="82" y="34" fill="var(--muted)">cheap write</text>
  <rect x="150" y="24" width="90" height="12" fill="var(--s1)"/><text x="244" y="34" fill="var(--muted)">read all 3</text>
  <text x="10" y="62" fill="var(--muted)">W2R2</text>
  <rect x="60" y="52" width="54" height="12" fill="var(--s2)"/><text x="118" y="62" fill="var(--muted)">write 2</text>
  <rect x="150" y="52" width="60" height="12" fill="var(--s1)"/><text x="214" y="62" fill="var(--muted)">read 2 (majority)</text>
  <text x="10" y="90" fill="var(--muted)">W3R1</text>
  <rect x="60" y="80" width="90" height="12" fill="var(--s2)"/><text x="154" y="90" fill="var(--muted)">write all 3</text>
  <rect x="150" y="80" width="18" height="12" fill="var(--s1)"/><text x="172" y="90" fill="var(--muted)">cheap read</text>
  </g>
</svg>
^ Write-one/read-all, majority, and write-all/read-one all clear R + W > N and so all guarantee fresh reads; they only move the cost between the write path and the read path to match a workload's read/write mix.

## Build

The abstract "minimum overlap 0" becomes a concrete stale value when you run the reads. Run `--stale`.

```text filename=--stale
STALE — a disjoint read (W1R1) vs an overlapping read (W2R2), N=3
------------------------------------------------------------------
  W=1: write replica 0 -> versions {0: 2, 1: 1, 2: 1}
       read replica [1] (R=1, disjoint) -> version 1  <- STALE (missed the write)
  W=2: write replicas 0,1 -> versions {0: 2, 1: 2, 2: 1}
       read replicas [1,2] (R=2) -> version 2  <- FRESH (replica 1 carried the write)
```

Under W1R1 the write lands on replica 0 (now version 2) while replicas 1 and 2 stay at version 1. A read that consults only replica 1 sees version 1 and returns it — a stale read, and a completely confident one: the read did exactly what it was told, contacted a live replica, and returned the newest version it found, which happened to be old. Nothing errored. Under W2R2 the write lands on replicas 0 and 1, and a read of replicas 1 and 2 finds version 2 on replica 1 (the overlap) and version 1 on replica 2, takes the newer, and returns version 2. The only thing that changed between the two is the quorum sizes; the data, the write, and the read pattern are otherwise identical. The write simply records the new version on the chosen replicas.

```python filename=modules/orchestration-and-governance/code/quorum-inter-01/quorum.py:57-62 COMPLETE
def apply_write(n, write_set, new_version=2):
    """Every replica starts at version 1; the write sets the write_set replicas to the new version."""
    replicas = {i: 1 for i in range(n)}
    for i in write_set:
        replicas[i] = new_version
    return replicas
```

<svg role="img" aria-label="Three replicas: W1R1 writes replica 0 to version 2 while a read of replica 1 sees version 1 (stale), and W2R2 writes replicas 0 and 1 so a read of replicas 1 and 2 finds version 2" viewBox="0 0 300 128" width="300" height="128">
  <text x="6" y="12" fill="var(--muted)" font-size="8">W1R1 read misses the write; W2R2 read overlaps it</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">W1R1</text>
  <g transform="translate(40,22)" font-size="7">
  <rect x="0" y="0" width="34" height="20" fill="var(--s2)"/><text x="4" y="14" fill="var(--panel)">r0 v2</text>
  <rect x="40" y="0" width="34" height="20" fill="none" stroke="var(--s1)"/><text x="44" y="14" fill="var(--muted)">r1 v1</text>
  <rect x="80" y="0" width="34" height="20" fill="none" stroke="var(--line)"/><text x="84" y="14" fill="var(--muted)">r2 v1</text>
  <text x="122" y="14" fill="var(--muted)">read r1 → v1 STALE</text>
  </g>
  <text x="10" y="86" fill="var(--muted)" font-size="7">W2R2</text>
  <g transform="translate(40,74)" font-size="7">
  <rect x="0" y="0" width="34" height="20" fill="var(--s2)"/><text x="4" y="14" fill="var(--panel)">r0 v2</text>
  <rect x="40" y="0" width="34" height="20" fill="var(--ink)" stroke="var(--s1)"/><text x="44" y="14" fill="var(--panel)">r1 v2</text>
  <rect x="80" y="0" width="34" height="20" fill="none" stroke="var(--s1)"/><text x="84" y="14" fill="var(--muted)">r2 v1</text>
  <text x="122" y="14" fill="var(--muted)">read r1,r2 → v2 FRESH</text>
  </g>
  <text x="40" y="118" fill="var(--muted)" font-size="7">the read set (outlined) meets the write set (filled) only under W2R2</text>
</svg>
^ Under W1R1 the read of replica 1 never touches the written replica 0, so it returns the stale version 1; under W2R2 the write covers replicas 0 and 1, so any two-replica read includes a written one and returns version 2.

## Definition of done

The self-test pins the no-guarantee case, the guaranteed case, both concrete reads, and the overlap formula.

```python filename=modules/orchestration-and-governance/code/quorum-inter-01/quorum.py:102-112 COMPLETE
    rw_le_n_no_guarantee = (w1["r"] + w1["w"] <= n) and min_overlap(n, w1["w"], w1["r"]) == 0
    print("  W1R1 has R+W<=N and a possible zero overlap = %s (R+W=%d, min overlap %d)"
          % (rw_le_n_no_guarantee, w1["r"] + w1["w"], min_overlap(n, w1["w"], w1["r"])))

    w2 = cfg["W2R2"]
    rw_gt_n_guaranteed = (w2["r"] + w2["w"] > n) and min_overlap(n, w2["w"], w2["r"]) >= 1
    print("  W2R2 has R+W>N and a guaranteed overlap >=1 = %s (R+W=%d, min overlap %d)"
          % (rw_gt_n_guaranteed, w2["r"] + w2["w"], min_overlap(n, w2["w"], w2["r"])))

    concrete_stale = read_version(apply_write(n, [0]), [1]) == 1
    print("  W1R1: writing replica 0 then reading replica 1 is stale = %s" % concrete_stale)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — R+W>N gives a guaranteed non-zero overlap; R+W<=N allows a disjoint, stale read; the concrete reads match
--------------------------------------------------------------------------------------------------------------------------
  W1R1 has R+W<=N and a possible zero overlap = True (R+W=2, min overlap 0)
  W2R2 has R+W>N and a guaranteed overlap >=1 = True (R+W=4, min overlap 1)
  W1R1: writing replica 0 then reading replica 1 is stale = True
  W2R2: writing replicas 0,1 then reading replicas 1,2 is fresh = True
  the enumerated min overlap equals max(0, W+R-N) for every config = True
```

**Done means the overlap guarantee and its failure are proven by enumeration: W1R1 (R + W = 2 ≤ 3) has a possible zero overlap and a concrete stale read (write replica 0, read replica 1 → version 1), W2R2 (R + W = 4 > 3) has a guaranteed overlap ≥ 1 and a concrete fresh read (→ version 2), and the enumerated minimum overlap equals max(0, W + R − N) for every config — so consistency requires R + W > N, sized as the read/write mix dictates.**

## Boss fight

Predict two ways R + W > N is necessary but not sufficient, because the formula assumes things a real system has to also provide.

The first trap is that quorum overlap gives you a *recent* value but not automatically the *right* one — you also need a way to tell which of the overlapping replicas' versions is newest, and to repair the stale ones. A read that contacts an up-to-date replica and a stale one gets two different versions and must pick the newer; that requires a version stamp that actually orders writes (a per-object version number, a vector clock, or a last-writer-wins timestamp), and last-writer-wins by wall-clock time can silently drop a concurrent write when two clients write near-simultaneously and clocks disagree. Concurrent writes that a single version counter cannot order are exactly what vector clocks and conflict resolution (or CRDTs) exist to handle. And overlap alone leaves the stale replicas stale: production quorum systems add read-repair (a read that notices a stale replica writes the newer value back) and anti-entropy (background reconciliation, the subject of the companion Merkle module), so that staleness is corrected rather than allowed to persist and spread. Quorum sizing decides whether a read *can* see the latest write; versioning and repair decide whether it can *identify* and *heal* it.

The second trap is that W and R are also availability and fault-tolerance knobs, so you cannot choose them for consistency in isolation. A write needs W replicas reachable to succeed and a read needs R, so large quorums that give a comfortable overlap also make the system less available: W = N (write-all) means any single down replica blocks all writes, and R = N blocks all reads. There is a tension with fault tolerance too — to survive f failures you need enough replicas that a quorum is still reachable, which for a majority quorum means N ≥ 2f + 1. And the whole R + W > N guarantee assumes the write actually reached W replicas *durably* before returning; if a write is acknowledged after reaching W replicas but one fails before persisting, the effective W drops and the overlap can vanish, which is why quorum writes must be durable and why "sloppy quorums" that write to substitute replicas (hinted handoff) relax the guarantee for availability and then must reconcile later. So the real design sets N for fault tolerance, then picks W and R to satisfy R + W > N while balancing read latency, write latency, and availability — the inequality is the floor, not the whole decision.

**R + W > N is the necessary floor for a read to see the latest write, but it is not sufficient: you also need versioning that orders writes (and conflict resolution or CRDTs for concurrent ones), read-repair and anti-entropy to heal stale replicas, durable quorum writes, and N chosen for fault tolerance (N ≥ 2f + 1) — because W and R are simultaneously the consistency, latency, and availability knobs, and sizing them is a trade-off, not just an inequality.**

## External resources

Amazon's Dynamo paper and any distributed-database documentation on tunable consistency (Cassandra, Riak) — the N/W/R quorum model, the R + W > N rule, and the read-repair and anti-entropy mechanisms that accompany it.

Writing on quorum systems and the CAP/PACELC trade-offs — why larger quorums improve consistency at the cost of availability and latency, and how N ≥ 2f + 1 relates quorum size to the number of failures tolerated.

The companion anti-entropy (Merkle) and idempotency modules in this topic — quorum overlap makes a recent value reachable, anti-entropy heals the replicas the quorum did not touch, and both assume writes that can be safely retried and reconciled.
