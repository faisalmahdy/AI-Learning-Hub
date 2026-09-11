---
id: ship-inter-18
title: Size the connection pool by Little's law — or a pool sized by request rate becomes the bottleneck
topic: ship-and-operate
level: intermediate
status: ready
time: 19 min
summary: Every request borrows a connection from a fixed pool, holds it for the downstream call's duration, then returns it. The tempting way to size the pool is by request rate — "we do 60 requests a second, give me 60 connections" — which ignores the number that actually decides capacity: how long each request holds its connection. A pool of N connections, each tied up for hold_time seconds, can only reuse a connection hold_time seconds after it is borrowed, so it completes at most N/hold_time requests per second. If each call takes 2 seconds, 60 connections complete only 30 requests a second, and the other half queue until they time out — the pool, not the downstream, is the bottleneck. Little's law gives the right size: pool ≥ arrival_rate × hold_time. On 60 req/s with 2s calls, that is 120 connections; a pool of 60 tops out at 30 req/s, a pool of 120 meets the 60.
eli5: A coat check with 60 hooks sounds like it can handle 60 people a second — but if each coat hangs there for two seconds before its owner leaves, a hook only frees up every two seconds, so you can really only take 30 people a second. The line backs up out the door. How many hooks you need depends not just on how fast people arrive but on how long each coat stays.
---

## Why this module

A connection pool's capacity is not how many connections it has — it is how many it can hand out and get back per second, and the "get back" half is the part rate-based sizing forgets.

Each request borrows a connection, holds it while the downstream call runs, and returns it. Size the pool by request rate — 60 requests a second, 60 connections — and you have silently assumed each connection is instantly reusable. It is not: a connection is tied up for the whole hold time, so a pool of N frees a connection only once every hold_time seconds per slot, capping throughput at N/hold_time. When calls take two seconds, sixty connections deliver thirty requests a second, and the arriving traffic that cannot get a connection queues. The queue grows without bound and latency climbs until requests time out — a self-inflicted outage from a pool that looked correctly sized.

**A pool completes N/hold_time requests per second, not N — so sizing by rate alone undersizes it by exactly the hold-time factor.**

Little's law names the right size: the number of connections in use equals arrival rate times hold time, so the pool must be at least that. This module computes each pool's throughput ceiling against demand and shows the rate-sized pool bottleneck while the Little's-law pool keeps up.

## Concepts

The **arrival rate** is how many requests per second come in. The **hold time** is how long one request keeps its connection — the downstream call's duration. These are two independent numbers, and capacity depends on both.

**Little's law** states that the average number of items in a system equals the arrival rate times the average time each spends there. Applied to a connection pool: connections in use = arrival_rate × hold_time. That product is the minimum pool size to keep up with demand.

The **throughput ceiling** of a pool is N/hold_time: each of the N connections becomes free again hold_time seconds after it is borrowed, so the pool can start at most N/hold_time new requests per second. If that ceiling is below the arrival rate, the pool is the bottleneck.

The mechanism of the failure is queueing. When arrival rate exceeds the ceiling, requests arrive faster than connections free up, so they wait for a connection. The wait grows every second the overload persists — this is an unstable queue, not a steady delay — and requests eventually breach their timeout. The downstream service may be perfectly healthy; the pool alone caused the outage.

**The pool size you need scales with hold time, so a pool that is fine for 200ms calls is catastrophically undersized when the same calls slow to 2s.**

Picture one connection's life: borrowed, held for the whole call, returned — so it can start a new request only once per hold time, and N of them start only N per hold time.

<svg role="img" aria-label="One connection's timeline shows it busy for the full hold time then free, so it can begin a new request only once every hold_time seconds" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="25" fill="var(--muted)" font-size="8">one connection over time →</text>
  <rect x="20" y="32" width="70" height="18" fill="var(--s2)"/>
  <text x="30" y="45" fill="var(--panel)" font-size="8">busy 2s</text>
  <rect x="92" y="32" width="70" height="18" fill="var(--ink)"/>
  <text x="102" y="45" fill="var(--panel)" font-size="8">busy 2s</text>
  <rect x="164" y="32" width="70" height="18" fill="var(--s2)"/>
  <text x="174" y="45" fill="var(--panel)" font-size="8">busy 2s</text>
  <line x1="20" y1="55" x2="20" y2="65" stroke="var(--s1)" stroke-width="1.5"/>
  <line x1="92" y1="55" x2="92" y2="65" stroke="var(--s1)" stroke-width="1.5"/>
  <line x1="164" y1="55" x2="164" y2="65" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="20" y="80" fill="var(--s1)" font-size="7">start</text>
  <text x="92" y="80" fill="var(--s1)" font-size="7">start</text>
  <text x="164" y="80" fill="var(--s1)" font-size="7">start</text>
  <text x="20" y="95" fill="var(--muted)" font-size="8">one start per hold time per connection → N/hold_time starts per second</text>
</svg>
^ A connection can begin a new request only when the previous one returns it, so each connection contributes 1/hold_time requests per second and the pool contributes N/hold_time.

That last point is the operational trap: hold time is not constant. A downstream slowdown lengthens the hold time, which lowers the pool's ceiling, which turns a comfortable pool into a bottleneck — an amplifier that converts a mild latency blip into a full outage.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/ship-inter-18/pool.py

The fixture is an arrival rate, a hold time, and three candidate pool sizes.

```json filename=modules/ship-and-operate/code/ship-inter-18/pool.json:1-11 COMPLETE
{
  "_meta": "A service that borrows a connection from a fixed pool for each request. arrival_rate is how many requests per second come in; hold_time is how many seconds each request keeps its connection (the downstream call's duration). A pool of N connections, each freed after hold_time, can complete at most N/hold_time requests per second (Little's law). pools are candidate pool sizes to evaluate against the demand.",
  "arrival_rate": 60,
  "hold_time": 2.0,
  "pools": {
    "by_rate": 60,
    "by_little": 120,
    "generous": 180
  }
}
```

The three quantities are three lines. The required pool is the Little's-law product; the throughput ceiling is N over hold time; keeping up is ceiling versus demand.

```python filename=modules/ship-and-operate/code/ship-inter-18/pool.py:42-53 COMPLETE
def required_pool(arrival_rate, hold_time):
    """Little's law: connections in use = arrival rate * hold time."""
    return arrival_rate * hold_time


def max_throughput(pool_size, hold_time):
    """The most requests per second a pool can complete: each connection frees every hold_time seconds."""
    return pool_size / hold_time


def keeps_up(pool_size, arrival_rate, hold_time):
    return max_throughput(pool_size, hold_time) >= arrival_rate
```

Run `--capacity` and read each pool's ceiling against the 60 req/s demand.

```text filename=--capacity
CAPACITY — throughput ceiling per pool (demand 60 req/s, hold 2.0s)
----------------------------------------------------------------
  by_rate     60 conns  ->   30.0 req/s   BOTTLENECK (30 short)
  by_little  120 conns  ->   60.0 req/s   meets demand
  generous   180 conns  ->   90.0 req/s   meets demand
----------------------------------------------------------------
  a pool completes N/hold_time req/s, not N req/s.
```

The rate-sized pool of 60 tops out at 30 req/s — half the demand, thirty requests a second short, and every one of those thirty queues. The Little's-law pool of 120 delivers exactly 60, meeting demand. The pool sized by the "obvious" rule is not slightly small; it serves half the traffic.

<svg role="img" aria-label="Throughput ceilings: by_rate pool reaches 30 req/s below the 60 demand line, by_little reaches 60, generous reaches 90" viewBox="0 0 300 140" width="300" height="140">
  <line x1="60" y1="15" x2="60" y2="110" stroke="var(--grid)" stroke-width="1"/>
  <line x1="60" y1="110" x2="285" y2="110" stroke="var(--grid)" stroke-width="1"/>
  <line x1="180" y1="15" x2="180" y2="110" stroke="var(--s1)" stroke-width="1" stroke-dasharray="3 2"/>
  <text x="150" y="26" fill="var(--s1)" font-size="8">demand 60</text>
  <rect x="60" y="30" width="60" height="16" fill="var(--s2)"/>
  <text x="10" y="42" fill="var(--muted)" font-size="8">by_rate</text>
  <text x="124" y="42" fill="var(--muted)" font-size="8">30</text>
  <rect x="60" y="55" width="120" height="16" fill="var(--ink)"/>
  <text x="10" y="67" fill="var(--muted)" font-size="8">by_little</text>
  <text x="184" y="67" fill="var(--muted)" font-size="8">60</text>
  <rect x="60" y="80" width="180" height="16" fill="var(--ink)"/>
  <text x="10" y="92" fill="var(--muted)" font-size="8">generous</text>
  <text x="244" y="92" fill="var(--muted)" font-size="8">90</text>
  <text x="60" y="128" fill="var(--muted)" font-size="8">bars past the dashed line meet demand; by_rate falls short</text>
</svg>
^ Only pools whose ceiling reaches the dashed demand line keep up — the rate-sized pool stops at 30, far short, because it counted connections without counting how long each is held.

## Build

The sizing view computes the required pool straight from the law and names the shortfall of the rate-only rule.

```python filename=modules/ship-and-operate/code/ship-inter-18/pool.py:70-76 COMPLETE
def sizing_view(data):
    rate, hold = data["arrival_rate"], data["hold_time"]
    req = required_pool(rate, hold)
    print("SIZING — the pool size Little's law requires")
    print("-" * 64)
    print("  required = arrival_rate * hold_time = %d * %.1f = %.0f connections" % (rate, hold, req))
    print("  sizing by rate alone would pick %d -- short by %.0f (a factor of %.1f)" % (rate, req - rate, hold))
```

Where did the factor of two go? Run `--sizing`.

```text filename=--sizing
SIZING — the pool size Little's law requires
----------------------------------------------------------------
  required = arrival_rate * hold_time = 60 * 2.0 = 120 connections
  sizing by rate alone would pick 60 -- short by 60 (a factor of 2.0)
----------------------------------------------------------------
  the missing factor is the hold time; ignore it and you undersize by exactly it.
```

The required pool is 60 × 2.0 = 120. Sizing by rate picks 60 — short by 60, a factor of exactly the hold time. That is the whole error in one line: the rate-based rule is Little's law with the hold-time factor dropped, so it undersizes by precisely that factor. At a half-second hold time it would over-provision; at two seconds it under-provisions two-to-one; the rule is only ever right by accident, when hold time happens to be one second.

<svg role="img" aria-label="Rate 60 times hold time 2 equals required 120; the by-rate rule keeps only the 60 and drops the times-2" viewBox="0 0 300 100" width="300" height="100">
  <text x="20" y="45" fill="var(--ink)" font-size="12">60</text>
  <text x="42" y="45" fill="var(--muted)" font-size="12">×</text>
  <text x="58" y="45" fill="var(--s1)" font-size="12">2.0</text>
  <text x="90" y="45" fill="var(--muted)" font-size="12">=</text>
  <text x="110" y="45" fill="var(--ink)" font-size="12">120 connections</text>
  <line x1="52" y1="52" x2="78" y2="52" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="40" y="72" fill="var(--s1)" font-size="8">by-rate drops this factor</text>
  <text x="20" y="92" fill="var(--muted)" font-size="8">the hold-time factor is the difference between 60 and the 120 you need</text>
</svg>
^ Little's law is rate times hold time; the rate-only rule keeps the rate and silently drops the hold-time factor, undersizing by exactly it.

## Definition of done

The self-test pins the law and the failure: the required pool is rate × hold, sizing by rate is undersized, the rate pool bottlenecks, the Little's-law pool meets demand, and the rate rule is exactly the law with the hold-time factor dropped.

```python filename=modules/ship-and-operate/code/ship-inter-18/pool.py:88-101 COMPLETE
    required_is_rate_times_hold = req == rate * hold
    print("  required pool = arrival_rate * hold_time = %s (%.0f)" % (required_is_rate_times_hold, req))

    by_rate_undersized = pools["by_rate"] < req
    print("  sizing by rate alone is undersized = %s (%d < %.0f)" % (by_rate_undersized, pools["by_rate"], req))

    by_rate_bottlenecks = not keeps_up(pools["by_rate"], rate, hold)
    print("  the by-rate pool cannot meet demand = %s (%.0f < %d req/s)" % (by_rate_bottlenecks, max_throughput(pools["by_rate"], hold), rate))

    by_little_meets = keeps_up(pools["by_little"], rate, hold)
    print("  the Little's-law pool meets demand = %s (%.0f >= %d req/s)" % (by_little_meets, max_throughput(pools["by_little"], hold), rate))

    hold_time_is_the_missing_factor = pools["by_rate"] == rate and abs(req - rate * hold) < 1e-9 and hold != 1.0
    print("  the by-rate rule drops the hold-time factor = %s (rate %d vs required %.0f)" % (hold_time_is_the_missing_factor, rate, req))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the by-rate pool bottlenecks; the Little's-law pool meets demand
------------------------------------------------------------------------------------------------
  required pool = arrival_rate * hold_time = True (120)
  sizing by rate alone is undersized = True (60 < 120)
  the by-rate pool cannot meet demand = True (30 < 60 req/s)
  the Little's-law pool meets demand = True (60 >= 60 req/s)
  the by-rate rule drops the hold-time factor = True (rate 60 vs required 120)
------------------------------------------------------------------------------------------------
SELF-TEST PASS  required_is_rate_times_hold=True  by_rate_undersized=True  by_rate_bottlenecks=True  by_little_meets=True  hold_time_is_the_missing_factor=True
```

**Done means the shortfall is derived from the law, not guessed: the required 120 is rate × hold, the rate-sized 60 delivers 30 req/s against 60 of demand, and the gap is exactly the hold-time factor.**

## Boss fight

The Little's-law pool of 120 meets demand exactly. Predict whether sizing it to precisely the required 120 is the right call in production. It is tempting to size to the number the law gives.

Sizing to exactly the average is a trap, because arrival rate and hold time are averages and real traffic is bursty. At 120 the pool has zero headroom: the instant a burst pushes arrivals above 60 or a downstream hiccup pushes hold time above 2s, the ceiling drops below demand and the queue starts growing. Little's law gives the floor, not the target — you provision above it for a safety margin, which is why the "generous" 180 exists. The discipline is to compute the floor from both factors, then add headroom for variance, not to skip the computation and hope a round number covers it.

The mirror-image mistake is treating hold time as fixed. The pool's ceiling is inversely proportional to hold time, so the most dangerous production event is a downstream slowdown: if hold time doubles to 4s, even the 120-connection pool now completes only 30 req/s and bottlenecks. This is why pools are paired with per-call timeouts — a timeout caps the hold time, which caps how far the ceiling can fall, keeping a slow dependency from silently converting your pool into the outage.

```python filename=modules/ship-and-operate/code/ship-inter-18/pool.py:47-49 COMPLETE
def max_throughput(pool_size, hold_time):
    """The most requests per second a pool can complete: each connection frees every hold_time seconds."""
    return pool_size / hold_time
```

**Size the pool from arrival_rate × hold_time and then add headroom, and cap hold time with a timeout — because the pool's capacity falls as the downstream slows, exactly when you can least afford it.**

## External resources

Little's law (L = λW) — any queueing-theory or operations text; the one-line result that a pool's occupancy is arrival rate times hold time, the whole basis of correct sizing.

The HikariCP "About Pool Sizing" wiki — a widely-cited practical treatment showing why bigger pools are not better and how to compute the size from throughput and latency.

Google's "Site Reliability Engineering", the "Addressing Cascading Failures" chapter — how an undersized resource plus a latency increase produces an unstable queue and a self-inflicted outage, the failure mode in the boss fight.
