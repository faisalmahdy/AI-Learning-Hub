---
id: chunkoverlap-inter-01
title: Overlap the chunks — a fact whose evidence straddles a boundary is sliced in half by non-overlapping chunks and lost
topic: context-and-retrieval
level: intermediate
status: ready
time: 15 min
summary: Retrieval works on chunks — split a document into pieces, embed each, fetch the most relevant for a query — and the obvious way to split is into consecutive non-overlapping windows, which tiles the document with no wasted duplication. It also puts a hard cut at every boundary, and a boundary does not care what it slices through. When the evidence a query needs spans that cut — "the dose was 5mg" in one sentence and "given twice daily" in the next, with the boundary between them — the fact is split across two chunks and neither contains the whole answer, so retrieval that fetches the single best chunk gets half the fact and the model answers from a fragment. The failure is invisible at indexing time: the chunks look fine, coverage is complete, every sentence is in exactly one chunk; the gap only appears for queries whose answer happens to straddle a boundary, which depends on where the arbitrary cuts fell, so it surfaces as sporadic, hard-to-reproduce misses on facts that are demonstrably in the corpus. The fix is to overlap adjacent chunks: step forward by less than the chunk size so each chunk repeats the last stretch of the previous one, which guarantees any fact short enough to fit in a chunk appears whole in at least one chunk, at the cost of redundancy — more chunks, the overlapped text stored and embedded twice. The overlap must be at least as large as the longest fact you need to keep intact. On a fixture where the answer spans sentences 3–4, which straddle the boundary between the non-overlapping chunks [0-3] and [4-7], no single non-overlapping chunk contains both, while with overlap 2 the chunk [2-5] contains both — at the cost of 5 chunks instead of 3.
eli5: Imagine cutting a long comic strip into pages of four panels each, with scissors, and never letting a page share panels with the next. Now suppose a joke needs the last panel of one page and the first panel of the next to make sense — you snipped right between them, so no single page has the whole joke, and someone handed just one page never gets it. The fix is to let each page overlap the one before it by a couple of panels, so the setup and the punchline always land together on at least one page. You end up with more pages and some repeated panels, but no joke ever gets cut in half.
---

## Why this module

Chunking is the unglamorous first step of every retrieval system, and it silently caps how good the system can be: retrieval can only ever return a chunk, so if the answer is not wholly inside some chunk, no retriever, reranker, or model can recover it. The default chunking — fixed-size, non-overlapping windows — is chosen because it is simple and wastes no space, and it introduces a failure that is easy to miss precisely because the index looks healthy. Every sentence is covered, every chunk is well-formed, and the problem only shows up on the specific queries whose answers happen to sit across a cut.

The cause is that the boundaries are arbitrary with respect to meaning. You split every N sentences (or tokens), and that cut lands wherever it lands — often in the middle of a fact whose two halves belong together. "The dose was 5mg" and "given twice daily" are one fact; if the boundary falls between them, one chunk has the dose and the next has the schedule, and a query asking for the full dosing instruction matches a chunk that is missing half the answer. The retriever did its job — it found the best chunk — and the best chunk is still incomplete.

Overlapping the chunks removes the guarantee that boundaries destroy facts. This module chunks the same document both ways and checks whether the answer span survives whole.

**Overlap adjacent chunks by at least the length of the facts you must keep intact, rather than splitting the document into non-overlapping windows, because a non-overlapping boundary can fall in the middle of a fact and split its evidence across two chunks so no single chunk answers the query — while overlapping windows guarantee any short-enough span appears whole in some chunk, at the cost of duplicated text.**

## Concepts

The fixture is a 12-sentence document, a chunk size of 4, and an overlap of 2. The answer the query needs spans sentences 3 and 4 — the dose and its schedule — which sit on either side of the first non-overlapping boundary.

```json filename=modules/context-and-retrieval/code/chunkoverlap-inter-01/chunkoverlap.json:3-5 COMPLETE
  "chunk_size": 4,
  "overlap": 2,
  "answer_span": [3, 4],
```

Chunking is one function parameterized by the step between chunk starts. Stepping by the full chunk size gives non-overlapping windows; stepping by less gives overlap.

```python filename=modules/context-and-retrieval/code/chunkoverlap-inter-01/chunkoverlap.py:32-42 COMPLETE
def chunk_ranges(n, chunk_size, step):
    """Chunk [start, end] index ranges tiling n items, stepping by `step` (step == chunk_size means no overlap)."""
    ranges = []
    start = 0
    while start < n:
        end = min(start + chunk_size - 1, n - 1)
        ranges.append((start, end))
        if end == n - 1:
            break
        start += step
    return ranges
```

Whether a chunk answers the query is whether it fully contains the answer span — both endpoints inside one chunk. The helper finds the first chunk that does, or reports none.

```python filename=modules/context-and-retrieval/code/chunkoverlap-inter-01/chunkoverlap.py:45-55 COMPLETE
def contains_span(rng, span):
    """Whether chunk range rng fully contains the answer span."""
    return rng[0] <= span[0] and span[1] <= rng[1]


def chunk_containing(ranges, span):
    """The first chunk range that fully contains the span, or None."""
    for r in ranges:
        if contains_span(r, span):
            return r
    return None
```

<svg role="img" aria-label="A row of 12 sentence cells; non-overlapping chunks cut between sentence 3 and 4 splitting the answer, while an overlapping chunk 2 to 5 covers both 3 and 4" viewBox="0 0 320 130">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">answer = sentences 3,4 (highlighted)</text>
  <g font-size="7" fill="var(--muted)">
  <rect x="20" y="24" width="22" height="16" fill="none" stroke="var(--line)"/><text x="28" y="35">0</text>
  <rect x="42" y="24" width="22" height="16" fill="none" stroke="var(--line)"/><text x="50" y="35">1</text>
  <rect x="64" y="24" width="22" height="16" fill="none" stroke="var(--line)"/><text x="72" y="35">2</text>
  <rect x="86" y="24" width="22" height="16" fill="var(--s1)"/><text x="94" y="35" fill="var(--panel)">3</text>
  <rect x="108" y="24" width="22" height="16" fill="var(--s1)"/><text x="116" y="35" fill="var(--panel)">4</text>
  <rect x="130" y="24" width="22" height="16" fill="none" stroke="var(--line)"/><text x="138" y="35">5</text>
  </g>
  <line x1="108" y1="20" x2="108" y2="44" stroke="var(--s2)" stroke-width="2"/>
  <text x="112" y="52" font-size="7.5" fill="var(--s2)">non-overlap boundary cuts here</text>
  <text x="10" y="76" font-size="8" fill="var(--muted)">no overlap:</text>
  <rect x="20" y="80" width="88" height="12" fill="none" stroke="var(--s2)"/><text x="55" y="89" font-size="7" fill="var(--s2)">0-3</text>
  <rect x="108" y="80" width="88" height="12" fill="none" stroke="var(--s2)"/><text x="143" y="89" font-size="7" fill="var(--s2)">4-7</text>
  <text x="10" y="112" font-size="8" fill="var(--muted)">overlap 2:</text>
  <rect x="64" y="104" width="88" height="12" fill="var(--s1)" opacity="0.4"/><text x="99" y="113" font-size="7" fill="var(--s1)">2-5 has 3 AND 4</text>
</svg>
^ The non-overlapping boundary falls between sentences 3 and 4, so chunk 0-3 has the dose and chunk 4-7 has the schedule — split. The overlapping chunk 2-5 straddles that boundary and holds both, keeping the fact whole.

**Retrieval can only return a chunk, so a fact split across two chunks is unrecoverable no matter how good the retriever — the chunking decides the ceiling.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the document-chunking step of a retrieval index, reduced to twelve sentences so every chunk boundary is checkable by hand.

Run `--chunks` to see both chunkings and whether either keeps the answer whole.

```text filename=chunkoverlap.py --chunks
  answer span = sentences 3-4
  no overlap (3 chunks): ['0-3', '4-7', '8-11']
    contains whole span? NONE -- answer split across a boundary
  overlap 2 (5 chunks): ['0-3', '2-5', '4-7', '6-9', '8-11']
    contains whole span? chunk 2-5
```

The non-overlapping chunking is three tidy chunks, and none of them contains both sentence 3 and sentence 4 — the answer is split across the [0-3]/[4-7] boundary, so no single chunk answers the query. The overlapping chunking adds the chunks [2-5] and [6-9] by stepping forward two sentences at a time, and [2-5] contains both 3 and 4. The fact survives whole, at the cost of five chunks instead of three.

Now `--span` shows exactly where the answer falls under non-overlapping chunks.

```text filename=chunkoverlap.py --span
  chunk 0 = sentences 0-3 <- has start s3
  chunk 1 = sentences 4-7 <- has end s4
  chunk 2 = sentences 8-11
  the span's start and end land in different chunks -> no single chunk has the whole fact
```

The span's start (sentence 3) is the last sentence of chunk 0, and its end (sentence 4) is the first sentence of chunk 1. The boundary fell exactly between the two halves of the fact. Chunk 0 retrieves with the dose but no schedule; chunk 1 retrieves with the schedule but no dose; whichever the retriever picks, the model gets half the answer and cannot tell it is missing the other half.

**The boundary landed one sentence into the fact, and that is enough: chunk 0 has the dose, chunk 1 has the schedule, and no chunk has both — the arbitrary cut, not the retriever, lost the answer.**

## Build

The self-test asserts the setup and both outcomes: that the span is short enough to fit in a chunk (so the miss is about placement, not size), that its start and end land in different non-overlapping chunks, that no non-overlapping chunk contains it, and that an overlapping chunk does.

```python filename=modules/context-and-retrieval/code/chunkoverlap-inter-01/chunkoverlap.py:100-112 COMPLETE
    answer_fits_in_chunk = span_len <= cs
    print("  the answer span fits within one chunk if aligned = %s (span %d <= chunk_size %d)" % (answer_fits_in_chunk, span_len, cs))

    start_chunk = next(i for i, r in enumerate(no) if r[0] <= span[0] <= r[1])
    end_chunk = next(i for i, r in enumerate(no) if r[0] <= span[1] <= r[1])
    answer_straddles_boundary = start_chunk != end_chunk
    print("  under non-overlap the span's start and end are in different chunks = %s (chunk %d vs %d)" % (answer_straddles_boundary, start_chunk, end_chunk))

    nooverlap_splits = chunk_containing(no, span) is None
    print("  no single non-overlapping chunk contains the whole span = %s" % nooverlap_splits)

    overlap_keeps_whole = chunk_containing(yes, span) is not None
    print("  some overlapping chunk contains the whole span = %s (%s)" % (overlap_keeps_whole, chunk_containing(yes, span)))
```

<svg role="img" aria-label="Two chunkings compared: non-overlap with 3 chunks and the answer split, overlap with 5 chunks and the answer whole in one, showing the redundancy cost" viewBox="0 0 320 120">
  <text x="10" y="18" font-size="9" fill="var(--s2)">no overlap: 3 chunks</text>
  <rect x="10" y="26" width="55" height="16" fill="none" stroke="var(--s2)"/>
  <rect x="68" y="26" width="55" height="16" fill="none" stroke="var(--s2)"/>
  <rect x="126" y="26" width="55" height="16" fill="none" stroke="var(--s2)"/>
  <text x="192" y="38" font-size="8" fill="var(--s2)">answer split ✗</text>
  <text x="10" y="70" font-size="9" fill="var(--s1)">overlap 2: 5 chunks</text>
  <rect x="10" y="78" width="40" height="16" fill="none" stroke="var(--s1)"/>
  <rect x="44" y="78" width="40" height="16" fill="var(--s1)" opacity="0.4"/>
  <rect x="78" y="78" width="40" height="16" fill="none" stroke="var(--s1)"/>
  <rect x="112" y="78" width="40" height="16" fill="none" stroke="var(--s1)"/>
  <rect x="146" y="78" width="40" height="16" fill="none" stroke="var(--s1)"/>
  <text x="196" y="90" font-size="8" fill="var(--s1)">answer whole ✓</text>
  <text x="10" y="110" font-size="7.5" fill="var(--muted)">overlap trades duplicated text (5 vs 3 chunks) for never slicing a fact</text>
</svg>
^ Overlap adds chunks (5 vs 3) and duplicates the shared sentences, and in exchange every boundary region is also covered by the middle of a neighbor — so the answer that the non-overlap cut split is whole in one overlapping chunk.

Running the check confirms every clause, including that the overlap is large enough and that it costs more chunks.

```text filename=chunkoverlap.py --check
  the answer span fits within one chunk if aligned = True (span 2 <= chunk_size 4)
  under non-overlap the span's start and end are in different chunks = True (chunk 0 vs 1)
  no single non-overlapping chunk contains the whole span = True
  some overlapping chunk contains the whole span = True ((2, 5))
  the overlap is large enough to capture the span = True (overlap 2 >= span_len-1 = 1)
  overlapping produces more chunks (redundancy cost) = True (5 > 3)
```

**The check pins the miss to the boundary, not the chunk size — the span fits in a chunk, it just straddled a cut — and shows overlap restoring it at a measured redundancy cost.**

## Definition of done

Two properties close it, and they are the win and its price. Some overlapping chunk must contain the whole span (the fact is recoverable), and the overlap must be at least large enough to capture the span — the design condition. The redundancy is the acknowledged cost, and it is bounded and predictable.

```python filename=modules/context-and-retrieval/code/chunkoverlap-inter-01/chunkoverlap.py:114-118 COMPLETE
    overlap_covers_span = ov >= span_len - 1
    print("  the overlap is large enough to capture the span = %s (overlap %d >= span_len-1 = %d)" % (overlap_covers_span, ov, span_len - 1))

    overlap_costs_more_chunks = len(yes) > len(no)
    print("  overlapping produces more chunks (redundancy cost) = %s (%d > %d)" % (overlap_costs_more_chunks, len(yes), len(no)))
```

The tradeoff has to be sized deliberately, so the tool is not over- or under-applied. Overlap must be at least the length of the longest fact you need to keep intact — too little overlap still splits longer facts, and there is no overlap that guarantees a fact longer than the chunk size survives (that needs a larger chunk, not more overlap). But overlap is not free: every extra sentence of overlap means more chunks to store, embed, and search, and the duplicated text can also return near-duplicate chunks for a query, which a diversity step (MMR) or de-duplication should clean up so the model does not see the same passage twice. The usual practice is a modest overlap — 10 to 20 percent of the chunk size, or a couple of sentences — enough to catch facts that span a boundary without doubling the index. And the deeper fix, when boundaries matter a lot, is to place them by meaning (splitting on section or paragraph structure) so cuts fall between facts rather than through them; overlap is the cheap, general insurance that works even when the boundaries are arbitrary.

<svg role="img" aria-label="A chunk boundary with an overlap band around it; a short fact fits inside the band and is captured, a fact longer than the chunk cannot be captured by any overlap" viewBox="0 0 320 120">
  <line x1="160" y1="20" x2="160" y2="70" stroke="var(--s2)" stroke-width="2"/>
  <text x="120" y="16" font-size="8" fill="var(--s2)">boundary</text>
  <rect x="120" y="30" width="80" height="14" fill="var(--s1)" opacity="0.35"/>
  <text x="128" y="55" font-size="7.5" fill="var(--s1)">overlap band (covers the boundary)</text>
  <rect x="140" y="30" width="30" height="14" fill="var(--s1)"/>
  <text x="132" y="27" font-size="7.5" fill="var(--ink)">short fact ✓ inside band</text>
  <rect x="70" y="80" width="180" height="14" fill="none" stroke="var(--muted)" stroke-dasharray="3 2"/>
  <text x="72" y="106" font-size="7.5" fill="var(--muted)">fact longer than a chunk ✗ — needs a bigger chunk, not more overlap</text>
</svg>
^ Overlap works when the fact fits in a chunk: sized to the longest such fact, the overlap band around each boundary catches it. A fact longer than the chunk itself cannot be rescued by any overlap — that requires a larger chunk.

**Done means some overlapping chunk holds the whole span and the overlap is sized to the fact, at a bounded redundancy cost — insurance against arbitrary boundaries slicing facts, tuned to the longest fact and cleaned of duplicates downstream.**

## Boss fight

Your RAG system answers most questions well but intermittently fails on questions whose answer you can see verbatim in the source documents — and the failures are not reproducible across documents, sometimes the same kind of question works and sometimes it does not. Retrieval quality metrics look fine on average. What is the likely cause, and what two changes would you make?

The likely cause is non-overlapping chunk boundaries slicing facts in half. When a fact's evidence spans a boundary, it is split across two chunks and no single chunk contains the whole answer, so retrieval returns a chunk with only part of the fact and the model answers from a fragment or fails. It is intermittent and non-reproducible because whether it happens depends on where the arbitrary fixed-size cut fell relative to the fact, which varies document to document — the same question fails when the cut lands mid-fact and works when it does not. Average retrieval metrics look fine because most facts sit comfortably inside a chunk; only the boundary-straddling ones fail, and they are a minority. The two changes: first, add chunk overlap — step chunks forward by less than the chunk size so adjacent chunks share a stretch, sized to at least the longest fact you need intact (a couple of sentences, or 10–20% of the chunk), which guarantees any short fact appears whole in some chunk. Second, where document structure is available, place boundaries on semantic units — paragraphs, sections, list items — so cuts fall between facts rather than through them, reducing how often overlap has to save you. Together they raise the ceiling that chunking imposes: overlap as cheap general insurance, structure-aware splitting as the targeted fix. After adding overlap, add a de-duplication or MMR step so the now-overlapping chunks do not return the same passage twice.

## External resources

The LangChain and LlamaIndex documentation on text splitters and `chunk_overlap` — the production parameters for exactly this, with guidance on choosing chunk size and overlap and on structure-aware (recursive, semantic) splitting that places boundaries between units.

Pinecone's and others' guides on chunking strategies for RAG — practical treatments of the size/overlap tradeoff, why boundary-straddling facts get lost, and how overlap interacts with downstream de-duplication and reranking.
