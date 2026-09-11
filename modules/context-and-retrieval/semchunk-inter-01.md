---
id: semchunk-inter-01
title: Cut chunks at topic boundaries, not at a fixed length — or a short topic is diluted and split across two chunks
topic: context-and-retrieval
level: intermediate
status: ready
time: 16 min
summary: A retriever indexes chunks and embeds each as one vector, roughly the average of its sentences — which is only meaningful when a chunk holds a single topic. Fixed-length chunking cannot guarantee that: documents change subject at moments unrelated to your chunk size, so a fixed cut lands mid-topic and a chunk straddles a boundary, mixing two subjects into a vector that points between them and matches neither. The damage is worst for a short topic, which a fixed grid can slice so its sentences fall into different chunks, each dominated by the surrounding topic, so no chunk represents it. Semantic chunking cuts where the document actually changes subject: walk the sentences, measure the cosine similarity between each adjacent pair, and start a new chunk wherever it drops below a threshold. On a fixture where a document runs topic A, a short topic B, then A again, fixed chunks of 4 split B across two A-heavy chunks whose centroids match a B query at only 0.32, while semantic chunking isolates B in a pure chunk whose centroid matches the query at 1.00.
eli5: To store a book so you can find any part later, you rip it into equal-length pages and file each. But topics don't end exactly every N lines, so a page often has the tail of one topic and the start of the next — and if you summarize that page in one sentence, the summary is a blurry mix. A short topic tucked between two long ones can get torn in half onto two pages, each mostly about its neighbors, so a question about the short topic finds nothing that's really about it. Better to tear the pages where the subject actually changes.
---

## Why this module

A chunk is retrieved by one vector that stands for all of it, so a chunk that spans two topics is represented by a vector that stands for neither — and where you place the cuts, not how big you make them, is what decides whether that vector means anything.

Retrieval indexes chunks, and it embeds each chunk as a single vector — in effect the average of its sentence embeddings. That average is a faithful summary only when the sentences are about the same thing. Fixed-length chunking cannot ensure that, because it cuts on a grid — every N sentences, every M tokens — and documents do not change subject on your grid. So a fixed boundary routinely falls in the middle of a topic, and a fixed chunk straddles a seam, blending two subjects into one vector that sits between them in embedding space and is a strong match for neither. The chunk is not wrong, exactly; it is unrepresentative, a blur where two clean pictures were.

**A chunk is embedded as one averaged vector, so a fixed-length cut that straddles a topic boundary produces a mixed vector that matches neither topic well — the harm is in where the boundary falls, which fixed sizing chooses blind to meaning.**

The worst case is a short topic. A two-sentence definition or a brief aside is smaller than a chunk, so a fixed grid can slice it: its first sentence lands at the end of one chunk, its second at the start of the next, and both chunks are dominated by the long topics around them. Now no chunk represents the short topic at all, and a query about it retrieves a diluted average that barely points its way. Semantic chunking fixes this by cutting where the document itself changes subject: walk the sentences in order, measure the cosine similarity between each adjacent pair, and start a new chunk wherever that similarity drops below a threshold — a drop is the document telling you the subject just changed. Every chunk comes out internally coherent, the short topic gets its own chunk, and the retriever, unchanged, finally has a vector that points at it. This module chunks a document both ways and retrieves against each.

## Concepts

**A chunk's vector is its centroid** — the average of its sentence embeddings — so a chunk's retrievability depends on its sentences pointing the same way. Mixed sentences average to a vector pointing nowhere useful.

**Fixed-size chunking** groups every N sentences regardless of meaning, so its boundaries fall wherever the counter lands, not where the subject changes.

**Semantic chunking** starts a new chunk wherever the cosine similarity between adjacent sentences drops below a threshold — cutting at the document's own topic seams.

```python filename=modules/context-and-retrieval/code/semchunk-inter-01/semchunk.py:62-72 COMPLETE
def semantic_chunks(sentences, threshold):
    """Start a new chunk wherever adjacent-sentence similarity drops below `threshold` (a topic boundary)."""
    chunks, cur = [], [0]
    for i in range(1, len(sentences)):
        if cosine(sentences[i - 1]["vec"], sentences[i]["vec"]) < threshold:
            chunks.append(cur)
            cur = [i]
        else:
            cur.append(i)
    chunks.append(cur)
    return chunks
```

<svg role="img" aria-label="A document of eight sentences AAABBAAA; the fixed grid cuts after 4, splitting the B topic, while semantic cuts at the two low-similarity drops keeping B whole" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">document: A A A B B A A A   (adjacent similarity below)</text>
  <g font-size="8" fill="var(--panel)">
  <rect x="20" y="20" width="30" height="16" fill="var(--s1)"/><text x="31" y="32">A</text><rect x="52" y="20" width="30" height="16" fill="var(--s1)"/><text x="63" y="32">A</text><rect x="84" y="20" width="30" height="16" fill="var(--s1)"/><text x="95" y="32">A</text>
  <rect x="116" y="20" width="30" height="16" fill="var(--s2)"/><text x="127" y="32">B</text><rect x="148" y="20" width="30" height="16" fill="var(--s2)"/><text x="159" y="32">B</text>
  <rect x="180" y="20" width="30" height="16" fill="var(--s1)"/><text x="191" y="32">A</text><rect x="212" y="20" width="30" height="16" fill="var(--s1)"/><text x="223" y="32">A</text><rect x="244" y="20" width="30" height="16" fill="var(--s1)"/><text x="255" y="32">A</text>
  </g>
  <g font-size="6" fill="var(--muted)"><text x="66" y="46">1.0</text><text x="98" y="46">0.0</text><text x="130" y="46">1.0</text><text x="162" y="46">0.0</text><text x="194" y="46">1.0</text></g>
  <text x="20" y="66" fill="var(--muted)" font-size="7">fixed (every 4):</text>
  <line x1="114" y1="58" x2="114" y2="74" stroke="var(--ink)" stroke-width="1.5"/><text x="118" y="72" fill="var(--s2)" font-size="7">cuts through B ✗</text>
  <text x="20" y="92" fill="var(--muted)" font-size="7">semantic (at drops):</text>
  <line x1="114" y1="84" x2="114" y2="100" stroke="var(--s1)" stroke-width="1.5"/><line x1="178" y1="84" x2="178" y2="100" stroke="var(--s1)" stroke-width="1.5"/><text x="120" y="98" fill="var(--s1)" font-size="7">B kept whole ✓</text>
</svg>
^ Similarity is 1.0 within a topic and drops to 0.0 at the two boundaries; the fixed cut at 4 slices through the B topic, while semantic cuts at both drops and keeps B in one chunk.

**Semantic chunking cuts at the document's topic seams — where adjacent-sentence similarity drops — so every chunk is one coherent topic with a meaningful centroid, instead of a fixed grid that slices topics blind to where they begin and end.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/semchunk-inter-01/semchunk.py

The document is topic A (3 sentences), a short topic B (2 sentences), then A again (3); the config sets the fixed size, the split threshold, and a query about B.

```json filename=modules/context-and-retrieval/code/semchunk-inter-01/semchunk.json:13-15 COMPLETE
  "fixed_size": 4,
  "split_threshold": 0.5,
  "query": {"about": "B", "vec": [0.0, 1.0]}
```

Run `--chunk` to cut the document both ways and judge each chunk's purity.

```text filename=--chunk
CHUNK — fixed-size grid vs cutting at similarity drops
------------------------------------------------------------
  adjacent cosine:  ['1.00', '1.00', '0.00', '1.00', '0.00', '1.00', '1.00']

  fixed     chunks:
    idx [0, 1, 2, 3] topics AAAB         MIXED
    idx [4, 5, 6, 7] topics BAAA         MIXED
  semantic  chunks:
    idx [0, 1, 2]  topics AAA          pure
    idx [3, 4]     topics BB           pure
    idx [5, 6, 7]  topics AAA          pure
```

The adjacent-cosine row is the document narrating its own structure: 1.00 within a topic, 0.00 at the two boundaries (after sentence 2 and after sentence 4). Fixed chunking of 4 ignores that and cuts after sentence 3, straight through the B topic: the first chunk is AAAB and the second is BAAA, each a MIXED blend of both topics, and B's two sentences are now in different chunks. Semantic chunking reads the two 0.00 drops and cuts exactly there, producing three pure chunks — AAA, BB, AAA — with B intact in its own. The fixed grid did not misunderstand the document; it never looked at it, and a grid that never looks will sooner or later slice a topic in half. Here it sliced the one topic small enough that the slice erases it.

<svg role="img" aria-label="Fixed chunking yields two mixed chunks AAAB and BAAA; semantic chunking yields three pure chunks AAA, BB, AAA" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">resulting chunks (color = topic makeup)</text>
  <text x="6" y="30" fill="var(--muted)" font-size="8">fixed</text>
  <rect x="60" y="20" width="100" height="14" fill="var(--s1)"/><rect x="150" y="20" width="34" height="14" fill="var(--s2)"/><text x="100" y="31" fill="var(--panel)" font-size="7">AAAB mixed</text>
  <rect x="188" y="20" width="34" height="14" fill="var(--s2)"/><rect x="212" y="20" width="66" height="14" fill="var(--s1)"/><text x="224" y="31" fill="var(--panel)" font-size="7">BAAA mixed</text>
  <text x="6" y="58" fill="var(--muted)" font-size="8">semantic</text>
  <rect x="60" y="48" width="72" height="14" fill="var(--s1)"/><text x="82" y="59" fill="var(--panel)" font-size="7">AAA</text>
  <rect x="136" y="48" width="48" height="14" fill="var(--s2)"/><text x="146" y="59" fill="var(--panel)" font-size="7">BB pure</text>
  <rect x="188" y="48" width="90" height="14" fill="var(--s1)"/><text x="222" y="59" fill="var(--panel)" font-size="7">AAA</text>
  <text x="6" y="86" fill="var(--muted)" font-size="8">fixed splits B across two A-heavy chunks; semantic gives B a chunk of its own</text>
</svg>
^ Fixed chunking produces two mixed AAAB/BAAA chunks with B's sentences separated; semantic chunking produces three pure chunks, isolating BB.

## Build

Mixed chunks are only a problem if they hurt retrieval — so query for the short topic. Run `--retrieve`.

```text filename=--retrieve
RETRIEVE — a query about topic B, best chunk cosine under each chunking
------------------------------------------------------------
  fixed chunking:    best chunk cosine = 0.32
  semantic chunking: best chunk cosine = 1.00
```

A query about B, embedded at [0, 1], matches the best available chunk at 0.32 under fixed chunking and 1.00 under semantic. The gap is the whole story. Under semantic chunking the pure BB chunk has centroid [0, 1] — it *is* the query direction — so the match is perfect. Under fixed chunking the two chunks are AAAB and BAAA, whose centroids are both [0.75, 0.25]: three parts A, one part B, a vector that leans heavily toward A because A outnumbers B three to one in each chunk. The B query's cosine with that is 0.32, weak enough to lose to any genuinely on-topic chunk elsewhere in the corpus, or to fall below a relevance floor and be dropped entirely. The retriever, the embedding model, and the query are identical in both runs; only the chunk boundaries moved, and that alone took B from unfindable to a perfect hit.

```python filename=modules/context-and-retrieval/code/semchunk-inter-01/semchunk.py:80-82 COMPLETE
def best_chunk_score(chunks, sentences, query_vec):
    """The highest cosine between the query and any chunk's centroid -- what the retriever would return."""
    return max(cosine(query_vec, centroid([sentences[i]["vec"] for i in c])) for c in chunks)
```

The mechanism is dilution by averaging. A chunk's centroid is pulled toward whichever topic contributes the most sentences, so a minority topic's direction is averaged away in proportion to how outnumbered it is — one B sentence among three A sentences yields a vector three-quarters of the way to A. Semantic chunking prevents the averaging from ever crossing a topic line: each centroid averages only sentences that already agree, so it stays a clean topic vector. This is why semantic chunking helps most exactly where fixed chunking hurts most — short or interleaved topics — and helps least on long, uniform sections where any cut lands within one topic anyway. The technique is not "smaller chunks" or "bigger chunks"; it is boundaries placed by content, so the averaging that produces each chunk vector never mixes things that should stay apart.

<svg role="img" aria-label="The B query vector points straight up; the semantic chunk centroid also points straight up (cosine 1.00) while the fixed chunk centroid leans toward A (cosine 0.32)" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">query B and each chunk's centroid, as directions</text>
  <line x1="40" y1="90" x2="140" y2="90" stroke="var(--grid)"/><line x1="40" y1="90" x2="40" y2="20" stroke="var(--grid)"/>
  <line x1="40" y1="90" x2="40" y2="24" stroke="var(--s2)" stroke-width="2"/><text x="44" y="24" fill="var(--s2)" font-size="7">query B [0,1]</text>
  <line x1="40" y1="90" x2="40" y2="30" stroke="var(--s1)" stroke-width="1.5" stroke-dasharray="3 2"/><text x="6" y="44" fill="var(--s1)" font-size="7">semantic [0,1]</text>
  <text x="30" y="20" fill="var(--s1)" font-size="7">cos 1.00 ↑</text>
  <line x1="40" y1="90" x2="122" y2="62" stroke="var(--muted)" stroke-width="1.5"/><text x="124" y="60" fill="var(--muted)" font-size="7">fixed [0.75,0.25]</text>
  <text x="150" y="80" fill="var(--muted)" font-size="7">cos 0.32 — leans toward A →</text>
  <text x="6" y="98" fill="var(--muted)" font-size="8">the fixed centroid is pulled 3/4 toward A by the outnumbering A sentences; the semantic one is pure B</text>
</svg>
^ The B query points straight up; the semantic chunk's centroid points the same way (cosine 1.00), while the fixed chunk's centroid leans three-quarters toward A (cosine 0.32) because A outnumbers B in the chunk.

## Definition of done

The self-test pins the chain: fixed chunking makes a mixed chunk, semantic chunking makes only pure chunks, the short topic is split by fixed and kept whole by semantic, and the B query retrieves better under semantic.

```python filename=modules/context-and-retrieval/code/semchunk-inter-01/semchunk.py:123-138 COMPLETE
    fixed_has_mixed = any(len(set(chunk_topics(c, s))) > 1 for c in fixed)
    print("  fixed chunking produces at least one mixed-topic chunk = %s" % fixed_has_mixed)

    semantic_all_pure = all(len(set(chunk_topics(c, s))) == 1 for c in sem)
    print("  semantic chunking produces only pure chunks = %s (%s)" % (semantic_all_pure, ["".join(chunk_topics(c, s)) for c in sem]))

    b_indices = [i for i, sent in enumerate(s) if sent["topic"] == q["about"]]
    b_split_in_fixed = len({next(k for k, c in enumerate(fixed) if i in c) for i in b_indices}) > 1
    print("  the short %s topic is split across chunks by fixed chunking = %s" % (q["about"], b_split_in_fixed))

    b_whole_in_semantic = any(set(b_indices) == set(c) for c in sem)
    print("  semantic chunking puts the whole %s topic in one chunk = %s" % (q["about"], b_whole_in_semantic))

    fx, sx = best_chunk_score(fixed, s, q["vec"]), best_chunk_score(sem, s, q["vec"])
    semantic_retrieves_better = sx > fx
    print("  the %s query matches a chunk better under semantic chunking = %s (%.2f > %.2f)" % (q["about"], semantic_retrieves_better, sx, fx))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — fixed chunking mixes topics and buries B; semantic chunking cuts at the drops and gives B a pure chunk
--------------------------------------------------------------------------------------------------------------------
  fixed chunking produces at least one mixed-topic chunk = True
  semantic chunking produces only pure chunks = True (['AAA', 'BB', 'AAA'])
  the short B topic is split across chunks by fixed chunking = True
  semantic chunking puts the whole B topic in one chunk = True
  the B query matches a chunk better under semantic chunking = True (1.00 > 0.32)
```

**Done means the boundary placement is proven to decide retrievability: fixed chunking of 4 makes two mixed AAAB/BAAA chunks that split the short B topic and match a B query at only 0.32, while semantic chunking cuts at both similarity drops to make three pure chunks — isolating B in a centroid of [0,1] that matches the B query at 1.00 — with the retriever, embeddings, and query unchanged.**

## Boss fight

Predict the two ways the similarity-drop rule misfires. It is tempting to treat the threshold as a fixed constant that works on any document.

The first trap is that the split threshold is not universal, and a wrong one destroys the method in either direction. Set it too high and every small stylistic wobble between adjacent sentences looks like a topic change, so the document shatters into single-sentence chunks — the tiny-chunk failure where an answer that spans two sentences falls between the pieces. Set it too low and only violent subject changes trigger a cut, so gently drifting topics never split and you are back to mixed chunks. The right threshold depends on the embedding model's scale and the document's style — technical prose with sharp topic shifts wants a different cutoff than a flowing narrative — so it must be calibrated, often by targeting a chunk-size distribution or using the distribution of adjacent similarities in the document itself (split at the low percentiles) rather than an absolute number. A single hardcoded 0.5 that worked on one corpus can over- or under-split the next.

```python filename=modules/context-and-retrieval/code/semchunk-inter-01/semchunk.py:43-49 COMPLETE
def cosine(u, v):
    """Cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(u, v))
    nu = math.sqrt(sum(a * a for a in u))
    nv = math.sqrt(sum(b * b for b in v))
    return dot / (nu * nv) if nu and nv else 0.0
```

The second trap is that semantic chunking has no upper bound on chunk size, and an unbounded chunk breaks the very retrieval it was meant to help. A long, coherent section — a ten-page uniform discussion — has no internal similarity drop, so the algorithm never cuts it, producing one enormous chunk that exceeds the embedding model's context window (so its tail is truncated and unindexed) and blows the retriever's token budget when injected. Pure coherence is not the only constraint; chunks must also fit downstream limits. So production semantic chunking is a constrained cut: split at the largest similarity drops, but also force a split when a chunk reaches a maximum size, and merge chunks that fall below a minimum. The clean rule "cut where the topic changes" has to be tempered by "and never let a chunk get too big or too small," which turns chunking into a small optimization over both coherence and size — the coherence keeps topics whole, the size bounds keep chunks usable. Semantic boundaries are necessary, but size limits are still required.

**Semantic chunking cuts at adjacent-similarity drops so each chunk is one coherent topic with a meaningful centroid — fixing the mixed-vector dilution that fixed grids inflict on short or interleaved topics — but the drop threshold is not universal (too high shatters into tiny chunks, too low leaves topics mixed, so calibrate it to the embeddings and document), and coherence alone bounds nothing, so cap and floor chunk sizes too, because an unbounded coherent section overflows the embedding window and the retrieval budget.**

## External resources

Writing on semantic / content-aware chunking and text segmentation (for example the TextTiling algorithm and modern embedding-based "semantic chunkers") — the methods for finding topic boundaries from adjacent-sentence similarity and for calibrating the split threshold.

Any reference on chunking strategy for retrieval that covers the size-versus-coherence trade-off and constrained chunking (min/max chunk size with semantic boundaries) — the practical recipe production systems use.

The companion "chunking: cut too fine and the answer falls between the pieces" and "overlap the chunks" modules — the first is the chunk-size half of this decision and the second is a different fix (overlapping windows) for the same straddling-boundary problem, so the three together cover where and how big to cut.
