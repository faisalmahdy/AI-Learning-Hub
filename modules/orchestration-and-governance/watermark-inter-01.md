---
id: watermark-inter-01
title: Close a stream window on a watermark, not on the first later event — an eager close drops the out-of-order latecomer
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: When you aggregate a stream of events into time windows — events per minute, a sum per hour — you must decide when a window is finished so you can emit its result. That is hard because events arrive out of order: an event that happened at time 7 can reach you after an event that happened at time 12, because of network delays, retries, buffering, or slow client clocks. So the moment you see an event timed 12 it is tempting to conclude the window covering 0..10 is done and emit it — but the event timed 7, which belongs in that window, may not have arrived yet. Close the window on the first event past its end and that latecomer arrives to find its window already emitted, so it is silently dropped and the count is low, with no error. A watermark makes the close decision explicit: it is a moving assertion "no event earlier than time W will still arrive," commonly computed as (max event-time seen) − (an allowed_lateness bound). A window is closed only when the watermark passes its end, so out-of-order events within the lateness bound are still counted; only events arriving after the watermark has passed their window are dropped, now an explicit tunable decision. On a fixture where window 0 [0,10) truly holds three events (times 2, 5, and the late 7), the naive close sees time 12, emits window 0 with just two, and drops the late 7, while the watermark close (allowed_lateness 5) keeps window 0 open until the watermark reaches 10 and counts all three.
eli5: Imagine collecting everyone's homework due by 10 o'clock, but some students hand theirs in late because the hallway is crowded. If you seal the box the instant you see a paper stamped "12 o'clock," you'll seal it before a student whose paper is stamped "7 o'clock" pushes through the crowd — and their on-time homework gets thrown away, even though it belonged in the box. Instead you wait a little: you tell yourself "papers can be up to 5 minutes slow getting here, so I'll only seal the 10-o'clock box once I've seen a paper stamped 15." That way the slow "7 o'clock" paper still makes it in, and you only shut the box once you're sure the stragglers have arrived.
---

## Why this module

The first thing streaming gets wrong is treating "I saw a later timestamp" as "the earlier window is done." Those are not the same statement, because a stream is not sorted — a later event showing up tells you nothing about whether every earlier event has already arrived. The danger is that closing a window is irreversible: once you emit its result, an event that belonged in it has nowhere to go, so a close made a moment too early does not error or retry, it just quietly produces a number that is too low. The completeness decision has to be made on evidence about the stream's progress, not on the arrival of any single event.

When you aggregate a stream into time windows, you must decide when a window is finished so you can emit it. Events arrive out of order — an event that happened at time 7 can reach you after an event that happened at time 12 — so the moment you see an event timed 12, concluding the window covering 0..10 is done and emitting it is a guess, and the event timed 7 may not have arrived yet. If you closed the window on the first event past its end, that latecomer finds its window already emitted and is silently dropped, so the window's count is low by however many stragglers you cut off, and nothing errors.

A watermark makes the close decision explicit. It is a moving assertion about completeness — "no event earlier than time W will still arrive" — commonly computed as (the maximum event-time seen so far) − (an allowed_lateness bound). A window is closed only when the watermark passes its end, so an out-of-order event that arrives while the watermark is still behind the window's end is inside the window and counted; only an event later than the lateness bound is dropped, now an explicit, tunable decision. This module runs both close rules.

**Close an event-time window on a watermark — an assertion (max-seen minus an allowed-lateness bound) that no earlier event will still arrive — not on the arrival of the first event past the window's end, because streams are out of order, so an eager close silently drops the latecomers that still belong in the window.**

## Concepts

**The naive close emits a window the instant any event reaches its end**, so a later-arriving event for that window finds it already closed and is dropped.

```python filename=modules/orchestration-and-governance/code/watermark-inter-01/watermark.py:59-71 COMPLETE
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
```

**The watermark close holds a window open until the watermark (max-seen − allowed_lateness) passes its end**, so latecomers within the bound are still counted.

```python filename=modules/orchestration-and-governance/code/watermark-inter-01/watermark.py:74-88 COMPLETE
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
```

<svg role="img" aria-label="An event-time axis with a window boundary at 10; events arrive in the order 2, 5, 12, 7, 15, so the event at time 7 that belongs before the boundary arrives after the event at time 12 that is past it" viewBox="0 0 300 116" width="300" height="116">
  <text x="6" y="12" fill="var(--muted)" font-size="8">event-time axis — arrival order is out of order (…12 then 7…)</text>
  <line x1="20" y1="60" x2="280" y2="60" stroke="var(--grid)"/>
  <line x1="150" y1="40" x2="150" y2="80" stroke="var(--s2)"/><text x="128" y="34" fill="var(--s2)" font-size="6">window 0 end = 10</text>
  <text x="14" y="94" fill="var(--muted)" font-size="6">0</text><text x="272" y="94" fill="var(--muted)" font-size="6">20</text>
  <circle cx="46" cy="60" r="3" fill="var(--s1)"/><text x="40" y="52" fill="var(--muted)" font-size="6">2 (1st)</text>
  <circle cx="85" cy="60" r="3" fill="var(--s1)"/><text x="79" y="52" fill="var(--muted)" font-size="6">5 (2nd)</text>
  <circle cx="203" cy="60" r="3" fill="var(--muted)"/><text x="197" y="52" fill="var(--muted)" font-size="6">12 (3rd)</text>
  <circle cx="111" cy="72" r="3" fill="var(--s1)"/><text x="98" y="88" fill="var(--s1)" font-size="6">7 (4th — late!)</text>
  <circle cx="242" cy="60" r="3" fill="var(--muted)"/><text x="236" y="52" fill="var(--muted)" font-size="6">15 (5th)</text>
  <text x="20" y="110" fill="var(--muted)" font-size="6">event-time 7 belongs in window 0 but arrives 4th, after the 3rd event at 12</text>
</svg>
^ On the event-time axis, window 0 ends at 10 and truly contains the events at times 2, 5, and 7; but 7 arrives fourth, after the event at time 12 that is past the boundary — so any rule that closes window 0 when it first sees a time past 10 will have already emitted before 7 shows up.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/watermark-inter-01/watermark.py

The fixture is five events in arrival order, deliberately out of order in event-time, with a window size of 10 and allowed_lateness of 5.

```json filename=modules/orchestration-and-governance/code/watermark-inter-01/watermark.json:4-10 COMPLETE
  "events": [
    {"t": 2, "value": "a"},
    {"t": 5, "value": "b"},
    {"t": 12, "value": "c"},
    {"t": 7, "value": "d"},
    {"t": 15, "value": "e"}
  ]
```

Run `--windows`.

```text filename=--windows
WINDOWS — event-time windows of 10, allowed_lateness 5
------------------------------------------------------------------
  window     range      true   naive-close   watermark-close
  window 0   [0,10)     3      2             3
  window 1   [10,20)     2      2             2
------------------------------------------------------------------
  naive dropped:     [(7, 'd')]
  watermark dropped: []
```

Read window 0. It truly contains three events — times 2, 5, and 7, all in [0,10). The naive close reports 2, because when the event at time 12 arrived it declared window 0 finished (12 is past the end 10), emitted it with the two events seen so far, and then dropped the event at time 7 that arrived next — you can see it in the "naive dropped" line. The watermark close reports 3, the true count, and dropped nothing. The difference is one event's worth of data, silently missing from an aggregate that looked complete, and the only thing that changed is the rule for deciding when the window was done. Note that window 1 agrees at 2 in both — the disagreement is exactly at the window that had a straggler, which is why this class of bug is so easy to miss: most windows are fine, and only the ones that happened to receive a late event are quietly wrong.

## Build

The watermark is the running assertion that lets the stream hold window 0 open just long enough.

```text filename=--watermark
WATERMARK — max event-time seen, watermark = max - 5, and window-0 close status
--------------------------------------------------------------------------
  arrival  event    max-seen   watermark   window 0 [0,10) closeable?
  t=2      a (t=2)  2          -3          no, keep open
  t=5      b (t=5)  5          0           no, keep open
  t=12     c (t=12)  12         7           no, keep open
  t=7      d (t=7)  12         7           no, keep open
  t=15     e (t=15)  15         10          yes -> emit
```

Follow the watermark column down. After the event at time 12, the max event-time seen is 12, so the watermark is 12 − 5 = 7 — still below window 0's end of 10, so window 0 stays open. That is the crucial moment: the naive rule closed here, but the watermark says "I have only seen up to time 12 and I allow events to be up to 5 late, so I cannot yet be sure everything before time 10 has arrived." One row later the event at time 7 arrives, and because window 0 is still open, it is counted. Only at the final event (time 15) does the watermark reach 10, and now the stream emits window 0 — after the straggler is safely inside. The allowed_lateness of 5 is exactly the promise "events run at most 5 out of order," and it bought the extra time needed to catch the event that was 5 out of order. Set it to 0 and the watermark equals max-seen and you are back to the naive close; set it larger and you tolerate more disorder at the cost of holding every window open longer.

<svg role="img" aria-label="The watermark rising across five arrivals from -3 to 10; window 0's end line is at 10, and the late event at time 7 arrives at the fourth step while the watermark is still 7, before it reaches 10 and closes window 0" viewBox="0 0 300 116" width="300" height="116">
  <text x="6" y="12" fill="var(--muted)" font-size="8">watermark climbs to 10 only at the last event — after t=7 is counted</text>
  <line x1="30" y1="92" x2="285" y2="92" stroke="var(--grid)"/>
  <line x1="30" y1="92" x2="30" y2="26" stroke="var(--grid)"/>
  <line x1="30" y1="40" x2="285" y2="40" stroke="var(--s2)" stroke-dasharray="3 2"/><text x="210" y="36" fill="var(--s2)" font-size="6">window 0 end = 10</text>
  <text x="12" y="43" fill="var(--muted)" font-size="6">10</text>
  <polyline points="55,86 105,80 155,68 205,68 265,40" fill="none" stroke="var(--s1)"/>
  <circle cx="55" cy="86" r="2" fill="var(--s1)"/><text x="46" y="102" fill="var(--muted)" font-size="6">-3</text>
  <circle cx="105" cy="80" r="2" fill="var(--s1)"/><text x="100" y="102" fill="var(--muted)" font-size="6">0</text>
  <circle cx="155" cy="68" r="2" fill="var(--s1)"/><text x="150" y="102" fill="var(--muted)" font-size="6">7</text>
  <circle cx="205" cy="68" r="3" fill="var(--s2)"/><text x="182" y="60" fill="var(--s2)" font-size="6">t=7 arrives (wm still 7)</text>
  <circle cx="265" cy="40" r="2" fill="var(--s1)"/><text x="256" y="102" fill="var(--muted)" font-size="6">10→emit</text>
  <text x="34" y="113" fill="var(--muted)" font-size="6">arrivals:  2      5      12     7      15</text>
</svg>
^ The watermark rises −3 → 0 → 7 → 7 → 10 across the five arrivals; it stays at 7 (below the window-0 end of 10) when the late event at time 7 arrives, so window 0 is still open to count it, and only reaches 10 at the last event, closing window 0 after the straggler is in.

```python filename=modules/orchestration-and-governance/code/watermark-inter-01/watermark.py:139-144 COMPLETE
    true_w0 = truth[0]
    naive_undercounts = naive.get(0, 0) < true_w0
    print("  naive-close window 0 count = %d of a true %d -> undercounts = %s" % (naive.get(0, 0), true_w0, naive_undercounts))

    watermark_correct = wm.get(0, 0) == true_w0
    print("  watermark-close window 0 count = %d of a true %d -> correct = %s" % (wm.get(0, 0), true_w0, watermark_correct))
```

## Definition of done

The self-test pins the naive undercount, the watermark's correct count, and which rule dropped the late event.

```python filename=modules/orchestration-and-governance/code/watermark-inter-01/watermark.py:146-154 COMPLETE
    late = {"t": 7, "value": "d"}
    naive_dropped_late = late in nd
    print("  the naive close dropped the late event (t=7) = %s" % naive_dropped_late)

    watermark_kept_late = late not in wd
    print("  the watermark close kept the late event (t=7) = %s" % watermark_kept_late)

    counts_differ = naive.get(0, 0) != wm.get(0, 0)
    print("  the two closes disagree on window 0 = %s (%d vs %d)" % (counts_differ, naive.get(0, 0), wm.get(0, 0)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the naive close drops the out-of-order event and undercounts window 0; the watermark counts all three
------------------------------------------------------------------------------------------------------------------
  naive-close window 0 count = 2 of a true 3 -> undercounts = True
  watermark-close window 0 count = 3 of a true 3 -> correct = True
  the naive close dropped the late event (t=7) = True
  the watermark close kept the late event (t=7) = True
  the two closes disagree on window 0 = True (2 vs 3)
```

<svg role="img" aria-label="Window 0 count under three rules: true count 3, naive close 2, watermark close 3" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">window 0 [0,10) count: true 3, naive 2, watermark 3</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">true</text>
  <rect x="80" y="24" width="180" height="12" fill="none" stroke="var(--line)"/><rect x="80" y="24" width="180" height="12" fill="var(--grid)"/><text x="264" y="34" fill="var(--muted)" font-size="7">3</text>
  <text x="10" y="54" fill="var(--muted)" font-size="7">naive</text>
  <rect x="80" y="44" width="120" height="12" fill="var(--s2)"/><text x="204" y="54" fill="var(--muted)" font-size="7">2 (dropped t=7)</text>
  <text x="10" y="74" fill="var(--muted)" font-size="7">watermark</text>
  <rect x="80" y="64" width="180" height="12" fill="var(--s1)"/><text x="264" y="74" fill="var(--muted)" font-size="7">3</text>
  <text x="10" y="90" fill="var(--muted)" font-size="6">the naive close is short by exactly the one straggler it cut off</text>
</svg>
^ Window 0's true count is 3; the naive close reports 2 because it emitted before the late event at time 7 arrived, while the watermark close matches the truth at 3 — the missing bar is exactly the straggler an eager close discards.

**Done means the close decision is proven on real events: window 0 [0,10) truly holds 3 events, the naive close emits it with 2 and drops the late event at time 7, and the watermark close (allowed_lateness 5) holds it open until the watermark reaches 10 and counts all 3 — so a stream window must close on a watermark asserting no earlier event will arrive, not on the first event past its end.**

## Boss fight

Predict two ways the watermark itself is set wrong, because it is a promise about the stream, and a promise that is too tight or too loose fails in opposite directions.

The first trap is that allowed_lateness is a bet, and a real straggler beyond the bound is still dropped — the watermark does not eliminate late-data loss, it only sets the threshold for it. If you promise events are at most 5 out of order and one arrives 8 out of order, the watermark will have already passed its window and the event is dropped exactly as in the naive case; the watermark bought tolerance up to 5, not forever. So the honest design has three parts, not one: pick allowed_lateness from the observed lateness distribution (say the 99th percentile of how late events actually run), decide explicitly what happens to the events beyond it (drop and count them as a monitored "late records dropped" metric, or route them to a side output / late-data path for a correction), and accept that there is no setting that both emits promptly and never drops — that trade-off is the whole point of the knob. A watermark that silently drops beyond-bound events without a metric is just the naive bug with extra latency.

The second trap is deriving the watermark wrongly so it advances when it should not, or never advances at all. Because the common formula keys off the max event-time seen, a single event with a corrupted far-future timestamp (a client with a wrong clock stamping year 2099) jumps the watermark far ahead and instantly closes every open window, dropping all their legitimate stragglers — so the watermark generator must be robust to outliers (clamp or ignore implausible timestamps, or derive the watermark per-source and take the minimum across sources). The mirror failure is a stream that goes idle or has one stalled partition: if the watermark is the minimum across input partitions and one partition stops sending, its contribution never advances, so the overall watermark freezes and no window ever closes — results stop emitting entirely. Real systems handle this with an idle-timeout that lets a quiet partition stop holding the watermark back. The watermark is only as good as the timestamps and the progress signal it is built from: too-trusting of a bad clock and it closes everything early; too-strict on a stalled source and it closes nothing.

**A watermark sets the threshold for late-data loss, it does not remove it: pick allowed_lateness from the real lateness distribution, and give beyond-bound events an explicit fate (a monitored drop metric or a late-data side path), because there is no setting that both emits promptly and never drops. And guard the watermark's derivation — a single bad far-future timestamp can jump it ahead and close every window early, while one stalled input partition can freeze it so nothing ever closes, so clamp implausible timestamps, take the minimum across sources, and idle-timeout quiet partitions.**

## External resources

The Dataflow/Beam model papers and documentation (Akidau et al., "The Dataflow Model," and "Streaming 101/102") — event-time versus processing-time, watermarks as a completeness signal, allowed lateness, triggers, and late-data handling.

Documentation for stream processors (Apache Flink, Kafka Streams, Spark Structured Streaming) — how watermarks are configured, how out-of-order and late events are counted or dropped, and the per-partition/idle-source watermark subtleties this module's boss fight warns about.

The companion logical-clock and vector-clock modules in this topic — all three concern ordering events without trusting wall-clock arrival order; a watermark is the streaming counterpart, turning "when has enough of event-time passed?" into an explicit, tunable assertion.
