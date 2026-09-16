---
id: spancontext-inter-01
title: Propagate span context to reconstruct the call tree — a flat correlation id groups the logs but can't tell you which hop was slow
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: A correlation id stamped on every log line groups all the events of one request, which beats an unlabeled jumble, but it is flat: it says these events belong together and nothing about their structure — not which service called which, and not where the time went. Where the time went is the incident question, and a flat id cannot answer it, because span durations nest. A parent span's duration already contains its children's: the gateway is busy for the whole request while it waits on the database, which is busy while it waits on the cache. So summing durations to find the total work double-counts the nested time and yields a number larger than the request's wall-clock time, and picking the span with the largest total duration as the bottleneck usually picks a caller that is mostly waiting — often the root itself. The fix is span context: give each span its own id and record its parent's id, so the collector rebuilds the call tree from the parent pointers and computes each span's self-time — its own duration minus the time inside its children — which attributes every slice of wall-clock time to exactly one span. On a fixture where the gateway (100ms) contains auth (20ms) and the database (60ms), and the database contains the cache (50ms), summing durations gives a meaningless 230ms, the largest-duration span is the gateway (the whole request), but the largest self-time is the cache at 50ms — the real hotspot, while the database's 60ms is 50ms of waiting and only 10ms of its own work.
eli5: Imagine a manager who asks four people to help with one job and wants to know who is the slow link. If she just writes down how long each person was involved, the boss who oversaw the whole thing was "involved" for the entire hour, and the worker who handed the job to someone else was "involved" the whole time he waited — so the totals overlap and add up to more than the hour the job actually took, and the person who looks busiest is really just the one who waited the longest. What she needs is a chart of who asked whom, so she can figure out each person's own working time — the time they were doing their part and not just waiting on someone below them. Then the real slow link stands out. Tagging every note with the same job number groups the notes but doesn't draw that chart; recording who each person was waiting on does.
---

## Why this module

The first fix for debugging concurrent requests is a correlation id: stamp every log line of a request with the same id, so that when a thousand requests interleave in the log you can still pull one request's story out of the jumble. A neighboring module makes exactly that case, and it is right — a correlation id is the difference between a readable trace and noise.

But a correlation id is flat. It answers "which lines belong to this request" and stops there. It does not record which service called which, so you cannot see the shape of the request, and — the part that bites during an incident — it cannot tell you where the time went, because the one thing you most want to measure, latency, does not add up the way a flat list invites you to add it.

The reason is nesting. In a request that fans out, a caller's span lasts as long as everything it waits for. The gateway's span covers the whole request; the database's span covers its own query plus the cache lookup it waits on. Those durations overlap by construction, so summing them counts the same wall-clock milliseconds several times, and the span that lasted longest is usually the one that waited longest — not the one doing the slow work. To find the real hotspot you need the structure a flat id threw away.

<svg role="img" aria-label="A timeline from 0 to 100ms with four overlapping span bars stacked vertically: gateway spans the whole 0 to 100, auth a short bar near the start, database from 30 to 90, and cache nested inside the database from 32 to 82. The overlap shows why summing the four durations exceeds the 100ms wall-clock." viewBox="0 0 440 150">
<line x1="70" y1="120" x2="410" y2="120" stroke="var(--line)"/>
<text x="70" y="134" fill="var(--muted)" font-size="8" text-anchor="middle">0ms</text>
<text x="410" y="134" fill="var(--muted)" font-size="8" text-anchor="middle">100ms wall-clock</text>
<text x="66" y="42" fill="var(--ink)" font-size="8" text-anchor="end">gateway</text>
<rect x="70" y="34" width="340" height="12" fill="var(--s2)"/>
<text x="66" y="62" fill="var(--ink)" font-size="8" text-anchor="end">auth</text>
<rect x="87" y="54" width="68" height="12" fill="var(--s2)"/>
<text x="66" y="82" fill="var(--ink)" font-size="8" text-anchor="end">database</text>
<rect x="172" y="74" width="204" height="12" fill="var(--s2)"/>
<text x="66" y="102" fill="var(--ink)" font-size="8" text-anchor="end">cache</text>
<rect x="179" y="94" width="170" height="12" fill="var(--s2)"/>
<text x="200" y="16" fill="var(--muted)" font-size="8" text-anchor="middle">100 + 20 + 60 + 50 = 230ms of overlapping bars in 100ms</text>
</svg>
^ The four spans overlap in time — the gateway covers the whole request, the cache is nested inside the database — so their durations sum to 230ms across only 100ms of wall-clock: the double-counting a flat sum cannot avoid.

**A correlation id groups a request's log lines but records no structure, and span durations nest — so you cannot sum them into a meaningful total or trust the longest span as the bottleneck; the caller that waits longest looks busiest.**

## Concepts

Span context is the structure a trace needs. Every unit of work is a span, and a span carries three ids: a trace id shared by every span in the request (the correlation id's job), the span's own id, and its parent span's id — the span of the work that called it. The parent pointer is the new information, and it is enough to rebuild the entire call tree at the collector: the root is the span with no parent, and every other span hangs off the span its parent id names.

Propagating that context is the operational work. When a service calls another, it passes the current trace id and its own span id along — in HTTP headers, in the message envelope — and the callee starts a new span whose parent is the caller's span. Drop the propagation at any hop and the subtree below it detaches: it either becomes a second root (a broken, orphaned trace) or is lost, which is why "the trace just stops at service X" is the classic symptom of a hop that forgot to forward the headers.

<svg role="img" aria-label="On the left a flat list of four spans each tagged with the same request id, with no lines connecting them. On the right the same four spans arranged as a tree: gateway at the root, auth and database as its children, and cache under the database." viewBox="0 0 440 165">
<text x="105" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">flat correlation id</text>
<rect x="40" y="30" width="130" height="16" fill="var(--panel)" stroke="var(--line)"/>
<text x="105" y="42" fill="var(--ink)" font-size="8" text-anchor="middle">gateway  req#42</text>
<rect x="40" y="52" width="130" height="16" fill="var(--panel)" stroke="var(--line)"/>
<text x="105" y="64" fill="var(--ink)" font-size="8" text-anchor="middle">auth  req#42</text>
<rect x="40" y="74" width="130" height="16" fill="var(--panel)" stroke="var(--line)"/>
<text x="105" y="86" fill="var(--ink)" font-size="8" text-anchor="middle">database  req#42</text>
<rect x="40" y="96" width="130" height="16" fill="var(--panel)" stroke="var(--line)"/>
<text x="105" y="108" fill="var(--ink)" font-size="8" text-anchor="middle">cache  req#42</text>
<text x="105" y="130" fill="var(--muted)" font-size="8" text-anchor="middle">grouped, but no structure</text>
<text x="335" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">span context (parent ids)</text>
<rect x="290" y="30" width="90" height="16" fill="var(--panel)" stroke="var(--s1)"/>
<text x="335" y="42" fill="var(--ink)" font-size="8" text-anchor="middle">gateway</text>
<line x1="335" y1="46" x2="305" y2="66" stroke="var(--line)"/>
<line x1="335" y1="46" x2="365" y2="66" stroke="var(--line)"/>
<rect x="270" y="66" width="70" height="16" fill="var(--panel)" stroke="var(--s1)"/>
<text x="305" y="78" fill="var(--ink)" font-size="8" text-anchor="middle">auth</text>
<rect x="345" y="66" width="80" height="16" fill="var(--panel)" stroke="var(--s1)"/>
<text x="385" y="78" fill="var(--ink)" font-size="8" text-anchor="middle">database</text>
<line x1="385" y1="82" x2="385" y2="102" stroke="var(--line)"/>
<rect x="350" y="102" width="70" height="16" fill="var(--panel)" stroke="var(--s1)"/>
<text x="385" y="114" fill="var(--ink)" font-size="8" text-anchor="middle">cache</text>
<text x="335" y="140" fill="var(--muted)" font-size="8" text-anchor="middle">the call tree, rebuilt</text>
</svg>
^ The same four spans: a flat correlation id groups them with no relationships; parent ids let the collector rebuild the call tree and see who called whom.

With the tree in hand, the measurement that matters is self-time: a span's own duration minus the durations of its direct children. The children's time is nested inside the parent, so subtracting it leaves only the milliseconds the parent itself was working rather than waiting. Self-times partition the request cleanly — each slice of wall-clock time belongs to exactly one span — so they sum to the request's wall-clock duration, not to some inflated total, and the span with the largest self-time is the real bottleneck.

This is why total duration misleads and self-time does not. The root span always has the largest total duration — it is the whole request — but its self-time is only the orchestration it does itself. A caller that spends its time blocked on a slow dependency has a large duration and a small self-time; the dependency it waited on is where the self-time, and the fix, actually lives.

**Give each span a parent id so the collector rebuilds the call tree, then rank by self-time — duration minus children — which attributes each millisecond to one span, sums to wall-clock time, and points at the span actually doing the slow work rather than the one waiting on it.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/spancontext-inter-01. The fixture is one request's spans, each with its own id, its parent's id, the service, and a duration.

```json filename=modules/ship-and-operate/code/spancontext-inter-01/spancontext.json:4-7 COMPLETE
    {"span_id": 1, "parent_id": null, "service": "gateway", "start_ms": 0, "duration_ms": 100},
    {"span_id": 2, "parent_id": 1, "service": "auth", "start_ms": 5, "duration_ms": 20},
    {"span_id": 3, "parent_id": 1, "service": "database", "start_ms": 30, "duration_ms": 60},
    {"span_id": 4, "parent_id": 3, "service": "cache", "start_ms": 32, "duration_ms": 50}
```

The flat view's idea of total work is to sum every span's duration — the operation nesting makes meaningless.

```python filename=modules/ship-and-operate/code/spancontext-inter-01/spancontext.py:36-38 COMPLETE
def flat_duration_sum(spans):
    """The naive 'total work': sum every span's duration -- double-counts nested time."""
    return sum(s["duration_ms"] for s in spans)
```

Self-time subtracts the direct children's durations, which nest inside the span, leaving only its own work.

```python filename=modules/ship-and-operate/code/spancontext-inter-01/spancontext.py:45-47 COMPLETE
def self_time(spans, span):
    """A span's own time: its duration minus the durations of its direct children (which nest inside it)."""
    return span["duration_ms"] - sum(c["duration_ms"] for c in children_of(spans, span["span_id"]))
```

The two bottleneck picks differ only in what they rank by — total duration versus self-time.

```python filename=modules/ship-and-operate/code/spancontext-inter-01/spancontext.py:50-57 COMPLETE
def bottleneck_by_duration(spans):
    """The naive pick: the span with the largest total duration."""
    return max(spans, key=lambda s: s["duration_ms"])


def bottleneck_by_self_time(spans):
    """The real pick: the span with the largest self-time."""
    return max(spans, key=lambda s: self_time(spans, s))
```

Before running it, predict: the request took 100ms wall-clock, so any "total work" larger than 100 is double-counted, and the largest-duration span will be the gateway — the whole request. Run `--flat`:

```text filename=spancontext.py --flat
FLAT — the correlation-id view: every span shares the request, no structure
------------------------------------------------------------
  span 1  gateway   duration 100ms
  span 2  auth      duration 20ms
  span 3  database  duration 60ms
  span 4  cache     duration 50ms
------------------------------------------------------------
  summed durations = 230ms, but the request took 100ms wall-clock
  largest-duration span = gateway (100ms) -- the naive bottleneck
```

The prediction holds. The durations sum to 230ms for a request that took 100ms — the flat view triple-counts the milliseconds where gateway, database, and cache were all "busy" at once. And the largest-duration span is the gateway, which is useless as a bottleneck: the gateway is the entrypoint, so of course it lasts the whole request. A flat id gives you exactly these two dead ends.

Now rebuild the tree and rank by self-time. Run `--tree`:

```text filename=spancontext.py --tree
TREE — the span-context view: the call tree and each span's self-time
------------------------------------------------------------
  gateway   total 100ms   self 20ms
    auth      total 20ms   self 20ms
    database  total 60ms   self 10ms
      cache     total 50ms   self 50ms
------------------------------------------------------------
  self-times sum to 100ms = wall-clock; real bottleneck = cache (self 50ms)
```

The tree tells the true story. The database has the largest duration after the root, 60ms, so the flat view would send you to optimize the database — but its self-time is only 10ms: it spends 50 of its 60ms waiting on the cache. The cache's self-time is 50ms, the largest of any span, and it is the real hotspot. The self-times — 20, 20, 10, 50 — sum to exactly 100ms, the wall-clock time, because each millisecond of the request now belongs to exactly one span.

<svg role="img" aria-label="A bar for each span split into self-time and waiting-on-children. Gateway 100ms is mostly waiting with 20ms self. Database 60ms is mostly waiting with 10ms self. Cache 50ms is entirely self-time. A note marks cache as the largest self-time." viewBox="0 0 440 155">
<text x="20" y="16" fill="var(--muted)" font-size="9">solid = self-time, dashed = waiting on children</text>
<text x="70" y="42" fill="var(--ink)" font-size="8" text-anchor="end">gateway</text>
<rect x="75" y="32" width="40" height="14" fill="var(--s1)"/>
<rect x="115" y="32" width="160" height="14" fill="var(--panel)" stroke="var(--line)" stroke-dasharray="3 3"/>
<text x="70" y="66" fill="var(--ink)" font-size="8" text-anchor="end">auth</text>
<rect x="75" y="56" width="40" height="14" fill="var(--s1)"/>
<text x="70" y="90" fill="var(--ink)" font-size="8" text-anchor="end">database</text>
<rect x="75" y="80" width="20" height="14" fill="var(--s1)"/>
<rect x="95" y="80" width="100" height="14" fill="var(--panel)" stroke="var(--line)" stroke-dasharray="3 3"/>
<text x="70" y="114" fill="var(--ink)" font-size="8" text-anchor="end">cache</text>
<rect x="75" y="104" width="100" height="14" fill="var(--s2)"/>
<text x="180" y="114" fill="var(--s2)" font-size="8">largest self-time — the real hotspot</text>
<text x="75" y="140" fill="var(--muted)" font-size="8">0ms scale to 100ms wall-clock</text>
</svg>
^ Each span's self-time (solid) versus time waiting on children (dashed): the gateway and database are mostly waiting, and the cache's bar is all self-time — the bottleneck the durations hid.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that the flat duration sum exceeds wall-clock time, that the self-times sum exactly to wall-clock time, that the duration bottleneck and the self-time bottleneck disagree, that the duration pick is mostly waiting, and that the tree is well-formed.

```python filename=modules/ship-and-operate/code/spancontext-inter-01/spancontext.py:101-116 COMPLETE
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
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the self-times ever stopped summing to wall-clock or the two bottleneck picks ever agreed:

```text filename=spancontext.py --check
SELF-TEST — the flat view double-counts and blames the wrong span; the tree attributes time exactly once and finds the real hotspot
----------------------------------------------------------------------------------------------------------------
  flat duration sum exceeds wall-clock (double-counts nesting) = True (230ms > 100ms)
  self-times sum exactly to wall-clock = True (100ms)
  duration bottleneck and self-time bottleneck disagree = True (gateway vs cache)
  the duration bottleneck is mostly waiting = True (self 20ms < 50ms)
  the tree is well-formed (one root, every parent resolves) = True
```

**The self-test pins the mechanism, not just the answer: it asserts the self-times sum exactly to wall-clock — the property that makes self-time a real attribution — and that the naive duration pick is mostly waiting, so a pass certifies the flat metric fails for the stated reason rather than by coincidence.**

## Definition of done

You can explain why a correlation id groups a request's logs but records no structure.
You can explain why span durations nest and why summing them double-counts wall-clock time.
You can define span context — trace id, span id, parent id — and how the collector rebuilds the call tree from it.
You can define self-time and explain why self-times partition the request and sum to its wall-clock duration.
You can explain why the largest-duration span (often the root) misleads and why the largest self-time span is the real bottleneck.

## Boss fight

Suppose the trace shows the cache at 50ms of self-time, but you also notice the request's wall-clock time is 100ms while the sum of the root's direct children is only 80ms (auth 20 plus database 60). Reason about the missing 20ms. That gap is the gateway's own self-time — real orchestration work it does outside its children — but it could also hide a subtler thing the simple nested model misses: whether the children ran in parallel or in series. Self-time as duration-minus-children assumes children nest cleanly inside the parent; when siblings overlap in time (auth and database running concurrently), the parent's self-time computed by subtraction can understate or misattribute, and the true critical path is the longest chain of spans by start and end time, not the largest single self-time. The honest version uses the spans' start and end timestamps to compute the critical path, and treats self-time as an approximation that is exact only when children do not overlap. The lesson: the tree gives you structure, but latency attribution in the presence of concurrency needs the timestamps, not just the durations.

Now the trap that silently corrupts every trace: sampling and clock skew. Traces are almost always sampled — you keep a fraction of requests to bound cost — and the sampling decision must be made once at the root and propagated, so that either all spans of a request are kept or none are; if each service decides independently, you get partial traces with holes that look exactly like a dropped-propagation bug. And span timestamps come from different machines whose clocks differ by milliseconds, so a child can appear to start before its parent or end after it; robust tracing clamps children to their parent's bounds or relies on relative durations rather than cross-host absolute times. Propagating the span context is necessary but not sufficient — you must also propagate the sampling decision and distrust cross-host timestamps.

**Self-time is exact only when children do not overlap; with concurrency, compute the critical path from start and end timestamps — and because traces are sampled and clocks skew across hosts, propagate one root sampling decision to every span and distrust cross-host absolute timestamps.**

## External resources

The OpenTelemetry tracing specification defines span context — trace id, span id, parent — and context propagation across process boundaries via headers like traceparent (the W3C Trace Context standard).
Google's Dapper paper (Sigelman et al., 2010) is the origin of this model: per-request trace trees built from propagated span context, with sampling to bound overhead.
The topic's own module on stamping every log line with a correlation id covers the flat grouping this one builds on; a distributed tracing UI such as Jaeger or Zipkin renders the self-time and critical-path views described here.
