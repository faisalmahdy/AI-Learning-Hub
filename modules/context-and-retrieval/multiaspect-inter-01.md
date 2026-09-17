---
id: multiaspect-inter-01
title: Decompose a multi-aspect query — one embedding lands between the aspects and retrieves a shallow compromise
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: A dense retriever turns a query into one vector and ranks documents by cosine similarity, which is exactly right for a query with one information need — and breaks for a query with two. A compound query — "compare the side effects of drug A and drug B", "what are the pricing and the SLA of plan X" — embeds to roughly the average of its two aspect directions and sits at the midpoint between them, and at that midpoint the geometry works against you: a document that thoroughly covers aspect A points in the A direction and is only moderately similar to the midpoint, while a document weakly about both aspects points near the midpoint itself and scores highest, even though it answers neither aspect well. So the top result is a vague both-mentioning passage, and the two documents that actually contain each aspect's answer rank below it; retrieve a few and you get the compromise plus, at best, one aspect. On the fixture the aspects are orthogonal directions and the compound query is their sum: single-vector retrieval ranks the weakly-both document first (cosine 1.000) and the two strong single-aspect documents below it (0.707 each), so top-2 covers only aspect A. The fix is to decompose — split the compound query into one sub-query per aspect, retrieve for each independently, and union the results, so each aspect's strong document is retrieved by a sub-query pointing straight at it and both answer sources are recovered (coverage A and B). This is distinct from multi-hop retrieval, where the aspects chain through a bridge entity and must resolve in sequence; here they are independent parallel needs. The rule: a single query vector can only point one direction, so a question with two directions needs two queries.
eli5: Imagine asking a librarian for "a book about volcanoes and a book about penguins" but you're only allowed to point at one spot on a map of the shelves. You'd point halfway between the volcano shelf and the penguin shelf — and the book sitting right there is some thin thing that mentions both a little and covers neither well, so that's what you get, while the real volcano book and the real penguin book are off to the sides where your single point doesn't reach. The fix is to point twice: once at the volcano shelf, once at the penguin shelf, and take the best book from each. One point can only aim one way, so a two-part question needs two points.
---

## Why this module

Dense retrieval is built on a clean idea: meaning is a direction, and a query points at the documents that mean the same thing. It works beautifully when the query means one thing. The failure this module is about happens the moment a query means two things, which is more common than it sounds — any "compare X and Y", any request that bundles two facts, any question with an "and" joining independent needs.

The trouble is not that the retriever is confused; it does exactly what it is designed to do. It points the single query vector in a single direction and returns what lies there. The bug is that a two-part question has no single direction, so the one vector aims at the compromise between them — and the compromise is the worst place to look.

**A query vector points one way, so a question that points two ways retrieves the midpoint, where the shallow both-mentioning document lives.**

## Concepts

An embedding places a document's meaning as a direction in vector space, and cosine similarity ranks by how closely a query's direction matches. For a single-aspect query this is ideal: the query points at its topic, and the documents most about that topic score highest.

A compound query embeds to a blend of its parts. Ask about two aspects and the query vector lands roughly at their average — the midpoint between the aspect-A direction and the aspect-B direction. Now consider what scores well against that midpoint. A document that thoroughly covers aspect A points in the A direction, which is off to one side of the midpoint, so its similarity is only moderate. A document that is weakly about both aspects points near the midpoint itself, so its similarity is high — higher than either strong document.

That is the whole failure. The retriever ranks the shallow both-mentioning document above the two documents that each contain a real answer, because proximity to the averaged query rewards being in the middle, and being in the middle is what a shallow compromise document does. Pull the top few and you get that compromise, and then perhaps one aspect's document; the other aspect's document, which you need, sits just below the cut.

The fix does not touch the retriever — it changes what you hand it. Decompose the compound query into one sub-query per aspect, each pointing straight at its aspect's direction. Run them independently and union the results. Sub-query A retrieves the strong A document, sub-query B the strong B document, and the merged set covers both aspects. You traded one badly-aimed query for two well-aimed ones.

This is a different situation from multi-hop retrieval, and the difference decides the fix. Multi-hop questions chain — you cannot retrieve the second piece until the first names a bridge entity, so the sub-queries run in sequence. Multi-aspect questions are parallel — the aspects are independent, so the sub-queries can run at once and simply merge.

**A single query vector aims at the average of a compound query's aspects; splitting it into a sub-query per aspect aims each one at a real target and recovers the documents the average buried.**

<svg role="img" aria-label="Two approaches. One compound query is a single arrow pointing at the midpoint between aspect A and aspect B. Decomposition is two arrows, one pointing at aspect A and one at aspect B." viewBox="0 0 440 150">
<rect x="0" y="0" width="440" height="150" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">one arrow at the midpoint, or two arrows at the aspects</text>
<text x="20" y="52" fill="var(--s1)" font-size="11">single query</text>
<line x1="120" y1="70" x2="200" y2="45" stroke="var(--s1)"></line>
<text x="150" y="40" fill="var(--s1)" font-size="9">midpoint (compromise)</text>
<text x="20" y="104" fill="var(--s2)" font-size="11">decomposed</text>
<line x1="120" y1="118" x2="210" y2="118" stroke="var(--s2)"></line>
<text x="216" y="121" fill="var(--s2)" font-size="9">&#8594; aspect A</text>
<line x1="120" y1="118" x2="150" y2="88" stroke="var(--s2)"></line>
<text x="150" y="86" fill="var(--s2)" font-size="9">&#8593; aspect B</text>
</svg>
^ The single query commits to one direction — the average — while decomposition sends one arrow at each aspect, so no aspect's document is left off to the side.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/context-and-retrieval/code/multiaspect-inter-01/multiaspect.py

The fixture uses orthogonal aspect directions so the geometry is exact.

```json filename=modules/context-and-retrieval/code/multiaspect-inter-01/multiaspect.json:3-11 COMPLETE
  "aspect_a": [1.0, 0.0],
  "aspect_b": [0.0, 1.0],
  "compound_query": [1.0, 1.0],
  "top_k": 2,
  "documents": [
    {"id": "doc_a",    "embedding": [1.0, 0.0],  "covers": ["A"]},
    {"id": "doc_b",    "embedding": [0.0, 1.0],  "covers": ["B"]},
    {"id": "doc_both_weak", "embedding": [1.0, 1.0], "covers": []},
    {"id": "doc_irrel", "embedding": [-1.0, 0.3], "covers": []}
  ]
```

Ranking is cosine similarity, and single-vector retrieval takes the top-k against the one compound query.

```python filename=modules/context-and-retrieval/code/multiaspect-inter-01/multiaspect.py:39-42 COMPLETE
def rank(query, documents):
    """Documents by descending cosine similarity to the query."""
    scored = [(d["id"], cosine(query, d["embedding"])) for d in documents]
    return sorted(scored, key=lambda t: t[1], reverse=True)
```

```python filename=modules/context-and-retrieval/code/multiaspect-inter-01/multiaspect.py:45-47 COMPLETE
def retrieve_single(query, documents, k):
    """Single-vector retrieval: the top-k documents by similarity to the one compound query."""
    return [doc_id for doc_id, _s in rank(query, documents)[:k]]
```

```text filename=multiaspect.py --single
SINGLE — one compound query vector [1.0, 1.0], top-2
----------------------------------------------------------------
  doc_both_weak  cosine 1.000
  doc_a          cosine 0.707
  doc_b          cosine 0.707
  doc_irrel      cosine -0.474
  retrieved: ['doc_both_weak', 'doc_a']   aspects covered: ['A']
----------------------------------------------------------------
  the weakly-both doc sits at the query midpoint and wins; an aspect's strong doc is missed
```

doc_both_weak points exactly along the compound query, so it scores a perfect 1.000 and tops the list — above doc_a and doc_b, the documents that actually cover each aspect, which tie at 0.707. The top-2 is the compromise plus aspect A's document; aspect B's document is left out, so the retrieved set covers only A.

<svg role="img" aria-label="A 2-D plot. Aspect A points right, aspect B points up, the compound query points diagonally between them. doc_a is on the A axis, doc_b on the B axis, doc_both_weak on the diagonal aligned with the query. The diagonal document is closest to the query." viewBox="0 0 300 200">
<rect x="0" y="0" width="300" height="200" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">the compound query aims at the midpoint</text>
<line x1="40" y1="170" x2="240" y2="170" stroke="var(--line)"></line>
<line x1="40" y1="170" x2="40" y2="40" stroke="var(--line)"></line>
<line x1="40" y1="170" x2="220" y2="170" stroke="var(--muted)"></line>
<text x="200" y="186" fill="var(--muted)" font-size="9">aspect A</text>
<line x1="40" y1="170" x2="40" y2="50" stroke="var(--muted)"></line>
<text x="46" y="52" fill="var(--muted)" font-size="9">aspect B</text>
<line x1="40" y1="170" x2="180" y2="60" stroke="var(--s1)" stroke-dasharray="4 3"></line>
<text x="150" y="52" fill="var(--s1)" font-size="9">compound query</text>
<circle cx="215" cy="170" r="4" fill="var(--s2)"></circle>
<text x="200" y="162" fill="var(--s2)" font-size="8">doc_a</text>
<circle cx="40" cy="55" r="4" fill="var(--s2)"></circle>
<text x="46" y="70" fill="var(--s2)" font-size="8">doc_b</text>
<circle cx="178" cy="63" r="4" fill="var(--s1)"></circle>
<text x="150" y="80" fill="var(--s1)" font-size="8">doc_both_weak (wins)</text>
</svg>
^ doc_both_weak lies on the query's diagonal, so it is closest and ranks first, while doc_a and doc_b sit off on the axes where each aspect's real answer lives — further from the midpoint the single query aims at.

## Build

Decomposition runs one sub-query per aspect and unions the tops.

```python filename=modules/context-and-retrieval/code/multiaspect-inter-01/multiaspect.py:50-57 COMPLETE
def retrieve_decomposed(sub_queries, documents):
    """Decomposed retrieval: the top-1 document for each sub-query, unioned (order preserved)."""
    out = []
    for q in sub_queries:
        top = rank(q, documents)[0][0]
        if top not in out:
            out.append(top)
    return out
```

```text filename=multiaspect.py --decompose
DECOMPOSE — one sub-query per aspect: [1.0, 0.0] and [0.0, 1.0]
----------------------------------------------------------------
  aspect A top: doc_a
  aspect B top: doc_b
  merged: ['doc_a', 'doc_b']   aspects covered: ['A', 'B']
----------------------------------------------------------------
  each sub-query points straight at one aspect's strong doc, so both are retrieved
```

Sub-query A points along the A axis and retrieves doc_a; sub-query B points along the B axis and retrieves doc_b. The merged set is exactly the two documents that answer the two aspects, covering both — the shallow doc_both_weak is not even needed.

<svg role="img" aria-label="A comparison of aspect coverage. Single-vector retrieval covers only aspect A. Decomposed retrieval covers both aspect A and aspect B." viewBox="0 0 440 130">
<rect x="0" y="0" width="440" height="130" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">aspects covered by the retrieved set (need both)</text>
<text x="20" y="56" fill="var(--s1)" font-size="11">single-vector</text>
<text x="170" y="56" fill="var(--s2)" font-size="11">A</text>
<text x="210" y="56" fill="var(--s1)" font-size="11">B missing</text>
<text x="20" y="96" fill="var(--s2)" font-size="11">decomposed</text>
<text x="170" y="96" fill="var(--s2)" font-size="11">A</text>
<text x="210" y="96" fill="var(--s2)" font-size="11">B</text>
<text x="250" y="96" fill="var(--muted)" font-size="9">both covered</text>
</svg>
^ The single query covers one aspect and drops the other; the two sub-queries between them cover both, which is what a compound question needs.

The self-test pins the ranking failure and the coverage fix.

```python filename=modules/context-and-retrieval/code/multiaspect-inter-01/multiaspect.py:104-110 COMPLETE
    weakboth_ranked_first = top_id == "doc_both_weak"
    print("  the compound query ranks the weakly-both doc first = %s (%s at %.3f)" % (weakboth_ranked_first, top_id, ranking[0][1]))

    single_got = retrieve_single(q, d["documents"], d["top_k"])
    single_cov = coverage(single_got, d["documents"])
    single_misses = single_cov != both_aspects
    print("  single-vector top-%d does NOT cover both aspects = %s (covers %s)" % (d["top_k"], single_misses, sorted(single_cov) or "none"))
```

```text filename=multiaspect.py --check
SELF-TEST — single-vector ranks the weak-both doc above the strong single-aspect docs and its top-k misses an aspect, while decomposition covers both aspects
----------------------------------------------------------------------------------------------------------------
  the compound query ranks the weakly-both doc first = True (doc_both_weak at 1.000)
  single-vector top-2 does NOT cover both aspects = True (covers ['A'])
  decomposed retrieval covers both aspects = True (covers ['A', 'B'])
  both strong single-aspect docs score below the weak-both doc = True (A 0.707, B 0.707 < 1.000)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  weakboth_ranked_first=True  single_misses=True  decompose_covers_both=True  strong_below_weak=True
```

**strong_below_weak is the geometry in one line: proximity to the averaged query rewards the document in the middle, so a shallow both-mentioning passage outranks the two documents that actually hold the answers.**

## Definition of done

You can explain why a compound query's single embedding lands at the midpoint between its aspects, and why the midpoint favors a shallow both-mentioning document over the strong single-aspect ones.

You can trace the retrieval failure: the top-k fills with the compromise and at most one aspect, leaving the other aspect's answer source just below the cut.

You can describe the decomposition fix — one sub-query per aspect, retrieved independently and merged — and why each sub-query aims at a real target the averaged query missed.

You can distinguish this from multi-hop retrieval: multi-aspect needs are independent and parallel (sub-queries at once), multi-hop needs chain through a bridge entity (sub-queries in sequence).

## Boss fight

Users of your support bot ask questions like "does the Pro plan include SSO, and what's its uptime guarantee?" and the bot reliably answers one half well and the other vaguely or wrong, even though your docs have a thorough SSO page and a thorough SLA page.

First: explain, in terms of where the query embedding sits relative to the SSO page and the SLA page, why the bot gets one half and botches the other. What kind of document would the single-vector retriever actually rank first for this query, and why is it the least useful one?

Then: implement decomposition. You need to split the query into aspects before retrieving — describe how you would detect that a query is multi-aspect and produce the sub-queries, and what you do with the two result sets before handing them to the generator. Why is unioning the tops better than concatenating the two full top-k lists?

Finally: decomposition has a cost the single query does not — more retrieval calls and a splitting step that can be wrong. Give one failure mode of the splitter (over-splitting a single-aspect query, or under-splitting a compound one) and its consequence, and describe a cheap check on the retrieved results that would tell you whether the decomposition helped or hurt for a given query.

## External resources

LlamaIndex and LangChain both ship "sub-question" or "multi-query" retrievers that implement exactly this — generate several sub-queries from one question, retrieve for each, and combine — and their documentation frames the motivation as a single embedding being unable to represent multiple intents.

The RAG-fusion and multi-query retrieval write-ups describe generating query variants and merging their results (often with reciprocal rank fusion), which is the practical machinery for the union step this module builds by hand.
