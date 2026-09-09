"""Close a stream window on a watermark, not on the first later event -- an eager close drops the out-of-order latecomer.

When you aggregate a stream of events into time windows -- events per minute, a sum per hour -- you have to decide WHEN a
window is finished so you can emit its result. That decision is hard because events arrive out of order: an event that
happened at time 7 can reach you after an event that happened at time 12, because of network delays, retries, buffering,
or clients with slow clocks. So the moment you see an event timed 12, it is tempting to conclude that the window covering
times 0..10 is done and emit it -- but the event timed 7, which belongs in that window, may not have arrived yet. If you
closed the window on the first event past its end, that latecomer arrives to find its window already emitted, and it is
silently dropped. Your count for that window is simply wrong, low by however many stragglers you cut off, and nothing
errors.

A watermark makes the close decision explicitly instead of implicitly. The watermark is a moving assertion about
completeness: 'I have now seen enough of the stream that no event earlier than time W will still arrive.' A common way to
compute it is watermark = (the maximum event-time seen so far) - (an allowed_lateness bound), which says 'I have seen an
event at time max, and I am willing to assume events run at most allowed_lateness out of order, so everything up to
max - allowed_lateness must have arrived by now.' A window is closed and emitted only when the watermark passes the
window's end -- meaning the stream has advanced far enough to be confident the window is complete. An out-of-order event
that arrives while the watermark is still behind the window's end is inside the window and counted; only an event that
arrives after the watermark has already passed its window (later than the lateness bound allowed) is dropped, and that
drop is now an explicit, tunable decision rather than an accident of arrival order.

The trade-off is latency against completeness: a larger allowed_lateness holds windows open longer, tolerating more
out-of-order events but delaying every result; a smaller one emits sooner but drops more stragglers. The watermark is
where you make that trade-off on purpose. Closing on the first later event is the degenerate case of zero tolerance made
by accident.

The rule: close an event-time window on a watermark -- an assertion (max-seen minus an allowed-lateness bound) that no
earlier event will still arrive -- not on the arrival of the first event past the window's end, because streams are
out of order, so an eager close silently drops the latecomers that still belong in the window.

On this fixture window 0 covers event-times [0,10) and truly contains three events (times 2, 5, and the late 7). The naive
stream sees event-time 12, closes window 0 with only the two events it had (times 2 and 5), and then drops the late
event-time 7. The watermark stream (allowed_lateness 5) keeps window 0 open -- when event 7 arrives the watermark is only
7, still below 10 -- so it counts all three, and closes window 0 only later when the watermark reaches 10. This computes both.

  --windows    each window's count under the naive close vs the watermark close vs the true count, and which events were dropped
  --watermark  the watermark rising event by event, and the moment window 0 is safe to close -- after the late event is in
  --check      the naive close drops the out-of-order event and undercounts window 0; the watermark close counts all three

The events, window size, and lateness bound are the fixture; every count, watermark, and drop is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "watermark.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def window_of(t, wsize):
    return t // wsize


def run_naive(events, wsize):
    """Close a window as soon as any event reaches its end (max-seen past the end); later events for it are dropped."""
    counts = {}
    dropped = []
    max_seen = None
    for ev in events:
        w = window_of(ev["t"], wsize)
        if max_seen is not None and (w + 1) * wsize <= max_seen:
            dropped.append(ev)  # its window already closed
            continue
        counts[w] = counts.get(w, 0) + 1
        max_seen = ev["t"] if max_seen is None else max(max_seen, ev["t"])
    return counts, dropped


def run_watermark(events, wsize, allowed):
    """Close a window only when the watermark (max-seen - allowed_lateness) passes its end; count everything before that."""
    counts = {}
    dropped = []
    watermark = None
    max_seen = None
    for ev in events:
        w = window_of(ev["t"], wsize)
        if watermark is not None and watermark >= (w + 1) * wsize:
            dropped.append(ev)  # arrived later than the lateness bound allowed
            continue
        counts[w] = counts.get(w, 0) + 1
        max_seen = ev["t"] if max_seen is None else max(max_seen, ev["t"])
        watermark = max_seen - allowed
    return counts, dropped


def true_counts(events, wsize):
    counts = {}
    for ev in events:
        counts[window_of(ev["t"], wsize)] = counts.get(window_of(ev["t"], wsize), 0) + 1
    return counts


# ----------------------------------------------------------------- printing

def windows_view(data):
    events, wsize, allowed = data["events"], data["window_size"], data["allowed_lateness"]
    naive, nd = run_naive(events, wsize)
    wm, wd = run_watermark(events, wsize, allowed)
    truth = true_counts(events, wsize)
    print("WINDOWS — event-time windows of %d, allowed_lateness %d" % (wsize, allowed))
    print("-" * 66)
    print("  window     range      true   naive-close   watermark-close")
    for w in sorted(truth):
        print("  %-10s [%d,%d)     %-6d %-13d %d"
              % ("window %d" % w, w * wsize, (w + 1) * wsize, truth[w], naive.get(w, 0), wm.get(w, 0)))
    print("-" * 66)
    print("  naive dropped:     %s" % [(e["t"], e["value"]) for e in nd])
    print("  watermark dropped: %s" % [(e["t"], e["value"]) for e in wd])


def watermark_view(data):
    events, wsize, allowed = data["events"], data["window_size"], data["allowed_lateness"]
    print("WATERMARK — max event-time seen, watermark = max - %d, and window-0 close status" % allowed)
    print("-" * 74)
    print("  arrival  event    max-seen   watermark   window 0 [0,%d) closeable?" % wsize)
    max_seen = None
    for ev in events:
        max_seen = ev["t"] if max_seen is None else max(max_seen, ev["t"])
        watermark = max_seen - allowed
        closeable = "yes -> emit" if watermark >= wsize else "no, keep open"
        print("  t=%-5d  %s (t=%d)  %-9d  %-10d  %s" % (ev["t"], ev["value"], ev["t"], max_seen, watermark, closeable))
    print("-" * 74)
    print("  the late event t=7 arrives while watermark=7 < 10, so window 0 is still open and counts it.")


def check(data):
    print("SELF-TEST — the naive close drops the out-of-order event and undercounts window 0; the watermark counts all three")
    print("-" * 114)
    events, wsize, allowed = data["events"], data["window_size"], data["allowed_lateness"]
    naive, nd = run_naive(events, wsize)
    wm, wd = run_watermark(events, wsize, allowed)
    truth = true_counts(events, wsize)

    true_w0 = truth[0]
    naive_undercounts = naive.get(0, 0) < true_w0
    print("  naive-close window 0 count = %d of a true %d -> undercounts = %s" % (naive.get(0, 0), true_w0, naive_undercounts))

    watermark_correct = wm.get(0, 0) == true_w0
    print("  watermark-close window 0 count = %d of a true %d -> correct = %s" % (wm.get(0, 0), true_w0, watermark_correct))

    late = {"t": 7, "value": "d"}
    naive_dropped_late = late in nd
    print("  the naive close dropped the late event (t=7) = %s" % naive_dropped_late)

    watermark_kept_late = late not in wd
    print("  the watermark close kept the late event (t=7) = %s" % watermark_kept_late)

    counts_differ = naive.get(0, 0) != wm.get(0, 0)
    print("  the two closes disagree on window 0 = %s (%d vs %d)" % (counts_differ, naive.get(0, 0), wm.get(0, 0)))

    ok = naive_undercounts and watermark_correct and naive_dropped_late and watermark_kept_late and counts_differ
    print("-" * 114)
    print("SELF-TEST %s  naive_undercounts=%s  watermark_correct=%s  naive_dropped_late=%s  watermark_kept_late=%s  counts_differ=%s"
          % ("PASS" if ok else "FAIL", naive_undercounts, watermark_correct, naive_dropped_late, watermark_kept_late, counts_differ))
    return ok


def main():
    p = argparse.ArgumentParser(description="Watermarks for event-time windowing: close a streaming window on a watermark -- an assertion (max event-time seen minus an allowed-lateness bound) that no earlier event will still arrive -- not on the arrival of the first event past the window's end, because streams are out of order and an eager close silently drops the latecomers that still belong in the window.")
    p.add_argument("--windows", action="store_true")
    p.add_argument("--watermark", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("window_size=%d  allowed_lateness=%d  events=%s  file=%s  (the events, window size, and lateness are a fixture)"
          % (data["window_size"], data["allowed_lateness"], [(e["t"], e["value"]) for e in data["events"]], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.windows:
        windows_view(data)
    elif args.watermark:
        watermark_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
