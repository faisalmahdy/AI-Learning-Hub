---
id: ship-inter-22
title: Warm a new instance before full traffic — or its first requests pay the cold-start cost and time out
topic: ship-and-operate
level: intermediate
status: ready
time: 17 min
summary: A freshly started instance looks healthy but is not ready: its connection pool is empty, its caches are cold, its hot paths are not yet compiled. A naive readiness check passes and the load balancer sends full traffic immediately, so the first requests each pay the setup cost — establishing a connection, filling a cache — on top of serving, and if that pushes latency past the timeout, they fail. Warm-up moves that cost off the user's critical path: pre-establish the connections and pre-load the caches before the instance is marked ready, so every real request finds the pool full and pays only the steady-state cost. On a fixture with a 10-connection pool costing 200ms each, 50ms base serving, and a 100ms timeout, a cold start makes its first 10 requests take 250ms — over the timeout — so all 10 fail, while a warmed instance serves every request at 50ms and none fail.
eli5: A shop that just opened has the lights off, the register not booted, and the coffee machine cold. If customers pour in the second the door unlocks, the first ten wait forever and leave. If instead the staff spend a few minutes turning everything on before flipping the sign to "open," those same first customers walk into a shop that's ready and get served fast. Warming up a server is flipping the "open" sign only after the lights are on.
---

## Why this module

A process that has started is not the same as a process that is ready to serve, and sending real traffic into that gap makes users pay the one-time setup cost the instance should have paid itself.

When an instance boots, the code is running and it will answer a request — but its connection pool is empty, its caches hold nothing, its JIT has not compiled the hot paths, its lazily-loaded config is unread. A readiness check that only asks "is the process up?" passes, and the load balancer routes it a full share of traffic at once. The first requests then arrive to find none of the warm state in place, so each one does the expensive first-time work — opening a connection, populating a cache — *and* serves the request. That setup cost lands on real users. If it merely makes them slow, it is a latency spike on every deploy; if it pushes them past the timeout, they fail outright, and a deploy that should have been invisible becomes a burst of errors.

**A started instance has cold caches and an empty pool, so the first requests pay the setup cost on top of serving — and when that exceeds the timeout, they do not run slow, they fail.**

Warm-up moves the cost to where no user sees it. Before the instance is marked ready, it does the first-time work against itself: pre-establishes its pooled connections, pre-loads its caches, exercises its hot paths. Only once it is genuinely warm does it start receiving traffic, so every real request finds the pool full and pays only the steady-state serving cost. The total setup work is identical — the difference is entirely who waits for it. This module compares a cold start against a warmed one and shows the cold instance's first requests time out while the warmed one serves them all.

## Concepts

**Started versus ready** is the distinction: the process answers, but its warm state (pool, caches, compiled paths) is not yet built. A readiness check must reflect ready, not merely started.

The **cold-start cost** is the first-time setup each resource needs — establishing a connection, filling a cache — paid by whichever request first touches that resource.

**Sending traffic to a cold instance** puts that cost on real requests. The first pool-size requests each pay a connection cost on top of serving, and if the sum exceeds the timeout they fail.

**Warm-up** performs the setup before the instance is marked ready, off the user's critical path, so real requests find the state already warm.

**Warm-up moves the cost, it does not remove it.** The instance still pays to build every connection and cache — the same total work — but it pays during warm-up instead of during a user's request, so the steady-state latency is identical and only the first-users' timeouts disappear.

```python filename=modules/ship-and-operate/code/ship-inter-22/warmup.py:42-45 COMPLETE
def latency(i, data, warmed):
    """Latency of request i (0-indexed). Cold: the first pool_size requests also pay connect_ms."""
    cold_conn = (not warmed) and i < data["pool_size"]
    return data["serve_ms"] + (data["connect_ms"] if cold_conn else 0)
```

**Warm-up is the act of paying the cold-start cost against the instance itself before it is marked ready, so that the users who arrive first are served at steady-state latency instead of absorbing the setup.**

<svg role="img" aria-label="Without warm-up, ready is marked right after started and users pay setup; with warm-up, a warming phase sits between started and ready so the instance pays setup" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">from process start to first served request</text>
  <text x="8" y="34" fill="var(--s2)" font-size="8">no warm-up</text>
  <rect x="70" y="24" width="40" height="16" fill="var(--grid)"/><text x="74" y="36" fill="var(--muted)" font-size="7">started</text>
  <rect x="110" y="24" width="40" height="16" fill="var(--s1)"/><text x="116" y="36" fill="var(--panel)" font-size="7">ready</text>
  <rect x="150" y="24" width="60" height="16" fill="var(--s2)"/><text x="154" y="36" fill="var(--panel)" font-size="7">USERS pay setup</text>
  <text x="8" y="72" fill="var(--s1)" font-size="8">warm-up</text>
  <rect x="70" y="62" width="40" height="16" fill="var(--grid)"/><text x="74" y="74" fill="var(--muted)" font-size="7">started</text>
  <rect x="110" y="62" width="55" height="16" fill="var(--s2)"/><text x="114" y="74" fill="var(--panel)" font-size="7">warming (self)</text>
  <rect x="165" y="62" width="40" height="16" fill="var(--s1)"/><text x="171" y="74" fill="var(--panel)" font-size="7">ready</text>
  <rect x="205" y="62" width="40" height="16" fill="var(--s1)"/><text x="209" y="74" fill="var(--panel)" font-size="7">fast</text>
  <text x="70" y="98" fill="var(--muted)" font-size="8">warm-up inserts a self-paid warming phase before ready, so users arrive to a warm instance</text>
</svg>
^ Without warm-up, ready follows started immediately and the setup cost lands on users; with warm-up, a self-paid warming phase sits between them so users only ever meet a warm instance.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/ship-inter-22/warmup.py

The fixture is a connection pool, its per-connection cost, the base serving time, and the timeout.

```json filename=modules/ship-and-operate/code/ship-inter-22/warmup.json:1-8 COMPLETE
{
  "_meta": "A cold-start model for a freshly deployed instance. Each request needs a connection from a pool of pool_size. On a COLD instance the pool starts empty, so the first pool_size requests each have to establish a connection, paying connect_ms on top of the base serve_ms; later requests reuse the warm connections and pay only serve_ms. A request whose total latency exceeds timeout_ms fails. WARM-UP establishes all pool_size connections BEFORE traffic is sent (during readiness, off the user's critical path), so every real request pays only serve_ms and none time out. requests is how many real requests we send. The point: sending full traffic to a cold instance times out its first pool_size requests; warming it first costs pool_size*connect_ms of preparation but zero user-facing timeouts.",
  "pool_size": 10,
  "connect_ms": 200,
  "serve_ms": 50,
  "timeout_ms": 100,
  "requests": 100
}
```

A request times out when its latency exceeds the timeout; warm-up's cost is establishing every connection up front.

```python filename=modules/ship-and-operate/code/ship-inter-22/warmup.py:48-55 COMPLETE
def timeouts(data, warmed):
    """How many of the requests exceed the timeout."""
    return sum(1 for i in range(data["requests"]) if latency(i, data, warmed) > data["timeout_ms"])


def warmup_cost(data):
    """Preparation cost paid before traffic: establish every pooled connection."""
    return data["pool_size"] * data["connect_ms"]
```

Run `--latency` for the first requests' latencies under each.

```text filename=--latency
LATENCY — per-request latency, cold vs warmed (timeout 100ms)
----------------------------------------------------------
  request   cold ms   warmed ms
  0          250        50  <- times out
  1          250        50  <- times out
  2          250        50  <- times out
  3          250        50  <- times out
  4          250        50  <- times out
  5          250        50  <- times out
  6          250        50  <- times out
  7          250        50  <- times out
  8          250        50  <- times out
  9          250        50  <- times out
  10          50        50
  11          50        50
  ...
```

Cold, each of the first ten requests takes 250ms — 50ms to serve plus 200ms to establish its connection — and every one of them is over the 100ms timeout, so every one fails. From request 10 on, the pool is full and latency drops to the steady-state 50ms. Warmed, the connections already exist, so even request 0 pays only 50ms and nothing times out. The two columns are identical from request 10 onward; the entire difference is the first ten.

<svg role="img" aria-label="Cold requests 0 to 9 take 250ms, over the 100ms timeout; from request 10 they take 50ms; warmed requests all take 50ms" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="12" fill="var(--muted)" font-size="8">per-request latency (dashed = 100ms timeout)</text>
  <line x1="25" y1="95" x2="290" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <line x1="25" y1="66" x2="290" y2="66" stroke="var(--line)" stroke-width="1" stroke-dasharray="3 3"/><text x="25" y="63" fill="var(--muted)" font-size="7">timeout</text>
  <text x="8" y="30" fill="var(--s2)" font-size="8">cold</text>
  <rect x="40" y="22" width="10" height="73" fill="var(--s2)"/><rect x="52" y="22" width="10" height="73" fill="var(--s2)"/><rect x="64" y="22" width="10" height="73" fill="var(--s2)"/><rect x="76" y="22" width="10" height="73" fill="var(--s2)"/><rect x="88" y="22" width="10" height="73" fill="var(--s2)"/><rect x="100" y="22" width="10" height="73" fill="var(--s2)"/><rect x="112" y="22" width="10" height="73" fill="var(--s2)"/><rect x="124" y="22" width="10" height="73" fill="var(--s2)"/><rect x="136" y="22" width="10" height="73" fill="var(--s2)"/><rect x="148" y="22" width="10" height="73" fill="var(--s2)"/>
  <rect x="160" y="80" width="10" height="15" fill="var(--s1)"/><rect x="172" y="80" width="10" height="15" fill="var(--s1)"/><rect x="184" y="80" width="10" height="15" fill="var(--s1)"/>
  <text x="200" y="40" fill="var(--s2)" font-size="8">first 10 over timeout → fail</text>
  <text x="200" y="90" fill="var(--s1)" font-size="8">then steady 50ms</text>
  <text x="25" y="112" fill="var(--muted)" font-size="8">warmed: every bar is the short 50ms bar — none cross the timeout</text>
</svg>
^ The cold instance's first ten bars tower over the timeout line and fail; from request ten they drop to the steady 50ms — the warmed instance is the short bar the whole way.

## Build

The user-facing count is what matters. Run `--timeouts`.

```text filename=--timeouts
TIMEOUTS — failed requests under a cold start vs after warm-up
----------------------------------------------------------
  cold start:   10 of 100 requests time out
  warmed:       0 of 100 requests time out
  warm-up cost: 2000ms of preparation (10 conns x 200ms), off the critical path
----------------------------------------------------------
  same setup work; warm-up moves it before traffic so users never see a timeout.
```

The cold start fails 10 of 100 requests — a 10% error spike on every deploy or scale-up, exactly when you are watching and hoping the release is clean. Warm-up fails zero. And the warm-up was not free work conjured away: it cost 2000ms of preparation, the same ten connections at 200ms each. That cost was simply paid by the instance before it accepted traffic, during its readiness phase, where no user was waiting on it. The setup bill is identical; warm-up only changes whose latency budget it is charged to — the instance's own startup instead of ten users' requests.

<svg role="img" aria-label="A cold start fails 10 of 100 requests; a warmed start fails 0; the 2000ms warm-up cost is paid before traffic" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">failed requests out of 100</text>
  <line x1="60" y1="20" x2="60" y2="72" stroke="var(--grid)" stroke-width="1"/>
  <line x1="60" y1="72" x2="285" y2="72" stroke="var(--grid)" stroke-width="1"/>
  <rect x="60" y="26" width="66" height="16" fill="var(--s2)"/><text x="130" y="38" fill="var(--muted)" font-size="8">cold: 10 fail</text>
  <rect x="60" y="50" width="2" height="16" fill="var(--s1)"/><text x="66" y="62" fill="var(--muted)" font-size="8">warmed: 0 fail</text>
  <text x="60" y="88" fill="var(--muted)" font-size="8">warm-up paid 2000ms before traffic so this bar is empty</text>
</svg>
^ The cold bar loses 10 requests to timeouts; the warmed bar loses none, because the identical setup cost was paid before the door opened.

## Definition of done

The self-test pins it: the first cold request is slow and times out, a cold start fails exactly pool-size requests, warm-up fails none, and past the pool the two are identical.

```python filename=modules/ship-and-operate/code/ship-inter-22/warmup.py:90-103 COMPLETE
    cold_first_is_slow = latency(0, data, False) > latency(0, data, True)
    print("  the first cold request is slower than warmed = %s (%dms vs %dms)" % (cold_first_is_slow, latency(0, data, False), latency(0, data, True)))

    cold_first_times_out = latency(0, data, False) > data["timeout_ms"]
    print("  the first cold request exceeds the timeout = %s (%dms > %dms)" % (cold_first_times_out, latency(0, data, False), data["timeout_ms"]))

    cold_timeouts_equal_pool = timeouts(data, False) == P
    print("  a cold start times out exactly the first pool_size requests = %s (%d = %d)" % (cold_timeouts_equal_pool, timeouts(data, False), P))

    warm_no_timeouts = timeouts(data, True) == 0
    print("  after warm-up no request times out = %s (%d)" % (warm_no_timeouts, timeouts(data, True)))

    steady_state_identical = latency(P, data, False) == latency(P, data, True)
    print("  past the pool, cold and warmed serve identically = %s (%dms)" % (steady_state_identical, latency(P, data, False)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — a cold start times out its first pool_size requests; warm-up eliminates the timeouts
----------------------------------------------------------------------------------------------------
  the first cold request is slower than warmed = True (250ms vs 50ms)
  the first cold request exceeds the timeout = True (250ms > 100ms)
  a cold start times out exactly the first pool_size requests = True (10 = 10)
  after warm-up no request times out = True (0)
  past the pool, cold and warmed serve identically = True (50ms)
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  cold_first_is_slow=True  cold_first_times_out=True  cold_timeouts_equal_pool=True  warm_no_timeouts=True  steady_state_identical=True
```

**Done means the shift is proven: a cold start times out exactly its first 10 requests (each 250ms, over the 100ms timeout) while a warmed start times out zero, and from request 10 on both serve at the identical 50ms — so warm-up moved the setup cost without changing the steady state.**

## Boss fight

Warm-up fixed the deploy spike. Predict where the cold-start cost bites even with warm-up, and what makes warming hard to get right. It is tempting to think one warm-up step at startup solves cold starts forever.

Warm-up guards the moment of readiness, but the cold-start cost returns wherever warm state is rebuilt: an autoscaler adding instances under a traffic surge (each new one cold exactly when load is highest), a connection pool that closes idle connections and must re-establish them on the next request, a cache with a TTL that expires and re-fetches, a serverless function that scales to zero and cold-starts on the next call. Each is the same cost reappearing, so warm-up is not one startup step but a policy: keep a minimum warm pool, refresh connections before they idle out, pre-scale ahead of predictable surges rather than reacting to them. The single worst case is scaling under load, because that is when a cold instance's timeouts hit the most users — which is why serious autoscaling adds capacity early and gradually, not at the last moment.

The trap in warm-up itself is warming the wrong things, or warming against reality. A warm-up that opens connections but never exercises the actual query paths leaves the caches and compiled code cold, so the readiness check passes while the first real requests still pay part of the cost — the warm-up must mimic real traffic, not just tick a box. And warm-up that hammers a shared downstream (every deploying instance opening its full pool at once) can itself become a thundering herd on the database. Ramp the new instance's traffic up gradually (slow-start load balancing) so it warms under a trickle rather than a flood, and warm against representative requests so the state you build is the state real traffic needs. Readiness should mean "warmed on the paths users will actually hit," not merely "connections opened."

```python filename=modules/ship-and-operate/code/ship-inter-22/warmup.py:53-55 COMPLETE
def warmup_cost(data):
    """Preparation cost paid before traffic: establish every pooled connection."""
    return data["pool_size"] * data["connect_ms"]
```

**Pay the cold-start cost against the instance before marking it ready — pre-fill the pool, pre-load the caches, exercise the real hot paths — so users are served at steady state, but treat warm-up as an ongoing policy (minimum warm capacity, pre-scaling, slow-start traffic) because the cost returns on every scale-up, idle timeout, and cache expiry.**

## External resources

Load-balancer slow-start documentation (for example AWS ELB/ALB slow start or Envoy's slow-start mode) — the mechanism that ramps traffic to a new instance gradually so it warms under a trickle instead of a flood.

Cloud autoscaling and serverless cold-start guidance (for example provisioned concurrency for functions, or keeping a warm instance pool) — the productionized forms of "warm before traffic" for elastic and scale-to-zero systems.

The companion "liveness and readiness are different checks" and "exponential backoff needs jitter" modules — readiness is where warm-up is enforced, and the thundering-herd caution on warm-up connections is the same synchronization problem jitter solves.
