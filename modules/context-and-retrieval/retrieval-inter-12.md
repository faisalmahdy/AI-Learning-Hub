---
id: retrieval-inter-12
title: Pre-filter the corpus by metadata before the search — post-filtering the top-k can return nothing
topic: context-and-retrieval
level: intermediate
status: ready
time: 21 min
summary: A metadata constraint — this user's docs, this date range, this team — can be applied before the vector search or after it, and they are not equivalent. Post-filter retrieves the top-k then drops what fails the filter, so if the top-k are all excluded it returns nothing. On a fixture where the three highest-scoring docs are the wrong team, post-filter returns 0 of 3; pre-filter returns 3 of 3.
eli5: If you want the three best pizza places that are open now, don't list the three best and then cross off the closed ones — you might cross off all three. Instead, first keep only the open ones, then pick the three best of those. Same shops, but you always end up with three.
---

## Why this module

Every real retrieval query carries a constraint — only this user's files, only documents from this quarter, only the current team's space, only published pages — and where you apply that constraint decides whether you get results or an empty list.

There are two orderings, and they look interchangeable until they are not. Post-filter runs the vector search first: it retrieves the top-k documents by similarity, then discards the ones that fail the metadata constraint, and returns what survives. Pre-filter applies the constraint first: it restricts the candidate set to the documents that pass the filter, then retrieves the top-k among those. When the top-k happen to satisfy the filter, both give the same answer. But when they do not — when the most similar documents are ones the filter excludes — post-filter retrieves them, throws them away, and hands back a list shorter than you asked for, sometimes empty.

The reason this happens constantly is that the highest-similarity documents are often precisely the ones the filter is there to exclude. The most relevant passage might live in another team's space that this user cannot see, or in a draft that is not published, or outside the requested date range. Post-filter faithfully retrieves those top matches and then deletes every one of them, leaving the caller with nothing — and the caller concludes there was no relevant content, when in fact the relevant *allowed* content was sitting just below the similarity cut, never retrieved because the top-k slots were spent on documents that would be filtered out.

Pre-filter avoids the trap by never spending a retrieval slot on a document that cannot be returned. It narrows to the allowed set first, so all k results come from documents that pass the filter, and you get k of them whenever k allowed documents exist. The constraint shapes the search space instead of pruning the search results.

We will run one query two ways against a corpus where the three highest-scoring documents are the wrong team and the allowed documents rank lower. Post-filter returns 0 of 3 requested. Pre-filter returns 3 of 3. Same documents, same filter — only filter-then-search versus search-then-filter differs.

**A metadata filter applied after the search prunes the results you already fetched, so if the top-k are all excluded you get nothing; applied before, it shapes the candidate set and you always get k allowed results.**

## Concepts

<svg role="img" aria-label="Two pipelines: post-filter goes corpus to search to filter to few results; pre-filter goes corpus to filter to search to k results" viewBox="0 0 460 170" width="460" height="170">
  <rect x="0" y="0" width="460" height="170" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--s2)">post-filter: search, then filter the results</text>
  <g font-family="var(--mono)" font-size="8">
    <rect x="20" y="30" width="70" height="26" fill="var(--panel)" stroke="var(--line)"/><text x="34" y="47" fill="var(--ink)">corpus</text>
    <rect x="130" y="30" width="70" height="26" fill="var(--acc-soft)" stroke="var(--line)"/><text x="142" y="47" fill="var(--ink)">top-k</text>
    <rect x="240" y="30" width="70" height="26" fill="var(--s2)" stroke="var(--line)"/><text x="250" y="47" fill="var(--ink)">filter</text>
    <rect x="350" y="30" width="90" height="26" fill="var(--panel)" stroke="var(--line)"/><text x="360" y="47" fill="var(--s2)">0–k results</text>
  </g>
  <g stroke="var(--ink)"><line x1="90" y1="43" x2="130" y2="43"/><line x1="200" y1="43" x2="240" y2="43"/><line x1="310" y1="43" x2="350" y2="43"/></g>
  <text x="16" y="95" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">pre-filter: filter, then search the allowed set</text>
  <g font-family="var(--mono)" font-size="8">
    <rect x="20" y="105" width="70" height="26" fill="var(--panel)" stroke="var(--line)"/><text x="34" y="122" fill="var(--ink)">corpus</text>
    <rect x="130" y="105" width="70" height="26" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="142" y="122" fill="var(--acc-ink)">filter</text>
    <rect x="240" y="105" width="70" height="26" fill="var(--acc-soft)" stroke="var(--line)"/><text x="252" y="122" fill="var(--ink)">top-k</text>
    <rect x="350" y="105" width="90" height="26" fill="var(--acc-soft)" stroke="var(--acc-ink)"/><text x="360" y="122" fill="var(--acc-ink)">k results</text>
  </g>
  <g stroke="var(--ink)"><line x1="90" y1="118" x2="130" y2="118"/><line x1="200" y1="118" x2="240" y2="118"/><line x1="310" y1="118" x2="350" y2="118"/></g>
  <text x="20" y="152" font-family="var(--mono)" font-size="9" fill="var(--muted)">swapping the middle two boxes is the whole fix</text>
</svg>
^ The only difference is the order of the filter and the search — post-filter filters what it already fetched (0–k left), pre-filter fetches from what passed (always k when enough exist).

The difference is which set the top-k is taken from. Post-filter takes the top-k of the *whole* corpus and then intersects with the allowed set — and the intersection can be small or empty, because the top-k of the whole corpus is chosen without any regard for the filter. Pre-filter takes the top-k of the *allowed* corpus directly, so every returned document is both allowed and among the best of the allowed. The first computes "best overall, that also pass"; the second computes "best among those that pass." When the best overall are excluded, those are very different sets, and only the second is what the user actually wanted.

Post-filter's failure is not just occasional emptiness — it is unpredictable result counts. You ask for k and you get somewhere between 0 and k, depending on how many of the top-k happened to pass the filter, which depends on the query and the corpus in ways you cannot know in advance. A retrieval layer that sometimes returns three results and sometimes zero for structurally identical queries is hard to build on. Pre-filter returns exactly min(k, number of allowed documents), which is predictable and is the count you would compute by hand.

There is a way to make post-filter usually work — over-fetch. Retrieve the top-N with N much larger than k, then filter, hoping enough survive to yield k. This is what naive implementations fall back to, and it has two problems. First, you have to guess N, and any fixed N can be defeated by a query whose allowed documents all rank below it — the more selective the filter, the larger N must be, without bound in the worst case. Second, over-fetching is wasteful: you retrieve and score far more than you need on every query to compensate for a filter you could have applied first. Pre-filter needs no guessing and no waste.

The reason post-filter exists at all is that pre-filter requires the index to support filtering during search — the vector index must be able to restrict its candidate set to documents matching the metadata, which some naive setups cannot do efficiently, forcing a post-filter or an over-fetch. Modern vector databases support metadata pre-filtering directly (filtered search), and it is the correct default; post-filter is what you are stuck with when your index cannot filter, and knowing that tells you what capability to demand of your index. The ordering is not a stylistic choice — it is a correctness property, and pre-filter is the correct order.

**Post-filter returns "best overall that also pass," an unpredictable 0-to-k count; pre-filter returns "best among those that pass," exactly min(k, allowed) — the count the user meant.**

## Worked example

The fixture is a small corpus with similarity scores and a team metadata field, and a query allowed to use only one team's documents.

```json filename=modules/context-and-retrieval/code/retrieval-inter-12/docs.json:7-14 COMPLETE
  "k": 3,
  "allowed_team": "eng",
  "docs": [
    {
      "id": "d1",
      "score": 0.9,
      "team": "sales"
    },
```

Three results wanted, and the query may only use `team == eng`. Documents are ranked by score.

```python filename=modules/context-and-retrieval/code/retrieval-inter-12/prefilter.py:40-41 COMPLETE
def by_score(docs):
    return sorted(docs, key=lambda d: -d["score"])
```

```text filename=modules/context-and-retrieval/code/retrieval-inter-12/prefilter.py --docs
DOCS — score and team per document (query allowed: team==eng)
----------------------------------------------
  d1  score 0.90  team=sales 
  d2  score 0.85  team=sales 
  d3  score 0.80  team=sales 
  d4  score 0.60  team=eng     <- allowed
  d5  score 0.55  team=eng     <- allowed
  d6  score 0.50  team=eng     <- allowed
  d7  score 0.40  team=sales 
----------------------------------------------
  the three highest scores are all the wrong team.
```

The three highest-scoring documents — d1, d2, d3 — are all `team == sales`, which the query cannot use. The allowed `eng` documents, d4, d5, d6, rank fourth through sixth. Post-filter takes the top-3 by score first, then drops the disallowed.

```python filename=modules/context-and-retrieval/code/retrieval-inter-12/prefilter.py:46-49 COMPLETE
def post_filter(docs, k, allowed):
    """Search first: take the top-k by score, THEN drop the ones failing the filter -- may return < k."""
    topk = by_score(docs)[:k]
    return [d for d in topk if d["team"] == allowed]
```

Pre-filter keeps the allowed documents first, then takes the top-3 of those.

```python filename=modules/context-and-retrieval/code/retrieval-inter-12/prefilter.py:52-55 COMPLETE
def pre_filter(docs, k, allowed):
    """Filter first: keep the allowed documents, THEN take the top-k among them -- returns k if enough exist."""
    allowed_docs = [d for d in docs if d["team"] == allowed]
    return by_score(allowed_docs)[:k]
```

Predict: post-filter's top-3 is d1, d2, d3 — all sales — so after filtering, nothing. Pre-filter's allowed set is d4, d5, d6, so its top-3 is exactly those. Run it.

```text filename=modules/context-and-retrieval/code/retrieval-inter-12/prefilter.py --retrieve
RETRIEVE — top-3 under post-filter vs pre-filter (allowed team==eng)
--------------------------------------------------------
  post-filter: (empty)   (0 of 3 wanted)
  pre-filter:  ['d4', 'd5', 'd6']   (3 of 3 wanted)
--------------------------------------------------------
  post-filter kept the top-3 (all sales) then dropped them; pre-filter searched within eng.
```

Post-filter returns an empty list — 0 of 3 — because the three retrieval slots were spent on documents the filter then removed, and it never looked deeper. The caller sees "no results" and reasonably concludes there was nothing relevant, which is false: there were three perfectly good allowed documents, d4 through d6, that post-filter never fetched. Pre-filter returns exactly those three. The allowed documents existed the whole time; post-filter just never gave them a chance to be retrieved.

<svg role="img" aria-label="Results returned of 3 wanted: post-filter 0, pre-filter 3" viewBox="0 0 460 140" width="460" height="140">
  <rect x="0" y="0" width="460" height="140" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="22" font-family="var(--mono)" font-size="11" fill="var(--muted)">usable results returned (of 3 wanted)</text>
  <line x1="60" y1="110" x2="440" y2="110" stroke="var(--line)"/>
  <rect x="100" y="108" width="90" height="2" fill="var(--s2)" stroke="var(--line)"/><text x="124" y="102" font-family="var(--mono)" font-size="11" fill="var(--s2)">0</text><text x="98" y="126" font-family="var(--mono)" font-size="9" fill="var(--muted)">post-filter</text>
  <rect x="280" y="40" width="90" height="70" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="316" y="34" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">3</text><text x="288" y="126" font-family="var(--mono)" font-size="9" fill="var(--muted)">pre-filter</text>
</svg>
^ Same corpus and same filter: post-filter hands back nothing, pre-filter hands back the full three allowed documents.

<svg role="img" aria-label="Documents ranked by score: the top three are sales (excluded), the next three are eng (allowed); post-filter cuts at rank 3 and keeps none, pre-filter searches only the eng docs" viewBox="0 0 460 210" width="460" height="210">
  <rect x="0" y="0" width="460" height="210" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">ranked by score; top-3 line = post-filter's reach</text>
  <g font-family="var(--mono)" font-size="9">
    <rect x="40" y="30" width="240" height="20" fill="var(--s2)" stroke="var(--line)"/><text x="48" y="44" fill="var(--ink)">d1  0.90  sales  (excluded)</text>
    <rect x="40" y="52" width="240" height="20" fill="var(--s2)" stroke="var(--line)"/><text x="48" y="66" fill="var(--ink)">d2  0.85  sales  (excluded)</text>
    <rect x="40" y="74" width="240" height="20" fill="var(--s2)" stroke="var(--line)"/><text x="48" y="88" fill="var(--ink)">d3  0.80  sales  (excluded)</text>
    <rect x="40" y="100" width="240" height="20" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="48" y="114" fill="var(--acc-ink)">d4  0.60  eng  ✓</text>
    <rect x="40" y="122" width="240" height="20" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="48" y="136" fill="var(--acc-ink)">d5  0.55  eng  ✓</text>
    <rect x="40" y="144" width="240" height="20" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="48" y="158" fill="var(--acc-ink)">d6  0.50  eng  ✓</text>
  </g>
  <line x1="30" y1="96" x2="300" y2="96" stroke="var(--s2)" stroke-width="2" stroke-dasharray="4 3"/><text x="305" y="99" font-family="var(--mono)" font-size="8" fill="var(--s2)">post-filter cut</text>
  <text x="305" y="130" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">pre-filter</text><text x="305" y="142" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">searches</text><text x="305" y="154" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">only here</text>
  <text x="40" y="188" font-family="var(--mono)" font-size="9" fill="var(--muted)">post-filter's cut sits above every allowed doc → 0 results</text>
</svg>
^ Post-filter's top-3 cut lands above all three allowed documents, so it returns none; pre-filter ignores the excluded rows entirely and takes the top-3 of the eng rows.

## Build

Reproduce the two retrievals. Pure standard library, deterministic scores, so the empty list and [d4, d5, d6] come out exactly.

Run `--docs` for the corpus, `--retrieve` for the two orderings, `--check` for the gate. The self-test pins the contrast: post-filter starves, pre-filter returns the full k, all pre-filter results pass the filter, and pre-filter beats post-filter.

```python filename=modules/context-and-retrieval/code/retrieval-inter-12/prefilter.py:89-95 COMPLETE
    post = post_filter(docs, k, allowed)
    pre = pre_filter(docs, k, allowed)

    post_starves = len(post) < k
    print("  post-filter returns fewer than the %d wanted = %s (%d returned)" % (k, post_starves, len(post)))

    pre_returns_k = len(pre) == k
    print("  pre-filter returns the full k = %s (%d returned, %d allowed exist)" % (pre_returns_k, len(pre), n_allowed))
```

The `pre_returns_k` check is paired with the fixture fact that exactly k allowed documents exist, so it proves pre-filter delivers the count the user asked for whenever that count is achievable. It is not enough to show pre-filter returns more than post-filter — it has to return the full k, because the whole promise of pre-filter is that the filter costs you no results as long as enough allowed documents exist. Post-filter breaks that promise; pre-filter keeps it. Here is the full gate.

```text filename=modules/context-and-retrieval/code/retrieval-inter-12/prefilter.py --check
SELF-TEST — post-filter starves under a restrictive filter; pre-filter returns the intended k
----------------------------------------------------------------------------------------
  post-filter returns fewer than the 3 wanted = True (0 returned)
  pre-filter returns the full k = True (3 returned, 3 allowed exist)
  every pre-filter result satisfies the filter = True
  pre-filter returns more usable results than post-filter = True (3 vs 0)
----------------------------------------------------------------------------------------
SELF-TEST PASS  post_starves=True  pre_returns_k=True  pre_all_allowed=True  pre_beats_post=True
```

Four True flags. Post_starves: post-filter returns fewer than requested — here zero. Pre_returns_k: pre-filter returns the full three. Pre_all_allowed: every pre-filter result passes the filter. Pre_beats_post: three usable results versus zero. The second flag is the promise — pre-filter costs no results when enough allowed documents exist — and it is exactly the promise post-filter cannot make.

**Pre_returns_k is checked against the fixture's exactly-k allowed documents, proving pre-filter costs no results when the count is achievable — the promise post-filter breaks.**

## Definition of done

You are done when you reproduce the empty and full results and can explain the ordering.

Concretely: `--retrieve` shows post-filter empty and pre-filter returning d4, d5, d6; `--check` prints PASS with four True flags. You can explain the difference between "best overall that also pass" and "best among those that pass," and why they diverge when the top matches are excluded. You can describe post-filter's unpredictable 0-to-k count and pre-filter's predictable min(k, allowed). And you can explain the over-fetch workaround and why it is a workaround — you must guess N, and no fixed N is safe against a selective filter.

The habit to carry: apply metadata constraints as pre-filters in the vector search, not as post-filters on the results, and demand filtered-search capability from your index. When a retrieval query returns fewer results than expected, or intermittently returns nothing, suspect a post-filter eating the top-k before you suspect the corpus is empty.

## Boss fight

The instructive failure is a permission filter that makes a search feature look broken for exactly the users it is supposed to serve.

A company builds document search with per-user access control, implemented as a post-filter: retrieve the top-10 by similarity, then drop the documents the user is not allowed to see. For an admin who can see everything, it works great. But for a regular employee, the most relevant documents to many queries are ones they cannot access — leadership docs, other teams' spaces — so the top-10 is full of forbidden matches, the post-filter strips them, and the employee gets few or no results for queries that have perfectly good answers in their own accessible documents. Support tickets say "search is broken for me but not for my manager," which is the signature of a post-filter interacting with per-user permissions. Switching to a pre-filter — restrict to the user's accessible documents, then search — fixes it: every user searches their own allowed corpus and gets the full result set.

Your turn, two moves. First, find how selective a filter post-filter can survive. With k=3, post-filter returns 3 only if all of the top-3 are allowed; predict the probability of that if a fraction f of the corpus is allowed and scores are unrelated to the filter — it is roughly f³, so at f = 0.5 you get a full result set only about an eighth of the time, and at f = 0.1 essentially never. The more selective the filter, the more often post-filter starves. Second, size the over-fetch that would rescue post-filter here. To be sure of getting 3 eng documents by post-filtering, you would need to retrieve down to at least rank 6 (where d6 sits), so N ≥ 6 for this query — but a query whose allowed documents ranked 50th would need N ≥ 50, and you cannot know which in advance. That unbounded, query-dependent N is exactly why over-fetch is a patch and pre-filter is the fix: pre-filter's cost does not depend on how deep the allowed documents are buried.

## External resources

Every major vector database documents metadata filtering and distinguishes pre-filter from post-filter; the Pinecone, Weaviate, Qdrant, and Milvus guides on "filtered search" describe the correctness and recall consequences this module isolates, and most default to or recommend pre-filtering.

For the indexing challenge — why filtered search during an approximate nearest-neighbor traversal is non-trivial — read the vector-database literature on "filtered ANN," which covers how indexes support restricting the search to a metadata-matching subset without falling back to post-filter.

For the access-control version, any treatment of secure or multi-tenant search stresses that permission filters must be applied as pre-filters (or at index level) so users cannot be starved of their own accessible results by higher-scoring documents they may not see.
