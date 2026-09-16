---
id: coordomit-inter-01
title: Count the requests a stall omitted, not just the one it caught — or your latency tail hides the worst of the outage
topic: ship-and-operate
level: intermediate
status: ready
time: 16 min
summary: A load tester measures latency by sending requests and timing responses, and the common design is closed-loop: send a request, wait for its response, then send the next. That feedback is the bug. When the server stalls — a GC pause, a lock, a failover — the one request in flight records the full stall as its latency, correctly; but while the tester sits blocked, it does not send the requests scheduled to go out during the freeze, so those never happen and never get measured. They are exactly the requests that would have measured the tail, because every one of them would have been stuck behind the same stall. The tester recorded one slow request and silently omitted the several equally-slow ones its own blocking prevented — coordinated omission, where the measurement colludes with the stall to hide it. The result is a distribution that looks far healthier than reality: a one-second freeze shows as a single outlier, so the p99 you page on stays green through an outage. The fix is to drive load open-loop or backfill the omitted requests with the latency they would have had. On a fixture of 20 requests, one per unit, with a 5-unit freeze at time 5, the closed-loop tester records 1 slow request (p90 = 0) while the corrected measurement records 5 (latencies 5, 4, 3, 2, 1; p90 = 3).
eli5: To test how long a checkout line takes, you send in one shopper, wait for them to finish, then send the next. But if the register freezes for five minutes, your shopper is stuck the whole time — and because you were waiting for them, you never sent the four shoppers who should have arrived during those five minutes and would have been stuck too. Your notes say "one slow checkout." Reality is "five slow checkouts." By waiting for each shopper before sending the next, your measurement accidentally skips exactly the people the freeze would have hurt.
---

## Why this module

A latency measurement is only honest if the act of measuring does not change what gets measured — and a closed-loop load tester, by waiting for each response before sending the next, stops sending precisely when the system is slowest, so it under-samples the exact moments it exists to catch.

The natural way to generate load is a loop: send a request, wait for the response, record the latency, send the next. It is simple and it self-throttles — you never pile requests onto a server faster than it answers. That self-throttling is the trap. When the server freezes for a moment, the request in flight blocks until the freeze ends and records the full stall as its latency, which is correct and looks like a captured outlier. But the tester is now blocked too, so during the entire freeze it sends nothing. The requests that were supposed to go out during that window — and that would each have hit the same freeze, recording their own slow latencies — are never sent. They do not appear as fast requests or slow requests; they simply do not appear. The measurement omitted them, and it omitted them *because* of the stall, so the omission is correlated with exactly the event you are trying to measure.

**A closed-loop load tester waits for each response before sending the next, so during a stall it stops sending and omits the requests that would have measured the tail — the omission is coordinated with the stall, so the slower the system gets, the more of its slowness the measurement throws away.**

The effect on the reported numbers is severe and always in the same direction: latency looks better than it is. A freeze that truly slowed a fifth of the intended requests is recorded as a single outlier among many fast samples, so the mean barely moves and the high percentiles — the p99 an alert watches — stay comfortable through an outage users felt sharply. The fix is to break the feedback between response and send. Either drive the load open-loop, emitting requests on a fixed schedule no matter when responses return, so the stalled window still generates its full complement of (slow) samples; or correct after the fact by backfilling each omitted request with the latency it would have had — the time from its intended send until the stall cleared. Either way the tail then reflects the whole stall instead of its tip. This module measures a stall both ways and shows the tail reappear.

## Concepts

**The true latency** of a request scheduled at time t is zero when the server is healthy, or the wait until the freeze clears if t falls inside a stall. Every scheduled request has one, whether or not a tester sent it.

```python filename=modules/ship-and-operate/code/coordomit-inter-01/coordomit.py:43-45 COMPLETE
def true_latency(t, stall_start, stall_end):
    """Latency of a request intended at time t: 0 normally, or the wait until the stall clears if it hit the freeze."""
    return stall_end - t if stall_start <= t < stall_end else 0
```

**Open-loop (corrected) measurement** records every scheduled request with its true latency — the honest distribution, because no request is skipped.

```python filename=modules/ship-and-operate/code/coordomit-inter-01/coordomit.py:48-51 COMPLETE
def corrected_latencies(data):
    """Open-loop: every scheduled request with the latency it would truly have had."""
    end = data["stall_start"] + data["stall_duration"]
    return [true_latency(t * data["interval"], data["stall_start"], end) for t in range(data["requests"])]
```

**Coordinated omission** is the gap between the two: the requests a closed-loop tester never sends because it was blocked, which are exactly the ones inside the freeze.

<svg role="img" aria-label="Requests scheduled one per time unit; a freeze from 5 to 10; the closed-loop tester sends the request at 5, blocks, and never sends the requests at 6, 7, 8, 9" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">scheduled requests (every unit); freeze shaded</text>
  <rect x="80" y="20" width="80" height="40" fill="var(--s2)" opacity="0.18" stroke="var(--s2)"/>
  <text x="92" y="18" fill="var(--s2)" font-size="7">freeze 5–10</text>
  <line x1="20" y1="52" x2="290" y2="52" stroke="var(--grid)"/>
  <g fill="var(--s1)"><circle cx="32" cy="52" r="3"/><circle cx="48" cy="52" r="3"/><circle cx="64" cy="52" r="3"/></g>
  <circle cx="80" cy="52" r="3.5" fill="var(--ink)"/><text x="70" y="74" fill="var(--muted)" font-size="7">sent, stuck</text>
  <g fill="none" stroke="var(--s2)"><circle cx="96" cy="52" r="3"/><circle cx="112" cy="52" r="3"/><circle cx="128" cy="52" r="3"/><circle cx="144" cy="52" r="3"/></g>
  <text x="96" y="40" fill="var(--s2)" font-size="7">never sent (omitted)</text>
  <g fill="var(--s1)"><circle cx="176" cy="52" r="3"/><circle cx="192" cy="52" r="3"/><circle cx="208" cy="52" r="3"/></g>
  <text x="20" y="94" fill="var(--muted)" font-size="8">the tester blocks on the stuck request and skips the four the freeze would have slowed</text>
</svg>
^ Requests are scheduled once per unit; the closed-loop tester sends the one at time 5, blocks through the freeze, and never sends those at 6–9 — the open (omitted) circles are the tail samples that vanish.

**A latency measurement must send on a schedule independent of responses, because a tester that waits for each response omits requests exactly during a stall — so the honest distribution includes every scheduled request's true latency, not only those the tester happened to send.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/coordomit-inter-01/coordomit.py

The fixture schedules 20 requests one per unit and freezes the server for 5 units starting at time 5.

```json filename=modules/ship-and-operate/code/coordomit-inter-01/coordomit.json:3-6 COMPLETE
  "requests": 20,
  "interval": 1,
  "stall_start": 5,
  "stall_duration": 5
```

Run `--measure` to record the stall both ways.

```text filename=--measure
MEASURE — closed-loop samples vs corrected (open-loop) samples
--------------------------------------------------------------
  closed-loop latencies:  [0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    samples 16   mean 0.312   max 5
  corrected latencies:    [0, 0, 0, 0, 0, 5, 4, 3, 2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    samples 20   mean 0.750   max 5
```

The closed-loop tester recorded 16 samples, fifteen of them zero and one of them 5 — the request that was in flight when the freeze hit. Its story of the outage is "one slow request." The corrected measurement recorded all 20 scheduled requests, and the freeze shows up as a staircase: the request at time 5 waited the full 5 units, the one at 6 waited 4, then 3, 2, 1, as each was scheduled progressively closer to the freeze's end. Five requests were slowed, not one. Notice the two agree on the *maximum* — both see a worst case of 5 — which is what makes coordinated omission so insidious: the single worst outlier is captured, so a naive look at "max latency" or even "the slowest request" reveals nothing wrong. The damage is to the shape of the distribution: the corrected mean is 0.750 against the closed-loop's 0.312, more than double, because four slow requests were resurrected from omission. The stall was always five requests deep; only the measurement made it look one deep.

<svg role="img" aria-label="The closed-loop distribution has one spike of height 5; the corrected distribution has a staircase of 5, 4, 3, 2, 1" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">latency samples (height = latency)</text>
  <text x="6" y="30" fill="var(--muted)" font-size="8">closed-loop</text>
  <line x1="70" y1="44" x2="290" y2="44" stroke="var(--grid)"/>
  <rect x="150" y="14" width="8" height="30" fill="var(--s2)"/><text x="160" y="24" fill="var(--muted)" font-size="7">one spike (5)</text>
  <g fill="var(--s1)"><rect x="74" y="42" width="8" height="2"/><rect x="86" y="42" width="8" height="2"/><rect x="98" y="42" width="8" height="2"/><rect x="110" y="42" width="8" height="2"/><rect x="122" y="42" width="8" height="2"/></g>
  <text x="6" y="66" fill="var(--muted)" font-size="8">corrected</text>
  <line x1="70" y1="94" x2="290" y2="94" stroke="var(--grid)"/>
  <rect x="150" y="64" width="8" height="30" fill="var(--s1)"/><rect x="160" y="70" width="8" height="24" fill="var(--s1)"/><rect x="170" y="76" width="8" height="18" fill="var(--s1)"/><rect x="180" y="82" width="8" height="12" fill="var(--s1)"/><rect x="190" y="88" width="8" height="6" fill="var(--s1)"/>
  <text x="204" y="80" fill="var(--muted)" font-size="7">staircase 5,4,3,2,1</text>
  <text x="6" y="102" fill="var(--muted)" font-size="8">same max, but the corrected set has five slow samples where the closed-loop has one</text>
</svg>
^ Both distributions peak at 5, but the closed-loop one has a single slow spike while the corrected one is a staircase of five slow samples — the four the tester omitted.

## Build

The distribution shape is where an alert lives, so look at the tail. Run `--tail`.

```text filename=--tail
TAIL — how many requests the stall actually slowed, and the p90
--------------------------------------------------------
  requests the stall slowed, closed-loop measured:  1
  requests the stall slowed, actually:              5
  p90 latency, closed-loop:  0
  p90 latency, corrected:    3
```

Under closed-loop measurement the 90th-percentile latency is 0 — because with 16 samples and only one non-zero, the 90th percentile still lands in the sea of zeros. A p90 (or even a p95) alert would show a perfectly healthy service straight through the freeze. The corrected p90 is 3, because five of the twenty samples are slow, so the top 10% of the distribution is squarely in the stall. That is the difference between an SLO dashboard that catches the outage and one that sleeps through it. And the fixture is gentle: a longer freeze or a higher request rate omits *more* requests, so the gap between the closed-loop tail and the true tail widens with the severity of the stall — coordinated omission hides the big outages best. This is why latency benchmarks that report suspiciously clean high percentiles are treated with suspicion, and why the fix is structural: correct the omission (backfill each skipped request's would-be latency) or avoid it (send open-loop). Measuring the max is not enough; the tail is a claim about *how many* requests were slow, and that is exactly the count coordinated omission corrupts.

<svg role="img" aria-label="Closed-loop p90 is 0 while corrected p90 is 3; the closed-loop tail stays flat through the stall" viewBox="0 0 300 92" width="300" height="92">
  <text x="6" y="12" fill="var(--muted)" font-size="8">p90 latency reported</text>
  <line x1="80" y1="18" x2="80" y2="76" stroke="var(--grid)"/>
  <text x="6" y="34" fill="var(--muted)" font-size="8">closed-loop</text>
  <rect x="80" y="26" width="2" height="14" fill="var(--s2)"/><text x="86" y="37" fill="var(--muted)" font-size="7">p90 = 0 (alert stays green)</text>
  <text x="6" y="60" fill="var(--muted)" font-size="8">corrected</text>
  <rect x="80" y="52" width="130" height="14" fill="var(--s1)"/><text x="214" y="63" fill="var(--muted)" font-size="7">p90 = 3 (alert fires)</text>
  <text x="6" y="88" fill="var(--muted)" font-size="8">the stall hit 5 of 20 requests; only the corrected p90 shows it</text>
</svg>
^ The closed-loop p90 is 0 and would keep an SLO alert green through the freeze; the corrected p90 is 3, reflecting that a quarter of the requests were slowed — the tail coordinated omission erased.

## Definition of done

The self-test pins the omission and its effect: closed-loop omits the requests scheduled during the freeze, both see the same single max, but correcting reveals more slow requests and raises the mean and the p90.

```python filename=modules/ship-and-operate/code/coordomit-inter-01/coordomit.py:109-122 COMPLETE
    omits_requests = omitted == data["stall_duration"] - 1
    print("  closed-loop omits the requests scheduled inside the freeze = %s (%d omitted)" % (omits_requests, omitted))

    same_max = max(cl) == max(co)
    print("  both see the same single worst request (the in-flight one) = %s (max %d)" % (same_max, max(cl)))

    more_slow_when_corrected = sum(1 for x in co if x > 0) > sum(1 for x in cl if x > 0)
    print("  correcting reveals more slow requests than closed-loop saw = %s (%d vs %d)"
          % (more_slow_when_corrected, sum(1 for x in co if x > 0), sum(1 for x in cl if x > 0)))

    mean_rises = mean(co) > mean(cl)
    print("  the corrected mean latency is higher = %s (%.3f > %.3f)" % (mean_rises, mean(co), mean(cl)))

    tail_rises = percentile(co, 90) > percentile(cl, 90)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — closed-loop omits the requests scheduled during the stall; correcting them raises the mean and the tail
----------------------------------------------------------------------------------------------------------------------
  closed-loop omits the requests scheduled inside the freeze = True (4 omitted)
  both see the same single worst request (the in-flight one) = True (max 5)
  correcting reveals more slow requests than closed-loop saw = True (5 vs 1)
  the corrected mean latency is higher = True (0.750 > 0.312)
  the corrected p90 is higher (the hidden tail) = True (3 > 0)
```

**Done means coordinated omission is proven and corrected: the closed-loop tester omits the 4 requests scheduled inside the freeze, both measurements agree on the single worst request (max 5), but correcting the omission reveals 5 slow requests instead of 1, raising the mean from 0.312 to 0.750 and the p90 from 0 to 3 — the tail the closed-loop tester's own blocking erased.**

## Boss fight

Predict the two places coordinated omission hides beyond a load tester. It is tempting to think this is only a benchmarking-tool bug.

The first trap is that the same omission lives inside production instrumentation, not just synthetic load. Any latency metric that starts its timer when a request *begins being served* rather than when it *should have started* has the same blind spot: if requests queue behind a stall, a server that times only from dequeue-to-response never counts the time each request spent waiting in the queue for the stalled one ahead of it. The queued requests are real (unlike the load tester's, they were actually sent by users), but their wait is omitted from the per-request latency unless you measure from *arrival*, not from *service start*. This is why service-time and response-time are different metrics, and why an honest latency SLO measures from the moment the request arrived at the system — queue time included — not from the moment a worker picked it up. Measure service time and a queue backup is invisible in your latency exactly as a stall is invisible to a closed-loop tester.

```python filename=modules/ship-and-operate/code/coordomit-inter-01/coordomit.py:54-58 COMPLETE
def closed_loop_latencies(data):
    """Closed-loop: the tester blocks during the stall, so requests scheduled strictly inside the freeze never send."""
    start, end = data["stall_start"], data["stall_start"] + data["stall_duration"]
    return [true_latency(t * data["interval"], start, end)
            for t in range(data["requests"]) if not (start < t * data["interval"] < end)]
```

The second trap is that "just correct it by backfilling" needs an intended schedule, and not all load is scheduled. The backfill — replaying each omitted request with the latency it would have had — assumes you know the rate requests were *supposed* to arrive at, which is well-defined for an open-loop benchmark with a target throughput but not for real, bursty, user-driven traffic where the arrival process is itself variable and sometimes genuinely responds to slowness (users retry, or give up). So the corrections are exact only under the model that requests arrive at a fixed rate independent of the system's health; where arrivals actually depend on responses (a closed-loop *client*, not just a closed-loop tester), the true user-experienced latency is a harder question that needs the real arrival process, not a uniform backfill. The safe defaults are to measure open-loop when you control the load, to record from arrival rather than service-start in production, and to distrust any latency histogram whose high percentiles look implausibly calm — coordinated omission's signature is a clean tail that no real system with stalls should have.

**Coordinated omission is a measurement colluding with a stall: a closed-loop tester (or any timer started at service-start rather than arrival) stops producing samples exactly when the system is slow, so it omits the tail and reports latencies far better than reality — correct it by driving load open-loop or measuring from request arrival with queue time included, and distrust suspiciously clean high percentiles; but the backfill correction assumes a known intended arrival rate, so for genuinely bursty, response-dependent user traffic the honest tail needs the real arrival process, not a uniform replay.**

## External resources

Gil Tene's talks and writing on coordinated omission and the HdrHistogram / wrk2 tools — the origin of the term, why closed-loop load generators understate the tail, and the correction (recording expected-interval samples) built into measurement tools.

Any queueing-theory reference on response time versus service time and on open-loop versus closed-loop load models — the distinction between measuring from arrival (queue time included) and from service start, and why the arrival model determines what the tail means.

The companion "track the p99, not the mean" and "pool the samples to get a fleet percentile" modules — the first is about which statistic to watch and the second about computing it across shards, while this module is about the sampling bias that corrupts the tail before either statistic is even computed.
