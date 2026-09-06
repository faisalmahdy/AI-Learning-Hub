---
id: little-inter-01
title: Size the pool by Little's Law — concurrency is rate × latency, so a slower dependency silently caps your throughput
topic: orchestration-and-governance
level: intermediate
status: ready
time: 16 min
summary: A service serves each request by holding a slot — a connection, worker, or thread — for as long as the request takes, so the number of slots it needs is not the request rate but the rate times the latency. Little's Law makes it exact: the average number of in-flight requests L = arrival_rate × latency. Sizing the pool by peak rate ("200 req/s so 200 connections") confuses rate with concurrency and hides the real dependency. When a downstream call slows, the same requests arrive at the same rate but each holds its slot longer, so the concurrency needed rises — and a pool sized for the fast case caps throughput at pool/latency, below the offered load, with the backlog growing at the difference. On a fixture at a steady 200 req/s, a healthy 0.05 s dependency needs 10 slots (a 20-slot pool has room), but a slowed 0.25 s dependency needs 50; the fixed 20-slot pool then caps throughput at 20/0.25 = 80 req/s, 120 short, and resizing to rate × latency = 50 restores 200.
eli5: A checkout lane can ring up one cart at a time. How many lanes you need isn't how many shoppers arrive each minute — it's that number times how long each cart takes to ring up. If arrivals stay the same but every cart suddenly takes five times longer (a price check on every item), you need five times the lanes, or the line grows and never stops growing. Counting only how many shoppers show up per minute, and ignoring how long each takes, is how you end up with far too few lanes exactly when things get slow.
---

## Why this module

Throughput is not a property of your request rate alone — it is capped by how many requests you can hold at once divided by how long you hold each, so the moment latency rises, a pool sized without it throttles you below the load you were already serving.

The intuition that fails is treating a pool size as a rate. You see 200 requests per second on a dashboard and reach for 200 connections, as if each request needs its own slot for a full second. It does not. A request occupies a slot only while it is being served, and if that takes 0.05 seconds, the slot is free again 0.05 seconds later to take the next one. Little's Law names the exact relationship: the average number of requests in flight at any instant is L = arrival_rate × latency. At 200 req/s and 0.05 s each, only 10 are ever in flight together, so 10 slots carry the whole load and 200 would sit idle. Concurrency is rate times latency, and reading the rate alone tells you nothing about how many slots you need.

**The concurrency a service needs is arrival_rate × latency, not the arrival rate — so a pool sized from the request rate alone is sized against the wrong quantity and its real dependency, latency, is invisible until it moves.**

And latency moves. A downstream dependency slows under its own load, a database index goes cold, a network path degrades — the requests keep arriving at the same rate, but each now holds its slot longer, so L = rate × latency climbs. A fixed pool cannot climb with it. With C slots each freed every W seconds, the most the service can complete is C/W requests per second; when that ceiling falls below the arrival rate, requests queue faster than they drain and the backlog grows without bound. Nothing ran out of CPU. The service ran out of slots, because the one variable the rate-based sizing ignored — latency — is exactly the one that changed. This module computes the required concurrency, the throughput ceiling, and the resize that fixes it.

## Concepts

**Little's Law** states that in any stable system, the average number of items in it equals the arrival rate times the average time each spends in it: L = λ × W. For a request pool, L is the concurrency needed, λ the request rate, W the per-request latency.

**Required concurrency** is therefore rate × latency — the number of slots that must exist for the pool never to be the bottleneck. It is what you size to, and it rises and falls with latency at a fixed rate.

```python filename=modules/orchestration-and-governance/code/little-inter-01/little.py:42-44 COMPLETE
def required_concurrency(rate, latency):
    """Little's Law: the average number of in-flight requests L = arrival_rate * latency."""
    return rate * latency
```

**The throughput ceiling** of a fixed pool is pool ÷ latency: each of the C slots completes 1/W requests per second, so C slots complete C/W. This is the most the service can deliver, regardless of how many requests are offered.

```python filename=modules/orchestration-and-governance/code/little-inter-01/little.py:47-49 COMPLETE
def max_throughput(pool, latency):
    """The most requests per second `pool` slots can complete when each is held for `latency` seconds."""
    return pool / latency
```

<svg role="img" aria-label="Requests arrive at a rate, occupy slots for the latency duration, and the number in flight equals rate times latency; the pool must be at least that large" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">L in flight = arrival_rate × latency</text>
  <text x="4" y="46" fill="var(--muted)" font-size="7">λ in</text>
  <line x1="26" y1="42" x2="58" y2="42" stroke="var(--ink)"/><polygon points="58,39 64,42 58,45" fill="var(--ink)"/>
  <rect x="66" y="22" width="150" height="52" fill="none" stroke="var(--line)"/>
  <rect x="72" y="28" width="18" height="12" fill="var(--s1)"/><rect x="94" y="28" width="18" height="12" fill="var(--s1)"/><rect x="116" y="28" width="18" height="12" fill="var(--s1)"/>
  <rect x="72" y="44" width="18" height="12" fill="var(--s1)"/><rect x="94" y="44" width="18" height="12" fill="var(--s1)"/><rect x="116" y="44" width="18" height="12" fill="var(--muted)"/>
  <rect x="72" y="60" width="18" height="12" fill="var(--muted)"/><rect x="94" y="60" width="18" height="12" fill="var(--muted)"/><rect x="116" y="60" width="18" height="12" fill="var(--muted)"/>
  <text x="140" y="52" fill="var(--muted)" font-size="7">pool of slots</text>
  <line x1="216" y1="42" x2="248" y2="42" stroke="var(--ink)"/><polygon points="248,39 254,42 248,45" fill="var(--ink)"/><text x="238" y="36" fill="var(--muted)" font-size="7">done</text>
  <text x="6" y="92" fill="var(--muted)" font-size="8">each request holds a slot for `latency`; the pool must hold at least L of them at once</text>
  <text x="6" y="101" fill="var(--muted)" font-size="8">throughput ceiling = pool ÷ latency</text>
</svg>
^ Requests occupy slots for the latency duration; the number in flight is rate × latency, and a pool smaller than that cannot deliver more than pool ÷ latency per second.

**Size the pool to rate × latency, and track latency — because the request rate alone never tells you how many slots you need, and the throughput a fixed pool can deliver, pool ÷ latency, falls exactly when latency rises.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/little-inter-01/little.py

The fixture is a steady 200 req/s, a dependency that slows from 0.05 s to 0.25 s, and a pool sized once at 20 slots.

```json filename=modules/orchestration-and-governance/code/little-inter-01/little.json:3-6 COMPLETE
  "arrival_rate": 200,
  "latency_fast": 0.05,
  "latency_slow": 0.25,
  "pool_size": 20
```

Run `--size` to compute the concurrency Little's Law requires in each regime.

```text filename=--size
SIZE — Little's Law: concurrency needed = arrival_rate x latency (pool is fixed at 20)
--------------------------------------------------------------------
  offered load           = 200 req/s (unchanged)
  fast dependency 0.05s:  need L = 200 x 0.05 = 10 slots   pool 20 -> fits
  slow dependency 0.25s:  need L = 200 x 0.25 = 50 slots   pool 20 -> SHORT
--------------------------------------------------------------------
  same request rate; the slower dependency needs 5x the slots, and 20 no longer covers it.
```

At the healthy latency the service needs 10 slots, and the 20-slot pool looks generously sized — twice the requirement, exactly the kind of headroom that passes a capacity review. Then the dependency slows by 5×, from 0.05 s to 0.25 s, and the requirement jumps to 50 slots, because the same 200 requests each now camp on a slot five times as long. The pool did not change; the requirement did, and the comfortable 2× headroom became a 2.5× deficit. The request rate on the dashboard never moved, so nothing that watches only the rate would fire — the failure is entirely in the latency term that the pool size never accounted for. This is why a pool sized against the rate is a latent outage: it is correct until latency drifts, and then it is wrong by whatever factor latency drifted.

<svg role="img" aria-label="At fast latency the required 10 slots fit inside the 20-slot pool; at slow latency the required 50 slots overflow it" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">required slots (L = rate × latency) vs the fixed 20-slot pool</text>
  <line x1="70" y1="20" x2="70" y2="94" stroke="var(--ink)" stroke-dasharray="2 2"/><text x="58" y="18" fill="var(--muted)" font-size="7">pool 20 ↓</text>
  <text x="6" y="38" fill="var(--muted)" font-size="8">fast .05</text>
  <rect x="70" y="30" width="40" height="14" fill="var(--s1)"/><text x="114" y="41" fill="var(--muted)" font-size="7">need 10 — fits</text>
  <text x="6" y="68" fill="var(--muted)" font-size="8">slow .25</text>
  <rect x="70" y="60" width="200" height="14" fill="var(--s2)"/><text x="150" y="71" fill="var(--panel)" font-size="7">need 50 — overflows pool</text>
  <line x1="70" y1="56" x2="70" y2="78" stroke="var(--ink)"/>
  <text x="6" y="99" fill="var(--muted)" font-size="8">same 200 req/s; the requirement grew 5x with latency while the pool stayed 20</text>
</svg>
^ At 0.05 s the required 10 slots sit well inside the 20-slot pool; at 0.25 s the requirement is 50 and overflows the unchanged pool by 2.5×, though the request rate never moved.

## Build

What does the deficit actually do to throughput? Run `--throughput`.

```text filename=--throughput
THROUGHPUT — a fixed pool caps throughput at pool/latency once latency rises
------------------------------------------------------------------
  offered load                 = 200 req/s
  throughput ceiling pool/lat  = 20 / 0.25 = 80 req/s
  shortfall vs offered load    = 120 req/s
  backlog grows by             = 120 req/s
  pool needed for 200 req/s      = ceil(200 x 0.25) = 50 slots
```

The 20-slot pool at 0.25 s per request can complete at most 20/0.25 = 80 requests per second. The load is 200. So 80 drain and 120 pile up every second, a backlog that grows linearly and forever — latency for the queued requests climbs without bound until something upstream times out or sheds load. The service is not overloaded in any resource sense; CPU and memory may be near idle, because only 20 requests are ever being worked at once. It is *slot*-starved, and the ceiling that starved it, pool ÷ latency, is a number you can compute in advance from Little's Law. The fix is not more machines or faster code; it is 50 slots instead of 20, restoring the ceiling to 50/0.25 = 200 and clearing the backlog. Size to rate × latency and the ceiling always sits at or above the load; size to the rate and the ceiling is a hostage to latency.

<svg role="img" aria-label="Offered load is 200 req/s; the 20-slot pool caps throughput at 80, leaving a 120 backlog; resizing to 50 slots restores 200" viewBox="0 0 300 106" width="300" height="106">
  <text x="6" y="12" fill="var(--muted)" font-size="8">req/s: offered vs what the pool can drain</text>
  <line x1="60" y1="18" x2="60" y2="92" stroke="var(--grid)"/>
  <text x="6" y="30" fill="var(--muted)" font-size="8">offered</text>
  <rect x="60" y="22" width="200" height="12" fill="none" stroke="var(--ink)"/><text x="264" y="32" fill="var(--muted)" font-size="7">200</text>
  <text x="6" y="52" fill="var(--muted)" font-size="8">pool 20</text>
  <rect x="60" y="44" width="80" height="12" fill="var(--s2)"/><text x="144" y="54" fill="var(--muted)" font-size="7">80 drained</text>
  <rect x="140" y="44" width="120" height="12" fill="var(--muted)" opacity="0.5"/><text x="150" y="54" fill="var(--panel)" font-size="7">120 backlog/s →</text>
  <text x="6" y="74" fill="var(--muted)" font-size="8">pool 50</text>
  <rect x="60" y="66" width="200" height="12" fill="var(--s1)"/><text x="150" y="76" fill="var(--panel)" font-size="7">200 drained — clears</text>
  <text x="6" y="100" fill="var(--muted)" font-size="8">the only change is 20 → 50 slots, the Little's-Law number for 0.25 s</text>
</svg>
^ The 20-slot pool drains 80 of the offered 200 req/s and lets 120 pile up each second; sizing to the Little's-Law 50 slots restores the full 200 and clears the backlog.

## Definition of done

The self-test pins the whole chain: required concurrency is rate × latency, the fixed pool covers the fast case but not the slow, throughput caps below the load, the backlog grows, and resizing to the Little's-Law number restores the load.

```python filename=modules/orchestration-and-governance/code/little-inter-01/little.py:92-106 COMPLETE
    littles_law = required_concurrency(rate, wf) == rate * wf and required_concurrency(rate, ws) == rate * ws
    print("  required concurrency equals arrival_rate x latency = %s (%.0f fast, %.0f slow)"
          % (littles_law, required_concurrency(rate, wf), required_concurrency(rate, ws)))

    fits_when_fast = pool >= required_concurrency(rate, wf)
    print("  the fixed pool covers the fast case = %s (%d >= %.0f)" % (fits_when_fast, pool, required_concurrency(rate, wf)))

    short_when_slow = pool < required_concurrency(rate, ws)
    print("  the fixed pool is short once latency rises = %s (%d < %.0f)" % (short_when_slow, pool, required_concurrency(rate, ws)))

    throughput_capped = max_throughput(pool, ws) < rate
    print("  throughput is capped below the offered load = %s (%.0f < %d req/s)" % (throughput_capped, max_throughput(pool, ws), rate))

    backlog_grows = backlog_rate(rate, pool, ws) > 0
    print("  the backlog grows without bound = %s (+%.0f req/s)" % (backlog_grows, backlog_rate(rate, pool, ws)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — required concurrency = rate x latency; a fixed pool caps throughput below the load when latency rises
--------------------------------------------------------------------------------------------------------------------
  required concurrency equals arrival_rate x latency = True (10 fast, 50 slow)
  the fixed pool covers the fast case = True (20 >= 10)
  the fixed pool is short once latency rises = True (20 < 50)
  throughput is capped below the offered load = True (80 < 200 req/s)
  the backlog grows without bound = True (+120 req/s)
  sizing the pool to rate x latency restores the load = True (50 slots -> 200 req/s)
```

**Done means the throughput ceiling is proven to be a function of latency: required concurrency is rate × latency (10 slots at 0.05 s, 50 at 0.25 s), the fixed 20-slot pool covers the fast case but falls short when latency rises, capping throughput at 80 req/s against a 200 req/s load so the backlog grows by 120/s — and sizing the pool to the Little's-Law 50 restores the full 200.**

## Boss fight

Predict the two ways Little's Law bites back — the sizing that is correct on average but fails on the bursts, and the resize that makes everything worse. It is tempting to size to rate × average-latency and call the capacity solved.

The first trap is that Little's Law governs *averages*, and a pool sized to the average concurrency is under-provisioned exactly when it matters. Arrivals are not perfectly smooth and latency is not constant; both fluctuate, so instantaneous in-flight count swings above rate × mean-latency during bursts and tail-latency episodes. Size to the average and the pool saturates on every spike, queuing requests that a little headroom would have absorbed — which is why real pools are sized to a high percentile of the concurrency distribution, not its mean, and why the tail latency (not the average) often sets the requirement. The backlog term shows why this is unforgiving: any sustained interval where offered load exceeds pool/latency grows a queue that does not shrink until load drops below the ceiling, so a brief overload leaves a lasting backlog.

```python filename=modules/orchestration-and-governance/code/little-inter-01/little.py:52-54 COMPLETE
def backlog_rate(rate, pool, latency):
    """How fast the queue grows: offered load minus what the pool can drain (0 if the pool keeps up)."""
    return max(0.0, rate - max_throughput(pool, latency))
```

The second trap is that enlarging the pool can deepen the outage instead of fixing it. More slots means more concurrent requests hitting the slow dependency — and if the dependency slowed *because* it is overloaded, adding concurrency pours fuel on the fire: latency rises further, which by Little's Law demands still more slots, a feedback loop that ends in collapse. The honest fix when the downstream is the bottleneck is the opposite of more slots: cap concurrency to what the dependency can bear, shed or queue the excess with backpressure, and let latency recover — the pool is protecting the dependency, not just feeding it. So the resize in this module is right only when your own pool is the bottleneck and the dependency has spare capacity; when the dependency is saturated, Little's Law still tells you the truth (you need N slots to push rate × latency), but pushing that concurrency is exactly what you must not do. Read the law both ways: it sizes the pool when you have a healthy downstream, and it tells you how bad the amplification will be when you do not.

**Little's Law fixes the concurrency a service needs at rate × latency, so size the pool to a high percentile of that (not the average) and track latency, because the throughput ceiling pool/latency and the backlog it sheds both move with latency — but when a dependency slowed because it is overloaded, adding slots amplifies the overload, so cap concurrency and apply backpressure instead of enlarging the pool; the law tells you the number either way, and whether raising it helps depends on which side is the bottleneck.**

## External resources

Any queueing-theory or performance-engineering reference on Little's Law (L = λW) and its assumptions (a stable system observed over a long interval) — the derivation and the conditions under which the average relationship holds.

The Universal Scalability Law and writing on concurrency limits, backpressure, and load shedding (for example, adaptive concurrency limits and the TCP-Vegas-style controllers used in service meshes) — how real systems find and enforce the pool/latency ceiling under changing latency.

The companion "bound the queue and apply backpressure" and "send a backup request after a short delay" modules — backpressure is what you do when the pool/latency ceiling is below the load, and backup requests trade extra concurrency for lower tail latency, the same rate-latency-concurrency triangle from the other corner.
