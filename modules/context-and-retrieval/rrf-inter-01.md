---
id: rrf-inter-01
title: Fuse two retrievers by rank, not by raw score — adding a lexical and a dense score lets the bigger scale win alone
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: Hybrid search combines a lexical retriever (BM25, keyword overlap) with a dense retriever (cosine of embeddings) because each finds documents the other misses. To return one list you fuse the two, and the obvious way — add each document's two scores and sort — is broken, because the scores are not on the same scale. BM25 is unbounded (a strong match scores 40, a weak one 5); cosine is bounded in [0,1]. Add them and the BM25 term dominates every sum, the cosine term is a rounding error next to it, so the fused ranking is just the BM25 ranking and the dense retriever contributes nothing — the semantic matches with few shared keywords, exactly what dense retrieval exists to find, are buried. Reciprocal Rank Fusion fixes this by fusing the ranks: each retriever contributes 1/(k+rank), and a document's fused score is the sum across retrievers, so being #1 by cosine counts the same as being #1 by BM25 regardless of raw magnitude. On a fixture of five documents, naive raw-sum reproduces the BM25 order and leaves the top dense match d3 stuck at rank 3, while RRF surfaces d3 to #1 — and putting cosine on a 0–100 scale flips the naive order to the cosine order but leaves the RRF order unchanged.
eli5: Imagine judging a contest with two judges. One judge scores from 0 to 100; the other scores from 0 to 1. If you just add their scores together, the first judge completely decides the winner and the second judge might as well not be there — a 0.9 from the second judge is nothing next to an 80 from the first. That's unfair; you wanted both judges to matter. The fix is to ignore the raw numbers and use each judge's RANKING instead: whoever a judge put first gets the same credit whether that judge scores out of 100 or out of 1. Now a contestant both judges liked rises to the top, and it doesn't matter what scale either judge happened to use.
---

## Why this module

The whole reason to run two retrievers is that they disagree productively — one catches exact keywords, the other catches meaning. But the moment you combine their scores by adding them, you can silently throw one of them away, and the fused list looks reasonable while quietly being a single retriever wearing a hybrid label.

Hybrid search combines a lexical retriever (BM25, keyword overlap) with a dense retriever (cosine similarity of embeddings), because each finds documents the other misses: BM25 nails exact terms and rare tokens, dense finds paraphrases and synonyms with no shared words. To return one ranked list you have to fuse the two, and the obvious way — add each document's two scores and sort — is broken, because the two scores are not on the same scale. BM25 is unbounded: a strong keyword match can score 40 while a weak one scores 5. Cosine is bounded in [0,1]. Add them and the BM25 term dominates every sum; the cosine term, never larger than 1, is a rounding error next to a BM25 of 40. So the fused ranking is just the BM25 ranking with imperceptible jitter, and the dense retriever — the whole reason you added semantic search — contributes nothing. The documents dense retrieval exists to surface, strong semantic matches with few shared keywords, are exactly the ones buried.

Reciprocal Rank Fusion fixes this by throwing away the raw scores and fusing the ranks. Each retriever contributes 1/(k+rank) for a document, where rank is its position in that retriever's list and k is a small constant, and the document's fused score is the sum of these across retrievers. Rank is scale-free: being #1 by BM25 is worth the same as being #1 by cosine, no matter that one raw score is 40 and the other is 0.95. So both retrievers get an equal vote, a document ranked highly by either is rewarded, and one ranked highly by both rises to the top. RRF needs no score normalization, no per-retriever weight tuning, and no assumption that the scores are comparable — only that each retriever produces an ordering. This module fuses five documents both ways and shows the dense match surface.

**Two retrievers on different score scales cannot be fused by adding their scores — the larger scale dominates and the fused list echoes one retriever — so fuse the ranks with 1/(k+rank), which is scale-free and gives every retriever an equal vote regardless of its raw magnitudes.**

## Concepts

**Naive fusion** adds the raw BM25 and cosine scores. Because BM25 is unbounded and cosine is capped at 1, the sum is governed almost entirely by BM25, so sorting by it reproduces the BM25 order.

```python filename=modules/context-and-retrieval/code/rrf-inter-01/rrf.py:56-58 COMPLETE
def naive_fuse(docs):
    """Add the raw bm25 and cosine scores -- broken: the unbounded bm25 scale dominates the [0,1] cosine."""
    return {d: docs[d]["bm25"] + docs[d]["cosine"] for d in docs}
```

**Ranks** are each retriever's ordering as positions — 1 for its top document, 2 for the next — discarding the raw magnitudes entirely. This is the scale-free signal RRF fuses.

```python filename=modules/context-and-retrieval/code/rrf-inter-01/rrf.py:51-53 COMPLETE
def ranks(scores):
    """Map each document to its 1-based rank under a retriever's scores (1 = top)."""
    return {d: i + 1 for i, d in enumerate(order_by(scores))}
```

**RRF** sums 1/(k+rank) across the retrievers. A small k makes top ranks count much more than tail ranks, and because it uses only ranks, each retriever contributes an equal, scale-independent vote.

```python filename=modules/context-and-retrieval/code/rrf-inter-01/rrf.py:61-65 COMPLETE
def rrf_fuse(docs, k):
    """Reciprocal Rank Fusion: sum 1/(k+rank) across retrievers, using ranks not raw scores."""
    bm = ranks({d: docs[d]["bm25"] for d in docs})
    co = ranks({d: docs[d]["cosine"] for d in docs})
    return {d: 1 / (k + bm[d]) + 1 / (k + co[d]) for d in docs}
```

<svg role="img" aria-label="Two score scales: BM25 running from 0 to 40 and beyond, cosine running only from 0 to 1, so a full cosine score is a tiny sliver next to a BM25 score" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">adding scores: cosine's whole range is a sliver of BM25's</text>
  <text x="10" y="40" fill="var(--muted)" font-size="7">BM25</text>
  <rect x="50" y="30" width="230" height="14" fill="var(--s2)"/>
  <text x="52" y="40" fill="var(--panel)" font-size="7">0 ————————————————————— 40+</text>
  <text x="10" y="72" fill="var(--muted)" font-size="7">cosine</text>
  <rect x="50" y="62" width="6" height="14" fill="var(--s1)"/>
  <text x="60" y="72" fill="var(--muted)" font-size="7">0–1 (max 1.0)</text>
  <text x="50" y="92" fill="var(--muted)" font-size="7">in bm25 + cosine, the cosine term can never move the ranking</text>
</svg>
^ BM25 ranges into the tens while cosine maxes out at 1.0, so in a raw sum the entire cosine range is smaller than the gap between two BM25 scores — the dense signal cannot change the order.

**Raw-score fusion is governed by whichever retriever has the larger scale, so it silently discards the other; fusing ranks with 1/(k+rank) gives each retriever an equal vote and depends on no scale at all.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/rrf-inter-01/rrf.py

The fixture is five documents, each with a BM25 score and a cosine score. d1–d2 are keyword-heavy; d3–d4 are strong semantic matches with modest keyword overlap.

```json filename=modules/context-and-retrieval/code/rrf-inter-01/rrf.json:4-10 COMPLETE
  "docs": {
    "d1": {"bm25": 40.0, "cosine": 0.20},
    "d2": {"bm25": 35.0, "cosine": 0.30},
    "d3": {"bm25": 10.0, "cosine": 0.95},
    "d4": {"bm25": 8.0, "cosine": 0.85},
    "d5": {"bm25": 5.0, "cosine": 0.10}
  }
```

Run `--fuse` to rank both retrievers and fuse them both ways.

```text filename=--fuse
FUSE — per-retriever ranks, then naive raw-sum vs RRF
------------------------------------------------------------------
  doc   bm25    (rank)   cosine   (rank)
  d1    40.0    (1)      0.20     (4)
  d2    35.0    (2)      0.30     (3)
  d3    10.0    (3)      0.95     (1)
  d4    8.0     (4)      0.85     (2)
  d5    5.0     (5)      0.10     (5)
------------------------------------------------------------------
  bm25 order        : ['d1', 'd2', 'd3', 'd4', 'd5']
  naive raw-sum     : ['d1', 'd2', 'd3', 'd4', 'd5']   <- identical to bm25; cosine ignored
  RRF (k=60)        : ['d3', 'd1', 'd2', 'd4', 'd5']   <- d3 (top cosine) surfaces to #1
```

Look at d3: it is the single best semantic match, ranked #1 by cosine at 0.95, but only #3 by BM25 at 10. Under naive raw-sum its fused score is 10 + 0.95 = 10.95, which sits below d1's 40.20 and d2's 35.30 — the 0.95 could not lift it past a ten-point BM25 gap — so it lands at rank 3, and the naive fused order is character-for-character the BM25 order. The dense retriever ran, produced a perfect result, and was ignored. RRF ranks d3 first: it gets a strong vote from being #1 in cosine (1/61) and a decent vote from being #3 in BM25 (1/63), and that pair of rank-votes beats d1's #1-BM25 / #4-cosine split. The retriever whose entire purpose is to find semantic matches now actually influences the top of the list.

## Build

The naive fusion's dependence on scale is not hypothetical — it means an arbitrary choice of score range silently reorders your results. Run `--scale`, which puts cosine on a 0–100 scale instead of 0–1.

```text filename=--scale
SCALE — put cosine on a 0-100 scale (x100) instead of 0-1, then re-fuse
--------------------------------------------------------------
  naive raw-sum, cosine in [0,1]   : ['d1', 'd2', 'd3', 'd4', 'd5']
  naive raw-sum, cosine x100       : ['d3', 'd4', 'd2', 'd1', 'd5']   <- flipped to the cosine order
  RRF, cosine in [0,1]             : ['d3', 'd1', 'd2', 'd4', 'd5']
  RRF, cosine x100                 : ['d3', 'd1', 'd2', 'd4', 'd5']   <- unchanged
--------------------------------------------------------------
  naive fusion depends on an arbitrary scale choice; RRF depends only on ranks, so its order is fixed.
```

Nothing about the documents changed — the same five results, the same relative similarities — only the units cosine is reported in. Yet the naive fused order flips completely: with cosine in [0,1] it was the BM25 order (d1 first), and with cosine ×100 it becomes the cosine order (d3, d4 first), because now the cosine term dominates the sum instead of BM25. That is the tell that raw-score fusion is broken: its output depends on a units choice that has nothing to do with relevance, so whoever picked the score ranges quietly picked the winner. RRF returns the identical order in both runs, because it never read the magnitudes — it read the ranks, and rescaling a score does not change any document's rank.

<svg role="img" aria-label="Document d3 moving from rank 3 under naive fusion up to rank 1 under RRF, while the naive order matches the BM25 order" viewBox="0 0 300 118" width="300" height="118">
  <text x="6" y="12" fill="var(--muted)" font-size="8">RRF lifts the top dense match d3 from rank 3 to rank 1</text>
  <text x="40" y="28" fill="var(--muted)" font-size="8">naive raw-sum</text>
  <text x="200" y="28" fill="var(--muted)" font-size="8">RRF</text>
  <g transform="translate(40,34)" font-size="7">
  <rect x="0" y="0" width="60" height="14" fill="var(--panel)" stroke="var(--line)"/><text x="4" y="10" fill="var(--muted)">1  d1</text>
  <rect x="0" y="16" width="60" height="14" fill="var(--panel)" stroke="var(--line)"/><text x="4" y="26" fill="var(--muted)">2  d2</text>
  <rect x="0" y="32" width="60" height="14" fill="var(--s2)" stroke="var(--line)"/><text x="4" y="42" fill="var(--panel)">3  d3</text>
  <rect x="0" y="48" width="60" height="14" fill="var(--panel)" stroke="var(--line)"/><text x="4" y="58" fill="var(--muted)">4  d4</text>
  <rect x="0" y="64" width="60" height="14" fill="var(--panel)" stroke="var(--line)"/><text x="4" y="74" fill="var(--muted)">5  d5</text>
  </g>
  <g transform="translate(200,34)" font-size="7">
  <rect x="0" y="0" width="60" height="14" fill="var(--s1)" stroke="var(--line)"/><text x="4" y="10" fill="var(--panel)">1  d3</text>
  <rect x="0" y="16" width="60" height="14" fill="var(--panel)" stroke="var(--line)"/><text x="4" y="26" fill="var(--muted)">2  d1</text>
  <rect x="0" y="32" width="60" height="14" fill="var(--panel)" stroke="var(--line)"/><text x="4" y="42" fill="var(--muted)">3  d2</text>
  <rect x="0" y="48" width="60" height="14" fill="var(--panel)" stroke="var(--line)"/><text x="4" y="58" fill="var(--muted)">4  d4</text>
  <rect x="0" y="64" width="60" height="14" fill="var(--panel)" stroke="var(--line)"/><text x="4" y="74" fill="var(--muted)">5  d5</text>
  </g>
  <line x1="102" y1="73" x2="198" y2="41" stroke="var(--s1)" stroke-dasharray="3 2"/>
</svg>
^ Under naive fusion d3 sits at rank 3 (the naive order matching BM25's), and RRF lifts it to rank 1 by counting its #1 cosine rank equally with the lexical ranks — the dashed line traces the promotion the scale-free fusion produces.

## Definition of done

The self-test pins the naive failure, the burial, the RRF fix, and the scale-invariance.

```python filename=modules/context-and-retrieval/code/rrf-inter-01/rrf.py:118-123 COMPLETE
    rrf_differs = rrf_order != bm_order
    print("  the RRF order differs from the BM25 order = %s" % rrf_differs)

    scaled = {d: {"bm25": docs[d]["bm25"], "cosine": docs[d]["cosine"] * 100} for d in docs}
    rrf_scale_free = order_by(rrf_fuse(scaled, k)) == rrf_order
    print("  putting cosine on a 0-100 scale leaves the RRF order unchanged = %s" % rrf_scale_free)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — naive fusion reproduces the BM25 order and buries the dense-top doc; RRF surfaces it and ignores score scale
--------------------------------------------------------------------------------------------------------------------------
  naive raw-sum fusion reproduces the BM25 order = True (['d1', 'd2', 'd3', 'd4', 'd5'])
  the top dense match (d3) is NOT first under naive fusion = True (rank 3)
  RRF ranks the top dense match first = True (['d3', 'd1', 'd2', 'd4', 'd5'])
  the RRF order differs from the BM25 order = True
  putting cosine on a 0-100 scale leaves the RRF order unchanged = True
```

**Done means the failure and the fix are proven on real orders: naive raw-sum fusion reproduces the BM25 order exactly (d1..d5) and leaves the top dense match d3 at rank 3, while RRF ranks d3 first and its order differs from BM25's — and rescaling cosine to [0,100] flips the naive order but leaves the RRF order unchanged, because RRF fuses ranks, not scores.**

## Boss fight

Predict where RRF's rank-only design, which is exactly what makes it robust, also costs you — because discarding the scores discards information.

<svg role="img" aria-label="Two retrievers with very different score gaps between rank 1 and rank 2 both reduce to the same ranks 1 and 2, so RRF cannot see that one is a runaway and the other a photo finish" viewBox="0 0 300 112" width="300" height="112">
  <text x="6" y="12" fill="var(--muted)" font-size="8">RRF sees only ranks, not the gap between them</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">runaway:</text>
  <rect x="70" y="24" width="120" height="12" fill="var(--s1)"/><text x="72" y="33" fill="var(--panel)" font-size="7">0.99</text>
  <rect x="70" y="40" width="12" height="12" fill="var(--s1)"/><text x="86" y="49" fill="var(--muted)" font-size="7">0.10</text>
  <text x="10" y="76" fill="var(--muted)" font-size="7">photo finish:</text>
  <rect x="70" y="66" width="120" height="12" fill="var(--s2)"/><text x="72" y="75" fill="var(--panel)" font-size="7">0.99</text>
  <rect x="70" y="82" width="118" height="12" fill="var(--s2)"/><text x="72" y="91" fill="var(--panel)" font-size="7">0.98</text>
  <text x="210" y="40" fill="var(--muted)" font-size="7">both → ranks</text>
  <text x="210" y="52" fill="var(--muted)" font-size="7">1 and 2,</text>
  <text x="210" y="76" fill="var(--muted)" font-size="7">identical to</text>
  <text x="210" y="88" fill="var(--muted)" font-size="7">RRF</text>
</svg>
^ A retriever that is far more confident in its top result (0.99 vs 0.10) and one that barely separates its top two (0.99 vs 0.98) both collapse to ranks 1 and 2, so RRF treats them identically — the robustness to incomparable scales is also blindness to real margins.

The first trap is that RRF is deliberately blind to margins, so it cannot tell a runaway top result from a photo finish. Because it uses only ranks, a document that a retriever scored 0.99 and the runner-up that scored 0.98 are treated identically to a 0.99 and a 0.10 — rank 1 and rank 2 either way. That robustness is the point when scores are incomparable across retrievers, but it means RRF throws away real confidence signal, and when one retriever is genuinely far more certain than another, or when the gap between rank 1 and rank 2 is huge, RRF flattens it. If your retrievers' scores ARE calibrated and comparable, a score-based fusion (after proper normalization — min-max or z-score per retriever) can beat RRF by keeping the margins; RRF wins precisely when you cannot trust the scores to be comparable, which is the common case but not the only one. The constant k also encodes a choice: small k sharply rewards top ranks (so being #1 matters enormously), large k flattens toward treating all ranks equally, and the default 60 is a convention, not a law — worth tuning if your retrievers have very different depth or quality.

The second trap is that fusion sits atop each retriever's own failures and cannot repair them. RRF fuses the lists it is given, so a document that neither retriever ranked well is unreachable no matter how you fuse — if BM25 missed it (no keyword overlap) and dense missed it (poor embedding), fusion has nothing to promote. And it inherits each retriever's biases: if the dense retriever has an embedding-version mismatch and is returning near-random orderings, RRF will faithfully fuse that noise in as an equal vote, degrading the result rather than ignoring the broken retriever. Fusion is a combining step, not a quality gate, so it must be paired with healthy retrievers, sensible per-retriever cutoffs (fuse the top-k of each, not their full noisy tails), and often a final precise reranker (a cross-encoder) over the fused top results — RRF gets a good, scale-robust candidate set cheaply, and a heavier reranker orders the few that matter. RRF is the right default for combining incomparable rankers, not a substitute for good retrieval or precise reranking.

**RRF's rank-only fusion is robust because it ignores incomparable score scales, but that same blindness discards calibrated confidence and margins (so normalized score-fusion can win when scores ARE comparable), depends on the constant k, and cannot fix a broken or missing retriever — so use it to combine trustworthy rankers over sensible per-retriever cutoffs, and pair it with a precise reranker when the top-of-list order must be exact.**

## External resources

The Reciprocal Rank Fusion paper (Cormack, Clarke, Buettcher) and any hybrid-search documentation (Elasticsearch, OpenSearch, vector databases) — the 1/(k+rank) formula, the default k=60, and why rank fusion avoids the score-normalization problem of combining lexical and dense retrievers.

Writing on score normalization for hybrid search — min-max and z-score normalization as the alternative to RRF when retriever scores are calibrated and comparable, and the trade-off between keeping margins and being scale-robust.

The companion cross-encoder reranking and embedding-version modules in this topic — RRF produces a scale-robust candidate set to rerank, and a broken dense retriever (e.g. a version mismatch) is fused in as noise, so fusion depends on the health of the retrievers beneath it.
