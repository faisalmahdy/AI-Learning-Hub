---
id: upsert-inter-01
title: Upsert a changed document by id — appending its new vector without deleting the old one leaves a stale duplicate that can win the top slot
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: A vector index is a set of (id, vector) entries, and when a document's text changes its embedding changes, so the correct update replaces the entry for that id. The trap is that a naive pipeline appends: it computes the new embedding and inserts it, and unless something explicitly deletes the prior vector for that id, the index now holds two vectors for one document — the stale one (the old text's embedding) and the fresh one (the new text's). Both are searchable, so a query can retrieve the stale vector and serve the document's old, outdated content; and because the old text may match the query better than the edited text does, the stale vector can outrank the fresh one and take the top slot, returning the pre-edit answer with confidence. The document also appears twice in the results, spending two slots on one source. This is a different failure from index freshness, where a new document is not yet indexed and so is invisible; here the new content is indexed correctly, but the old content was never removed, so the stale copy lingers and competes. The fix is upsert-by-id: delete any existing vector for the id, then insert the new one, so the index holds exactly one vector per document. On a fixture where d1 was edited and its old embedding matches the query slightly better than its new one, the append index keeps both d1 vectors and returns the stale one at the top (cosine 0.9138 vs 0.8000), while the upsert index keeps only the new d1 vector and returns the fresh content.
eli5: Imagine a library catalog where each book has one card. You revise a book, so you type a new card describing the new edition — but you forget to pull the old card. Now there are two cards for one book, and when someone searches, they might pull the old card and check out the outdated edition, never knowing a revised copy exists. Worse, if the old card's wording happens to match their search better, it comes up first, so the outdated edition is exactly what they get. The fix is to replace the card, not add a second one: pull the old, file the new, so there is always exactly one card per book and it always describes the current edition.
---

## Why this module

Documents change. A wiki page is edited, a product description is updated, a policy is revised — and a retrieval system built on those documents has to keep up. Keeping up has two halves that are easy to conflate: getting the new content in, and getting the old content out. A neighboring module covers the first half — a document not yet indexed is invisible. This module is about the second half, which is quieter and more dangerous because the system looks like it is working.

The mechanism is that a vector index stores entries keyed by an id, and an update to a document is supposed to replace that document's entry. The write path computes the new embedding from the new text and inserts it. If nothing explicitly removes the previous embedding for that id, the insert is an append, not a replace, and the index ends up with two vectors carrying the same document id: one from before the edit, one from after.

Both vectors are live in the search. So a query can match and return the stale vector, and the retriever hands back the document's old content as if it were current. There is no error and no empty result — just a fluent, confident answer built on text that was edited away. And it is not a rare corner: any document that was ever updated is a candidate, and every update without a delete adds another stale copy.

<svg role="img" aria-label="Two failure modes side by side. Freshness: a new document sits outside the index, missing, a false negative. Staleness: an old superseded document sits inside the index alongside its replacement, a false positive." viewBox="0 0 440 130">
<text x="110" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">freshness (other module)</text>
<rect x="40" y="30" width="140" height="70" fill="none" stroke="var(--line)"/>
<text x="110" y="26" fill="var(--muted)" font-size="7" text-anchor="middle">index</text>
<rect x="55" y="42" width="110" height="16" fill="var(--panel)" stroke="var(--line)"/>
<text x="110" y="54" fill="var(--ink)" font-size="8" text-anchor="middle">old docs</text>
<rect x="55" y="106" width="110" height="16" fill="var(--panel)" stroke="var(--s2)" stroke-dasharray="3 2"/>
<text x="110" y="118" fill="var(--s2)" font-size="7" text-anchor="middle">new doc — outside (missing)</text>
<text x="330" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">staleness (this module)</text>
<rect x="260" y="30" width="140" height="70" fill="none" stroke="var(--line)"/>
<text x="330" y="26" fill="var(--muted)" font-size="7" text-anchor="middle">index</text>
<rect x="275" y="42" width="110" height="16" fill="var(--panel)" stroke="var(--s2)"/>
<text x="330" y="54" fill="var(--s2)" font-size="7" text-anchor="middle">old version — still inside</text>
<rect x="275" y="62" width="110" height="16" fill="var(--panel)" stroke="var(--s1)"/>
<text x="330" y="74" fill="var(--s1)" font-size="7" text-anchor="middle">new version</text>
</svg>
^ Two opposite failures: freshness leaves the new content outside the index (a false negative); staleness leaves the old content inside it (a false positive) — different fixes.

**A vector index update that appends the new embedding without deleting the old one leaves two vectors for one document, and the stale one stays searchable — so a query can retrieve and serve the document's pre-edit content.**

## Concepts

The right mental model is that the index is a key-value store where the key is the document id and the value should be its current vector. An update is therefore a replace at that key. Databases have a name for "insert if absent, replace if present" — an upsert — and that is exactly the operation a document update needs against the index. Append is the wrong primitive; it is insert-always, which duplicates the key.

<svg role="img" aria-label="Two index states after editing document d1. The append index has two rows for d1, one labeled stale and one fresh, plus d2 and d3. The upsert index has one row for d1 labeled fresh, plus d2 and d3." viewBox="0 0 440 150">
<text x="110" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">append: two d1 vectors</text>
<rect x="40" y="26" width="140" height="18" fill="var(--panel)" stroke="var(--s2)"/>
<text x="110" y="39" fill="var(--s2)" font-size="8" text-anchor="middle">d1 (stale)</text>
<rect x="40" y="46" width="140" height="18" fill="var(--panel)" stroke="var(--s1)"/>
<text x="110" y="59" fill="var(--s1)" font-size="8" text-anchor="middle">d1 (fresh)</text>
<rect x="40" y="66" width="140" height="18" fill="var(--panel)" stroke="var(--line)"/>
<text x="110" y="79" fill="var(--ink)" font-size="8" text-anchor="middle">d2</text>
<rect x="40" y="86" width="140" height="18" fill="var(--panel)" stroke="var(--line)"/>
<text x="110" y="99" fill="var(--ink)" font-size="8" text-anchor="middle">d3</text>
<text x="330" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">upsert: one d1 vector</text>
<rect x="260" y="26" width="140" height="18" fill="var(--panel)" stroke="var(--s1)"/>
<text x="330" y="39" fill="var(--s1)" font-size="8" text-anchor="middle">d1 (fresh)</text>
<rect x="260" y="46" width="140" height="18" fill="var(--panel)" stroke="var(--line)"/>
<text x="330" y="59" fill="var(--ink)" font-size="8" text-anchor="middle">d2</text>
<rect x="260" y="66" width="140" height="18" fill="var(--panel)" stroke="var(--line)"/>
<text x="330" y="79" fill="var(--ink)" font-size="8" text-anchor="middle">d3</text>
</svg>
^ After editing d1, the append index carries a stale and a fresh d1; upsert deletes the old vector first, so exactly one d1 — the current one — remains.

Why the stale copy is not merely harmless clutter is the crux. If the two copies always ranked below the fresh one, you would only waste a slot. But the old and new text differ, so they match a given query differently, and there is no rule that the newer text matches better. An edit that generalizes a page, fixes a typo that happened to be a keyword, or shifts the topic can make the old embedding closer to a query than the new one — and then the stale vector outranks the fresh vector and takes the top slot. The system serves the exact content that was edited away.

This is distinct from the freshness problem, and it helps to hold the two apart. Freshness is a false negative: the right, new content is missing from the index. Stale duplicates are a false positive: wrong, old content is present in the index and competing. A system can have both, and they need different fixes — freshness needs timely indexing of new writes, staleness needs deletion of superseded vectors. Upsert-by-id is the operation that guarantees the second: one vector per id, always the current one.

**An update is a replace at the document's id — an upsert — not an append; the stale vector is not harmless clutter because the old text can match a query better than the edited text, so it can win the top slot and serve superseded content.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/upsert-inter-01. The fixture is a query, the edited document's id, its old and new embeddings, and a couple of other documents.

```json filename=modules/context-and-retrieval/code/upsert-inter-01/upsert.json:3-6 COMPLETE
  "query": [1, 0, 0],
  "updated_doc": "d1",
  "old_vector": [0.9, 0.4, 0],
  "new_vector": [0.8, 0.0, 0.6],
```

Retrieval ranks by cosine similarity to the query.

```python filename=modules/context-and-retrieval/code/upsert-inter-01/upsert.py:31-36 COMPLETE
def cosine(a, b):
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)
```

The append index is what a naive update produces: the old d1 vector is still present, and the new one was added next to it.

```python filename=modules/context-and-retrieval/code/upsert-inter-01/upsert.py:39-45 COMPLETE
def append_index(data):
    """The naive update: the old d1 vector is still here, and the new one was appended -- two entries for d1."""
    entries = [(data["updated_doc"], "stale", data["old_vector"]),
               (data["updated_doc"], "fresh", data["new_vector"])]
    for cid, vec in data["other_docs"].items():
        entries.append((cid, "-", vec))
    return entries
```

The upsert index deletes the old d1 vector first, then writes the new one — one entry for d1.

```python filename=modules/context-and-retrieval/code/upsert-inter-01/upsert.py:48-53 COMPLETE
def upsert_index(data):
    """The correct update: delete d1's old vector, then write the new one -- one entry for d1."""
    entries = [(data["updated_doc"], "fresh", data["new_vector"])]
    for cid, vec in data["other_docs"].items():
        entries.append((cid, "-", vec))
    return entries
```

Before running it, predict: d1's old vector [0.9, 0.4, 0] points more toward the query [1, 0, 0] than its new vector [0.8, 0, 0.6], so in the append index the stale copy should outrank the fresh one. Run `--index` then `--search`:

```text filename=upsert.py --index
INDEX — entries for the edited document d1 after the update
--------------------------------------------------------
  append index : [('d1', 'stale'), ('d1', 'fresh'), ('d2', '-'), ('d3', '-')]
  upsert index : [('d1', 'fresh'), ('d2', '-'), ('d3', '-')]
--------------------------------------------------------
  append leaves two d1 vectors (stale + fresh); upsert leaves one
```

```text filename=upsert.py --search
SEARCH — ranked results for the query
--------------------------------------------------------
  append index:
      d1   stale  cos 0.9138
      d1   fresh  cos 0.8000
      d2   -      cos 0.7071
      d3   -      cos 0.7071
  append top-1 = d1 (stale)  ->  returns the stale content
  upsert index:
      d1   fresh  cos 0.8000
      d2   -      cos 0.7071
      d3   -      cos 0.7071
  upsert top-1 = d1 (fresh)  ->  returns the fresh content
--------------------------------------------------------
  the append index serves the pre-edit content; the upsert index serves the current content
```

The prediction holds and the consequence is stark. In the append index, the stale d1 vector scores 0.9138 and the fresh one 0.8000, so the top result is the pre-edit content — the retriever confidently returns text that was edited away, and d1 also occupies the first two slots as a duplicate. In the upsert index, the stale vector is gone, so the top result is the fresh d1 content at 0.8000, and d1 appears once. The corpus, the query, and the embedding model are identical; the only difference is whether the update deleted the old vector.

<svg role="img" aria-label="Two ranked lists for the same query. The append list has d1 stale at the top with cosine 0.91, then d1 fresh 0.80, then d2 and d3 at 0.71. The upsert list has d1 fresh at the top at 0.80, then d2 and d3. The stale top result is marked as outdated content." viewBox="0 0 440 150">
<text x="20" y="16" fill="var(--muted)" font-size="9">append: top result is the stale copy</text>
<rect x="20" y="24" width="180" height="16" fill="var(--s2)"/>
<text x="110" y="36" fill="var(--s2)" font-size="8" text-anchor="middle">d1 stale  0.91  (outdated)</text>
<rect x="20" y="42" width="160" height="16" fill="var(--panel)" stroke="var(--s1)"/>
<text x="100" y="54" fill="var(--s1)" font-size="8" text-anchor="middle">d1 fresh  0.80</text>
<rect x="20" y="60" width="141" height="16" fill="var(--panel)" stroke="var(--line)"/>
<text x="90" y="72" fill="var(--ink)" font-size="8" text-anchor="middle">d2 / d3  0.71</text>
<text x="240" y="16" fill="var(--muted)" font-size="9">upsert: top result is current</text>
<rect x="240" y="24" width="160" height="16" fill="var(--s1)"/>
<text x="320" y="36" fill="var(--s1)" font-size="8" text-anchor="middle">d1 fresh  0.80  (current)</text>
<rect x="240" y="42" width="141" height="16" fill="var(--panel)" stroke="var(--line)"/>
<text x="310" y="54" fill="var(--ink)" font-size="8" text-anchor="middle">d2 / d3  0.71</text>
</svg>
^ The append index puts the stale copy first and serves outdated content; the upsert index has no stale copy, so the current content is the top result.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that the append index holds two vectors for d1, that the upsert index holds exactly one, that the stale vector outscores the fresh one for this query, that the append search returns the stale content at the top, and that the upsert search returns the fresh content.

```python filename=modules/context-and-retrieval/code/upsert-inter-01/upsert.py:101-115 COMPLETE
    append_duplicates_doc = sum(1 for cid, _, _ in ai if cid == doc) == 2
    print("  the append index holds two vectors for %s = %s" % (doc, append_duplicates_doc))

    upsert_single_entry = sum(1 for cid, _, _ in ui if cid == doc) == 1
    print("  the upsert index holds exactly one vector for %s = %s" % (doc, upsert_single_entry))

    stale_outranks_fresh = cosine(q, data["old_vector"]) > cosine(q, data["new_vector"])
    print("  the stale vector outscores the fresh one for this query = %s (%.4f > %.4f)"
          % (stale_outranks_fresh, cosine(q, data["old_vector"]), cosine(q, data["new_vector"])))

    append_returns_stale = at[0][0] == doc and at[0][1] == "stale"
    print("  the append search returns the stale content at the top = %s (%s %s)" % (append_returns_stale, at[0][0], at[0][1]))

    upsert_returns_fresh = ut[0][0] == doc and ut[0][1] == "fresh"
    print("  the upsert search returns the fresh content at the top = %s (%s %s)" % (upsert_returns_fresh, ut[0][0], ut[0][1]))
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the append index ever stopped duplicating d1 or the stale copy ever stopped winning:

```text filename=upsert.py --check
SELF-TEST — the append index duplicates the doc and returns its stale content; the upsert index holds one and returns the fresh content
----------------------------------------------------------------------------------------------------------------
  the append index holds two vectors for d1 = True
  the upsert index holds exactly one vector for d1 = True
  the stale vector outscores the fresh one for this query = True (0.9138 > 0.8000)
  the append search returns the stale content at the top = True (d1 stale)
  the upsert search returns the fresh content at the top = True (d1 fresh)
```

**The self-test asserts the stale vector actually outscores the fresh one, not merely that a duplicate exists — so a pass certifies the strong failure (the retriever serves the pre-edit content at the top), not just the harmless case where the duplicate ranks below and only wastes a slot.**

## Definition of done

You can explain why a vector index update should be a replace at the document id, not an append.
You can explain how appending a new embedding without deleting the old one leaves two vectors for one document.
You can explain why a stale duplicate is not harmless — how the old text can outrank the edited text for some queries.
You can distinguish this false-positive failure (old content present) from the freshness false-negative (new content absent).
You can describe upsert-by-id as the operation that keeps exactly one current vector per document.

## Boss fight

Suppose deletes are the fix, but you also chunk each document into several vectors before indexing. Reason about what upsert must delete now. A single document maps to many index entries — one per chunk — so upserting it is not "delete one vector, write one"; it is "delete every chunk vector that belongs to this document id, then write the new chunks." And the new version may have a different number of chunks than the old (the edit made the document longer or shorter), so a naive "overwrite chunk 0, chunk 1, ..." leaves orphaned tail chunks from the longer old version. The robust pattern is delete-by-document-id followed by insert-all-new-chunks, which requires the index to support deletion filtered by a document-id field on each chunk — a schema decision you must make before you have an update problem, not after. The lesson: upsert is per-document, but the index stores per-chunk, so the delete must be keyed on the document, and the chunk count must not be assumed stable across edits.

Now the trap that makes stale vectors survive even a correct delete: eventual consistency and tombstones. Many vector stores do not remove a deleted vector immediately; they mark it with a tombstone and reclaim the space during a later compaction, and some approximate indexes can still return a tombstoned vector until that compaction runs. So a delete that "succeeded" may not have taken effect for search yet, and a read-back can still surface the stale copy — the same visible symptom as forgetting to delete. The defense is to treat deletion as asynchronous where the store documents it so, filter results by a validity flag or version if the store supports it, and verify (not assume) that a delete is reflected in search before trusting freshness. The rule generalizes: one vector per document is the goal, but achieving it depends on the store's delete semantics, which you must know rather than assume.

**With chunked documents, upsert means delete-all-chunks-by-document-id then insert the new chunks (the chunk count can change, orphaning tail chunks otherwise); and because some stores delete via tombstones with delayed compaction, a "successful" delete may not be reflected in search yet, so verify deletion rather than assume it.**

## External resources

The documentation for vector databases (Pinecone, Weaviate, Qdrant, Milvus, pgvector) describes upsert semantics, delete-by-id and delete-by-filter, and — importantly — each store's consistency and tombstone/compaction behavior.
Guides on production RAG data pipelines cover change-data-capture and reconciliation: keeping the index in sync with a source of truth by deleting superseded vectors, not only inserting new ones.
The topic's own module on index freshness covers the complementary failure — a new document not yet indexed — which this one is carefully distinguished from: freshness is missing new content, staleness is lingering old content.
