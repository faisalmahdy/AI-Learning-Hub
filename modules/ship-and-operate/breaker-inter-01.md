---
id: breaker-inter-01
title: Trip a circuit breaker when a dependency fails — without one, every request waits the full timeout and piles onto the outage
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: When a downstream dependency goes down, calls to it do not fail instantly — they hang until a timeout fires, so each attempt costs the full timeout, and each is load thrown onto a service already failing. A client that keeps calling a dead dependency on every request wastes its own capacity (threads and connections blocked on doomed calls, which can exhaust the client) and hammers the downstream exactly when the traffic most needs to stop. A circuit breaker is a small state machine in front of the dependency: it starts CLOSED, counts consecutive failures, and after a threshold trips OPEN, failing every call fast (returning immediately without touching the downstream). After a cooldown it goes HALF-OPEN and lets one probe through — closing if it succeeds, re-opening if it fails — so instead of attempting a dead service on every request it attempts it a handful of times and fails everything else fast. The trade-off is a small recovery latency: while OPEN it fails fast even after the dependency has quietly recovered, until the next probe finds it. On a fixture where the dependency is down for 10 ticks then up for 5, a no-breaker client attempts the down service all 10 times, while a breaker (threshold 3, cooldown 5) trips OPEN after 3 failures, probes at ticks 7 (still down, re-opens) and 12 (recovered, closes), attempting the down service only 4 times and fast-failing 8 requests.
eli5: If you keep phoning a shop whose line is dead, every call makes you wait for it to ring out, and you tie up your own phone doing it — over and over, for nothing. A smarter rule: after a few dead calls in a row, stop trying for a while and just assume it's closed, so you don't waste time. Every so often, place one test call to check if they're back; if they answer, resume normally, and if not, keep waiting. You spend a couple of calls finding out they're down and one every so often checking if they're up, instead of burning every call on a phone that isn't going to answer.
---

## Why this module

A dependency going down should be its problem, not yours — but the default behavior of a client makes the outage spread upward. Calls that hang on a timeout are the mechanism: they consume the caller's threads and connections while achieving nothing, and they keep pounding the failing service, so without a breaker a downstream outage becomes a client outage and the failing service never gets the quiet it needs to recover.

When a downstream dependency goes down, calls to it do not fail instantly — they hang until a timeout fires, so each attempt costs the full timeout, and every one of those attempts is load thrown onto a service that is already failing. A client that keeps calling a dead dependency on every request therefore does the worst possible thing twice over: it wastes its own capacity — threads or connections blocked on doomed calls, which can exhaust the client's own resources — and it hammers the downstream just when the downstream most needs the traffic to stop so it can recover. During an outage, the naive "just make the call" behavior turns a downstream failure into a client failure too.

A circuit breaker is a small state machine that sits in front of the dependency and stops calling it when it is clearly down. It starts CLOSED (calls pass through). It counts consecutive failures, and after a threshold it trips OPEN: now every call fails fast — it returns an error immediately without touching the downstream — which protects both sides. After a cooldown it moves to HALF-OPEN and lets a single probe call through: if the probe succeeds the dependency has recovered, so it closes; if the probe fails it re-opens for another cooldown. So instead of attempting a dead service on every request, the breaker attempts it a handful of times (the threshold plus one probe per cooldown) and fails everything else fast. This module runs both clients through a 10-tick outage.

**Without a circuit breaker a client calls a down dependency on every request, paying the full timeout each time and piling load onto the outage; a breaker trips OPEN after a threshold of consecutive failures to fail fast, probes HALF-OPEN after a cooldown, and closes on a successful probe — turning many wasted timeouts into a few probes.**

## Concepts

**The no-breaker client** attempts the downstream on every request, so during an outage it pays one full timeout per tick and dumps one failed request on the dependency per tick.

```python filename=modules/ship-and-operate/code/breaker-inter-01/breaker.py:48-50 COMPLETE
def run_no_breaker(health):
    """Attempt the downstream on every tick; count the attempts that hit a down service (each a wasted timeout)."""
    return sum(1 for h in health if h == "down")
```

**The OPEN state** is the fast-fail: once tripped, a request returns immediately without calling the downstream, until the cooldown elapses and the breaker allows one probe (HALF-OPEN).

```python filename=modules/ship-and-operate/code/breaker-inter-01/breaker.py:62-68 COMPLETE
        if state == "OPEN":
            if t - opened_at >= cooldown:
                state = "HALF_OPEN"
            else:
                fast_fails += 1
                trace.append((t, "OPEN", "fast-fail"))
                continue
```

**The transitions** on an actual call: a success closes the breaker (or confirms a probe), a failure increments the counter and trips OPEN at the threshold, and a failed probe from HALF-OPEN re-opens.

```python filename=modules/ship-and-operate/code/breaker-inter-01/breaker.py:74-87 COMPLETE
        else:
            attempts_down += 1
            if state == "HALF_OPEN":
                state = "OPEN"
                opened_at = t
                trace.append((t, "HALF_OPEN", "probe failed -> OPEN"))
            else:
                failures += 1
                if failures >= threshold:
                    state = "OPEN"
                    opened_at = t
                    trace.append((t, "CLOSED", "fail #%d -> trip OPEN" % failures))
                else:
                    trace.append((t, "CLOSED", "fail #%d" % failures))
```

<svg role="img" aria-label="The circuit breaker state machine: CLOSED trips to OPEN after threshold failures, OPEN moves to HALF-OPEN after a cooldown, HALF-OPEN closes on a successful probe or re-opens on a failed probe" viewBox="0 0 300 118" width="300" height="118">
  <text x="6" y="12" fill="var(--muted)" font-size="8">CLOSED → OPEN → HALF-OPEN → CLOSED (or back to OPEN)</text>
  <rect x="10" y="40" width="60" height="24" fill="none" stroke="var(--s1)"/><text x="24" y="55" fill="var(--muted)" font-size="8">CLOSED</text>
  <rect x="120" y="40" width="60" height="24" fill="none" stroke="var(--s2)"/><text x="134" y="55" fill="var(--muted)" font-size="8">OPEN</text>
  <rect x="228" y="40" width="66" height="24" fill="none" stroke="var(--line)"/><text x="236" y="55" fill="var(--muted)" font-size="7">HALF-OPEN</text>
  <line x1="70" y1="52" x2="120" y2="52" stroke="var(--muted)"/><text x="74" y="36" fill="var(--muted)" font-size="6">N failures</text>
  <line x1="180" y1="52" x2="228" y2="52" stroke="var(--muted)"/><text x="184" y="36" fill="var(--muted)" font-size="6">cooldown</text>
  <path d="M260,64 Q200,100 40,64" fill="none" stroke="var(--s1)"/><text x="120" y="100" fill="var(--muted)" font-size="6">probe ok → CLOSED</text>
  <path d="M240,64 Q210,84 182,64" fill="none" stroke="var(--s2)"/><text x="196" y="82" fill="var(--muted)" font-size="6">probe fails → OPEN</text>
  <path d="M40,40 Q40,24 55,24 Q70,24 68,40" fill="none" stroke="var(--muted)"/><text x="30" y="20" fill="var(--muted)" font-size="6">call ok</text>
</svg>
^ The breaker cycles CLOSED → (threshold failures) → OPEN → (cooldown) → HALF-OPEN, and from HALF-OPEN a successful probe returns it to CLOSED while a failed probe sends it back to OPEN — so it calls the downstream only while closed or on a single probe.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/breaker-inter-01/breaker.py

The fixture is a dependency down for 10 ticks then up for 5, with a 3-failure threshold and a 5-tick cooldown.

```json filename=modules/ship-and-operate/code/breaker-inter-01/breaker.json:3-5 COMPLETE
  "health": ["down", "down", "down", "down", "down", "down", "down", "down", "down", "down", "up", "up", "up", "up", "up"],
  "threshold": 3,
  "cooldown": 5
```

Run `--timeline` to watch the breaker's state.

```text filename=--timeline
TIMELINE — breaker state per tick (threshold 3, cooldown 5)
--------------------------------------------------------------
  tick 0   down    CLOSED      fail #1
  tick 1   down    CLOSED      fail #2
  tick 2   down    CLOSED      fail #3 -> trip OPEN
  tick 3   down    OPEN        fast-fail
  tick 4   down    OPEN        fast-fail
  tick 5   down    OPEN        fast-fail
  tick 6   down    OPEN        fast-fail
  tick 7   down    HALF_OPEN   probe failed -> OPEN
  tick 8   down    OPEN        fast-fail
  tick 9   down    OPEN        fast-fail
  tick 10  up      OPEN        fast-fail
  tick 11  up      OPEN        fast-fail
  tick 12  up      ->CLOSED    call ok
  tick 13  up      ->CLOSED    call ok
  tick 14  up      ->CLOSED    call ok
```

Follow the state column. Ticks 0–2 are CLOSED: the breaker lets the calls through, they fail, and on the third consecutive failure it trips OPEN. Ticks 3–6 are OPEN: every request fails fast, no downstream call, no wasted timeout. Tick 7 is HALF-OPEN — the cooldown of 5 has elapsed since it opened at tick 2 — so it sends one probe, which fails (still down) and re-opens. Ticks 8–11 fast-fail again, and note ticks 10 and 11: the service is *up* now, but the breaker is still OPEN and fast-failing, because it has not probed yet. Tick 12 is the next HALF-OPEN probe (5 ticks after re-opening at 7), it succeeds, and the breaker closes; ticks 13–14 pass through normally. The breaker actually attempted the dead service only at ticks 0, 1, 2, and 7 — four times — and everything else during the outage was a fast-fail. The two ticks of delayed recovery (10, 11) are the price of not hammering the service.

<svg role="img" aria-label="A 15-tick timeline: ticks 0-2 CLOSED with failures, ticks 3-11 mostly OPEN fast-failing with probes at 7 and 12, ticks 12-14 CLOSED after recovery; the service is down through tick 9 and up from tick 10" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">breaker state per tick (service down 0–9, up 10–14)</text>
  <text x="10" y="34" fill="var(--muted)" font-size="6">state</text>
  <g transform="translate(38,24)">
  <rect x="0" y="0" width="16" height="12" fill="var(--s1)"/><rect x="17" y="0" width="16" height="12" fill="var(--s1)"/><rect x="34" y="0" width="16" height="12" fill="var(--s1)"/>
  <rect x="51" y="0" width="16" height="12" fill="var(--s2)"/><rect x="68" y="0" width="16" height="12" fill="var(--s2)"/><rect x="85" y="0" width="16" height="12" fill="var(--s2)"/><rect x="102" y="0" width="16" height="12" fill="var(--s2)"/>
  <rect x="119" y="0" width="16" height="12" fill="var(--ink)"/>
  <rect x="136" y="0" width="16" height="12" fill="var(--s2)"/><rect x="153" y="0" width="16" height="12" fill="var(--s2)"/><rect x="170" y="0" width="16" height="12" fill="var(--s2)"/><rect x="187" y="0" width="16" height="12" fill="var(--s2)"/>
  <rect x="204" y="0" width="16" height="12" fill="var(--ink)"/>
  <rect x="221" y="0" width="16" height="12" fill="var(--s1)"/><rect x="238" y="0" width="16" height="12" fill="var(--s1)"/>
  </g>
  <text x="38" y="52" fill="var(--muted)" font-size="6">0  1  2   3  4  5  6   7   8  9 10 11  12  13 14</text>
  <text x="38" y="70" fill="var(--s1)" font-size="7">■ CLOSED (call)</text><text x="150" y="70" fill="var(--s2)" font-size="7">■ OPEN (fast-fail)</text><text x="38" y="84" fill="var(--ink)" font-size="7">■ HALF-OPEN probe (ticks 7, 12)</text>
  <text x="38" y="100" fill="var(--muted)" font-size="7">probe at 7 fails (still down); probe at 12 succeeds → CLOSED</text>
</svg>
^ The breaker calls the downstream only in the three CLOSED failure ticks and the two probe ticks; the long OPEN stretch fast-fails, and the probe at tick 12 discovers recovery — the OPEN ticks at 10–11 (service already up) are the recovery-latency cost.

## Build

The point is the load the breaker keeps off the failing dependency. Run `--compare`.

```text filename=--compare
COMPARE — downstream attempts during a 10-tick outage
----------------------------------------------------------
  no breaker : 10 attempts to the down service (all 10 wasted timeouts)
  breaker    : 4 attempts, 8 requests failed fast (no downstream call)
----------------------------------------------------------
  the breaker cut load on the failing service from 10 to 4.
```

Without the breaker the client attempts the down service on all 10 down ticks: 10 full timeouts burned in the client (each blocking a thread or connection for the timeout duration) and 10 failed requests piled onto a service that is trying to recover. With the breaker, the down service is attempted 4 times and 8 requests fail fast — returning an error immediately, in microseconds instead of a timeout, and adding nothing to the downstream's load. That is the double win: the client stops wasting its own capacity on doomed calls (so a slow dependency cannot exhaust the caller's thread pool and take the caller down too — the failure is contained), and the failing service gets a 60% reduction in the traffic hitting it, which is often exactly what it needs to catch up and recover. The whole simulation is just counting which requests actually reached the downstream.

```python filename=modules/ship-and-operate/code/breaker-inter-01/breaker.py:124-133 COMPLETE
    no_breaker_hits_all = nb == down_ticks
    print("  no-breaker attempts the down service on every down tick = %s (%d of %d)" % (no_breaker_hits_all, nb, down_ticks))

    trace, attempts, fast, final = run_breaker(health, thr, cd)
    breaker_attempts_fewer = attempts < nb
    print("  the breaker attempts the down service far fewer times = %s (%d < %d)" % (breaker_attempts_fewer, attempts, nb))

    trip_tick = next(t for t, s, note in trace if "trip OPEN" in note)
    trips_after_threshold = trip_tick == thr - 1
    print("  the breaker trips OPEN after exactly %d failures = %s (at tick %d)" % (thr, trips_after_threshold, trip_tick))
```

<svg role="img" aria-label="Downstream attempts during the outage: no breaker makes 10 attempts, the breaker makes 4 attempts and fails 8 fast" viewBox="0 0 300 110" width="300" height="110">
  <text x="6" y="12" fill="var(--muted)" font-size="8">load on the failing service: 10 attempts vs 4</text>
  <text x="10" y="40" fill="var(--muted)" font-size="7">no breaker</text>
  <g transform="translate(70,30)">
  <rect x="0" y="0" width="200" height="14" fill="var(--s2)"/><text x="204" y="10" fill="var(--muted)" font-size="7">10 attempts</text>
  </g>
  <text x="10" y="72" fill="var(--muted)" font-size="7">breaker</text>
  <g transform="translate(70,62)">
  <rect x="0" y="0" width="80" height="14" fill="var(--s2)"/><text x="8" y="10" fill="var(--panel)" font-size="6">4 attempts</text>
  <rect x="82" y="0" width="118" height="14" fill="none" stroke="var(--s1)"/><text x="120" y="10" fill="var(--muted)" font-size="6">8 fast-fail</text>
  </g>
  <text x="10" y="98" fill="var(--muted)" font-size="7">the breaker replaces most timeouts with instant fast-fails</text>
</svg>
^ The no-breaker client throws 10 attempts (10 wasted timeouts) at the down service; the breaker attempts it only 4 times and turns the other 8 requests into instant fast-fails that neither block the client nor load the dependency.

## Definition of done

The self-test pins the no-breaker load, the reduced breaker attempts, the trip point, the fast-fails, and the recovery. Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the no-breaker client attempts the down service every tick; the breaker trips after the threshold, fails fast, and recovers
--------------------------------------------------------------------------------------------------------------------------------
  no-breaker attempts the down service on every down tick = True (10 of 10)
  the breaker attempts the down service far fewer times = True (4 < 10)
  the breaker trips OPEN after exactly 3 failures = True (at tick 2)
  some requests failed fast without calling the downstream = True (8)
  the breaker closes again after the service recovers = True (ended CLOSED)
```

**Done means the breaker's protection and recovery are proven on the timeline: the no-breaker client attempts the down service all 10 times while the breaker attempts it only 4 (tripping OPEN after exactly 3 failures at tick 2, fast-failing 8 requests), and the breaker closes again once the service recovers — so the breaker caps the load on a failing dependency and the wasted timeouts in the client, at the cost of a small recovery delay.**

## Boss fight

Predict two ways a real breaker is more than "trip after N failures," because both the tripping condition and the shared state hide design decisions.

The first trap is that a raw consecutive-failure count is a crude trip condition, and production breakers trip on a *rate* over a window instead. Counting consecutive failures misses the common failure mode where a dependency is not fully down but degraded — succeeding 60% of the time and timing out 40% — which never produces N failures in a row yet is clearly unhealthy and should trip; and a single blip (one timeout among thousands of successes) should not trip a breaker that only looks at the last few. So real breakers track a failure *ratio* over a rolling window (say, "trip if >50% of the last 20 requests failed, given a minimum volume"), which catches partial degradation and ignores isolated errors. The threshold, window, and cooldown are all tuning knobs with a tension: trip too eagerly and you fast-fail a dependency that was fine (a false outage you inflicted); trip too reluctantly and you leave the client hammering a dead service. And the cooldown sets the recovery latency this module showed — too long and you keep rejecting a recovered service, too short and you keep probing a dead one and lose the protection. There is no universal setting; it depends on the dependency's failure and recovery profile.

The second trap is that a breaker protects a client, so *where* its state lives determines what it actually protects, and it must be paired with a fallback and with the other resilience patterns. A breaker per client instance means each process learns about an outage independently (each pays its own threshold of failures to trip), while a shared/coordinated breaker trips once for the whole fleet but adds coordination cost and a shared failure point — most systems use per-instance breakers for simplicity and accept the redundant discovery. More importantly, tripping OPEN only decides *not to call* the dependency; it does not decide what to return instead, so a breaker is only useful with a fallback — a cached value, a default, a degraded response, or a fast error the caller can handle — otherwise "fail fast" just moves the failure, it does not contain it. And the breaker composes with the rest of the incident-handling toolkit: it sits on top of per-call timeouts (which is what makes a failure detectable and bounded), it caps the retry amplification from the companion module (a breaker stops retries from stacking onto a dead service), and it works alongside bulkheads (isolating the thread pool for one dependency so its slowness cannot drain the whole client) and load shedding. The breaker is one instrument; resilience is the ensemble — timeout to bound the call, breaker to stop calling a dead dependency, fallback to answer without it, bulkhead to contain the blast radius.

**A production breaker trips on a failure ratio over a rolling window (not a raw consecutive count, which misses partial degradation and overreacts to blips), with threshold/window/cooldown tuned to the dependency's failure and recovery profile — and because a breaker only decides not to call, it is useful only with a fallback to answer without the dependency, and composes with per-call timeouts, retry limits, and bulkheads rather than replacing them.**

## External resources

Martin Fowler's "CircuitBreaker" article and the documentation for resilience libraries (Resilience4j, Polly, Hystrix) — the CLOSED/OPEN/HALF-OPEN state machine, rolling-window failure-rate tripping, and the fallback that pairs with a tripped breaker.

Google's SRE Book on handling overload and cascading failures — why a client hammering a failing dependency spreads the outage, and how breakers, timeouts, and load shedding together keep a downstream failure from becoming a client failure.

The companion retry-amplification and coordinated-omission modules in this topic — a breaker caps the retry storm a failing dependency would otherwise amplify, and the timeouts it depends on are exactly the latency a naive measurement (coordinated omission) under-reports during the incident.
