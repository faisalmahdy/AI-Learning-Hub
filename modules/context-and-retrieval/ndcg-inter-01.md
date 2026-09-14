---
id: ndcg-inter-01
title: Score retrieval ranking with nDCG, not recall — two orderings of the same results have identical recall but the one that buries the best result should score lower
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: Retrieval quality has two parts — did you fetch the relevant items, and did you order them well — and recall or hit-rate measures only the first. They treat the result list as a set, so a ranking that returns the perfect answer at position 1 and a ranking that returns the same answer at position 10 look identical, both having "retrieved" it; for anything a person or a model reads top-down, that is the wrong thing to measure, because position is most of the value. nDCG measures both parts at once: it starts from graded relevance (a result is exactly right, useful, marginal, or irrelevant — a score, not a flag), discounts each result's relevance by its rank (dividing the gain by the logarithm of the position, so a highly relevant result earns much more at rank 1 than at rank 4), sums the discounted gains into DCG, and normalizes by IDCG (the DCG of the ideal best-first ordering) so the score lands in 0 to 1 where 1 means the ranking is already optimal. A set metric cannot do this by construction: because it ignores order, it assigns the same recall to the best and worst possible ordering of an identical retrieved set, blind to exactly the ranking quality that matters most. On a fixture where two orderings retrieve the identical set of four graded results, recall is 0.75 for both, but the good ordering (best first) scores nDCG 1.0 while the bad ordering (best last) scores about 0.61.
eli5: Imagine a search that finds the four books you need, but one search hands them to you with the most useful book on top and the least useful on the bottom, while another hands you the exact same four books flipped upside down — least useful on top. If all you ask is "did it find the books?", both searches score the same: yes, all four are in the pile. But you read from the top down and stop when you've got what you need, so the first search is far more useful — you find the best book immediately, the second makes you dig to the bottom. A good score for search has to care about the order, not just the contents. nDCG does that: it gives more credit for putting the best results near the top, and a search that buries the best result gets a lower score even though it found everything.
---

## Why this module

A retrieval system is judged by how well it serves the thing downstream of it — a person scanning results, or a language model reading a top-k context window. Both consume the list from the top and give the earliest items the most weight: the reader may stop after the first good hit, and the model attends most to what comes first. So the position of a relevant result is not a cosmetic detail; it is a large part of the result's actual value to the consumer.

Recall and hit-rate are blind to this. They ask a set question — is the relevant item somewhere in the retrieved list — and return the same answer whether it is first or last. Two systems with identical recall can deliver wildly different experiences, one surfacing the answer immediately and the other burying it under noise, and the metric cannot tell them apart. Optimizing recall alone can even reward a system that retrieves more junk as long as it also keeps the relevant items somewhere in the pile.

The fix is a metric that scores the ordering, and nDCG is the standard one. It combines graded relevance with a positional discount so that placing a highly relevant result near the top is worth more than placing it near the bottom, and it normalizes against the best possible ordering so scores are comparable across queries. This module scores two orderings of the same retrieved set and shows recall calling them equal while nDCG separates them.

**Consumers read top-down, so a relevant result's position is most of its value; recall is a set metric blind to position, so it scores the best and worst ordering of the same results identically — nDCG scores the ordering.**

## Concepts

The three letters name three ideas that build on each other. Gain is graded relevance: instead of a relevant/irrelevant flag, each result carries a score for how relevant it is, so an exactly-right result contributes more than a marginal one. Cumulative means you add up the gains down the list. Discounted means each gain is divided by a function of its rank — the logarithm of the position — so the same relevance contributes less the further down it sits. DCG is the discounted cumulative gain of one ordering.

The positional discount is the heart of it. Dividing by log of the rank makes the drop steep at the top and gentle further down, which matches how attention actually falls off: the difference between rank 1 and rank 2 matters a lot, the difference between rank 19 and rank 20 barely at all. That shape is why a highly relevant result earns nearly its full gain at the top and a fraction of it if buried, and why moving a good result up the list raises the score.

The normalization is what makes it a fair metric rather than a raw number. DCG alone is not comparable across queries: a query with five relevant documents can rack up more DCG than a query with one, just by having more to accumulate, so a low raw DCG might mean a hard query, not a bad ranking. Dividing by IDCG — the DCG of the ideal ordering, the same relevances sorted best-first — puts every query on a 0-to-1 scale where 1 is "you ordered these as well as possible." nDCG thus rewards both retrieving the right things (they contribute gain) and ordering them well (the discount and the normalization), in one number.

<svg role="img" aria-label="A curve of the positional discount 1 over log2 of rank plus 1: steep drop from rank 1 to rank 2, then flattening, showing top positions are worth far more" viewBox="0 0 440 150">
<line x1="40" y1="120" x2="410" y2="120" stroke="var(--line)"/>
<line x1="40" y1="20" x2="40" y2="120" stroke="var(--line)"/>
<text x="225" y="142" fill="var(--muted)" font-size="9" text-anchor="middle">rank</text>
<text x="24" y="70" fill="var(--muted)" font-size="9" text-anchor="middle">discount</text>
<circle cx="70" cy="30" r="4" fill="var(--s1)"/>
<text x="70" y="22" fill="var(--muted)" font-size="7" text-anchor="middle">1.00</text>
<circle cx="130" cy="63" r="4" fill="var(--s1)"/>
<text x="130" y="55" fill="var(--muted)" font-size="7" text-anchor="middle">.63</text>
<circle cx="190" cy="80" r="4" fill="var(--s1)"/>
<text x="190" y="72" fill="var(--muted)" font-size="7" text-anchor="middle">.50</text>
<circle cx="250" cy="90" r="4" fill="var(--s1)"/>
<circle cx="310" cy="97" r="4" fill="var(--s1)"/>
<circle cx="370" cy="102" r="4" fill="var(--s1)"/>
<path d="M70 30 Q 120 60, 190 80 T 370 102" fill="none" stroke="var(--s1)" stroke-dasharray="3 3"/>
<text x="240" y="35" fill="var(--muted)" font-size="8">big drop rank 1 to 2, then flat</text>
</svg>
^ The 1/log2(rank+1) discount falls steeply at the top and flattens below, so promoting a relevant result from rank 2 to rank 1 gains far more than moving it from rank 19 to 18.

**Gain is graded relevance, the log discount makes top positions worth far more, and normalizing by the ideal ordering puts every query on a comparable 0-to-1 scale — so nDCG scores retrieval and ordering together.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/ndcg-inter-01. The fixture is two orderings of the same four graded results — one best-first, one best-last.

```json filename=modules/context-and-retrieval/code/ndcg-inter-01/ndcg.json:3-5 COMPLETE
  "orderings": {
    "good": [3, 2, 1, 0],
    "bad": [0, 1, 2, 3]
```

DCG divides each result's relevance by the log of its rank and sums.

```python filename=modules/context-and-retrieval/code/ndcg-inter-01/ndcg.py:35-37 COMPLETE
def dcg(relevances):
    """Discounted cumulative gain: each relevance divided by log2 of its (1-based) rank + 1."""
    return sum(rel / math.log2(rank + 1) for rank, rel in enumerate(relevances, start=1))
```

nDCG normalizes that by the DCG of the ideal ordering.

```python filename=modules/context-and-retrieval/code/ndcg-inter-01/ndcg.py:40-43 COMPLETE
def ndcg(relevances):
    """Normalize DCG by the DCG of the ideal (best-first) ordering of the same relevances."""
    ideal = dcg(sorted(relevances, reverse=True))
    return dcg(relevances) / ideal if ideal else 0.0
```

Recall, the set metric, is order-blind — just the fraction of relevant items present.

```python filename=modules/context-and-retrieval/code/ndcg-inter-01/ndcg.py:46-49 COMPLETE
def recall(relevances):
    """Order-blind: the fraction of relevant items (relevance > 0) present in the set."""
    total_relevant = sum(1 for r in relevances if r > 0)
    return total_relevant / len(relevances)
```

Before running it, predict: the good ordering front-loads the relevance so its DCG should be high (and equal to the ideal), while the bad ordering back-loads it. Run `--dcg`:

```text filename=ndcg.py --dcg
DCG — per-rank discounted gain for each ordering
----------------------------------------------------------
  good ordering: relevances [3, 2, 1, 0]
    rank 1: 3 / log2(2) = 3.000
    rank 2: 2 / log2(3) = 1.262
    rank 3: 1 / log2(4) = 0.500
    rank 4: 0 / log2(5) = 0.000
    DCG = 4.762   (ideal DCG = 4.762)
  bad ordering: relevances [0, 1, 2, 3]
    rank 1: 0 / log2(2) = 0.000
    rank 2: 1 / log2(3) = 0.631
    rank 3: 2 / log2(4) = 1.000
    rank 4: 3 / log2(5) = 1.292
    DCG = 2.923   (ideal DCG = 4.762)
```

The prediction holds. The good ordering earns the grade-3 result's full 3.000 at rank 1; the bad ordering earns that same grade-3 result only 1.292 at rank 4, because the log discount has shrunk it. Same items, same total relevance, but the good ordering's DCG (4.762) far exceeds the bad one's (2.923) purely from position.

<svg role="img" aria-label="Discounted gain per rank for two orderings: good ordering has a tall bar at rank 1 falling off; bad ordering has a short bar at rank 1 rising toward rank 4 but never as tall" viewBox="0 0 440 160">
<line x1="40" y1="130" x2="410" y2="130" stroke="var(--line)"/>
<text x="120" y="150" fill="var(--muted)" font-size="10" text-anchor="middle">good (best first)</text>
<rect x="55" y="40" width="22" height="90" fill="var(--s1)"/>
<rect x="82" y="92" width="22" height="38" fill="var(--s1)"/>
<rect x="109" y="115" width="22" height="15" fill="var(--s1)"/>
<rect x="136" y="130" width="22" height="1" fill="var(--s1)"/>
<text x="105" y="34" fill="var(--s1)" font-size="8" text-anchor="middle">DCG 4.76</text>
<text x="320" y="150" fill="var(--muted)" font-size="10" text-anchor="middle">bad (best last)</text>
<rect x="255" y="130" width="22" height="1" fill="var(--s2)"/>
<rect x="282" y="111" width="22" height="19" fill="var(--s2)"/>
<rect x="309" y="100" width="22" height="30" fill="var(--s2)"/>
<rect x="336" y="91" width="22" height="39" fill="var(--s2)"/>
<text x="305" y="80" fill="var(--s2)" font-size="8" text-anchor="middle">DCG 2.92</text>
</svg>
^ The good ordering banks the big gain at rank 1 before the discount bites; the bad ordering earns its biggest relevance last, heavily discounted.

Now the metrics side by side. Run `--score`:

```text filename=ndcg.py --score
SCORE — nDCG vs order-blind recall
--------------------------------------------------
  ordering   recall   nDCG
  good       0.75     1.000
  bad        0.75     0.614
--------------------------------------------------
  recall is identical; nDCG separates the good ordering from the bad
```

The prediction lands. Recall is 0.75 for both — three of the four items are relevant, and both orderings contain the same items — so the set metric declares them equally good. nDCG says otherwise: the good ordering scores a perfect 1.000 (it is the ideal ordering) and the bad one scores 0.614, correctly marking it as a worse ranking of the same results.

<svg role="img" aria-label="Recall and nDCG for the two orderings: recall equal at 0.75 for both; nDCG 1.0 for good and 0.61 for bad" viewBox="0 0 440 150">
<text x="120" y="20" fill="var(--ink)" font-size="10" text-anchor="middle">recall (order-blind)</text>
<rect x="70" y="70" width="40" height="55" fill="var(--muted)"/>
<text x="90" y="64" fill="var(--muted)" font-size="8" text-anchor="middle">good .75</text>
<rect x="140" y="70" width="40" height="55" fill="var(--muted)"/>
<text x="160" y="64" fill="var(--muted)" font-size="8" text-anchor="middle">bad .75</text>
<text x="120" y="140" fill="var(--s2)" font-size="8" text-anchor="middle">cannot tell them apart</text>
<text x="330" y="20" fill="var(--ink)" font-size="10" text-anchor="middle">nDCG (order-aware)</text>
<rect x="280" y="52" width="40" height="73" fill="var(--s1)"/>
<text x="300" y="46" fill="var(--s1)" font-size="8" text-anchor="middle">good 1.0</text>
<rect x="350" y="80" width="40" height="45" fill="var(--s2)"/>
<text x="370" y="74" fill="var(--s2)" font-size="8" text-anchor="middle">bad .61</text>
<text x="330" y="140" fill="var(--s1)" font-size="8" text-anchor="middle">separates them</text>
</svg>
^ Recall is flat across both orderings; nDCG marks the best-first ordering ideal and the best-last ordering clearly worse.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that both orderings retrieve the same set, that recall is therefore identical, that nDCG scores the good ordering above the bad, that the best-first ordering scores the ideal 1.0, and that the buried ordering scores below 1.0.

```python filename=modules/context-and-retrieval/code/ndcg-inter-01/ndcg.py:84-94 COMPLETE
    same_set = sorted(good) == sorted(bad)
    print("  both orderings retrieve the identical set of items = %s" % same_set)

    recall_identical = recall(good) == recall(bad)
    print("  recall is the same for both orderings = %s (%.2f == %.2f)" % (recall_identical, recall(good), recall(bad)))

    ndcg_distinguishes = ndcg(good) > ndcg(bad)
    print("  nDCG scores the good ordering above the bad = %s (%.3f > %.3f)" % (ndcg_distinguishes, ndcg(good), ndcg(bad)))

    good_is_ideal = abs(ndcg(good) - 1.0) < 1e-9
    print("  the best-first ordering scores the ideal nDCG of 1.0 = %s" % good_is_ideal)
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if recall ever separates the orderings or nDCG ever stops rewarding the better one:

```text filename=ndcg.py --check
SELF-TEST — recall is identical for both orderings; nDCG rewards the one that ranks relevant results highest
----------------------------------------------------------------------------------------------------------------
  both orderings retrieve the identical set of items = True
  recall is the same for both orderings = True (0.75 == 0.75)
  nDCG scores the good ordering above the bad = True (1.000 > 0.614)
  the best-first ordering scores the ideal nDCG of 1.0 = True
  the buried ordering scores below 1.0 = True (0.614)
```

**The self-test pins recall identical while nDCG differs — proving nDCG measures the ordering quality recall is blind to, on a retrieved set the two metrics agree is equally complete.**

## Definition of done

You can explain why a relevant result's position is most of its value to a top-down consumer, and why recall ignores position.
You can name the three parts of DCG — graded gain, cumulative sum, positional discount — and say what each contributes.
You can explain why the log discount matches how attention falls off with rank.
You can explain why DCG must be normalized by IDCG to compare across queries, and what nDCG = 1 means.
You can predict that two orderings of the same set have equal recall but different nDCG, and compute which is higher.

## Boss fight

Consider the cutoff. In practice nDCG is reported at a rank k — nDCG@10, say — because only the top k are shown or fit the context window. This introduces a subtlety recall does not have: a relevant result at rank 11 contributes to recall (it was retrieved) but nothing to nDCG@10 (it is below the cutoff). So the two metrics can even disagree in direction — a system with higher recall can have lower nDCG@k if its extra relevant items all land past k while its top k are worse ordered. The lesson sharpens: choose k to match what the consumer actually sees, and know that beyond-k relevant items are free to recall and worthless to nDCG@k, which is usually the more honest accounting for a top-k system.

Now consider the graded relevance itself, which nDCG depends on and recall does not. nDCG needs a relevance grade for each result, and those grades come from human judgments or a model, both of which are noisy and expensive. Get the grades wrong — treat a marginal result as exactly right — and nDCG rewards the wrong ordering with full confidence. So nDCG buys ordering-awareness at the cost of needing graded labels, whereas recall needs only a binary relevant/not judgment. The richer metric has a richer input requirement, and a shaky grading rubric can make nDCG's precision spurious; the metric is only as trustworthy as the relevance grades feeding it.

**nDCG is reported at a cutoff k matched to what the consumer sees, so beyond-k relevant items help recall but not nDCG@k and the two can disagree in direction; and nDCG's ordering-awareness costs graded relevance labels, so its precision is only as sound as the grading rubric behind it.**

## External resources

Manning, Raghavan, and Schütze's "Introduction to Information Retrieval" derives DCG, IDCG, and nDCG and situates them among the order-aware ranking metrics.
The original Järvelin and Kekäläinen paper (2002) introduced discounted cumulative gain and its normalization as the standard graded-relevance ranking measure.
The topic's own module on measuring retrieval by rank covers the binary hit/rank metrics this graded, order-aware metric extends.
