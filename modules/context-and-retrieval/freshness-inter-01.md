---
id: freshness-inter-01
title: Search the index, but the index is a snapshot — a document added after the last build is invisible until you re-index
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: A retrieval system does not search your data; it searches an index of your data, and the index is a snapshot frozen at the moment it was last built. Every document that existed then is in it; every document created or changed since then is not, until the index is rebuilt or incrementally updated. This is easy to forget because the corpus and the index feel like the same thing — you add a document and assume it is findable — but they are decoupled: the write hits the store immediately, and the index catches up only on its own schedule. In the gap between "document added" and "index updated," the document exists and is completely invisible to search. A query whose true best answer is that new document gets, instead, the best of the old documents, and it comes back looking like a perfectly good result — no error, no empty response, just a confidently returned older, worse match with the right answer sitting unindexed a few milliseconds away. The failure is worst exactly where it matters: freshness-sensitive queries (the latest release, today's incident, the just-uploaded file), because the correct answer is the newest document, the one most likely to be on the wrong side of the last build. The fix is to manage freshness as a first-class property: incremental/near-real-time indexing, monitored indexing lag, and a freshness SLA. On a fixture where the best answer d2_latest_update (relevance 5) was added after the index build so it is unindexed, a search against the stale index returns d1_overview (relevance 2) and misses it entirely, while re-indexing lets the same search find d2.
eli5: Imagine a library where you don't walk the shelves — you search a card catalog that a librarian typed up last night. If a brand-new book arrives this morning, it's on the shelf, but there's no card for it yet, so when you search the catalog you can't find it — you get an older book on the same topic instead, and nothing tells you the better, newer book is sitting right there. The catalog isn't your library; it's a snapshot of your library from the last time someone updated it. To find the new book you have to wait for (or ask for) the catalog to be updated. Fast-moving questions — "what's the newest book on X?" — are exactly the ones the out-of-date catalog gets wrong.
---

## Why this module

The most natural assumption in retrieval is also a trap: that searching your documents means searching your documents. It does not — it means searching an index, a derived structure built from your documents at a particular moment and frozen there until it is rebuilt. The store and the index are two different things that drift apart the instant you write to the store, and search only ever consults the index. So a document can be fully saved, visible in the database, referenced by its id everywhere else in the system, and still be completely unfindable by search, for no reason except that the index has not caught up. Nothing about this announces itself; the search returns a result, and the result is simply the best of what the index happened to contain.

The index is a snapshot: every document that existed when it was built is in it, and every document created or changed since is not, until the index is rebuilt or incrementally updated. In the gap between "document added" and "index updated," the document is invisible to search, and a query whose true best answer is that new document gets the best of the old documents instead — a confidently returned older, worse match, with the right answer sitting unindexed nearby.

The failure is worst on freshness-sensitive queries: the latest release, today's incident, the price that changed this morning — the correct answer is the newest document, which is the one most likely to be on the wrong side of the last build. The fix is to manage freshness as a first-class property — incremental indexing, monitored lag, a freshness SLA. This module searches a stale index and a fresh one over the same corpus.

**A search index is a snapshot, so a document added or changed after the last index build is invisible to search until the index is updated — and a query for it silently returns an older, worse match instead of the right answer — so index freshness must be managed (incremental/near-real-time indexing, monitored lag, a freshness SLA) rather than assumed.**

## Concepts

**Search sees only what the index contains** — a stale index restricts the candidates to the indexed documents, and returns the best of those.

```python filename=modules/context-and-retrieval/code/freshness-inter-01/freshness.py:53-58 COMPLETE
def search(documents, use_full_corpus):
    """Return the highest-relevance document the search can see. A stale index sees only indexed docs."""
    candidates = documents if use_full_corpus else [d for d in documents if d["indexed"]]
    if not candidates:
        return None
    return max(candidates, key=lambda d: d["relevance"])
```

**The truly best answer is defined over the whole corpus**, indexed or not — the target the stale search cannot reach.

```python filename=modules/context-and-retrieval/code/freshness-inter-01/freshness.py:61-63 COMPLETE
def best_document(documents):
    """The truly best answer in the corpus, indexed or not."""
    return max(documents, key=lambda d: d["relevance"])
```

<svg role="img" aria-label="A corpus box containing three documents; the index snapshot is a smaller box inside it holding only two, with d2_latest_update outside the index because it was added after the build" viewBox="0 0 300 116" width="300" height="116">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the index is a snapshot inside the corpus — d2 is outside it</text>
  <rect x="14" y="22" width="272" height="80" fill="none" stroke="var(--muted)"/><text x="20" y="34" fill="var(--muted)" font-size="7">corpus (the store)</text>
  <rect x="26" y="44" width="150" height="48" fill="none" stroke="var(--s1)"/><text x="32" y="56" fill="var(--s1)" font-size="7">index snapshot</text>
  <rect x="34" y="62" width="60" height="22" fill="var(--s1)"/><text x="40" y="76" fill="var(--panel)" font-size="6">d1 (rel 2)</text>
  <rect x="100" y="62" width="60" height="22" fill="var(--s1)"/><text x="106" y="76" fill="var(--panel)" font-size="6">d3 (rel 1)</text>
  <rect x="200" y="62" width="72" height="22" fill="var(--s2)"/><text x="204" y="76" fill="var(--panel)" font-size="6">d2 (rel 5)</text>
  <text x="196" y="56" fill="var(--s2)" font-size="6">added after build →</text>
  <text x="200" y="96" fill="var(--s2)" font-size="6">in corpus, NOT in index</text>
</svg>
^ The corpus holds all three documents, but the index snapshot contains only the two that existed at build time (d1, d3); the best match d2 was added afterward and sits in the corpus outside the index, so search — which consults the index — cannot see it.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/freshness-inter-01/freshness.py

The fixture is three documents with their relevance to the query and whether the current index snapshot contains them.

```json filename=modules/context-and-retrieval/code/freshness-inter-01/freshness.json:3-7 COMPLETE
  "documents": [
    {"id": "d1_overview", "relevance": 2, "indexed": true},
    {"id": "d2_latest_update", "relevance": 5, "indexed": false},
    {"id": "d3_misc", "relevance": 1, "indexed": true}
  ]
```

Run `--search`.

```text filename=--search
SEARCH — top result from the stale index vs a freshly rebuilt index
------------------------------------------------------------------
  corpus (id, relevance, indexed?):
    d1_overview        relevance 2   indexed=True
    d2_latest_update   relevance 5   indexed=False
    d3_misc            relevance 1   indexed=True
------------------------------------------------------------------
  stale index returns: d1_overview (relevance 2)
  fresh index returns: d2_latest_update (relevance 5)
  the stale index misses the best document because it is not yet indexed.
```

Read the corpus and the two results. The best answer to this query is d2_latest_update, with relevance 5 — clearly better than d1 (2) or d3 (1). But d2's `indexed` flag is false: it was added after the last index build, so it is in the corpus but not in the index. The stale index, searching only the documents it contains (d1 and d3), returns d1_overview at relevance 2 — a real document, a plausible answer, and wrong, because a strictly better document existed and was simply invisible. The fresh index, having been rebuilt to include d2, returns d2 at relevance 5. Nothing about the stale result looks broken: it is not empty, not an error, not obviously low-quality; it is confidently the best of an incomplete set. The user asked a question whose answer was added five minutes ago and got last week's answer, with no indication that anything was missing.

## Build

The gap that caused this is visible when you compare the index's contents to the corpus.

```text filename=--index
INDEX — the snapshot index vs the corpus
----------------------------------------------------------
  corpus has 3 documents: ['d1_overview', 'd2_latest_update', 'd3_misc']
  index (snapshot) has 2: ['d1_overview', 'd3_misc']
  NOT yet indexed (added after the last build): ['d2_latest_update']
----------------------------------------------------------
  the freshness gap is the 1 document(s) in the corpus but not the index.
```

<svg role="img" aria-label="A timeline: the index is built at time T, document d2 is added at T+1, and a query arrives at T+2; because d2 arrived after the build, it falls in the indexing-lag gap and the query misses it" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">d2 lands in the gap between index build and query</text>
  <line x1="20" y1="54" x2="285" y2="54" stroke="var(--grid)"/>
  <line x1="60" y1="46" x2="60" y2="62" stroke="var(--s1)"/><text x="40" y="40" fill="var(--s1)" font-size="6">index built (T)</text>
  <rect x="60" y="66" width="120" height="10" fill="var(--grid)" opacity="0.5"/><text x="64" y="88" fill="var(--muted)" font-size="6">indexing lag (d2 invisible)</text>
  <line x1="120" y1="46" x2="120" y2="62" stroke="var(--s2)"/><text x="104" y="40" fill="var(--s2)" font-size="6">d2 added (T+1)</text>
  <circle cx="120" cy="54" r="3" fill="var(--s2)"/>
  <line x1="230" y1="46" x2="230" y2="62" stroke="var(--ink)"/><text x="212" y="40" fill="var(--ink)" font-size="6">query (T+2)</text>
  <text x="150" y="54" fill="var(--muted)" font-size="6">→ searches the T snapshot → misses d2</text>
</svg>
^ The index is a snapshot taken at time T; d2 is added at T+1 and the query arrives at T+2, so d2 lives entirely inside the indexing-lag window and the query — which searches the T snapshot — cannot see it, however relevant it is.

The corpus has three documents; the index has two. That one-document difference — the freshness gap — is the entire bug, and it is a property of the *system's timing*, not of the query or the documents' content. d2 is a perfectly good, highly relevant document; it is missing purely because it arrived after the snapshot. This reframes what "retrieval quality" means: a retriever can have a flawless ranking algorithm, perfect embeddings, and an ideal reranker, and still return the wrong answer because the right document was not in the index it searched. Quality is bounded by coverage, and coverage is bounded by freshness. The size of the gap is determined by the indexing lag — how long a document waits between being written and being indexed — so a system that rebuilds its index nightly has up to a day of documents invisible at any moment, while one that indexes within seconds has a near-empty gap. The lag is a dial the system's designers set (explicitly or by neglect), and it directly determines how many recent documents are unsearchable right now.

```python filename=modules/context-and-retrieval/code/freshness-inter-01/freshness.py:104-112 COMPLETE
    index_is_snapshot = sum(1 for d in docs if d["indexed"]) < len(docs)
    print("  the index is a snapshot missing some corpus documents = %s (%d of %d indexed)"
          % (index_is_snapshot, sum(1 for d in docs if d["indexed"]), len(docs)))

    best_doc_unindexed = not best["indexed"]
    print("  the best document is not in the index = %s (%s, relevance %d)" % (best_doc_unindexed, best["id"], best["relevance"]))

    stale_misses_best = stale["id"] != best["id"]
    print("  the stale index misses the best document = %s (returns %s, not %s)" % (stale_misses_best, stale["id"], best["id"]))
```

## Definition of done

The self-test pins the snapshot gap, the unindexed best document, the stale miss, the worse result, and the fix on re-index.

```python filename=modules/context-and-retrieval/code/freshness-inter-01/freshness.py:114-117 COMPLETE
    stale_returns_worse = stale["relevance"] < best["relevance"]
    print("  the stale result is worse than the true best = %s (relevance %d < %d)" % (stale_returns_worse, stale["relevance"], best["relevance"]))

    reindex_finds_best = fresh["id"] == best["id"]
    print("  re-indexing makes the search find the best document = %s (%s, relevance %d)" % (reindex_finds_best, fresh["id"], fresh["relevance"]))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the best document is unindexed, so the stale index returns a worse match; re-indexing finds the best
--------------------------------------------------------------------------------------------------------------
  the index is a snapshot missing some corpus documents = True (2 of 3 indexed)
  the best document is not in the index = True (d2_latest_update, relevance 5)
  the stale index misses the best document = True (returns d1_overview, not d2_latest_update)
  the stale result is worse than the true best = True (relevance 2 < 5)
  re-indexing makes the search find the best document = True (d2_latest_update, relevance 5)
```

<svg role="img" aria-label="Relevance of the returned document: the stale index returns relevance 2, the true best is relevance 5, and re-indexing reaches the best" viewBox="0 0 300 92" width="300" height="92">
  <text x="6" y="12" fill="var(--muted)" font-size="8">returned relevance: stale 2 vs the true best 5</text>
  <line x1="70" y1="24" x2="70" y2="74" stroke="var(--grid)"/>
  <text x="10" y="38" fill="var(--muted)" font-size="7">stale index</text>
  <rect x="70" y="30" width="60" height="12" fill="var(--s2)"/><text x="134" y="40" fill="var(--muted)" font-size="7">d1, relevance 2</text>
  <text x="10" y="60" fill="var(--muted)" font-size="7">fresh index</text>
  <rect x="70" y="52" width="150" height="12" fill="var(--s1)"/><text x="224" y="62" fill="var(--muted)" font-size="7">d2, relevance 5</text>
  <line x1="220" y1="24" x2="220" y2="74" stroke="var(--grid)" stroke-dasharray="1 3"/><text x="204" y="84" fill="var(--muted)" font-size="6">true best = 5</text>
  <text x="10" y="84" fill="var(--muted)" font-size="6">the stale bar falls short only because the best doc was not indexed</text>
</svg>
^ The stale index returns a relevance-2 document while the true best is relevance 5; re-indexing lifts the result to the full 5 — the shortfall is entirely a coverage gap from staleness, not a ranking failure.

**Done means the staleness gap is proven on real results: the best document d2_latest_update (relevance 5) is unindexed because it was added after the build, so the stale index returns d1_overview (relevance 2) and misses it, while re-indexing lets the same search return d2 at relevance 5 — so a search index is a snapshot whose freshness must be managed, because a document added after the last build is silently invisible to search.**

## Boss fight

Predict two ways the freshness problem is deeper than "re-index more often," because the gap has an update side and freshness trades against cost and consistency.

The first trap is that staleness is not only about *added* documents — it is equally about *changed* and *deleted* ones, and the deletion case is a correctness and even safety hazard, not just a missed hit. If a document is edited after indexing, search still ranks and returns it by its OLD content, so a query can match text that no longer exists in the document and surface a stale version — worse, if a document is *deleted* from the corpus but not from the index, search will still return it, handing the user content that was removed, which for access-revoked or legally-retracted documents is a real leak. So the index must track the full lifecycle (add, update, delete/tombstone), and "freshness lag" applies to each: a system that promptly indexes new documents but lazily removes deleted ones has a different, more dangerous staleness than one that just misses recent additions. This is why real indexes use tombstones and versioning and reconcile against the source of truth, and why access control especially must be enforced at query time against current permissions rather than trusting a possibly-stale index — the index can lag, but a deleted or newly-restricted document must not be retrievable through it.

The second trap is that freshness costs, and pushing it toward zero fights throughput, cost, and consistency, so the right answer is a managed target, not "always fresh." Rebuilding or updating an index has real expense — re-embedding documents, rewriting index structures, invalidating caches — and near-real-time indexing amplifies that cost and can hurt query performance (frequent small updates fragment an index; some ANN indexes are expensive to update incrementally and prefer periodic rebuilds). So systems pick an architecture matched to their freshness need: batch rebuild for slow-moving corpora, incremental/streaming indexing for fast-moving ones, and often a hybrid where a small, always-fresh index of very recent documents is searched alongside the large batch index and the results merged — so the newest documents are covered cheaply without re-indexing everything constantly. There is also a monitoring discipline: measure the indexing lag as a real metric, alert when it exceeds the freshness SLA, and make the acceptable staleness an explicit product decision per query type (a knowledge base can tolerate hours; an incident-response or trading system cannot tolerate seconds). The honest framing is that the index being a snapshot is inherent; the engineering is choosing, measuring, and enforcing how stale a snapshot you can afford, and covering the recency-critical paths with a faster source.

**Freshness covers the whole document lifecycle, not just additions: a changed document is returned by its stale content and a deleted-but-not-de-indexed document is still retrievable — a real leak for revoked or retracted content — so track updates and deletions with tombstones/versioning and enforce access control at query time against current permissions, never trusting a possibly-stale index. And freshness is a cost/consistency trade-off, not a free maximum: near-real-time indexing fights throughput and some indexes prefer periodic rebuilds, so match the architecture to the need (batch, incremental, or a hybrid of a small fresh index over a large batch one), monitor indexing lag against an explicit per-query-type freshness SLA, and cover recency-critical paths with a faster source.**

## External resources

Documentation for search engines and vector databases on indexing and refresh (Elasticsearch/OpenSearch refresh interval and near-real-time search, and the incremental-vs-rebuild guidance for FAISS/vector stores) — how the index snapshot is updated, the refresh/commit semantics, and the lag they introduce.

Writing on retrieval-system freshness and lifecycle (incremental indexing, tombstones for deletes, hybrid fresh+batch indexes, and query-time access control) — how production systems bound staleness and handle updated, deleted, and permission-changed documents.

The companion embedding-version, metadata-filter, and multi-hop modules in this topic — freshness is a coverage property upstream of ranking (like using one embedding model version or pre-filtering the corpus), and a retriever's quality is capped by whether the right, current document is in the index it searches at all.
