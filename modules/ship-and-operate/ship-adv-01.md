---
id: ship-adv-01
title: A resilient request path — retry bounds, a circuit breaker, and recovery, composed
topic: ship-and-operate
level: advanced
status: ready
time: 12-16h
summary: When a downstream dependency goes down, a naive request path retries every failing request many times, so an outage of six requests becomes 60 downstream calls hammering a service that is already dead — a retry storm that turns the outage into a cascading failure. A resilient path composes three primitives: bounded retries give up on a request after a few tries, a circuit breaker opens after enough consecutive failures so further requests fail fast without calling the dependency at all, and half-open recovery probes once after a cooldown and closes the circuit when the probe succeeds. Composed, the same outage costs 5 downstream attempts instead of 60 — a twelvefold cut — the breaker opens once, three requests fast-fail with zero downstream calls, and the path recovers automatically when the service returns, all while completing the exact same requests the naive path did. Resilience is not one trick but the composition, and its payoff is the load it does not send to a dependency that cannot take it.
eli5: If a shop is closed, knocking on the door a hundred times will not open it — it just annoys everyone and makes it harder for the shop to reopen. A smart visitor knocks a couple of times, and if there is no answer, stops knocking for a while, then tries once more later to see if the shop is back. Same result — you still can't shop while it's closed — but you didn't pound the door into the ground, and you notice the moment it reopens.
---

## Why this module

Every resilience primitive in the ship track — bounded retries, the circuit breaker, dead-lettering, deadlines — is a partial answer to the same question: what does a request path do when its dependency fails. This module composes the retry bound, the circuit breaker, and its recovery into one path and measures the composition against the naive alternative during a downstream outage, because resilience is not any single mechanism but their assembly, and the assembly has a property none of the parts have alone: it stops your own system from turning a dependency's outage into a self-inflicted cascade.

The failure the composition prevents is the retry storm. When a dependency goes down, every in-flight and incoming request fails, and a naive path retries each one — and retries are load. Dozens or thousands of retries pile onto a service that is already struggling, so the instant it tries to recover it is knocked flat again, and the outage that might have lasted seconds lasts minutes. The caller caused that, by treating a failing dependency as a transient blip to retry through. The resilient path breaks the cycle with three composed mechanisms. Bounded retries cap how many times a single request calls the dependency. The circuit breaker watches for consecutive failures and, past a threshold, opens — failing subsequent requests fast, without calling the dependency at all, so the load drops to nearly zero while it is down. And half-open recovery, after a cooldown, lets one request through as a probe; if it succeeds the breaker closes and normal service resumes, so the path heals itself the moment the dependency returns. Composed, these produce the same user-visible outcome as the naive path — the outage requests still fail, because you cannot serve a request against a dead service — but with a fraction of the downstream load and automatic recovery.

You need the retry-bound and circuit-breaker modules (`ship-inter-04`) and the dead-letter idea (`govern-inter-06`). Everything runs offline against a traffic fixture — twelve requests over a downstream that is down for a six-request window — stdlib Python 3, `$0.00`. The up/down pattern is the fixture, so the run is deterministic. The instinct to unlearn is that resilience is a feature you add. It is a composition you assemble, and the whole is worth far more than the sum, because the parts interact: the retry bound feeds the breaker's failure count, the breaker's open state suppresses the load, and the recovery closes the loop.

Here is the naive path's retry storm:

```
# modules/ship-and-operate/code/ship-adv-01/ — COMPLETE, run from that directory
$ python3 path.py --naive

NAIVE — retry every request up to 10 times (no breaker)
------------------------------------------------------------------
  downstream attempts total:          66
  downstream attempts during outage:  60  (requests [3, 4, 5, 6, 7, 8] hammered)
  completed: [0, 1, 2, 9, 10, 11]
```

run: 2026-08-26 · deterministic; up/down is a fixture · 12 requests · `python3 path.py --naive`

Six outage requests generate 60 downstream calls, all failing, all pounding a dead dependency. The six completed requests are the ones outside the outage — the retries bought nothing during it. This module is that 60 turned into 5.

## Concepts

Named here so you can find them again; each is built below.

- **Retry storm** — many retries piling onto a failing dependency, deepening its outage.
- **Cascading failure** — a caller's retries preventing a dependency from recovering.
- **Bounded retry** — a cap on how many times one request calls the dependency.
- **Circuit breaker** — opening after consecutive failures to fail fast without calling the dependency.
- **Fast-fail** — rejecting a request with zero downstream calls while the breaker is open.
- **Half-open recovery** — probing once after a cooldown and closing the breaker if it succeeds.
- **Composition** — the three primitives assembled into one path, worth more than their sum.

## Worked example

Source: the resilient request path from distributed-systems practice (retry budgets, circuit breakers, and half-open probes as in Hystrix, resilience4j, and the SRE literature on cascading failures); the up/down pattern here stands in for a real outage so the downstream load and recovery are exact and checkable.

Script and fixture: `modules/ship-and-operate/code/ship-adv-01/` — `path.py`, and `traffic.json`, twelve requests, a downstream down for requests 3–8, and the protection config. Every command runs from there.

### The naive path: retry everything

The naive path retries every request up to a cap, with no memory that the dependency is down.

```
# path.py:40-53 — COMPLETE (retry every request; no breaker)
def run_naive(data):
    """Retry every request up to naive_retries. No breaker -> a retry storm during the outage."""
    up = data["up"]
    cap = data["naive_retries"]
    attempts = [0] * len(up)      # downstream attempts per request
    completed = []
    for i, ok in enumerate(up):
        for _ in range(cap):
            attempts[i] += 1
            if ok:
                completed.append(i)
                break
    return attempts, completed
```

Each request loops up to `cap` (10) times, calling the dependency each time, stopping only on success. During the outage every call fails, so every outage request burns all 10 attempts — 6 requests times 10 is 60 downstream calls, every one of them a knock on a door that will not open. The cap is the only thing bounding it; without even that, it is infinite. And crucially, nothing in this path notices that request 3 failing 10 times means requests 4 through 8 will also fail — it rediscovers the outage, expensively, on every single request.

### The resilient path: three primitives, one loop

The resilient path composes bounded retries, the breaker, and recovery. It is one loop with a small state machine.

```
# path.py:68-93 — COMPLETE (the composed path: bounded retries + breaker + half-open recovery)
    for i, ok in enumerate(up):
        if breaker_open:
            if i - opened_at >= cooldown:          # half-open: allow one probe
                attempts[i] += 1
                if ok:
                    breaker_open, consec = False, 0
                    disposition[i] = "probe-ok"     # recovered -> circuit closes
                else:
                    opened_at = i                   # probe failed -> stay open, reset cooldown
                    disposition[i] = "probe-fail"
            else:
                disposition[i] = "fast-fail"        # breaker open -> no downstream call at all
            continue
        # closed: bounded retries
        served = False
        for _ in range(max_retries):
            attempts[i] += 1
            if ok:
                served, consec = True, 0
                break
            consec += 1
            if consec >= threshold:
                breaker_open, opened_at, opens = True, i, opens + 1
                break
        disposition[i] = "ok" if served else "failed"
```

The state it carries is small — a consecutive-failure counter, the open flag, and when it opened:

```
# path.py:61-66 — COMPLETE (the composed path's state)
    attempts = [0] * len(up)
    disposition = ["" for _ in up]      # 'ok', 'failed', 'fast-fail', 'probe-ok', 'probe-fail'
    consec = 0
    breaker_open = False
    opened_at = None
    opens = 0
```

Trace the three mechanisms interacting. When the breaker is closed, a request retries up to `max_retries` (3), and each failure increments a consecutive-failure counter; when that counter hits `threshold` (3), the breaker opens. When the breaker is open, a request either fast-fails — returned immediately with zero downstream calls — or, once `cooldown` requests have passed since opening, becomes a probe: one call, and if it succeeds the breaker closes. The three primitives are not independent features bolted together; they share state. The retry bound feeds the breaker's counter, the breaker's open state gates the retries entirely, and the recovery reads the same open state. That shared state is what makes it a composition rather than a checklist.

<svg viewBox="0 0 700 180" role="img" aria-label="A three-state machine. CLOSED (calls with bounded retries) transitions to OPEN on 'threshold consecutive failures'. OPEN (fast-fail, no calls) transitions to HALF-OPEN after 'cooldown'. HALF-OPEN sends one probe: on success it goes to CLOSED (recovered), on failure back to OPEN.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the circuit breaker's three states (retries live inside CLOSED)</text>
    <circle cx="130" cy="100" r="48" fill="var(--acc-soft)" stroke="var(--acc-line)"></circle><text x="130" y="98" text-anchor="middle" fill="var(--acc-ink)">CLOSED</text><text x="130" y="112" text-anchor="middle" fill="var(--acc-ink)" font-size="7">retry, count fails</text>
    <circle cx="380" cy="100" r="48" fill="var(--panel)" stroke="var(--s2)"></circle><text x="380" y="98" text-anchor="middle" fill="var(--s2)">OPEN</text><text x="380" y="112" text-anchor="middle" fill="var(--s2)" font-size="7">fast-fail, no calls</text>
    <circle cx="600" cy="100" r="48" fill="var(--panel)" stroke="var(--line)"></circle><text x="600" y="98" text-anchor="middle" fill="var(--ink)">HALF-OPEN</text><text x="600" y="112" text-anchor="middle" fill="var(--ink)" font-size="7">one probe</text>
    <line x1="178" y1="92" x2="332" y2="92" stroke="var(--s2)"></line><text x="255" y="84" text-anchor="middle" fill="var(--s2)" font-size="7">threshold fails</text>
    <line x1="428" y1="100" x2="552" y2="100" stroke="var(--muted)"></line><text x="490" y="94" text-anchor="middle" fill="var(--muted)" font-size="7">cooldown</text>
    <path d="M 585 145 Q 350 200 145 145" fill="none" stroke="var(--s1)"></path><text x="360" y="185" text-anchor="middle" fill="var(--s1)" font-size="7">probe OK → recovered</text>
    <path d="M 600 148 Q 490 165 428 120" fill="none" stroke="var(--s2)" stroke-dasharray="3 2"></path><text x="520" y="150" fill="var(--s2)" font-size="7">probe fail</text>
  </g>
</svg>
^ Closed is normal service with bounded retries; enough consecutive failures open the breaker; after a cooldown it half-opens for one probe; the probe closes it on success or reopens it on failure. The retry bound lives inside the closed state, feeding the failure count that trips the transition.

### The disposition: what each request did

Run it and every request's fate is visible.

```
# $ python3 path.py --resilient
#   req  3  up=False attempts=3  failed      <- retries exhausted, breaker trips
#   req  4  up=False attempts=0  fast-fail   <- breaker open, no downstream call
#   req  5  up=False attempts=1  probe-fail  <- cooldown passed, probe fails, stay open
#   req  6  up=False attempts=0  fast-fail
#   req  7  up=False attempts=1  probe-fail
#   req  8  up=False attempts=0  fast-fail
#   req  9  up=True  attempts=1  probe-ok    <- outage over, probe succeeds, breaker closes
#   downstream attempts during outage: 5 (breaker opened 1 time(s))
```

run: 2026-08-26 · deterministic · `python3 path.py --resilient`

Follow the outage. Request 3 hits the down dependency, retries 3 times, exhausts its bound, and those 3 consecutive failures trip the breaker. Request 4 fast-fails — the breaker is open, so zero downstream calls. Requests 5 and 7 are probes (the cooldown has elapsed), each one call that fails and reopens; requests 6 and 8 fast-fail between them. Then the outage ends: request 9 is a probe, succeeds, and the breaker closes, so requests 10 and 11 are served normally. Total downstream attempts during the outage: 5 — request 3's three retries plus two probes — against the naive path's 60.

<svg viewBox="0 0 700 220" role="img" aria-label="Twelve requests across the timeline. Requests 0-2 served (up). Requests 3-8 during the outage: request 3 has three failed attempts and trips the breaker; 4,6,8 fast-fail with zero calls; 5,7 are single probe calls. Request 9 is a probe that succeeds and closes the breaker; 10,11 served. A shaded band marks the outage window, and a line shows the breaker open from request 3 to 9.">
  <g font-family="var(--mono)" font-size="8">
    <text x="20" y="16" fill="var(--muted)">the resilient path across the outage (bar height = downstream attempts)</text>
    <rect x="150" y="30" width="300" height="150" fill="var(--s2)" opacity="0.08"></rect>
    <text x="300" y="44" text-anchor="middle" fill="var(--s2)">outage window (req 3–8)</text>
    <line x1="40" y1="160" x2="660" y2="160" stroke="var(--grid)"></line>
    <g>
      <rect x="46" y="140" width="20" height="20" fill="var(--s1)"></rect><rect x="96" y="140" width="20" height="20" fill="var(--s1)"></rect><rect x="146" y="140" width="20" height="20" fill="var(--s1)"></rect>
      <rect x="196" y="100" width="20" height="60" fill="var(--s2)"></rect>
      <rect x="246" y="158" width="20" height="2" fill="var(--muted)"></rect>
      <rect x="296" y="140" width="20" height="20" fill="var(--s2)"></rect>
      <rect x="346" y="158" width="20" height="2" fill="var(--muted)"></rect>
      <rect x="396" y="140" width="20" height="20" fill="var(--s2)"></rect>
      <rect x="446" y="158" width="20" height="2" fill="var(--muted)"></rect>
      <rect x="496" y="140" width="20" height="20" fill="var(--s1)"></rect><rect x="546" y="140" width="20" height="20" fill="var(--s1)"></rect><rect x="596" y="140" width="20" height="20" fill="var(--s1)"></rect>
    </g>
    <g fill="var(--muted)" text-anchor="middle" font-size="7"><text x="56" y="175">0</text><text x="206" y="175">3</text><text x="256" y="175">4</text><text x="306" y="175">5</text><text x="356" y="175">6</text><text x="406" y="175">7</text><text x="456" y="175">8</text><text x="506" y="175">9</text></g>
    <text x="206" y="95" text-anchor="middle" fill="var(--s2)" font-size="7">3 tries → trip</text>
    <text x="256" y="188" fill="var(--muted)" font-size="7">fast-fail (0)</text>
    <text x="506" y="135" text-anchor="middle" fill="var(--s1)" font-size="7">probe-ok → close</text>
    <text x="40" y="205" fill="var(--muted)">tall bar = req 3 trips the breaker; near-zero bars after = fast-fails; req 9 probe recovers</text>
  </g>
</svg>
^ Only request 3 makes a full set of attempts; once the breaker opens, the outage requests barely touch the dependency (fast-fails at zero, probes at one), and request 9's probe closes the circuit. The tall bar plus a few slivers is the whole downstream load during an outage the naive path answered with 60 calls.

### The payoff: downstream load

Put the two paths' outage load side by side. This is the number that matters, because it is the load you send to a dependency that cannot take it.

```
# path.py:98-99 — COMPLETE (the outage window)
def outage_indices(data):
    return [i for i, ok in enumerate(data["up"]) if not ok]
```

The naive path sends 60 downstream calls during the outage; the resilient path sends 5. That is a twelvefold reduction in the load hitting a service precisely when it is least able to handle it. The naive path's retries are not resilience — they are an attack on your own dependency, indistinguishable from a denial-of-service, mounted by your own retry loop. The resilient path recognizes the outage after three failures and then essentially stops calling, which is the only humane thing to do to a service that is down: leave it alone so it can recover.

<svg viewBox="0 0 700 150" role="img" aria-label="Two horizontal bars of downstream attempts during the outage. Naive: a long bar at 60. Resilient: a tiny stub at 5. The resilient bar is about one twelfth the naive one.">
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="20" fill="var(--muted)">downstream calls during the outage (lower is kinder)</text>
    <text x="20" y="58" fill="var(--ink)">naive</text>
    <rect x="130" y="44" width="480" height="20" fill="var(--s2)"></rect><text x="618" y="59" fill="var(--s2)" font-size="9">60</text>
    <text x="20" y="98" fill="var(--ink)">resilient</text>
    <rect x="130" y="84" width="40" height="20" fill="var(--s1)"></rect><text x="178" y="99" fill="var(--s1)" font-size="9">5</text>
    <text x="130" y="128" fill="var(--muted)" font-size="8">same failed requests, same completions — 12x less load on the dependency that is down</text>
  </g>
</svg>
^ The resilient path sends a twelfth of the naive path's outage load. The user-visible outcome is identical — the outage requests fail either way — but the dependency is left alone to recover instead of being pounded.

### Same outcome, cheaper — and recovered

The crucial fairness check: the resilient path does not sacrifice successful requests to save load. Both paths complete the identical set — requests 0, 1, 2 (before) and 9, 10, 11 (after). You cannot serve a request against a down service, so the outage requests fail under both; the resilient path simply fails them cheaply (fast-fail, bounded retries) instead of expensively (a full retry storm each). And the resilient path recovers on its own: request 9's probe succeeds, the breaker closes, and normal service resumes with no operator intervention. The naive path, by contrast, would have kept storming had the outage continued, and only "recovers" in the sense that it never stopped trying.

**Resilience is the composition, not the parts: bounded retries feed a circuit breaker that opens to fail fast, and half-open recovery closes it when the dependency returns — together they cut downstream load during an outage by an order of magnitude and heal automatically, completing the same requests a naive retry path does without turning the outage into a cascade.**

### The self-test

The `--check` mode asserts the whole composition: the resilient path slashes downstream load, opens the breaker, fast-fails some requests, recovers, and completes the same requests as the naive path.

```
# $ python3 path.py --check
#   resilient cuts downstream load during the outage = True (5 vs 60 attempts)
#   the circuit breaker opened during the outage = True (1 time(s))
#   some outage requests fast-failed without a downstream call = True
#   the path recovered and served requests after the outage = True
#   both paths complete the same requests (resilient just fails cheaply) = True
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 path.py --check`

The load-protection assertion compares the two paths' outage-window downstream calls directly:

```
# path.py:134-139 — COMPLETE (the composition's load protection, measured)
    na, nc = run_naive(data)
    ra, rd, opens = run_resilient(data)

    naive_out = sum(na[i] for i in outage)
    res_out = sum(ra[i] for i in outage)
    protects = res_out < naive_out / 3
```

All five conditions must hold together for the composition to pass:

```
# path.py:158 — COMPLETE (the composition passes only if every guarantee holds)
    ok = protects and breaker_opened and fast_failed and recovered and same_completions
```

The `protects` line is the composition's reason to exist: the resilient outage load must be a fraction of the naive one, and if any of the three primitives were removed — unbounded retries, no breaker, no fast-fail — that reduction would collapse. The recovery and fairness assertions confirm the loop closes and no successful request is sacrificed:

```
# path.py:149-155 — COMPLETE (recovery, and identical completions across paths)
    recovered = "probe-ok" in rd and rd[-1] == "ok"

    naive_ok = set(nc)
    res_ok = {i for i, d in enumerate(rd) if d in ("ok", "probe-ok")}
    same_completions = naive_ok == res_ok
```

The `same_completions` line is the fairness anchor, proving the load savings cost no successful request: both paths complete the identical set, so resilience is free at the level of outcomes and pure gain at the level of load. The breaker and fast-fail assertions confirm the middle two mechanisms fired:

```
# path.py:143-147 — COMPLETE (the breaker opened and some requests fast-failed)
    breaker_opened = opens >= 1
    print("  the circuit breaker opened during the outage = %s (%d time(s))" % (breaker_opened, opens))

    fast_failed = "fast-fail" in rd
    print("  some outage requests fast-failed without a downstream call = %s" % fast_failed)
```

And `recovered` confirms the loop closes itself, which is what separates a composed path from one that merely gives up.

<svg viewBox="0 0 700 160" role="img" aria-label="A flow showing how the three primitives feed each other. Bounded retries produce a failure count, which feeds the circuit breaker, whose open state gates further retries (a back arrow) and whose recovery closes the loop. The three are chained, not independent.">
  <g font-family="var(--mono)" font-size="8">
    <text x="20" y="16" fill="var(--muted)">the primitives share state — a chain, not a checklist</text>
    <rect x="40" y="55" width="140" height="34" rx="4" fill="var(--panel)" stroke="var(--line)"></rect><text x="110" y="70" text-anchor="middle" fill="var(--ink)">bounded retries</text><text x="110" y="82" text-anchor="middle" fill="var(--muted)" font-size="7">cap per request</text>
    <path d="M180 72 L250 72" stroke="var(--muted)"></path><text x="215" y="66" text-anchor="middle" fill="var(--muted)" font-size="7">fail count</text>
    <rect x="250" y="55" width="140" height="34" rx="4" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="320" y="70" text-anchor="middle" fill="var(--acc-ink)">circuit breaker</text><text x="320" y="82" text-anchor="middle" fill="var(--acc-ink)" font-size="7">opens at threshold</text>
    <path d="M390 72 L460 72" stroke="var(--muted)"></path><text x="425" y="66" text-anchor="middle" fill="var(--muted)" font-size="7">open state</text>
    <rect x="460" y="55" width="140" height="34" rx="4" fill="var(--panel)" stroke="var(--line)"></rect><text x="530" y="70" text-anchor="middle" fill="var(--ink)">half-open recovery</text><text x="530" y="82" text-anchor="middle" fill="var(--ink)" font-size="7">probe → close</text>
    <path d="M320 89 Q 210 130 110 89" fill="none" stroke="var(--s2)" stroke-dasharray="3 2"></path><text x="215" y="128" text-anchor="middle" fill="var(--s2)" font-size="7">open → gates retries (no calls)</text>
    <path d="M530 89 Q 420 145 320 91" fill="none" stroke="var(--s1)"></path><text x="430" y="140" fill="var(--s1)" font-size="7">probe closes the breaker</text>
  </g>
</svg>
^ The retry bound produces the failure count the breaker trips on; the breaker's open state gates the retries (they stop calling); recovery closes the breaker. Remove any link and the chain breaks — which is why resilience is the composition, not any one box.

### The running tally

| path | outage downstream load | breaker | recovery | requests completed |
|---|---|---|---|---|
| naive | 60 | none | none (never stops) | 0,1,2,9,10,11 |
| resilient | 5 | opened once | probe-ok at req 9 | 0,1,2,9,10,11 |

Read the two rows: the completed column is identical, and every other column favors the composition. Same outcomes, a twelfth of the load, a breaker that contained the failure, and automatic recovery — none of which any single primitive delivers alone. A bounded retry alone still hammers (every request retries its bounded amount); a breaker without a retry bound trips on noisier signals; recovery without a breaker has nothing to recover. The value is in the assembly, and the assembly is the difference between a system that degrades gracefully under a dependency's failure and one that amplifies it.

### What we did not settle

This composes three primitives; a production path adds more and tunes each. Deadlines (from the deadline module) bound the total time including retries, so a request does not wait through its full retry budget past its SLA. Retries need backoff and jitter, not immediate re-fire, or even the bounded retries thunder in sync. The breaker is usually rate-based (open if more than X% of a window fails) rather than consecutive-count, which handles high-throughput services better. Dead-lettering (from the DLQ module) captures the failed requests for later, rather than dropping them. Load shedding and bulkheads isolate failures between dependencies. And the config — threshold, cooldown, retry count — must be tuned to real latency and failure patterns, not guessed. The invariant across all of it: bound the retries, break the circuit, fail fast while down, and recover on a probe — compose resilience, do not sprinkle it.

## Build

The build in one paragraph: assemble the request path as a composition — bound retries per request, feed their failures to a circuit breaker that opens past a consecutive (or rate) threshold, fail fast while open so the dependency is not called, and half-open after a cooldown to probe and recover; measure downstream load during a simulated outage and confirm it is a fraction of the naive path's while completing the same requests; and layer deadlines, backoff with jitter, and dead-lettering on top. Tune the thresholds to real failure data, and never ship unbounded retries.

We opened on the naive storm. The number that proves the composition works is the outage downstream load:

```
# modules/ship-and-operate/code/ship-adv-01/ — COMPLETE, run from that directory
$ python3 path.py --check
  resilient cuts downstream load during the outage = True (5 vs 60 attempts)
```

Now build your own. Compose bounded retries, a circuit breaker, and half-open recovery into a request path, and run it against a simulated downstream outage. Your number to beat is not the success rate — the outage requests fail either way; it is **the downstream load during the outage versus a naive retry path, which the composition must cut by an order of magnitude while completing the same requests**. Confirm the breaker opens and the path recovers. Bring back both paths' outage load and completed sets. Good luck.

## Definition of done

- [ ] A request path composing bounded retries, a circuit breaker, and half-open recovery
- [ ] A simulated downstream outage window
- [ ] A naive retry path for contrast, showing the retry storm
- [ ] Downstream load during the outage measured for both paths
- [ ] Confirmation the composition cuts outage load by an order of magnitude
- [ ] Confirmation the breaker opens, some requests fast-fail, and the path recovers on a probe
- [ ] Confirmation both paths complete the same requests
- [ ] `python3 path.py --check` printing SELF-TEST PASS: protects, breaker-opened, fast-failed, recovered, same-completions
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. What is a retry storm, and how does a naive retry path turn a dependency's outage into a cascading failure?
2. Name the three primitives the resilient path composes, and the state they share.
3. During the outage the resilient path made 5 downstream calls to the naive path's 60, yet completed the same requests. Explain how both are true.
4. What does half-open recovery do, and why is it what makes the path heal automatically?
5. Your own path was run against an outage. What was the downstream load under each path, did the breaker open, and did it recover?

## External resources

- Google SRE Book, *Addressing Cascading Failures* — my summary: how retries, overload, and slow recovery combine into cascades, and the retry budgets and circuit breakers that prevent them; read it for the operational theory this composition implements.
- resilience4j / Hystrix documentation on combined retry + circuit breaker + bulkhead — my summary: production libraries that compose exactly these primitives, with rate-based breakers and half-open probes; read it for the real APIs and the config knobs beyond the counts here.
- This hub, *ship-inter-04* and *govern-inter-06* — the circuit-breaker and dead-letter-queue modules this capstone composes; read them for each primitive in isolation before seeing them assembled into a request path.
