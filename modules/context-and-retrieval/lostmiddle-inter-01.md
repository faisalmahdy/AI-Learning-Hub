---
id: lostmiddle-inter-01
title: Put the most relevant documents at the ends of the context — a model attends least to the middle, so a gold passage buried there goes unused
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: You retrieve the right documents and paste them into the context, and the model still misses the answer — the retrieval was not the problem, the order was. A long-context model does not read its context uniformly: it attends most strongly to the beginning and the end and least to the middle, an empirically robust "lost in the middle" effect. So a document's usefulness depends not only on whether it is in the context but on where; the same gold passage that would be used at position one or last can be effectively invisible sitting in the middle of a stack of retrieved documents. The naive pipeline triggers this easily — retrieve top-k, place documents in whatever order the retriever returned, hand the block to the model — because retrievers rank by relevance, not by where relevance should sit, so the most relevant document can land in the low-attention middle. It is in the context; the model just does not lean on it, and the failure looks like a retrieval miss when the document was right there in the dead zone. The fix reorders the retrieved documents to match the context's attention profile: highest relevance at one end, next at the other, folding inward, so the strongest documents occupy the high-attention positions and the weakest fall into the middle where being under-attended costs least. On a fixture where the gold document d2 (most relevant, relevance 9) is returned in the middle of the retriever's order, naive placement gives it positional weight 0.2 — below the 0.4 recall threshold, so it is lost — while edge reordering puts it at an end (weight 1.0, used) and raises the total effective signal from 11.3 to 17.9.
eli5: Imagine you hand someone a tall stack of note cards and ask them to find an answer, but they only really read the top few cards and the bottom few — the ones in the middle they barely glance at. If you put the one card that actually has the answer right in the middle of the stack, they will probably miss it and tell you the answer is not there, even though it is. The card was in the stack; they just did not look at it. The trick is to put your best cards on the top and the bottom, where they actually read carefully, and leave the least important ones for the middle. Same cards, better order, and now they find the answer.
---

## Why this module

There is a failure mode in retrieval-augmented systems that survives a perfect retriever. You fetch exactly the right documents, they are all in the context window, and the model still answers as if the key passage were missing. It is tempting to blame retrieval and go tune the embeddings, but the documents are there — the problem is that the context window is not a uniform place, and where a document sits changes whether the model uses it. This is worth understanding because it is a cheap fix that people skip: reordering costs nothing and no amount of better retrieval addresses it.

The cause is a measured property of long-context models: attention is U-shaped over position. Information at the very start and the very end of the context is used reliably; information in the middle is used much less, sometimes barely at all. So a retrieved document has two things that determine its value — its relevance, and its position — and a pipeline that optimizes only the first while ignoring the second can place its single most relevant document into the exact region the model neglects. The document is present, the retrieval metrics look great, and the answer is still wrong.

The fix aligns placement with the attention profile instead of leaving it to retrieval rank. This module places the same five retrieved documents two ways — in retrieval order and reordered to the edges — and measures whether the gold document lands where the model will actually attend to it.

**Order retrieved documents so the most relevant sit at the start and end of the context and the least relevant in the middle, rather than pasting them in retrieval-rank order, because a model attends least to the middle of a long context — so a highly relevant document placed there is present but effectively unused, while edge placement puts it where the model actually attends.**

## Concepts

The fixture models the attention bias as a per-position weight: how much of a document's content the model effectively uses at that context position. The weights are U-shaped — 1.0 at the two ends, 0.2 in the middle — and a document needs a positional weight of at least 0.4 (the recall threshold) to be used rather than lost. The gold document, d2, is the most relevant (relevance 9), but the retriever returned it in the middle of its ranking.

```json filename=modules/context-and-retrieval/code/lostmiddle-inter-01/lostmiddle.json:3-13 COMPLETE
  "positional_weights": [1.0, 0.5, 0.2, 0.5, 1.0],
  "recall_threshold": 0.4,
  "gold": "d2",
  "retrieved_order": [
    {"id": "d1", "relevance": 3},
    {"id": "d3", "relevance": 5},
    {"id": "d2", "relevance": 9},
    {"id": "d5", "relevance": 4},
    {"id": "d4", "relevance": 2}
  ]
```

Naive placement is the identity — documents go in the order the retriever returned them. Edge placement is the fix: sort by relevance, then fold the ranking onto the positions, placing the top document at one end, the second at the other, and working inward, so the highest-relevance documents occupy the highest-weight positions.

```python filename=modules/context-and-retrieval/code/lostmiddle-inter-01/lostmiddle.py:53-71 COMPLETE
def naive_placement(docs):
    """Place documents in the order the retriever returned them."""
    return list(docs)


def edge_placement(docs):
    """Reorder by relevance to the edges: highest at one end, next at the other, folding inward."""
    ranked = sorted(docs, key=lambda d: (-d["relevance"], d["id"]))
    slots = [None] * len(ranked)
    left, right = 0, len(ranked) - 1
    for i, d in enumerate(ranked):
        if i % 2 == 0:
            slots[left] = d
            left += 1
        else:
            slots[right] = d
            right -= 1
    return slots
```

Two measurements score a placement. The gold document's positional weight decides whether it clears the recall threshold, and the total effective signal — each document's relevance times its position's weight — measures how much usable information the whole arrangement delivers.

```python filename=modules/context-and-retrieval/code/lostmiddle-inter-01/lostmiddle.py:74-87 COMPLETE
def gold_weight(placement, weights, gold):
    """The positional weight of the slot the gold document lands in."""
    for i, d in enumerate(placement):
        if d["id"] == gold:
            return weights[i], i
    return 0.0, -1


def effective_signal(placement, weights):
    """Total attended signal: each document's relevance times its position's weight."""
    return sum(d["relevance"] * weights[i] for i, d in enumerate(placement))
```

<svg role="img" aria-label="A U-shaped curve of attention weight over five context positions, high at the ends and low in the middle, with the gold document marked at the low middle point" viewBox="0 0 320 150">
  <line x1="30" y1="20" x2="30" y2="120" stroke="var(--line)" stroke-width="1"/>
  <line x1="30" y1="120" x2="300" y2="120" stroke="var(--line)" stroke-width="1"/>
  <line x1="30" y1="72" x2="300" y2="72" stroke="var(--ink)" stroke-width="1" stroke-dasharray="4 3"/>
  <text x="2" y="34" font-size="8" fill="var(--muted)">1.0</text>
  <text x="4" y="76" font-size="8" fill="var(--ink)">0.4</text>
  <text x="2" y="118" font-size="8" fill="var(--muted)">0.2</text>
  <polyline points="55,30 120,72 175,112 230,72 290,30" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <circle cx="55" cy="30" r="3" fill="var(--s2)"/>
  <circle cx="120" cy="72" r="3" fill="var(--s2)"/>
  <circle cx="175" cy="112" r="4" fill="var(--s1)"/>
  <circle cx="230" cy="72" r="3" fill="var(--s2)"/>
  <circle cx="290" cy="30" r="3" fill="var(--s2)"/>
  <text x="120" y="132" font-size="8.5" fill="var(--s1)">gold d2 lands here (weight 0.2, below the 0.4 line)</text>
  <text x="200" y="46" font-size="8.5" fill="var(--muted)">ends: attended</text>
</svg>
^ Attention weight is U-shaped over position: high at the ends, low in the middle, with the 0.4 recall threshold as the dashed line. Naive placement drops the gold document into the trough, below the line — present but unused.

**A retrieved document has two properties that decide its value — relevance and position — and a pipeline that orders only by relevance can place its best document exactly where the model attends least.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the context-assembly step of a retrieval pipeline, reduced to five documents so every placement and weight is checkable by hand.

Run `--place` to see the two arrangements and each document's positional weight.

```text filename=lostmiddle.py --place
  position weights (U-shaped): [1.0, 0.5, 0.2, 0.5, 1.0]
  naive : d1(r3,w1.0) d3(r5,w0.5) d2(r9,w0.2) d5(r4,w0.5) d4(r2,w1.0)
  edges : d2(r9,w1.0) d5(r4,w0.5) d4(r2,w0.2) d1(r3,w0.5) d3(r5,w1.0)
```

Read the naive row: the gold d2, with relevance 9, sits at the middle position with weight 0.2 — the model's least-attended slot. Meanwhile d1 (relevance 3) and d4 (relevance 2), the two weakest documents, sit at the two ends with weight 1.0. Relevance and position are anti-aligned: the best document is in the worst place. The edges row inverts that — d2 moves to position 0 (weight 1.0) and d3 (the second most relevant) to the last position (weight 1.0), while the weak documents fall into the middle.

Now `--signal` scores both.

```text filename=lostmiddle.py --signal
  gold = d2 (threshold to be used = 0.4)
  naive: gold at position 2, weight 0.2 -> LOST (below threshold)
  edges: gold at position 0, weight 1.0 -> USED
  total effective signal (sum relevance x weight):  naive = 11.3   edges = 17.9
```

Under naive placement the gold document's weight is 0.2, below the 0.4 threshold — it is in the context but the model does not lean on it, so the answer is missed. Under edge reordering the gold is at weight 1.0, comfortably used. And the total effective signal rises from 11.3 to 17.9: aligning relevance with position does not just rescue the gold document, it makes the whole context deliver more usable information, because every high-relevance document now sits where it is attended.

<svg role="img" aria-label="Two horizontal bars comparing total effective signal: naive at 11.3 and edges at 17.9, the edges bar noticeably longer" viewBox="0 0 320 110">
  <text x="10" y="30" font-size="9" fill="var(--s2)">naive order</text>
  <rect x="90" y="20" width="113" height="20" fill="var(--s2)"/>
  <text x="208" y="35" font-size="10" fill="var(--ink)">11.3</text>
  <text x="10" y="72" font-size="9" fill="var(--s1)">edge reorder</text>
  <rect x="90" y="62" width="179" height="20" fill="var(--s1)"/>
  <text x="274" y="77" font-size="10" fill="var(--ink)">17.9</text>
  <text x="90" y="100" font-size="8.5" fill="var(--muted)">total effective signal = sum(relevance x positional weight)</text>
</svg>
^ Total usable signal, both placements: aligning high relevance with high-attention positions lifts it from 11.3 to 17.9. The gain is the whole context working better, not just the gold document being rescued.

**Reordering the identical five documents moves the gold from weight 0.2 (lost) to 1.0 (used) and lifts total usable signal by more than half — the retrieval never changed, only the seating.**

## Build

The self-test asserts the whole causal chain: the weights are genuinely U-shaped, the gold is the most relevant document, naive placement buries it in a low-weight middle slot, and it falls below threshold there.

```python filename=modules/context-and-retrieval/code/lostmiddle-inter-01/lostmiddle.py:106-119 COMPLETE
    weights_u_shaped = weights[n // 2] < weights[0] and weights[n // 2] < weights[-1]
    print("  the position weights are U-shaped (middle < ends) = %s (mid %.1f < ends %.1f/%.1f)" % (weights_u_shaped, weights[n // 2], weights[0], weights[-1]))

    gold_is_most_relevant = gold == max(docs, key=lambda d: d["relevance"])["id"]
    print("  the gold document is the most relevant retrieved = %s" % gold_is_most_relevant)

    naive_buries_gold = 0 < ni < n - 1 and nw < thr
    print("  naive placement puts the gold in a low-weight middle slot = %s (position %d, weight %.1f < %.1f)" % (naive_buries_gold, ni, nw, thr))

    naive_loses_gold = nw < thr
    print("  under naive placement the gold is lost (below threshold) = %s" % naive_loses_gold)
```

<svg role="img" aria-label="Two rows of five slots; naive has the gold in the dark middle slot, edges has the gold in a bright end slot, with the weak documents moved to the middle" viewBox="0 0 320 130">
  <text x="10" y="22" font-size="9" fill="var(--muted)">naive</text>
  <rect x="60" y="12" width="34" height="22" fill="var(--s1)"/><text x="70" y="27" font-size="9" fill="var(--panel)">d1</text>
  <rect x="96" y="12" width="34" height="22" fill="var(--s1)" opacity="0.6"/><text x="106" y="27" font-size="9" fill="var(--panel)">d3</text>
  <rect x="132" y="12" width="34" height="22" fill="var(--muted)" stroke="var(--ink)" stroke-width="2"/><text x="142" y="27" font-size="9" fill="var(--panel)">d2</text>
  <rect x="168" y="12" width="34" height="22" fill="var(--s1)" opacity="0.6"/><text x="178" y="27" font-size="9" fill="var(--panel)">d5</text>
  <rect x="204" y="12" width="34" height="22" fill="var(--s1)"/><text x="214" y="27" font-size="9" fill="var(--panel)">d4</text>
  <text x="244" y="27" font-size="8" fill="var(--s2)">gold lost</text>
  <text x="10" y="82" font-size="9" fill="var(--muted)">edges</text>
  <rect x="60" y="72" width="34" height="22" fill="var(--s1)" stroke="var(--ink)" stroke-width="2"/><text x="70" y="87" font-size="9" fill="var(--panel)">d2</text>
  <rect x="96" y="72" width="34" height="22" fill="var(--s1)" opacity="0.6"/><text x="106" y="87" font-size="9" fill="var(--panel)">d5</text>
  <rect x="132" y="72" width="34" height="22" fill="var(--muted)"/><text x="142" y="87" font-size="9" fill="var(--panel)">d4</text>
  <rect x="168" y="72" width="34" height="22" fill="var(--s1)" opacity="0.6"/><text x="178" y="87" font-size="9" fill="var(--panel)">d1</text>
  <rect x="204" y="72" width="34" height="22" fill="var(--s1)"/><text x="214" y="87" font-size="9" fill="var(--panel)">d3</text>
  <text x="244" y="87" font-size="8" fill="var(--s1)">gold used</text>
</svg>
^ The dark middle slot is the low-attention zone. Naive parks the gold d2 there; edge reordering swaps it to a bright end slot and lets the weakest documents (d4) take the middle, where being under-attended costs least.

Running the check confirms every clause, including that edge reordering recovers the gold and raises the total signal.

```text filename=lostmiddle.py --check
  the position weights are U-shaped (middle < ends) = True (mid 0.2 < ends 1.0/1.0)
  the gold document is the most relevant retrieved = True
  naive placement puts the gold in a low-weight middle slot = True (position 2, weight 0.2 < 0.4)
  under naive placement the gold is lost (below threshold) = True
  edge reordering places the gold at an end position = True (position 0)
  under edge reordering the gold is used (at or above threshold) = True (weight 1.0)
  edge reordering raises the total effective signal = True (17.9 > 11.3)
```

**The check ties the miss to position, not retrieval — the gold was fetched and included, and only its middle placement made it unused — so the fix is reordering, not re-retrieving.**

## Definition of done

Two properties close it. Edge reordering must place the gold at an end position and lift it to or above the recall threshold — the direct rescue — and it must raise the total effective signal, showing the reorder helps the whole context, not only the one document.

```python filename=modules/context-and-retrieval/code/lostmiddle-inter-01/lostmiddle.py:121-127 COMPLETE
    edge_places_gold_at_end = ei == 0 or ei == n - 1
    print("  edge reordering places the gold at an end position = %s (position %d)" % (edge_places_gold_at_end, ei))

    edge_recovers_gold = ew >= thr
    print("  under edge reordering the gold is used (at or above threshold) = %s (weight %.1f)" % (edge_recovers_gold, ew))

    edge_raises_signal = effective_signal(edges, weights) > effective_signal(naive, weights)
    print("  edge reordering raises the total effective signal = %s (%.1f > %.1f)" % (edge_raises_signal, effective_signal(edges, weights), effective_signal(naive, weights)))
```

Two honest boundaries keep the tool from being over-applied. First, this models attention bias with a fixed U-shaped weight and a hard threshold; real models have a softer, model-specific curve, and the effect is strongest with many documents and long contexts — with two or three short documents in a small context there is barely a middle to get lost in, and reordering buys little. Second, edge reordering assumes you trust your relevance ranking enough to decide which documents deserve the edges; if the ranking is noisy, you may promote a wrong document to a high-attention slot. The robust reading is not "always fold to edges" but "position is a lever alongside relevance": when a long context forces a real middle, keep your best evidence out of it, and prefer including fewer, better documents over burying the best one in a long stack.

**Done means edge reordering moves the gold to an end above threshold and raises total usable signal — a placement fix for a positional failure, most valuable exactly when the context is long enough to have a neglected middle.**

## Boss fight

Your RAG system retrieves 15 passages per query and concatenates them in retrieval-score order into a long prompt. Evaluation shows a strange pattern: accuracy is high when the answer happens to be in the top-ranked passage or the bottom-ranked one, and noticeably lower when the retriever ranks the correct passage somewhere in positions 6 through 10 — even though those passages are clearly in the context. A colleague proposes retrieving more passages (top-25) to raise the chance of including the answer. Why will that not help, and what would?

Retrieving more passages does not help because the answer is already being retrieved and included — the failure is not a retrieval miss, it is that middle-ranked passages land in the low-attention middle of a long context and the model does not use them. Adding more passages makes this worse, not better: it lengthens the context, enlarges the neglected middle, and pushes even more content into it, so the mid-ranked correct passage is buried deeper. The U-shaped accuracy pattern your evaluation shows is the signature of the lost-in-the-middle effect, not of incomplete retrieval. What helps is changing placement and length rather than fetching more: reorder the retrieved passages so the highest-relevance ones sit at the start and end of the prompt and the weakest fill the middle, and reduce the number of passages so there is less dead middle to fall into — a tighter set of well-placed passages beats a longer stack that buries the good ones. If the concern is that the relevance ranking is imperfect, add a reranking step so the passages you promote to the edges are the ones most likely to hold the answer. The lever is position and count, not recall.

## External resources

Liu et al., "Lost in the Middle: How Language Models Use Long Contexts" — the paper that measured the U-shaped position bias this module models, showing accuracy dropping sharply when the relevant document sits in the middle of a long context across multiple models.

The LangChain `LongContextReorder` document transformer and LongLLMLingua's document reordering — production implementations of exactly the edge-placement fix here, taking a ranked list of retrieved documents and interleaving them to the ends so the most relevant occupy the high-attention positions.
