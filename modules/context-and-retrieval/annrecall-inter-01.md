---
id: annrecall-inter-01
title: An ANN index searches only the nearest clusters, so it misses a true neighbor across a boundary — recall < 1 until nprobe rises
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: Exact nearest-neighbor search compares the query to every indexed vector and returns the genuinely closest — perfectly accurate but O(N) per query, which does not scale to millions of vectors. So production vector search uses approximate nearest-neighbor (ANN) indexes that are far faster by not looking at every point. A common one is IVF: at build time it partitions the vectors into clusters around centroids, and at query time it finds the query's nearest centroids and searches only the points in those nprobe clusters, skipping the rest. Skipping most of the index is where the speed comes from and where the accuracy loss comes from, because a true nearest neighbor that lives in a cluster the query did not search is never seen. This happens at every cluster boundary: a point just across the boundary can be one of the closest overall yet belong to a different cluster than the query's own, so with nprobe=1 it is missed, and the returned list is missing some of the true top-k — measured as recall, the fraction of the exact top-k actually found. The knob is nprobe: searching more clusters raises recall toward 1 at the cost of touching more points, so ANN is a tunable speed/recall trade-off, not exact search. On a fixture where the query at 4.5 is closest to p1 (4.0) and p2 (5.5) but p2 sits in a different cluster, exact top-3 is [p1,p2,p3] while IVF nprobe=1 returns [p1,p3,p4] (recall 0.67, missing p2) and nprobe=2 recovers the exact result at recall 1.0.
eli5: Imagine searching for the nearest coffee shops, but to save time you only look in your own neighborhood. A shop one block over — just across the neighborhood line — might actually be closer than some in your neighborhood, but you never checked that block, so you miss it. That's how fast vector search works: it splits everything into neighborhoods and only checks the nearest one or two, which is quick but can skip a genuinely close result sitting just over a border. If you check more neighborhoods you find more of the real nearest ones, but it takes longer — so you tune how many to check based on how many misses you can live with.
---

## Why this module

At scale you cannot compare a query to every vector, so vector databases quietly return *approximate* nearest neighbors — and code that treats them as the exact nearest neighbors is trusting results the index never promised. The misses are not random noise; they cluster at boundaries, they are silent, and how many you get is a dial you have to set, not a property you can assume.

Exact nearest-neighbor search compares the query to every indexed vector and returns the genuinely closest — perfectly accurate, but O(N) per query, which does not scale to millions of vectors. So production vector search uses approximate nearest-neighbor (ANN) indexes that are far faster by not looking at every point. A common one is IVF (inverted file): at build time it partitions the vectors into clusters around centroids; at query time it finds the query's nearest centroids and searches only the points in those nprobe clusters, skipping the rest. Skipping most of the index is where the speed comes from — and where the accuracy loss comes from, because a true nearest neighbor that lives in a cluster the query did not search is simply never seen.

This is not a rare edge case; it happens at every cluster boundary. A point just on the far side of a boundary from the query can be one of the closest points overall, yet belong to a different cluster than the query's own, so with nprobe=1 (search only the single nearest cluster) it is missed. The result is a returned list missing some of the true top-k, measured as recall: the fraction of the exact top-k that the ANN search actually found. The knob is nprobe: searching more clusters raises recall toward 1 because the boundary neighbors' clusters get included, at the cost of touching more points and so more time. ANN is a speed/recall trade-off you tune, not exact search, and the mistake is treating an ANN index as if it returned exact results. This module runs an exact search and an IVF search and measures the recall.

**An IVF vector index searches only the nprobe clusters nearest the query, so a true neighbor across a cluster boundary is missed and recall (the fraction of the exact top-k found) is below 1; raising nprobe recovers recall at the cost of touching more points — ANN is a tunable speed/recall trade-off, not exact search.**

## Concepts

**Exact search** compares the query to every point and takes the k closest — the ground truth against which recall is measured, and the thing ANN approximates to go faster.

```python filename=modules/context-and-retrieval/code/annrecall-inter-01/annrecall.py:61-64 COMPLETE
def exact_topk(data):
    """Compare the query to every point and return the k genuinely closest."""
    q, pts, k = data["query"], data["points"], data["k"]
    return sorted(pts, key=lambda p: dist(q, pts[p]))[:k]
```

**IVF search** finds the nprobe centroids nearest the query and searches only the points in those clusters — fast because it skips the other clusters, lossy because a neighbor in a skipped cluster is invisible.

```python filename=modules/context-and-retrieval/code/annrecall-inter-01/annrecall.py:67-73 COMPLETE
def ivf_topk(data, nprobe):
    """Search only the nprobe clusters nearest the query, then take the k closest among their points."""
    q, pts, k, cents = data["query"], data["points"], data["k"], data["centroids"]
    assign = assignments(pts, cents)
    probed = sorted(cents, key=lambda c: dist(q, cents[c]))[:nprobe]
    candidates = [p for p in pts if assign[p] in probed]
    return sorted(candidates, key=lambda p: dist(q, pts[p]))[:k]
```

<svg role="img" aria-label="A 1-D line with two clusters: the query sits in cluster c0 near the boundary, and a true neighbor p2 sits just across the boundary in cluster c1, so searching only c0 misses it" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the query's cluster is searched; a neighbor across the border is not</text>
  <line x1="20" y1="56" x2="285" y2="56" stroke="var(--line)"/>
  <line x1="150" y1="40" x2="150" y2="72" stroke="var(--ink)" stroke-dasharray="3 2"/><text x="132" y="88" fill="var(--muted)" font-size="6">cluster boundary</text>
  <rect x="20" y="48" width="130" height="16" fill="var(--s1)" opacity="0.25"/><text x="30" y="34" fill="var(--muted)" font-size="6">c0 (searched)</text>
  <rect x="150" y="48" width="135" height="16" fill="var(--s2)" opacity="0.25"/><text x="230" y="34" fill="var(--muted)" font-size="6">c1 (skipped)</text>
  <circle cx="128" cy="56" r="3" fill="var(--ink)"/><text x="118" y="50" fill="var(--muted)" font-size="6">query 4.5</text>
  <circle cx="116" cy="56" r="3" fill="var(--s1)"/><text x="106" y="72" fill="var(--muted)" font-size="6">p1</text>
  <circle cx="164" cy="56" r="3" fill="var(--s2)"/><text x="158" y="72" fill="var(--muted)" font-size="6">p2 (missed!)</text>
</svg>
^ The query and p1 are in cluster c0, which nprobe=1 searches; p2 is just across the boundary in c1, closer to the query than most of c0's points, but nprobe=1 never looks in c1 and misses it.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/annrecall-inter-01/annrecall.py

The fixture is a query, two cluster centroids, and five points (each assigned to its nearest centroid).

```json filename=modules/context-and-retrieval/code/annrecall-inter-01/annrecall.json:3-5 COMPLETE
  "query": [4.5, 0.0],
  "k": 3,
  "centroids": {"c0": [0.0, 0.0], "c1": [10.0, 0.0]},
```

Run `--search` to compare exact and IVF (nprobe=1).

```text filename=--search
SEARCH — exact top-3 vs IVF nprobe=1 (query [4.5, 0.0])
--------------------------------------------------------------
  query's nearest cluster: c0
  exact top-3      : ['p1', 'p2', 'p3']
  IVF nprobe=1     : ['p1', 'p3', 'p4']   <- searched only the query's cluster
--------------------------------------------------------------
  missed neighbor(s): ['p2']  (recall 0.67)
```

The exact top-3 are p1 (at 4.0, distance 0.5), p2 (at 5.5, distance 1.0), and p3 (at 3.0, distance 1.5). IVF with nprobe=1 returns p1, p3, p4 — it found p1 and p3 but missed p2 and substituted p4 (at 1.0, distance 3.5, much farther). The reason is entirely structural: the query at 4.5 is nearest to centroid c0 (at 0, distance 4.5, versus 5.5 to c1), so nprobe=1 searches only cluster c0, whose points are p1, p3, p4. But p2 at 5.5 is assigned to centroid c1 (distance 4.5 to c1 at 10, versus 5.5 to c0 at 0), so it lives in the cluster the query did not search — even though p2 is only 1.0 from the query, closer than most of c0's own points. That is exactly the boundary case that makes ANN lossy: p2 is one of the query's true nearest neighbors but sits just across the cluster line from it, so it is invisible to a single-cluster search. Recall is 2/3 = 0.67: the ANN search found two of the three true neighbors and silently dropped the third. Nothing errored; the returned list just quietly omits a relevant result, which in retrieval means the passage that answered the query never reaches the model.

<svg role="img" aria-label="Two result lists: exact returns p1, p2, p3; IVF nprobe 1 returns p1, p3, p4, dropping the true neighbor p2 and substituting the farther p4" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">IVF drops the true neighbor p2 and substitutes the farther p4</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">exact</text>
  <g transform="translate(60,24)" font-size="7" fill="var(--panel)">
  <rect x="0" y="0" width="40" height="16" fill="var(--s1)"/><text x="8" y="11">p1</text>
  <rect x="44" y="0" width="40" height="16" fill="var(--s2)"/><text x="52" y="11">p2</text>
  <rect x="88" y="0" width="40" height="16" fill="var(--s1)"/><text x="96" y="11">p3</text>
  <text x="134" y="11" fill="var(--muted)">← true top-3</text>
  </g>
  <text x="10" y="66" fill="var(--muted)" font-size="7">IVF np=1</text>
  <g transform="translate(60,56)" font-size="7" fill="var(--panel)">
  <rect x="0" y="0" width="40" height="16" fill="var(--s1)"/><text x="8" y="11">p1</text>
  <rect x="44" y="0" width="40" height="16" fill="var(--s1)"/><text x="52" y="11">p3</text>
  <rect x="88" y="0" width="40" height="16" fill="var(--muted)"/><text x="94" y="11">p4</text>
  <text x="134" y="11" fill="var(--s2)">p2 dropped → recall .67</text>
  </g>
  <text x="10" y="92" fill="var(--muted)" font-size="7">the reranker downstream can only reorder p1,p3,p4 — it can never recover p2</text>
</svg>
^ Exact returns [p1, p2, p3]; IVF nprobe=1 returns [p1, p3, p4], silently dropping the genuine neighbor p2 (in the unsearched cluster) and filling the slot with the farther p4 — recall 0.67, and nothing downstream can recover the missing p2.

## Build

The fix is to search more clusters, and the cost is looking at more points. Run `--nprobe`.

```text filename=--nprobe
NPROBE — recall rises as more clusters are searched
----------------------------------------------------------
  nprobe   result            recall
  1        ['p1', 'p3', 'p4']  0.67
  2        ['p1', 'p2', 'p3']  1.00
----------------------------------------------------------
  nprobe=1 is fast but misses the boundary neighbor; nprobe=2 is complete here.
```

With nprobe=2 the search includes both clusters, so p2 in c1 is now a candidate, and the result becomes p1, p2, p3 — exactly the exact top-3, recall 1.0. That is the whole trade-off in two rows: nprobe=1 touched only one cluster (fast, recall 0.67), nprobe=2 touched both (slower, recall 1.0). In a real index with thousands of clusters, nprobe=1 might touch 0.1% of the vectors and nprobe=20 might touch 2%, trading a 20× increase in points examined for a jump in recall from, say, 0.7 to 0.95 — and you pick the operating point from how much missed-neighbor loss the application tolerates against its latency budget. The recall number is what makes that choice measurable: it is the fraction of the exact top-k the ANN search recovered, so you compute it on a sample of queries against a slow exact search and tune nprobe until recall is high enough.

```python filename=modules/context-and-retrieval/code/annrecall-inter-01/annrecall.py:76-77 COMPLETE
def recall(result, exact):
    return len(set(result) & set(exact)) / len(exact)
```

<svg role="img" aria-label="Recall versus nprobe: 0.67 at nprobe 1, 1.0 at nprobe 2, with more points searched at higher nprobe" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">recall rises with nprobe (and so does work)</text>
  <line x1="40" y1="88" x2="290" y2="88" stroke="var(--line)"/>
  <line x1="40" y1="24" x2="40" y2="88" stroke="var(--line)"/>
  <text x="34" y="28" fill="var(--muted)" font-size="7" text-anchor="end">1.0</text>
  <text x="34" y="60" fill="var(--muted)" font-size="7" text-anchor="end">.67</text>
  <g transform="translate(90,0)">
  <rect x="0" y="56" width="40" height="32" fill="var(--s2)"/><text x="2" y="100" fill="var(--muted)" font-size="7">nprobe 1</text><text x="8" y="52" fill="var(--muted)" font-size="7">0.67</text>
  </g>
  <g transform="translate(200,0)">
  <rect x="0" y="24" width="40" height="64" fill="var(--s1)"/><text x="2" y="100" fill="var(--muted)" font-size="7">nprobe 2</text><text x="12" y="20" fill="var(--muted)" font-size="7">1.0</text>
  </g>
  <text x="90" y="20" fill="var(--muted)" font-size="6">1 cluster searched</text><text x="200" y="20" fill="var(--muted)" font-size="6">2 clusters searched</text>
</svg>
^ Searching one cluster gives recall 0.67; searching both gives 1.0 — recall climbs toward 1 as nprobe rises, at the cost of examining more points, which is the tunable speed/recall trade-off ANN exists to expose.

## Definition of done

The self-test pins exact completeness, the nprobe=1 miss, the boundary cause, and the recovery.

```python filename=modules/context-and-retrieval/code/annrecall-inter-01/annrecall.py:115-123 COMPLETE
    exact_full = recall(ex, ex) == 1.0
    print("  exact search returns the full top-%d = %s (%s)" % (data["k"], exact_full, ex))

    iv1 = ivf_topk(data, 1)
    nprobe1_misses = recall(iv1, ex) < 1.0
    print("  IVF nprobe=1 misses a true neighbor = %s (%s, recall %.2f)" % (nprobe1_misses, iv1, recall(iv1, ex)))

    missed = [p for p in ex if p not in iv1][0]
    boundary_neighbor = assign[missed] != nearest_centroid(q, cents)
    print("  the missed neighbor is in a different cluster than the query = %s (%s in %s, query in %s)"
          % (boundary_neighbor, missed, assign[missed], nearest_centroid(q, cents)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — exact search finds all top-k; IVF nprobe=1 misses a boundary neighbor (recall<1); raising nprobe restores recall
----------------------------------------------------------------------------------------------------------------------------
  exact search returns the full top-3 = True (['p1', 'p2', 'p3'])
  IVF nprobe=1 misses a true neighbor = True (['p1', 'p3', 'p4'], recall 0.67)
  the missed neighbor is in a different cluster than the query = True (p2 in c1, query in c0)
  IVF nprobe=2 recovers full recall = True (['p1', 'p2', 'p3'])
  recall rises with nprobe = True (0.67 -> 1.00)
```

**Done means the approximation and its knob are proven on real results: exact search returns the full top-3, IVF nprobe=1 misses p2 (recall 0.67) because p2 is in cluster c1 while the query is in c0, and nprobe=2 recovers the exact top-3 (recall 1.0) — so an ANN index returns approximate results whose recall depends on nprobe and must be measured, not assumed.**

## Boss fight

Predict two ways ANN recall is subtler than "raise nprobe," because recall is a per-index, per-workload property and it interacts with the rest of the retrieval stack.

The first trap is that recall is not a single number — it depends on the index type and its build parameters, the data distribution, and the query, so it must be measured on your own data, not read off a benchmark. Different ANN algorithms expose different knobs (IVF has nprobe and the number of clusters; HNSW has ef_search and the graph degree M; product quantization adds a compression error on top of the search error), and each trades recall against latency and memory differently. Build-time choices matter as much as query-time ones: too few IVF clusters and each is huge (slow to scan even one); too many and boundary effects worsen; a badly trained set of centroids leaves lopsided clusters. And recall varies by query — queries near cluster boundaries or in sparse regions have lower recall than queries in dense cluster centers — so a single average recall hides a tail of poorly-served queries. The only reliable way to know your recall is to run a sample of real queries through both the ANN index and an exact search and measure it, then tune to your latency budget; a benchmark's recall on other data does not transfer.

The second trap is that ANN's recall loss stacks with every other lossy stage of retrieval, so the end-to-end recall is a product, not a single term. A RAG pipeline typically embeds (lossy: the embedding may not capture the query's intent), retrieves via ANN (lossy: this module's recall), maybe reranks a shortlist (can only reorder what ANN returned — it cannot recover a neighbor ANN already dropped), and truncates to a context budget (can drop a retrieved-but-low-ranked passage). A neighbor missed by the ANN stage is gone for good downstream: the reranker never sees it, the model never reads it. So chasing reranker quality while running the ANN index at 0.7 recall is optimizing the wrong stage — the ceiling on what the reranker and model can use is set by ANN recall. The implications: measure recall at the retrieval stage specifically (not just end-to-end answer quality, which conflates all the losses), set nprobe/ef high enough that ANN is not the bottleneck for your accuracy needs, and remember that for a small enough corpus exact (brute-force) search is fast enough and has recall 1 by definition — ANN is a scaling tool whose approximation you accept only because exact search is too slow, so use exact search when you can afford it.

**ANN recall is a property of the specific index (IVF vs HNSW vs PQ), its build parameters, the data distribution, and even the individual query (boundary queries fare worst), so it must be measured on your own data and tuned to your latency budget rather than assumed from a benchmark — and because a neighbor the ANN stage drops cannot be recovered by a reranker or the model downstream, ANN recall sets the ceiling for the whole pipeline, so measure it at the retrieval stage and use exact search whenever the corpus is small enough to afford it.**

## External resources

Documentation for FAISS, HNSW, and IVF/product-quantization indexes — the nprobe / ef_search knobs, how clusters and graphs trade recall for speed, and how to measure recall@k against exact search.

The ANN-Benchmarks project and writing on approximate nearest-neighbor search — recall/latency curves across algorithms, why recall depends on data and query distribution, and why it must be measured per workload.

The companion reranking, MMR, and cosine modules in this topic — ANN produces the candidate set those stages operate on, so a neighbor ANN misses is invisible to reranking and diversification, and ANN recall bounds the whole retrieval pipeline.
