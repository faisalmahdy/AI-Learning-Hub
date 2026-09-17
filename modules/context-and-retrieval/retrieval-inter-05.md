---
id: retrieval-inter-05
title: Rerank for precision — but the reranker can only reorder what it's given
topic: context-and-retrieval
level: intermediate
status: ready
time: 8-10h
summary: A cheap first-stage retriever pulls k candidates and an expensive reranker reorders them for precision, but the reranker can only promote a document the first stage returned — so with k=1 the pipeline scores 2 of 5 even though the reranker would nail every query, because three golds never entered the pool. Widen the first stage to k=3 and recall@k reaches 5 of 5, the pipeline follows to 5 of 5, and pipeline hit@1 never once exceeds first-stage recall@k, which is the ceiling the reranker cannot break.
eli5: A quick resume filter passes a few candidates to a careful interview. The interview can only hire someone it actually meets — so if the filter throws out the best person, no amount of interviewing gets them back. Let the filter pass enough people, then interview hard.
---

## Why this module

The earlier retrieval modules built one-stage retrieval: score every document, return the top. Production retrieval is two stages, because the two things you want — high recall and high precision — pull toward different, incompatible retrievers. A cheap, fast retriever (approximate nearest-neighbour over quantized vectors) can scan a huge corpus and pull a pool of plausible candidates, but its ranking is coarse. An expensive, precise reranker (a cross-encoder that reads the query and each document together) ranks beautifully but is far too slow to run over the whole corpus. So you compose them: the cheap stage proposes a pool, the precise stage disposes within it. This module builds that pipeline and the one property that governs it.

The property is a hard ceiling: a reranker can only reorder the pool it is handed. If the cheap first stage's top-k does not contain the right document, no reranker — however good — can promote a document it never received. This makes the first-stage pool size, k, a recall dial, and it is the most common way a two-stage system is quietly broken: someone tunes the expensive reranker, sees mediocre end-to-end numbers, and blames the reranker, when the real fault is a first stage set to return too few candidates, starving the reranker of the answer. Pipeline accuracy is bounded by first-stage recall@k, full stop, and knowing that tells you which knob to turn.

You need the retrieval-measurement instinct from `retrieval-basic-01`. Everything runs offline against a candidate-score fixture — each candidate carries a cheap score and a precise score, standing in for real ANN and cross-encoder outputs — stdlib Python 3, `$0.00`. The instinct to unlearn is that a better reranker fixes a retrieval pipeline. A better reranker cannot see past the pool; only a wider pool can raise the ceiling it works under.

Here is the pipeline as the pool grows:

```
# modules/context-and-retrieval/code/retrieval-inter-05/ — COMPLETE, run from that directory
$ python3 rerank.py --sweep

SWEEP — first-stage recall@K vs pipeline hit@1 as the pool grows
------------------------------------------------------------------
  K    stage1 recall@K   pipeline hit@1
  1    2/5              2/5
  2    4/5              4/5
  3    5/5              5/5
  5    5/5              5/5
```

run: 2026-08-25 · deterministic; candidate scores are a fixture · 5 queries · `python3 rerank.py --sweep`

At k=1 the pipeline gets 2 of 5, not because the reranker is weak — it is perfect here — but because three of the golds never made it into a one-document pool. Widen the pool and the pipeline climbs in lockstep with first-stage recall, and never above it. This module is that lockstep and the ceiling it reveals.

## Concepts

Named here so you can find them again; each is built below.

- **First stage** — a cheap, recall-oriented retriever that pulls a pool of k candidates from the whole corpus.
- **Reranker** — an expensive, precise scorer that reorders the pool; too slow to run over the corpus.
- **Pool size k** — how many candidates the first stage keeps; the recall dial.
- **recall@k** — whether the gold document is in the first stage's top-k; the ceiling.
- **Pipeline hit@1** — whether the reranked top-1 is the gold; bounded by recall@k.
- **The ceiling** — a reranker cannot promote a document the first stage did not return.

## Worked example

Source: the labs' hybrid retrieval work and the general two-stage pattern (ANN retrieve, cross-encoder rerank) that production RAG uses; the candidate scores here stand in for a real first-stage and reranker so the ceiling is exact and checkable.

Script and fixture: `modules/context-and-retrieval/code/retrieval-inter-05/` — `rerank.py`, and `candidates.json`, five queries whose candidates each carry a cheap score and a precise score. Every command runs from there.

### The frame: a resume filter feeding an interview

Picture hiring in two stages. A cheap resume filter skims a thousand applicants fast and passes a shortlist to an expensive interview panel that assesses each carefully. The panel is excellent — give it the right person and it hires them. But the panel only ever meets the shortlist. If the filter, being crude, drops the best applicant, the panel never sees them, and no amount of interviewing skill recovers a candidate who was filtered out. The end-to-end quality of your hiring is capped by whether the filter's shortlist contains the best person — the filter's recall — not by how good the interview is.

Retrieval is that funnel. The first-stage retriever is the resume filter; the reranker is the interview panel. The pool size k is how long the shortlist is. Make it too short and the filter's crudeness throws out the answer before the precise stage ever scores it. The whole module is seeing that the reranker's excellence is wasted below the ceiling the filter sets, and that the fix is a longer shortlist, not a better panel.

### The first stage: cheap, coarse, recall-oriented

The first stage ranks candidates by their cheap score and keeps the top-k.

```
# rerank.py:37-43 — COMPLETE (the cheap stage orders by the approximate score)
def stage1_ranked(query):
    """The cheap first stage orders candidates by their cheap (approximate) score."""
    return sorted(query["candidates"], key=lambda c: (-c["cheap"], c["id"]))


def stage1_topk(query, k):
    return [c["id"] for c in stage1_ranked(query)[:k]]
```

Its recall depends entirely on k. Look at what it keeps at k=1:

```
# $ python3 rerank.py --stage1 1
#   which gym day          pool=['a'] gold=b MISSED
#   coffee preference      pool=['a'] gold=a IN
#   flight departure time  pool=['a'] gold=a ... MISSED (gold c)
#   bill due date          pool=['a'] gold=a IN
#   dentist appointment ti pool=['a'] gold=b MISSED
#   recall@1 = 2/5 -- the ceiling on what any reranker can achieve.
```

run: 2026-08-25 · fixture · `python3 rerank.py --stage1 1`

At k=1 the cheap stage's coarse ranking puts the gold first for only two of five queries. For the other three the gold has a lower cheap score — it is a document the precise reranker loves but the approximate retriever ranked second or third — so a one-document pool excludes it. That "recall@1 = 2/5" is not a statement about the reranker; it is the ceiling the reranker will run into.

### The reranker: precise, within the pool only

The pipeline takes the first stage's top-k and reranks that pool by the precise score.

```
# rerank.py:46-50 — COMPLETE (retrieve k, then rerank the pool by the precise score)
def pipeline_top1(query, k):
    """Take the first stage's top-k, then rerank that pool by the precise score."""
    pool = stage1_ranked(query)[:k]
    best = max(pool, key=lambda c: (c["precise"], -ord(c["id"][0])))
    return best["id"]
```

The reranker is excellent — in this fixture the gold always has the highest precise score, so whenever the gold is in the pool the reranker puts it first. But "whenever the gold is in the pool" is the whole catch. At k=1 the pool is one document, so the reranker has nothing to reorder; it returns the cheap stage's single pick, and the pipeline scores exactly what the cheap stage scored: 2 of 5. The precise stage's excellence is completely wasted, because it was starved.

Watch it fail at k=1, where every pool is a single document:

```
# $ python3 rerank.py --pipeline 1
#   which gym day          rerank top=a  <-- wrong
#   coffee preference      rerank top=a  ok
#   flight departure time  rerank top=a  <-- wrong
#   bill due date          rerank top=a  ok
#   dentist appointment ti rerank top=a  <-- wrong
#   pipeline hit@1 = 2/5 at k=1.
```

run: 2026-08-25 · fixture · `python3 rerank.py --pipeline 1`

Three queries return the same wrong document `a` — the one the cheap stage happened to rank first. The reranker is present for all five and changes nothing, because a one-item pool has nothing to reorder. Those three wrongs are exactly the three golds the cheap stage dropped: the reranker's failure is the first stage's, wearing the reranker's name.

<svg viewBox="0 0 700 180" role="img" aria-label="A two-stage funnel. The whole corpus flows into a cheap first stage that keeps top-k. That pool flows into an expensive reranker that outputs the top-1. An arrow shows that if the gold is dropped by the first stage, the reranker never sees it.">
  <g font-family="var(--mono)" font-size="10">
    <rect x="20" y="60" width="90" height="34" rx="5" fill="var(--panel)" stroke="var(--line)"></rect><text x="65" y="81" text-anchor="middle" fill="var(--ink)">corpus</text>
    <rect x="150" y="55" width="120" height="44" rx="5" fill="var(--panel)" stroke="var(--line)"></rect><text x="210" y="73" text-anchor="middle" fill="var(--ink)">cheap stage</text><text x="210" y="88" text-anchor="middle" fill="var(--muted)" font-size="8">keep top-k</text>
    <rect x="330" y="55" width="120" height="44" rx="5" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="390" y="73" text-anchor="middle" fill="var(--acc-ink)">reranker</text><text x="390" y="88" text-anchor="middle" fill="var(--acc-ink)" font-size="8">precise, slow</text>
    <rect x="500" y="60" width="90" height="34" rx="5" fill="var(--panel)" stroke="var(--s1)"></rect><text x="545" y="81" text-anchor="middle" fill="var(--s1)">top-1</text>
    <line x1="110" y1="77" x2="148" y2="77" stroke="var(--muted)"></line><line x1="270" y1="77" x2="328" y2="77" stroke="var(--muted)"></line><line x1="450" y1="77" x2="498" y2="77" stroke="var(--muted)"></line>
    <text x="210" y="120" fill="var(--muted)" font-size="8">k too small: gold dropped here</text>
    <path d="M 210 108 L 210 99" stroke="var(--s2)" stroke-width="1.2"></path>
    <text x="330" y="140" fill="var(--s2)" font-size="9">the reranker never receives what the cheap stage dropped -> the ceiling</text>
  </g>
</svg>
^ The pipeline is a funnel: the cheap stage narrows the corpus to a pool, the reranker orders the pool. Everything the cheap stage drops is invisible to the reranker, so the pool is the reranker's entire world — and a pool too small to hold the gold caps the whole system.

### Measuring the ceiling

Two metrics: first-stage recall@k (is the gold in the pool) and pipeline hit@1 (is the reranked top the gold).

```
# rerank.py:55-60 — COMPLETE (first-stage recall, and end-to-end hit@1)
def recall_at_k(queries, k):
    return sum(1 for q in queries if q["gold"] in stage1_topk(q, k))


def pipeline_hit1(queries, k):
    return sum(1 for q in queries if pipeline_top1(q, k) == q["gold"])
```

The sweep from the cold open shows them moving together: recall@k and pipeline hit@1 are 2, 4, 5, 5 across k = 1, 2, 3, 5 — identical at every k, because this reranker is perfect and so realizes exactly the recall the first stage allows. The general law is the inequality, not the equality: pipeline hit@1 can be *below* recall@k if the reranker is imperfect, but it can never be *above* it. Recall@k is the ceiling; the reranker's quality decides how close to it you get.

<svg viewBox="0 0 700 180" role="img" aria-label="Two lines rising with k: first-stage recall@k (2,4,5,5) and pipeline hit@1 (2,4,5,5), on top of each other. A shaded ceiling region above shows hit@1 can never exceed recall@k.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">pipeline hit@1 rises with the pool, and never crosses the recall ceiling</text>
    <line x1="60" y1="150" x2="640" y2="150" stroke="var(--grid)"></line>
    <line x1="60" y1="30" x2="60" y2="150" stroke="var(--grid)"></line>
    <polyline points="110,110 250,66 390,42 560,42" fill="none" stroke="var(--s2)" stroke-width="3"></polyline>
    <text x="400" y="36" fill="var(--s2)" font-size="8">recall@k (ceiling)</text>
    <polyline points="110,113 250,69 390,45 560,45" fill="none" stroke="var(--s1)" stroke-width="1.6" stroke-dasharray="4 3"></polyline>
    <text x="400" y="58" fill="var(--s1)" font-size="8">pipeline hit@1</text>
    <g fill="var(--muted)" text-anchor="middle"><text x="110" y="165">k=1</text><text x="250" y="165">k=2</text><text x="390" y="165">k=3</text><text x="560" y="165">k=5</text></g>
    <g fill="var(--muted)" text-anchor="end"><text x="54" y="150">2</text><text x="54" y="42">5</text></g>
  </g>
</svg>
^ The two curves rise together and the pipeline never crosses the recall ceiling above it. A better reranker lifts the dashed line toward the solid one; only a wider pool lifts the solid line itself.

**A reranker can only reorder the pool it is handed, so the pipeline's accuracy is capped by first-stage recall@k — widen the first stage for recall, then rerank for precision, and never blame the reranker for a pool that never held the answer.**

The self-test confirms the ceiling and the fix:

```
# $ python3 rerank.py --check
#   pipeline hit@1 <= recall@K at every K = True
#   widening K=1 -> K=3 raises pipeline hit@1 = True (2 -> 5)
#   at K=3 recall is full (5/5) and rerank hit@1 is full (5/5) = True
#   reranking a wide pool beats the cheap stage's own top-1 = True (5 vs 2)
#   SELF-TEST PASS ...
```

run: 2026-08-25 · deterministic · `python3 rerank.py --check`

### The running tally

| pool size k | first-stage recall@k | pipeline hit@1 | what happened |
|---|---|---|---|
| 1 | 2/5 | 2/5 | three golds never entered the pool |
| 2 | 4/5 | 4/5 | one more gold in the pool, reranked to the top |
| 3 | 5/5 | 5/5 | every gold present, reranker nails all |

<svg viewBox="0 0 700 170" role="img" aria-label="Three pairs of bars, one pair per pool size k=1,2,3. At each k the first-stage recall@k bar and the pipeline hit@1 bar are equal height: 2 and 2 at k=1, 4 and 4 at k=2, 5 and 5 at k=3. The bars grow with k.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">recall@k and pipeline hit@1, equal at every k, climbing together</text>
    <line x1="60" y1="140" x2="660" y2="140" stroke="var(--grid)"></line>
    <rect x="110" y="92" width="34" height="48" fill="var(--s2)"></rect><rect x="150" y="92" width="34" height="48" fill="var(--s1)"></rect>
    <text x="147" y="155" text-anchor="middle" fill="var(--muted)">k=1</text><text x="147" y="86" text-anchor="middle" fill="var(--muted)" font-size="8">2 / 2</text>
    <rect x="320" y="44" width="34" height="96" fill="var(--s2)"></rect><rect x="360" y="44" width="34" height="96" fill="var(--s1)"></rect>
    <text x="357" y="155" text-anchor="middle" fill="var(--muted)">k=2</text><text x="357" y="38" text-anchor="middle" fill="var(--muted)" font-size="8">4 / 4</text>
    <rect x="530" y="20" width="34" height="120" fill="var(--s2)"></rect><rect x="570" y="20" width="34" height="120" fill="var(--s1)"></rect>
    <text x="567" y="155" text-anchor="middle" fill="var(--muted)">k=3</text><text x="567" y="14" text-anchor="middle" fill="var(--muted)" font-size="8">5 / 5</text>
    <rect x="620" y="30" width="10" height="10" fill="var(--s2)"></rect><text x="634" y="39" fill="var(--muted)" font-size="8">recall@k</text>
    <rect x="620" y="46" width="10" height="10" fill="var(--s1)"></rect><text x="634" y="55" fill="var(--muted)" font-size="8">hit@1</text>
  </g>
</svg>
^ The paired bars are equal at every k because this reranker is perfect; the point is that both grow only as k grows. Nothing about the reranker moved between the panels — only the pool it was allowed to see.

The reranker never changed; only how many candidates it was allowed to see. At k=1 it scored a perfect reranker at 2 of 5 and made it look mediocre; at k=3 the same reranker scored 5 of 5. If you had been tuning the reranker at k=1, every improvement would have shown no end-to-end gain, and you would have concluded reranking does not help — the exact wrong conclusion, drawn from the exact right measurement read at the wrong stage. The first move in any two-stage system is to confirm first-stage recall@k is high; only then does reranker quality translate into pipeline quality.

### What we did not settle

The fixture gives the reranker a perfect precise score, so pipeline hit@1 equals recall@k; a real cross-encoder is imperfect, so the pipeline sits somewhere below the ceiling, and both knobs — pool size and reranker quality — matter, in that order. Three real details we skipped: widening k is not free, since the reranker cost is linear in pool size, so k trades recall against latency and you tune it to the smallest pool that captures nearly all the recall; recall@k is measured against gold labels here, which in production you estimate on a labelled eval set and then trust in the wild; and a reranker can *reintroduce* a first-stage error if it is miscalibrated on out-of-pool-distribution candidates, so a wider pool has a small precision cost too. The dial here is k against a perfect reranker; the real tuning is k and reranker quality against latency.

## Build

The pipeline in one paragraph: retrieve a pool of k candidates with a cheap, recall-oriented first stage; rerank that pool with an expensive, precise scorer and take the top; measure first-stage recall@k and pipeline hit@1 separately, and set k to the smallest pool where recall@k captures nearly all the gold; and never tune the reranker before confirming the first stage's recall, because the pipeline can never beat it. Report both numbers, always.

We opened on the sweep. The pool size that unlocks the reranker:

```
# modules/context-and-retrieval/code/retrieval-inter-05/ — COMPLETE, run from that directory
$ python3 rerank.py --sweep
  3    5/5              5/5
```

Now measure your own pipeline. Take a real first stage and reranker, and plot first-stage recall@k and pipeline hit@1 as you widen k. Your number to beat is not pipeline hit@1 alone — it is **the gap between pipeline hit@1 and first-stage recall@k**: if the gap is large, improve the reranker; if recall@k itself is low, widen k. Set k to the knee where recall@k stops rising, then rerank. Bring back both curves and the k you chose. Good luck.

## Definition of done

- [ ] A two-stage pipeline: a cheap first stage returning a pool of k, and a precise reranker over the pool
- [ ] First-stage recall@k and pipeline hit@1 measured separately across a range of k
- [ ] Confirmation that pipeline hit@1 never exceeds first-stage recall@k
- [ ] Your own candidate set (or real retriever + reranker), with gold labels per query
- [ ] The k=1 pipeline kept for contrast, so the starved-reranker failure is visible
- [ ] `python3 rerank.py --check` printing SELF-TEST PASS: capped by recall, widening helps, full at the right k, beats the cheap stage
- [ ] Both curves recorded, and the k chosen at the recall knee
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. A perfect reranker scored 2 of 5 end-to-end. Explain how a perfect reranker produces a mediocre pipeline, and the one number that predicted it.
2. State the ceiling law relating pipeline hit@1 and first-stage recall@k, and why the inequality only goes one way.
3. An engineer tunes the reranker and sees no end-to-end improvement. What is the likely cause and the diagnostic that would reveal it?
4. Why is widening k not simply "always better"? Name the cost it trades against recall.
5. Your own pipeline was swept over k. Where was the recall knee, and how large was the gap between pipeline hit@1 and recall@k there?

## External resources

- Anthropic, *Introducing Contextual Retrieval* — https://www.anthropic.com/news/contextual-retrieval — my summary: a production two-stage retrieval system (embeddings + BM25, then a reranker) with measured failure-rate reductions; read it for the real first-stage-then-rerank pipeline this module abstracts, and for how much reranking buys once recall is high.
- Nogueira & Cho, *Passage Re-ranking with BERT* (2019) — https://arxiv.org/abs/1901.04085 — my summary: the cross-encoder reranker that reads query and passage together, the "precise stage" here; read it for why it is accurate and why it is too slow to run over a whole corpus, which is the entire reason for a cheap first stage.
- This hub, *retrieval-basic-01* — modules/context-and-retrieval/retrieval-basic-01.md — my summary: measuring retrieval with hit@1 and rank-aware metrics; read it for the recall@k and hit@1 measurements this module builds a two-stage pipeline on top of.
