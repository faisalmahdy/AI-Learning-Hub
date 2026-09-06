---
id: ship-inter-24
title: Count requests in a sliding window — or a fixed-window rate limiter lets a double burst through at the boundary
topic: ship-and-operate
level: intermediate
status: ready
time: 17 min
summary: A rate limiter promises no more than a limit of requests per window. The simplest implementation counts requests in fixed calendar buckets and resets the counter to zero at each boundary — cheap, one counter on a timer, but the reset is a loophole. A client sends the full limit at the very end of one bucket, then, a fraction of a second later when the boundary flips and the counter resets, sends the full limit again at the start of the next, so twice the limit lands in a span shorter than one window and the peak rate is double what you configured. A sliding window closes it by counting requests in the trailing window up to each request: there is no boundary to straddle, because the first burst is still inside the trailing window when the second arrives, so it still counts and the second is rejected. On a limit of 5 per 10 seconds with five requests at t=9 and five at t=10, the fixed window admits all 10 (2× the limit in one second) while the sliding window admits 5.
eli5: Imagine a ride that allows five people per hour, and the gatekeeper wipes the tally clean exactly on the hour. Five people rush in at 1:59, the tally resets at 2:00, and five more rush in at 2:01 — ten people in two minutes, twice what was meant. A smarter gatekeeper instead checks "how many got in during the last sixty minutes" at each arrival, so the 1:59 group still counts at 2:01 and the second rush is turned away. Counting the rolling last-hour beats wiping the tally on the hour.
---

## Why this module

A rate limit is supposed to bound the peak rate, but counting in fixed buckets that reset on a boundary bounds only the per-bucket average, and a client aiming at the boundary can push the instantaneous rate to double the limit.

The obvious way to limit requests to a rate is to count them in fixed windows: divide time into buckets of length W, keep a counter per bucket, admit while the counter is under the limit, and reset the counter to zero when the bucket rolls over. It is minimal — one integer, reset on a timer — and it looks correct, because within any single bucket you never admit more than the limit. But the guarantee is per bucket, not per any window of length W, and those are different. A client sends the full limit in the last instant of bucket k, the boundary flips and the counter resets, and the client sends the full limit again in the first instant of bucket k+1. Two full limits land within a span far shorter than one window, so the actual peak rate over that span is twice the configured limit. The limiter enforced the average across each fixed bucket while permitting a 2× spike straddling the boundary, and an adversary — or just a synchronized client fleet — will hit exactly that seam.

**A fixed-window limiter bounds the count per calendar bucket, not per rolling window, so a client can send the full limit at the end of one bucket and again at the start of the next, doubling the peak rate the limit was meant to cap.**

A sliding window fixes it by asking a different question at each request: how many requests were admitted in the trailing W seconds up to now, not in the current fixed bucket. There is no boundary to exploit, because the trailing window moves with every request — when the second burst arrives, the first burst has not yet aged out of the trailing window, so it still counts, the limit is already reached, and the second burst is rejected. The rate holds at every instant, not just per bucket. This module runs both limiters against a boundary-straddling burst and shows the fixed window admit double while the sliding window holds the line.

## Concepts

The **limit and window** are the promise: at most `limit` requests per `window` seconds. The question is *which* window — a fixed calendar bucket, or a rolling one.

A **fixed-window limiter** counts requests in buckets `[0, W)`, `[W, 2W)`, … and resets at each boundary. Cheap, but it bounds the per-bucket count, not the rolling rate.

The **boundary loophole** is the flaw: the full limit at the end of one bucket plus the full limit at the start of the next puts `2 × limit` requests in a span shorter than one window.

```python filename=modules/ship-and-operate/code/ship-inter-24/ratelimit.py:43-51 COMPLETE
def fixed_window(requests, limit, window):
    """Admit if the fixed calendar bucket [k*window, (k+1)*window) holds fewer than `limit` so far."""
    counts, admitted = {}, []
    for t in requests:
        bucket = t // window
        if counts.get(bucket, 0) < limit:
            counts[bucket] = counts.get(bucket, 0) + 1
            admitted.append(t)
    return admitted
```

A **sliding-window limiter** counts requests in the trailing `window` seconds up to each request, so the window moves and there is no boundary to straddle.

**The bound holds at every instant.** Because the trailing window includes the recent past, the limit-per-window guarantee is true continuously, not only per calendar bucket.

**A fixed window enforces the average per bucket while leaking a 2× peak at the boundary; a sliding window enforces the limit over every rolling window, at the cost of remembering recent timestamps instead of one counter.**

<svg role="img" aria-label="A fixed window resets its counter at the boundary, so a full burst just before and just after the reset both fit; a rolling window spans the boundary and catches both" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">counter resets at the boundary (fixed) vs rolls (sliding)</text>
  <line x1="150" y1="22" x2="150" y2="70" stroke="var(--ink)" stroke-width="1" stroke-dasharray="3 2"/><text x="126" y="20" fill="var(--muted)" font-size="7">boundary</text>
  <rect x="30" y="30" width="115" height="14" fill="var(--s2)" opacity="0.5"/><text x="60" y="40" fill="var(--muted)" font-size="7">bucket k (count→5)</text>
  <rect x="155" y="30" width="115" height="14" fill="var(--s2)" opacity="0.5"/><text x="185" y="40" fill="var(--muted)" font-size="7">bucket k+1 (reset→5)</text>
  <rect x="95" y="52" width="115" height="14" fill="none" stroke="var(--s1)" stroke-width="1.5"/><text x="112" y="62" fill="var(--s1)" font-size="7">rolling window spans it</text>
  <text x="20" y="90" fill="var(--muted)" font-size="8">the reset splits one burst across two buckets; the rolling window sees both together</text>
</svg>
^ The fixed buckets meet at the boundary and each accept a full limit, so the two bursts sit in adjacent buckets; a rolling window straddles the boundary and counts both bursts against one limit.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/ship-inter-24/ratelimit.py

The fixture is a limit, a window, and a burst arranged to straddle the boundary.

```json filename=modules/ship-and-operate/code/ship-inter-24/ratelimit.json:1-6 COMPLETE
{
  "_meta": "A rate limiter is meant to cap requests at `limit` per window of `window` seconds. A FIXED-WINDOW limiter counts requests in fixed calendar buckets [0,W), [W,2W), ... and resets the count to zero at each boundary. That reset is the flaw: a client can send the full limit at the very END of one bucket and the full limit again at the very START of the next, so 2*limit requests land in a span shorter than one window -- double the rate the limit was supposed to enforce. A SLIDING-WINDOW limiter instead counts requests in the trailing `window` seconds up to each request, so there is no boundary to exploit: the burst at the end of the old window is still inside the trailing window when the new requests arrive, so they are rejected. requests is the arrival times (seconds); this schedule clusters `limit` requests just before the boundary at W and `limit` more just after it.",
  "limit": 5,
  "window": 10,
  "requests": [9, 9, 9, 9, 9, 10, 10, 10, 10, 10]
}
```

Run `--admit` to see how many each limiter admits and the peak rate.

```text filename=--admit
ADMIT — requests admitted (limit 5 per 10s), 10 arrivals at the boundary
--------------------------------------------------------------
  fixed window:    admitted 10   peak in one window: 10   (2x the limit)
  sliding window:  admitted 5   peak in one window: 5   (at the limit)
--------------------------------------------------------------
  the fixed window's reset lets a second full burst through; the sliding window does not.
```

Five requests arrive at t=9 — the end of the first 10-second bucket — and five at t=10, the start of the second. The fixed-window limiter admits all five at t=9 (bucket 0's count goes 0 to 5) and then, because t=10 falls in bucket 1 whose counter just reset to zero, admits all five again. Ten requests in a one-second span, twice the limit of 5, exactly across the boundary. The sliding-window limiter admits the first five at t=9, but at t=10 it looks back over the trailing 10 seconds, sees those five still inside the window, finds the limit already reached, and rejects all five of the second burst. Same requests, same limit; only the fixed window's reset let the peak double.

<svg role="img" aria-label="The fixed window admits 5 at t=9 and 5 at t=10 for 10 total; the sliding window admits 5 at t=9 and rejects the 5 at t=10" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">admitted requests around the boundary at t=10 (limit 5)</text>
  <text x="8" y="36" fill="var(--s2)" font-size="8">fixed</text>
  <rect x="55" y="26" width="90" height="16" fill="var(--s2)"/><text x="60" y="38" fill="var(--panel)" font-size="8">5 at t=9</text>
  <rect x="147" y="26" width="90" height="16" fill="var(--s2)"/><text x="152" y="38" fill="var(--panel)" font-size="8">5 at t=10</text>
  <text x="242" y="38" fill="var(--s2)" font-size="7">10 = 2x</text>
  <text x="8" y="72" fill="var(--s1)" font-size="8">sliding</text>
  <rect x="55" y="62" width="90" height="16" fill="var(--s1)"/><text x="60" y="74" fill="var(--panel)" font-size="8">5 at t=9</text>
  <rect x="147" y="62" width="90" height="16" fill="none" stroke="var(--grid)" stroke-dasharray="3 2"/><text x="152" y="74" fill="var(--muted)" font-size="8">5 rejected</text>
  <text x="242" y="74" fill="var(--s1)" font-size="7">5 = limit</text>
  <line x1="147" y1="20" x2="147" y2="84" stroke="var(--ink)" stroke-width="1" stroke-dasharray="2 2"/><text x="150" y="98" fill="var(--muted)" font-size="7">boundary</text>
  <text x="30" y="106" fill="var(--muted)" font-size="8">the fixed window's second batch is admitted; the sliding window rejects it</text>
</svg>
^ Both admit the first five at the bucket's end; the fixed window then admits five more past the reset (2× the limit), while the sliding window rejects them because they are still inside its trailing window.

## Build

The sliding limiter admits a request only if the trailing-window count is still under the limit.

```python filename=modules/ship-and-operate/code/ship-inter-24/ratelimit.py:54-61 COMPLETE
def sliding_window(requests, limit, window):
    """Admit if the trailing `window` seconds up to t hold fewer than `limit` already-admitted requests."""
    admitted = []
    for t in requests:
        in_window = [a for a in admitted if t - window < a <= t]
        if len(in_window) < limit:
            admitted.append(t)
    return admitted
```

Why does the sliding window reject the second burst? Run `--window`.

```text filename=--window
WINDOW — what the sliding limiter sees when the second burst arrives at t=10
--------------------------------------------------------------
  admitted in the trailing 10 seconds (0, 10]: 5
  limit: 5  ->  the trailing window is already full, so the second burst is rejected
```

When the second burst arrives at t=10, the sliding limiter counts admitted requests in the trailing 10 seconds — the span (0, 10]. The five requests admitted at t=9 fall inside that span; they were admitted only one second ago and have not aged out. So the trailing count is already 5, equal to the limit, and every request in the second burst is rejected. The fixed window could not see this because its bucket boundary at t=10 threw away the memory of t=9's requests; the sliding window keeps that memory for a full window and only forgets a request once it is genuinely more than W seconds old. The whole difference is whether "the window" is anchored to the clock (and resets) or anchored to now (and rolls) — and only the rolling one bounds the rate the limiter claims to bound.

<svg role="img" aria-label="At t=10 the trailing 10-second window still contains the five requests from t=9, so the count is already at the limit" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">trailing window (0,10] at the moment t=10</text>
  <rect x="30" y="30" width="220" height="24" fill="none" stroke="var(--s1)" stroke-width="1"/><text x="34" y="26" fill="var(--s1)" font-size="7">trailing 10s window</text>
  <circle cx="210" cy="42" r="3" fill="var(--s1)"/><circle cx="214" cy="42" r="3" fill="var(--s1)"/><circle cx="218" cy="42" r="3" fill="var(--s1)"/><circle cx="222" cy="42" r="3" fill="var(--s1)"/><circle cx="226" cy="42" r="3" fill="var(--s1)"/>
  <text x="196" y="68" fill="var(--muted)" font-size="7">5 from t=9 (still inside)</text>
  <line x1="250" y1="24" x2="250" y2="60" stroke="var(--ink)" stroke-width="1" stroke-dasharray="2 2"/><text x="240" y="72" fill="var(--muted)" font-size="7">now t=10</text>
  <text x="30" y="90" fill="var(--muted)" font-size="8">count in the window = 5 = limit → the second burst is rejected</text>
</svg>
^ At t=10 the five t=9 requests are still inside the trailing window, so the count already equals the limit and the second burst cannot get in.

## Definition of done

The self-test pins it: the fixed window admits twice the limit and its peak exceeds the limit, the sliding window admits exactly the limit and never exceeds it, and both admit the first burst.

```python filename=modules/ship-and-operate/code/ship-inter-24/ratelimit.py:103-116 COMPLETE
    fixed_admits_double = len(fx) == 2 * limit
    print("  the fixed window admits twice the limit = %s (%d = 2*%d)" % (fixed_admits_double, len(fx), limit))

    fixed_peak_exceeds = peak_in_any_window(fx, w) > limit
    print("  the fixed window's peak rate exceeds the limit = %s (%d > %d in one window)" % (fixed_peak_exceeds, peak_in_any_window(fx, w), limit))

    sliding_admits_limit = len(sl) == limit
    print("  the sliding window admits exactly the limit = %s (%d)" % (sliding_admits_limit, len(sl)))

    sliding_peak_within = peak_in_any_window(sl, w) <= limit
    print("  the sliding window never exceeds the limit in any window = %s (%d <= %d)" % (sliding_peak_within, peak_in_any_window(sl, w), limit))

    both_admit_first_burst = len([t for t in fx if t == 9]) == limit and len([t for t in sl if t == 9]) == limit
    print("  both admit the first burst at the window's end = %s" % both_admit_first_burst)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the fixed window admits 2x the limit at the boundary; the sliding window holds the limit
--------------------------------------------------------------------------------------------------------
  the fixed window admits twice the limit = True (10 = 2*5)
  the fixed window's peak rate exceeds the limit = True (10 > 5 in one window)
  the sliding window admits exactly the limit = True (5)
  the sliding window never exceeds the limit in any window = True (5 <= 5)
  both admit the first burst at the window's end = True
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  fixed_admits_double=True  fixed_peak_exceeds=True  sliding_admits_limit=True  sliding_peak_within=True  both_admit_first_burst=True
```

**Done means the boundary loophole and its fix are proven: the fixed window admits 10 requests (2× the limit of 5) with a peak of 10 in one window, while the sliding window admits exactly 5 and never exceeds the limit in any trailing window — both admitting the first burst, differing only on the second.**

## Boss fight

The sliding window held the limit but had to remember timestamps. Predict its cost at scale, and the middle-ground limiters that approximate it. It is tempting to store every request's exact timestamp.

An exact sliding-window log keeps a timestamp for every request in the window, so memory grows with the request rate — at millions of requests per second that log is enormous, and evicting aged-out entries on every request adds work. That cost is why production systems rarely use the exact log and instead approximate it. The sliding-window *counter* keeps just two fixed-window counters (the current bucket and the previous one) and estimates the trailing count by weighting the previous bucket by how much of it still overlaps the trailing window — a single subtraction, O(1) memory, and it removes almost all of the fixed window's 2× spike while costing nothing near the log's memory. The token bucket, meanwhile, tracks one number (available tokens, refilled at the rate) and naturally smooths bursts. So the real design space is not "fixed versus exact sliding" but a spectrum of approximations trading accuracy for memory, and the sliding-window counter is the usual sweet spot.

The deeper point is what a rate limit is actually protecting, because that decides how tight it must be. If the limit exists to keep a downstream service from being overwhelmed, the 2× boundary spike is a real hazard — it is exactly the instantaneous load the downstream cannot take — and you need the sliding behavior. If the limit is a rough fairness quota over a long period (an API's "1000 requests per day"), the boundary doubling is harmless and the cheap fixed counter is fine. And whatever the limiter, it must be shared correctly across a fleet: a per-instance fixed window on ten servers already allows ten times the limit, so a distributed limiter needs shared state (a central store, or a coordinated counter) or the algorithm choice is moot. Match the limiter's precision to what a burst actually costs the thing you are protecting, and make sure the counter is global to the limit's scope.

```python filename=modules/ship-and-operate/code/ship-inter-24/ratelimit.py:64-66 COMPLETE
def peak_in_any_window(admitted, window):
    """The most admitted requests inside any trailing `window`-second span."""
    return max((sum(1 for a in admitted if t - window < a <= t) for t in admitted), default=0)
```

**A fixed-window rate limiter bounds the per-bucket count, not the rolling rate, so a burst straddling the boundary reaches 2× the limit — count requests over the trailing window instead so the bound holds at every instant, and where the exact log costs too much use a sliding-window counter or token bucket, matching the limiter's precision to what a burst actually costs the service you protect and sharing the count across the whole fleet.**

## External resources

The Cloudflare and Stripe engineering posts on rate limiting — the fixed-window boundary problem, the sliding-window log versus the sliding-window counter approximation, and the token bucket, with the memory and accuracy trade-offs.

Any system-design reference on rate-limiting algorithms — fixed window, sliding log, sliding counter, token bucket, and leaky bucket side by side, and distributed rate limiting with shared state.

The companion "rate-limit with a token bucket — and cap it, or a burst floods after idle" and "shed load when the queue is full" modules — the token bucket is the burst-smoothing alternative to windowed counting, and load shedding is what to do once the limiter (or the queue) says no.
