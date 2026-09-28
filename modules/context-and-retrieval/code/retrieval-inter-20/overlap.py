"""Overlap the chunks, or an answer that straddles a boundary is split across two and retrievable from neither.

Retrieval indexes a document by cutting it into chunks and embedding each one. If the chunks abut with no
overlap -- chunk one ends exactly where chunk two begins -- then any span that crosses that boundary is torn in
half: its first part is the tail of one chunk, its second part the head of the next, and NO single chunk
contains the whole thing. A query that needs that whole span matches each half only weakly, because each chunk
holds only a fragment of the answer. The information is in the document, indexed, and still unretrievable,
purely because the cut landed in the middle of it.

Overlapping chunks fix it. Slide the chunk window by a stride SMALLER than its size, so consecutive chunks
share their edges. Now a span shorter than the overlap is guaranteed to sit whole inside at least one chunk --
the one whose window happens to straddle the same boundary. The overlap is a safety margin sized to the longest
answer span you need to keep intact: make the overlap at least one less than that length and no span of that
length can fall through a crack. The cost is redundancy -- overlapping chunks repeat their shared tokens, so
you index more chunks -- which is the price of never splitting an answer.

On this fixture a 12-token document is chunked into size-6 pieces, and the answer occupies tokens 5-6, straddling
the boundary at 6. With no overlap the chunks are [0-5] and [6-11]; the answer is in neither. With a stride of 3
the chunks are [0-5], [3-8], [6-11]; the answer sits whole inside [3-8]. This computes both.

  --chunks     the chunk ranges under each chunking, and whether the answer span fits inside one
  --span       where the answer straddles the boundary, and the overlap needed to keep it whole
  --check      no overlap splits the straddling answer; overlap keeps it whole in one chunk

The document, chunk size, span, and strides are the fixture; every chunk is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "doc.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


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


def holding_chunks(cks, span_start, span_len):
    return [c for c in cks if contains(c, span_start, span_len)]


# ----------------------------------------------------------------- printing

def rng(c):
    return "[%d-%d]" % (c[0], c[1] - 1)


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


def span_view(data):
    n, size, a, al = data["doc_len"], data["chunk_size"], data["answer_start"], data["answer_len"]
    boundary = ((a // size) + 1) * size
    print("SPAN — why the answer is torn, and the overlap that saves it")
    print("-" * 60)
    print("  answer tokens %d..%d ; a no-overlap boundary sits at %d, inside the span" % (a, a + al - 1, boundary))
    print("  needed overlap to keep a length-%d span whole: at least %d tokens" % (al, al - 1))
    print("  chosen overlap = size - stride = %d - %d = %d" % (size, data["overlap_stride"], size - data["overlap_stride"]))
    print("-" * 60)
    print("  overlap >= span_len - 1 guarantees no span of that length is split.")


def check(data):
    print("SELF-TEST — no overlap splits the straddling answer; overlap keeps it whole in one chunk")
    print("-" * 100)
    n, size, a, al = data["doc_len"], data["chunk_size"], data["answer_start"], data["answer_len"]
    no_cks = chunks(n, size, data["non_overlap_stride"])
    ov_cks = chunks(n, size, data["overlap_stride"])
    boundary = ((a // size) + 1) * size

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

    ok = span_straddles_boundary and no_overlap_misses and overlap_holds and overlap_meets_guarantee and overlap_costs_more_chunks
    print("-" * 100)
    print("SELF-TEST %s  span_straddles_boundary=%s  no_overlap_misses=%s  overlap_holds=%s  overlap_meets_guarantee=%s  overlap_costs_more_chunks=%s"
          % ("PASS" if ok else "FAIL", span_straddles_boundary, no_overlap_misses, overlap_holds, overlap_meets_guarantee, overlap_costs_more_chunks))
    return ok


def main():
    p = argparse.ArgumentParser(description="Overlap chunks with a stride smaller than their size so an answer never splits across a boundary.")
    p.add_argument("--chunks", action="store_true")
    p.add_argument("--span", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("doc_len=%d  chunk_size=%d  answer=%d..%d  file=%s  (the document is a fixture)"
          % (data["doc_len"], data["chunk_size"], data["answer_start"], data["answer_start"] + data["answer_len"] - 1, DATA.name))
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
