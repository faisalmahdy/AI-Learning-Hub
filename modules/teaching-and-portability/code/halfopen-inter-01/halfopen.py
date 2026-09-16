"""Represent a range as half-open [start, end), excluding the upper bound, so adjacent ranges tile a whole without gaps or overlaps -- closed inclusive ranges double-count the shared boundary and overrun the end.

A range needs two numbers, a start and an end, and the only real decision is whether the end is part of it. A closed interval [a, b] includes both ends. A half-open interval [a, b) includes the start and excludes the end. That single difference decides whether ranges compose cleanly.

The trouble with closed intervals shows up the moment two of them are adjacent. Chunk the indices 0..29 into tens as [0, 10] and [10, 20] and both chunks contain the index 10 -- it is the end of the first and the start of the second, and a closed interval includes both, so 10 is in two chunks at once. Every boundary is double-counted, and the last chunk [20, 30] reaches index 30, one past the last real item. To make closed chunks tile you have to litter the code with minus-ones -- [0, 9], [10, 19] -- and every one is a chance to get the off-by-one wrong.

Half-open intervals compose by construction. [0, 10) and [10, 20) meet exactly at 10, which belongs only to the second, so no index is in two chunks and none is in none: the chunks partition the whole. The arithmetic is clean too -- the count of integers in [a, b) is exactly b minus a, chunk i is [i*size, (i+1)*size) with no fencepost corrections, and the last chunk [20, 30) stops right at the end without overrunning it. This is why Python's range, list slicing, and almost every good range API exclude the upper bound.

On this fixture 30 items are chunked into three tens. Closed chunks double-count the indices 10 and 20 and reach a nonexistent index 30; half-open chunks put every index in exactly one chunk and cover exactly 0..29. This computes both.

  --closed     closed inclusive chunks: the boundaries 10 and 20 land in two chunks, and 30 overruns the end
  --halfopen   half-open chunks: every index is in exactly one chunk, and the count in each is end minus start
  --check      closed intervals double-count boundaries and overrun the end, while half-open intervals partition the items exactly

n_items and chunk_size are the fixture; the chunk memberships, double-counts, overrun, and partition checks are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "halfopen.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def make_chunks(n_items, chunk_size):
    """The (start, end) pairs, chunk i = (i*size, (i+1)*size) -- the boundaries themselves are scheme-neutral."""
    return [(i, i + chunk_size) for i in range(0, n_items, chunk_size)]


def contains_closed(chunk, x):
    """Closed interval [start, end]: the end index is included."""
    start, end = chunk
    return start <= x <= end


def contains_halfopen(chunk, x):
    """Half-open interval [start, end): the end index is excluded."""
    start, end = chunk
    return start <= x < end


def chunks_of(chunks, x, contains):
    """The indices of the chunks that contain item x under the given membership rule."""
    return [i for i, c in enumerate(chunks) if contains(c, x)]


# ----------------------------------------------------------------- printing

def _describe(data, contains):
    n = data["n_items"]
    chunks = make_chunks(n, data["chunk_size"])
    universe = range(n)
    multi = [x for x in universe if len(chunks_of(chunks, x, contains)) > 1]
    overrun = [c[1] for c in chunks if contains(c, c[1]) and c[1] >= n]  # end index included and past the data
    covered = {x for x in range(-1, n + data["chunk_size"]) if chunks_of(chunks, x, contains)}
    return chunks, multi, overrun, covered


def closed_view(data):
    chunks, multi, overrun, covered = _describe(data, contains_closed)
    print("CLOSED — inclusive ranges [start, end]")
    print("-" * 60)
    print("  chunks: %s" % ["[%d, %d]" % c for c in chunks])
    print("  indices in TWO chunks (double-counted): %s" % multi)
    print("  chunk sizes (end - start + 1): %s" % [c[1] - c[0] + 1 for c in chunks])
    print("  overruns to index past the last item (%d): %s" % (data["n_items"] - 1, overrun))
    print("-" * 60)
    print("  the boundaries belong to two chunks and the last chunk reaches a nonexistent index")


def halfopen_view(data):
    chunks, multi, overrun, covered = _describe(data, contains_halfopen)
    print("HALF-OPEN — end-exclusive ranges [start, end)")
    print("-" * 60)
    print("  chunks: %s" % ["[%d, %d)" % c for c in chunks])
    print("  indices in two chunks: %s" % multi)
    print("  chunk sizes (end - start): %s" % [c[1] - c[0] for c in chunks])
    print("  covers exactly 0..%d: %s" % (data["n_items"] - 1, covered == set(range(data["n_items"]))))
    print("-" * 60)
    print("  every index is in exactly one chunk and the size is just end minus start")


def check(data):
    print("SELF-TEST — closed intervals double-count boundaries and overrun the end, while half-open intervals partition the items exactly")
    print("-" * 112)
    n = data["n_items"]
    chunks = make_chunks(n, data["chunk_size"])
    universe = list(range(n))

    closed_multi = [x for x in universe if len(chunks_of(chunks, x, contains_closed)) > 1]
    closed_double_counts = len(closed_multi) > 0
    print("  closed intervals put a boundary index in two chunks = %s (%s)" % (closed_double_counts, closed_multi))

    closed_overruns = any(contains_closed(c, n) for c in chunks)
    print("  a closed chunk reaches the nonexistent index %d = %s" % (n, closed_overruns))

    halfopen_partitions = all(len(chunks_of(chunks, x, contains_halfopen)) == 1 for x in universe)
    print("  half-open intervals put every index in exactly one chunk = %s" % halfopen_partitions)

    covered = {x for x in range(-1, n + data["chunk_size"]) if chunks_of(chunks, x, contains_halfopen)}
    halfopen_covers_exactly = covered == set(universe)
    print("  half-open chunks cover exactly 0..%d, no gap or overrun = %s" % (n - 1, halfopen_covers_exactly))

    halfopen_size_is_diff = all((c[1] - c[0]) == data["chunk_size"] for c in chunks)
    print("  a half-open chunk's size is end minus start = %s" % halfopen_size_is_diff)

    ok = (closed_double_counts and closed_overruns and halfopen_partitions
          and halfopen_covers_exactly and halfopen_size_is_diff)
    print("-" * 112)
    print("SELF-TEST %s  closed_double_counts=%s  closed_overruns=%s  halfopen_partitions=%s  halfopen_covers_exactly=%s  halfopen_size_is_diff=%s"
          % ("PASS" if ok else "FAIL", closed_double_counts, closed_overruns, halfopen_partitions,
             halfopen_covers_exactly, halfopen_size_is_diff))
    return ok


def main():
    p = argparse.ArgumentParser(description="Half-open intervals: represent a range as [start, end) with the end excluded, so adjacent ranges partition a whole with no gaps or overlaps and the size is end minus start, because closed inclusive intervals double-count the shared boundary between adjacent chunks and overrun the end, forcing error-prone off-by-one corrections.")
    p.add_argument("--closed", action="store_true")
    p.add_argument("--halfopen", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("n_items=%d  chunk_size=%d  file=%s  (indices 0..%d)"
          % (data["n_items"], data["chunk_size"], DATA.name, data["n_items"] - 1))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.closed:
        closed_view(data)
    elif args.halfopen:
        halfopen_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
