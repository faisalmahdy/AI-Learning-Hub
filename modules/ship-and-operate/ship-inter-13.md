---
id: ship-inter-13
title: Shed load when the queue is full — an overloaded server that accepts everything wastes all its capacity on doomed requests
topic: ship-and-operate
level: intermediate
status: ready
time: 21 min
summary: When arrivals exceed capacity, a server with an unbounded queue accepts everything and the backlog grows until every request waits past its deadline — served too late to matter. On a burst of 18 requests against 1/tick with a 3-tick deadline, accept-everything serves only 4 in time and wastes its capacity on 14 doomed requests. Shedding at a queue cap of 3 rejects 10 fast and serves 8, every one in time — goodput doubles from 4 to 8.
eli5: If a tiny coffee shop lets an endless line pile up, by the time the barista reaches most people they've already left — the coffee is made but no one takes it. If instead the shop says "line's full, come back later" once it's full, everyone who does wait gets served fast. Turning some people away means the ones you keep actually get their coffee.
---

## Why this module

An overloaded server that accepts every request ends up serving almost none of them in time, and the fix is to reject some on purpose.

When the rate of arrivals exceeds what a server can process, something has to give. The naive server accepts everything and puts the overflow in a queue. The queue grows without bound, so each new request waits behind a longer and longer backlog. Past a point, every request waits longer than its deadline — by the time the server reaches it, the client has already timed out and thrown the answer away. The server is pegged at 100% utilization and its useful output is near zero: it spends every cycle producing replies no one will read. That is congestion collapse, and it is the default failure mode of any queue you forgot to bound.

The counterintuitive part is that accepting a request you cannot serve in time is worse than rejecting it. An accepted-but-doomed request still consumes a service slot — a slot that a servable request could have used. So the doomed requests do not just fail themselves; they push everyone behind them further past the deadline, converting near-misses into misses. Utilization stays high while goodput — the requests actually served within their deadline — falls toward zero. The server is busy failing.

Load shedding breaks the collapse by bounding the queue. When the queue is full, new arrivals are rejected immediately with a fast error instead of being enqueued. A rejected client fails fast — it can retry elsewhere, fall back to a cached result, or degrade gracefully — which is far better than waiting a long time for a stale answer. The requests that are admitted wait behind a bounded queue, so their wait is bounded too; set the cap no larger than the deadline allows and every admitted request is served in time. The flood becomes a steady stream the server can actually satisfy.

On the fixture 18 requests arrive in a burst against a server that clears one per tick with a 3-tick deadline. Accept-everything serves only 4 within their deadline and burns the rest on 14 requests that are already too late. Shedding at a queue cap of 3 rejects 10 fast and serves 8, every one in time — goodput doubles from 4 to 8.

**An unbounded queue turns overload into congestion collapse, because doomed requests consume the slots servable ones need; shedding — rejecting arrivals when the queue is full — bounds the wait so admitted requests meet their deadline, and goodput stays near capacity instead of collapsing.**

## Concepts

The metric that matters under overload is goodput, not utilization. Utilization asks "is the server busy?" and under overload the answer is always yes — a collapsing server is 100% busy. Goodput asks the question the users actually care about: "how many requests were served within their deadline?" These two numbers diverge exactly when the system is in trouble. A healthy server has high utilization and high goodput; a collapsing server has high utilization and near-zero goodput, because all that busyness is spent on requests whose answers are discarded. Watching utilization alone hides the collapse; watching goodput reveals it.

The reason an unbounded queue destroys goodput is that queue length is latency. A FIFO queue serving c requests per tick makes a request that arrives behind k others wait k/c ticks before it is served. If arrivals outpace service, k grows without bound, so the wait grows without bound, so eventually every request's wait exceeds its deadline. The queue does not protect the server from overload; it converts overload into delay, and delay past the deadline is just failure with extra steps. An unbounded buffer is not a safety margin — it is a machine for turning a fast failure into a slow one.

Shedding works because a bounded queue bounds the wait. If the queue can hold at most q requests and the server clears c per tick, no admitted request ever waits more than q/c ticks. Choose q so that q/c is within the deadline and every admitted request is guaranteed to be served in time — the bound is structural, not a hope. The cost is that arrivals beyond the cap are rejected, but those are precisely the requests that could not have been served in time anyway. Shedding does not lose goodput; it converts requests that would have been served-too-late (worthless, and costing a slot) into fast rejections (worthless to that client, but costing nothing and freeing the slot).

<svg role="img" aria-label="Under rising load, utilization climbs to 100 percent and stays there while goodput rises then collapses back toward zero" viewBox="0 0 470 190" width="470" height="190">
  <rect x="0" y="0" width="470" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">utilization vs goodput as offered load rises (no shedding)</text>
  <line x1="40" y1="160" x2="450" y2="160" stroke="var(--line)"/>
  <line x1="40" y1="40" x2="40" y2="160" stroke="var(--line)"/>
  <polyline points="48,150 120,90 200,55 280,50 360,50 440,50" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <text x="300" y="44" font-family="var(--mono)" font-size="8" fill="var(--s2)">utilization → pinned at 100%</text>
  <polyline points="48,150 120,90 200,60 240,70 300,110 380,145 440,155" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <text x="300" y="135" font-family="var(--mono)" font-size="8" fill="var(--s1)">goodput → collapses past saturation</text>
  <line x1="230" y1="40" x2="230" y2="160" stroke="var(--acc-line)" stroke-dasharray="3 3"/>
  <text x="196" y="176" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">saturation</text>
  <text x="60" y="176" font-family="var(--mono)" font-size="8" fill="var(--muted)">low load</text>
  <text x="410" y="176" font-family="var(--mono)" font-size="8" fill="var(--muted)">overload</text>
</svg>
^ Past saturation, utilization stays pinned at 100% while goodput collapses — the server is fully busy producing answers that arrive too late, which is why utilization hides the failure and goodput reveals it.

This is why every serious server has an admission-control limit — a max concurrency, a bounded queue, a semaphore — and why "just make the queue bigger" is the wrong instinct. A bigger queue admits more requests to wait longer, which under sustained overload means more requests served too late: it raises latency and lowers goodput. Load shedding is distinct from rate limiting, which caps a client's input rate for fairness; shedding is the server protecting its own goodput by refusing work it cannot complete in time, regardless of who sent it. The two compose — rate limit per client, shed globally when saturated — but the shedding is what stops the collapse.

**Goodput, not utilization, measures an overloaded server, and an unbounded queue drives goodput to zero by turning overload into unbounded delay; a bounded queue bounds the wait, so shedding converts served-too-late requests into fast rejections and keeps goodput near capacity.**

## Worked example

The fixture is a burst of arrivals against a slow server with a tight deadline.

```json filename=modules/ship-and-operate/code/ship-inter-13/load.json:3-6 COMPLETE
  "capacity": 1,
  "deadline": 3,
  "queue_cap": 3,
  "arrivals": [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5]
```

Eighteen requests, three per tick for six ticks, against a server that clears one per tick — a 3× overload. A request is good only if served within 3 ticks of arrival. The queue cap of 3 is the shedding threshold. The simulator serves capacity requests per tick from the front of the queue, then admits that tick's arrivals — rejecting them if the queue is at its cap.

```python filename=modules/ship-and-operate/code/ship-inter-13/shed.py:51-65 COMPLETE
    q = deque()
    horizon = max(arrivals) + len(arrivals) + deadline + 2
    for t in range(horizon):
        for _ in range(capacity):                 # serve from the front of the queue
            if q:
                rid = q.popleft()
                r = records[rid]
                r["served"], r["waited"] = t, t - r["arrival"]
                r["good"] = r["waited"] <= deadline
        for rid in by_tick.get(t, []):            # admit this tick's arrivals, or shed if full
            if queue_cap is not None and len(q) >= queue_cap:
                records[rid]["rejected"] = True
            else:
                q.append(rid)
    return records
```

Accept-everything passes `queue_cap=None`, so the reject branch never fires and the queue is unbounded. Predict: the backlog grows by two per tick (three in, one out), so waits climb steadily and cross the 3-tick deadline early — only the first handful of requests make it. Run it.

```text filename=modules/ship-and-operate/code/ship-inter-13/shed.py --run
ACCEPT-EVERYTHING (unbounded queue)   (18 arrivals, 1/tick, deadline 3)
--------------------------------------------------------------
  req  0  arr 0  served  1  waited 1  in time
  req  1  arr 0  served  2  waited 2  in time
  req  2  arr 0  served  3  waited 3  in time
  req  3  arr 1  served  4  waited 3  in time
  req  4  arr 1  served  5  waited 4  TOO LATE (wasted)
  req  5  arr 1  served  6  waited 5  TOO LATE (wasted)
  req  6  arr 2  served  7  waited 5  TOO LATE (wasted)
  req  7  arr 2  served  8  waited 6  TOO LATE (wasted)
  goodput 4   late 14   rejected 0
```

The waits climb without bound — 1, 2, 3, 3, 4, 5, 5, 6, and on up to 13 for the last request. Only four requests (0 through 3) are served within the 3-tick deadline; the other fourteen are served too late to matter, each having consumed a service tick to produce a discarded answer. Goodput is 4, and the server was 100% busy the whole time. Now the shed policy, at queue cap 3.

```text filename=modules/ship-and-operate/code/ship-inter-13/shed.py --run
SHED at queue cap 3   (18 arrivals, 1/tick, deadline 3)
--------------------------------------------------------------
  req  0  arr 0  served  1  waited 1  in time
  req  3  arr 1  served  4  waited 3  in time
  req  4  arr 1  REJECTED (queue full)
  req  6  arr 2  served  5  waited 3  in time
  req  9  arr 3  served  6  waited 3  in time
  req 12  arr 4  served  7  waited 3  in time
  req 15  arr 5  served  8  waited 3  in time
  goodput 8   late 0   rejected 10
```

Every admitted request waits at most 3 ticks — the queue cap guarantees it — so all 8 admitted requests are served in time. Ten requests are rejected fast at the moment they arrive to a full queue. Goodput is 8, double the accept-everything server's 4, from the same capacity serving the same burst. The only difference is that shedding refused the requests it could not have served in time instead of admitting them to waste slots.

<svg role="img" aria-label="Waiting time per request: accept-everything climbs past the deadline line and stays above it; shedding stays flat at the deadline with rejected requests marked" viewBox="0 0 470 200" width="470" height="200">
  <rect x="0" y="0" width="470" height="200" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">wait per request (dashed = 3-tick deadline)</text>
  <line x1="40" y1="170" x2="450" y2="170" stroke="var(--line)"/>
  <line x1="40" y1="40" x2="40" y2="170" stroke="var(--line)"/>
  <line x1="40" y1="140" x2="450" y2="140" stroke="var(--acc-line)" stroke-dasharray="3 3"/>
  <text x="360" y="136" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">deadline = 3</text>
  <polyline points="48,160 68,150 88,140 108,140 128,130 148,120 168,120 188,110 208,100 228,100 248,90 268,80 288,80 308,70 328,60 348,60 368,50 388,40" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <text x="210" y="70" font-family="var(--mono)" font-size="8" fill="var(--s2)">accept-everything: wait climbs, 14 served too late</text>
  <g fill="var(--acc-line)"><circle cx="48" cy="160" r="3"/><circle cx="108" cy="140" r="3"/><circle cx="168" cy="140" r="3"/><circle cx="228" cy="140" r="3"/><circle cx="288" cy="140" r="3"/><circle cx="348" cy="140" r="3"/><circle cx="388" cy="140" r="3"/></g>
  <text x="150" y="162" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">shed: 8 admitted, wait ≤ 3, none late (rest rejected)</text>
</svg>
^ Accept-everything's wait rises steadily past the deadline and never returns; shedding holds every admitted request at or under the 3-tick deadline and turns the rest away.

## Build

Reproduce the run. Pure standard library, deterministic, so the goodput of 4 versus 8 and the 14 wasted services come out exactly.

Run `--run` for the tick-by-tick trace, `--goodput` for the summary, `--check` for the gate. The tally splits every request into three buckets: good (served in time), late (served but past deadline — wasted work), and rejected.

```python filename=modules/ship-and-operate/code/ship-inter-13/shed.py:68-72 COMPLETE
def tally(records):
    good = sum(1 for r in records.values() if r["good"])
    late = sum(1 for r in records.values() if r["served"] is not None and not r["good"])
    rejected = sum(1 for r in records.values() if r["rejected"])
    return good, late, rejected
```

The `late` bucket is the one that indicts the accept-everything policy: a served-but-late request cost a full service slot and produced nothing, so it is strictly worse than a rejection, which costs nothing.

```text filename=modules/ship-and-operate/code/ship-inter-13/shed.py --goodput
GOODPUT — requests served in time vs capacity wasted on late ones
--------------------------------------------------------------
  policy               goodput   late(wasted)   rejected
  accept-everything        4           14          0
  shed cap 3               8            0         10
--------------------------------------------------------------
  shedding trades rejections for goodput; late work is pure waste.
```

<svg role="img" aria-label="Stacked outcome bars: accept-everything is mostly wasted late work with a small goodput slice; shedding is a larger goodput slice plus fast rejections and no waste" viewBox="0 0 470 190" width="470" height="190">
  <rect x="0" y="0" width="470" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">18 requests: goodput (solid) vs late-wasted vs rejected</text>
  <text x="60" y="46" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">accept-everything</text>
  <rect x="60" y="52" width="40" height="110" fill="var(--s1)"/>
  <rect x="100" y="52" width="280" height="110" fill="var(--s2)"/>
  <text x="66" y="112" font-family="var(--mono)" font-size="8" fill="var(--ink)">good 4</text>
  <text x="150" y="112" font-family="var(--mono)" font-size="8" fill="var(--ink)">late/wasted 14</text>
  <text x="60" y="184" font-family="var(--mono)" font-size="8" fill="var(--muted)">every slot used, most output discarded</text>
  <text x="60" y="12" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)"> </text>
</svg>
^ Accept-everything spends 14 of its 18 slots on late, discarded work for a goodput of 4; shedding (goodput 8, 10 fast rejections, zero waste) doubles the useful output from the same capacity.

The self-test pins the story: accept-everything serves requests too late to matter, shedding never does, shedding's goodput is higher, and shedding fails fast where accept-everything rejects nothing.

```python filename=modules/ship-and-operate/code/ship-inter-13/shed.py:115-118 COMPLETE
    open_wastes = l_open > 0
    print("  accept-everything serves requests too late to matter = %s (%d wasted)" % (open_wastes, l_open))

    shed_no_waste = l_shed == 0
    print("  shedding never serves a request too late = %s (%d wasted)" % (shed_no_waste, l_shed))
```

```text filename=modules/ship-and-operate/code/ship-inter-13/shed.py --check
SELF-TEST — accept-everything wastes capacity on late requests; shedding lifts goodput and wastes none
--------------------------------------------------------------------------------------------------
  accept-everything serves requests too late to matter = True (14 wasted)
  shedding never serves a request too late = True (0 wasted)
  shedding's goodput beats accept-everything's = True (8 vs 4)
  accept-everything rejects nothing; shedding fails fast = True (10 rejected)
--------------------------------------------------------------------------------------------------
SELF-TEST PASS  open_wastes=True  shed_no_waste=True  shed_lifts_goodput=True  open_rejects_none=True
```

Four True flags. Open_wastes: accept-everything serves 14 requests too late, pure wasted capacity. Shed_no_waste: shedding serves nothing late, because its bounded queue bounds the wait under the deadline. Shed_lifts_goodput: 8 versus 4, double, from the same capacity. Open_rejects_none: accept-everything turns no one away, which is exactly why it collapses; shedding fails 10 fast.

**The late bucket is the indictment — 14 requests served too late cost 14 slots and produced nothing, so shedding's 10 fast rejections are not lost goodput but reclaimed capacity, which is why goodput doubles.**

## Definition of done

You are done when you reproduce the goodput gap and can explain why rejecting requests raises it.

Concretely: `--run` shows accept-everything's waits climbing past the deadline with only 4 served in time, and shedding holding every admitted request at or under 3 ticks; `--goodput` shows 4 versus 8 with 14 wasted versus 0; `--check` prints PASS with four True flags. You can explain that goodput, not utilization, measures an overloaded server, and that an unbounded queue turns overload into unbounded delay so goodput collapses. You can explain that a bounded queue of size q with service rate c bounds the wait at q/c, so choosing q within the deadline guarantees admitted requests are served in time, and that the rejected requests are the ones that could not have been served in time anyway.

The habit to carry: bound every queue and every concurrency limit, and shed — fail fast — when the bound is hit, rather than admitting work you cannot complete in time. When an overloaded service shows 100% CPU and near-zero successful responses, suspect an unbounded queue serving stale requests, not a capacity shortage; adding capacity without shedding just raises the collapse threshold. Watch goodput, not utilization.

## Boss fight

The instructive failure is a service that gets slower the more capacity you add, because every new worker also serves doomed requests.

A service under a traffic spike shows every worker at 100% CPU and a success rate near zero — clients are timing out at 2 s while the service happily computes 8 s responses for requests those clients abandoned long ago. The team scales out, doubling the worker count, and it barely helps: the new workers also pull from the same unbounded queue and also spend their time on requests that will time out, so goodput inches up while cost doubles. The queue is the problem, not the worker count. The fix is admission control: bound the queue (or cap in-flight requests per worker) and return a fast 503 when the bound is hit. Now workers only ever serve requests fresh enough to beat the deadline, goodput jumps to near capacity, and the fast 503s let clients retry elsewhere or degrade instead of blocking.

Your turn, two moves. First, prove that a bigger queue is not the fix. Raise queue_cap toward the unbounded case (say 12) and predict: goodput falls back toward the accept-everything number, because a longer queue admits requests to wait longer, past the deadline — there is a sweet spot near deadline × capacity and larger is worse, not better. Find the cap that maximizes goodput and confirm it is small. Second, make the overload transient rather than sustained: keep the 18-request burst but stretch the arrivals over more ticks so average load is under capacity. Confirm that with load under capacity the unbounded queue is fine (the backlog drains between bursts) and shedding rejects nothing — shedding costs nothing when you are not overloaded and saves you when you are, which is why it is safe to leave on always.

## External resources

Google's SRE book chapter on handling overload is the canonical treatment — it covers graceful degradation, load shedding, and why a server must reject work it cannot complete, with the goodput-versus-utilization distinction at the center.

The literature on congestion collapse (originally from TCP, e.g. Nagle and Jacobson) is the same phenomenon in a different setting — an uncontrolled queue turning offered load into delay until useful throughput collapses — and reading it shows why bounded buffers and early drop are the general cure.

Netflix's writing on concurrency-limits and adaptive load shedding (the concurrency-limits library) shows a production approach that measures latency to set the admission limit dynamically, so the queue cap tracks real capacity instead of a hand-tuned constant.
