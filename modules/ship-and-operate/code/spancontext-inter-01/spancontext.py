"""Propagate span context -- a trace id plus each span's own id and its parent's id -- so a trace can reconstruct the call tree and each span's self-time, not just a flat correlation id that groups the log lines but cannot say which hop was slow.

A correlation id stamped on every log line of a request is a real step up from an unlabeled jumble: you can now pull all the events of one request together. But it is flat. It tells you these events belong to the same request and nothing about their shape -- not which service called which, and not where the time went.

Where the time went is the question you actually have during an incident, and a flat id cannot answer it, because span durations nest. A parent span's duration already contains its children's: the gateway is 'busy' for the entire request while it waits on the database, which is itself busy while it waits on the cache. So if you sum the durations to see the total work, you double-count the nested time and get a number larger than the request's wall-clock time -- a total that is meaningless. And if you pick the span with the largest total duration as the bottleneck, you usually pick a caller that is mostly waiting, not the code that is actually slow.

The fix is span context: give each span its own id and record its parent's id, so the collector can rebuild the call tree from the parent pointers. With the tree you compute each span's self-time -- its own duration minus the time spent inside its children -- which attributes every slice of wall-clock time to exactly one span. The self-times sum to the request's wall-clock time, and the span with the largest self-time is the real hotspot.

On this fixture the gateway (100ms) contains auth (20ms) and the database (60ms), and the database contains the cache (50ms). By total duration the database looks worst at 60ms; by self-time it is only 10ms and the cache's 50ms is the real bottleneck. This computes both.

  --flat   the correlation-id view: all spans share the request, and summing durations double-counts the nested time
  --tree   the span-context view: the reconstructed call tree, each span's self-time, and the real bottleneck
  --check  the flat view double-counts and blames the wrong span; the tree attributes time exactly once and finds the real hotspot

spans is the fixture; the duration sum, the tree, the self-times, and the two bottleneck picks are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "spancontext.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def wall_time(spans):
    """The request's real duration is the root span's duration."""
    root = next(s for s in spans if s["parent_id"] is None)
    return root["duration_ms"]


def flat_duration_sum(spans):
    """The naive 'total work': sum every span's duration -- double-counts nested time."""
    return sum(s["duration_ms"] for s in spans)


def children_of(spans, span_id):
    return [s for s in spans if s["parent_id"] == span_id]


def self_time(spans, span):
    """A span's own time: its duration minus the durations of its direct children (which nest inside it)."""
    return span["duration_ms"] - sum(c["duration_ms"] for c in children_of(spans, span["span_id"]))


def bottleneck_by_duration(spans):
    """The naive pick: the span with the largest total duration."""
    return max(spans, key=lambda s: s["duration_ms"])


def bottleneck_by_self_time(spans):
    """The real pick: the span with the largest self-time."""
    return max(spans, key=lambda s: self_time(spans, s))


# ----------------------------------------------------------------- printing

def flat_view(data):
    spans = data["spans"]
    print("FLAT — the correlation-id view: every span shares the request, no structure")
    print("-" * 60)
    for s in spans:
        print("  span %d  %-9s duration %dms" % (s["span_id"], s["service"], s["duration_ms"]))
    print("-" * 60)
    print("  summed durations = %dms, but the request took %dms wall-clock" % (flat_duration_sum(spans), wall_time(spans)))
    b = bottleneck_by_duration(spans)
    print("  largest-duration span = %s (%dms) -- the naive bottleneck" % (b["service"], b["duration_ms"]))


def tree_view(data):
    spans = data["spans"]
    print("TREE — the span-context view: the call tree and each span's self-time")
    print("-" * 60)
    by_id = {s["span_id"]: s for s in spans}

    def show(span, depth):
        st = self_time(spans, span)
        print("  %s%-9s total %dms   self %dms" % ("  " * depth, span["service"], span["duration_ms"], st))
        for c in children_of(spans, span["span_id"]):
            show(c, depth + 1)

    root = next(s for s in spans if s["parent_id"] is None)
    show(root, 0)
    print("-" * 60)
    total_self = sum(self_time(spans, s) for s in spans)
    b = bottleneck_by_self_time(spans)
    print("  self-times sum to %dms = wall-clock; real bottleneck = %s (self %dms)"
          % (total_self, b["service"], self_time(spans, b)))


def check(data):
    print("SELF-TEST — the flat view double-counts and blames the wrong span; the tree attributes time exactly once and finds the real hotspot")
    print("-" * 112)
    spans = data["spans"]
    wall = wall_time(spans)

    flat_double_counts = flat_duration_sum(spans) > wall
    print("  flat duration sum exceeds wall-clock (double-counts nesting) = %s (%dms > %dms)"
          % (flat_double_counts, flat_duration_sum(spans), wall))

    total_self = sum(self_time(spans, s) for s in spans)
    selftimes_account_exactly = abs(total_self - wall) < 1e-9
    print("  self-times sum exactly to wall-clock = %s (%dms)" % (selftimes_account_exactly, total_self))

    dur_pick = bottleneck_by_duration(spans)
    self_pick = bottleneck_by_self_time(spans)
    bottleneck_disagrees = dur_pick["span_id"] != self_pick["span_id"]
    print("  duration bottleneck and self-time bottleneck disagree = %s (%s vs %s)"
          % (bottleneck_disagrees, dur_pick["service"], self_pick["service"]))

    dur_pick_mostly_waiting = self_time(spans, dur_pick) < self_time(spans, self_pick)
    print("  the duration bottleneck is mostly waiting = %s (self %dms < %dms)"
          % (dur_pick_mostly_waiting, self_time(spans, dur_pick), self_time(spans, self_pick)))

    roots = [s for s in spans if s["parent_id"] is None]
    ids = {s["span_id"] for s in spans}
    tree_wellformed = len(roots) == 1 and all(s["parent_id"] in ids for s in spans if s["parent_id"] is not None)
    print("  the tree is well-formed (one root, every parent resolves) = %s" % tree_wellformed)

    ok = (flat_double_counts and selftimes_account_exactly and bottleneck_disagrees
          and dur_pick_mostly_waiting and tree_wellformed)
    print("-" * 112)
    print("SELF-TEST %s  flat_double_counts=%s  selftimes_account_exactly=%s  bottleneck_disagrees=%s  dur_pick_mostly_waiting=%s  tree_wellformed=%s"
          % ("PASS" if ok else "FAIL", flat_double_counts, selftimes_account_exactly, bottleneck_disagrees,
             dur_pick_mostly_waiting, tree_wellformed))
    return ok


def main():
    p = argparse.ArgumentParser(description="Span context: propagate a trace id plus each span's own id and its parent's id, so a trace can reconstruct the call tree and each span's self-time, not just a flat correlation id that groups the log lines but cannot say which hop was slow -- span durations nest, so summing them double-counts and the largest-duration span is usually a caller that is mostly waiting.")
    p.add_argument("--flat", action="store_true")
    p.add_argument("--tree", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("spans=%d  file=%s  (the spans are a fixture)" % (len(data["spans"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.flat:
        flat_view(data)
    elif args.tree:
        tree_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
