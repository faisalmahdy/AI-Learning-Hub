---
id: govern-inter-16
title: Make the read and write quorums overlap (R + W > N) — or a read can miss the latest write
topic: orchestration-and-governance
level: intermediate
status: ready
time: 21 min
summary: In a store replicated across N nodes, a write succeeds after W acknowledge and a read queries R and takes the newest version it sees. A read reflects the latest write only if its R nodes are guaranteed to include one the write reached — which holds exactly when R + W > N, by pigeonhole. On N=3 with a write to 2 nodes, a strong config (R=2, so R+W=4>3) makes every read fresh, while a weak config (R=1, R+W=3) allows a read of the one node that missed the write, returning stale data.
eli5: Imagine news is posted on some of three bulletin boards, and you check some of them. If the boards you post to and the boards you check are guaranteed to share at least one board, you'll always see the latest news. That's guaranteed only if the number you post to plus the number you check is more than three — otherwise you might post and check completely different boards and miss it.
---

## Why this module

Reading from a replicated store is only guaranteed to see the latest write when the nodes you read and the nodes you wrote are forced to overlap, and that overlap is not automatic.

A value is replicated across N nodes so it survives a node failure. To stay fast and available, neither operation waits for all N: a write succeeds once W nodes acknowledge it, and a read queries R nodes and returns the newest version it finds among them. This is quorum replication, and it is the backbone of highly available datastores — you tune W and R to trade off read speed, write speed, and durability without ever blocking on a slow or dead node.

The question that decides correctness is whether a read is guaranteed to reflect the most recent successful write. A read sees the latest write only if at least one of the R nodes it asks is a node the write actually reached. If the R read nodes can be entirely disjoint from the W write nodes, then a read can land only on replicas that never received the write, and it returns the old value — even though the write succeeded and acknowledged. That is a silent stale read: no error, no timeout, just yesterday's data served with full confidence.

Whether that disjoint case is possible comes down to arithmetic. If R + W is not greater than N, you can fit R read nodes and W write nodes into the N nodes without any overlap, so a stale read is possible. If R + W > N, they cannot both fit without sharing a node — by the pigeonhole principle, any set of R nodes and any set of W nodes together demand more than N slots, so they must intersect in at least one node, and that node carries the latest write. Overlap is the guarantee of freshness; R + W > N is simply how you force overlap. Common settings all satisfy it: W = N with R = 1 (fast reads), R = N with W = 1 (fast writes), or R = W = a majority (balanced).

On the fixture, N = 3 and a write reached 2 nodes. A strong config with R = 2 gives R + W = 4 > 3, so every possible read set includes an up-to-date node and every read is fresh. A weak config with R = 1 gives R + W = 3, not greater than 3, so a read can ask the single node that missed the write and return the stale old value.

**A quorum read reflects the latest write only if its R nodes must include one of the W the write reached, and that is guaranteed exactly when R + W > N, because pigeonhole forces the read and write quorums to overlap; if R + W ≤ N a disjoint read set exists and returns stale data silently.**

## Concepts

The whole guarantee is a statement about set intersection, not about timing or coordination. A write marks W of the N nodes with the new version; a read inspects R of them and takes the max version. The read is correct if and only if the read set and the write set share at least one node — that shared node has the new version, so the max the read computes is the new version. There is no need for the nodes to talk to each other at read time; the freshness comes purely from the guarantee that the two sets cannot avoid each other. Quorum systems turn a consistency question into a combinatorics question.

Pigeonhole is why R + W > N is exactly the right threshold. Two subsets of an N-element set, of sizes R and W, are forced to intersect precisely when R + W > N: if their sizes sum to more than N, they cannot be packed into N elements disjointly, so they overlap. If R + W ≤ N they can be disjoint (there is room for R + W distinct nodes), and a stale read becomes possible — not guaranteed on every read, but possible, and in distributed systems "possible" means "will happen." So the inequality is not a heuristic or a safety margin; it is the exact boundary between "every read is fresh" and "some read can be stale."

<svg role="img" aria-label="Two subsets of N nodes: when R+W exceeds N they must overlap, when R+W is at most N they can be disjoint" viewBox="0 0 470 175" width="470" height="175">
  <rect x="0" y="0" width="470" height="175" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">pigeonhole: R + W nodes cannot fit in N without overlap</text>
  <text x="30" y="46" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">R + W &gt; N (4 &gt; 3): forced overlap</text>
  <rect x="40" y="54" width="120" height="26" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="70" y="71" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">write {0,1}</text>
  <rect x="120" y="54" width="120" height="26" fill="var(--s1)" opacity="0.3" stroke="var(--s1)"/>
  <text x="180" y="71" font-family="var(--mono)" font-size="8" fill="var(--s1)">read {1,2}</text>
  <text x="122" y="98" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">↑ share node 1 → fresh</text>
  <text x="30" y="128" font-family="var(--mono)" font-size="8" fill="var(--s2)">R + W = N (3): can be disjoint</text>
  <rect x="40" y="136" width="120" height="26" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="70" y="153" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">write {0,1}</text>
  <rect x="300" y="136" width="60" height="26" fill="var(--s2)" opacity="0.3" stroke="var(--s2)"/>
  <text x="312" y="153" font-family="var(--mono)" font-size="8" fill="var(--s2)">read {2}</text>
  <text x="180" y="153" font-family="var(--mono)" font-size="7" fill="var(--s2)">no shared node → STALE</text>
</svg>
^ When R + W exceeds N the read and write sets must share a node (fresh); when R + W ≤ N there is room for them to be disjoint, and the disjoint read returns stale data.

This exposes the tuning space quorum systems live in. Because only the sum R + W (relative to N) governs freshness, you can slide the cost between reads and writes freely while keeping the guarantee. Want fast reads? Set R small and W large (W = N, R = 1: read one node, but every write must hit all N). Want fast writes? The mirror (W = 1, R = N). Want balance and also tolerance of a node being down for both operations? Set R = W = ⌈(N+1)/2⌉, a majority each, which satisfies R + W > N with the smallest quorums that do. There is also a separate durability constraint — W must be large enough that a write survives the failures you tolerate — but freshness is governed by the sum.

This is the classic Dynamo-style tunable-consistency model, and its cautions are worth carrying. R + W > N gives you read-your-writes-style freshness for a single value under this simple model, but real systems add wrinkles: concurrent writes need version reconciliation (vector clocks, last-write-wins) because "newest version" can be ambiguous; sloppy quorums and hinted handoff (accepting writes on substitute nodes when the intended ones are down) can weaken the guarantee; and this is not full linearizability, just quorum overlap for one key. Choosing R + W ≤ N is a legitimate choice too — it buys lower latency and higher availability at the cost of possible stale reads, which many systems accept deliberately (eventual consistency). The point is to choose the sum on purpose, knowing that R + W ≤ N means stale reads are on the table.

**Freshness reduces to whether the read and write sets intersect, and pigeonhole makes R + W > N the exact condition that forces intersection; the sum governs consistency while its split between R and W tunes read-versus-write cost, with durability and concurrent-write reconciliation as separate concerns.**

## Worked example

The fixture is a replica count, the write set, and two read-quorum configs.

```json filename=modules/orchestration-and-governance/code/govern-inter-16/replicas.json:3-9 COMPLETE
  "n": 3,
  "write_set": [0, 1],
  "configs": {
    "strong": 2,
    "weak": 1
  }
```

Three nodes; the write reached nodes 0 and 1 (W = 2), so they hold the new version and node 2 holds the old. The strong config reads R = 2 nodes, the weak config reads R = 1. A node's version is new if the write reached it, and a read returns the newest version among the nodes it queried.

```python filename=modules/orchestration-and-governance/code/govern-inter-16/quorum.py:43-50 COMPLETE
def versions(n, write_set):
    """Version per replica: written replicas hold the new version (2), the rest the old (1)."""
    return [2 if i in write_set else 1 for i in range(n)]


def read_value(read_set, vers):
    """A read returns the newest version among the replicas it queried."""
    return max(vers[i] for i in read_set)
```

A stale read is any read set that returns the old version — equivalently, one disjoint from the write set. The code enumerates every possible read set to check.

```python filename=modules/orchestration-and-governance/code/govern-inter-16/quorum.py:57-61 COMPLETE
def stale_reads(n, r, write_set):
    """Read sets (of size r) that return the OLD version -- i.e. disjoint from the write set."""
    vers = versions(n, write_set)
    new = max(vers)
    return [rs for rs in all_read_sets(n, r) if read_value(rs, vers) != new]
```

Enumerating all possible read sets is one line of combinatorics — every R-subset of the N nodes.

```python filename=modules/orchestration-and-governance/code/govern-inter-16/quorum.py:53-54 COMPLETE
def all_read_sets(n, r):
    return [set(c) for c in itertools.combinations(range(n), r)]
```

Predict: strong has R + W = 4 > 3, so no read set can avoid the write set — all fresh. Weak has R + W = 3, so the read set {2} is disjoint from {0, 1} and returns stale. Check the sums first.

```text filename=modules/orchestration-and-governance/code/govern-inter-16/quorum.py --config
CONFIG — does R + W exceed N = 3? (write reached 2 nodes)
----------------------------------------------------------
  strong   R=2 W=2  R+W=4 > 3  overlap guaranteed: True
  weak     R=1 W=2  R+W=3 <= 3  overlap guaranteed: False
----------------------------------------------------------
  R + W > N is what forces the read and write quorums to overlap.
```

Strong's sum is 4 > 3, so overlap is guaranteed; weak's sum is 3, not greater than 3, so it is not. Now enumerate every read set and see which return stale.

```text filename=modules/orchestration-and-governance/code/govern-inter-16/quorum.py --reads
READS — every read set's result (write set = [0, 1], new version = 2)
----------------------------------------------------------
  strong (R=2):
    read [0, 1]     -> version 2  fresh
    read [0, 2]     -> version 2  fresh
    read [1, 2]     -> version 2  fresh
  weak (R=1):
    read [0]        -> version 2  fresh
    read [1]        -> version 2  fresh
    read [2]        -> version 1  STALE
```

Under the strong config every 2-node read set — {0,1}, {0,2}, {1,2} — contains at least one of the written nodes 0 or 1, so all three return the fresh version 2. There is no way to pick 2 of 3 nodes and miss both written ones. Under the weak config, reading a single node, the sets {0} and {1} hit written nodes and are fresh, but {2} is the one node the write missed, and it returns the stale version 1. That stale read is not a bug in the code; it is the direct consequence of R + W = 3 not exceeding N = 3, which leaves room for a read set disjoint from the write.

<svg role="img" aria-label="Three nodes with nodes 0 and 1 written (new); a size-2 read always overlaps the write set, while a size-1 read can pick node 2 and miss it" viewBox="0 0 470 195" width="470" height="195">
  <rect x="0" y="0" width="470" height="195" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">3 nodes: 0,1 written (new v2), 2 stale (old v1)</text>
  <g font-family="var(--mono)" font-size="9">
    <circle cx="90" cy="55" r="20" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="85" y="59" fill="var(--acc-ink)">0</text>
    <circle cx="160" cy="55" r="20" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="155" y="59" fill="var(--acc-ink)">1</text>
    <circle cx="230" cy="55" r="20" fill="var(--panel)" stroke="var(--s2)"/><text x="225" y="59" fill="var(--s2)">2</text>
  </g>
  <text x="70" y="90" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">written (v2)</text>
  <text x="210" y="90" font-family="var(--mono)" font-size="7" fill="var(--s2)">missed (v1)</text>
  <text x="30" y="125" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">strong R=2: any 2 nodes hit a written one → fresh</text>
  <text x="30" y="150" font-family="var(--mono)" font-size="8" fill="var(--s2)">weak R=1: read {2} misses both writes → STALE</text>
  <text x="30" y="176" font-family="var(--mono)" font-size="8" fill="var(--muted)">R+W>N (4>3) forces overlap; R+W=N (3) leaves the gap at node 2</text>
</svg>
^ With the write on nodes 0 and 1, any 2-node read must include one of them (fresh), but a 1-node read can pick node 2 and miss the write entirely (stale) — the gap R + W ≤ N leaves open.

## Build

Reproduce the reads. Pure standard library — it enumerates every read set — so the strong config's all-fresh and the weak config's stale {2} come out exactly.

Run `--config` for the sums, `--reads` for every read set's result, `--check` for the gate. <svg role="img" aria-label="A grid of R by W at N equals 3, with cells above the anti-diagonal marked fresh (R+W>3) and cells on or below marked stale-possible" viewBox="0 0 470 175" width="470" height="175">
  <rect x="0" y="0" width="470" height="175" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">R (across) by W (down) at N=3: which pairs guarantee fresh?</text>
  <g font-family="var(--mono)" font-size="8" fill="var(--muted)"><text x="70" y="40">R=1</text><text x="150" y="40">R=2</text><text x="230" y="40">R=3</text><text x="20" y="66">W=1</text><text x="20" y="106">W=2</text><text x="20" y="146">W=3</text></g>
  <g font-family="var(--mono)" font-size="8">
    <rect x="60" y="52" width="60" height="28" fill="var(--s2)" opacity="0.3" stroke="var(--s2)"/><text x="76" y="70" fill="var(--s2)">2 ✗</text>
    <rect x="140" y="52" width="60" height="28" fill="var(--s2)" opacity="0.3" stroke="var(--s2)"/><text x="156" y="70" fill="var(--s2)">3 ✗</text>
    <rect x="220" y="52" width="60" height="28" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="236" y="70" fill="var(--acc-ink)">4 ✓</text>
    <rect x="60" y="92" width="60" height="28" fill="var(--s2)" opacity="0.3" stroke="var(--s2)"/><text x="76" y="110" fill="var(--s2)">3 ✗</text>
    <rect x="140" y="92" width="60" height="28" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="156" y="110" fill="var(--acc-ink)">4 ✓</text>
    <rect x="220" y="92" width="60" height="28" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="236" y="110" fill="var(--acc-ink)">5 ✓</text>
    <rect x="60" y="132" width="60" height="28" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="76" y="150" fill="var(--acc-ink)">4 ✓</text>
    <rect x="140" y="132" width="60" height="28" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="156" y="150" fill="var(--acc-ink)">5 ✓</text>
    <rect x="220" y="132" width="60" height="28" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="236" y="150" fill="var(--acc-ink)">6 ✓</text>
  </g>
  <text x="300" y="100" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">✓ = R+W&gt;3 (fresh),</text>
  <text x="300" y="116" font-family="var(--mono)" font-size="8" fill="var(--s2)">✗ = stale possible</text>
</svg>
^ A whole family of (R, W) pairs clears R + W > 3, so you pick the point that makes the cheaper operation small — the sum sets consistency, the split sets cost.

The self-test pins that R + W > N gives all-fresh, R + W ≤ N allows stale, and that freshness holds exactly when the sum exceeds N.

```python filename=modules/orchestration-and-governance/code/govern-inter-16/quorum.py:101-110 COMPLETE
    strong_sum_exceeds = strong_r + w > n
    print("  strong config has R + W > N = %s (%d > %d)" % (strong_sum_exceeds, strong_r + w, n))

    strong_all_fresh = len(stale_reads(n, strong_r, write_set)) == 0
    print("  strong config: every read set is fresh = %s" % strong_all_fresh)

    weak_sum_insufficient = not (weak_r + w > n)
    print("  weak config has R + W <= N = %s (%d <= %d)" % (weak_sum_insufficient, weak_r + w, n))

    weak_has_stale = len(stale_reads(n, weak_r, write_set)) > 0
    print("  weak config: some read set returns stale = %s (%s)"
          % (weak_has_stale, [sorted(s) for s in stale_reads(n, weak_r, write_set)]))
```

```text filename=modules/orchestration-and-governance/code/govern-inter-16/quorum.py --check
SELF-TEST — R + W > N makes every read fresh; R + W <= N allows a stale read
------------------------------------------------------------------------------------------
  strong config has R + W > N = True (4 > 3)
  strong config: every read set is fresh = True
  weak config has R + W <= N = True (3 <= 3)
  weak config: some read set returns stale = True ([[2]])
  freshness holds exactly when R + W > N = True
------------------------------------------------------------------------------------------
SELF-TEST PASS  strong_sum_exceeds=True  strong_all_fresh=True  weak_sum_insufficient=True  weak_has_stale=True  overlap_iff_sum=True
```

Five True flags. Strong_sum_exceeds and strong_all_fresh: the strong config has R + W = 4 > 3 and every read set is fresh. Weak_sum_insufficient and weak_has_stale: the weak config has R + W = 3 and the read set {2} returns stale. Overlap_iff_sum: freshness holds exactly when R + W > N — the arithmetic and the behavior agree, which is the theorem made concrete. That last flag is the point: the guarantee is not approximately about the sum, it is exactly the sum crossing N.

**The overlap-iff-sum flag is the theorem — every read is fresh precisely when R + W > N and stale reads appear the moment it is not, so the single inequality is the entire freshness guarantee, tunable by how you split the sum between R and W.**

## Definition of done

You are done when you reproduce the fresh and stale configs and can explain why R + W > N is the exact condition.

Concretely: `--config` shows strong at R + W = 4 > 3 and weak at 3; `--reads` shows every strong read set fresh and the weak read {2} stale; `--check` prints PASS with five True flags. You can explain that freshness is set intersection (the read must hit a written node), that pigeonhole makes R + W > N the exact threshold that forces overlap, and that the sum governs consistency while its split between R and W tunes read-versus-write cost. You can name the caveats: durability is a separate constraint on W, concurrent writes need version reconciliation, and R + W ≤ N is a legitimate eventual-consistency choice.

The habit to carry: when configuring a quorum-replicated store, set R + W > N if you need a read to reflect the latest write, and choose the split by whether reads or writes must be cheap — and recognize that R + W ≤ N deliberately trades freshness for latency. When a replicated system serves occasional stale reads with no error, check the quorum arithmetic before suspecting a bug: R + W ≤ N makes stale reads a guaranteed possibility, not a glitch.

## Boss fight

The instructive failure is a session store that occasionally logs a user back out right after they log in.

A service stores sessions in a 3-replica quorum store configured for speed: W = 1 (a write acknowledges after one replica) and R = 1 (a read asks one replica). R + W = 2, well under N = 3, so a login that writes the session to one replica can be followed by a read that hits a different replica which has not yet received it — the session appears missing, and the user is bounced back to the login page. It is intermittent and load-dependent, so it is misdiagnosed as a flaky client. The fix is to raise the sum above N — for a session store, W = 2 and R = 2 (majorities) gives read-your-writes freshness while tolerating one node down — and to accept the modest latency cost. The tell is stale reads with no error, correlated with recent writes.

Your turn, two moves. First, find every sufficient config: sweep R and W over 1..3 at N = 3 and list the pairs with R + W > N, confirming there is a family (not one answer) — W=3/R=1, W=1/R=3, W=2/R=2, and more — so you can pick the point that makes the cheaper operation fast. Second, separate durability from freshness: set W = 1 (a write survives on only one node) with R = 3 so that R + W = 4 > 3 and confirm reads are fresh yet a single node failure can lose the write entirely — showing that R + W > N buys freshness but not durability, which needs W large enough to survive the failures you tolerate.

## External resources

The Dynamo paper (DeCandia et al., 2007) introduced tunable N/R/W quorums with the R + W > N consistency condition, and reading it shows the sloppy-quorum and hinted-handoff wrinkles this module flags as caveats.

Any distributed-systems text (Kleppmann's "Designing Data-Intensive Applications," the replication and quorum chapters) derives the R + W > N overlap condition and separates it from durability and from full linearizability.

Documentation for quorum-configurable stores (Cassandra's consistency levels, Riak's n_val/r/w, MongoDB's write and read concerns) shows the knobs in production and the read-your-writes guidance that follows directly from forcing R + W > N.
