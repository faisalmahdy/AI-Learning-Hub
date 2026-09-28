---
id: distsign-inter-01
title: Sort by the index's actual metric — a distance is smallest-first and a similarity largest-first, and confusing them returns the least relevant results
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: A vector index answers a query with one number per document, and that number is one of two opposite kinds: a similarity (cosine, inner product), where higher means more relevant, or a distance (Euclidean L2, or one minus cosine), where lower means more relevant. The correct sort direction depends entirely on which one the index returns. The trap is that many indexes return a distance by default — FAISS's flat and IVF indexes return squared L2 distance — and a distance is still just a float, so it is easy to treat it as a score and sort descending to take the top results. Sorting a distance descending takes the largest distances, which are the farthest, least-relevant documents, in exactly reversed order; the mirror mistake is sorting a similarity ascending. The failure is silent because the retriever still returns k results with real numbers through the same interface a correct retriever uses — they are simply the worst matches instead of the best, and the model downstream answers from confidently-scored irrelevant context. The fix is to know which metric the index returns and sort to match it: smallest-first for a distance, largest-first for a similarity, and confirm with a known-perfect match that it comes out on top. On a fixture where four documents carry both a distance and a similarity to the query, sorting the distance ascending puts the reset guide (distance 0.2) first and shipping info (distance 1.4) last, while sorting that same distance descending — as if it were a similarity — puts shipping info first and reverses the entire ranking.
eli5: Imagine ranking runners in a race two different ways. One scoreboard shows finishing time, where the smallest number is the winner. Another shows points scored, where the biggest number is the winner. If you glance at the finishing-time board but rank people as if it were points — biggest number on top — you crown the slowest runner as the champion and put the actual winner last. The number is just a number; whether big or small means "best" depends on which board you are reading. A search index has the same two kinds of scoreboard — distance, where small wins, and similarity, where big wins — and reading one as the other hands you the worst matches while looking exactly like it handed you the best.
---

## Why this module

Vector search ends in a sort: score every candidate document against the query, order them, take the top k. The scoring is where all the attention goes — which embedding model, cosine or dot product — and the sort at the end looks like a formality. It is not, because the score can run in either of two directions, and the sort has to know which.

There are two conventions, and they are opposites. A similarity score is larger when the document is a better match: cosine similarity, inner product. A distance is smaller when the document is a better match: Euclidean (L2) distance, or one minus cosine. Both are single floating-point numbers attached to each document, indistinguishable by type, and only the metric's convention tells you whether "best" is the biggest or the smallest.

The trap is that a distance is a perfectly good-looking score, and the reflex — for anyone used to similarities — is to sort descending and take the highest. Do that to a distance and you take the largest distances, which are the farthest documents: the least relevant, returned in precisely reversed order. And many popular indexes return a distance by default, so this is not a rare confusion — it is the default output meeting the default sort.

**A vector index returns either a similarity (higher is better) or a distance (lower is better); the correct sort direction is opposite for the two, so sorting a distance the way you sort a similarity returns the farthest, least-relevant documents in reversed order.**

## Concepts

Fix the two directions in mind. Similarity increases toward relevance — the best match has the highest similarity, so you sort descending. Distance increases away from relevance — the best match has the lowest distance, so you sort ascending. They are mirror images: on unit vectors, in fact, similarity and distance are monotonically related, so the very same ranking comes out either way — but only if you sort each in its own direction.

<svg role="img" aria-label="Two axes for the same documents. The distance axis runs left (0, nearest, best) to right (large, farthest, worst). The similarity axis runs the opposite way, left (low, worst) to right (high, best). The best document sits at the low-distance, high-similarity end." viewBox="0 0 440 130">
<text x="20" y="18" fill="var(--muted)" font-size="9">the two metrics run in opposite directions</text>
<line x1="40" y1="50" x2="400" y2="50" stroke="var(--line)"/>
<text x="40" y="42" fill="var(--s1)" font-size="8">distance 0 (best)</text>
<text x="400" y="42" fill="var(--s2)" font-size="8" text-anchor="end">distance large (worst)</text>
<circle cx="60" cy="50" r="4" fill="var(--s1)"/><text x="60" y="66" fill="var(--s1)" font-size="7" text-anchor="middle">nearest</text>
<circle cx="380" cy="50" r="4" fill="var(--s2)"/><text x="380" y="66" fill="var(--s2)" font-size="7" text-anchor="middle">farthest</text>
<line x1="40" y1="95" x2="400" y2="95" stroke="var(--line)"/>
<text x="40" y="87" fill="var(--s2)" font-size="8">similarity low (worst)</text>
<text x="400" y="87" fill="var(--s1)" font-size="8" text-anchor="end">similarity high (best)</text>
<circle cx="60" cy="95" r="4" fill="var(--s2)"/>
<circle cx="380" cy="95" r="4" fill="var(--s1)"/>
<text x="220" y="120" fill="var(--muted)" font-size="8" text-anchor="middle">same documents, mirrored axes — sort each toward its "best" end</text>
</svg>
^ Distance and similarity point opposite ways: the best document is at the low-distance end and the high-similarity end, so a distance sorts ascending and a similarity descending.

Now the bug as a picture. Take a distance and sort it descending, the way you would a similarity. Descending on a distance puts the largest distance on top — the farthest document, the worst match — and the smallest distance, the true best, at the bottom. Every position is inverted. It is not "slightly off" or "approximately right"; it is the exact reverse of the correct ranking, so the top-k you return is the bottom-k you should have returned.

<svg role="img" aria-label="A distance sorted two ways. Ascending (correct) lists the nearest document first; descending (buggy, treating distance as a similarity) lists the farthest first, the exact reverse." viewBox="0 0 440 130">
<text x="110" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">distance ascending (correct)</text>
<rect x="50" y="26" width="130" height="14" fill="var(--s1)"/><text x="115" y="37" fill="var(--ink)" font-size="8" text-anchor="middle">nearest (0.2)</text>
<rect x="50" y="42" width="130" height="14" fill="var(--panel)" stroke="var(--line)"/><text x="115" y="53" fill="var(--ink)" font-size="8" text-anchor="middle">0.5</text>
<rect x="50" y="58" width="130" height="14" fill="var(--panel)" stroke="var(--line)"/><text x="115" y="69" fill="var(--ink)" font-size="8" text-anchor="middle">0.9</text>
<rect x="50" y="74" width="130" height="14" fill="var(--panel)" stroke="var(--line)"/><text x="115" y="85" fill="var(--ink)" font-size="8" text-anchor="middle">farthest (1.4)</text>
<text x="330" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">distance descending (buggy)</text>
<rect x="270" y="26" width="130" height="14" fill="var(--s2)"/><text x="335" y="37" fill="var(--ink)" font-size="8" text-anchor="middle">farthest (1.4)</text>
<rect x="270" y="42" width="130" height="14" fill="var(--panel)" stroke="var(--line)"/><text x="335" y="53" fill="var(--ink)" font-size="8" text-anchor="middle">0.9</text>
<rect x="270" y="58" width="130" height="14" fill="var(--panel)" stroke="var(--line)"/><text x="335" y="69" fill="var(--ink)" font-size="8" text-anchor="middle">0.5</text>
<rect x="270" y="74" width="130" height="14" fill="var(--panel)" stroke="var(--line)"/><text x="335" y="85" fill="var(--ink)" font-size="8" text-anchor="middle">nearest (0.2)</text>
<text x="220" y="108" fill="var(--muted)" font-size="8" text-anchor="middle">the buggy top is the correct bottom — the whole list is reversed</text>
</svg>
^ Sorting a distance descending, as if it were a similarity, lifts the farthest document to the top and buries the nearest — the exact reverse of the correct ascending order.

What makes it dangerous is that nothing looks wrong. The retriever returns k documents, each with a real number, through the same call a correct retriever uses; a smoke test that just checks "did it return results" passes. The results are simply the least relevant ones, so the model is handed confidently-scored off-topic context and answers from it — a quality collapse with no error and no obvious cause, because the scores are all present and plausible.

The fix is to treat the metric's direction as a fact about the index that you confirm, not assume. Know whether your index returns a distance or a similarity — read its docs; FAISS L2 is a distance, a cosine index is a similarity — and sort accordingly. The cheap confirmation is to query with a document you know is a perfect match and check it comes out on top; if the perfect match lands at the bottom, your sort direction is backwards.

**Sort a distance ascending and a similarity descending; sorting a distance descending reverses the entire ranking silently, so confirm the metric's direction from the index and verify a known-perfect match ranks first.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/distsign-inter-01. The fixture is a query and four documents, each carrying both its distance and its similarity to the query.

```json filename=modules/context-and-retrieval/code/distsign-inter-01/distsign.json:3-9 COMPLETE
  "query": "how do I reset my password",
  "docs": {
    "reset_guide": {"distance": 0.2, "similarity": 0.95},
    "login_help": {"distance": 0.5, "similarity": 0.70},
    "billing_faq": {"distance": 0.9, "similarity": 0.40},
    "shipping_info": {"distance": 1.4, "similarity": 0.10}
  }
```

The correct ranking for a distance metric sorts ascending — smallest distance first.

```python filename=modules/context-and-retrieval/code/distsign-inter-01/distsign.py:32-34 COMPLETE
def rank_by_distance(docs):
    """Correct for a distance metric: smallest distance first (nearest = most relevant)."""
    return sorted(docs, key=lambda d: docs[d]["distance"])
```

The correct ranking for a similarity metric sorts descending — largest similarity first.

```python filename=modules/context-and-retrieval/code/distsign-inter-01/distsign.py:37-39 COMPLETE
def rank_by_similarity(docs):
    """Correct for a similarity metric: largest similarity first."""
    return sorted(docs, key=lambda d: docs[d]["similarity"], reverse=True)
```

The bug treats the distance as a score and sorts it descending — largest distance first.

```python filename=modules/context-and-retrieval/code/distsign-inter-01/distsign.py:42-44 COMPLETE
def distance_sorted_as_similarity(docs):
    """The bug: treat the distance as a score and sort it descending -- largest distance first."""
    return sorted(docs, key=lambda d: docs[d]["distance"], reverse=True)
```

Before running it, predict: the reset guide has the smallest distance (0.2) and the highest similarity (0.95), so it is the true best; sorting the distance descending should put it last and the shipping info (distance 1.4) first. Run `--scores` then `--rank`:

```text filename=distsign.py --scores
SCORES — distance (lower better) and similarity (higher better) to the query
--------------------------------------------------------
  document        distance   similarity
  reset_guide     0.20       0.95
  login_help      0.50       0.70
  billing_faq     0.90       0.40
  shipping_info   1.40       0.10
--------------------------------------------------------
  the two metrics run in opposite directions
```

```text filename=distsign.py --rank
RANK — correct (distance ascending) vs distance sorted as a similarity
--------------------------------------------------------
  correct top-k : ['reset_guide', 'login_help', 'billing_faq', 'shipping_info']
  buggy   top-k : ['shipping_info', 'billing_faq', 'login_help', 'reset_guide']
--------------------------------------------------------
  the buggy sort returns the farthest documents first -- the least relevant
```

The prediction holds, completely. The scores table shows the two metrics moving in opposite directions: reset_guide is best on both (lowest distance, highest similarity), shipping_info worst on both. The correct ranking, distance ascending, is reset_guide, login_help, billing_faq, shipping_info — best to worst. The buggy ranking, distance descending, is shipping_info, billing_faq, login_help, reset_guide — the exact reverse. The document you most want to retrieve for "how do I reset my password," the reset guide, is dead last under the bug, and the shipping info is served first.

That total reversal is the signature. A ranking bug that merely perturbed the order would swap a few neighbors; this one inverts the whole list, because negating the sort direction of a monotone key reverses it exactly. The top result is not just suboptimal — it is the single worst match in the set.

<svg role="img" aria-label="The correct ranking and the buggy ranking side by side, with lines connecting the same document across the two lists, showing every line crosses because the order is fully reversed." viewBox="0 0 440 140">
<text x="90" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">correct</text>
<text x="350" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">buggy</text>
<text x="70" y="34" fill="var(--s1)" font-size="8" text-anchor="end">reset_guide</text><circle cx="80" cy="30" r="3" fill="var(--s1)"/>
<text x="70" y="58" fill="var(--ink)" font-size="8" text-anchor="end">login_help</text><circle cx="80" cy="54" r="3" fill="var(--ink)"/>
<text x="70" y="82" fill="var(--ink)" font-size="8" text-anchor="end">billing_faq</text><circle cx="80" cy="78" r="3" fill="var(--ink)"/>
<text x="70" y="106" fill="var(--s2)" font-size="8" text-anchor="end">shipping_info</text><circle cx="80" cy="102" r="3" fill="var(--s2)"/>
<circle cx="360" cy="30" r="3" fill="var(--s2)"/><text x="370" y="34" fill="var(--s2)" font-size="8">shipping_info</text>
<circle cx="360" cy="54" r="3" fill="var(--ink)"/><text x="370" y="58" fill="var(--ink)" font-size="8">billing_faq</text>
<circle cx="360" cy="78" r="3" fill="var(--ink)"/><text x="370" y="82" fill="var(--ink)" font-size="8">login_help</text>
<circle cx="360" cy="102" r="3" fill="var(--s1)"/><text x="370" y="106" fill="var(--s1)" font-size="8">reset_guide</text>
<line x1="80" y1="30" x2="360" y2="102" stroke="var(--s1)"/>
<line x1="80" y1="54" x2="360" y2="78" stroke="var(--grid)"/>
<line x1="80" y1="78" x2="360" y2="54" stroke="var(--grid)"/>
<line x1="80" y1="102" x2="360" y2="30" stroke="var(--s2)"/>
</svg>
^ Every connecting line crosses: the best document (reset_guide) travels from first to last and the worst (shipping_info) from last to first — a full reversal, not a small perturbation.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that the correct top result is the nearest document, that the buggy top result is the farthest, that the buggy ranking is the exact reverse of the correct one, that distance-ascending and similarity-descending agree, and that the buggy top result has the lowest similarity of all.

```python filename=modules/context-and-retrieval/code/distsign-inter-01/distsign.py:82-94 COMPLETE
    correct_top_is_nearest = correct[0] == nearest
    print("  the correct top result is the nearest document = %s (%s, distance %.2f)" % (correct_top_is_nearest, correct[0], docs[correct[0]]["distance"]))

    buggy_top_is_farthest = buggy[0] == farthest
    print("  the buggy top result is the farthest document = %s (%s, distance %.2f)" % (buggy_top_is_farthest, buggy[0], docs[buggy[0]]["distance"]))

    ranking_reversed = buggy == correct[::-1]
    print("  the buggy ranking is the exact reverse of the correct one = %s" % ranking_reversed)

    distance_and_similarity_agree = rank_by_distance(docs) == rank_by_similarity(docs)
    print("  distance-ascending and similarity-descending give the same correct order = %s" % distance_and_similarity_agree)

    buggy_top_is_least_relevant = docs[buggy[0]]["similarity"] == min(docs[d]["similarity"] for d in docs)
    print("  the buggy top result has the lowest similarity of all = %s (similarity %.2f)" % (buggy_top_is_least_relevant, docs[buggy[0]]["similarity"]))
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the buggy sort ever stopped reversing the order or the two correct metrics ever disagreed:

```text filename=distsign.py --check
SELF-TEST — sorting a distance descending returns the farthest documents, exactly reversing the correct order
----------------------------------------------------------------------------------------------------------------
  the correct top result is the nearest document = True (reset_guide, distance 0.20)
  the buggy top result is the farthest document = True (shipping_info, distance 1.40)
  the buggy ranking is the exact reverse of the correct one = True
  distance-ascending and similarity-descending give the same correct order = True
  the buggy top result has the lowest similarity of all = True (similarity 0.10)
```

**The self-test cross-checks the two metrics against each other — distance-ascending must equal similarity-descending — so a pass certifies which direction is correct independently of the distance sort alone, and then that the buggy sort inverts it and serves the least-similar document.**

## Definition of done

You can state the two metric conventions and which sort direction each requires.
You can explain why sorting a distance descending returns the farthest, least-relevant documents.
You can explain why the failure is a total reversal rather than a small perturbation.
You can explain why the bug is silent — real numbers, k results, the same interface — and how it surfaces downstream.
You can describe how to confirm the metric's direction (read the index's docs; verify a known-perfect match ranks first).

## Boss fight

Suppose your index returns squared L2 distance and you correctly sort ascending, but a downstream component expects a similarity in [0, 1] to threshold on (a relevance floor, say). Reason about the conversion. You cannot just negate the distance and call it a similarity — a negated distance is unbounded and has no fixed scale, so a threshold picked for cosine will not transfer. The principled conversions depend on the metric: for unit-normalized vectors, squared L2 and cosine are related by cosine = 1 − L2squared/2, an exact monotone map you can invert to recover a bounded similarity; for a raw distance with no such relation, you can only rank, not threshold, unless you calibrate the distance-to-relevance mapping empirically. The lesson: sorting only needs the direction, but any component that compares scores to an absolute threshold needs the actual metric and its scale, so mixing a distance-based index with a similarity-based threshold silently mis-thresholds even when the sort is right.

Now the trap that hides a sign bug from your tests. The most common way this ships is a metric change that the sort code does not track: someone swaps the index from cosine (similarity) to L2 (distance) for performance, or a library updates its default, and the retrieval code that sorted descending is now sorting a distance descending — instantly reversed, with no code change at the sort site. Unit tests written against the old metric may still pass if they mock the scores with the old convention. The defenses are to make the metric explicit and coupled to the sort (a single retrieval function that knows its index's metric and chooses the direction, never a bare sorted(..., reverse=True) scattered in callers), and to include an end-to-end test with a known-relevant document that must rank first regardless of metric — the one check that catches a reversal however it was introduced. Direction is a property of the metric, so bind them together rather than hard-coding a direction that a metric change can silently invalidate.

**A distance cannot be thresholded as a similarity without the metric's exact scale (for unit vectors, cosine = 1 − L2squared/2), so ranking needs only direction but absolute thresholds need the true metric; and because a metric swap silently reverses a hard-coded sort direction, couple the direction to the index's metric and keep an end-to-end test that a known-relevant document ranks first.**

## External resources

The FAISS documentation states which indexes return which metric (L2 distance versus inner product) and how to request each, the single most common source of this reversal.
Vector-database references (pgvector's distance operators, and the metric options in Pinecone, Weaviate, Milvus, Qdrant) document per-metric ordering and the distance-to-similarity conversions.
The topic's own module on ranking by cosine versus raw dot product covers the neighboring metric-choice question — which score to compute — while this one is about sorting whichever score you get in the correct direction.
