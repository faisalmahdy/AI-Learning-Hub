---
id: retrieval-inter-14
title: Fuse retrievers by rank, not raw score — or one retriever's score scale outvotes the other
topic: context-and-retrieval
level: intermediate
status: ready
time: 21 min
summary: Hybrid retrieval must combine a lexical ranking (BM25, scores ~0-30) and a dense one (cosine, 0-1), and adding the scores lets the larger scale dominate — the fused order is essentially the lexical order, and rescaling either retriever changes the winner. Reciprocal rank fusion keeps only the ranks (sum 1/(k+rank)), so units cancel and consensus wins. On a fixture where the answer ranks 2nd in both retrievers, raw-score fusion crowns a lexical distractor (and flips to a dense one when scores are rescaled); RRF crowns the answer and never moves.
eli5: Two judges score a contest, but one rates out of 30 and the other out of 1. If you just add their scores, the out-of-30 judge decides everything and the other barely matters. Better: ask each judge only for their ranking — first, second, third — and combine those. Now both judges count equally, and the entry they both liked wins.
---

## Why this module

Combining two retrievers by adding their scores quietly hands the decision to whichever one uses bigger numbers.

Hybrid retrieval runs two retrievers over the same corpus and has to merge their results into one ranking. A lexical retriever like BM25 scores documents on a scale that might run from 0 to 30; a dense retriever scores by cosine similarity on a scale from 0 to 1. Both rankings are meaningful, and the promise of hybrid search is that fusing them beats either alone — lexical catches exact terms, dense catches paraphrases, and together they cover both. The question is how to fuse, and the obvious answer is to add each document's two scores and sort. That answer is broken.

It is broken because the two scales are not comparable. BM25's numbers are tens of times larger than cosine's, so when you add them, the lexical score dominates every sum — a document's BM25 score of 28 plus a cosine of 0.3 is 28.3, and the 0.3 is a rounding error. The fused ranking is therefore just the lexical ranking wearing a disguise; the dense retriever's opinion, the whole reason you added it, barely counts. And because the outcome depends on the raw magnitudes, it depends on the arbitrary units each retriever happens to use: rescale one retriever's scores — which changes no ranking — and the fused winner can change. A fusion whose answer moves when you multiply one input by a constant is not measuring agreement; it is measuring units.

Reciprocal rank fusion fixes this by throwing the scores away and keeping only the ranks. Each retriever contributes 1 divided by (k plus the document's rank), where k is a small constant, and the contributions are summed across retrievers. A document near the top of both lists collects two large contributions and scores high; a document ranked first in one list but buried in the other collects one large and one tiny contribution and cannot win. Only rank order enters the formula, so the score scales cancel completely — RRF gives the same answer whatever units the retrievers use — and it rewards consensus, which is the thing you actually wanted to fuse on.

On the fixture the true answer ranks second in both retrievers — strong agreement, first in neither. A lexical distractor ranks first on BM25 (score 28) but fourth on cosine; a dense distractor is the mirror image. Raw-score fusion crowns the lexical distractor, because its BM25 score of 28 swamps everything, and rescaling the dense scores flips the winner to the dense distractor. RRF crowns the true answer and does not budge when the scores are rescaled.

**Adding retriever scores lets the larger score scale dominate the fusion and makes the result depend on arbitrary units; reciprocal rank fusion uses only rank order, so the scales cancel and the document both retrievers rank highly wins — even when it is first in neither.**

## Concepts

The core problem is that a score is only meaningful within its own retriever. BM25 scores and cosine scores both order documents correctly for their own retriever, but there is no exchange rate between them — a BM25 score of 14 does not "equal" a cosine of 0.47 in any principled sense. Adding them assumes an exchange rate of one-to-one, which is arbitrary and, given the scale difference, wildly favors the bigger-numbered retriever. You could try to fix this by normalizing each retriever's scores to a common range, but that is fragile: min-max normalization is thrown off by a single outlier score, and z-scoring assumes a distribution shape the scores may not have. Score fusion keeps forcing you to make the incomparable comparable.

Rank fusion sidesteps the whole problem by using the one thing the two retrievers express in the same language: rank. Being ranked first means the same thing for BM25 and for cosine — most relevant, according to that retriever — regardless of the scores behind it. RRF's formula, 1 over (k plus rank), turns each retriever's ranking into a contribution that decays with rank, and sums them. Because rank is unitless, the sum is unitless, and no retriever can dominate by using bigger numbers. The method is deliberately blind to how confident a retriever claims to be; it listens only to the order it puts documents in.

<svg role="img" aria-label="Two number lines: BM25 scores spread across 0 to 30 while cosine scores are squeezed near 0 to 1, so their sum is dominated by the BM25 axis" viewBox="0 0 470 165" width="470" height="165">
  <rect x="0" y="0" width="470" height="165" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">the two score scales, drawn to the same axis</text>
  <line x1="40" y1="60" x2="440" y2="60" stroke="var(--line)"/>
  <text x="40" y="50" font-family="var(--mono)" font-size="8" fill="var(--s2)">lexical (BM25): 0 .. 30</text>
  <g fill="var(--s2)"><circle cx="80" cy="60" r="4"/><circle cx="200" cy="60" r="4"/><circle cx="330" cy="60" r="4"/><circle cx="410" cy="60" r="4"/></g>
  <text x="70" y="78" font-family="var(--mono)" font-size="8" fill="var(--muted)">3</text>
  <text x="400" y="78" font-family="var(--mono)" font-size="8" fill="var(--muted)">28</text>
  <line x1="40" y1="120" x2="440" y2="120" stroke="var(--line)"/>
  <text x="40" y="110" font-family="var(--mono)" font-size="8" fill="var(--s1)">dense (cosine): 0 .. 1</text>
  <g fill="var(--s1)"><circle cx="47" cy="120" r="4"/><circle cx="52" cy="120" r="4"/><circle cx="55" cy="120" r="4"/><circle cx="58" cy="120" r="4"/></g>
  <text x="64" y="124" font-family="var(--mono)" font-size="8" fill="var(--muted)">all cosine scores live in this sliver</text>
  <text x="120" y="145" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">sum ≈ BM25 + a rounding error → lexical decides</text>
</svg>
^ Drawn to one axis, the entire cosine range fits inside the gap between two BM25 scores, so adding the two makes the cosine term a rounding error and the lexical retriever decides every fusion.

The constant k controls how sharply the contribution decays with rank, and it encodes a useful reluctance to trust any single retriever's top result. With k around 60, the standard value, the difference between rank 1 and rank 2 is small (1/61 versus 1/62), so being first in one list is only a slight edge over being second — not enough to overcome being far down the other list. That is what makes RRF reward consensus: a document has to rank well in both lists to accumulate a winning score, because no single high rank is worth much on its own. A smaller k would make the top rank more decisive and RRF more like "whoever is first somewhere"; k near 60 is a well-tested default that favors documents both retrievers like.

This is why RRF is the default fusion in production hybrid search despite being almost trivially simple. It needs no score normalization, no per-retriever calibration, and no tuning beyond the single robust constant k; it is invariant to score scale by construction, so adding or swapping a retriever never destabilizes it; and it directly optimizes for the thing hybrid search is supposed to deliver — documents that multiple independent signals agree are relevant. It generalizes to any number of retrievers by adding more terms to the sum, which is how systems fuse lexical, dense, and reranker signals in one line.

**A score is meaningful only inside its own retriever, so fusing scores requires a fake exchange rate that the larger scale wins; rank is a common language across retrievers, so RRF's sum of 1/(k+rank) is unit-free, and k near 60 makes it reward documents that rank well in both lists rather than first in one.**

## Worked example

The fixture is two retrievers scoring the same five documents on different scales, plus the true answer.

```json filename=modules/context-and-retrieval/code/retrieval-inter-14/retrievers.json:4-8 COMPLETE
  "answer": "A",
  "k": 60,
  "retrievers": {
    "lexical": {"A": 20.0, "X": 28.0, "Y": 6.0, "P": 12.0, "Q": 3.0},
    "dense":   {"A": 0.80, "X": 0.30, "Y": 0.90, "P": 0.20, "Q": 0.55}
  }
```

The answer A scores second-highest in both retrievers. Distractor X tops the lexical list (28) but is weak on dense; distractor Y tops dense (0.90) but is weak on lexical. Ranks come from sorting each retriever's scores.

```python filename=modules/context-and-retrieval/code/retrieval-inter-14/rrf.py:43-46 COMPLETE
def ranks(scores):
    """Map each document to its 1-based rank (highest score = rank 1)."""
    order = sorted(scores, key=lambda d: scores[d], reverse=True)
    return {doc: i + 1 for i, doc in enumerate(order)}
```

Raw-score fusion sums the two scores; RRF sums 1 over (k plus rank).

```python filename=modules/context-and-retrieval/code/retrieval-inter-14/rrf.py:49-61 COMPLETE
def fuse_rawscore(retrievers):
    """Fuse by summing raw scores across retrievers -- sensitive to each retriever's scale."""
    docs = next(iter(retrievers.values())).keys()
    total = {d: sum(r[d] for r in retrievers.values()) for d in docs}
    return sorted(total, key=lambda d: total[d], reverse=True), total


def fuse_rrf(retrievers, k):
    """Fuse by reciprocal rank: sum 1/(k+rank) across retrievers -- uses only rank order."""
    rank_maps = {name: ranks(scores) for name, scores in retrievers.items()}
    docs = next(iter(retrievers.values())).keys()
    total = {d: sum(1.0 / (k + rm[d]) for rm in rank_maps.values()) for d in docs}
    return sorted(total, key=lambda d: total[d], reverse=True), total
```

First, look at the ranks — the answer is second in both, the distractors first in one and buried in the other.

```text filename=modules/context-and-retrieval/code/retrieval-inter-14/rrf.py --rank
RANK — each document's rank and score per retriever (answer = A)
------------------------------------------------------------
  doc     lexical          dense         
  A       rank 2 (20.00)     rank 2 (0.80)    <- answer
  X       rank 1 (28.00)     rank 4 (0.30)  
  Y       rank 4 (6.00)     rank 1 (0.90)  
  P       rank 3 (12.00)     rank 5 (0.20)  
  Q       rank 5 (3.00)     rank 3 (0.55)  
------------------------------------------------------------
  the answer is rank 2 in both — strong agreement, first in neither.
```

Predict: raw-score fusion sums 20 + 0.8 = 20.8 for A but 28 + 0.3 = 28.3 for X, so X wins on its BM25 score alone — the wrong answer. RRF gives A two rank-2 contributions (1/62 each) and gives X a rank-1 plus a rank-4 (1/61 + 1/64), which is slightly less, so A wins. And rescaling the dense scores should leave RRF alone but move raw-score fusion. Run the fusion.

```text filename=modules/context-and-retrieval/code/retrieval-inter-14/rrf.py --fuse
FUSE — top document under each method (k=60), original vs dense rescaled x1000
------------------------------------------------------------
  raw-score:  top X   (rescaled: top Y)
  RRF:        top A   (rescaled: top A)
------------------------------------------------------------
  answer is A; raw-score misses it and moves when rescaled, RRF holds.
```

Raw-score fusion crowns X, the lexical distractor, because 28.3 beats everything — the dense retriever's preference for A barely registered. Multiply the dense scores by 1000 (which changes no dense ranking) and now dense dominates instead, so raw-score fusion flips to Y, the dense distractor: the same documents, the same rankings, a different winner purely because of units. RRF crowns A both times. A ranked second in both lists, so neither retriever alone returns it first and raw-score fusion never sees it — but it is the document both retrievers agree on, and RRF is built to find exactly that.

<svg role="img" aria-label="Answer A sits at rank 2 in both retrievers; distractor X is rank 1 lexical but rank 4 dense; distractor Y is rank 1 dense but rank 4 lexical" viewBox="0 0 470 195" width="470" height="195">
  <rect x="0" y="0" width="470" height="195" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">rank in each retriever (top = rank 1); lines link the same doc</text>
  <text x="90" y="44" font-family="var(--mono)" font-size="9" fill="var(--muted)">lexical</text>
  <text x="330" y="44" font-family="var(--mono)" font-size="9" fill="var(--muted)">dense</text>
  <line x1="120" y1="60" x2="120" y2="180" stroke="var(--line)"/>
  <line x1="360" y1="60" x2="360" y2="180" stroke="var(--line)"/>
  <line x1="120" y1="88" x2="360" y2="88" stroke="var(--acc-line)" stroke-width="2"/>
  <g fill="var(--acc-line)"><circle cx="120" cy="88" r="5"/><circle cx="360" cy="88" r="5"/></g>
  <text x="128" y="84" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">A rank2</text>
  <text x="330" y="84" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">A rank2</text>
  <line x1="120" y1="64" x2="360" y2="136" stroke="var(--s2)" stroke-width="1.5"/>
  <g fill="var(--s2)"><circle cx="120" cy="64" r="4"/><circle cx="360" cy="136" r="4"/></g>
  <text x="128" y="62" font-family="var(--mono)" font-size="8" fill="var(--s2)">X r1</text>
  <text x="336" y="150" font-family="var(--mono)" font-size="8" fill="var(--s2)">X r4</text>
  <line x1="120" y1="136" x2="360" y2="64" stroke="var(--s1)" stroke-width="1.5"/>
  <g fill="var(--s1)"><circle cx="120" cy="136" r="4"/><circle cx="360" cy="64" r="4"/></g>
  <text x="96" y="150" font-family="var(--mono)" font-size="8" fill="var(--s1)">Y r4</text>
  <text x="368" y="62" font-family="var(--mono)" font-size="8" fill="var(--s1)">Y r1</text>
</svg>
^ The answer A's line is flat near the top (rank 2 in both); each distractor's line runs from top on one side to bottom on the other — first in one retriever, buried in the other, which is what stops RRF from picking it.

## Build

Reproduce the fusion. Pure standard library, deterministic, so the raw-score winner X, its flip to Y under rescaling, and the RRF winner A come out exactly.

Run `--rank` for the per-retriever ranks, `--fuse` for the two methods and the rescaling test, `--check` for the gate. The self-test pins that the answer is first in neither retriever, that raw-score fusion misses it and is scale-dependent, and that RRF finds it and is scale-invariant.

```python filename=modules/context-and-retrieval/code/retrieval-inter-14/rrf.py:111-115 COMPLETE
    raw_top = fuse_rawscore(retr)[0][0]
    rawscore_wrong = raw_top != ans
    print("  raw-score fusion's top is not the answer = %s (top %s)" % (rawscore_wrong, raw_top))

    rrf_top = fuse_rrf(retr, k)[0][0]
    rrf_correct = rrf_top == ans
    print("  RRF's top is the answer = %s (top %s)" % (rrf_correct, rrf_top))
```

```text filename=modules/context-and-retrieval/code/retrieval-inter-14/rrf.py --check
SELF-TEST — raw-score fusion picks a distractor and is scale-dependent; RRF picks the answer and is invariant
------------------------------------------------------------------------------------------------------------
  the answer is first in neither retriever = True (ranks [2, 2])
  raw-score fusion's top is not the answer = True (top X)
  RRF's top is the answer = True (top A)
  RRF's top is unchanged when dense is rescaled = True (A)
  raw-score fusion's top changes when dense is rescaled = True (X -> Y)
------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  answer_top_neither=True  rawscore_wrong=True  rrf_correct=True  rrf_invariant=True  rawscore_scale_dependent=True
```

The rescaling test is one helper that multiplies a single retriever's scores by a constant — which changes no ranking, so it isolates pure scale sensitivity.

```python filename=modules/context-and-retrieval/code/retrieval-inter-14/rrf.py:64-68 COMPLETE
def scaled(retrievers, name, factor):
    """Return a copy with one retriever's scores multiplied by factor (same ranking, different scale)."""
    out = {n: dict(s) for n, s in retrievers.items()}
    out[name] = {d: v * factor for d, v in out[name].items()}
    return out
```

<svg role="img" aria-label="Under a dense rescale, raw-score fusion's winner moves from X to Y while RRF's winner stays A in both cases" viewBox="0 0 470 170" width="470" height="170">
  <rect x="0" y="0" width="470" height="170" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">fused winner: original vs dense scores x1000</text>
  <text x="150" y="46" font-family="var(--mono)" font-size="9" fill="var(--muted)">original</text>
  <text x="330" y="46" font-family="var(--mono)" font-size="9" fill="var(--muted)">rescaled</text>
  <text x="30" y="82" font-family="var(--mono)" font-size="9" fill="var(--s2)">raw-score</text>
  <rect x="130" y="66" width="60" height="26" fill="var(--s2)"/>
  <text x="150" y="83" font-family="var(--mono)" font-size="9" fill="var(--panel)">X</text>
  <line x1="190" y1="79" x2="310" y2="79" stroke="var(--s2)" stroke-dasharray="3 3"/>
  <rect x="310" y="66" width="60" height="26" fill="var(--s2)"/>
  <text x="330" y="83" font-family="var(--mono)" font-size="9" fill="var(--panel)">Y</text>
  <text x="380" y="83" font-family="var(--mono)" font-size="8" fill="var(--s2)">moved!</text>
  <text x="30" y="132" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">RRF</text>
  <rect x="130" y="116" width="60" height="26" fill="var(--acc-line)"/>
  <text x="150" y="133" font-family="var(--mono)" font-size="9" fill="var(--panel)">A</text>
  <line x1="190" y1="129" x2="310" y2="129" stroke="var(--acc-line)"/>
  <rect x="310" y="116" width="60" height="26" fill="var(--acc-line)"/>
  <text x="330" y="133" font-family="var(--mono)" font-size="9" fill="var(--panel)">A</text>
  <text x="380" y="133" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">held</text>
</svg>
^ The same rescaling that changes no ranking moves raw-score fusion's winner from X to Y but leaves RRF's winner at the answer A — scale sensitivity versus scale invariance in one picture.

Five True flags. Answer_top_neither: A is rank 2 in both, so no single retriever ranks it first. Rawscore_wrong: raw-score fusion crowns X, the lexical distractor. Rrf_correct: RRF crowns A. Rrf_invariant: RRF's winner is unchanged when dense scores are multiplied by 1000. Rawscore_scale_dependent: raw-score's winner flips from X to Y under the same rescaling. The last two flags are the argument for RRF: the same rankings must give the same fusion, and only the rank-based method does.

**The scale flags are the verdict — raw-score fusion's winner moves from X to Y when you multiply an input by a constant that changes no ranking, while RRF's winner never moves, so only RRF is fusing on agreement rather than on units.**

## Definition of done

You are done when you reproduce both fusions and can explain why rank fusion is scale-invariant.

Concretely: `--rank` shows A at rank 2 in both retrievers with X and Y each first in one and fourth in the other; `--fuse` shows raw-score fusion picking X and flipping to Y under a dense rescale, while RRF picks A both times; `--check` prints PASS with five True flags. You can explain that scores are comparable only within a retriever so summing them lets the larger scale dominate and makes the result unit-dependent, that RRF uses only rank so units cancel, and that k near 60 makes the top rank only a slight edge so RRF rewards documents ranked well in both lists.

The habit to carry: fuse retrievers by reciprocal rank, not by summed scores, and reach for score normalization only when you have a specific reason RRF is insufficient. When a hybrid pipeline behaves like one of its retrievers is being ignored, check whether you are summing raw scores of different scales — that is the classic way a dense retriever's votes get swamped by BM25's larger numbers. Fuse on rank, and the consensus document wins.

## Boss fight

The instructive failure is a hybrid search that shipped with dense retrieval "on" but performing exactly like pure BM25.

A team adds a dense retriever to an existing BM25 system and fuses by adding the scores. Offline metrics barely move, and inspection shows the fused ranking is identical to BM25's on almost every query — the expensive dense retriever is contributing nothing. The cause is the scales: BM25 scores run into the tens, cosine scores are below one, so every fused sum is dominated by the BM25 term and the dense score only ever breaks ties. The team tries min-max normalizing the scores, which helps until one query has a BM25 outlier that squashes all the other normalized scores to near zero. The stable fix is RRF: fuse on rank, drop the normalization entirely, and the dense retriever's rankings finally count equally, lifting recall on paraphrase queries that BM25 alone missed.

Your turn, two moves. First, confirm the scale is the whole story. Multiply the lexical scores by 0.01 (so both retrievers are now on a 0-to-1-ish scale) and check that raw-score fusion suddenly starts finding A — proving its earlier failure was units, not information, and that it only ever works when you happen to have matched the scales by hand. Second, sweep k in RRF from 1 upward and watch the winner: at very small k the top rank dominates and a distractor that is first in one list can win, while at k near 60 the consensus document A wins — showing that k is the knob that sets how much RRF rewards a single high rank versus agreement across lists.

## External resources

The original RRF paper, Cormack, Clarke, and Buettcher's "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods" (2009), introduces the 1/(k+rank) formula and the k=60 default, and shows it beating more complex learned fusion methods.

Production hybrid-search documentation (Elasticsearch, OpenSearch, Weaviate, and others) describes RRF as the recommended way to combine BM25 and vector rankings, and reading it shows the same score-scale motivation this module builds from.

Any treatment of rank aggregation and voting theory (the Condorcet and Borda methods) is the broader context — RRF is a rank-aggregation rule chosen for robustness and simplicity, and comparing it to score-based aggregation clarifies why using ranks avoids the incomparable-scale problem.
