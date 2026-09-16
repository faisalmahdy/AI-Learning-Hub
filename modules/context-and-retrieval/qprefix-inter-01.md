---
id: qprefix-inter-01
title: Prefix queries and documents the way the embedding model was trained — an asymmetric retriever with no query prefix returns look-alikes, not answers
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: Many modern retrieval embedding models are asymmetric: they are trained with a short instruction prefix on every input saying whether the text is a search query or a document being searched — "query: ..." versus "passage: ..." (the exact tokens vary by model). This is not decoration. Queries and documents have systematically different shapes — a short question versus a long passage — and the prefix lets one model handle both by learning to map a correctly-prefixed query near the passages that answer it, rather than near passages that merely resemble it in wording or length. The prefix feels cosmetic, so it is one of the most commonly dropped steps, and dropping it fails silently: embed a query with no prefix and the model treats it as a passage, placing the query vector where a document of that text would go — a different region of the space than the query encoder would have used — so nearest-neighbor search finds documents that look like the query instead of documents that answer it. Retrieval quality drops and nothing flags it, because the results still look plausible. The fix is to embed each text with the prefix the model documents for its role, on every call, matching training — a one-line formatting step whose omission quietly degrades every retrieval. On a fixture of unit embeddings, the query embedded with its prefix ranks the answering document d1 first (cosine 0.80 vs 0.60), while the same query embedded without the prefix lands elsewhere and ranks the distractor d2 first (0.99 vs 0.92).
eli5: Some search tools use a helper that needs to be told whether a piece of text is a question you're asking or a page it should search through — you tell it by sticking a little label at the front, like "query:" or "passage:". The helper was trained to put a labeled question right next to the pages that answer it. If you forget the "query:" label, the helper thinks your question is just another page, and files it next to pages that sound like your question rather than pages that answer it — so you get back things that look similar instead of things that actually help. Nothing breaks; you just quietly get worse results. The label isn't optional decoration — it's how the helper knows what it's looking at.
---

## Why this module

Embedding-based retrieval feels model-agnostic: turn text into a vector, find the nearest vectors. That mental model quietly assumes the encoder treats all text the same way, and for a large class of modern retrieval models that assumption is false. They are asymmetric dual encoders, trained with an explicit instruction prefix that tells the model the role of each input — a query to search with, or a passage to be searched. The prefix is part of the input the model was optimized on, not a label for your own bookkeeping.

The reason is that queries and documents are genuinely different objects. A query is short, often a question, phrased the way a user asks; a passage is longer, declarative, phrased the way an answer is written. A symmetric encoder that embedded both identically would place a query near text that is phrased like the query — other questions, similar wording — rather than near the declarative passage that answers it. The prefix lets a single model learn two behaviors: prefixed as a query, map toward answers; prefixed as a passage, sit where answers live. The whole query-to-answer geometry is conditioned on the prefix being present.

Omit it and you have not made a small stylistic slip; you have fed the model an input from outside its training distribution and taken the nearest neighbors of the wrong point. This module shows the retrieval flipping between the correctly-prefixed and unprefixed query on the same documents.

**Asymmetric retrievers learn the query-to-answer mapping only for correctly-prefixed inputs, so a query embedded without its prefix lands in passage space and retrieves documents that resemble the query rather than documents that answer it — the prefix is a required part of the input, not decoration.**

## Concepts

The fixture is the query embedded two ways — with its prefix and without — and two documents, one that answers the query and one distractor. The vectors are unit-length and 2-D so every cosine is a hand-checkable dot product.

```json filename=modules/context-and-retrieval/code/qprefix-inter-01/qprefix.json:3-8 COMPLETE
  "q_correct": [1.0, 0.0],
  "q_no_prefix": [0.5, 0.866],
  "documents": [
    {"id": "d1", "answer": true, "emb": [0.8, 0.6]},
    {"id": "d2", "answer": false, "emb": [0.6, 0.8]}
  ]
```

Retrieval ranks documents by cosine similarity to the query embedding — and since all vectors are unit-length, cosine is just the dot product. A helper marks which document is the true answer.

```python filename=modules/context-and-retrieval/code/qprefix-inter-01/qprefix.py:32-43 COMPLETE
def cosine(a, b):
    """Vectors are unit-length, so cosine is the dot product."""
    return sum(x * y for x, y in zip(a, b))


def rank(query, documents):
    scored = [(d["id"], cosine(query, d["emb"])) for d in documents]
    return sorted(scored, key=lambda kv: kv[1], reverse=True)


def answer_id(documents):
    return next(d["id"] for d in documents if d["answer"])
```

The ranking function is identical for both query embeddings — the only thing that changes is which query vector goes in, and that is decided entirely by whether the prefix was applied before embedding.

<svg role="img" aria-label="On a unit circle, the prefixed query points along d1 the answer, while the unprefixed query is rotated toward d2 the distractor, so each retrieves the document it points at" viewBox="0 0 320 140">
  <circle cx="70" cy="80" r="50" fill="none" stroke="var(--line)" stroke-width="1"/>
  <line x1="70" y1="80" x2="120" y2="80" stroke="var(--s1)" stroke-width="2"/><text x="122" y="82" font-size="7" fill="var(--s1)">query: (prefixed)</text>
  <line x1="70" y1="80" x2="95" y2="37" stroke="var(--s2)" stroke-width="2"/><text x="96" y="34" font-size="7" fill="var(--s2)">no prefix</text>
  <line x1="70" y1="80" x2="110" y2="50" stroke="var(--ink)" stroke-width="1" stroke-dasharray="2 2"/><text x="112" y="50" font-size="7" fill="var(--ink)">d1 answer</text>
  <line x1="70" y1="80" x2="94" y2="42" stroke="var(--muted)" stroke-width="1" stroke-dasharray="2 2"/><text x="60" y="24" font-size="7" fill="var(--muted)">d2 distractor</text>
  <text x="150" y="96" font-size="7.5" fill="var(--s1)">prefixed query nearest d1 (answer)</text>
  <text x="150" y="112" font-size="7.5" fill="var(--s2)">unprefixed query nearest d2 (look-alike)</text>
  <text x="150" y="128" font-size="7.5" fill="var(--muted)">same documents; the prefix decides where the query points</text>
</svg>
^ The prefixed query points along d1, the answering document, so it is the nearest neighbor. Dropping the prefix rotates the query vector toward d2, the distractor that resembles the query — so the unprefixed query retrieves the look-alike. Same documents; only the query's position moved.

**The ranking is the same nearest-neighbor search either way; the prefix decides where the query vector sits, and that alone flips which document is closest.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the query-embedding step of a dense retriever, reduced to 2-D unit vectors so every cosine is checkable by hand.

Run `--embed` to see the cosines.

```text filename=qprefix.py --embed
  document   answer?   query: prefix   no prefix
  d1         True      0.80            0.92
  d2         False     0.60            0.99
```

With the query prefix, the answering document d1 scores 0.80 and the distractor d2 scores 0.60 — the answer is closer, as it should be. Without the prefix, both scores rise (the unprefixed query happens to sit near both), but d2 now scores 0.99 against d1's 0.92 — the distractor is closer. The prefix did not just scale the scores; it reordered them, because it moved the query to a different point whose nearest neighbor is a different document.

Now `--rank` ranks the documents under each query embedding.

```python filename=modules/context-and-retrieval/code/qprefix-inter-01/qprefix.py:62-63 COMPLETE
    rc = rank(data["q_correct"], docs)
    rn = rank(data["q_no_prefix"], docs)
```

The two orderings put a different document on top.

```text filename=qprefix.py --rank
  with 'query:' prefix : [('d1', 0.8), ('d2', 0.6)]  -> top d1
  without prefix       : [('d2', 0.9928000000000001), ('d1', 0.9196)]  -> top d2
```

The correctly-prefixed query retrieves d1 first — the answer. The unprefixed query retrieves d2 first — the distractor that resembles the query. A retrieval-augmented system built on the unprefixed query would hand the model the wrong passage and generate from it, and nothing in the pipeline would signal an error: d2 was returned with a high similarity of 0.99, higher than anything the correct query produced, so it looks like a confident, good match. The failure is invisible precisely because the wrong answer scores well.

<svg role="img" aria-label="Retrieval outcome: prefixed query returns d1 the answer, unprefixed query returns d2 the distractor with a high but misleading similarity" viewBox="0 0 320 110">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">top retrieved document (answer = d1)</text>
  <text x="10" y="42" font-size="8.5" fill="var(--s1)">query: prefix</text>
  <rect x="110" y="32" width="80" height="16" fill="var(--s1)"/><text x="126" y="44" font-size="8" fill="var(--panel)">d1 (answer)</text>
  <text x="196" y="44" font-size="8" fill="var(--ink)">correct</text>
  <text x="10" y="72" font-size="8.5" fill="var(--s2)">no prefix</text>
  <rect x="110" y="62" width="80" height="16" fill="var(--s2)"/><text x="126" y="74" font-size="8" fill="var(--panel)">d2 (distractor)</text>
  <text x="196" y="74" font-size="8" fill="var(--ink)">wrong — but scores 0.99</text>
  <text x="10" y="98" font-size="7.5" fill="var(--muted)">the wrong result looks confident, so the missing prefix never gets noticed</text>
</svg>
^ The prefixed query retrieves the answer d1; the unprefixed query retrieves the distractor d2, and does so with a higher similarity (0.99) than the correct query ever produced. The high score on a wrong result is what makes the missing prefix a silent bug.

**The prefixed query retrieves the answer d1; the unprefixed query retrieves the distractor d2 at a misleadingly high 0.99 — the prefix reorders the results, and its absence fails silently because the wrong document scores well.**

## Build

The self-test establishes the mechanism and the failure: the prefix changes the query embedding, the correctly-prefixed query retrieves the answer, and the unprefixed query retrieves the wrong document.

```python filename=modules/context-and-retrieval/code/qprefix-inter-01/qprefix.py:81-88 COMPLETE
    prefix_changes_embedding = data["q_correct"] != data["q_no_prefix"]
    print("  the prefix changes the query's embedding = %s (%s vs %s)" % (prefix_changes_embedding, data["q_correct"], data["q_no_prefix"]))

    prefixed_retrieves_answer = rc[0][0] == ans
    print("  the correctly-prefixed query retrieves the answer first = %s (top %s)" % (prefixed_retrieves_answer, rc[0][0]))

    unprefixed_retrieves_wrong = rn[0][0] != ans
    print("  the unprefixed query retrieves the wrong document first = %s (top %s)" % (unprefixed_retrieves_wrong, rn[0][0]))
```

Then the diagnosis: the two embeddings produce different rankings, and the unprefixed query is closest to the look-alike distractor rather than the answer.

```python filename=modules/context-and-retrieval/code/qprefix-inter-01/qprefix.py:90-93 COMPLETE
    rankings_differ = [i for i, _ in rc] != [i for i, _ in rn]
    print("  the two query embeddings produce different rankings = %s" % rankings_differ)

    unprefixed_prefers_lookalike = cosine(data["q_no_prefix"], next(d["emb"] for d in docs if not d["answer"])) > cosine(data["q_no_prefix"], next(d["emb"] for d in docs if d["answer"]))
    print("  the unprefixed query is closest to the distractor, not the answer = %s" % unprefixed_prefers_lookalike)
```

Running the check confirms every clause.

```text filename=qprefix.py --check
  the prefix changes the query's embedding = True ([1.0, 0.0] vs [0.5, 0.866])
  the correctly-prefixed query retrieves the answer first = True (top d1)
  the unprefixed query retrieves the wrong document first = True (top d2)
  the two query embeddings produce different rankings = True
  the unprefixed query is closest to the distractor, not the answer = True
```

**The check ties the wrong retrieval to the missing prefix — a different query embedding, closest to the look-alike — and shows the correctly-prefixed query retrieving the answer, the fix being the one formatting step the model was trained to expect.**

## Definition of done

Done means the correctly-prefixed query retrieves the answer and the unprefixed query retrieves a look-alike distractor, from the same documents and the same ranking code. The clause that the unprefixed query prefers the distractor over the answer is the concrete statement of "query embedded in passage space": it lands near text that resembles it rather than text that answers it, which is exactly the symmetric-encoder behavior the prefix exists to prevent.

Two clarifications keep this correct in practice. First, the exact prefixes are model-specific and must match what the model was trained with — E5 uses "query:" and "passage:", BGE uses an instruction like "Represent this sentence for searching relevant passages:" on the query side only, Nomic uses "search_query:" and "search_document:", and some models are symmetric and need no prefix at all. There is no universal prefix; the rule is to read the model card and apply exactly its documented format, on both the query and the document side, consistently between indexing and querying. Applying the wrong prefix, or the query prefix to documents, is as broken as applying none. Second, the mismatch is especially insidious because it survives testing: a demo where you embed a handful of documents and queries the same way (both unprefixed, say) can still return something, and top-1 on easy queries may look fine, so the degradation shows up only as mediocre recall on harder queries that a correctly-prefixed model would have nailed. The safeguard is to follow the model's documented usage exactly from the start, and to sanity-check retrieval quality against the model's own reported benchmark setup, which always includes the prefixes.

<svg role="img" aria-label="Different models use different prefixes: E5 query/passage, Nomic search_query/search_document, BGE an instruction on the query only, some none; apply exactly the model's documented format on both sides" viewBox="0 0 320 118">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">the prefix is model-specific — match the model card exactly</text>
  <text x="16" y="34" font-size="7.5" fill="var(--s1)">E5:</text><text x="70" y="34" font-size="7" fill="var(--ink)">query:  /  passage:</text>
  <text x="16" y="50" font-size="7.5" fill="var(--s1)">Nomic:</text><text x="70" y="50" font-size="7" fill="var(--ink)">search_query:  /  search_document:</text>
  <text x="16" y="66" font-size="7.5" fill="var(--s1)">BGE:</text><text x="70" y="66" font-size="7" fill="var(--ink)">instruction on the query side only</text>
  <text x="16" y="82" font-size="7.5" fill="var(--s1)">some:</text><text x="70" y="82" font-size="7" fill="var(--ink)">symmetric — no prefix</text>
  <text x="10" y="104" font-size="7.5" fill="var(--muted)">apply the documented format on BOTH sides, consistently at index and query time</text>
</svg>
^ There is no universal prefix — E5, Nomic, and BGE each specify a different format, and some models use none. The rule is to apply exactly the model's documented prefixes on both the query and document side, consistently between indexing and querying.

**Done means the correctly-prefixed query retrieves the answer while the unprefixed query retrieves a look-alike — so the rule is to apply the model's exact documented prefixes on both sides, matching training, since the query-to-answer geometry exists only for correctly-prefixed inputs.**

## Boss fight

A team switches their retriever from OpenAI embeddings to a self-hosted E5 model to cut costs. Offline metrics on their labeled set drop noticeably, and users report the search "feels dumber" — it returns pages that use the same words as the query but do not answer it. The migration was a drop-in replacement of the embedding call. What is the likely cause, and how would you fix and verify it?

The likely cause is a missing instruction prefix. E5 is an asymmetric model trained with "query: " on queries and "passage: " on documents, and a drop-in replacement of the embedding call almost certainly embeds both queries and documents as raw text with no prefix. Without the query prefix, E5 embeds the query as if it were a passage, so it lands near documents that resemble the query in wording rather than documents that answer it — exactly the reported symptom of returning same-words pages that do not answer, and exactly the offline-metric drop. The fix is to apply E5's documented prefixes: prepend "query: " to every query before embedding and "passage: " to every document before embedding and indexing, matching how E5 was trained. Both sides must be reindexed with the passage prefix and queried with the query prefix; applying it to only one side, or swapping them, is still wrong. To verify, re-run the offline metrics on the labeled set after adding the prefixes and confirm recall recovers to or above the previous embeddings' level, and spot-check a few of the previously-bad queries to confirm they now return answering passages rather than word-matches. As a general safeguard, when adopting any embedding model, read its model card for whether it is asymmetric and what prefixes (or instruction templates) it expects, and bake that formatting into the shared embedding function so queries and documents cannot be embedded without it — the prefix is part of the model's input contract, not an optional string, and treating an embedding call as a drop-in replacement across models with different contracts is what caused the regression.

## External resources

The model cards and papers for asymmetric retrieval embedders (E5's "query:"/"passage:" convention, BGE's query instruction, Nomic's "search_query:"/"search_document:", and the instruction-tuned embedding literature) — the exact prefixes each model expects and why asymmetric encoding maps queries toward answers rather than look-alikes.

Documentation for embedding libraries and vector-DB integrations on prefixing/instruction handling (Sentence-Transformers prompt/prompt_name arguments and the guidance to apply the model's documented format consistently at index and query time) — the mechanics of applying prefixes correctly on both sides and the failure mode of omitting or mismatching them.
