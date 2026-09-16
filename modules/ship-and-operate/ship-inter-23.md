---
id: ship-inter-23
title: Don't fail readiness on a shared dependency — or one dependency blip pulls the whole fleet at once
topic: ship-and-operate
level: intermediate
status: ready
time: 17 min
summary: A readiness check tells the load balancer whether to route to an instance. The tempting design is thorough — check the database, the cache, the downstream API, report unhealthy if any is down. But every instance shares that database, so when it degrades every instance's check fails at the same instant, the balancer pulls all of them, and a partial degradation the fleet could have ridden out on a cache or fallback becomes a total, fleet-wide outage. The fix is to separate two questions: "can this instance serve?" is local (process up, not out of memory) and belongs in readiness, while "is the shared dependency healthy?" belongs in request handling (circuit breakers, fallbacks) and alerting, not in the check that decides fleet membership. On a fixture of 6 locally-healthy instances with the shared dependency down, a cascading readiness check leaves 0 in rotation (total outage) while a local check keeps all 6 in rotation, serving degraded but up.
eli5: Imagine a row of ticket booths that all look up prices in one shared book. If each clerk is told "close your booth whenever the book is missing," then the moment the book goes missing, every booth closes at once and nobody can buy a ticket — even though the clerks could have quoted yesterday's prices from memory. The better rule is "stay open as long as you personally can serve customers," so a missing book means slightly worse service, not a closed station.
---

## Why this module

A readiness check decides whether an instance stays in the load balancer's rotation, so putting a shared dependency's health inside it means one dependency can evict the entire fleet in a single instant.

The instinct is to make the readiness check comprehensive: it should verify the instance can actually do its job, so check the database connection, the cache, the downstream service, and report unhealthy if any of them is failing. It sounds prudent — why send traffic to an instance that cannot reach its database? The flaw is that the dependency is *shared*. Every instance checks the same database, so when that database degrades, every instance's readiness check flips to unhealthy at the same moment. The load balancer, seeing its whole pool go unhealthy, pulls every instance from rotation, and now there is nothing to serve — a total outage. Worse, the instances might have survived the degradation: served from cache, returned a fallback, degraded a feature. Instead, the check that was meant to protect users removed every server the instant the dependency blipped.

**A readiness check that fails on a shared dependency makes every instance fail at once when that dependency degrades, so the load balancer pulls the whole fleet and a partial degradation becomes a total outage.**

The fix is to separate two different questions. "Can this instance serve a request?" is local — is the process up, is it out of memory, can it accept a connection — and that is what readiness should answer, so the balancer removes only genuinely broken instances. "Is the shared dependency healthy?" is a separate question whose answer, when the dependency degrades, is to serve in a degraded mode — stale cache, fallback, partial response — not to remove every instance. Dependency health belongs in request handling (circuit breakers, fallbacks) and in alerting, not in the check that decides fleet membership. This module runs both readiness designs against a degraded dependency and shows one empty the fleet while the other keeps it serving.

## Concepts

**A readiness check** decides whether the load balancer routes traffic to an instance. Fail it, and the instance is pulled from rotation.

A **shared dependency** is one that every instance uses — a database, a cache, a downstream API. Its health is common to the whole fleet, not per-instance.

**A cascading readiness check** fails whenever the shared dependency is unhealthy. Because the dependency is common, all instances fail together, so the balancer empties the pool at once.

```python filename=modules/ship-and-operate/code/ship-inter-23/healthcheck.py:43-50 COMPLETE
def ready_cascading(local_ok, dependency_ok):
    """Cascading readiness: healthy only if the instance AND the shared dependency are healthy."""
    return local_ok and dependency_ok


def ready_local(local_ok, dependency_ok):
    """Local readiness: healthy if this instance can serve, regardless of the dependency."""
    return local_ok
```

**A local readiness check** reports only whether this instance can serve, so a dependency blip leaves the fleet in rotation, serving degraded.

**Dependency health belongs elsewhere.** A degraded dependency should trigger fallbacks and alerts, not fleet eviction — readiness answers "am I able to serve," not "is everything downstream perfect."

**Readiness gates fleet membership on a per-instance question, so a shared dependency must never appear in it — its failure is common to all instances, and any check it fails, it fails everywhere at once.**

<svg role="img" aria-label="Several instances each check their own local health and all check the one shared dependency; the shared check is common to all" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">what each readiness check looks at</text>
  <rect x="20" y="26" width="30" height="16" fill="var(--s1)"/><rect x="60" y="26" width="30" height="16" fill="var(--s1)"/><rect x="100" y="26" width="30" height="16" fill="var(--s1)"/><rect x="140" y="26" width="30" height="16" fill="var(--s1)"/>
  <text x="20" y="54" fill="var(--muted)" font-size="7">instance (local check = its own health)</text>
  <line x1="35" y1="42" x2="150" y2="72" stroke="var(--s2)" stroke-width="1"/><line x1="75" y1="42" x2="150" y2="72" stroke="var(--s2)" stroke-width="1"/><line x1="115" y1="42" x2="150" y2="72" stroke="var(--s2)" stroke-width="1"/><line x1="155" y1="42" x2="152" y2="72" stroke="var(--s2)" stroke-width="1"/>
  <rect x="120" y="72" width="70" height="16" fill="var(--s2)"/><text x="126" y="84" fill="var(--panel)" font-size="7">shared dependency</text>
  <text x="200" y="84" fill="var(--muted)" font-size="7">one failure → all lines fail</text>
</svg>
^ Each instance's own health is separate, but the shared dependency is a single node every cascading check touches — so its one failure trips every instance's check together.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/ship-inter-23/healthcheck.py

The fixture is a fleet of locally-healthy instances with the shared dependency down.

```json filename=modules/ship-and-operate/code/ship-inter-23/healthcheck.json:1-6 COMPLETE
{
  "_meta": "A fleet of instances behind a load balancer, all sharing one downstream dependency (a database, say). Each instance is locally healthy: its process is up and it can serve requests, possibly in a degraded mode (stale cache, a fallback) if the dependency is slow. The load balancer routes only to instances whose readiness check passes. Two readiness designs: a CASCADING check returns unhealthy whenever the shared dependency is unhealthy, so if the dependency degrades, EVERY instance fails its check at once and the balancer pulls the whole fleet -- a partial degradation becomes a total outage. A LOCAL check reports only whether THIS instance can serve, so a dependency blip leaves every instance in rotation, serving degraded but up. instances is the fleet size; local_ok is each instance's own health; dependency_ok is the shared dependency's status.",
  "instances": 6,
  "local_ok": true,
  "dependency_ok": false
}
```

Run `--rotation` to see how many instances stay in rotation under each check, dependency up and down.

```text filename=--rotation
ROTATION — instances in the load-balancer rotation (fleet of 6, all locally healthy)
--------------------------------------------------------------
  dependency   cascading check   local check
  healthy      6 of 6           6 of 6
  DOWN         0 of 6           6 of 6
--------------------------------------------------------------
  when the dependency is down, the cascading check empties the rotation; the local check keeps it full.
```

When the dependency is healthy, both checks agree: all 6 instances are in rotation. The difference appears the instant the dependency goes down. The cascading check now fails on all 6 instances — they are all locally fine, but they all share the down dependency — so the rotation empties to 0 and the service is dark. The local check still passes on all 6, because each instance can still serve (from cache, with a fallback), so all 6 stay in rotation. Same fleet, same dependency failure: one design produces a total outage, the other a degraded-but-up service.

<svg role="img" aria-label="With the dependency down, the cascading check leaves 0 of 6 instances in rotation while the local check leaves all 6" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">rotation with the shared dependency DOWN (6 instances)</text>
  <text x="8" y="36" fill="var(--s2)" font-size="8">cascading</text>
  <rect x="70" y="26" width="18" height="16" fill="none" stroke="var(--grid)"/><rect x="90" y="26" width="18" height="16" fill="none" stroke="var(--grid)"/><rect x="110" y="26" width="18" height="16" fill="none" stroke="var(--grid)"/><rect x="130" y="26" width="18" height="16" fill="none" stroke="var(--grid)"/><rect x="150" y="26" width="18" height="16" fill="none" stroke="var(--grid)"/><rect x="170" y="26" width="18" height="16" fill="none" stroke="var(--grid)"/>
  <text x="195" y="38" fill="var(--s2)" font-size="8">0 in rotation → outage</text>
  <text x="8" y="72" fill="var(--s1)" font-size="8">local</text>
  <rect x="70" y="62" width="18" height="16" fill="var(--s1)"/><rect x="90" y="62" width="18" height="16" fill="var(--s1)"/><rect x="110" y="62" width="18" height="16" fill="var(--s1)"/><rect x="130" y="62" width="18" height="16" fill="var(--s1)"/><rect x="150" y="62" width="18" height="16" fill="var(--s1)"/><rect x="170" y="62" width="18" height="16" fill="var(--s1)"/>
  <text x="195" y="74" fill="var(--s1)" font-size="8">6 in rotation → degraded</text>
  <text x="30" y="100" fill="var(--muted)" font-size="8">the same locally-healthy fleet: empty under cascading, full under local</text>
</svg>
^ Under the cascading check every instance is pulled (empty boxes) and the service goes dark; under the local check all six stay in rotation and serve degraded.

## Build

The blast radius is the fleet size minus whoever stayed in rotation, under each check.

```python filename=modules/ship-and-operate/code/ship-inter-23/healthcheck.py:73-75 COMPLETE
    n, local = data["instances"], data["local_ok"]
    cascading_removed = n - in_rotation(n, local, False, ready_cascading)
    local_removed = n - in_rotation(n, local, False, ready_local)
```

The failure amplification is the point. Run `--blast`.

```text filename=--blast
BLAST — instances removed by ONE shared-dependency failure
--------------------------------------------------------------
  cascading check:  6 of 6 removed   (the whole fleet -> total outage)
  local check:      0 of 6 removed   (none -> degraded but serving)
--------------------------------------------------------------
  cascading readiness makes one dependency the single point of failure for the entire fleet.
```

One dependency failure removes 6 of 6 instances under the cascading check and 0 of 6 under the local check. That is the whole danger stated as a blast radius: the cascading readiness check takes a single shared dependency and turns it into a single point of failure for the entire fleet, with an amplification factor equal to the fleet size. Adding more instances does not help — it makes it worse, because now the dependency can take down more servers at once. The local check has a blast radius of zero for a dependency failure: the dependency's problem is handled where it belongs, in the request path and the alerts, and the fleet stays up to serve whatever it still can.

<svg role="img" aria-label="A cascading check has a blast radius of the whole 6-instance fleet; a local check has a blast radius of zero" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">instances removed by one dependency failure</text>
  <line x1="80" y1="20" x2="80" y2="74" stroke="var(--grid)" stroke-width="1"/>
  <line x1="80" y1="74" x2="285" y2="74" stroke="var(--grid)" stroke-width="1"/>
  <rect x="80" y="26" width="190" height="16" fill="var(--s2)"/><text x="84" y="38" fill="var(--panel)" font-size="8">cascading: 6 of 6 (whole fleet)</text>
  <rect x="80" y="50" width="2" height="16" fill="var(--s1)"/><text x="86" y="62" fill="var(--muted)" font-size="8">local: 0 of 6</text>
  <text x="80" y="92" fill="var(--muted)" font-size="8">cascading readiness makes the shared dependency a fleet-wide single point of failure</text>
</svg>
^ The cascading bar spans the whole fleet — one dependency failure evicts every instance — while the local bar is empty, because the dependency's health never gated rotation.

## Definition of done

The self-test pins it: cascading empties the rotation, local keeps the whole fleet, both agree when healthy, and the blast radius is the fleet versus zero.

```python filename=modules/ship-and-operate/code/ship-inter-23/healthcheck.py:89-102 COMPLETE
    cascading_empties = in_rotation(n, local, False, ready_cascading) == 0
    print("  cascading check empties the rotation when the dependency is down = %s (%d in rotation)" % (cascading_empties, in_rotation(n, local, False, ready_cascading)))

    local_keeps_all = in_rotation(n, local, False, ready_local) == n
    print("  local check keeps the whole fleet in rotation when the dependency is down = %s (%d of %d)" % (local_keeps_all, in_rotation(n, local, False, ready_local), n))

    agree_when_healthy = in_rotation(n, local, True, ready_cascading) == in_rotation(n, local, True, ready_local) == n
    print("  both checks agree (all in rotation) when the dependency is healthy = %s" % agree_when_healthy)

    cascade_blast_is_fleet = (n - in_rotation(n, local, False, ready_cascading)) == n
    print("  one dependency failure removes the entire fleet under cascading = %s (blast %d = %d)" % (cascade_blast_is_fleet, n - in_rotation(n, local, False, ready_cascading), n))

    local_blast_is_zero = (n - in_rotation(n, local, False, ready_local)) == 0
    print("  the same failure removes nothing under the local check = %s" % local_blast_is_zero)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the cascading check removes the whole fleet on a dependency blip; the local check keeps it serving
------------------------------------------------------------------------------------------------------------
  cascading check empties the rotation when the dependency is down = True (0 in rotation)
  local check keeps the whole fleet in rotation when the dependency is down = True (6 of 6)
  both checks agree (all in rotation) when the dependency is healthy = True
  one dependency failure removes the entire fleet under cascading = True (blast 6 = 6)
  the same failure removes nothing under the local check = True
------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  cascading_empties=True  local_keeps_all=True  agree_when_healthy=True  cascade_blast_is_fleet=True  local_blast_is_zero=True
```

**Done means the amplification is proven: with the shared dependency down and all 6 instances locally healthy, the cascading check leaves 0 in rotation (blast radius 6, the whole fleet) while the local check leaves all 6 (blast radius 0) — the dependency failure evicts everyone or no one, depending only on which question readiness asks.**

## Boss fight

The local check kept the fleet up. Predict when routing to an instance that cannot reach its dependency is actually the wrong thing, and where the dependency's health should live instead. It is tempting to swing to the other extreme and never check dependencies at all.

Sometimes an instance genuinely cannot serve without the dependency, and then keeping it in rotation just returns errors — routing to it is no better than dropping it. The distinction is whether a degraded mode exists. If the instance can serve from cache, return a fallback, or degrade a feature, the local check is right: stay up and serve what you can. If a request is meaningless without the dependency (a login that must hit the auth database, with no fallback), then failing fast is legitimate — but even then, the answer is usually a circuit breaker in the request path that returns a fast, clear error, not a readiness failure that evicts the instance, because eviction removes capacity you will need the instant the dependency recovers. The rule is not "never check dependencies," it is "a shared dependency's health must not gate fleet membership," and the fallback-versus-fail-fast choice belongs per-request, not per-instance.

The deeper design is to make the dependency's health visible without making it evict. Report it: expose a separate deep health endpoint (checked by monitoring and alerting, not the load balancer) that does verify the database and downstream, so operators see the degradation and page on it. Handle it: circuit breakers, timeouts, and fallbacks in the request path decide what to do about a slow or down dependency on each call. Isolate it: bulkheads keep one dependency's failure from consuming all the instance's capacity. Readiness stays narrow — "can this process accept a request" — while a richer picture of downstream health lives in the layers built to act on it. The mistake was overloading one signal (fleet membership) with a question (dependency health) that has its own, better-suited machinery.

```python filename=modules/ship-and-operate/code/ship-inter-23/healthcheck.py:53-55 COMPLETE
def in_rotation(n, local_ok, dependency_ok, check):
    """How many of the n instances the load balancer keeps, given a readiness check."""
    return n if check(local_ok, dependency_ok) else 0
```

**Gate load-balancer rotation on a per-instance question — can this process serve — never on a shared dependency, whose failure would fail every instance's check at once and evict the whole fleet; put dependency health in circuit breakers and fallbacks in the request path, a separate deep-health endpoint for alerting, and bulkheads for isolation, so a degraded dependency means degraded service, not a total outage.**

## External resources

Google's SRE book chapters on load balancing and cascading failures — the pattern where health checks that verify downstream dependencies turn a partial failure into a total one, and why health signals must be scoped carefully.

Kubernetes documentation on liveness, readiness, and startup probes — the guidance that readiness probes should reflect an instance's own ability to serve, and the failure modes of probing shared dependencies.

The companion "liveness and readiness are different checks" and "trip a circuit breaker after repeated failures" modules — readiness scope is the subject here, and the circuit breaker is where a down dependency's handling belongs instead of the readiness check.
