---
id: hedged-inter-01
title: Hedge the slow requests — send a duplicate to another replica so one slow replica cannot own your tail latency
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: In a replicated service, average latency is easy and tail latency is hard: most requests are fast, but a few land on a replica that is briefly slow — a GC pause, a hot cache miss, a noisy neighbor — and those few define the p99 and p99.9 that users feel. You cannot prevent a replica from occasionally being slow, so the question is not how to make every replica always fast but how to stop one occasionally-slow replica from making a request slow when other replicas are available. Hedged requests answer it: send the request to one replica as usual, but if it has not answered within a short delay — chosen around the normal p95, well below the tail — send a second copy to a different replica and take whichever comes back first. Because a replica being slow now is mostly independent of another being slow now, the chance that both the original and the hedge are slow is much smaller than the chance one is, so a request that would have waited 200ms instead waits until a healthy replica answers the duplicate, capping its latency near the hedge delay plus a normal response. The cost is controlled by the delay: the hedge fires only for requests still outstanding at the delay, and since the delay sits above normal latency, the fast majority finish first and hedging adds duplicate work only for the slow tail. On a fixture where four requests are fast (10–13ms) and one hit a slow replica (200ms), a 20ms hedge delay to a 15ms replica drops the slow request to min(200, 35)=35ms and leaves the four fast ones untouched (they finish before the hedge fires), cutting the tail from 200ms to 35ms while sending just one extra request.
eli5: Imagine you order the same dish at a busy restaurant, and usually it comes in a few minutes — but every so often one kitchen is backed up and your food takes forever. You can't make every kitchen fast. So here's the trick: if your food hasn't arrived after a short wait, you quietly place the same order at a second kitchen and eat whichever plate shows up first. Most of the time your first order arrives before you'd even place the second, so you never bother. Only when the first kitchen is slow do you send the backup order — and since the second kitchen is usually fine, you almost never wait for the slow one. You occasionally make one extra dish, but you almost never wait forever.
---

## Why this module

Tail latency is where replicated systems disappoint users, and it disappoints them in a way averages hide. A service can have a 12ms median and a 200ms p99, and it is the p99 that shows up as the spinner, the timeout, the "why is this slow" ticket — because at scale, every user request fans out to many backend calls and hits the tail of at least one. The uncomfortable truth is that you cannot engineer the tail away at the source: replicas will occasionally pause for garbage collection, miss a cache, or share a machine with a noisy neighbor, and no amount of tuning removes every transient slowdown. So the strategy has to be to tolerate a slow replica, not to prevent it.

The leverage is redundancy you already have. A replicated service has more than one replica that can serve any request, and — crucially — one replica being slow at a given instant is largely uncorrelated with another being slow at that instant. That independence is the whole opportunity: if you can arrange to be served by whichever of two replicas is fast right now, the probability that you are stuck waiting drops from "one replica is slow" to "two replicas are slow at once," which is far rarer.

Hedged requests turn that into a mechanism, and the art is doing it without doubling your load. This module runs the same five requests with and without hedging and measures both the tail and the extra work.

**Hedge slow requests — after a delay set near the normal p95, send a duplicate to another replica and take the first response — rather than waiting on a single replica, because tail latency is dominated by the occasional slow replica and a second replica is usually fast, so the duplicate caps the tail near the hedge delay while firing only for the slow minority, adding little extra load.**

## Concepts

The fixture is five requests, each carrying the latency of the replica it landed on: four fast (10–13ms) and one that hit a slow replica (200ms) — the tail. The hedge delay is 20ms (above the ~12ms typical, below the 200ms tail), and the second replica the hedge goes to responds in 15ms.

```json filename=modules/ship-and-operate/code/hedged-inter-01/hedged.json:3-5 COMPLETE
  "latencies_ms": [10, 12, 11, 200, 13],
  "hedge_delay_ms": 20,
  "fallback_ms": 15
```

Two rules define hedging. A hedge fires only if the request is still outstanding at the delay; and when it fires, the effective latency is the minimum of the original and the delay-plus-fallback (because you take whichever replica answers first).

```python filename=modules/ship-and-operate/code/hedged-inter-01/hedged.py:32-41 COMPLETE
def hedge_fires(orig, delay):
    """A hedge is sent only if the request is still outstanding at the hedge delay."""
    return orig > delay


def effective_latency(orig, delay, fallback):
    """With hedging: if the hedge fires, the effective latency is min(original, delay + fallback)."""
    if hedge_fires(orig, delay):
        return min(orig, delay + fallback)
    return orig
```

Tail latency is the max, and the median stands in for the typical latency the delay must sit above.

```python filename=modules/ship-and-operate/code/hedged-inter-01/hedged.py:44-49 COMPLETE
def tail(latencies):
    return max(latencies)


def median(latencies):
    s = sorted(latencies)
    return s[len(s) // 2]
```

<svg role="img" aria-label="A timeline: a slow request runs to 200ms, but at the 20ms hedge delay a duplicate is sent to a fast replica that answers at 35ms, and the request completes at 35ms" viewBox="0 0 320 120">
  <line x1="20" y1="40" x2="300" y2="40" stroke="var(--line)" stroke-width="1"/>
  <line x1="60" y1="20" x2="60" y2="100" stroke="var(--s2)" stroke-width="1.2" stroke-dasharray="3 2"/>
  <text x="40" y="16" font-size="7.5" fill="var(--s2)">hedge delay 20ms</text>
  <rect x="20" y="34" width="270" height="12" fill="var(--muted)" opacity="0.5"/>
  <text x="200" y="32" font-size="7.5" fill="var(--muted)">original replica → 200ms (slow)</text>
  <rect x="60" y="60" width="40" height="12" fill="var(--s1)"/>
  <text x="104" y="70" font-size="7.5" fill="var(--s1)">hedge to fast replica → answers at 35ms</text>
  <line x1="100" y1="20" x2="100" y2="100" stroke="var(--ink)" stroke-width="1"/>
  <text x="104" y="94" font-size="7.5" fill="var(--ink)">take first: 35ms</text>
</svg>
^ The original replica is slow (200ms). At 20ms the hedge goes to a healthy replica that answers 15ms later, at 35ms — and taking the first response ends the request at 35ms instead of 200ms. The tail is capped near delay + fallback.

**Hedging exploits replica independence: the request finishes when the faster of two replicas answers, so it only waits the tail when both are slow at once — a far rarer event than one being slow.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the request-dispatch step of a replicated service client, reduced to five requests so every effective latency is checkable by hand.

Run `--latency` to see each request's original and effective latency and whether a hedge fired.

```text filename=hedged.py --latency
  req  original   hedge fires?   effective
  0    10         False          10
  1    12         False          12
  2    11         False          11
  3    200        True           35
  4    13         False          13
  the hedge fires only for requests slower than the 20ms delay
```

The four fast requests (10, 12, 11, 13ms) all complete before the 20ms delay, so no hedge is sent and their latency is unchanged — hedging is invisible for them. The slow request (200ms) is still outstanding at 20ms, so the hedge fires: a duplicate goes to the fast replica, and taking the first response gives min(200, 20+15) = 35ms. One request triggered a hedge; four did not.

Now `--tail` compares the tail latency and counts the extra work.

```text filename=hedged.py --tail
  median latency        = 12ms
  tail (max) no hedge   = 200ms
  tail (max) hedged     = 35ms
  extra requests sent by hedging = 1 of 5 (only the slow tail)
```

Without hedging the tail is 200ms — one slow replica sets the worst-case for the whole batch. With hedging the tail drops to 35ms, an almost 6× improvement on the metric users feel, and the cost is a single extra request out of five: hedging duplicated only the one request that was actually slow, because the delay sits above the normal latency so the fast requests never triggered it. That is the trade in one line — a few percent extra load for a dramatically lower tail.

**The tail falls from 200ms to 35ms for the cost of one duplicated request, because the hedge fired only for the slow request and the four fast ones finished before it could — a large tail win at a small, targeted load cost.**

## Build

The self-test asserts the setup and the effect: that there is a real tail far above the median, that the delay sits above the typical latency (so it fires selectively), and that hedging caps the tail while leaving fast requests unchanged.

```python filename=modules/ship-and-operate/code/hedged-inter-01/hedged.py:86-96 COMPLETE
    has_tail = tail(lat) > 5 * median(lat)
    print("  one request has a tail latency far above the median = %s (%dms vs median %dms)" % (has_tail, tail(lat), median(lat)))

    delay_above_typical = delay > median(lat)
    print("  the hedge delay sits above the typical latency = %s (%dms > %dms)" % (delay_above_typical, delay, median(lat)))

    hedging_caps_tail = tail(hedged) < tail(lat)
    print("  hedging caps the tail latency = %s (%dms < %dms)" % (hedging_caps_tail, tail(hedged), tail(lat)))

    fast_unaffected = all(effective_latency(o, delay, fb) == o for o in lat if not hedge_fires(o, delay))
    print("  requests faster than the delay are unchanged (no hedge sent) = %s" % fast_unaffected)
```

<svg role="img" aria-label="Two bars for tail latency: no hedge at 200ms and hedged at 35ms, with a small marker showing one extra request sent" viewBox="0 0 320 110">
  <text x="10" y="18" font-size="8.5" fill="var(--muted)">tail (max) latency</text>
  <text x="10" y="40" font-size="8.5" fill="var(--s2)">no hedge</text>
  <rect x="80" y="30" width="210" height="16" fill="var(--s2)"/><text x="255" y="43" font-size="8" fill="var(--panel)">200ms</text>
  <text x="10" y="68" font-size="8.5" fill="var(--s1)">hedged</text>
  <rect x="80" y="58" width="37" height="16" fill="var(--s1)"/><text x="120" y="71" font-size="8" fill="var(--ink)">35ms</text>
  <text x="10" y="98" font-size="7.5" fill="var(--muted)">cost: 1 extra request of 5 (only the slow one hedged)</text>
</svg>
^ The hedged tail bar is a fraction of the un-hedged one (35 vs 200ms), bought with a single extra request. The load cost is proportional to how much traffic is slower than the delay — here, one request in five.

Running the check confirms every clause, including that the tail is capped near delay + fallback and extra requests are bounded to the slow tail.

```text filename=hedged.py --check
  one request has a tail latency far above the median = True (200ms vs median 12ms)
  the hedge delay sits above the typical latency = True (20ms > 12ms)
  hedging caps the tail latency = True (35ms < 200ms)
  requests faster than the delay are unchanged (no hedge sent) = True
  hedging sends extra requests only for the slow tail = True (1 of 5)
  the hedged tail is capped near delay + fallback = True (35ms <= 35ms)
```

**The check ties the tail cut to a bounded extra-request count — the win is on the tail, the cost is only the slow minority — so hedging is shown as a targeted trade, not a blanket doubling of load.**

## Definition of done

Two properties close it, and they are the win and its price. Hedging must cap the tail (the effective max falls well below the un-hedged max) and it must send extra requests only for the slow tail (the fast majority never trigger it). The delay is what couples the two: set above typical latency, it makes the win big and the cost small.

```python filename=modules/ship-and-operate/code/hedged-inter-01/hedged.py:98-102 COMPLETE
    extra_bounded = extra < len(lat) and extra == sum(1 for o in lat if o > delay)
    print("  hedging sends extra requests only for the slow tail = %s (%d of %d)" % (extra_bounded, extra, len(lat)))

    tail_capped_near_delay = tail(hedged) <= delay + fb
    print("  the hedged tail is capped near delay + fallback = %s (%dms <= %dms)" % (tail_capped_near_delay, tail(hedged), delay + fb))
```

Three cautions keep hedging from being misapplied. First, the delay is the whole tuning knob: too low (below typical latency) and the hedge fires for most requests, doubling your load to chase latency you did not need to; set near the p95, only the slow tail hedges, and the extra load is a few percent. Second, hedging assumes the extra capacity exists and that replica slowness is independent — if the system is already overloaded, sending duplicates makes it worse, and if all replicas are slow together (a global cause, not a local hiccup), the hedge lands on another slow replica and buys nothing; some systems tie hedging to a load signal and disable it under pressure. Third, hedged requests must be safe to duplicate — a read is naturally idempotent, but hedging a non-idempotent write can execute it twice, so writes need idempotency keys or hedging must be restricted to reads. And to avoid the duplicate wasting work after the winner returns, the client should cancel the loser. Within those bounds, hedging is one of the highest-leverage tail-latency tools there is: a large p99 reduction for a small, self-limiting cost.

<svg role="img" aria-label="A dial of hedge delay: too low fires for most requests doubling load, near p95 fires only for the tail, too high barely helps the tail" viewBox="0 0 320 110">
  <line x1="20" y1="60" x2="300" y2="60" stroke="var(--line)" stroke-width="1"/>
  <circle cx="60" cy="60" r="4" fill="var(--s2)"/>
  <text x="30" y="40" font-size="7.5" fill="var(--s2)">delay too low</text>
  <text x="24" y="80" font-size="7" fill="var(--muted)">hedges most reqs</text>
  <text x="30" y="90" font-size="7" fill="var(--muted)">~2x load</text>
  <circle cx="160" cy="60" r="5" fill="var(--s1)"/>
  <text x="132" y="40" font-size="7.5" fill="var(--s1)">delay ≈ p95</text>
  <text x="126" y="80" font-size="7" fill="var(--muted)">hedges only the tail</text>
  <text x="140" y="90" font-size="7" fill="var(--muted)">few % load</text>
  <circle cx="270" cy="60" r="4" fill="var(--s2)"/>
  <text x="242" y="40" font-size="7.5" fill="var(--s2)">delay too high</text>
  <text x="244" y="80" font-size="7" fill="var(--muted)">tail barely cut</text>
</svg>
^ The hedge delay is the single tuning knob. Too low and it fires for nearly every request, roughly doubling load; too high and the slow request has almost finished before the hedge helps. Near the p95 it fires only for the tail — the sweet spot this fixture uses.

**Done means the tail is capped near the hedge delay and extra requests fire only for the slow minority — a large tail-latency win at a small, delay-tuned cost, valid for idempotent requests when spare capacity and replica independence hold.**

## Boss fight

Your service reads from a three-replica datastore, and p50 latency is great but p99 is terrible and spiky, tracking the garbage-collection pauses of whichever replica is currently collecting. A teammate proposes lowering the client timeout so slow requests fail fast and retry. Why is that worse than hedging, and how would you introduce hedging safely?

Lowering the timeout and retrying makes the tail worse, not better, in two ways. First, a retry only starts after the timeout expires, so the slow request pays the full timeout and then a fresh request's latency on top — the effective tail is timeout plus a normal response, which is larger than a hedge that fires early and runs concurrently. Second, timeout-and-retry converts slow requests into errors for anything that exhausts its retries, turning a latency problem into an availability problem, and if the timeout is tight it will also fail some requests that were merely normal-slow, adding load exactly when a replica is already struggling. Hedging is better because it runs the duplicate concurrently after a short delay well below the timeout, so the request completes when the fast replica answers rather than after the slow one times out, and it never turns a slow request into a failure. To introduce it safely: set the hedge delay around the current p95 (not lower) so only the genuine tail hedges and the added load is a few percent; restrict hedging to idempotent reads (the datastore reads here qualify) or use idempotency keys so a hedged write cannot double-apply; cancel the loser once the first response returns so the duplicate does not keep consuming a replica; and gate hedging on a load signal so it backs off when the whole cluster is hot (when replica slowness is correlated, hedging cannot help and only adds load). That gives you the p99 reduction from serving whichever replica is fast, without the failure and load-amplification of aggressive timeouts.

## External resources

Dean and Barroso, "The Tail at Scale" (Communications of the ACM, 2013) — the paper that named tail-tolerant techniques including hedged requests and tied requests, with the independence argument and the guidance to fire the hedge around the 95th percentile modeled here.

The gRPC and Envoy documentation on request hedging and retries — production implementations with hedge delay configuration, per-try timeouts, and the interaction with idempotency and load, the practical form of the mechanism in this module.
