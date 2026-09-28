---
id: retrieval-adv-01
title: The hybrid retrieval pipeline — lexical and dense, fused, then reranked
topic: context-and-retrieval
level: advanced
status: ready
time: 12-16h
summary: No single retriever covers a mixed query set: lexical retrieval finds exact-term matches and misses paraphrases, dense retrieval finds paraphrases and misses exact keywords, so each recovers only its own half — 3 of 6 gold documents at rank 1. The production answer is a pipeline: fuse the two rankings with reciprocal rank fusion, which lifts recall@1 to 5 of 6 and recall@3 to 6 of 6 because a document ranked well by either retriever rises, then rerank the fused top-3 with a precise cross-encoder to lift recall@1 to 6 of 6. The fusion must be rank-based, not score-based: lexical term counts (0 to 14) and dense cosines (0 to 1) live on different scales, so adding them raw lets lexical dominate and collapses fusion back to 3 of 6 — the same as lexical alone, the dense half discarded. Recall is a fusion problem, precision is a rerank problem, and scale-free rank fusion is what makes combining two retrievers actually combine them.
eli5: One friend is great at remembering exact words, another at remembering what you meant. Ask each alone and you only get half your answers. Ask both and merge their picks — by how highly each ranked something, not by their raw scores, since they score on different scales — and you get answers from both. Then have a careful expert sort the merged shortlist to put the best one first.
---

## Why this module

The retrieval track built the pieces — measuring retrieval, chunking, the lexical-versus-dense head-to-head, rank fusion, reranking, and diversity. This module assembles them into the pipeline that production retrieval-augmented systems actually run, and measures it stage by stage, because the whole is a specific composition with a specific failure mode, and seeing it end to end is what turns a pile of techniques into an architecture. The headline is that recall and precision are different problems solved by different stages: fusion for recall, reranking for precision, and the glue between them — rank-based fusion — is where a naive implementation quietly throws away half its retrievers.

The composition rests on a fact from the head-to-head module: lexical and dense retrieval fail on different queries. Lexical retrieval, ranking by term overlap, nails queries whose answer shares rare exact words and stumbles when the answer is paraphrased; dense retrieval, ranking by embedding similarity, catches paraphrases and can miss an exact keyword that the embedding blurs. On a query set that mixes both kinds, each retriever recovers only its own half. Fusion combines their rankings so the gold is recovered whichever retriever found it — but only if the fusion is scale-free. Lexical scores are term counts and dense scores are cosines, on wildly different scales, so adding the raw scores lets the larger scale dominate and reproduces one retriever's ranking, discarding the other. Reciprocal rank fusion combines the ranks instead of the scores, which is immune to scale, so a document ranked well by either retriever rises. Then a reranker — an expensive cross-encoder — reorders the fused top-k for precision, lifting the gold from "in the top three" to "at rank one". Each stage does one job, and the pipeline is their sum.

You need the whole retrieval track behind you: `retrieval-inter-02` for the lexical-dense head-to-head, `retrieval-inter-04` for rank fusion, and `retrieval-inter-05` for reranking. Everything runs offline against a query fixture — six queries over six documents, with lexical, dense, and precise scores per document — stdlib Python 3, `$0.00`. The scores are a fixture standing in for real BM25, embedding, and cross-encoder outputs, so the recall at each stage is exact. The instinct to unlearn is that you pick the best retriever. You do not pick; you compose, and the composition beats every part of it — but only if you fuse ranks, not scores.

Here is the pipeline climbing, stage by stage:

```
# modules/context-and-retrieval/code/retrieval-adv-01/ — COMPLETE, run from that directory
$ python3 retrieve.py --stages

STAGES — recall@1 through the pipeline (n=6 queries)
------------------------------------------------------------------
  lexical only        recall@1 = 3/6
  dense only          recall@1 = 3/6
  RRF fusion          recall@1 = 5/6   recall@3 = 6/6
  + rerank top-3      recall@1 = 6/6
```

run: 2026-08-26 · deterministic; scores are a fixture · 6 queries · `python3 retrieve.py --stages`

Each retriever alone gets 3 of 6; fusion lifts recall@1 to 5 and recall@3 to a full 6; rerank finishes the job at 6 of 6. This module is that climb and the one fusion mistake that flattens it.

## Concepts

Named here so you can find them again; each is built below.

- **Lexical retrieval** — ranking by exact term overlap (BM25-style); strong on rare keywords.
- **Dense retrieval** — ranking by embedding similarity; strong on paraphrase.
- **Complementary failure** — the two retrievers miss on different queries, so each covers only its half.
- **Reciprocal rank fusion (RRF)** — combining rankings by summing 1/(k0 + rank); scale-free.
- **Scale bug** — raw-sum fusion letting the larger-scaled retriever dominate and discard the other.
- **Reranking** — reordering the fused top-k with a precise cross-encoder to lift the gold to rank 1.
- **recall@k** — whether the gold is in the top-k; the metric each stage moves.

## Worked example

<svg viewBox="0 0 700 170" role="img" aria-label="The pipeline architecture. The corpus feeds two parallel retrievers: lexical (BM25) and dense (embeddings). Their two rankings feed into an RRF fusion box, which outputs a top-k candidate pool. The pool feeds a reranker (cross-encoder), which outputs the final top-1. Labels: fusion for recall, rerank for precision.">
  <g font-family="var(--mono)" font-size="8">
    <text x="20" y="16" fill="var(--muted)">the hybrid pipeline: two retrievers, fuse, rerank</text>
    <rect x="30" y="70" width="70" height="26" rx="4" fill="var(--panel)" stroke="var(--line)"></rect><text x="65" y="87" text-anchor="middle" fill="var(--ink)">corpus</text>
    <rect x="150" y="42" width="90" height="24" rx="4" fill="var(--panel)" stroke="var(--line)"></rect><text x="195" y="58" text-anchor="middle" fill="var(--ink)">lexical (BM25)</text>
    <rect x="150" y="100" width="90" height="24" rx="4" fill="var(--panel)" stroke="var(--line)"></rect><text x="195" y="116" text-anchor="middle" fill="var(--ink)">dense (embed)</text>
    <path d="M100 78 L150 54" stroke="var(--muted)" fill="none"></path><path d="M100 88 L150 112" stroke="var(--muted)" fill="none"></path>
    <rect x="290" y="70" width="90" height="26" rx="4" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="335" y="87" text-anchor="middle" fill="var(--acc-ink)">RRF fuse</text>
    <path d="M240 54 L290 78" stroke="var(--muted)" fill="none"></path><path d="M240 112 L290 88" stroke="var(--muted)" fill="none"></path>
    <rect x="420" y="70" width="90" height="26" rx="4" fill="var(--panel)" stroke="var(--line)"></rect><text x="465" y="87" text-anchor="middle" fill="var(--ink)">top-k pool</text>
    <path d="M380 83 L420 83" stroke="var(--muted)"></path>
    <rect x="540" y="70" width="90" height="26" rx="4" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="585" y="87" text-anchor="middle" fill="var(--acc-ink)">rerank</text>
    <path d="M510 83 L540 83" stroke="var(--muted)"></path>
    <text x="335" y="118" text-anchor="middle" fill="var(--s1)" font-size="7">recall</text><text x="585" y="118" text-anchor="middle" fill="var(--s1)" font-size="7">precision</text>
    <text x="120" y="150" fill="var(--muted)">cheap retrievers scan the whole corpus; the expensive reranker runs only on the small fused pool</text>
  </g>
</svg>
^ Two cheap retrievers scan the corpus in parallel; RRF fuses their rankings into a small candidate pool; the expensive reranker reorders only that pool. Fusion owns recall, reranking owns precision, and each stage is sized to its cost.

Source: the hybrid retrieve-and-rerank pipeline that production RAG systems run (lexical + dense with RRF, then a cross-encoder reranker, as in Anthropic's contextual retrieval and many vector-DB stacks); the scores here stand in for real BM25, embedding, and cross-encoder outputs so the per-stage recall is exact and checkable.

Script and fixture: `modules/context-and-retrieval/code/retrieval-adv-01/` — `retrieve.py`, and `queries.json`, six queries over six documents, each doc scored by lexical, dense, and precise retrievers. Every command runs from there.

### The two retrievers, and their complementary blind spots

Both retrievers are a ranking by a per-document score. What differs is which score, and which queries each gets right.

```
# retrieve.py:39-41 — COMPLETE (rank documents by any per-doc score)
def rank_by(query, key):
    """Rank the docs by a per-doc score (lex, dense, or precise), descending, id-tiebroken."""
    return [d for d, _ in sorted(query["docs"].items(), key=lambda kv: (-kv[1][key], kv[0]))]
```

The metric across every stage is recall@k — whether the gold document is in the top-k of a stage's output:

```
# retrieve.py:69-70 — COMPLETE (recall@k over a query set for any ranker)
def recall_at(queries, ranker, at):
    return sum(1 for q in queries if q["gold"] in ranker(q)[:at])
```

That single function scores lexical, dense, fusion, and rerank alike — pass it a ranker and a cutoff and it counts how many golds landed in the top-k. Every number in this module comes from it. Ranking by `lex` gives the lexical retriever, by `dense` the dense one. The fixture's six queries split into three "exact" (the answer shares rare terms) and three "paraphrase" (the answer is worded differently). On the exact queries lexical ranks the gold at the top and dense ranks it lower; on the paraphrase queries it is reversed. So lexical gets recall@1 of 3 of 6 — its three exact queries — and dense gets 3 of 6 — its three paraphrase queries. Neither is bad; each is simply blind to the other's half. The two 3-of-6 scores in the cold open are not two mediocre retrievers, they are two specialists, and the specialties do not overlap.

<svg viewBox="0 0 700 190" role="img" aria-label="A 2x6 grid. Rows: lexical, dense. Columns: q1 to q6 (q1-q3 exact, q4-q6 paraphrase). Lexical row: q1-q3 are hits (filled), q4-q6 misses (empty). Dense row: q1-q3 misses, q4-q6 hits. The two rows are complementary — where one hits the other misses.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">recall@1 by query: lexical and dense are complementary</text>
    <g fill="var(--muted)"><text x="150" y="44">q1</text><text x="220" y="44">q2</text><text x="290" y="44">q3</text><text x="360" y="44">q4</text><text x="430" y="44">q5</text><text x="500" y="44">q6</text></g>
    <text x="120" y="44" text-anchor="end" fill="var(--muted)" font-size="7">exact | para</text>
    <text x="70" y="72" fill="var(--ink)">lexical</text>
    <g><rect x="140" y="58" width="22" height="22" fill="var(--s1)"></rect><rect x="210" y="58" width="22" height="22" fill="var(--s1)"></rect><rect x="280" y="58" width="22" height="22" fill="var(--s1)"></rect><rect x="350" y="58" width="22" height="22" fill="none" stroke="var(--line)"></rect><rect x="420" y="58" width="22" height="22" fill="none" stroke="var(--line)"></rect><rect x="490" y="58" width="22" height="22" fill="none" stroke="var(--line)"></rect></g>
    <text x="540" y="74" fill="var(--muted)" font-size="8">3/6</text>
    <text x="70" y="112" fill="var(--ink)">dense</text>
    <g><rect x="140" y="98" width="22" height="22" fill="none" stroke="var(--line)"></rect><rect x="210" y="98" width="22" height="22" fill="none" stroke="var(--line)"></rect><rect x="280" y="98" width="22" height="22" fill="none" stroke="var(--line)"></rect><rect x="350" y="98" width="22" height="22" fill="var(--s2)"></rect><rect x="420" y="98" width="22" height="22" fill="var(--s2)"></rect><rect x="490" y="98" width="22" height="22" fill="var(--s2)"></rect></g>
    <text x="540" y="114" fill="var(--muted)" font-size="8">3/6</text>
    <text x="140" y="150" fill="var(--muted)" font-size="8">filled = gold at rank 1; every column is hit by exactly one retriever — fusion should get all six</text>
  </g>
</svg>
^ Lexical hits the three exact queries, dense the three paraphrase queries, and no column is hit by both or by neither. That perfect complementarity is why fusing them should, in principle, recover all six — and why using only one throws away half.

### Fusion done right: reciprocal rank fusion

Fusion combines the two rankings. The correct fusion is rank-based: each document scores 1/(k0 + rank) in each retriever, summed.

```
# retrieve.py:46-50 — COMPLETE (reciprocal rank fusion: sum 1/(k0 + rank) across retrievers)
def rrf_fuse(query, k0):
    """Reciprocal rank fusion: sum 1/(k0 + rank) across the lexical and dense rankings."""
    lex, den = rank_by(query, "lex"), rank_by(query, "dense")
    score = {d: 1.0 / (k0 + lex.index(d) + 1) + 1.0 / (k0 + den.index(d) + 1) for d in query["docs"]}
    return [d for d, _ in sorted(score.items(), key=lambda kv: (-kv[1], kv[0]))]
```

Work a single query by hand to see the mechanism. On a paraphrase query the gold is dense-rank 1 and lexical-rank 3, while a lexical-strong distractor is lexical-rank 1 and dense-rank far down:

```
# a paraphrase query, k0=60 (illustrative RRF arithmetic)
#   gold        : dense #1, lex #3  ->  1/61 + 1/63 = 0.01639 + 0.01587 = 0.03226
#   lex distract : lex #1,  dense #8 ->  1/61 + 1/68 = 0.01639 + 0.01471 = 0.03110
#   dense distract: dense #2, lex #6 ->  1/62 + 1/66 = 0.01613 + 0.01515 = 0.03128
#   -> gold wins: strong in BOTH beats strong in ONE
```

The gold is not the single best in either retriever, but it is good in both, and RRF rewards that — the two mid-high ranks sum higher than one top rank plus one poor rank. The key property is that RRF reads only ranks, never raw scores, so the two retrievers' incompatible scales never meet. A document ranked first by lexical and third by dense scores 1/61 + 1/63; a distractor ranked first by dense but eighth by lexical scores 1/61 + 1/68 — lower, because it is strong in only one retriever. So a document that is reasonably good in both retrievers beats a document that is excellent in one and poor in the other, which is exactly what recovers the gold: on each query the gold is decent in both retrievers while each distractor is strong in only one. Fusion lifts recall@1 to 5 of 6 and recall@3 to a full 6 of 6 — every gold is now in the top three, which is the recall the reranker needs.

### The rerank stage: precision on the fused pool

Fusion gets the gold into the top-k; reranking gets it to the top. The reranker reorders the fused top-3 by a precise cross-encoder score.

```
# retrieve.py:61-64 — COMPLETE (rerank the fused top-k by the precise score)
def rerank(query, k0, k=3):
    """Take the fused top-k, reorder by the precise (cross-encoder) score."""
    pool = rrf_fuse(query, k0)[:k]
    return sorted(pool, key=lambda d: (-query["docs"][d]["precise"], d)) + rrf_fuse(query, k0)[k:]
```

The reranker is expensive — it reads the query and each document together — so it runs only on the fused top-3, not the whole corpus, which is the entire reason for the cheap fusion stage in front of it. In the fixture the gold always has the highest precise score, so whenever fusion put the gold in the top-3 (which, at recall@3 of 6 of 6, is always), the reranker lifts it to rank 1. That takes recall@1 from fusion's 5 of 6 to the reranker's 6 of 6: the one query where fusion left the gold at rank 2 or 3 is fixed by the precise reorder. This is the recall-ceiling lesson from the reranking module in its natural habitat — the reranker can only promote what fusion retrieved, and fusion's job was to make sure the gold was there.

<svg viewBox="0 0 700 180" role="img" aria-label="A rising staircase of recall@1 across four stages. Lexical 3/6 and dense 3/6 at the same low level. RRF fusion 5/6 higher. Rerank 6/6 at the top. A dashed line shows RRF recall@3 at 6/6, the ceiling the reranker fills recall@1 up to.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">recall@1 climbing the pipeline (of 6)</text>
    <line x1="60" y1="150" x2="650" y2="150" stroke="var(--grid)"></line>
    <line x1="60" y1="35" x2="650" y2="35" stroke="var(--acc)" stroke-dasharray="4 3"></line><text x="500" y="31" fill="var(--acc-ink)" font-size="8">RRF recall@3 = 6/6 (the pool)</text>
    <rect x="90" y="93" width="70" height="57" fill="var(--s1)"></rect><text x="125" y="88" text-anchor="middle" fill="var(--s1)" font-size="8">lex 3</text>
    <rect x="230" y="93" width="70" height="57" fill="var(--s1)"></rect><text x="265" y="88" text-anchor="middle" fill="var(--s1)" font-size="8">dense 3</text>
    <rect x="370" y="55" width="70" height="95" fill="var(--acc)"></rect><text x="405" y="50" text-anchor="middle" fill="var(--acc-ink)" font-size="8">RRF 5</text>
    <rect x="510" y="35" width="70" height="115" fill="var(--s2)"></rect><text x="545" y="30" text-anchor="middle" fill="var(--s2)" font-size="8">rerank 6</text>
    <g fill="var(--muted)" text-anchor="middle" font-size="8"><text x="125" y="165">lexical</text><text x="265" y="165">dense</text><text x="405" y="165">+ fusion</text><text x="545" y="165">+ rerank</text></g>
  </g>
</svg>
^ Each stage lifts recall@1: the two retrievers tie low, fusion jumps to 5, rerank tops out at 6. The dashed line is fusion's recall@3 — the pool the reranker works within — and rerank fills recall@1 right up to it.

### The scale bug: raw-sum fusion discards a retriever

Now the mistake that flattens the pipeline. The obvious fusion — add the two scores — is wrong, because the scores are on different scales.

```
# retrieve.py:53-56 — COMPLETE (the bug: add raw scores, letting the larger scale dominate)
def rawsum_fuse(query):
    """The bug: add the raw lexical and dense scores. The larger scale (lexical) dominates."""
    score = {d: v["lex"] + v["dense"] for d, v in query["docs"].items()}
    return [d for d, _ in sorted(score.items(), key=lambda kv: (-kv[1], kv[0]))]
```

Lexical scores are term counts, ranging up to 14 here; dense scores are cosines, in 0 to 1. Add them and the lexical value dwarfs the dense value, so the sum is essentially the lexical score with a rounding wobble, and the fused ranking is the lexical ranking. Run it against RRF:

```
# $ python3 retrieve.py --fusion
#   RRF fusion    recall@1 = 5/6
#   raw-sum fusion recall@1 = 3/6  (same as lexical alone -- dense half discarded)
```

run: 2026-08-26 · deterministic · `python3 retrieve.py --fusion`

<svg viewBox="0 0 700 160" role="img" aria-label="Two number lines showing the scale mismatch. Lexical scores span 0 to 14 (a long axis). Dense scores span 0 to 1 (a tiny axis drawn to the same physical width for contrast). When summed, the lexical magnitude dominates, so the combined ranking follows lexical. Two recall bars: RRF 5/6, raw-sum 3/6.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">why raw-sum fails: the scales do not match</text>
    <text x="40" y="42" fill="var(--s1)">lexical</text><line x1="120" y1="38" x2="620" y2="38" stroke="var(--s1)" stroke-width="2"></line><text x="628" y="41" fill="var(--s1)" font-size="8">0–14</text>
    <text x="40" y="66" fill="var(--s2)">dense</text><line x1="120" y1="62" x2="155" y2="62" stroke="var(--s2)" stroke-width="2"></line><text x="628" y="65" fill="var(--s2)" font-size="8">0–1</text>
    <text x="120" y="90" fill="var(--muted)" font-size="8">lex + dense ≈ lex — the dense contribution is a rounding wobble</text>
    <text x="40" y="126" fill="var(--ink)">recall@1:</text>
    <rect x="120" y="114" width="250" height="16" fill="var(--s1)"></rect><text x="378" y="127" fill="var(--s1)" font-size="8">RRF 5/6</text>
    <rect x="120" y="136" width="150" height="14" fill="var(--s2)"></rect><text x="278" y="147" fill="var(--s2)" font-size="8">raw-sum 3/6 (= lexical)</text>
  </g>
</svg>
^ The lexical axis is fourteen times the dense axis, so their sum is essentially the lexical score, and raw-sum fusion drops to lexical's recall@1 of 3. RRF, reading only ranks, is immune to the scale gap and reaches 5.

Raw-sum fusion scores 3 of 6 — identical to lexical alone. It ran both retrievers and then threw the dense one away, because on the combined scale the dense contribution was noise next to the lexical counts. This is the subtle, expensive failure: the system looks like a hybrid retriever, it computes both scores, it "fuses" them, and it performs exactly like the lexical retriever it was supposed to improve on. Only RRF, by fusing ranks instead of scores, actually combines the two — which is why every production fusion is rank-based or careful score normalization, never a raw sum.

**A hybrid pipeline fuses complementary retrievers for recall and reranks for precision, but the fusion must combine ranks, not raw scores — lexical counts and dense cosines are on different scales, so raw-sum fusion lets the larger scale dominate and discards a retriever, collapsing the hybrid back to its lexical half.**

### The self-test

The `--check` mode asserts the whole pipeline: the retrievers are complementary, fusion beats both and fills the pool, rerank lifts recall@1 to full, and raw-sum fusion collapses to lexical.

```
# $ python3 retrieve.py --check
#   neither retriever alone is complete = True (lex 3, dense 3 of 6)
#   RRF fusion beats both single retrievers at recall@1 = True (5 > 3, 3)
#   RRF fusion gets every gold into the top-3 = True (recall@3 = 6/6)
#   rerank lifts recall@1 to full = True (6/6, up from 5)
#   raw-sum fusion collapses to lexical (the scale bug) = True (3, = lexical, < RRF 5)
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 retrieve.py --check`

The two contract assertions are the fusion win and the handoff to the reranker:

```
# retrieve.py:113-119 — COMPLETE (fusion beats both retrievers and fills the rerank pool)
    rrf1 = recall_at(qs, lambda q: rrf_fuse(q, k0), 1)
    fusion_beats = rrf1 > lex1 and rrf1 > den1
    print("  RRF fusion beats both single retrievers at recall@1 = %s (%d > %d, %d)" % (fusion_beats, rrf1, lex1, den1))

    rrf3 = recall_at(qs, lambda q: rrf_fuse(q, k0), 3)
    fusion_recall = rrf3 == n
    print("  RRF fusion gets every gold into the top-3 = %s (recall@3 = %d/%d)" % (fusion_recall, rrf3, n))
```

The `fusion_beats` line is the pipeline's reason to exist: fusion must exceed both single retrievers, or composing them bought nothing. The `fusion_recall` line is the handoff contract — fusion must get every gold into the top-3, because that is the pool the reranker operates on, and a gold fusion missed is a gold the reranker can never recover. The scale-bug assertion pins raw-sum fusion to lexical's score, below RRF's:

```
# retrieve.py:125-126 — COMPLETE (raw-sum fusion collapses to the lexical retriever)
    raw1 = recall_at(qs, rawsum_fuse, 1)
    rawsum_bug = raw1 == lex1 and raw1 < rrf1
```

And `rawsum_bug` proves the scale failure is real: raw-sum fusion must equal the lexical score and fall below RRF, so the test demonstrates that a plausible fusion silently discards half the pipeline.

### The running tally

| stage | recall@1 | recall@3 | what it added |
|---|---|---|---|
| lexical only | 3/6 | — | exact-term queries |
| dense only | 3/6 | — | paraphrase queries |
| RRF fusion | 5/6 | 6/6 | both halves, scale-free |
| + rerank top-3 | 6/6 | — | precision on the fused pool |
| raw-sum fusion (bug) | 3/6 | — | nothing — dense discarded |

Read the column of recall@1 down the correct stages: 3, 3, 5, 6 — each stage strictly improving, and each doing a distinct job. Fusion is where recall is won, taking two 3s to a 5 (and a full 6 at rank 3); reranking is where precision is won, taking the fused 5 to 6 by reordering within the pool fusion supplied. The bug row is the cautionary one: it sits at 3, tied with lexical alone, because a fusion that ignores scale is not a fusion. The architecture is only as good as its glue, and the glue is rank-based combination.

### What we did not settle

This is the core pipeline; production adds layers on every stage. The retrievers themselves are richer — real lexical retrieval is BM25 with tuned term weighting, real dense retrieval needs the chunking and embedding choices from earlier modules, and the two can be joined at the index level (a single query over a hybrid index) rather than fused after. Fusion has variants — weighted RRF when one retriever is known better, or learned fusion — and score normalization (min-max, z-score) is an alternative to rank fusion when calibrated scores exist. The reranker's pool size k trades recall against latency, the ceiling tradeoff from the reranking module, and diversity (MMR) may be applied after reranking so the final context is not redundant. And the whole thing must be measured on your own labelled query set, not assumed. The invariant across all of it: retrieve broadly and cheaply, fuse scale-free, rerank precisely on a small pool, and measure recall at each stage.

## Build

The build in one paragraph: run a lexical and a dense retriever over the corpus; fuse their rankings with reciprocal rank fusion — combining ranks, never raw scores, so the scales cannot fight — to a candidate pool; rerank that pool with a precise cross-encoder for the final order; and measure recall@k after each stage so you can see where recall is won (fusion) and where precision is won (rerank). Never raw-sum scores on different scales, size the rerank pool to the recall you need, and evaluate on your own labelled queries.

We opened on the staged climb. The number that proves fusion did its job is recall@3, the pool the reranker inherits:

```
# modules/context-and-retrieval/code/retrieval-adv-01/ — COMPLETE, run from that directory
$ python3 retrieve.py --stages
  RRF fusion          recall@1 = 5/6   recall@3 = 6/6
  + rerank top-3      recall@1 = 6/6
```

Now build your own. Take a real query set with gold documents, run lexical and dense retrieval, fuse with RRF, and rerank the top-k. Your number to beat is not any single retriever's recall; it is **the recall@1 of the full pipeline against the best single retriever, and the recall@3 fusion hands the reranker** — plus a raw-sum fusion for contrast, which should collapse to your dominant-scale retriever. Bring back recall at every stage. Good luck.

## Definition of done

- [ ] A lexical and a dense retriever over the same corpus, shown to fail on complementary queries
- [ ] Reciprocal rank fusion of the two rankings (combining ranks, not scores)
- [ ] Confirmation fusion beats both single retrievers and gets the gold into the top-k
- [ ] A cross-encoder rerank of the fused top-k, lifting recall@1
- [ ] recall@1 and recall@3 measured at every stage
- [ ] A raw-sum fusion shown to collapse to the dominant-scale retriever
- [ ] `python3 retrieve.py --check` printing SELF-TEST PASS: complementary, fusion-beats, fusion-recall, rerank-lifts, rawsum-bug
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why does neither lexical nor dense retrieval alone suffice on a mixed query set, and what does each miss?
2. Why must fusion combine ranks rather than raw scores? What specifically goes wrong with a raw sum?
3. Fusion won recall and reranking won precision. Explain the division of labor and why the reranker runs only on the fused top-k.
4. Fusion's recall@3 was 6/6 but recall@1 was 5/6. Why is the recall@3 the number that matters for the reranker?
5. Your own pipeline was measured stage by stage. What was recall@1 for each retriever, for fusion, and after reranking, and what did raw-sum fusion score?

## External resources

- Cormack, Clarke & Buettcher, *Reciprocal Rank Fusion* (2009) — my summary: the RRF method this module fuses with, and why rank-based combination outperforms score combination across retrievers; read it for the derivation and the choice of k0.
- Anthropic, *Introducing Contextual Retrieval* — https://www.anthropic.com/news/contextual-retrieval — my summary: a production hybrid pipeline (embeddings + BM25, fused, then reranked) with measured failure-rate reductions; read it for the real system this module abstracts.
- This hub, *retrieval-inter-02*, *retrieval-inter-04*, *retrieval-inter-05* — the lexical-dense head-to-head, rank fusion, and reranking modules this capstone composes; read them for each stage in isolation before seeing them assembled here.
