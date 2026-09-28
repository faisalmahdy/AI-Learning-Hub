---
id: quantvec-inter-01
title: Rescore the quantized search's top candidates with exact vectors — quantization is cheap but misranks close neighbors
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: Storing every document's embedding at full precision is expensive — millions of vectors of hundreds of 32-bit floats is gigabytes, and scanning it per query is slow. A standard fix is quantization: store the vectors at lower precision (round each component to an 8-bit integer, or a single bit), shrinking the index several-fold and speeding up the distance math. The catch is that rounding is lossy: two vectors slightly different at full precision can round to the same or crossed values, so distances on the quantized vectors are approximate, and the approximation is worst exactly where it matters — among documents close to the query, whose true distances differ by less than the rounding step. There, quantization can flip the order, so the quantized search's top result is not actually the nearest neighbor, just a plausible one. The fix is a two-stage search: use the cheap quantized index to fetch a candidate set (the top-k by quantized distance, k larger than you ultimately want), then re-score just those candidates with the exact, full-precision vectors and rank by exact distance. The quantized stage does not need the order right; it only needs to pull the true nearest into the candidate set (high recall at k), which it usually does because its errors reorder close neighbors but rarely eject them. On a fixture where the true nearest is d1 (exact distance 0.10) but rounding puts d2 in the query's integer bucket (quantized distance 0.00) and rounds d1 away (quantized distance 1.00), the quantized search ranks d2 first — wrong — while the quantized top-2 still includes d1, and exact rescoring returns d1.
eli5: Imagine finding the closest star to a spot using a map where every star's position has been rounded to the nearest whole grid square, to save ink. Rounding is fast and the map is small, but two stars that are almost equally close can get shoved into different squares, so the "closest by rounded grid" star might not really be the closest — it just landed in a lucky square. The trick: use the cheap rounded map to grab the few nearest stars (the real closest is surely among them, even if it's not first), then pull out your precise measuring tape and measure just those few exactly. You get the true closest star, but you only had to do the slow precise measurement on a handful, not on the whole sky.
---

## Why this module

Vector search at scale forces a bargain: full-precision embeddings are accurate but too big and slow, so you compress them, and compression means throwing away exactly the small differences that decide which of two close documents is nearest. The quantized index is wonderful for the corpus-wide scan — it fits in memory and the distances are fast — but its answer to "which document is closest?" is only approximately right, and it is least right in the one region you care about most: the tight cluster of near-neighbors around the query, where the true distances differ by less than a rounding step. Trust that approximate top result and you routinely return the second-best passage, beaten on a rounding artifact.

Rounding is lossy: two vectors that were slightly different at full precision can round to the same or crossed values, so distances computed on the quantized vectors are approximate, and the approximation is worst exactly where it matters — among documents close to the query. There, quantization can flip the order, so the quantized search's top result is not actually the nearest neighbor. And the failure is silent: the returned document is a plausible neighbor, just not the closest one.

The fix is a two-stage search: use the cheap quantized index to fetch a candidate set — the top-k by quantized distance, with k larger than you ultimately want — then re-score just those candidates with the exact, full-precision vectors, ranking by exact distance. The quantized stage only needs to pull the true nearest somewhere into the candidate set, which it usually does; the exact stage fixes the order precisely, on a short list. This module runs the quantized search and the two-stage version.

**Search a quantized (low-precision) vector index to fetch a candidate set, then re-score those candidates with the exact full-precision vectors and rank by exact distance, because quantization's rounding error misranks close neighbors — so the quantized top result is not reliably the nearest — but the candidate set still contains the true nearest, which exact rescoring recovers cheaply.**

## Concepts

**Quantization rounds each vector component to low precision; distance is exact Euclidean** either way — the difference is which vectors go in.

```python filename=modules/context-and-retrieval/code/quantvec-inter-01/quantvec.py:54-61 COMPLETE
def distance(a, b):
    """Euclidean distance between two vectors."""
    return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))


def quantize(vec):
    """Low-precision storage: round each component to the nearest integer."""
    return [round(x) for x in vec]
```

**The quantized ranking uses rounded vectors; the two-stage search takes its top-k and re-ranks them by exact distance.**

```python filename=modules/context-and-retrieval/code/quantvec-inter-01/quantvec.py:69-79 COMPLETE
def quantized_ranking(query, docs):
    """Documents ranked by distance between the quantized query and quantized doc vectors."""
    q = quantize(query)
    return sorted(docs, key=lambda d: (distance(q, quantize(docs[d])), d))


def two_stage(query, docs, k):
    """Fetch the top-k candidates by quantized distance, then re-rank them by exact distance."""
    candidates = quantized_ranking(query, docs)[:k]
    rescored = sorted(candidates, key=lambda d: (distance(query, docs[d]), d))
    return candidates, rescored
```

<svg role="img" aria-label="A 2-D grid: the query at 5.4,2.0 rounds to cell 5,2; d1 at 5.5,2.0 rounds to cell 6,2 (away), d2 at 4.6,2.0 rounds to cell 5,2 (same as query), so quantization puts the farther d2 in the query's cell and the nearer d1 in a different cell" viewBox="0 0 300 112" width="300" height="112">
  <text x="6" y="12" fill="var(--muted)" font-size="8">rounding to the grid: d2 lands in the query's cell, d1 rounds away</text>
  <g stroke="var(--grid)"><line x1="40" y1="30" x2="40" y2="90"/><line x1="110" y1="30" x2="110" y2="90"/><line x1="180" y1="30" x2="180" y2="90"/><line x1="250" y1="30" x2="250" y2="90"/><line x1="40" y1="60" x2="250" y2="60"/></g>
  <text x="66" y="54" fill="var(--muted)" font-size="6">cell 5,2</text><text x="136" y="54" fill="var(--muted)" font-size="6">cell 6,2</text>
  <circle cx="118" cy="60" r="3" fill="var(--ink)"/><text x="112" y="74" fill="var(--ink)" font-size="6">query 5.4</text>
  <circle cx="125" cy="60" r="3" fill="var(--s1)"/><text x="128" y="52" fill="var(--s1)" font-size="6">d1 5.5 (nearest, cell 6)</text>
  <circle cx="90" cy="60" r="3" fill="var(--s2)"/><text x="52" y="52" fill="var(--s2)" font-size="6">d2 4.6 (cell 5)</text>
  <text x="40" y="104" fill="var(--muted)" font-size="6">true nearest d1 is 0.1 away but rounds to a different cell than the query</text>
</svg>
^ On the integer grid, the query (5.4) and its true nearest d1 (5.5) are only 0.1 apart but straddle the boundary between cells 5 and 6, so d1 rounds away; the farther d2 (4.6) rounds into the query's own cell — so quantized distance ranks d2 above the genuinely closer d1.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/quantvec-inter-01/quantvec.py

The fixture is a query, three document embeddings, and the candidate-set size.

```json filename=modules/context-and-retrieval/code/quantvec-inter-01/quantvec.json:3-9 COMPLETE
  "query": [5.4, 2.0],
  "documents": {
    "d1": [5.5, 2.0],
    "d2": [4.6, 2.0],
    "d3": [5.4, 5.0]
  },
  "candidate_k": 2
```

Run `--search`.

```text filename=--search
SEARCH — exact vs quantized distances (query [5.4, 2.0], quantized [5, 2])
----------------------------------------------------------------------
  doc   vector       quantized   exact-dist   quantized-dist
  d1    [5.5, 2.0]   [6, 2]      0.10         1.00
  d2    [4.6, 2.0]   [5, 2]      0.80         0.00
  d3    [5.4, 5.0]   [5, 5]      3.00         3.00
```

Compare the exact-dist and quantized-dist columns. By exact distance, d1 is nearest (0.10), then d2 (0.80), then d3 (3.00) — d1 is the right answer. But the query 5.4 rounds to 5, d1's 5.5 rounds to 6, and d2's 4.6 rounds to 5. So after quantization, d2 sits in the query's exact bucket (quantized distance 0.00) while d1 has rounded to the neighboring bucket (quantized distance 1.00). The quantized search therefore ranks d2 first — the wrong document — because the 0.1-vs-0.8 exact gap between d1 and d2 is smaller than the rounding step of 1, so rounding was free to reorder them. Note that d3, which is genuinely far (3.00), is ranked last by both: quantization scrambles the order of *close* neighbors but is perfectly capable of telling near from far. That is the key property the two-stage design exploits — the quantized search's errors are local, among the near cluster, not global.

## Build

The two-stage search turns that local error into a recoverable one.

```text filename=--twostage
TWOSTAGE — quantized candidate set, then exact rescoring
--------------------------------------------------------------
  stage 1 (quantized) top-2 candidates: ['d2', 'd1']
  stage 2 (exact rescore of candidates):
    d1    exact distance 0.10
    d2    exact distance 0.80
--------------------------------------------------------------
  final nearest = d1 (the true nearest, recovered by rescoring)
```

<svg role="img" aria-label="A two-stage pipeline: the whole corpus is scanned cheaply by the quantized index to produce a small candidate set, which is then re-scored with exact vectors to produce the final ranking" viewBox="0 0 300 92" width="300" height="92">
  <text x="6" y="12" fill="var(--muted)" font-size="8">cheap approximate scan → small candidate set → exact rescore</text>
  <rect x="14" y="30" width="70" height="30" fill="none" stroke="var(--muted)"/><text x="20" y="44" fill="var(--muted)" font-size="6">whole corpus</text><text x="20" y="55" fill="var(--muted)" font-size="6">(quantized)</text>
  <path d="M84 45 L108 45" fill="none" stroke="var(--s2)"/><text x="86" y="40" fill="var(--s2)" font-size="6">cheap</text>
  <rect x="110" y="30" width="70" height="30" fill="none" stroke="var(--s1)"/><text x="116" y="44" fill="var(--s1)" font-size="6">candidates</text><text x="116" y="55" fill="var(--s1)" font-size="6">[d2, d1] (k=2)</text>
  <path d="M180 45 L204 45" fill="none" stroke="var(--s1)"/><text x="182" y="40" fill="var(--s1)" font-size="6">exact</text>
  <rect x="206" y="30" width="80" height="30" fill="var(--s1)"/><text x="212" y="44" fill="var(--panel)" font-size="6">rescored → d1</text><text x="212" y="55" fill="var(--panel)" font-size="6">(true nearest)</text>
  <text x="14" y="80" fill="var(--muted)" font-size="6">full-precision cost paid on 2 candidates, not the whole corpus</text>
</svg>
^ The quantized index scans the whole corpus cheaply to produce a small candidate set, and only that short list is re-scored with exact full-precision vectors — so the expensive exact computation runs on k=2 candidates instead of the entire corpus, recovering the true nearest d1 at a fraction of the cost.

Stage 1 runs the cheap quantized search and takes the top 2 candidates: d2 and d1. Crucially, even though the quantized search got the *order* wrong (d2 before d1), it still pulled the true nearest d1 into the candidate set — because its rounding error reordered the two close neighbors but did not eject either of them, and it correctly left the far d3 out. Stage 2 then re-scores just those two candidates with the exact, full-precision vectors: d1 at 0.10, d2 at 0.80, and picks d1 — the correct nearest neighbor. The whole point is the division of labor: the quantized stage did the expensive part (scanning the whole corpus) approximately but cheaply, and only needed to achieve *recall* — get the right document into a short list — while the exact stage did the precise part (ranking) on just k=2 vectors, paying full-precision cost on a handful instead of the millions in the corpus. This is why production vector search is almost always two-stage (a compressed/approximate index for the scan, exact rescoring of the top candidates): you get quantization's memory and speed for the corpus and exactness where it decides the answer. The candidate size k is the knob — larger k makes it more likely the true nearest is in the set (higher recall) at the cost of more exact rescoring.

```python filename=modules/context-and-retrieval/code/quantvec-inter-01/quantvec.py:118-125 COMPLETE
    quantized_misranks = quant[0] != true_nearest
    print("  the quantized search's top-1 is NOT the true nearest = %s (quantized %s, true %s)" % (quantized_misranks, quant[0], true_nearest))

    true_nearest_in_candidates = true_nearest in candidates
    print("  the true nearest is still in the quantized candidate set = %s (%s in %s)" % (true_nearest_in_candidates, true_nearest, candidates))

    rescoring_recovers = rescored[0] == true_nearest
    print("  exact rescoring of the candidates recovers the true nearest = %s (%s)" % (rescoring_recovers, rescored[0]))
```

## Definition of done

The self-test pins the quantized misrank, the true nearest surviving in the candidate set, the exact-rescoring recovery, and the sub-rounding-step gap that caused it.

```python filename=modules/context-and-retrieval/code/quantvec-inter-01/quantvec.py:127-131 COMPLETE
    far_doc_excluded = exact[-1] not in candidates
    print("  the far document is excluded by the quantized stage = %s (%s not in candidates)" % (far_doc_excluded, exact[-1]))

    exact_gap_below_rounding = distance(q, docs[exact[1]]) - distance(q, docs[exact[0]]) < 1.0
    print("  the true nearest and runner-up differ by less than the rounding step = %s (%.2f gap)"
          % (exact_gap_below_rounding, distance(q, docs[exact[1]]) - distance(q, docs[exact[0]])))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the quantized search misranks the nearest neighbor; two-stage rescoring recovers it from the candidate set
----------------------------------------------------------------------------------------------------------------------
  the quantized search's top-1 is NOT the true nearest = True (quantized d2, true d1)
  the true nearest is still in the quantized candidate set = True (d1 in ['d2', 'd1'])
  exact rescoring of the candidates recovers the true nearest = True (d1)
  the far document is excluded by the quantized stage = True (d3 not in candidates)
  the true nearest and runner-up differ by less than the rounding step = True (0.70 gap)
```

<svg role="img" aria-label="Quantized search returns d2 (wrong), two-stage returns d1 (correct); both from the same candidate set d2, d1" viewBox="0 0 300 92" width="300" height="92">
  <text x="6" y="12" fill="var(--muted)" font-size="8">same candidates, different final answer</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">quantized top-1</text>
  <rect x="100" y="24" width="80" height="16" fill="var(--s2)"/><text x="106" y="36" fill="var(--panel)" font-size="7">d2 (dist 0.80) ✗</text>
  <text x="10" y="62" fill="var(--muted)" font-size="7">two-stage top-1</text>
  <rect x="100" y="52" width="80" height="16" fill="var(--s1)"/><text x="106" y="64" fill="var(--panel)" font-size="7">d1 (dist 0.10) ✓</text>
  <text x="190" y="36" fill="var(--muted)" font-size="6">from candidates [d2, d1]</text>
  <text x="190" y="64" fill="var(--muted)" font-size="6">exact-rescored</text>
  <text x="10" y="86" fill="var(--muted)" font-size="6">the exact rescore of the same short list flips the answer to the true nearest</text>
</svg>
^ The quantized search returns d2 (exact distance 0.80, wrong) while the two-stage search re-scores the same candidate list [d2, d1] with exact vectors and returns d1 (0.10, correct) — the recovery costs only the exact rescoring of two candidates.

**Done means the quantization trade and its fix are proven on real distances: the true nearest is d1 (exact 0.10) but rounding puts d2 in the query's bucket (quantized 0.00) and rounds d1 away (quantized 1.00), so the quantized search ranks d2 first, while the quantized top-2 still contains d1 and exact rescoring returns it — so a quantized vector search must fetch a candidate set and re-score it with full-precision vectors.**

## Boss fight

Predict two ways two-stage quantized search has to be tuned, because the candidate size and the quantization scheme trade recall against cost in opposite directions.

The first trap is that the whole scheme rests on the quantized stage having high RECALL at k — the true nearest must actually be in the candidate set — and that is not guaranteed; it is a tunable that can fail. If the candidate size k is too small, or the quantization is too aggressive (fewer bits, coarser buckets), the true nearest can be pushed out of the top-k entirely, and then exact rescoring has nothing to recover — it re-ranks a candidate set that never contained the right answer, and returns a confident wrong result. So the design has two coupled knobs: how coarse the quantization is (more compression = more memory saved but lower recall per k) and how large the candidate set is (larger k = higher recall but more exact rescoring cost). You size them together against a target recall measured empirically — check on a labeled set that the true nearest is in the candidate set often enough — and there is no free lunch: reclaiming the recall lost to aggressive quantization costs a bigger k, which costs more rescoring. Binary quantization (1 bit per dimension, ~32x smaller) is popular precisely because it pairs with a generous candidate set and cheap Hamming-distance scan, then rescores — but only works because k is set large enough to absorb its coarseness.

The second trap is that quantization is one of several stacked approximations in a real vector search, and they compound, so the exact-rescore stage is defending against more than just rounding. Production nearest-neighbor search is usually BOTH quantized (compressed vectors) AND approximate in its traversal (an ANN index like HNSW or IVF that does not scan every vector but only a subset of the graph or the nearest clusters) — so the candidate set can miss the true nearest for two independent reasons: it rounded wrong (this module) or the ANN traversal never visited the region it was in (the recall-vs-nprobe problem). The two-stage rescore fixes the ranking of whatever candidates it gets, but it cannot recover a document neither stage ever surfaced, so recall is bounded by the WORSE of the two approximations. This is why serious systems measure end-to-end recall (does the pipeline return the true nearest?) rather than trusting either stage, and tune the ANN parameters (how much of the graph to explore) and the quantization/candidate-size together. And there are finer points: the quantization should be calibrated to the data's actual distribution (scalar quantization with per-dimension min/max, or product quantization that clusters sub-vectors, both far better than naive integer rounding), and asymmetric distance computation (quantize only the stored vectors, keep the query full-precision) reduces the error this module showed. The unifying idea is that every corner cut for speed and memory — coarse vectors, partial traversal — trades away exact recall, and the exact-rescore stage buys back precision on the survivors, but only the survivors; getting the true nearest to survive both approximations is the real engineering.

**The scheme lives or dies on the quantized stage's recall at k: too coarse a quantization or too small a candidate set pushes the true nearest out of the set, and then exact rescoring re-ranks a list that never contained the answer — so tune the compression level and k together against an empirically measured recall, accepting that reclaiming recall lost to aggressive quantization costs a bigger k. And quantization is one of several stacked approximations (a compressed index AND an approximate ANN traversal), which compound, so end-to-end recall is bounded by the worse of them — measure the whole pipeline's recall, calibrate the quantizer to the data (scalar/product quantization, asymmetric distance keeping the query full-precision) rather than naive rounding, and remember exact rescoring buys back precision only on the candidates both approximations happened to surface.**

## External resources

Documentation for vector databases and libraries on quantization and rescoring (FAISS product/scalar quantization and refine/rerank, and the binary-quantization + rescore guides from vector-DB vendors) — how compressed indexes are searched and how exact rescoring of the candidate set is configured.

Writing on approximate nearest-neighbor search and its recall trade-offs (product quantization, HNSW/IVF, asymmetric distance computation) — how quantization and approximate traversal compound and how recall is measured and tuned end-to-end.

The companion ANN-recall, cross-encoder-rerank, and cosine modules in this topic — quantized rescoring is the same two-stage retrieve-then-rerank shape as bi-encoder-then-cross-encoder and cluster-search-then-refine, where a cheap approximate first stage must have high recall so an exact second stage can fix the ranking it cannot fix alone.
