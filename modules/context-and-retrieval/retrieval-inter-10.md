---
id: retrieval-inter-10
title: Probe enough clusters — approximate nearest-neighbor silently misses the answer across a boundary
topic: context-and-retrieval
level: intermediate
status: ready
time: 23 min
summary: An IVF vector index buckets documents by nearest centroid and searches only the nprobe buckets closest to the query — fast, but it misses a document sitting just across a cluster boundary. On five queries, nprobe=1 recall@1 is 0.60; the two boundary queries fail. nprobe=2 recovers exhaustive recall, 1.00.
eli5: Imagine books sorted into a few rooms by topic. To answer fast you only search the one room closest to your question. But the perfect book might be on a shelf just inside the next room, and you'll never see it — you'll grab a worse book from your room and think you did fine. Searching two rooms instead of one fixes it, but takes a little longer.
---

## Why this module

Every production vector database you will use is lying to you a little, on purpose, and the lie is invisible until you go looking for it.

Exhaustive nearest-neighbor search — compare the query to every document — is exact but scales linearly with the corpus, which is fine for a thousand documents and hopeless for a hundred million. So real vector indexes are approximate. The most common family, IVF (inverted file, the backbone of FAISS and most vector databases), buckets the documents by their nearest centroid and, at query time, searches only the nprobe buckets closest to the query. If there are a thousand buckets and you probe ten, you have looked at roughly one percent of the corpus and returned an answer a hundred times faster. That speed is why approximate search exists and why you are almost certainly using it.

The catch is baked into the geometry. A document's true distance to the query does not care about bucket walls, but the search does. When the query lands near a boundary between two clusters, its genuinely-nearest document can sit just across that boundary, in a bucket the query did not probe. The search dutifully returns the nearest document among the buckets it *did* look at — a worse answer — and reports success. No error, no warning. The retrieval just quietly got worse for that query, and your RAG system fed the model a less relevant chunk than the one that existed.

This failure is not spread evenly, which is what makes it dangerous. Most queries land squarely inside a cluster and their nearest document is right there — those are fine at nprobe=1. The queries that fail are the boundary queries, and averaged over a benchmark they can hide behind the ones that pass. We will build a three-cluster index where two of five queries have their answer one bucket away, watch recall@1 sit at 0.60, then turn one knob — nprobe from 1 to 2 — and watch it climb to 1.00, exactly matching exhaustive search.

**Approximate search buys speed by looking at a fraction of the corpus, and the bill comes due on exactly the boundary queries whose nearest document lives in a bucket it skipped.**

## Concepts

The IVF index has two moving parts. First, the buckets: every document is assigned to its nearest centroid, so the corpus is partitioned into as many buckets as there are centroids. Second, the probe: a query is routed to the centroids nearest *it*, and only the documents in the nprobe closest buckets are considered. The whole speedup is that nprobe is small relative to the number of buckets.

The recall problem lives entirely in the gap between "nearest document" and "document in the nearest bucket." These are not the same thing, and they diverge at boundaries. Picture a query sitting almost exactly between centroid A and centroid B, tipped slightly toward B so B is its nearest centroid. Now picture a document that sits right at the A–B border, on A's side, very close to the query. That document is the query's true nearest — but it is in bucket A, and at nprobe=1 the query only searches bucket B. The search returns B's best, which is farther. The nearer the query is to a boundary, the more likely its true nearest is on the wrong side of it.

The knob that trades recall for speed is nprobe. At nprobe=1 you search one bucket and are blind to every neighbor across every boundary. Raise nprobe and you search the query's nearest bucket plus its next-nearest, then the next — each additional bucket catches the boundary cases that lean that way. At nprobe equal to the number of buckets you have searched everything, and approximate search has become exact, at exhaustive cost. Every value in between is a point on the recall-versus-latency curve, and choosing nprobe is choosing where on that curve you want to sit.

<svg role="img" aria-label="For query q1, nprobe=1 searches only bucket B and misses x1; nprobe=2 adds bucket A and finds it" viewBox="0 0 460 170" width="460" height="170">
  <rect x="0" y="0" width="460" height="170" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="24" font-family="var(--mono)" font-size="11" fill="var(--muted)">q1's centroid order: B (nearest), A, C</text>
  <text x="16" y="58" font-family="var(--mono)" font-size="11" fill="var(--ink)">nprobe=1:</text>
  <rect x="110" y="42" width="70" height="24" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="132" y="59" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">B</text>
  <rect x="190" y="42" width="70" height="24" fill="var(--panel)" stroke="var(--line)"/><text x="212" y="59" font-family="var(--mono)" font-size="11" fill="var(--muted)">A</text>
  <rect x="270" y="42" width="70" height="24" fill="var(--panel)" stroke="var(--line)"/><text x="292" y="59" font-family="var(--mono)" font-size="11" fill="var(--muted)">C</text>
  <text x="350" y="59" font-family="var(--mono)" font-size="10" fill="var(--s2)">misses x1</text>
  <text x="16" y="108" font-family="var(--mono)" font-size="11" fill="var(--ink)">nprobe=2:</text>
  <rect x="110" y="92" width="70" height="24" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="132" y="109" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">B</text>
  <rect x="190" y="92" width="70" height="24" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="212" y="109" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">A</text>
  <rect x="270" y="92" width="70" height="24" fill="var(--panel)" stroke="var(--line)"/><text x="292" y="109" font-family="var(--mono)" font-size="11" fill="var(--muted)">C</text>
  <text x="350" y="109" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">finds x1</text>
  <text x="16" y="150" font-family="var(--mono)" font-size="10" fill="var(--muted)">shaded = searched; x1 lives in bucket A, the second-nearest</text>
</svg>
^ Adding the second-nearest bucket to the probe set is exactly what brings x1 into view; nprobe is how far down the centroid order you are willing to look.

The reason this is worth a whole module is that the default is often too aggressive. A tutorial sets nprobe=1 because it is fastest and the demo corpus is small enough that nothing lands near a boundary. It ships. The corpus grows, the clusters get tighter, more queries fall near boundaries, and recall quietly erodes — never with an error, only with slightly worse answers that no one traces back to the index. The fix is not exotic; it is knowing the knob exists and measuring recall against exhaustive search before trusting the number.

**"Nearest bucket" is not "nearest document"; nprobe is how many buckets of slack you give that difference, and at nprobe=1 you give it none.**

## Worked example

The fixture is a tiny two-dimensional index — three centroids, fourteen documents, five queries — small enough to reason about by eye but built so the boundary case is exact.

```json filename=modules/context-and-retrieval/code/retrieval-inter-10/points.json:7-20 COMPLETE
  "centroids": {
    "A": [
      0,
      0
    ],
    "B": [
      10,
      0
    ],
    "C": [
      5,
      8
    ]
  },
```

Three clusters: A at the origin, B ten units east, C up and between them. Each document is assigned to its nearest centroid, which gives the buckets.

```python filename=modules/context-and-retrieval/code/retrieval-inter-10/search.py:47-49 COMPLETE
def bucket_of(point, centroids):
    """Assign a point to its nearest centroid -- the IVF bucket it lands in."""
    return min(centroids, key=lambda c: dist(point, centroids[c]))
```

```text filename=modules/context-and-retrieval/code/retrieval-inter-10/search.py --index
INDEX — 14 documents bucketed by nearest centroid into 3 clusters
--------------------------------------------------
  bucket A @ [0, 0]  : a1 a2 a3 a4 x1
  bucket B @ [10, 0] : b1 b2 b3 b4
  bucket C @ [5, 8]  : c1 c2 c3 c4 x2
--------------------------------------------------
  5 queries to answer: q1 q2 q3 q4 q5
```

Notice `x1` in bucket A. It sits at (5, 0.5) — halfway between A and B, tipped just toward A, so it buckets with A. Hold onto it; it is the document two of our queries will need. The approximate search probes the nprobe buckets nearest the query and takes the best document among them.

```python filename=modules/context-and-retrieval/code/retrieval-inter-10/search.py:57-62 COMPLETE
def ann_nearest(q, docs, centroids, buckets, nprobe):
    """Approximate: search only the nprobe buckets nearest the query."""
    order = sorted(centroids, key=lambda c: dist(q, centroids[c]))
    probed = set(order[:nprobe])
    candidates = [d for d in docs if buckets[d] in probed]
    return min(candidates, key=lambda d: dist(q, docs[d]))
```

Query q1 is at (6, 0.5). Its nearest centroid is B (distance 4.03) — closer than A (6.02) — so at nprobe=1 it searches only bucket B. But its true nearest document is x1 at (5, 0.5), distance 1.0, sitting in bucket A. Predict the miss, then run all five.

<svg role="img" aria-label="A 2D map: three clusters A, B, C; query q1 near the A-B boundary with its true nearest document x1 in bucket A, but its nearest centroid is B" viewBox="0 0 460 220" width="460" height="220">
  <rect x="0" y="0" width="460" height="220" fill="var(--panel)" stroke="var(--line)"/>
  <line x1="230" y1="20" x2="230" y2="200" stroke="var(--grid)" stroke-dasharray="4 4"/>
  <text x="150" y="205" font-family="var(--mono)" font-size="10" fill="var(--muted)">A–B boundary</text>
  <circle cx="70" cy="150" r="9" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="60" y="154" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">A</text>
  <circle cx="400" cy="150" r="9" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="393" y="154" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">B</text>
  <circle cx="235" cy="45" r="9" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="228" y="49" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">C</text>
  <circle cx="205" cy="140" r="4" fill="var(--s1)" stroke="var(--ink)"/><text x="180" y="134" font-family="var(--mono)" font-size="10" fill="var(--ink)">x1 (bucket A)</text>
  <rect x="243" y="136" width="9" height="9" fill="var(--s2)" stroke="var(--ink)"/><text x="258" y="144" font-family="var(--mono)" font-size="10" fill="var(--ink)">q1</text>
  <line x1="247" y1="140" x2="209" y2="140" stroke="var(--ink)" stroke-dasharray="2 2"/><text x="150" y="122" font-family="var(--mono)" font-size="9" fill="var(--muted)">true nearest, dist 1.0</text>
  <text x="300" y="176" font-family="var(--mono)" font-size="9" fill="var(--muted)">q1's nearest centroid is B →</text>
</svg>
^ q1 sits just right of the boundary so its nearest centroid is B, but its nearest document x1 is just left of the boundary in bucket A — probe only B and you miss it.

```text filename=modules/context-and-retrieval/code/retrieval-inter-10/search.py --search
SEARCH — true nearest vs approximate at nprobe 1 and 2
----------------------------------------------------------
  query   true   np=1   np=2   nprobe=1 result
  q1    x1     b2     x1     MISS (answer in bucket A)
  q2    x1     x1     x1     hit
  q3    x2     x2     x2     hit
  q4    a2     a2     a2     hit
  q5    x1     b2     x1     MISS (answer in bucket A)
----------------------------------------------------------
  the misses are the queries whose nearest doc sits one bucket away.
```

Two misses, q1 and q5, both returning b2 when the truth is x1 — and both flagged "answer in bucket A," the bucket they never probed. The other three queries land inside a bucket that holds their nearest document and pass at nprobe=1. That is recall@1 of 0.60: three of five queries got the exact answer, two got a plausible wrong one and no signal that anything was off. At nprobe=2 the np=2 column is all correct — every query now probes its nearest bucket and the neighbor, catching x1 across the boundary.

The recall is just the fraction of queries whose approximate answer matches the exhaustive truth.

```python filename=modules/context-and-retrieval/code/retrieval-inter-10/search.py:65-73 COMPLETE
def recall_at_1(data, nprobe):
    """Fraction of queries whose approximate nearest equals the true nearest."""
    docs, cents, queries = data["docs"], data["centroids"], data["queries"]
    buckets = {d: bucket_of(p, cents) for d, p in docs.items()}
    hits = 0
    for q in queries.values():
        if ann_nearest(q, docs, cents, buckets, nprobe) == exhaustive_nearest(q, docs):
            hits += 1
    return round(hits / len(queries), 4)
```

<svg role="img" aria-label="Recall at 1 versus nprobe: 0.60 at nprobe 1, 1.00 at nprobe 2, 1.00 at nprobe 3" viewBox="0 0 460 180" width="460" height="180">
  <rect x="0" y="0" width="460" height="180" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="24" font-family="var(--mono)" font-size="11" fill="var(--muted)">recall@1 vs nprobe (3 clusters)</text>
  <line x1="60" y1="140" x2="440" y2="140" stroke="var(--line)"/>
  <line x1="60" y1="40" x2="440" y2="40" stroke="var(--grid)" stroke-dasharray="3 3"/><text x="30" y="44" font-family="var(--mono)" font-size="10" fill="var(--muted)">1.0</text>
  <rect x="100" y="80" width="60" height="60" fill="var(--s2)" stroke="var(--line)"/><text x="112" y="74" font-family="var(--mono)" font-size="10" fill="var(--ink)">0.60</text><text x="108" y="156" font-family="var(--mono)" font-size="10" fill="var(--muted)">np=1</text>
  <rect x="220" y="40" width="60" height="100" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="232" y="34" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">1.00</text><text x="228" y="156" font-family="var(--mono)" font-size="10" fill="var(--muted)">np=2</text>
  <rect x="340" y="40" width="60" height="100" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="352" y="34" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">1.00</text><text x="340" y="156" font-family="var(--mono)" font-size="10" fill="var(--muted)">np=3 (exact)</text>
</svg>
^ One extra probe lifts recall from 0.60 to 1.00; at nprobe = number of clusters the approximate search is exhaustive.

## Build

Reproduce the recall curve. Pure standard library, deterministic geometry — 0.60 at nprobe=1 and 1.00 at nprobe=2 must come out exactly.

Run `--index` for the buckets, `--search` for the per-query results, `--check` for the gate. The self-test checks the whole recall story: that nprobe=1 misses, that nprobe=2 recovers fully, that more probes help monotonically, and that probing all buckets equals exhaustive search.

```python filename=modules/context-and-retrieval/code/retrieval-inter-10/search.py:111-118 COMPLETE
    r1 = recall_at_1(data, 1)
    r2 = recall_at_1(data, 2)
    r_full = recall_at_1(data, len(cents))

    np1_misses = r1 < 1.0
    print("  nprobe=1 misses some true nearest neighbors = %s (recall@1 = %.2f)" % (np1_misses, r1))

    np2_recovers = r2 == 1.0
    print("  nprobe=2 recovers every true nearest = %s (recall@1 = %.2f)" % (np2_recovers, r2))
```

The `full_is_exact` leg — recall at nprobe = number of clusters equals 1.00 — is the load-bearing sanity check. It proves the misses at low nprobe are purely an artifact of not probing enough buckets, not a bug in the distance function or the fixture: when the index is allowed to look everywhere, it finds the exhaustive answer every time. If that flag failed, the whole story would be suspect. Here is the full gate.

```text filename=modules/context-and-retrieval/code/retrieval-inter-10/search.py --check
SELF-TEST — nprobe=1 misses the boundary queries; nprobe=2 recovers exhaustive recall
----------------------------------------------------------------------------
  nprobe=1 misses some true nearest neighbors = True (recall@1 = 0.60)
  nprobe=2 recovers every true nearest = True (recall@1 = 1.00)
  probing more buckets raises recall = True (0.60 -> 1.00)
  probing all buckets equals exhaustive search = True (recall@1 = 1.00)
----------------------------------------------------------------------------
SELF-TEST PASS  np1_misses=True  np2_recovers=True  more_probes_help=True  full_is_exact=True
```

Four True flags. Np1_misses: the fast setting drops answers. Np2_recovers: one more probe fixes it here. More_probes_help: recall rises with nprobe, never falls. Full_is_exact: at full probe the approximation is the truth. Together they make the point that recall is a dial, not a fixed property — and that the dial was turned too low.

**The self-test proves the misses are a probe-count artifact, not a bug — probe everything and the approximate index returns exactly what exhaustive search does.**

## Definition of done

You are done when you reproduce the recall curve and can explain the miss geometrically.

Concretely: `--search` shows q1 and q5 missing with the answer in bucket A; `--check` prints PASS with recall 0.60 at nprobe=1 and 1.00 at nprobe=2. You can explain why the miss happens — the query's nearest centroid and its nearest document's bucket differ near a boundary — and why raising nprobe fixes it. You can state the trade nprobe governs: recall against how much of the corpus you touch, exact at full probe, fastest and blindest at nprobe=1. And you can say why the failure is dangerous in production: it is silent, it is concentrated on boundary queries, and it hides in an average.

The habit to carry: never trust an approximate index's default nprobe. Measure recall@k against exhaustive search on a sample of real queries, pick the nprobe that clears your recall bar, and re-measure when the corpus grows — because tighter, more numerous clusters push more queries toward boundaries.

## Boss fight

The expensive version is a RAG system whose answer quality degrades as the knowledge base grows, and no one can find the bug because there isn't one — in the code.

A team launches with ten thousand documents, nprobe=1, and it works great: the corpus is sparse, few queries land near boundaries, recall is near-perfect. A year later the knowledge base has a million documents. To keep latency flat they raised the number of clusters, which made each cluster tighter and multiplied the boundaries. Recall has quietly fallen; the retriever now misses the best chunk on a meaningful slice of queries, the model answers from second-best context, and users report the assistant "getting vaguer." Every trace looks clean. The fix is a one-line nprobe change, but finding it requires knowing this failure mode exists and measuring recall against exhaustive search — which no one did, because the system never errored.

Your turn, two moves. First, find each miss's break-even nprobe. q1 and q5 both recover at nprobe=2 here — but construct a query whose true nearest is two buckets away and predict its recovery point: it will still miss at nprobe=2 and only pass at nprobe=3. The break-even nprobe for a query is the rank of its true nearest document's bucket in the query's centroid ordering. Second, weigh the cost. Recall went from 0.60 to 1.00 by doubling the buckets searched — on a real index with a thousand buckets, going from nprobe=1 to nprobe=10 is a 10x recall-side gain in coverage for a 10x search cost. Sit with the shape of that trade: there is no free recall, only a curve, and the right point on it depends on how much a missed document costs your application versus how much latency you can spend. A legal-search tool and a chat toy do not want the same nprobe.

## External resources

The FAISS wiki's "Guidelines to choose an index" and its IVF documentation are the practitioner's reference for nprobe and the recall-latency trade — including the rule that nprobe equal to the number of lists is exhaustive.

For the HNSW graph-based indexes that dominate modern vector databases, the parameter is ef_search rather than nprobe, but the trade is identical; Malkov and Yashunin's HNSW paper describes the same recall-versus-speed knob in graph terms.

For the measurement discipline — recall@k against an exhaustive ground truth — the ann-benchmarks project is the standard: it plots recall against queries-per-second for every major index, which is exactly the curve this module walks by hand.
