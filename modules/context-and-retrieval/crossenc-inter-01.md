---
id: crossenc-inter-01
title: Retrieve with the bi-encoder, rerank with the cross-encoder — or you pay accuracy for scale, or scale for accuracy
topic: context-and-retrieval
level: intermediate
status: ready
time: 18 min
summary: Two encoder architectures score a query against a document with opposite trade-offs. A bi-encoder embeds the query and each document separately, then scores by dot product — so document vectors precompute once and a query-time search over millions is cheap, but it never sees query and document together and cannot judge whether the document addresses the query jointly rather than merely containing its words. A cross-encoder reads the query and document together in one pass, catching the interaction and judging whole-query coverage — far more accurate, but the score depends on the pair, so there is nothing to precompute and it cannot scale to millions. The resolution is to retrieve a shortlist with the cheap bi-encoder and rerank just that shortlist with the accurate cross-encoder. On a fixture, the bi-encoder ranks a term-padded doc first (term count 5) over the true answer (2), the cross-encoder ranks the answer first (covers both query aspects, 2 vs 1), and reranking the bi-encoder's top 2 recovers the answer while scoring 2 pairs, not all 3.
eli5: To find the best matching sock in a huge pile, you first grab everything roughly the right color — fast, but you might grab a few wrong ones. Then you hold each candidate up next to the sock you have and check it carefully — slow, so you only do it for the handful you grabbed, not the whole pile. The fast rough grab is the bi-encoder; the careful side-by-side check is the cross-encoder; doing the careful check only on the shortlist is how you get both speed and accuracy.
---

## Why this module

Scoring a query against a document either lets you precompute the documents (fast, but blind to how query and document interact) or reads them together (accurate, but nothing to precompute) — and a search engine needs both properties at once.

A bi-encoder turns the query into a vector and each document into a vector, independently, and scores a pair by the similarity of the two vectors. The decisive property is that a document's vector does not depend on the query, so you compute all the document vectors once, ahead of time, and at query time a nearest-neighbor search over millions of them is cheap. But that same independence is a blind spot: the bi-encoder scores the query and document in isolation and combines them only at the very end with a dot product, so it cannot represent an *interaction* between them — whether the document actually answers the query as a whole rather than just containing its terms. A document that repeats one query word many times can score high while ignoring the rest of the query, and the bi-encoder, having compressed each side to a fixed vector separately, is fooled.

**A bi-encoder embeds query and document separately so document vectors precompute and search is cheap, but it never sees the pair together and so cannot judge whether a document jointly addresses the whole query.**

A cross-encoder reads the query and document together, in a single pass, so every word of the query can attend to every word of the document. It sees the interactions and judges whole-query coverage, and it is far more accurate. Its cost is the mirror of the bi-encoder's virtue: because the score depends on the specific pair, there is nothing to precompute — you must run the model on each (query, document) pair — so it cannot be run over millions. The resolution uses each for its strength: retrieve a shortlist cheaply with the bi-encoder, then rerank only that shortlist with the cross-encoder. This module scores documents both ways and shows the bi-encoder misrank, the cross-encoder fix it, and reranking recover the answer at a fraction of the cross-encoder's full cost.

## Concepts

A **bi-encoder** encodes the query and each document into separate vectors and scores by their similarity. Document vectors are query-independent, so they precompute and search is cheap over huge corpora.

The **bi-encoder's blind spot** is interaction: it compresses each side alone, so it cannot tell whether a document addresses the whole query or merely repeats some of its words.

A **cross-encoder** encodes the query and document jointly, in one pass, so it captures every interaction and judges whole-query coverage — much more accurate.

```python filename=modules/context-and-retrieval/code/crossenc-inter-01/crossenc.py:43-50 COMPLETE
def bi_score(doc, query):
    """Bi-encoder stand-in: total query-term occurrences (separable, precomputable, no interaction)."""
    return sum(count for term, count in doc.items() if term in query)


def cross_score(doc, query):
    """Cross-encoder stand-in: how many DISTINCT query aspects the doc covers (joint, sees the interaction)."""
    return sum(1 for term in query if term in doc)
```

The **cross-encoder's cost** is that its score depends on the pair, so nothing precomputes — it must run per (query, document) pair, which does not scale to millions.

**Retrieve then rerank** uses both: the bi-encoder's scale gets the answer into the top-k, and the cross-encoder's accuracy pulls it to the top, paying the per-pair cost only on the k shortlisted documents.

**The two architectures trade scale against interaction-awareness in exactly opposite directions, so the standard pipeline retrieves a shortlist with the cheap bi-encoder and reranks only that shortlist with the accurate cross-encoder.**

<svg role="img" aria-label="A bi-encoder encodes query and document into separate vectors then dots them; a cross-encoder feeds both together into one model" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">bi-encoder: separate → dot   cross-encoder: joint → score</text>
  <text x="8" y="34" fill="var(--s2)" font-size="8">bi</text>
  <rect x="30" y="26" width="34" height="14" fill="var(--s2)"/><text x="34" y="36" fill="var(--panel)" font-size="7">query</text>
  <rect x="30" y="44" width="34" height="14" fill="var(--s2)"/><text x="32" y="54" fill="var(--panel)" font-size="7">doc (pre)</text>
  <text x="68" y="46" fill="var(--muted)" font-size="8">→ · →</text>
  <text x="100" y="46" fill="var(--muted)" font-size="7">cheap dot, doc vector precomputed</text>
  <text x="8" y="86" fill="var(--s1)" font-size="8">cross</text>
  <rect x="30" y="78" width="70" height="16" fill="var(--s1)"/><text x="34" y="90" fill="var(--panel)" font-size="7">query + doc together</text>
  <text x="104" y="90" fill="var(--muted)" font-size="7">→ one model → score (per pair, no precompute)</text>
  <text x="30" y="106" fill="var(--muted)" font-size="8">bi joins only at the dot; cross joins from the start and sees the interaction</text>
</svg>
^ The bi-encoder joins the two sides only at the final dot product, so the document half is precomputable; the cross-encoder joins them from the input, so it sees every interaction but must run per pair.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/crossenc-inter-01/crossenc.py

The fixture is a query and three documents, one of which pads a single query term to game a term-count score.

```json filename=modules/context-and-retrieval/code/crossenc-inter-01/crossenc.json:3-11 COMPLETE
  "query": ["async", "python"],
  "documents": {
    "d_pad": {"python": 5},
    "d_answer": {"async": 1, "python": 1, "await": 1},
    "d_other": {"async": 1}
  },
  "answer": "d_answer",
  "top_k": 2
}
```

Run `--score` to score every document both ways.

```text filename=--score
SCORE — bi-encoder (term count) vs cross-encoder (aspect coverage)
--------------------------------------------------------------
  document    bi (term count)   cross (aspects covered)
  d_pad       5                 1
  d_answer    2                 2
  d_other     1                 1
--------------------------------------------------------------
  bi top: d_pad (repeats a term)   cross top: d_answer (covers the query)
```

The bi-encoder, scoring by term count, ranks d_pad first with a 5 — it contains "python" five times. But d_pad never mentions "async"; it addresses only half the query, and the bi-encoder cannot see that, because it scored the document's terms without weighing them against the query's structure. The true answer d_answer, which covers both "async" and "python", scores only 2 and comes second. The cross-encoder scores by how many distinct query aspects each document covers: d_answer covers both (2), while d_pad covers only "python" (1), so it correctly ranks d_answer first. The interaction — "does this document address every part of the query" — is invisible to the bi-encoder and decisive for the cross-encoder.

<svg role="img" aria-label="The bi-encoder scores d_pad 5 over d_answer 2; the cross-encoder scores d_answer 2 over d_pad 1" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="12" fill="var(--muted)" font-size="8">bi-encoder score (left) vs cross-encoder score (right)</text>
  <text x="8" y="30" fill="var(--s2)" font-size="8">bi</text>
  <text x="10" y="45" fill="var(--muted)" font-size="7">d_pad</text><rect x="55" y="38" width="100" height="9" fill="var(--s2)"/><text x="159" y="46" fill="var(--s2)" font-size="7">5 ← wrong top</text>
  <text x="10" y="58" fill="var(--muted)" font-size="7">d_answer</text><rect x="55" y="51" width="40" height="9" fill="var(--grid)"/><text x="99" y="59" fill="var(--muted)" font-size="7">2</text>
  <text x="8" y="82" fill="var(--s1)" font-size="8">cross</text>
  <text x="10" y="97" fill="var(--muted)" font-size="7">d_answer</text><rect x="55" y="90" width="100" height="9" fill="var(--s1)"/><text x="159" y="98" fill="var(--s1)" font-size="7">2 ← right top</text>
  <text x="10" y="110" fill="var(--muted)" font-size="7">d_pad</text><rect x="55" y="103" width="50" height="9" fill="var(--grid)"/><text x="109" y="111" fill="var(--muted)" font-size="7">1</text>
</svg>
^ The bi-encoder's tallest bar is d_pad (gamed by repetition); the cross-encoder's tallest is d_answer (covers both query aspects) — the two architectures crown different documents.

## Build

The pipeline ranks the whole corpus by the bi-encoder, keeps the top-k, and reranks that shortlist by the cross-encoder.

```python filename=modules/context-and-retrieval/code/crossenc-inter-01/crossenc.py:76-78 COMPLETE
    docs, q, k = data["documents"], data["query"], data["top_k"]
    shortlist = bi_ranking(docs, q)[:k]
    reranked = max(shortlist, key=lambda d: cross_score(docs[d], q))
```

The fix is not to choose one architecture but to chain them. Run `--rerank`.

```text filename=--rerank
RERANK — bi-encoder retrieves top 2, cross-encoder reranks them
--------------------------------------------------------------
  bi-encoder shortlist (cheap, all 3 docs):  ['d_pad', 'd_answer']
  cross-encoder rerank (scores 2 pairs):      top = d_answer
  a FULL cross-encoder pass would score all 3 pairs
--------------------------------------------------------------
  the answer rode into the shortlist on scale, then the cross-encoder pulled it to the top.
```

The bi-encoder ranks all three documents cheaply and passes its top 2 — `['d_pad', 'd_answer']` — as a shortlist. Crucially, the answer is in it: the bi-encoder is wrong about the *order* but right enough about *membership* to include d_answer in the top 2. The cross-encoder then scores only those 2 pairs and correctly puts d_answer first. Reranking scored 2 pairs, not all 3; on a real corpus this is the difference between running the expensive cross-encoder on a shortlist of, say, 100 documents versus on ten million. You spent the bi-encoder's cheap scale to get the answer into the shortlist, then the cross-encoder's costly accuracy to order the shortlist — each doing only the job it is efficient at.

<svg role="img" aria-label="The bi-encoder scores all documents cheaply and passes a top-k shortlist; the cross-encoder scores only the shortlist and reorders it" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">retrieve (bi, all docs) → rerank (cross, top-k only)</text>
  <rect x="15" y="26" width="70" height="46" fill="none" stroke="var(--grid)"/>
  <rect x="20" y="30" width="60" height="8" fill="var(--s2)"/><rect x="20" y="40" width="60" height="8" fill="var(--s2)"/><rect x="20" y="50" width="60" height="8" fill="var(--s2)"/>
  <text x="18" y="82" fill="var(--muted)" font-size="7">bi: all N (cheap)</text>
  <text x="90" y="52" fill="var(--muted)" font-size="10">→</text>
  <rect x="110" y="34" width="55" height="30" fill="none" stroke="var(--grid)"/>
  <rect x="115" y="38" width="45" height="8" fill="var(--s1)"/><rect x="115" y="48" width="45" height="8" fill="var(--s1)"/>
  <text x="108" y="82" fill="var(--muted)" font-size="7">cross: top-k only</text>
  <text x="170" y="52" fill="var(--muted)" font-size="10">→</text>
  <rect x="190" y="42" width="95" height="14" fill="var(--s1)"/><text x="196" y="52" fill="var(--panel)" font-size="8">d_answer on top</text>
  <text x="15" y="96" fill="var(--muted)" font-size="8">scale gets the answer into the shortlist; accuracy pulls it to the top</text>
</svg>
^ The bi-encoder cheaply ranks the whole corpus into a shortlist; the cross-encoder runs only on that shortlist and reorders it, so the expensive model touches k documents, not all N.

## Definition of done

The self-test pins it: the bi-encoder misranks, the cross-encoder is correct, the bi-encoder rewards repetition, the cross-encoder rewards coverage, and reranking the top-k recovers the answer while scoring fewer pairs.

```python filename=modules/context-and-retrieval/code/crossenc-inter-01/crossenc.py:93-108 COMPLETE
    bi_misranks = top_by(docs, q, bi_score) != answer
    print("  the bi-encoder ranks the wrong document first = %s (got %s, answer %s)" % (bi_misranks, top_by(docs, q, bi_score), answer))

    cross_correct = top_by(docs, q, cross_score) == answer
    print("  the cross-encoder ranks the answer first = %s (%s)" % (cross_correct, top_by(docs, q, cross_score)))

    bi_rewards_repetition = bi_score(docs["d_pad"], q) > bi_score(docs[answer], q)
    print("  the bi-encoder scores a term-padded doc above the answer = %s (%d > %d)" % (bi_rewards_repetition, bi_score(docs["d_pad"], q), bi_score(docs[answer], q)))

    cross_rewards_coverage = cross_score(docs[answer], q) > cross_score(docs["d_pad"], q)
    print("  the cross-encoder scores the answer above the padded doc = %s (%d > %d)" % (cross_rewards_coverage, cross_score(docs[answer], q), cross_score(docs["d_pad"], q)))

    shortlist = bi_ranking(docs, q)[:k]
    reranked = max(shortlist, key=lambda d: cross_score(docs[d], q))
    rerank_recovers_cheaply = answer in shortlist and reranked == answer and k < len(docs)
    print("  reranking the top %d recovers the answer while scoring fewer pairs = %s (%d < %d pairs)" % (k, rerank_recovers_cheaply, k, len(docs)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the bi-encoder misranks on the interaction; the cross-encoder fixes it; reranking recovers it cheaply
----------------------------------------------------------------------------------------------------------------
  the bi-encoder ranks the wrong document first = True (got d_pad, answer d_answer)
  the cross-encoder ranks the answer first = True (d_answer)
  the bi-encoder scores a term-padded doc above the answer = True (5 > 2)
  the cross-encoder scores the answer above the padded doc = True (2 > 1)
  reranking the top 2 recovers the answer while scoring fewer pairs = True (2 < 3 pairs)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  bi_misranks=True  cross_correct=True  bi_rewards_repetition=True  cross_rewards_coverage=True  rerank_recovers_cheaply=True
```

**Done means the trade-off and its resolution are proven: the bi-encoder ranks the padded d_pad first (5 > 2) while the cross-encoder ranks the true d_answer first (2 > 1), and reranking the bi-encoder's top 2 recovers d_answer while scoring 2 pairs instead of all 3.**

## Boss fight

Reranking the top-k fixed the order. Predict the parameter that decides whether it can, and the middle-ground architecture that softens the whole trade-off. It is tempting to set k small to save cross-encoder cost.

The reranker can only reorder what the retriever gave it, so k sets a recall ceiling: if the bi-encoder's top-k does not contain the answer, no reranking recovers it — the answer this module rescued was safe only because it landed in the top 2. Shrink k to save cross-encoder cost and you risk dropping answers the bi-encoder ranked just outside the cutoff; grow k for safety and you pay more cross-encoder passes. So k is a recall-versus-cost dial, tuned to how good the bi-encoder's recall is: a strong retriever needs only a small k, a weak one needs a large one, and the cross-encoder's accuracy is wasted if the retriever's recall was too low to get the answer into the window in the first place. Reranking amplifies a good retriever; it cannot rescue a bad one.

The middle ground is late-interaction models like ColBERT. A pure bi-encoder crushes each side to a single vector (maximally precomputable, minimally interaction-aware); a cross-encoder keeps everything joined (maximally interaction-aware, not precomputable). Late interaction keeps a vector *per token* for each document — precomputable, like a bi-encoder — but scores a pair by matching query tokens to document tokens at query time, recovering much of the cross-encoder's interaction-awareness at a cost between the two. It buys accuracy back for more storage and a heavier query-time computation than a single dot product. The broader lesson is that "separate encoding versus joint encoding" is a spectrum, not a binary: single-vector bi-encoders, multi-vector late interaction, and full cross-encoders trade precomputability against interaction-awareness in graded steps, and a production stack often chains them — cheap bi-encoder to retrieve, late-interaction or cross-encoder to rerank — placing each where its point on the spectrum pays off.

```python filename=modules/context-and-retrieval/code/crossenc-inter-01/crossenc.py:58-59 COMPLETE
def bi_ranking(docs, query):
    return sorted(docs, key=lambda d: bi_score(docs[d], query), reverse=True)
```

**A bi-encoder scales because it embeds query and document separately, but that separation blinds it to their interaction; a cross-encoder sees the interaction by encoding them jointly, but that joining stops it scaling — so retrieve a shortlist with the bi-encoder and rerank it with the cross-encoder, tuning k to the retriever's recall, and reach for late-interaction models when you want a point between the two.**

## External resources

The Sentence-Transformers documentation on bi-encoders versus cross-encoders — the canonical explanation of the architectures, their speed/accuracy trade-off, and the retrieve-then-rerank pipeline they recommend.

The ColBERT papers (Khattab and Zaharia) on late interaction — the multi-vector middle ground that keeps precomputable per-token representations while restoring much of the cross-encoder's interaction-awareness.

The companion "rerank for precision — but the reranker can only reorder what it's given" and "the hybrid retrieval pipeline" modules — the recall-ceiling constraint on any reranker, and where the cross-encoder rerank stage sits in a full retrieval pipeline.
