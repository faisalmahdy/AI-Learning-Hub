---
id: retrieval-inter-20
title: Overlap the chunks — or an answer that straddles a boundary is split across two and retrievable from neither
topic: context-and-retrieval
level: intermediate
status: ready
time: 19 min
summary: Retrieval indexes a document by cutting it into chunks and embedding each. If the chunks abut with no overlap — chunk one ends exactly where chunk two begins — any span crossing that boundary is torn in half: its first part is the tail of one chunk, its second the head of the next, and no single chunk holds the whole thing. A query needing that span matches each half only weakly, so the information is indexed and still unretrievable, purely because the cut landed in the middle of it. Overlapping chunks fix it: slide the window by a stride smaller than its size so consecutive chunks share edges, and any span shorter than the overlap sits whole in at least one chunk. On a 12-token document chunked into size-6 pieces with the answer at tokens 5–6, no overlap gives [0–5] and [6–11] with the answer in neither, while a stride of 3 gives [0–5], [3–8], [6–11] with the answer whole inside [3–8].
eli5: If you cut a long comic strip into panels and one joke's setup ends a panel while its punchline starts the next, neither panel is funny on its own. If instead each panel overlaps a little with the one before, some panel will always contain the whole joke. Overlapping the cuts means no sentence gets sliced right down the middle and lost.
---

## Why this module

A chunk boundary is an invisible cut through the document, and anything the cut passes through is destroyed for retrieval even though every token is still indexed.

Chunking splits a document into pieces and embeds each piece so a query can match it. When the pieces do not overlap — the first ends exactly where the second begins — the boundary between them is a hard cut. A sentence, a fact, a definition that happens to span that cut is split: its opening words are the last thing in one chunk, its closing words the first thing in the next. No chunk contains the whole statement. A query that needs the whole statement embeds close to neither fragment, because each chunk holds only half the meaning. The answer is in the corpus, correctly indexed, and unreachable — not because it is missing, but because the knife came down through the middle of it.

**A non-overlapping cut through an answer span leaves every chunk holding only a fragment, so the whole answer matches nothing.**

Overlapping chunks remove the hard cut. Slide the chunk window forward by a stride smaller than its size, so consecutive chunks share their edges; then any span shorter than the shared region sits intact inside at least one chunk — the one whose window straddles the same place the cut used to be. This module chunks a document with and without overlap and shows the straddling answer survive only with overlap.

## Concepts

A **chunk** is a window over the document, here a range of token positions. The **stride** is how far the window moves between chunks. When stride equals the chunk size, chunks abut with no overlap; when stride is smaller, consecutive chunks **overlap** by size − stride tokens.

An **answer span** is the contiguous run of tokens that actually answers a query. To be retrievable it must sit *whole* inside some chunk — a chunk holding only part of it embeds far from a query about the whole.

A **boundary** is where one non-overlapping chunk ends and the next begins. A span **straddles** a boundary when it starts before the boundary and ends after it, so no single abutting chunk can contain it.

The **overlap guarantee** is precise: if the overlap (size − stride) is at least span_len − 1, then no span of that length can fall through a crack, because some window will always cover it. The overlap is a safety margin sized to the longest answer you need to keep intact.

The cost is **redundancy**. Overlapping chunks repeat their shared tokens, so you produce more chunks and index more text for the same document. That is the price of never splitting an answer, and the overlap size is the dial that trades redundancy against safety.

**Overlap turns the hard boundary into a shared region, so a span up to the overlap length is guaranteed whole in some chunk — at the cost of indexing the shared tokens twice.**

Sliding the window by less than its width leaves a shared strip between neighbors, and that strip is exactly where a straddling answer is caught.

<svg role="img" aria-label="Two windows offset by a stride smaller than their size, overlapping in a shared strip that spans the former boundary" viewBox="0 0 300 100" width="300" height="100">
  <rect x="20" y="30" width="140" height="16" fill="none" stroke="var(--s2)" stroke-width="1"/><text x="70" y="42" fill="var(--muted)" font-size="7">chunk A</text>
  <rect x="90" y="52" width="140" height="16" fill="none" stroke="var(--s2)" stroke-width="1"/><text x="150" y="64" fill="var(--muted)" font-size="7">chunk B (stride &lt; size)</text>
  <rect x="90" y="30" width="70" height="38" fill="var(--s2)" opacity="0.25"/>
  <text x="95" y="84" fill="var(--s2)" font-size="7">shared overlap strip</text>
  <line x1="125" y1="24" x2="125" y2="74" stroke="var(--s1)" stroke-width="1.5" stroke-dasharray="2 2"/>
  <text x="128" y="22" fill="var(--s1)" font-size="7">old boundary, now inside the strip</text>
</svg>
^ Because chunk B starts before chunk A ends, they share a strip, and any answer that would have been cut at the old boundary now lives whole inside that shared strip.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/context-and-retrieval/code/retrieval-inter-20/overlap.py

The fixture is a 12-token document, a chunk size of 6, an answer at tokens 5–6, and two strides.

```json filename=modules/context-and-retrieval/code/retrieval-inter-20/doc.json:1-9 COMPLETE
{
  "_meta": "A document of doc_len tokens (positions 0..doc_len-1) chunked into pieces of chunk_size tokens. answer_start and answer_len mark the span that actually answers a query -- it must appear WHOLE inside some chunk to be retrievable. non_overlap_stride equals chunk_size (chunks abut, no overlap); overlap_stride is smaller, so consecutive chunks overlap by chunk_size-overlap_stride tokens. The question: does the answer span survive whole in some chunk under each chunking?",
  "doc_len": 12,
  "chunk_size": 6,
  "answer_start": 5,
  "answer_len": 2,
  "non_overlap_stride": 6,
  "overlap_stride": 3
}
```

Chunking slides a window by the stride; containment checks whether a chunk holds the whole span.

```python filename=modules/context-and-retrieval/code/retrieval-inter-20/overlap.py:40-54 COMPLETE
def chunks(doc_len, size, stride):
    """Chunk ranges (start, end half-open), sliding the window by stride; the last chunk clamps to doc_len."""
    out, start = [], 0
    while start < doc_len:
        out.append((start, min(start + size, doc_len)))
        if start + size >= doc_len:
            break
        start += stride
    return out


def contains(chunk, span_start, span_len):
    """Does this chunk hold the whole span [span_start, span_start+span_len)?"""
    s, e = chunk
    return s <= span_start and span_start + span_len <= e
```

The chunks view builds both chunkings and reports, for each, whether any chunk holds the whole answer.

```python filename=modules/context-and-retrieval/code/retrieval-inter-20/overlap.py:67-78 COMPLETE
def chunks_view(data):
    n, size, a, al = data["doc_len"], data["chunk_size"], data["answer_start"], data["answer_len"]
    print("CHUNKS — answer at tokens %d-%d (%d-token doc, size %d)" % (a, a + al - 1, n, size))
    print("-" * 60)
    for label, stride in (("no overlap", data["non_overlap_stride"]), ("overlap", data["overlap_stride"])):
        cks = chunks(n, size, stride)
        held = holding_chunks(cks, a, al)
        where = " ".join(rng(c) for c in cks)
        verdict = "answer whole in %s" % rng(held[0]) if held else "answer in NO chunk"
        print("  %-11s stride %d: %s   -> %s" % (label, stride, where, verdict))
    print("-" * 60)
    print("  overlapping the windows keeps the straddling answer whole.")
```

Run `--chunks` and see which chunking keeps the answer whole.

```text filename=--chunks
CHUNKS — answer at tokens 5-6 (12-token doc, size 6)
------------------------------------------------------------
  no overlap  stride 6: [0-5] [6-11]   -> answer in NO chunk
  overlap     stride 3: [0-5] [3-8] [6-11]   -> answer whole in [3-8]
------------------------------------------------------------
  overlapping the windows keeps the straddling answer whole.
```

With no overlap the chunks are [0–5] and [6–11]. The answer spans tokens 5 and 6 — token 5 is the last of the first chunk, token 6 the first of the second — so neither chunk contains both, and the answer is retrievable from nothing. Adding a stride-3 window inserts a chunk [3–8] that straddles the old boundary, and tokens 5 and 6 both fall inside it. The extra chunk is the safety net stretched across the cut.

<svg role="img" aria-label="No-overlap chunks [0-5] and [6-11] split the answer at tokens 5-6; an overlap chunk [3-8] contains both tokens" viewBox="0 0 300 130" width="300" height="130">
  <text x="10" y="14" fill="var(--muted)" font-size="8">tokens 0 .. 11 (answer = 5,6 shaded)</text>
  <rect x="130" y="20" width="40" height="12" fill="var(--acc-soft)"/>
  <text x="20" y="45" fill="var(--muted)" font-size="8">no overlap</text>
  <rect x="20" y="48" width="130" height="12" fill="none" stroke="var(--s1)" stroke-width="1"/><text x="70" y="57" fill="var(--muted)" font-size="7">[0-5]</text>
  <rect x="150" y="48" width="130" height="12" fill="none" stroke="var(--s1)" stroke-width="1"/><text x="200" y="57" fill="var(--muted)" font-size="7">[6-11]</text>
  <line x1="150" y1="16" x2="150" y2="64" stroke="var(--s1)" stroke-width="1.5" stroke-dasharray="2 2"/>
  <text x="120" y="76" fill="var(--s1)" font-size="7">cut splits the answer</text>
  <text x="20" y="98" fill="var(--muted)" font-size="8">overlap</text>
  <rect x="20" y="101" width="130" height="10" fill="none" stroke="var(--s2)" stroke-width="1"/>
  <rect x="85" y="101" width="130" height="10" fill="var(--s2)" opacity="0.35" stroke="var(--s2)"/><text x="120" y="109" fill="var(--ink)" font-size="7">[3-8] holds 5,6</text>
  <rect x="150" y="101" width="130" height="10" fill="none" stroke="var(--s2)" stroke-width="1"/>
</svg>
^ The non-overlap boundary falls between tokens 5 and 6, splitting the shaded answer; the overlapping [3–8] window spans the same place and holds both answer tokens whole.

## Build

The `--span` view gives the rule behind it.

```text filename=--span
SPAN — why the answer is torn, and the overlap that saves it
------------------------------------------------------------
  answer tokens 5..6 ; a no-overlap boundary sits at 6, inside the span
  needed overlap to keep a length-2 span whole: at least 1 tokens
  chosen overlap = size - stride = 6 - 3 = 3
------------------------------------------------------------
  overlap >= span_len - 1 guarantees no span of that length is split.
```

The no-overlap boundary at token 6 falls strictly inside the answer, which is exactly what "straddles" means. To guarantee a length-2 span is never split, the overlap must be at least 1 — enough that some window covers any single boundary a 2-token span could cross. The fixture's overlap is 3 (size 6 minus stride 3), comfortably above the required 1, so not just this answer but any span up to 4 tokens is safe. The guarantee is a formula, not a hope: pick the overlap from the longest answer you must keep whole.

<svg role="img" aria-label="A length-2 span needs overlap at least 1; the chosen overlap of 3 covers spans up to length 4" viewBox="0 0 300 100" width="300" height="100">
  <line x1="20" y1="40" x2="285" y2="40" stroke="var(--grid)" stroke-width="1"/>
  <text x="20" y="30" fill="var(--muted)" font-size="8">overlap (tokens) →</text>
  <line x1="70" y1="34" x2="70" y2="46" stroke="var(--s1)" stroke-width="1.5"/><text x="55" y="60" fill="var(--s1)" font-size="7">need ≥1</text>
  <circle cx="170" cy="40" r="4" fill="var(--s2)"/><text x="150" y="60" fill="var(--s2)" font-size="7">chosen 3</text>
  <line x1="170" y1="34" x2="285" y2="34" stroke="var(--s2)" stroke-width="1.5"/>
  <text x="200" y="30" fill="var(--s2)" font-size="7">safe: spans up to length 4</text>
  <text x="20" y="82" fill="var(--muted)" font-size="8">overlap ≥ span_len − 1 is the guarantee</text>
</svg>
^ A length-2 answer needs only 1 token of overlap; the chosen 3 sits well past the threshold, protecting every span up to length 4.

## Definition of done

The self-test pins the split and the fix: the span straddles a boundary, no non-overlapping chunk holds it, an overlapping chunk does, the overlap meets the span_len − 1 guarantee, and overlapping costs more chunks.

```python filename=modules/context-and-retrieval/code/retrieval-inter-20/overlap.py:101-113 COMPLETE
    span_straddles_boundary = a < boundary < a + al
    print("  the answer span crosses a no-overlap chunk boundary = %s (boundary %d in %d..%d)" % (span_straddles_boundary, boundary, a, a + al - 1))

    no_overlap_misses = len(holding_chunks(no_cks, a, al)) == 0
    print("  no non-overlapping chunk holds the whole answer = %s (%s)" % (no_overlap_misses, " ".join(rng(c) for c in no_cks)))

    overlap_holds = len(holding_chunks(ov_cks, a, al)) >= 1
    print("  an overlapping chunk holds the whole answer = %s (in %s)" % (overlap_holds, rng(holding_chunks(ov_cks, a, al)[0])))

    overlap_meets_guarantee = (size - data["overlap_stride"]) >= (al - 1)
    print("  the overlap is at least span_len-1 = %s (%d >= %d)" % (overlap_meets_guarantee, size - data["overlap_stride"], al - 1))

    overlap_costs_more_chunks = len(ov_cks) > len(no_cks)
    print("  overlapping produces more chunks (redundancy cost) = %s (%d vs %d)" % (overlap_costs_more_chunks, len(ov_cks), len(no_cks)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — no overlap splits the straddling answer; overlap keeps it whole in one chunk
----------------------------------------------------------------------------------------------------
  the answer span crosses a no-overlap chunk boundary = True (boundary 6 in 5..6)
  no non-overlapping chunk holds the whole answer = True ([0-5] [6-11])
  an overlapping chunk holds the whole answer = True (in [3-8])
  the overlap is at least span_len-1 = True (3 >= 1)
  overlapping produces more chunks (redundancy cost) = True (3 vs 2)
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  span_straddles_boundary=True  no_overlap_misses=True  overlap_holds=True  overlap_meets_guarantee=True  overlap_costs_more_chunks=True
```

**Done means the fix is proven by containment, not asserted: the answer is in zero of the two non-overlapping chunks and whole inside [3–8] of the three overlapping ones, with the overlap clearing the span_len − 1 threshold.**

## Boss fight

More overlap keeps more answers whole. Predict whether cranking the overlap toward the chunk size is therefore the safe default. It is tempting to maximize it.

It is not, because redundancy grows as you shrink the stride, and near-total overlap is near-total duplication. At stride 1 every chunk shares all but one token with its neighbor, so you index roughly size times as many chunks as a non-overlapping scheme — size times the storage, the embedding cost, and the number of near-duplicate hits a query has to rerank past. The right overlap is the smallest that keeps your longest real answer span whole: span_len − 1, not the maximum. Overlap is insurance, and over-insuring is just paying for redundancy you do not need.

The mirror-image mistake is picking the overlap without knowing your answer spans, then discovering long answers still split. If some answers are whole paragraphs, a token or two of overlap will not keep them intact, and the honest fix is not more overlap but a different chunking unit — split on semantic boundaries (sentences, sections) so cuts land between answers rather than through them, and keep a modest overlap as the safety margin. Overlap protects against unlucky cuts; choosing where to cut protects against needing luck.

```python filename=modules/context-and-retrieval/code/retrieval-inter-20/overlap.py:51-54 COMPLETE
def contains(chunk, span_start, span_len):
    """Does this chunk hold the whole span [span_start, span_start+span_len)?"""
    s, e = chunk
    return s <= span_start and span_start + span_len <= e
```

**Overlap chunks by at least span_len − 1 so no answer of that length is ever split, and no more — over-overlapping duplicates the index, and truly long answers want semantic boundaries, not just a bigger margin.**

## External resources

The LangChain and LlamaIndex text-splitter documentation — `chunk_size` and `chunk_overlap` parameters, the exact knobs this module models, with defaults and guidance.

Discussions of sentence-window and semantic chunking in RAG guides — the boss-fight alternative of cutting on natural boundaries so answers are not split, with overlap as a supplement rather than the whole defense.

The companion "chunking: cut too fine" module — chunk *size* trades context against precision, while chunk *overlap* trades redundancy against not splitting answers; the two knobs are set together.
