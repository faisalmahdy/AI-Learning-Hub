---
id: retrieval-inter-13
title: Prepend each chunk's document context before embedding — a chunk that lost its subject won't match the query
topic: context-and-retrieval
level: intermediate
status: ready
time: 21 min
summary: A chunk torn from its document loses the words that named its subject, so a query naming that subject barely matches it — and an off-topic chunk that happens to mention the subject outscores it. Prepending a short context blurb (title, subject, date) to each chunk before embedding restores those terms. Bare, the answer chunk scores 0.218 and loses to a wrong chunk at 0.436; augmented, it wins at 0.500.
eli5: If you tear one page out of a book, it might say "he then doubled the budget" without ever saying who "he" is — that page was counting on the rest of the book. Someone searching for that person won't find the page. Writing a one-line note at the top of each torn page ("From the chapter about Acme's CEO") makes it findable again.
---

## Why this module

Chunking a document for retrieval quietly strips each chunk of the context that told you what it was about, and that missing context is exactly what queries search on.

To retrieve from long documents you split them into chunks small enough to embed and rank. But a document is coherent: it names its subject once and then refers back to it — "the company," "he," "that quarter," or just by continuing the topic. When you cut it into chunks, a chunk in the middle inherits none of that. A chunk that reads "revenue rose 20 percent in the quarter" is perfectly clear inside its document, which was about Acme's 2023 results, but on its own it never says Acme and never says 2023. Those words were in the title and the opening paragraph, left behind when the chunk was cut out.

Now a user searches "Acme 2023 revenue." The chunk that actually answers it does not contain "Acme" or "2023," so it matches the query weakly. Meanwhile some other chunk — "Acme opened a new office in 2023" — contains both "Acme" and "2023" and matches strongly, even though it is about real estate, not revenue. Retrieval returns the wrong chunk, not because the embedding is bad but because the right chunk was stripped of the terms that would have connected it to the query. The answer is in your corpus; the retriever cannot recognize it.

Contextual augmentation fixes this at index time. Before embedding each chunk, prepend a short blurb describing where it came from — the document title, the subject, the date — so the chunk carries the entity and time terms it was relying on the document for. The blurb is added to every chunk, so the comparison stays fair; it just gives each chunk back the context it lost. Now the revenue chunk carries "Acme" and "2023," matches the query, and rises above the off-topic chunk.

We will retrieve one query against two chunks. Bare, the answer chunk scores 0.218 and loses to the off-topic chunk at 0.436 — wrong answer. Augment every chunk with its document context and the answer chunk rises to 0.500, above the off-topic chunk's 0.480 — the retrieval flips to correct. Same chunks; the difference is whether they carry their context.

**Chunking strips each chunk of the words that named its subject, so a query on that subject misses the right chunk and matches an off-topic one that happens to mention it; prepending a context blurb restores those terms and fixes the match.**

## Concepts

The failure is a vocabulary mismatch created by chunking. Retrieval matches a query to a chunk on shared meaning, and for a chunk to match a query about an entity, the chunk has to carry some signal of that entity. Inside a document, chunks share the entity implicitly through the document's coherence — the reader carries "Acme" forward from the title. But the retriever does not read the document; it embeds each chunk in isolation, and an isolated chunk has only its own words. If those words omit the entity, the chunk is, to the retriever, not about that entity, no matter how clearly the document was.

This is why the off-topic chunk wins bare. Term-matching and dense embeddings alike score on the content actually present, and the off-topic chunk literally contains the query's rare, high-signal terms (the entity, the year) while the answer chunk contains only the common ones (revenue). Rare terms carry the most retrieval weight, so a chunk that has the rare query terms for the wrong reason beats a chunk that has the right meaning but lacks the terms. Chunking manufactured a situation where surface term overlap and true relevance point at different chunks.

<svg role="img" aria-label="At index time, a context blurb is prepended to each chunk before embedding, so the embedded text carries the document's subject and date" viewBox="0 0 460 130" width="460" height="130">
  <rect x="0" y="0" width="460" height="130" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">index-time augmentation (before embedding)</text>
  <rect x="20" y="45" width="150" height="34" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="30" y="60" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">context blurb</text><text x="30" y="72" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">"acme corp 2023 …"</text>
  <text x="176" y="66" font-family="var(--mono)" font-size="12" fill="var(--ink)">+</text>
  <rect x="192" y="45" width="150" height="34" fill="var(--panel)" stroke="var(--line)"/><text x="202" y="60" font-family="var(--mono)" font-size="8" fill="var(--ink)">bare chunk</text><text x="202" y="72" font-family="var(--mono)" font-size="8" fill="var(--ink)">"revenue rose 20% …"</text>
  <line x1="342" y1="62" x2="372" y2="62" stroke="var(--ink)"/>
  <rect x="372" y="45" width="70" height="34" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="382" y="66" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">embed</text>
  <text x="20" y="104" font-family="var(--mono)" font-size="8" fill="var(--muted)">the embedded vector now carries the entity + year the bare chunk had lost</text>
</svg>
^ Each chunk is embedded with its source context prepended, so its vector reflects both its own content and the document identity it would otherwise have left behind.

Contextual augmentation repairs the chunk's content so its surface matches its true topic. The prepended blurb adds the entity, subject, and date — the high-signal terms the document supplied and the chunk lost — so the answer chunk now overlaps the query on exactly the terms that were missing. Crucially it is applied to every chunk, so it does not cheat: the off-topic chunk also gets its context, but its context ("newsroom press release") does not add revenue-relevance, so it gains little, while the answer chunk gains the terms the query actually needs. The augmentation helps each chunk in proportion to how much context it was missing on the query's terms.

The production form of this is Anthropic's Contextual Retrieval and related techniques: at index time, generate a short chunk-specific context (often with a model, summarizing what the chunk is about within its document) and prepend it before embedding, which measurably cuts retrieval failures. The mechanism is the one shown here — give the chunk back the identifying context it lost when it was cut out — and it stacks with the other retrieval tools (hybrid search, reranking) rather than replacing them. The core lesson is that a chunk's embedding is only as good as the words in the chunk, and chunking removes words the chunk needs.

**A chunk's embedding sees only its own words, so chunking that strips the entity makes surface overlap and true relevance diverge; augmenting with the document context restores the identifying terms, helping each chunk by what it was missing.**

## Worked example

The fixture is a query and two chunks, each with its bare text and its document context.

```json filename=modules/context-and-retrieval/code/retrieval-inter-13/chunks.json:7-13 COMPLETE
  "query": "acme 2023 revenue",
  "chunks": {
    "right": {
      "bare": "revenue rose 20 percent in the quarter",
      "context": "acme corp 2023 annual report",
      "answer": true
    },
```

The query is "acme 2023 revenue." The answer chunk's bare text is about revenue but never says acme or 2023; its context — the document it came from — does.

```text filename=modules/context-and-retrieval/code/retrieval-inter-13/context.py --chunks
CHUNKS — query: 'acme 2023 revenue'
----------------------------------------------------------
  right (the true answer)
    bare:    revenue rose 20 percent in the quarter
    context: acme corp 2023 annual report
  wrong
    bare:    acme opened a new office in 2023
    context: acme newsroom press release
```

The answer chunk (right) is about revenue; the wrong chunk is about an office opening but happens to contain "acme" and "2023." Similarity is bag-of-words cosine, a visible stand-in for an embedding.

```python filename=modules/context-and-retrieval/code/retrieval-inter-13/context.py:42-46 COMPLETE
def vec(text):
    """Bag-of-words term vector -- a stand-in for an embedding, so the matching is visible."""
    d = {}
    for w in text.lower().split():
        d[w] = d.get(w, 0) + 1
```

Bare similarity uses the chunk's own text; augmented similarity prepends the context.

```python filename=modules/context-and-retrieval/code/retrieval-inter-13/context.py:58-60 COMPLETE
def bare_sim(query, chunk):
    """Similarity of the query to the chunk's bare text alone."""
    return cosine(vec(query), vec(chunk["bare"]))
```

```python filename=modules/context-and-retrieval/code/retrieval-inter-13/context.py:63-65 COMPLETE
def augmented_sim(query, chunk):
    """Similarity of the query to the chunk with its document context prepended."""
    return cosine(vec(query), vec(chunk["context"] + " " + chunk["bare"]))
```

Predict: bare, the answer chunk shares only "revenue" with the query (low), while the wrong chunk shares "acme" and "2023" (higher), so bare retrieval picks the wrong chunk. Augmented, the answer chunk gains "acme" and "2023" from its context and should overtake. Run it.

```text filename=modules/context-and-retrieval/code/retrieval-inter-13/context.py --retrieve
RETRIEVE — similarity to the query, bare vs context-augmented
----------------------------------------------------------
  chunk    bare     augmented
  right    0.218    0.500
  wrong    0.436    0.480
----------------------------------------------------------
  bare top: wrong   augmented top: right   (answer: right)
```

Bare, the wrong chunk wins 0.436 to 0.218 — retrieval returns the office-opening chunk for a revenue query, because it has the entity and year terms and the answer chunk does not. Augmented, the answer chunk jumps to 0.500 (it now carries "acme" and "2023" from its context) and edges out the wrong chunk at 0.480, so retrieval returns the correct chunk. The augmentation more than doubled the answer chunk's score while barely moving the wrong chunk's, because the answer chunk was the one missing the query's terms. The flip from wrong to right is entirely due to giving each chunk back its context.

<svg role="img" aria-label="Similarity bare vs augmented: the right chunk rises from 0.22 to 0.50, the wrong chunk stays near 0.44 to 0.48, so the winner flips from wrong to right" viewBox="0 0 460 180" width="460" height="180">
  <rect x="0" y="0" width="460" height="180" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">similarity to query (bare → augmented)</text>
  <text x="90" y="40" font-family="var(--mono)" font-size="9" fill="var(--muted)">bare</text><text x="300" y="40" font-family="var(--mono)" font-size="9" fill="var(--muted)">augmented</text>
  <line x1="40" y1="150" x2="440" y2="150" stroke="var(--line)"/>
  <rect x="60" y="106" width="50" height="44" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="66" y="100" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">right .22</text>
  <rect x="120" y="63" width="50" height="87" fill="var(--s2)" stroke="var(--line)"/><text x="126" y="57" font-family="var(--mono)" font-size="8" fill="var(--s2)">wrong .44</text>
  <text x="90" y="168" font-family="var(--mono)" font-size="8" fill="var(--s2)">wrong wins</text>
  <rect x="270" y="50" width="50" height="100" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="276" y="44" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">right .50</text>
  <rect x="330" y="54" width="50" height="96" fill="var(--s2)" stroke="var(--line)"/><text x="336" y="48" font-family="var(--mono)" font-size="8" fill="var(--ink)">wrong .48</text>
  <text x="290" y="168" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">right wins</text>
</svg>
^ Augmentation more than doubles the answer chunk (0.22→0.50) and barely moves the off-topic one (0.44→0.48), flipping the top result from wrong to right.

<svg role="img" aria-label="Query terms acme, 2023, revenue matched against each chunk: the right bare chunk has only revenue; the wrong chunk has acme and 2023; augmenting the right chunk adds acme and 2023 so it matches all three" viewBox="0 0 460 200" width="460" height="200">
  <rect x="0" y="0" width="460" height="200" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">query terms: acme · 2023 · revenue  (● = present)</text>
  <text x="20" y="52" font-family="var(--mono)" font-size="9" fill="var(--ink)">right (bare)</text>
  <circle cx="160" cy="48" r="7" fill="var(--panel)" stroke="var(--line)"/><text x="175" y="51" font-family="var(--mono)" font-size="8" fill="var(--muted)">acme</text>
  <circle cx="240" cy="48" r="7" fill="var(--panel)" stroke="var(--line)"/><text x="255" y="51" font-family="var(--mono)" font-size="8" fill="var(--muted)">2023</text>
  <circle cx="330" cy="48" r="7" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="345" y="51" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">revenue</text>
  <text x="360" y="51" font-family="var(--mono)" font-size="8" fill="var(--s2)"> 0.22</text>
  <text x="20" y="92" font-family="var(--mono)" font-size="9" fill="var(--ink)">wrong (bare)</text>
  <circle cx="160" cy="88" r="7" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="175" y="91" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">acme</text>
  <circle cx="240" cy="88" r="7" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="255" y="91" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">2023</text>
  <circle cx="330" cy="88" r="7" fill="var(--panel)" stroke="var(--line)"/><text x="345" y="91" font-family="var(--mono)" font-size="8" fill="var(--muted)">revenue</text>
  <text x="360" y="91" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)"> 0.44 ✓bare</text>
  <text x="20" y="140" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">right (+context)</text>
  <circle cx="160" cy="136" r="7" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="175" y="139" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">acme</text>
  <circle cx="240" cy="136" r="7" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="255" y="139" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">2023</text>
  <circle cx="330" cy="136" r="7" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="345" y="139" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">revenue</text>
  <text x="360" y="139" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)"> 0.50 ✓aug</text>
  <text x="20" y="176" font-family="var(--mono)" font-size="8" fill="var(--muted)">context adds acme+2023 to the right chunk, so it matches all three and wins</text>
</svg>
^ Bare, the answer chunk matches only "revenue" and loses to the off-topic chunk that has "acme" and "2023"; its context supplies those two terms, so augmented it matches all three and wins.

## Build

Reproduce the similarities. Pure standard library, deterministic bag-of-words cosine, so 0.218, 0.436, 0.500, 0.480 come out exactly.

Run `--chunks` for the setup, `--retrieve` for the scores, `--check` for the gate. The self-test pins the flip: bare returns the wrong chunk, augmented returns the answer, augmentation lifts the answer chunk, and the context supplied the missing terms.

```python filename=modules/context-and-retrieval/code/retrieval-inter-13/context.py:109-113 COMPLETE
    bare_wrong = top(q, chunks, bare_sim) != ans
    print("  bare retrieval's top chunk is NOT the answer = %s (top %s, answer %s)"
          % (bare_wrong, top(q, chunks, bare_sim), ans))

    augmented_right = top(q, chunks, augmented_sim) == ans
    print("  augmented retrieval's top chunk IS the answer = %s (top %s)" % (augmented_right, top(q, chunks, augmented_sim)))
```

The `context_supplies_terms` check, in the gate, is what identifies the mechanism rather than just the outcome. It computes which query terms the answer chunk's bare text was missing and confirms the context blurb contains them — here "acme" and "2023." That proves the fix worked because the context restored the specific terms the chunk lacked, not by some incidental scoring shift. It ties the improvement to the actual cause: the chunk regained the identifying words chunking had stripped. Here is the full gate.

```text filename=modules/context-and-retrieval/code/retrieval-inter-13/context.py --check
SELF-TEST — bare retrieval returns the wrong chunk; augmenting with context returns the right one
------------------------------------------------------------------------------------------
  bare retrieval's top chunk is NOT the answer = True (top wrong, answer right)
  augmented retrieval's top chunk IS the answer = True (top right)
  augmentation lifts the answer chunk's score = True (0.218 -> 0.500)
  the context supplies query terms the bare chunk lacked = True (['2023', 'acme'])
------------------------------------------------------------------------------------------
SELF-TEST PASS  bare_wrong=True  augmented_right=True  augment_lifts_answer=True  context_supplies_terms=True
```

Four True flags. Bare_wrong: bare retrieval returns the off-topic chunk. Augmented_right: augmentation returns the answer. Augment_lifts_answer: the answer chunk's score more than doubled. Context_supplies_terms: the context restored exactly the query terms — acme, 2023 — the bare chunk was missing. The last flag names the cause, so the fix is explained, not just observed.

**The context-supplies-terms check names the exact terms the chunk regained, tying the retrieval flip to the mechanism — the chunk got back the identifying words chunking stripped.**

## Definition of done

You are done when you reproduce the flip and can explain why chunking caused it.

Concretely: `--retrieve` shows the wrong chunk winning bare (0.436 vs 0.218) and the answer chunk winning augmented (0.500 vs 0.480); `--check` prints PASS with four True flags. You can explain why an isolated chunk carries only its own words and loses the entity terms its document supplied, and why that makes surface overlap and true relevance diverge — an off-topic chunk with the rare query terms beats a relevant chunk without them. You can describe contextual augmentation as prepending a source blurb to every chunk before embedding, and why applying it to all chunks keeps the comparison fair. And you can connect it to production Contextual Retrieval and note it stacks with hybrid search and reranking.

The habit to carry: when chunking documents, prepend each chunk with a short context blurb (title, subject, date, or a model-generated summary) before embedding, so chunks keep the identifying terms they would otherwise lose. When retrieval returns off-topic chunks that merely mention the query's entities, suspect context-stripped chunks and augment them.

## Boss fight

The instructive failure is a RAG system that retrieves confidently wrong passages because every chunk forgot what document it was in.

A company indexes thousands of reports by splitting each into paragraph chunks and embedding them bare. Users ask entity-specific questions — "what was Acme's Q3 margin," "when did Globex acquire Initech" — and the system keeps returning paragraphs from the wrong company, because the paragraph with the actual answer never repeats the company name (the report's title did), while some paragraph from another report that happens to name the queried company scores higher. The answers are plausible and wrong, and the team blames the embedding model. The fix is not a better embedder; it is prepending each chunk with its report's title and date before indexing, so the answer paragraphs carry the entity they were relying on their document for. After re-indexing with context, the entity-specific queries resolve correctly.

Your turn, two moves. First, confirm the augmentation must be fair. Augment only the answer chunk (not the wrong one) and note that while it still flips correctly here, augmenting only some chunks biases the comparison — the honest and standard practice is to augment every chunk, so the improvement comes from restored context, not from selectively boosting the answer. Verify the flip still holds when both are augmented, which is the real test. Second, find a query the bare index gets right to see the effect is specific. Query "office 2023" instead — now the wrong chunk (about opening an office) is the true answer and its bare text already carries the terms, so bare retrieval is correct and augmentation does not hurt it. That shows contextual augmentation is not a blunt boost; it specifically rescues chunks whose relevant content lacks the query's identifying terms, and leaves already-matchable chunks alone — which is why it improves recall without trading away precision.

## External resources

Anthropic's "Introducing Contextual Retrieval" (2024) is the direct reference: it prepends a short, chunk-specific context to each chunk before embedding (and before BM25 indexing), and measures a large reduction in retrieval failures, especially on entity- and time-specific queries.

For the underlying problem, the chunking literature (for example Pinecone's and LlamaIndex's chunking guides) discusses how chunk boundaries destroy coreference and context, which is the mechanism this module isolates.

For how it combines with other tools, the contextual-retrieval write-ups show it stacking with hybrid (dense + lexical) search and a reranking pass — augmentation improves what is retrievable, hybrid and reranking improve how the retrievable set is ordered.
