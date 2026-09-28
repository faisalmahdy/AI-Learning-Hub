---
id: ship-inter-08
title: Liveness and readiness are different checks — conflate them and you route to a broken instance
topic: ship-and-operate
level: intermediate
status: ready
time: 5-8h
summary: An orchestrator asks each instance one "healthy?" question to make two different decisions — should I restart it (is the process wedged?) and should I send it traffic (can it serve a request right now?) — and those are not the same question, so a single check breaks whichever decision it is not wired to. A freshly-started instance is alive but still loading, so do not restart it and do not route to it; an instance whose database connection dropped is alive but cannot serve, so route away but restarting may not help. The fix is two probes: liveness (is the process running) drives restarts, and readiness (alive AND dependencies up AND done warming) drives routing. On a fleet of four, a naive balancer routing by liveness sends traffic to three instances and two fail — one warming, one with a dead dependency — while a readiness-gated balancer routes only to the one instance that can serve and drops nothing, and restarts correctly target only the single crashed process, sparing the warming and dependency-degraded ones that just need to be left alone. Liveness and readiness disagree on exactly the instances a single health check gets wrong.
eli5: Imagine a shop with several checkout lanes. "Is the cashier breathing?" and "is the cashier ready to ring you up?" are different questions — a cashier can be alive but on a phone call, or setting up their till. If you send customers to every breathing cashier, some land at a lane that can't serve them and the sale is lost. And if you fire every cashier who isn't ringing someone up right now, you fire the ones still setting up. You need two separate checks: one to decide who to send customers to, another to decide who to replace.
---

## Why this module

When you put a service behind an orchestrator and a load balancer, two automated decisions get made about every instance, continuously. The load balancer decides where to send the next request. The orchestrator decides whether to restart an instance it thinks is broken. Both decisions are driven by a health check the instance exposes — and the classic mistake is to expose one check and wire both decisions to it, because the two decisions are answering genuinely different questions.

"Should I restart this instance?" is asking whether the process is wedged — hung, deadlocked, out of memory, unresponsive. If so, killing and replacing it is the fix. "Should I send this instance traffic?" is asking whether it can successfully serve a request at this moment — which requires more than a running process. A just-started instance is running but may still be loading a model or filling a cache; it is not wedged, so restarting it would be destructive (throwing away the warmup it has done), but it also cannot serve, so routing to it drops requests. An instance whose downstream database went unreachable is running fine; restarting it does not bring the database back, but it cannot serve either, so traffic must go elsewhere. A single "healthy?" bit cannot distinguish "wedged" from "not ready to serve," and whichever decision you attach it to, the other one misfires.

The fix is two separate probes. Liveness answers "is the process alive?" and is the *only* input to the restart decision. Readiness answers "can it serve right now?" — which is alive, and dependencies reachable, and done warming up — and is the input to the routing decision.

<svg viewBox="0 0 700 170" role="img" aria-label="Two decisions each wired to their correct probe. The restart decision is driven by the liveness probe. The routing decision is driven by the readiness probe. A crossed dashed line shows the bug: wiring the routing decision to liveness, which sends traffic to non-serving instances.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">two decisions, two probes — the bug is a crossed wire</text>
    <rect x="40" y="45" width="130" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="105" y="64" text-anchor="middle" fill="var(--acc-ink)" font-size="8">LIVENESS probe</text>
    <rect x="40" y="105" width="130" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="105" y="124" text-anchor="middle" fill="var(--acc-ink)" font-size="8">READINESS probe</text>
    <line x1="170" y1="60" x2="380" y2="60" stroke="var(--s1)"></line>
    <line x1="170" y1="120" x2="380" y2="120" stroke="var(--s1)"></line>
    <rect x="380" y="45" width="150" height="30" fill="var(--panel)" stroke="var(--line)"></rect><text x="455" y="64" text-anchor="middle" fill="var(--ink)" font-size="8">RESTART decision</text>
    <rect x="380" y="105" width="150" height="30" fill="var(--panel)" stroke="var(--line)"></rect><text x="455" y="124" text-anchor="middle" fill="var(--ink)" font-size="8">ROUTING decision</text>
    <line x1="170" y1="66" x2="380" y2="114" stroke="var(--s2)" stroke-dasharray="4 3"></line><text x="250" y="98" fill="var(--s2)" font-size="7">✗ the bug: route by liveness</text>
    <text x="540" y="64" fill="var(--muted)" font-size="7">replace wedged</text>
    <text x="540" y="124" fill="var(--muted)" font-size="7">send traffic</text>
  </g>
</svg>
^ Each decision has its own probe: liveness → restart, readiness → route. The dashed crossed wire is the conflation bug — driving the routing decision from liveness — which sends traffic to instances that are alive but cannot serve. This module models a fleet where these two signals disagree, and shows a naive liveness-only router sending traffic to instances that cannot serve while a readiness-gated router routes cleanly, and restarts correctly targeting only the truly dead process. Everything runs offline against a fleet fixture, stdlib Python 3, `$0.00`. The instinct to unlearn is that a service has a health status. It has two — alive, and able-to-serve — and collapsing them into one is how a warming instance gets killed or a broken one gets traffic.

## Concepts

Named here so you can find them again; each is built below.

- **Liveness** — is the process running (not wedged)? The restart signal.
- **Readiness** — can the instance serve a request now? Alive, dependencies up, done warming. The routing signal.
- **Warming** — a just-started instance loading state; alive but not yet ready.
- **Dependency degraded** — a downstream (database, cache) is unreachable; alive but not ready.
- **Route target** — an instance the load balancer sends traffic to; should be readiness-gated.
- **Restart target** — an instance the orchestrator replaces; should be liveness-gated.

## Worked example

Source: the health-check contract between a service, its load balancer, and its orchestrator — the probes that decide routing and restarts. The instance states stand in for real conditions (warming, dependency loss, crash) that separate "alive" from "able to serve."

Script and fixture: `modules/ship-and-operate/code/ship-inter-08/` — `health.py`, and `fleet.json`, four instances. Every command runs from there.

### The two probes

Liveness is one flag; readiness is a conjunction of three.

```
# health.py:41-49 — COMPLETE (liveness: is the process up; readiness: can it serve now)
def is_live(inst):
    """Liveness: is the process running at all? Drives the restart decision."""
    return inst["alive"]


def is_ready(inst):
    """Readiness: can it serve a request right now? Alive AND deps up AND done warming. Drives routing."""
    return inst["alive"] and inst["deps_ok"] and not inst["warming"]
```

Readiness implies liveness — you cannot serve if you are not alive — but not the reverse: an instance can be alive and still fail readiness because a dependency is down or it is warming. That one-directional gap is the whole subject; it is the set of instances that are "up" but must not receive traffic. Look at the fleet:

```
# $ python3 health.py --fleet
#   id     alive  deps_ok  warming  live  ready  note
#   i0     True   True     False    True  True   serving
#   i1     True   False    False    True  False  dependency down
#   i2     True   True     True     True  False  warming up
#   i3     False  False    False    False False  crashed
```

run: 2026-08-27 · deterministic; the instance states are a fixture · 4 instances · `python3 health.py --fleet`

Read the `live` and `ready` columns against each other. i0 is both — it serves. i3 is neither — it crashed, and it is the one thing that should be restarted. The two interesting rows are i1 and i2: both are live but not ready. i1's dependency is down and i2 is still warming — different causes, same consequence: the process is fine (do not restart) but it cannot serve (do not route). A single health bit has to pick one column to be, and both choices are wrong for these two instances.

<svg viewBox="0 0 700 200" role="img" aria-label="Four instances as two columns: live and ready. i0 is both live and ready (serving). i1 and i2 are live but not ready (dependency down, warming) — the trap zone. i3 is neither (crashed). A Venn-like split shows readiness as a strict subset of liveness, with i1 and i2 in the gap between them.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">readiness is a strict subset of liveness — the gap is the trap</text>
    <rect x="60" y="40" width="420" height="130" fill="var(--panel)" stroke="var(--line)"></rect><text x="70" y="56" fill="var(--muted)" font-size="8">LIVE (don't restart) — restart only what's outside</text>
    <rect x="80" y="70" width="180" height="80" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="90" y="86" fill="var(--acc-ink)" font-size="8">READY (route here)</text>
    <text x="140" y="120" text-anchor="middle" fill="var(--acc-ink)" font-size="9">i0</text>
    <text x="370" y="100" text-anchor="middle" fill="var(--s2)" font-size="9">i1  i2</text>
    <text x="370" y="118" text-anchor="middle" fill="var(--s2)" font-size="7">live, NOT ready</text>
    <text x="370" y="130" text-anchor="middle" fill="var(--muted)" font-size="7">(deps down / warming)</text>
    <text x="560" y="110" text-anchor="middle" fill="var(--muted)" font-size="9">i3</text><text x="560" y="128" text-anchor="middle" fill="var(--muted)" font-size="7">crashed</text>
    <line x1="480" y1="105" x2="530" y2="105" stroke="var(--muted)"></line>
    <text x="60" y="190" fill="var(--muted)" font-size="8">route to the inner box (i0); restart only outside the outer box (i3); i1/i2 need neither</text>
  </g>
</svg>
^ Readiness sits strictly inside liveness. Route to the ready set (i0); restart the not-live set (i3); the live-but-not-ready gap (i1, i2) must be neither routed to nor restarted — the exact instances a single check mishandles.

### Routing: by liveness vs by readiness

The load balancer picks a probe, and which one decides whether it drops requests.

```
# health.py:53-63 — COMPLETE (route by a probe; a failure is a routed instance that isn't ready)
def route_targets(fleet, by_readiness):
    """Instances the load balancer will send traffic to."""
    probe = is_ready if by_readiness else is_live
    return [i["id"] for i in fleet if probe(i)]


def failures(fleet, targets):
    """Of the routed instances, which cannot actually serve (routed but not ready)."""
    ready = {i["id"] for i in fleet if is_ready(i)}
    return [t for t in targets if t not in ready]
```

A failure is defined honestly: any instance the balancer routed to that is not actually ready will drop or fail the request. Run both routings:

```
# $ python3 health.py --route
#   route by liveness:  ['i0', 'i1', 'i2']   -> failures: ['i1', 'i2']
#   route by readiness: ['i0']   -> failures: []
#   restart targets (by liveness): ['i3']
```

run: 2026-08-27 · deterministic · `python3 health.py --route`

Restarts are keyed on liveness alone — the not-live set — so a warming or dependency-degraded instance is never bounced:

```
# health.py:65-67 — COMPLETE (restart exactly the wedged processes, keyed on liveness)
def restart_targets(fleet):
    """Restart exactly the instances whose process is wedged -- keyed on liveness, not readiness."""
    return [i["id"] for i in fleet if not is_live(i)]
```

<svg viewBox="0 0 700 160" role="img" aria-label="Two routing outcomes. Route by liveness sends traffic to three instances i0, i1, i2, of which i1 and i2 fail — two of three drop. Route by readiness sends traffic to one instance i0, which succeeds — zero drops.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">where each router sends traffic, and what fails</text>
    <text x="30" y="52" fill="var(--s2)" font-size="8">by liveness</text>
    <rect x="120" y="38" width="90" height="22" fill="var(--s1)"></rect><text x="165" y="53" text-anchor="middle" fill="var(--panel)" font-size="7">i0 ✓</text>
    <rect x="220" y="38" width="90" height="22" fill="var(--s2)"></rect><text x="265" y="53" text-anchor="middle" fill="var(--panel)" font-size="7">i1 ✗ deps</text>
    <rect x="320" y="38" width="90" height="22" fill="var(--s2)"></rect><text x="365" y="53" text-anchor="middle" fill="var(--panel)" font-size="7">i2 ✗ warming</text>
    <text x="430" y="53" fill="var(--s2)" font-size="8">2 of 3 drop</text>
    <text x="30" y="102" fill="var(--s1)" font-size="8">by readiness</text>
    <rect x="120" y="88" width="90" height="22" fill="var(--s1)"></rect><text x="165" y="103" text-anchor="middle" fill="var(--panel)" font-size="7">i0 ✓</text>
    <text x="230" y="103" fill="var(--s1)" font-size="8">0 drop — every target serves</text>
    <text x="120" y="138" fill="var(--muted)" font-size="8">fewer targets, but all of them work; and restarts touch only i3, the crashed one</text>
  </g>
</svg>
^ Liveness routing spreads traffic over three instances and drops two-thirds of it; readiness routing uses one instance and drops nothing. Fewer targets that all serve beats more targets that mostly fail.

Routing by liveness sends traffic to all three alive instances — i0, i1, i2 — and two of them fail: i1 cannot reach its database, i2 is still warming. That is the bug in production: a load balancer using a liveness-style health check spreads requests onto instances that are up but cannot serve, and a fraction of every request wave dies. Routing by readiness sends traffic only to i0, and drops nothing — fewer targets, but every one of them works. And restarts, keyed on liveness, target only i3, the crashed process — exactly right, and notably *not* i1 or i2, which a readiness-keyed restart would have needlessly killed, throwing away i2's warmup and pointlessly bouncing i1 while its database is the real problem.

**Liveness (is the process up) and readiness (can it serve now: alive, dependencies up, done warming) are different questions driving different decisions — restart and route — so a single health check breaks one of them: route by liveness and traffic hits the two live-but-not-ready instances (a dead dependency, a warming one) and fails, while readiness-gated routing drops nothing and liveness-gated restarts correctly spare everything but the crashed process.**

### The self-test

The `--check` mode plants the bug — routing by liveness — and proves it: liveness routing hits non-serving instances, readiness routing drops nothing, the two probes disagree on some instance, and restarts target only the dead.

```
# $ python3 health.py --check
#   routing by liveness sends traffic to non-serving instances = True (['i1', 'i2'])
#   routing by readiness drops nothing and still has a target = True (targets ['i0'])
#   some instance is live but not ready (the two probes disagree) = True (['i1', 'i2'])
#   restarts target only crashed processes, sparing warming/degraded ones = True (['i3'])
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 health.py --check`

The `probes_differ` line is the one that justifies having two checks at all: if liveness and readiness never disagreed, one bit would do. They disagree on i1 and i2, and those are precisely the instances the naive router mishandles — which is the general pattern, that the cost of conflating two signals is paid exactly where they diverge.

```
# health.py:107-113 — COMPLETE (liveness routing fails; readiness routing is clean)
    naive_routes_broken = len(naive_fail) > 0
    print("  routing by liveness sends traffic to non-serving instances = %s (%s)"
          % (naive_routes_broken, naive_fail))

    ready = route_targets(fleet, by_readiness=True)
    ready_fail = failures(fleet, ready)
    readiness_clean = len(ready_fail) == 0 and len(ready) > 0
```

### The running tally

| instance | live | ready | route-by-liveness | route-by-readiness | restart |
|---|---|---|---|---|---|
| i0 | yes | yes | routed ✓ | routed ✓ | no |
| i1 (deps down) | yes | no | routed ✗ fails | skipped | no |
| i2 (warming) | yes | no | routed ✗ fails | skipped | no |
| i3 (crashed) | no | no | skipped | skipped | yes |

Read the two routing columns against readiness: the readiness column and the route-by-readiness column are identical, as they should be, while route-by-liveness routes to two instances (i1, i2) that the readiness column marks not-ready — the two failures. And the restart column matches the *not*-live rows, only i3. Each decision lines up with its correct probe, and the naive design goes wrong precisely by using the restart-appropriate probe (liveness) to make the routing decision. Two decisions, two probes; borrow one for the other and you route to the broken or restart the recovering.

### What we did not settle

This is the core split; production adds nuance. Readiness is dynamic — an instance flips out of readiness the moment a dependency drops and back when it recovers, so the probe must be cheap and frequent, and it should *not* cascade (an instance reporting unready because a shared dependency is down can, across a fleet, pull every instance out of rotation at once — sometimes you want to keep serving degraded rather than serve nothing). A third probe, startup, is now common: it guards the liveness probe during a slow boot so a warming instance is not restarted for failing liveness before it has finished starting. Liveness probes should be shallow (does the event loop respond) not deep (can I reach the database), precisely so a dependency outage does not trigger a restart storm that makes things worse. And readiness feeds graceful shutdown (`ship-inter-06`): an instance draining should report unready first so traffic stops arriving before it exits. The invariant: separate the probe that decides restarts from the probe that decides routing, because they answer different questions.

## Build

The build in one paragraph: expose two health probes, not one — a shallow liveness probe answering "is the process wedged?" that drives restarts, and a readiness probe answering "can I serve a request now?" (alive, dependencies reachable, warmup complete) that drives load-balancer routing — so a warming or dependency-degraded instance is routed away from without being restarted, and only a truly wedged process is replaced. Keep liveness shallow so a dependency outage does not cause a restart storm, add a startup probe to protect slow boots, flip to unready first during graceful shutdown, and decide deliberately whether readiness should cascade a fleet out of rotation or keep serving degraded.

We opened on the fleet. The number that proves the split is the requests each routing drops:

```
# modules/ship-and-operate/code/ship-inter-08/ — COMPLETE, run from that directory
$ python3 health.py --route
  route by liveness:  ['i0', 'i1', 'i2']   -> failures: ['i1', 'i2']
  route by readiness: ['i0']   -> failures: []
```

Now build your own. Model a fleet with a warming instance and a dependency-degraded one, expose separate liveness and readiness probes, and route by each. Your number to beat is not uptime; it is **the requests dropped by liveness-gated routing versus readiness-gated routing** — readiness should drop none while liveness routes into the not-ready instances, and restarts should target only the crashed process. Confirm your two probes disagree on the warming and degraded instances. Bring back both routings' failures. Good luck.

## Definition of done

- [ ] A liveness probe (process alive) and a readiness probe (alive, deps up, done warming)
- [ ] Routing driven by readiness; restarts driven by liveness
- [ ] A fleet where liveness and readiness disagree (a warming and a dependency-degraded instance)
- [ ] Confirmation routing by liveness sends traffic to non-serving instances
- [ ] Confirmation routing by readiness drops nothing and still has a target
- [ ] Confirmation restarts target only crashed processes, sparing warming/degraded ones
- [ ] `python3 health.py --check` printing SELF-TEST PASS: naive_routes_broken, readiness_clean, probes_differ, restart_correct
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. What two distinct decisions does an orchestrator make about an instance, and which probe should drive each?
2. Why is readiness a strict subset of liveness? Give two ways an instance can be live but not ready.
3. What breaks if you route by liveness? What breaks if you restart by readiness?
4. Why should a liveness probe be shallow rather than checking the database?
5. Your own fleet was routed by both probes. How many requests did each routing drop, and did restarts spare the warming instance?

## External resources

- Kubernetes documentation on liveness, readiness, and startup probes — my summary: the three-probe model and exactly this separation of restart from routing; read it for the startup probe and the failure modes of a deep liveness check.
- Google SRE Book / production readiness material on health checking — my summary: why conflating health signals causes restart storms and traffic to degraded instances; read it for the fleet-level dynamics this module abstracts.
- This hub, *ship-inter-06* (graceful shutdown drains in-flight requests) — read it for how readiness feeds draining: an instance flips to unready first so traffic stops before it exits.
