---
id: prefilter-inter-01
title: Apply the hard filter before the top-k cut, not after — post-filtering a search can return far fewer hits than you asked for
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: Retrieval often carries a hard constraint alongside the semantic query — only documents from this year, only this user's files, only the "legal" category, only in-stock products — and there are two places to apply it that are not equivalent. Post-filtering runs the vector search first, takes the top-k most similar documents, then discards the ones that fail the constraint; pre-filtering restricts to the documents that satisfy the constraint first and searches for the top-k within that subset. They sound interchangeable and are not: post-filtering can hand back far fewer results than requested, sometimes none. The failure is starvation — the top-k cut happens before the constraint is checked, so the k slots fill with the most similar documents regardless of the constraint, and if the highest-similarity documents fail it, they consume the slots and are then thrown away, leaving only the few matching documents that made the top-k. Worse, matching documents that ranked just below the cut are never considered: they lost their slots to non-matching documents that were only going to be discarded, so post-filtering under-returns and misses valid results at once, silently. Pre-filtering makes the constraint part of the search space: restrict to matching documents, then take the top-k, so every slot goes to a valid document and you get the k most similar matching ones. The cost is that the index must support filtering during search; where it cannot, over-fetching (retrieve far more than k, then post-filter) is the middle ground. On a fixture where the query wants the top-3 category-A documents, post-filtering takes the top-3 by similarity (two category-B, one A) and discards the B's, returning just 1 and missing d5 and d6 (valid A documents), while pre-filtering restricts to A first and returns the top-3 A documents.
eli5: Imagine you want the three best pizza places that deliver to your house. One way: look up the three best pizza places in the whole city, then cross off the ones that don't deliver to you — and if the top three all happen to be too far away, you're left with zero, even though there are perfectly good places nearby that deliver. The smarter way: first list only the places that deliver to you, then pick the three best of those. You still get three great options, and you never waste your shortlist on places you can't order from. The rule is: apply the "must deliver to me" filter before you pick your top three, not after.
---

## Why this module

Almost every real retrieval query is a semantic search plus a hard filter: find passages about X, but only from documents this user is allowed to see, or only from this date range, or only in this language. The filter is not a preference to be traded off against similarity — it is a requirement, a document that fails it is simply not an answer. And exactly because it is a hard requirement, where you apply it in the pipeline changes the results, in a way that quietly breaks retrieval when done wrong.

The two orderings look symmetric and are not. Post-filtering searches, takes the top-k, then drops the failures — which means the top-k is chosen by similarity alone, blind to the constraint. If the most similar documents happen not to satisfy the filter, they still take the k slots, and dropping them afterward leaves you with fewer than k. The valid documents that would have filled those slots, had the filter been applied first, ranked just below the cut and were never retrieved. So the constraint does not just shrink the result set; it starves it, discarding good matches that were never given a chance to compete.

Pre-filtering restricts the search to the matching documents up front, so the top-k is taken among valid documents only. This module runs the same constrained query both ways and counts what each returns.

**Apply a hard metadata constraint before the top-k cut (pre-filter: search within the matching subset), not after it (post-filter: search then discard), because taking the top-k first lets high-similarity non-matching documents consume the slots and be thrown away — so post-filtering returns fewer than k and misses valid lower-ranked matches, while pre-filtering fills all k slots with the best matching documents.**

## Concepts

The fixture is six documents, each with a similarity score and a category, and a query that wants the top-3 documents in category A.

```json filename=modules/context-and-retrieval/code/prefilter-inter-01/prefilter.json:3-8 COMPLETE
  "top_k": 3,
  "required_category": "A",
  "documents": [
    {"id": "d1", "similarity": 0.9, "category": "B"},
    {"id": "d2", "similarity": 0.8, "category": "B"},
    {"id": "d3", "similarity": 0.7, "category": "A"},
```

The remaining documents include two more category-A files, d5 and d6, at lower similarity — the ones the ordering will decide the fate of.

```json filename=modules/context-and-retrieval/code/prefilter-inter-01/prefilter.json:9-11 COMPLETE
    {"id": "d4", "similarity": 0.6, "category": "B"},
    {"id": "d5", "similarity": 0.5, "category": "A"},
    {"id": "d6", "similarity": 0.4, "category": "A"}
```

The two strategies differ in the order of two operations — the top-k cut and the filter. Post-filtering cuts first; pre-filtering filters first.

```python filename=modules/context-and-retrieval/code/prefilter-inter-01/prefilter.py:32-45 COMPLETE
def by_similarity(docs):
    return sorted(docs, key=lambda d: (-d["similarity"], d["id"]))


def post_filter(docs, k, category):
    """Search first: take the top-k by similarity, THEN discard non-matching."""
    topk = by_similarity(docs)[:k]
    return [d for d in topk if d["category"] == category]


def pre_filter(docs, k, category):
    """Restrict to matching documents first, THEN take the top-k by similarity."""
    matching = [d for d in docs if d["category"] == category]
    return by_similarity(matching)[:k]
```

That single swap — filter then cut, versus cut then filter — is the whole module. When the top similarity slots are occupied by non-matching documents, the two produce very different result sets.

<svg role="img" aria-label="Six documents ranked by similarity; the top-3 cut captures two category-B and one category-A, post-filter keeps only the A, while pre-filter pulls the three category-A documents regardless of rank" viewBox="0 0 320 130">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">ranked by similarity (top-3 cut after d3)</text>
  <g font-size="7.5">
  <rect x="14" y="24" width="46" height="16" fill="var(--s2)"/><text x="20" y="35" fill="var(--panel)">d1 B</text>
  <rect x="62" y="24" width="46" height="16" fill="var(--s2)"/><text x="68" y="35" fill="var(--panel)">d2 B</text>
  <rect x="110" y="24" width="46" height="16" fill="var(--s1)"/><text x="116" y="35" fill="var(--panel)">d3 A</text>
  <line x1="158" y1="20" x2="158" y2="44" stroke="var(--ink)" stroke-width="1.5"/><text x="160" y="18" fill="var(--muted)">cut</text>
  <rect x="162" y="24" width="46" height="16" fill="none" stroke="var(--s2)"/><text x="168" y="35" fill="var(--muted)">d4 B</text>
  <rect x="210" y="24" width="46" height="16" fill="none" stroke="var(--s1)"/><text x="216" y="35" fill="var(--s1)">d5 A</text>
  <rect x="258" y="24" width="46" height="16" fill="none" stroke="var(--s1)"/><text x="264" y="35" fill="var(--s1)">d6 A</text>
  </g>
  <text x="10" y="66" font-size="8" fill="var(--s2)">post-filter: keep A's in top-3 → d3 only (1 of 3)</text>
  <text x="10" y="90" font-size="8" fill="var(--s1)">pre-filter: A's first, top-3 → d3, d5, d6 (3 of 3)</text>
  <text x="10" y="114" font-size="7.5" fill="var(--ink)">d5, d6 are valid A docs just past the cut — post-filter never sees them</text>
</svg>
^ The top-3 cut captures d1, d2 (category B) and d3 (A). Post-filter keeps only d3. Pre-filter ignores the global ranking, pulls the category-A documents, and returns the top three of them — including d5 and d6, which sat just past the cut and post-filter never considered.

**Filter-then-cut and cut-then-filter are not the same operation: the cut is where results are lost, so applying the constraint after it discards matches the constraint would have kept.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the filtered-retrieval step of a search pipeline, reduced to six documents so every ranking is checkable by hand.

Run `--docs` to see the documents and the top-k cut.

```text filename=prefilter.py --docs
  doc   similarity   category   in top-3?
  d1    0.9          B          True
  d2    0.8          B          True
  d3    0.7          A          True
  d4    0.6          B          False
  d5    0.5          A          False
  d6    0.4          A          False
  the top-3 by similarity is ['d1', 'd2', 'd3'] -- categories mixed
```

The top-3 by similarity is d1, d2, d3 — but only d3 is category A. The two most similar documents are category B, so they occupy two of the three slots. Meanwhile d5 and d6, both category A, sit just below the cut at similarities 0.5 and 0.4. There are three category-A documents in the corpus — enough to satisfy the request — but two of them are below the top-3 line.

Now `--filter` runs both strategies.

```text filename=prefilter.py --filter
  post-filter: ['d3'] -> 1 result(s) of 3 requested
  pre-filter:  ['d3', 'd5', 'd6'] -> 3 result(s) of 3 requested
  valid matches post-filter missed: ['d5', 'd6']
```

Post-filter returns one document. It took the top-3 (d1, d2, d3), discarded the two category-B documents, and was left with d3 alone — a third of what was asked for, from a corpus that contained three valid answers. Pre-filter returns all three: it restricted to category A first (d3, d5, d6) and took the top-3 of those. The last line names the cost of post-filtering: d5 and d6, valid matches, were missed entirely — not because they were poor, but because non-matching documents consumed the slots before the filter ran.

**Post-filter returned 1 of 3 requested and missed two valid category-A documents; pre-filter returned all 3 — the same corpus and constraint, and the ordering of the cut and the filter decided whether good answers were found.**

## Build

The self-test asserts the setup and both failures: enough matching documents exist to fill the request, post-filter returns fewer than k, and pre-filter returns the full top-k.

```python filename=modules/context-and-retrieval/code/prefilter-inter-01/prefilter.py:87-97 COMPLETE
    enough_matches_exist = total_matching >= k
    print("  enough matching documents exist to fill top-%d = %s (%d category-'%s')" % (k, enough_matches_exist, total_matching, cat))

    postfilter_underreturns = len(post) < k
    print("  post-filter returns fewer than requested = %s (%d of %d)" % (postfilter_underreturns, len(post), k))

    prefilter_returns_k = len(pre) == k
    print("  pre-filter returns the full top-%d = %s (%s)" % (k, prefilter_returns_k, ids(pre)))

    postfilter_misses_valid = any(d["id"] not in ids(post) for d in pre)
    missed = [d["id"] for d in pre if d["id"] not in ids(post)]
    print("  post-filter misses valid matching documents = %s (%s)" % (postfilter_misses_valid, missed))
```

<svg role="img" aria-label="Two result bars: post-filter returns 1 of 3 requested, pre-filter returns 3 of 3, with the missed documents d5 and d6 marked on the post-filter bar" viewBox="0 0 320 110">
  <text x="10" y="18" font-size="8.5" fill="var(--muted)">results returned (requested: 3)</text>
  <text x="10" y="42" font-size="8.5" fill="var(--s2)">post-filter</text>
  <rect x="90" y="32" width="60" height="16" fill="var(--s2)"/><text x="112" y="44" font-size="8" fill="var(--panel)">d3</text>
  <text x="160" y="44" font-size="8" fill="var(--ink)">1 of 3 (missed d5, d6)</text>
  <text x="10" y="72" font-size="8.5" fill="var(--s1)">pre-filter</text>
  <rect x="90" y="62" width="180" height="16" fill="var(--s1)"/><text x="140" y="74" font-size="8" fill="var(--panel)">d3  d5  d6</text>
  <text x="10" y="98" font-size="7.5" fill="var(--muted)">same corpus, same constraint — only the order of cut and filter differs</text>
</svg>
^ Post-filter delivers a third of the request and drops two valid matches; pre-filter delivers the full top-k. The gap is entirely the ordering of the top-k cut and the constraint.

Running the check confirms every clause, including that every pre-filter result matches and they are the best matching documents.

```text filename=prefilter.py --check
  enough matching documents exist to fill top-3 = True (3 category-'A')
  post-filter returns fewer than requested = True (1 of 3)
  pre-filter returns the full top-3 = True (['d3', 'd5', 'd6'])
  post-filter misses valid matching documents = True (['d5', 'd6'])
  every pre-filter result satisfies the constraint = True
  pre-filter returns the k most similar matching documents = True (['d3', 'd5', 'd6'])
```

**The check ties the under-return to matches that existed but ranked below the cut, and shows pre-filter recovering them — the constraint applied before the cut competes with nothing, so no valid document is starved.**

## Definition of done

Two properties close it. Post-filter must under-return while enough matches exist (the failure is starvation, not a genuinely empty result), and pre-filter must return the full top-k of the best matching documents (the fix). The "enough matches exist" clause is what makes the post-filter shortfall a bug rather than an honest "there just aren't three."

```python filename=modules/context-and-retrieval/code/prefilter-inter-01/prefilter.py:100-104 COMPLETE
    all_prefilter_match = all(d["category"] == cat for d in pre)
    print("  every pre-filter result satisfies the constraint = %s" % all_prefilter_match)

    prefilter_is_best_matching = ids(pre) == ids(by_similarity([d for d in docs if d["category"] == cat])[:k])
    print("  pre-filter returns the k most similar matching documents = %s (%s)" % (prefilter_is_best_matching, ids(pre)))
```

Two clarifications keep the tradeoff calibrated. First, pre-filtering requires the index to support filtering during the nearest-neighbor search — a "filtered ANN" query or a metadata index — and not all vector indexes do this efficiently; when they cannot, the practical middle ground is to over-fetch (retrieve k times some multiple, then post-filter) so the constraint is far less likely to starve the result, trading extra retrieval work for coverage. The severity of the post-filter problem scales with how selective the filter is: a filter that keeps most documents rarely starves the top-k, while a highly selective filter (this user's 5 documents out of a million) makes naive post-filtering return almost nothing, which is exactly when pre-filtering is essential. Second, pre-filtering interacts with approximate search: restricting the candidate set can change recall behavior of the ANN index, so production systems use purpose-built filtered-search algorithms rather than naively intersecting a filter with a separate ANN result. The principle is unchanged regardless of implementation: a hard constraint belongs in the search space, applied before the top-k cut, not as a post-hoc filter on results the cut already chose.

<svg role="img" aria-label="A curve showing post-filter yield falling as the filter gets more selective: a loose filter keeps most of the top-k, a selective filter returns almost nothing" viewBox="0 0 320 110">
  <line x1="35" y1="20" x2="35" y2="90" stroke="var(--line)" stroke-width="1"/>
  <line x1="35" y1="90" x2="300" y2="90" stroke="var(--line)" stroke-width="1"/>
  <text x="0" y="26" font-size="7.5" fill="var(--muted)">post-filter</text>
  <text x="0" y="36" font-size="7.5" fill="var(--muted)">yield</text>
  <text x="150" y="106" font-size="7.5" fill="var(--muted)">filter selectivity (more selective →)</text>
  <path d="M 50 28 Q 130 40 290 82" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <circle cx="50" cy="28" r="3" fill="var(--s1)"/><text x="42" y="24" font-size="7" fill="var(--s1)">loose: fine</text>
  <circle cx="290" cy="82" r="3" fill="var(--s2)"/><text x="228" y="80" font-size="7" fill="var(--s2)">selective: starves</text>
</svg>
^ Post-filter's shortfall grows with how selective the constraint is: a loose filter (keeps most docs) rarely starves the top-k, while a highly selective one (this user's few files) returns almost nothing. Pre-filtering is essential exactly where the filter is selective.

**Done means post-filter under-returns despite enough matches existing and pre-filter returns the full top-k of the best matching documents — the constraint applied before the cut, with over-fetching as the fallback when the index cannot filter during search.**

## Boss fight

A document-search feature lets users search their own files, implemented as a vector search over all files followed by a filter to the current user's documents. Users with few documents complain that search "returns nothing" or one result even when they have relevant files, while users with many documents are fine. What is happening, and how would you fix it?

It is post-filter starvation, and the pattern (bad for users with few documents, fine for users with many) is the tell. The pipeline searches all files, takes the top-k by similarity, then filters to the current user — so the top-k is chosen across everyone's documents, and for a user with few files, the top-k is dominated by other users' documents, which the filter then discards, leaving one result or none. That user's own relevant files existed but ranked below the global top-k (because someone else's documents were more similar), so they were never retrieved and the filter had nothing to keep. Users with many documents are fine only because enough of their files make the global top-k by chance. The security/correctness requirement (a user must only see their own files) is a hard constraint and belongs before the top-k cut. The fix is to pre-filter: scope the vector search to the current user's documents and take the top-k within that set, so every slot goes to one of their files and the k most similar of their documents are returned. If the vector index supports filtered nearest-neighbor search, apply the user-id filter as part of the query; if it does not, either partition the index by user (search only that user's shard) or, as a stopgap, over-fetch a large multiple of k before filtering — though for a per-user filter this selective, proper pre-filtering or per-user partitioning is the right answer, not over-fetching. This also removes any risk of the ranking being influenced by other users' documents at all.

## External resources

The documentation on filtered/metadata search in vector databases (Pinecone, Weaviate, Qdrant, Milvus) and their "pre-filter vs post-filter" guidance — the production treatment of applying constraints during nearest-neighbor search and when to over-fetch, matching the tradeoff modeled here.

Research and engineering writeups on filtered approximate nearest neighbor search (for example, filtered-DiskANN and vector-index filtering strategies) — why naive post-filtering starves selective queries and how purpose-built filtered-ANN algorithms apply the constraint inside the search rather than after it.
