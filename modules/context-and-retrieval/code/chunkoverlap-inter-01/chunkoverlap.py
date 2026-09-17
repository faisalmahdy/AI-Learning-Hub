"""Overlap the chunks -- a fact whose evidence straddles a chunk boundary is sliced in half by non-overlapping chunks and lost.

Retrieval works on chunks: you split a document into pieces, embed each, and fetch the most relevant piece for a query. The obvious way to split is into consecutive, non-overlapping windows -- sentences 0 to 3, then 4 to 7, and so on -- which tiles the document with no wasted duplication. It also puts a hard cut at every boundary, and a boundary does not care what it slices through. When the evidence a query needs spans that cut -- 'the dose was 5mg' in one sentence and 'given twice daily' in the next, with the boundary between them -- the fact is split across two chunks, and neither chunk contains the whole answer. Retrieval that fetches the single best chunk gets half the fact; even the best-matching chunk is incomplete, and the model answers from a fragment.

The failure is invisible at indexing time. The chunks look fine, the embeddings are computed, coverage is complete -- every sentence is in exactly one chunk. The gap only appears for queries whose answer happens to straddle a boundary, and which queries those are depends on where the arbitrary cuts fell, so it surfaces as sporadic, hard-to-reproduce misses on facts that are demonstrably in the corpus.

The fix is to OVERLAP adjacent chunks: instead of stepping forward by the full chunk size, step forward by less, so each chunk repeats the last stretch of the previous one. With an overlap of a few sentences, any fact short enough to fit in a chunk is guaranteed to appear whole in at least one chunk, because wherever the fact sits, some window starts early enough to contain all of it. A boundary still exists, but every boundary region is now also covered by the middle of a neighboring chunk. The cost is redundancy -- more chunks, and the overlapped text is stored and embedded twice -- which is the price of never slicing a fact in half. The overlap must be at least as large as the longest fact you need to keep intact.

The rule: overlap adjacent chunks by at least the length of the facts you must keep intact, rather than splitting the document into non-overlapping windows, because a non-overlapping boundary can fall in the middle of a fact and split its evidence across two chunks so no single chunk answers the query -- while overlapping windows guarantee any short-enough span appears whole in some chunk, at the cost of duplicated text.

On this fixture the answer spans sentences 3 and 4, which straddle the boundary between the non-overlapping chunks [0-3] and [4-7]: no single non-overlapping chunk contains both. With overlap 2 the chunk [2-5] contains both -- the answer survives whole -- at the cost of 5 chunks instead of 3. This computes both.

  --chunks    the non-overlapping and overlapping chunk ranges, and which contain the whole answer span
  --span      why the answer straddles a boundary under non-overlapping chunks and is captured under overlap
  --check     non-overlapping chunks split the answer across a boundary; overlapping chunks keep it whole in one chunk

sentences, chunk_size, overlap, and answer_span are the fixture; every chunk range and containment is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "chunkoverlap.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


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


def contains_span(rng, span):
    """Whether chunk range rng fully contains the answer span."""
    return rng[0] <= span[0] and span[1] <= rng[1]


def chunk_containing(ranges, span):
    """The first chunk range that fully contains the span, or None."""
    for r in ranges:
        if contains_span(r, span):
            return r
    return None


# ----------------------------------------------------------------- printing

def chunks_view(data):
    n = len(data["sentences"])
    cs, ov, span = data["chunk_size"], data["overlap"], data["answer_span"]
    no = chunk_ranges(n, cs, cs)
    yes = chunk_ranges(n, cs, cs - ov)
    print("CHUNKS — non-overlapping vs overlapping (chunk_size %d, overlap %d)" % (cs, ov))
    print("-" * 66)
    print("  answer span = sentences %d-%d" % (span[0], span[1]))
    print("  no overlap (%d chunks): %s" % (len(no), ["%d-%d" % r for r in no]))
    print("    contains whole span? %s" % (chunk_containing(no, span) or "NONE -- answer split across a boundary"))
    print("  overlap %d (%d chunks): %s" % (ov, len(yes), ["%d-%d" % r for r in yes]))
    print("    contains whole span? %s" % ("chunk %d-%d" % chunk_containing(yes, span) if chunk_containing(yes, span) else "NONE"))


def span_view(data):
    n = len(data["sentences"])
    cs, ov, span = data["chunk_size"], data["overlap"], data["answer_span"]
    no = chunk_ranges(n, cs, cs)
    print("SPAN — where the answer falls under non-overlapping chunks")
    print("-" * 60)
    for i, r in enumerate(no):
        marks = []
        if r[0] <= span[0] <= r[1]:
            marks.append("start s%d" % span[0])
        if r[0] <= span[1] <= r[1]:
            marks.append("end s%d" % span[1])
        print("  chunk %d = sentences %d-%d %s" % (i, r[0], r[1], ("<- has " + ", ".join(marks)) if marks else ""))
    print("-" * 60)
    print("  the span's start and end land in different chunks -> no single chunk has the whole fact")


def check(data):
    print("SELF-TEST — non-overlapping chunks split the answer across a boundary; overlapping chunks keep it whole in one chunk")
    print("-" * 122)
    n = len(data["sentences"])
    cs, ov, span = data["chunk_size"], data["overlap"], data["answer_span"]
    no = chunk_ranges(n, cs, cs)
    yes = chunk_ranges(n, cs, cs - ov)
    span_len = span[1] - span[0] + 1

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

    overlap_covers_span = ov >= span_len - 1
    print("  the overlap is large enough to capture the span = %s (overlap %d >= span_len-1 = %d)" % (overlap_covers_span, ov, span_len - 1))

    overlap_costs_more_chunks = len(yes) > len(no)
    print("  overlapping produces more chunks (redundancy cost) = %s (%d > %d)" % (overlap_costs_more_chunks, len(yes), len(no)))

    ok = (answer_fits_in_chunk and answer_straddles_boundary and nooverlap_splits and overlap_keeps_whole
          and overlap_covers_span and overlap_costs_more_chunks)
    print("-" * 122)
    print("SELF-TEST %s  answer_fits_in_chunk=%s  answer_straddles_boundary=%s  nooverlap_splits=%s  overlap_keeps_whole=%s  overlap_covers_span=%s  overlap_costs_more_chunks=%s"
          % ("PASS" if ok else "FAIL", answer_fits_in_chunk, answer_straddles_boundary, nooverlap_splits, overlap_keeps_whole, overlap_covers_span, overlap_costs_more_chunks))
    return ok


def main():
    p = argparse.ArgumentParser(description="Chunk overlap: overlap adjacent chunks by at least the length of the facts you must keep intact, rather than splitting the document into non-overlapping windows, because a non-overlapping boundary can fall in the middle of a fact and split its evidence across two chunks so no single chunk answers the query -- while overlapping windows guarantee any short-enough span appears whole in some chunk, at the cost of duplicated text.")
    p.add_argument("--chunks", action="store_true")
    p.add_argument("--span", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("sentences=%d  chunk_size=%d  overlap=%d  answer_span=%s  file=%s  (all are a fixture)"
          % (len(data["sentences"]), data["chunk_size"], data["overlap"], data["answer_span"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.chunks:
        chunks_view(data)
    elif args.span:
        span_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
