---
id: aggregate-inter-01
title: Retrieve by relevance threshold, not a fixed top-k, for a "how many" query — the answer is spread across every relevant passage, so a small k undercounts
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: Top-k retrieval is built for a needle query — "what is X" — whose answer lives in the single best passage or two, so returning the top few and stopping is exactly right, and a bigger k would only add noise. Almost every retrieval default (a fixed k of 3, 5, 10) assumes this shape. An aggregation query has the opposite shape: "how many security incidents were there in 2023," "list all the affected customers," "what are every error code" — the answer is not in one passage, it is the whole set of relevant passages, each contributing a piece. The number of passages you need is the size of the answer, which is exactly what you do not know in advance. A fixed top-k smaller than the number of relevant passages then undercounts: it returns its k best passages, all genuinely relevant with no error raised, and the answer built from them is short. On the fixture five passages each describe one distinct 2023 incident and all score above 0.5, while two irrelevant passages score below it; top-3 retrieves three of the five and counts 3 against a true count of 5, while threshold retrieval — every passage at or above 0.5 — returns all five and counts the true 5. The retriever did its job; k was the wrong stopping rule for a query whose answer is a set. The fix is to stop by relevance, not by rank: retrieve every passage above a relevance threshold so the amount retrieved adapts to how much is relevant — one or two for a needle query, all of them for an aggregation query. The rule: match the stopping rule to the query, and use a relevance threshold rather than a fixed top-k whenever the answer is a count or a list.
eli5: Imagine you ask "how many red cars are parked on my street" and a helper walks out, notes the three closest red cars, and reports "three." But there are five red cars — two are further down the block, just as red, and the helper stopped after three because you can only carry so many in your head. The report is wrong, not because the helper picked the wrong cars, but because "the three nearest" was the wrong rule for a counting question: to count all of them you have to keep going until you run out of red cars, not stop at a fixed number. Searching documents works the same way. Grabbing the top few is right when you want one fact, but for "how many" or "list all," you have to grab every relevant one, or your count comes up short.
---

## Why this module

Retrieval systems are tuned for the question everyone tests them on: find the passage that answers this. You paginate to the top 3 or top 5, feed them to the model, and the answer is right there in the best chunk. The fixed k is a sensible default, and it works so well for these queries that it becomes invisible — a constant nobody revisits.

Then a user asks a counting question. "How many outages did we have last quarter?" "List every customer affected by the breach." The system runs the same retrieval, returns the same top-k passages, and the model dutifully counts what it was given — and gets a number that is quietly, confidently too small. Nothing errored. The retrieved passages were all relevant. The answer is just incomplete.

This module shows why. Five passages each describe one distinct incident, all genuinely relevant; a top-3 retrieval returns three of them and the count comes out 3 instead of 5. Then it switches from stopping at a fixed rank to stopping at a relevance threshold, retrieves all five, and counts correctly. The lesson is that k is a stopping rule tuned for one query shape, and an aggregation query has a different shape that the same k gets wrong.

**A fixed top-k assumes the answer is concentrated in the best few passages, which is true for a needle query and false for a counting or list-all query — where the answer is the whole relevant set, so any k below its size undercounts.**

## Concepts

Sort queries by where their answer lives. A needle query — "what is our refund policy" — has its answer concentrated: one passage states the policy, maybe a second adds detail, and everything after is redundant or off-topic. For this shape, retrieving the top few passages by relevance is optimal: you get the answer and stop before the noise. A fixed k of 3 or 5 is a good stopping rule because the answer's size is small and roughly constant.

An aggregation query — "how many incidents," "list all customers," "every error code" — has its answer distributed. Each relevant passage carries one member of the answer set: one incident, one customer, one code. The complete answer is the union of all of them, and its size is however many relevant passages exist, which varies per query and is not known before retrieving. There is no small constant that is the right amount to retrieve, because the right amount is "all the relevant ones."

Now the failure is arithmetic. If a query has R relevant passages and you retrieve the top k of them with k less than R, you get k members of an answer that has R, so a count comes out k instead of R and a list is missing R minus k items. Every passage you returned was correct; the error is entirely in stopping at k. And it is silent: the retriever has no way to know it was asked a counting question, the passages it returned are all relevant, and the model counts exactly what it received.

This is distinct from a passage-diversity problem. Diversity concerns — one document monopolizing the top-k slots — are fixed by capping per source so multiple documents get in; the answer is still a single best thing you want from varied sources. Aggregation is about the total amount retrieved for an answer that is a set, regardless of how the passages are distributed across documents. The two can co-occur, but the fix for aggregation is the size of the retrieval, not its diversity.

<svg role="img" aria-label="Two query shapes. A needle query has its answer in the top one or two passages, so a top-k line after 3 captures it. An aggregation query has its answer spread across all five relevant passages, so the top-3 line captures only three and misses two." viewBox="0 0 640 210">
<text x="160" y="26" fill="var(--ink)" font-size="12" text-anchor="middle">needle query</text>
<rect x="90" y="40" width="140" height="20" fill="var(--s1)" opacity="0.7"/>
<text x="240" y="55" fill="var(--muted)" font-size="9">← the answer</text>
<rect x="90" y="64" width="140" height="20" fill="var(--panel)" stroke="var(--line)"/>
<rect x="90" y="88" width="140" height="20" fill="var(--panel)" stroke="var(--line)"/>
<line x1="80" y1="112" x2="250" y2="112" stroke="var(--ink)" stroke-width="1.5" stroke-dasharray="4 3"/>
<text x="160" y="128" fill="var(--muted)" font-size="9" text-anchor="middle">top-3 cut — captures the answer</text>
<text x="480" y="26" fill="var(--ink)" font-size="12" text-anchor="middle">aggregation query</text>
<rect x="410" y="40" width="140" height="20" fill="var(--s1)" opacity="0.7"/>
<rect x="410" y="64" width="140" height="20" fill="var(--s1)" opacity="0.7"/>
<rect x="410" y="88" width="140" height="20" fill="var(--s1)" opacity="0.7"/>
<line x1="400" y1="112" x2="570" y2="112" stroke="var(--s2)" stroke-width="1.5" stroke-dasharray="4 3"/>
<rect x="410" y="116" width="140" height="20" fill="var(--s1)" opacity="0.7"/>
<rect x="410" y="140" width="140" height="20" fill="var(--s1)" opacity="0.7"/>
<text x="580" y="131" fill="var(--s2)" font-size="9">← missed</text>
<text x="480" y="180" fill="var(--muted)" font-size="9" text-anchor="middle">top-3 cut — misses two of five</text>
</svg>
^ For a needle query the answer is above the top-k cut; for an aggregation query the answer extends below it, so the same cut that captures one loses part of the other.

**The right amount to retrieve is the size of the answer, and an aggregation query's answer is the whole relevant set — so a stopping rule that is a small constant is guaranteed to undercount whenever the set is larger than the constant.**

## Worked example

The fixture is five incident passages, all relevant, plus two irrelevant ones, with a fixed k and a relevance threshold.

```json filename=modules/context-and-retrieval/code/aggregate-inter-01/aggregate.json:3-14 COMPLETE
  "true_count": 5,
  "top_k": 3,
  "relevance_threshold": 0.5,
  "passages": [
    {"id": "p1", "incident": true, "relevance": 0.90},
    {"id": "p2", "incident": true, "relevance": 0.88},
    {"id": "p3", "incident": true, "relevance": 0.85},
    {"id": "p4", "incident": true, "relevance": 0.83},
    {"id": "p5", "incident": true, "relevance": 0.80},
    {"id": "p6", "incident": false, "relevance": 0.30},
    {"id": "p7", "incident": false, "relevance": 0.25}
  ]
```

Top-k stops at a fixed rank.

```python filename=modules/context-and-retrieval/code/aggregate-inter-01/aggregate.py:32-34 COMPLETE
def retrieve_topk(passages, k):
    """The k highest-relevance passages -- a fixed stopping rule, right for a needle query."""
    return sorted(passages, key=lambda p: p["relevance"], reverse=True)[:k]
```

Threshold retrieval stops at a relevance level, so the amount adapts.

```python filename=modules/context-and-retrieval/code/aggregate-inter-01/aggregate.py:37-39 COMPLETE
def retrieve_threshold(passages, threshold):
    """Every passage at or above the relevance threshold -- the amount adapts to how much is relevant."""
    return [p for p in passages if p["relevance"] >= threshold]
```

The answer to the count is how many retrieved passages are incidents.

```python filename=modules/context-and-retrieval/code/aggregate-inter-01/aggregate.py:42-44 COMPLETE
def count_incidents(retrieved):
    """The answer to 'how many incidents': the retrieved passages that each describe one."""
    return sum(1 for p in retrieved if p["incident"])
```

Top-3 retrieves three incidents and counts short.

```text filename=aggregate.py --topk
TOPK — fixed top-3 retrieval
------------------------------------------------------------
  retrieved: ['p1', 'p2', 'p3']
  incidents counted = 3   (true count 5)
------------------------------------------------------------
  every retrieved passage is relevant, yet the count is short -- k stopped too early
```

Three of the five incidents, counted as 3 against a true 5 — and all three are correct, so nothing flags the error. Threshold retrieval gets them all.

```text filename=aggregate.py --threshold
THRESHOLD — retrieve every passage at or above relevance 0.50
------------------------------------------------------------
  retrieved: ['p1', 'p2', 'p3', 'p4', 'p5']
  incidents counted = 5   (true count 5)
------------------------------------------------------------
  the amount retrieved adapted to how much was relevant, so the count is complete
```

All five incident passages clear the 0.5 threshold and the two irrelevant ones do not, so threshold retrieval returns exactly the five and counts the true 5. The figure shows the two cutoffs against the ranked passages.

<svg role="img" aria-label="Seven passages ranked by relevance: p1 to p5 are incidents scoring 0.90 down to 0.80, p6 and p7 are non-incidents at 0.30 and 0.25. A top-3 line falls after p3, capturing three incidents. A threshold line at 0.5 falls after p5, capturing all five incidents and excluding p6 and p7." viewBox="0 0 640 220">
<rect x="60" y="40" width="180" height="18" fill="var(--s1)" opacity="0.7"/><text x="250" y="54" fill="var(--muted)" font-size="9">p1 incident 0.90</text>
<rect x="60" y="62" width="176" height="18" fill="var(--s1)" opacity="0.7"/><text x="250" y="76" fill="var(--muted)" font-size="9">p2 incident 0.88</text>
<rect x="60" y="84" width="170" height="18" fill="var(--s1)" opacity="0.7"/><text x="250" y="98" fill="var(--muted)" font-size="9">p3 incident 0.85</text>
<line x1="50" y1="106" x2="420" y2="106" stroke="var(--ink)" stroke-width="1.5" stroke-dasharray="5 3"/>
<text x="430" y="110" fill="var(--ink)" font-size="9">top-3 cut → count 3</text>
<rect x="60" y="110" width="166" height="18" fill="var(--s1)" opacity="0.7"/><text x="250" y="124" fill="var(--muted)" font-size="9">p4 incident 0.83</text>
<rect x="60" y="132" width="160" height="18" fill="var(--s1)" opacity="0.7"/><text x="250" y="146" fill="var(--muted)" font-size="9">p5 incident 0.80</text>
<line x1="50" y1="154" x2="420" y2="154" stroke="var(--s2)" stroke-width="1.5" stroke-dasharray="5 3"/>
<text x="430" y="158" fill="var(--s2)" font-size="9">threshold 0.5 → count 5</text>
<rect x="60" y="158" width="60" height="18" fill="var(--panel)" stroke="var(--line)"/><text x="250" y="172" fill="var(--muted)" font-size="9">p6 other 0.30</text>
<rect x="60" y="180" width="50" height="18" fill="var(--panel)" stroke="var(--line)"/><text x="250" y="194" fill="var(--muted)" font-size="9">p7 other 0.25</text>
</svg>
^ The top-3 cut lands in the middle of the relevant set and counts 3; the relevance threshold lands below all five incidents and above the two irrelevant passages, counting the true 5.

**The top-3 cut is not at a natural boundary in the data — it slices through the middle of five equally-relevant passages — while the threshold falls in the real gap between relevant and irrelevant, which is why it counts correctly.**

## Build

The self-test pins the asymmetry: the top-k count is short, the threshold count matches, and every incident passage was above the threshold — so retrieval quality is not the problem, the stopping rule is.

```python filename=modules/context-and-retrieval/code/aggregate-inter-01/aggregate.py:80-87 COMPLETE
    topk_undercounts = count_incidents(topk) < true
    print("  the top-%d count is short of the true count = %s (%d < %d)" % (data["top_k"], topk_undercounts, count_incidents(topk), true))

    threshold_correct = count_incidents(thr) == true
    print("  the threshold count matches the true count = %s (%d == %d)" % (threshold_correct, count_incidents(thr), true))

    all_incidents_relevant = all(p["relevance"] >= data["relevance_threshold"] for p in passages if p["incident"])
    print("  every incident passage is above the threshold (retrieval is not at fault) = %s" % all_incidents_relevant)
```

The remaining flags confirm top-k returned exactly k passages while the threshold returned at least the true count. All five pass.

```text filename=aggregate.py --check
SELF-TEST — the top-k count is short of the truth while the threshold count matches it, and every incident passage was above the threshold
----------------------------------------------------------------------------------------------------------------
  the top-3 count is short of the true count = True (3 < 5)
  the threshold count matches the true count = True (5 == 5)
  every incident passage is above the threshold (retrieval is not at fault) = True
  top-k returned exactly k passages (the cap) = True (3)
  threshold returned at least the true count of passages = True (5)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  topk_undercounts=True  threshold_correct=True  all_incidents_relevant=True  topk_returns_k=True  threshold_returns_all=True
```

**"Every incident passage is above the threshold" is the exoneration of the retriever: it ranked all five relevant passages correctly, and only the top-k cap kept two of them out — the bug is the stopping rule, not the ranking.**

## Definition of done

You are done when the retrieval stopping rule is chosen for the query's shape — a small top-k for needle queries, and a relevance threshold (or another size-adaptive rule) for counting and list-all queries whose answer is the whole relevant set.

The practical form is to stop by relevance rather than rank when the answer is an aggregate: retrieve every passage whose score clears a threshold, so a needle query pulls one or two passages and a counting query pulls all of them. This requires a comparable, calibrated relevance score, which raw cosine scores often are not across queries, so in practice you set the threshold from a held-out labeled set, or over-fetch a large k and then trim by score, or route by query type — a classifier or the LLM detecting "how many / list all" and switching to exhaustive retrieval. Two cautions. A threshold that is too low pulls in irrelevant passages and over-counts, the mirror failure, so the threshold must sit in the real gap between relevant and irrelevant — which is why calibrating it matters. And even exhaustive retrieval only counts what is in the corpus: if some incidents were never documented, no retrieval strategy recovers them, so a complete-looking count is complete relative to the index, not the world. Keep this separate from diversity fixes like capping chunks per document: that ensures multiple sources contribute to a single best answer, while this ensures the full set is retrieved for an answer that is a set.

<svg role="img" aria-label="A decision on the stopping rule by query type: a needle query 'what is X' uses a small top-k; an aggregation query 'how many / list all' uses a relevance threshold that retrieves the whole relevant set." viewBox="0 0 640 180">
<text x="320" y="28" fill="var(--muted)" font-size="12" text-anchor="middle">what shape is the answer?</text>
<text x="170" y="64" fill="var(--ink)" font-size="11" text-anchor="middle">needle: "what is X"</text>
<line x1="170" y1="74" x2="170" y2="104" stroke="var(--line)" stroke-width="1"/>
<polygon points="170,104 165,94 175,94" fill="var(--line)"/>
<rect x="60" y="106" width="220" height="46" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="170" y="126" fill="var(--ink)" font-size="10" text-anchor="middle">small top-k</text>
<text x="170" y="142" fill="var(--muted)" font-size="9" text-anchor="middle">the answer is in the best few</text>
<text x="470" y="64" fill="var(--ink)" font-size="11" text-anchor="middle">aggregate: "how many / list all"</text>
<line x1="470" y1="74" x2="470" y2="104" stroke="var(--line)" stroke-width="1"/>
<polygon points="470,104 465,94 475,94" fill="var(--line)"/>
<rect x="360" y="106" width="220" height="46" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="470" y="126" fill="var(--ink)" font-size="10" text-anchor="middle">relevance threshold</text>
<text x="470" y="142" fill="var(--muted)" font-size="9" text-anchor="middle">retrieve the whole relevant set</text>
</svg>
^ Choose the stopping rule by the answer's shape: the top few for a needle, everything above the relevance bar for an aggregate.

**A relevance threshold makes the amount retrieved a function of how much is relevant rather than a constant, so it serves both query shapes — a needle query naturally clears it with one or two passages, and an aggregation query with all of them.**

## Boss fight

Your turn: raise the fixed k and watch it fail from the other side. Set `top_k` to 7 — larger than the five incidents — and rerun `--topk`. Now the retrieval includes p6 and p7, the two irrelevant passages, and if the counting logic is not careful to check relevance it will count them too and over-count, or if it counts only true incidents it gets the right 5 but at the cost of stuffing two irrelevant passages into the model's context. This is why a bigger constant is not the fix: too small undercounts, too large drags in noise, and the right size is different for every query because it depends on how many passages are actually relevant. Only a rule that adapts to the data — the threshold — gets both a needle query and an aggregation query right without a per-query constant you cannot know in advance.

Then confront the hard prerequisite the threshold needs. Change p4's and p5's relevance to 0.45 — still clearly relevant incidents, but now below the 0.5 threshold. Threshold retrieval drops them and counts 3, the same undercount top-k made, because the threshold was set above the real boundary. The threshold only works if it sits in the genuine gap between relevant and irrelevant, and raw retrieval scores are frequently not comparable across queries — a score of 0.5 might mean "very relevant" for one query and "barely related" for another. So the honest version of this fix is not "pick 0.5" but "calibrate the cutoff," from labeled data or per-query score statistics, so that "above threshold" reliably means "relevant." Without that calibration the threshold just relocates the arbitrary cutoff from a rank to a score, and an aggregation answer can be truncated just the same.

**A relevance threshold fixes aggregation only when it is calibrated to the real relevant/irrelevant boundary — an uncalibrated threshold is just a fixed cutoff in score space instead of rank space, and it truncates the answer set exactly as a fixed k does.**

## External resources

The retrieval-augmented generation literature distinguishes "extractive" or single-answer questions from "aggregation" or "counting" questions, and notes that fixed top-k retrieval is a poor fit for the latter — surveys of RAG failure modes catalog this as a distinct class of query.

Work on adaptive and query-dependent retrieval (self-RAG, adaptive-k, and confidence-thresholded retrieval) formalizes stopping by relevance or by an estimated answer size rather than a constant k, which is the size-adaptive rule this module argues for.

Guides on calibrating retrieval score thresholds (per-query score normalization, and setting cutoffs from labeled relevance judgments) address the prerequisite the boss fight raises — that a threshold only works when it corresponds to a real relevance boundary.
