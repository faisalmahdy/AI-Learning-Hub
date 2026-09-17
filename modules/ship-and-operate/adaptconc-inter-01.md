---
id: adaptconc-inter-01
title: Adapt the concurrency limit to the dependency's live capacity — a static limit overloads it when degraded or starves it when healthy
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: A concurrency limit caps how many requests a client keeps in flight to a dependency at once — the client-side analogue of a bulkhead. The dependency has a capacity C, the number of concurrent requests it serves at its baseline latency; send more than C and the surplus queues, so latency climbs roughly in proportion to how far concurrency overshoots capacity (Little's law made visible), and send fewer than C and the dependency sits partly idle while requests wait in your own queue. If C were constant you would set the limit to C and stop, but C varies: a dependency that serves 10 concurrent when healthy might serve only 2 when degraded, and no static limit is right for both — a limit tuned to the healthy capacity keeps ten requests hammering a dependency that can now handle two, driving latency up several-fold exactly when it is weakest, while a limit tuned to the degraded capacity throttles the client to a fraction of the throughput available when healthy. Adaptive concurrency limiting refuses the choice by measuring: it additively increases the limit while latency stays at baseline and multiplicatively decreases it when latency spikes — the same AIMD control that lets TCP find a link's capacity — so the limit tracks the current C, converging up when the dependency recovers and down when it degrades. On a fixture where the dependency serves 10 concurrent healthy and 2 degraded, a static limit of 10 gives baseline latency healthy but 50ms (5×) when degraded, a static limit of 2 is safe degraded but caps throughput at 2 of 10 when healthy, and the AIMD limit converges to 10 and to 2 respectively — right in both.
eli5: Imagine pouring water through a funnel. How fast you can pour depends on how wide the funnel's opening is right now — pour faster than it drains and it overflows; pour slower and you're wasting time. The catch is the opening changes size: sometimes wide, sometimes nearly clogged. If you pick one fixed pouring speed, you'll either overflow when it clogs or dribble when it's wide open. The smart way is to watch: pour a little faster as long as it's draining fine, and back off quickly the moment it starts backing up. That way you always pour at whatever speed the funnel can take right now. A concurrency limit is the pouring speed, the dependency is the funnel, and "watching for backup" is watching the latency.
---

## Why this module

Every client that calls a dependency has to decide how many requests to have outstanding at once, and the decision is usually made once, as a config value, and forgotten. That works while the dependency's capacity is stable and breaks the moment it is not — which is precisely during an incident, when the dependency slows down and the client keeps shoving the same number of requests at it. The concurrency limit that was fine yesterday becomes the thing amplifying today's outage.

The physics is Little's law: concurrency equals throughput times latency. A dependency has some capacity C it can serve at baseline latency; push concurrency past C and the extra requests queue, so latency rises and the client's requests spend their time waiting rather than being served. Below C, the client is leaving throughput unused. The right limit is C — but C is a moving target, dropping when the dependency degrades and rising when it recovers, and a single number cannot follow it.

The insight of adaptive concurrency limiting is that you do not need to know C; you can find it the way TCP finds a link's bandwidth, by probing and backing off. This module compares two static limits and an adaptive one across a healthy and a degraded regime.

**A dependency's capacity varies, so any static concurrency limit is wrong in some regime — too high overloads it when degraded, too low starves it when healthy — while an AIMD limit driven by latency converges to the current capacity in every regime.**

## Concepts

The fixture is a baseline latency, a latency threshold, two capacity regimes, and two static limits to compare against the adaptive one.

```json filename=modules/ship-and-operate/code/adaptconc-inter-01/adaptconc.json:3-7 COMPLETE
  "d0": 10,
  "threshold": 10,
  "regimes": {"healthy": 10, "degraded": 2},
  "static_high": 10,
  "static_low": 2
}
```

Latency is baseline up to capacity and rises with the overshoot beyond it; throughput is the smaller of the limit and the capacity. The AIMD controller additively increases the limit while latency is at or under the threshold and decreases it when latency spikes, returning the limit it settles at.

```python filename=modules/ship-and-operate/code/adaptconc-inter-01/adaptconc.py:32-49 COMPLETE
def latency(limit, capacity, d0):
    """Baseline latency up to capacity; above it, requests queue and latency rises with the overshoot."""
    return d0 if limit <= capacity else round(d0 * limit / capacity)


def throughput(limit, capacity):
    """Concurrent requests actually served: the smaller of the limit and the capacity."""
    return min(limit, capacity)


def aimd_limit(capacity, d0, threshold, rounds=40):
    """Additive-increase while latency is at/under threshold, decrease when it spikes; return the settled low limit."""
    limit, history = 12, []
    for _ in range(rounds):
        limit = limit + 1 if latency(limit, capacity, d0) <= threshold else limit - 1
        limit = max(1, limit)
        history.append(limit)
    return min(history[-8:])
```

The AIMD loop never reads the capacity directly — it only sees the latency its own limit produces, and moves the limit toward wherever latency is acceptable, which is exactly the current capacity.

<svg role="img" aria-label="Latency versus concurrency limit: flat at baseline up to the capacity, then rising steeply beyond it; a static-high limit sits past the degraded capacity in the rising region, the adaptive limit sits at the knee" viewBox="0 0 320 130">
  <line x1="30" y1="20" x2="30" y2="105" stroke="var(--line)" stroke-width="1"/>
  <line x1="30" y1="105" x2="300" y2="105" stroke="var(--line)" stroke-width="1"/>
  <text x="2" y="24" font-size="7" fill="var(--muted)">latency</text>
  <text x="250" y="118" font-size="7" fill="var(--muted)">concurrency limit</text>
  <polyline points="30,90 90,90 200,30" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="120" y="52" font-size="7" fill="var(--s1)">degraded (C=2): knee at 2</text>
  <line x1="90" y1="20" x2="90" y2="105" stroke="var(--ink)" stroke-width="0.8" stroke-dasharray="2 2"/><text x="72" y="16" font-size="6.5" fill="var(--ink)">C=2</text>
  <circle cx="90" cy="90" r="3" fill="var(--s1)"/><text x="60" y="102" font-size="6.5" fill="var(--s1)">adaptive sits here</text>
  <circle cx="200" cy="30" r="3" fill="var(--s2)"/><text x="150" y="30" font-size="6.5" fill="var(--s2)">static_high=10: far up the curve</text>
</svg>
^ Latency is flat until the concurrency limit reaches capacity, then rises steeply. When the dependency degrades to C=2, a static limit of 10 sits far up the rising part of the curve (high latency), while the adaptive limit settles at the knee where latency just starts to rise — the current capacity.

**The right limit is the knee of the latency curve, which is the current capacity; a static limit is fixed while that knee moves, and the AIMD controller follows it by reading only its own latency.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the concurrency-control step of a client calling a dependency, reduced to two regimes so every latency is checkable by hand.

Run `--regimes` to see each policy in each regime.

```text filename=adaptconc.py --regimes
  regime    cap   static_high(10)      static_low(2)       adaptive
  healthy   10    lat 10  thru 10      lat 10  thru 2       lat 10  thru 10 (L=10)
  degraded  2     lat 50  thru 2       lat 10  thru 2       lat 10  thru 2  (L=2)
```

Read the two static policies across the two rows. static_high (limit 10) is perfect when healthy — latency 10ms, full throughput 10 — but when the dependency degrades to capacity 2, ten in-flight requests against a two-wide dependency drive latency to 50ms, a 5× blowup, exactly when the dependency can least afford the load. static_low (limit 2) is the mirror image: safe when degraded (latency 10ms), but when the dependency is healthy it caps the client at 2 concurrent out of a possible 10, wasting 80% of the available throughput. Each static limit is right in one regime and wrong in the other. The adaptive limit reads latency 10ms and full throughput in both, because it converged to a different limit in each — 10 and 2.

Now `--adapt` runs the controller in each regime and reports where it settles.

```python filename=modules/ship-and-operate/code/adaptconc-inter-01/adaptconc.py:74-76 COMPLETE
    for name, C in data["regimes"].items():
        aL = aimd_limit(C, d0, thr)
        print("  %-8s  capacity %-3d  ->  adaptive limit converges to %d" % (name, C, aL))
```

It lands on the capacity it never saw.

```text filename=adaptconc.py --adapt
  healthy   capacity 10   ->  adaptive limit converges to 10
  degraded  capacity 2    ->  adaptive limit converges to 2
```

The controller was never told the capacity. In the healthy regime it probed upward — latency stayed at baseline as the limit rose — until it reached 10, where pushing further would raise latency, and it settled there. In the degraded regime the same controller found latency spiking above baseline and backed off until it reached 2, the new capacity. One control law, no per-regime tuning, tracking a capacity it only ever observed through latency. That is the whole value: the operator does not choose the limit for each regime; the controller discovers it.

<svg role="img" aria-label="Bars: static_high fine healthy but 50ms degraded, static_low starves healthy throughput, adaptive good in both regimes" viewBox="0 0 320 130">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">is the policy right in the regime? (need: baseline latency AND full throughput)</text>
  <text x="10" y="36" font-size="8" fill="var(--s2)">static_high</text>
  <rect x="90" y="28" width="60" height="12" fill="var(--s1)"/><text x="154" y="38" font-size="7" fill="var(--s1)">healthy OK</text>
  <rect x="200" y="28" width="60" height="12" fill="var(--s2)"/><text x="264" y="38" font-size="7" fill="var(--s2)">degraded 50ms</text>
  <text x="10" y="60" font-size="8" fill="var(--s2)">static_low</text>
  <rect x="90" y="52" width="60" height="12" fill="var(--s2)"/><text x="154" y="62" font-size="7" fill="var(--s2)">healthy thru 2/10</text>
  <rect x="200" y="52" width="60" height="12" fill="var(--s1)"/><text x="264" y="62" font-size="7" fill="var(--s1)">degraded OK</text>
  <text x="10" y="84" font-size="8" fill="var(--s1)">adaptive</text>
  <rect x="90" y="76" width="60" height="12" fill="var(--s1)"/><text x="154" y="86" font-size="7" fill="var(--s1)">healthy OK</text>
  <rect x="200" y="76" width="60" height="12" fill="var(--s1)"/><text x="264" y="86" font-size="7" fill="var(--s1)">degraded OK</text>
  <text x="10" y="112" font-size="7.5" fill="var(--muted)">each static limit fails one regime; the adaptive limit is right in both</text>
</svg>
^ Each static limit is right in exactly one regime — static_high fails degraded (50ms), static_low fails healthy (throughput 2 of 10) — while the adaptive limit is right in both, because it converged to the capacity of each.

**static_high gives 50ms latency when degraded and static_low caps throughput at 2 of 10 when healthy, but the adaptive limit converges to 10 and to 2 — baseline latency and full throughput in both regimes, from a controller that only ever read latency.**

## Build

The self-test establishes that each static limit fails one regime: static_high overloads the degraded dependency, and static_low starves the healthy one.

```python filename=modules/ship-and-operate/code/adaptconc-inter-01/adaptconc.py:88-96 COMPLETE
    static_high_overloads_degraded = latency(hi, degraded, d0) > 2 * d0
    print("  static_high overloads the degraded dependency = %s (%dms latency)" % (static_high_overloads_degraded, latency(hi, degraded, d0)))

    static_low_starves_healthy = throughput(lo, healthy) < healthy
    print("  static_low starves the healthy dependency = %s (throughput %d of %d)" % (static_low_starves_healthy, throughput(lo, healthy), healthy))

    ah, ad = aimd_limit(healthy, d0, thr), aimd_limit(degraded, d0, thr)
    adaptive_tracks_capacity = ah == healthy and ad == degraded
    print("  the adaptive limit converges to the capacity in each regime = %s (%d, %d)" % (adaptive_tracks_capacity, ah, ad))
```

Then the payoff: the adaptive limit keeps latency at baseline and uses the full capacity in both regimes.

```python filename=modules/ship-and-operate/code/adaptconc-inter-01/adaptconc.py:98-101 COMPLETE
    adaptive_bounded_latency = latency(ah, healthy, d0) <= thr and latency(ad, degraded, d0) <= thr
    print("  adaptive keeps latency at baseline in both regimes = %s" % adaptive_bounded_latency)

    adaptive_full_throughput = throughput(ah, healthy) == healthy and throughput(ad, degraded) == degraded
    print("  adaptive uses the full capacity in both regimes = %s" % adaptive_full_throughput)
```

Running the check confirms every clause.

```text filename=adaptconc.py --check
  static_high overloads the degraded dependency = True (50ms latency)
  static_low starves the healthy dependency = True (throughput 2 of 10)
  the adaptive limit converges to the capacity in each regime = True (10, 2)
  adaptive keeps latency at baseline in both regimes = True
  adaptive uses the full capacity in both regimes = True
```

**The check shows each static limit failing a different regime while the adaptive limit converges to the capacity in both, keeping latency at baseline and throughput full — the controller tracking a capacity it only observed through latency.**

## Definition of done

Done means each static limit is shown to fail one regime (overload or starvation) and the adaptive limit to track the capacity in both, holding latency at baseline and throughput full. The pairing of the two static failures is the argument: it is not that a better static number exists, but that the two regimes demand different numbers, so any single value is wrong somewhere and only an adaptive limit escapes the tradeoff.

Two clarifications ground this in real systems. First, the latency model here is a clean stand-in; real controllers use a robust signal and a gentler law. Netflix's concurrency-limits library and similar implementations track a rolling minimum RTT as the baseline and compare the current RTT (or its gradient) against it, increasing the limit while the ratio is near one and decreasing it as latency inflates — a gradient or AIMD update that hunts around the capacity rather than snapping to it, and that tolerates noise better than a single-sample threshold. The convergence is the same idea this module shows; the production robustness is in the signal choice and the update smoothing. Second, adaptive concurrency limiting composes with, and does not replace, the other resilience tools: a load shedder still rejects work when even the adaptive limit's queue is full, a circuit breaker still trips when a dependency fails outright rather than merely slows, and per-dependency bulkheads still isolate one dependency's limit from another's. What the adaptive limit adds is that the size of each bulkhead is no longer a guess frozen at deploy time but a value that follows the dependency's real, current capacity — which is the only thing that is right in every regime.

<svg role="img" aria-label="Adaptive concurrency limiting uses a rolling minimum RTT as baseline and adjusts the limit by the latency gradient, composing with load shedding, circuit breakers, and per-dependency bulkheads" viewBox="0 0 320 120">
  <rect x="14" y="22" width="150" height="40" fill="none" stroke="var(--s1)"/>
  <text x="22" y="37" font-size="7.5" fill="var(--s1)">adaptive limit (AIMD)</text>
  <text x="22" y="49" font-size="7" fill="var(--ink)">baseline = rolling min RTT,</text>
  <text x="22" y="58" font-size="7" fill="var(--ink)">adjust by latency gradient</text>
  <rect x="176" y="22" width="130" height="40" fill="none" stroke="var(--s2)"/>
  <text x="184" y="37" font-size="7.5" fill="var(--s2)">composes with</text>
  <text x="184" y="49" font-size="7" fill="var(--ink)">load shed, breaker,</text>
  <text x="184" y="58" font-size="7" fill="var(--ink)">per-dependency bulkheads</text>
  <text x="14" y="84" font-size="7.5" fill="var(--muted)">the adaptive limit sizes each bulkhead to the dependency's live capacity</text>
  <text x="14" y="104" font-size="7.5" fill="var(--ink)">no frozen guess — the one value that is right in every regime is the measured one</text>
</svg>
^ Real adaptive limiters use a rolling minimum RTT as the baseline and adjust by the latency gradient, and they compose with load shedding, circuit breakers, and per-dependency bulkheads — sizing each bulkhead to the dependency's live capacity instead of a deploy-time guess.

**Done means each static limit fails a different regime while the adaptive limit tracks the capacity in both — so the concurrency limit is set by an AIMD controller reading latency (rolling-min-RTT baseline in production), composing with shedding, breakers, and bulkheads rather than frozen as a guess.**

## Boss fight

A service calls a database with a fixed connection-pool size of 50, tuned during a load test to maximize throughput. It runs well for months, but during a database incident where queries slowed down, the service's own latency exploded and it started timing out on nearly every request, making the incident far worse than the database slowdown alone would suggest. The pool size had been carefully chosen. What went wrong, and how would you make the pool robust?

The fixed pool size was tuned for the database's healthy capacity and became far too large when the database degraded. A connection pool is a concurrency limit: 50 outstanding queries is right when the database can serve 50 concurrently at low latency, but when the database slowed, its effective concurrent capacity dropped sharply, so 50 in-flight queries piled into its queue, each waiting behind the others. By Little's law, holding concurrency at 50 against a database that can now only serve a handful means latency rises in proportion to the overshoot — which is the service's latency exploding — and once requests take longer than the timeout, nearly all of them fail, turning a database slowdown into a near-total outage. The carefully chosen number was correct for exactly one regime and catastrophically wrong for the one that mattered. The fix is to make the effective concurrency adapt to the database's current capacity rather than staying pinned at the load-test value: add an adaptive concurrency limiter in front of the database calls that tracks query latency — using a rolling minimum RTT as the baseline and reducing the in-flight limit when latency inflates above it, increasing it again as the database recovers — so during the incident the limit shrinks to what the database can actually serve, keeping per-query latency bounded and shedding or queuing the rest rather than dogpiling. Pair it with a timeout and a load shedder so that requests which cannot be served promptly fail fast instead of consuming a connection, and keep the pool as an upper bound (it caps resources) while the adaptive limiter sets the real operating concurrency below it. The general lesson: any fixed concurrency limit — thread pool, connection pool, semaphore — is a guess about a capacity that changes, and during an incident the capacity changes against you, so the limit should track measured latency rather than a number frozen at deploy time.

## External resources

Netflix's adaptive concurrency limits work (the concurrency-limits library and the writeups on applying TCP-congestion-control-style AIMD/gradient algorithms to service concurrency) — the rolling-minimum-RTT baseline, the gradient update, and why an adaptive limit outperforms a static one across changing capacity.

Background on Little's law and its use in capacity and concurrency reasoning (queueing-theory treatments and SRE material on concurrency = throughput × latency) — the relationship this module models between concurrency, capacity, and latency, and why overshooting capacity inflates latency.
