---
id: deadline-inter-01
title: Propagate the deadline down the call chain — a hop with its own timeout runs work the caller already gave up on
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: A request that fans out through several backend hops — gateway to auth to database — inherits one end-to-end deadline from the client: answer within 100ms or the client gives up. The natural way to enforce it is to give each hop its own timeout, and it wastes work, because a per-hop timeout knows only its own hop and nothing about how much of the shared budget the earlier hops already spent. A late hop, starting with almost none of the budget left, still measures itself against its own fresh timeout and runs to completion, producing a result the client stopped waiting for — work that consumed a thread, a connection, a query, and was then discarded. Under load this is how one slow dependency fills a backend with threads computing answers nobody awaits. The fix carries the deadline itself down the chain instead of a fixed per-hop timeout: each hop receives how much budget remains, and before starting real work checks whether that is even enough to finish; if not, it fails fast, doing none of the doomed work and returning deadline-exceeded up the chain. The request still fails — it was always going to miss the deadline — but it fails without a downstream service burning its full cost on a doomed call. On a fixture with a 100ms budget and hops costing 30 + 40 + 50 = 120ms, per-hop timeouts run the last hop (db) its full 50ms starting at elapsed 70ms and finishing at 120ms — 50ms of doomed work — while deadline propagation has db see 30ms remaining against its 50ms cost, refuse immediately, do 0ms of doomed work, and free the backend at 70ms instead of 120ms.
eli5: Imagine you send a friend to buy you lunch and tell them "I'm leaving in ten minutes, be back by then or don't bother." They stop at the sandwich shop, then the bakery, and by the time they reach the coffee counter there are only two minutes left but the coffee takes five. If each stop just follows its own little rule ("always finish what you started"), they buy the coffee anyway — and come back after you have already left, holding a lunch nobody is waiting for. The smarter rule is to carry the real deadline with them: at the coffee counter they check the clock, see there is not enough time, and skip it right away instead of wasting five minutes and money on a coffee that will arrive too late. You still miss lunch either way — but this way your friend does not burn time and money on something already doomed.
---

## Why this module

A single client request rarely touches one service. It fans out — an API gateway calls an auth service, which calls a database, which might call a cache — and the client is holding one stopwatch over the whole thing: reply within 100 milliseconds or I give up. The question every backend has to answer is how to enforce that end-to-end deadline across hops that each know only about themselves. The obvious answer, a timeout per hop, is the one that quietly wastes the most resources under load, and the reason is worth seeing because it is invisible until traffic spikes.

A per-hop timeout is local. The database's 100ms timeout does not know that the gateway and auth already spent 70ms of the shared budget before the call arrived. So the database, starting with 30ms of real budget left, still measures itself against its own fresh 100ms, runs its full query, and hands back an answer at 120ms — twenty milliseconds after the client stopped listening. The query ran. It held a connection and a worker thread and did real I/O, and then its result was thrown on the floor. One slow dependency, multiplied across every in-flight request, fills the backend with threads computing answers no one is waiting for, and that is how a small slowdown becomes a cascading outage.

The fix is to make the deadline travel with the request instead of resetting at each hop. This module runs the same three-hop chain both ways and measures the doomed work each does.

**Propagate the request's remaining deadline down every hop of a call chain — each hop failing fast when the budget left is smaller than its own work — rather than giving each hop an independent fixed timeout, because an independent timeout lets a late hop run its full duration on a request whose deadline has already passed, burning downstream resources for a result the caller abandoned.**

## Concepts

The fixture is one request through three hops under a single 100ms budget. Gateway costs 30ms, auth 40ms, db 50ms — summing to 120ms, which is the whole point: the request is doomed before it starts, because the work needed exceeds the time allowed.

```json filename=modules/ship-and-operate/code/deadline-inter-01/deadline.json:14-19 COMPLETE
  "budget_ms": 100,
  "chain": [
    {"service": "gateway", "cost_ms": 30},
    {"service": "auth", "cost_ms": 40},
    {"service": "db", "cost_ms": 50}
  ]
```

Under independent per-hop timeouts, every hop simply runs its full cost. The simulation records each hop's start (the elapsed time when it begins) and finish, and marks a hop's work doomed when it starts with less budget remaining than it needs — that is exactly the condition a per-hop timeout is blind to, and it runs the work anyway.

```python filename=modules/ship-and-operate/code/deadline-inter-01/deadline.py:47-59 COMPLETE
def run_independent(budget, chain):
    """Per-hop timeouts: every hop runs its full cost regardless of the shared budget. Returns per-hop timing and doomed-work total."""
    elapsed = 0
    rows = []
    doomed = 0
    for hop in chain:
        start = elapsed
        remaining = budget - start
        finishes_in_time = hop["cost_ms"] <= remaining
        elapsed += hop["cost_ms"]
        if not finishes_in_time:
            doomed += hop["cost_ms"]
        rows.append({"service": hop["service"], "cost": hop["cost_ms"], "start": start, "finish": elapsed, "in_time": finishes_in_time})
    return rows, doomed, elapsed
```

Deadline propagation runs the same chain but makes the check the per-hop timeout could not: before each hop starts, compare the remaining budget to the hop's cost, and if the work will not fit, stop the chain there without running it. That is the whole difference — the same comparison, made before the work instead of never.

```python filename=modules/ship-and-operate/code/deadline-inter-01/deadline.py:62-79 COMPLETE
def run_propagated(budget, chain):
    """Deadline propagation: each hop checks the remaining budget and fails fast if it cannot finish. Returns timing and where it stopped."""
    elapsed = 0
    rows = []
    doomed = 0
    stopped_at = None
    for hop in chain:
        start = elapsed
        remaining = budget - start
        if hop["cost_ms"] > remaining:
            rows.append({"service": hop["service"], "cost": hop["cost_ms"], "start": start, "finish": start, "ran": False})
            stopped_at = hop["service"]
            break
        elapsed += hop["cost_ms"]
        rows.append({"service": hop["service"], "cost": hop["cost_ms"], "start": start, "finish": elapsed, "ran": True})
    return rows, doomed, elapsed, stopped_at
```

<svg role="img" aria-label="A timeline from 0 to 120ms with a deadline line at 100ms; gateway 0-30, auth 30-70 both left of the line, db 70-120 crossing past it" viewBox="0 0 330 130">
  <line x1="20" y1="95" x2="310" y2="95" stroke="var(--line)" stroke-width="1"/>
  <line x1="260" y1="25" x2="260" y2="105" stroke="var(--ink)" stroke-width="1.5" stroke-dasharray="4 3"/>
  <text x="228" y="20" font-size="9" fill="var(--ink)">deadline 100ms</text>
  <rect x="20" y="55" width="72" height="18" fill="var(--s1)"/>
  <text x="36" y="68" font-size="9" fill="var(--panel)">gateway 30</text>
  <rect x="92" y="55" width="96" height="18" fill="var(--s1)"/>
  <text x="112" y="68" font-size="9" fill="var(--panel)">auth 40</text>
  <rect x="188" y="55" width="120" height="18" fill="var(--s2)"/>
  <text x="210" y="68" font-size="9" fill="var(--panel)">db 50 (70→120)</text>
  <text x="16" y="112" font-size="8" fill="var(--muted)">0</text>
  <text x="180" y="112" font-size="8" fill="var(--muted)">70</text>
  <text x="298" y="112" font-size="8" fill="var(--muted)">120</text>
  <text x="192" y="46" font-size="8.5" fill="var(--s2)">starts at 70 with only 30 left, needs 50</text>
</svg>
^ Gateway and auth finish inside the 100ms deadline; db starts at 70ms with 30ms of budget but needs 50, so it runs past the deadline line to 120ms. That overshoot is the doomed work a per-hop timeout cannot see.

**A per-hop timeout and deadline propagation make the identical comparison — remaining budget versus hop cost — but one makes it before running the work and one never makes it at all; that timing is the entire difference in resources burned.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the request-fan-out step of a service chain, reduced to three hops under one budget so every start time and wasted-work total is checkable by hand.

Run `--trace` to see the chain under independent per-hop timeouts.

```text filename=deadline.py --trace
  hop       cost   start   finish   finishes in time?
  gateway   30     0       30       True
  auth      40     30      70       True
  db        50     70      120      False
  total chain cost = 120ms vs budget 100ms ; last hop finishes at 120ms
```

Read down the start column: gateway begins at 0 and finishes at 30, auth begins at 30 and finishes at 70 — both comfortably inside the 100ms budget. Then db begins at 70 with only 30ms of budget left, needs 50, and finishes at 120ms, twenty past the deadline. Its "finishes in time?" is False, and yet under per-hop timeouts it ran the full 50ms anyway.

Now `--budget` puts the two strategies side by side.

```text filename=deadline.py --budget
  per-hop timeouts:   backend busy until 120ms, doomed work = 50ms
    (gateway, auth, db each ran its full timeout; db finished after the 100ms deadline)
  deadline propagation: backend freed at 70ms, doomed work = 0ms
    (db failed fast: 30ms remaining < 50ms cost)
  both outcomes: request MISSES its 100ms deadline either way -- propagation saves resources, not the request
```

The difference is 50ms of database work and 50ms of extra backend occupancy — from 70ms of freed capacity under propagation to 120ms of busy capacity under per-hop timeouts. And the last line is the honest part: the request misses its deadline both ways. Propagation did not rescue it; the request was doomed the moment its work exceeded its budget. What propagation bought was the 50ms of database time and the connection and thread that per-hop timeouts spent on a result nobody would receive.

<svg role="img" aria-label="At db with 30ms remaining and 50ms cost, a fork: per-hop timeout runs to 120ms wasting 50ms, propagation fails fast at 70ms wasting nothing" viewBox="0 0 330 140">
  <rect x="110" y="15" width="110" height="28" fill="none" stroke="var(--line)" stroke-width="1"/>
  <text x="120" y="27" font-size="9" fill="var(--ink)">db reached at 70ms</text>
  <text x="120" y="39" font-size="8.5" fill="var(--muted)">30ms left, needs 50</text>
  <line x1="140" y1="43" x2="70" y2="78" stroke="var(--s2)" stroke-width="1.2"/>
  <line x1="190" y1="43" x2="260" y2="78" stroke="var(--s1)" stroke-width="1.2"/>
  <text x="20" y="92" font-size="9" fill="var(--s2)">per-hop timeout</text>
  <text x="20" y="106" font-size="8.5" fill="var(--muted)">run full 50ms</text>
  <text x="20" y="119" font-size="8.5" fill="var(--muted)">finish 120ms</text>
  <text x="24" y="132" font-size="8.5" fill="var(--s2)">50ms doomed</text>
  <text x="215" y="92" font-size="9" fill="var(--s1)">propagation</text>
  <text x="215" y="106" font-size="8.5" fill="var(--muted)">30 &lt; 50 → refuse</text>
  <text x="215" y="119" font-size="8.5" fill="var(--muted)">stop at 70ms</text>
  <text x="219" y="132" font-size="8.5" fill="var(--s1)">0ms doomed</text>
</svg>
^ Both reach db at 70ms with the same 30-versus-50 arithmetic. Per-hop timeouts ignore it and run to 120ms; propagation reads it and stops at 70ms. The request fails on the left branch too — only the wasted 50ms differs.

**The two strategies produce the same failed request; they differ only in whether the database burned 50ms on it — which is precisely the resource that runs out first when a slow dependency meets real traffic.**

## Build

The self-test asserts the whole shape of the claim, including the parts that keep it honest. It confirms the request genuinely cannot fit its budget (so there is a real failure to handle), that per-hop timeouts perform doomed work, and that propagation performs none.

```python filename=modules/ship-and-operate/code/deadline-inter-01/deadline.py:113-124 COMPLETE
    request_exceeds_budget = total_cost(chain) > budget
    print("  the chain cannot finish within the budget = %s (%dms cost > %dms budget)" % (request_exceeds_budget, total_cost(chain), budget))

    naive_does_doomed_work = idoomed > 0
    print("  per-hop timeouts perform doomed downstream work = %s (%dms wasted on hops finishing after the deadline)" % (naive_does_doomed_work, idoomed))

    propagation_fails_fast = stopped is not None
    print("  deadline propagation fails fast at a hop = %s (stopped at %s)" % (propagation_fails_fast, stopped))

    propagation_no_wasted_work = pdoomed == 0
    print("  deadline propagation performs zero doomed work = %s (%dms)" % (propagation_no_wasted_work, pdoomed))
```

<svg role="img" aria-label="Two bars: per-hop timeouts busy to 120ms with a doomed segment past the deadline, deadline propagation freed at 70ms with no doomed segment" viewBox="0 0 330 130">
  <line x1="120" y1="20" x2="120" y2="110" stroke="var(--ink)" stroke-width="1.5" stroke-dasharray="4 3"/>
  <text x="96" y="16" font-size="8.5" fill="var(--ink)">deadline 100ms</text>
  <text x="10" y="42" font-size="9" fill="var(--muted)">per-hop</text>
  <rect x="10" y="46" width="84" height="18" fill="var(--s1)"/>
  <rect x="94" y="46" width="60" height="18" fill="var(--s2)"/>
  <text x="98" y="59" font-size="8" fill="var(--panel)">doomed 50</text>
  <text x="160" y="59" font-size="8" fill="var(--muted)">busy to 120ms</text>
  <text x="10" y="88" font-size="9" fill="var(--muted)">propagation</text>
  <rect x="10" y="92" width="84" height="18" fill="var(--s1)"/>
  <text x="100" y="105" font-size="8" fill="var(--muted)">freed at 70ms — 0 doomed</text>
</svg>
^ Both do the useful gateway+auth work (left segment). Per-hop timeouts add a 50ms doomed segment that runs past the deadline line; propagation stops at the line and frees the backend 50ms sooner.

Running the check confirms every clause, including that propagation frees the backend earlier and that the request misses its deadline either way.

```text filename=deadline.py --check
  the chain cannot finish within the budget = True (120ms cost > 100ms budget)
  per-hop timeouts perform doomed downstream work = True (50ms wasted on hops finishing after the deadline)
  deadline propagation fails fast at a hop = True (stopped at db)
  deadline propagation performs zero doomed work = True (0ms)
  propagation frees the backend earlier than per-hop timeouts = True (70ms < 120ms)
  the request misses its deadline both ways = True (propagation saves resources, not the request)
```

**The check pins both the failure and the honest limit: per-hop timeouts burn 50ms of doomed work, propagation burns none, and neither strategy delivers the doomed request — the win is entirely on the resource side.**

## Definition of done

Two measurements close it, and they are deliberately not "the request succeeds," because it does not. The first is that propagation performs zero doomed work while per-hop timeouts perform some — the resource saving that is the entire point. The second is the honesty clause: the request misses its deadline both ways, so the module cannot be read as claiming propagation is a performance trick that makes slow requests fast.

```python filename=modules/ship-and-operate/code/deadline-inter-01/deadline.py:126-130 COMPLETE
    propagation_frees_backend_earlier = pfinish < ifinish
    print("  propagation frees the backend earlier than per-hop timeouts = %s (%dms < %dms)" % (propagation_frees_backend_earlier, pfinish, ifinish))

    both_miss_deadline = ifinish > budget and pfinish <= budget and stopped is not None
    print("  the request misses its deadline both ways = %s (propagation saves resources, not the request)" % both_miss_deadline)
```

There is a real cost to weigh, so the tool is not oversold. Failing fast at db means the request gives up 30ms before its deadline actually expires, on the certainty that the remaining work cannot fit. If cost estimates are wrong — if db sometimes finishes faster than its stated cost — a propagated deadline could abandon a request that would have squeaked in. In practice hops propagate the deadline and let the downstream call itself time out against it, rather than predicting the cost, so the decision is "is any budget left at all" rather than "will this exact work fit"; the fixture uses fixed costs to make the doomed case unambiguous. The principle is unchanged: never start work against a deadline that has already passed.

**Done means propagation does zero doomed work and frees the backend 50ms sooner while the doomed request fails either way — a resource win under load, explicitly not a rescue of the request.**

## Boss fight

Your service is healthy at normal load but falls over the moment a downstream database slows down: within seconds every application server's thread pool is exhausted and even requests that do not touch the database start timing out. You check and every hop has a sensible per-hop timeout, none longer than the client's overall deadline. Why does a single slow dependency exhaust pools on services that are themselves fast, and what one change stops the cascade without touching the database?

Each per-hop timeout is fine in isolation, but none of them accounts for budget already spent upstream, so when the database slows, requests reach it having already burned most of their deadline — and the database, measuring against its own fresh timeout, keeps working on every one of them until its full timeout elapses. Each of those requests holds an application-server thread the whole time, waiting on a database call whose result will arrive after the client has given up. The threads are not consumed by the database's slowness directly; they are consumed by the application servers waiting on doomed calls they should never have made. The change is deadline propagation: carry the remaining budget into the database call, so a request that arrives with no budget left fails fast instead of occupying a thread until the per-hop timeout expires. The database is untouched — it simply stops being handed work for requests that are already too late, which frees the upstream threads to serve the requests that still have time.

## External resources

The gRPC documentation on deadlines and deadline propagation — the canonical description of carrying a deadline across service boundaries so downstream calls inherit the remaining budget, exactly the mechanism modeled here, in a production RPC system.

Google's *Site Reliability Engineering*, the chapter on handling overload and cascading failures — why doomed work under load is the mechanism behind cascading outages, and how deadline propagation plus load shedding keeps one slow dependency from taking down everything upstream of it.
