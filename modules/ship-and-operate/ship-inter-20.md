---
id: ship-inter-20
title: Fall back to the stale cache when a dependency is down — or every request during the outage just fails
topic: ship-and-operate
level: intermediate
status: ready
time: 19 min
summary: A service that reads from a downstream dependency must decide what to do when that dependency is unavailable. The default is to fail — the read errors, the request errors, and for the whole outage the service returns nothing. But the service usually does not need a live read; it needs a good-enough answer, and the last value it fetched is often still fine. Failing every request couples your availability to the dependency's: if the dependency is down 40% of a window, so are you, even while holding a usable recent value. Graceful degradation serves that value — cache the last successful read, and when the dependency is down return the cached value labeled with its staleness. On a fixture where the dependency is up 3 ticks, down 4, then up 3, no fallback serves 6 of 10 (60% availability) while a stale-cache fallback serves all 10 (100%) with the served value at most 4 ticks stale.
eli5: If the town's news office closes for the afternoon, you can either tell everyone "no news, come back later" and turn them all away, or hand them this morning's paper and say "here's the latest, it's a few hours old." Most people are fine with the slightly old paper. Keeping the last edition to hand out means the office closing doesn't shut you down too — it just means the news is a little stale until they reopen.
---

## Why this module

Failing a request because a dependency is momentarily unavailable throws away a perfectly usable answer you were already holding.

When a service reads from a downstream dependency and that dependency is down, the reflexive behavior is to propagate the failure: the read errors, so the request errors. Do that and your availability is chained to the dependency's — every second it is down, you are down too, and a dependency that is unavailable 40% of some window drags you to 60% availability over that window. Yet during that entire outage you were sitting on the last value you successfully fetched, which for most reads is still a fine answer. Configuration, catalog data, a recommendation list, a rarely-changing price — none of these need to be live to the millisecond, and returning nothing for them is a self-inflicted outage.

**Propagating a dependency's failure couples your availability to its uptime, even when the last value you fetched would have answered the request fine.**

Graceful degradation breaks that coupling. Cache the last successful read; when the dependency is down, serve the cached value instead of an error, labeled with how stale it is. Your availability now rests on your own cache, so a dependency outage becomes a bounded staleness rather than an outage of your own. This module runs both policies through an outage and measures the availability recovered against the staleness paid.

## Concepts

The **dependency status** is up or down per tick. A **request** arrives every tick and needs a value.

The **no-fallback** policy serves a value only when the dependency is up; during an outage every request fails. Its availability equals the dependency's uptime.

The **stale-cache fallback** keeps the **last-known-good** value — the most recent successful read — and serves it when the dependency is down. Its availability depends on the cache being warm (having a value at all), not on the dependency, so once warm it serves every request.

The **staleness** of a served value is how many ticks old it is: zero when the dependency is up (fresh read), and the time since the last successful fetch during an outage. The key property is that staleness is **bounded by the outage length** — the value can only be as old as the time since the dependency last worked, so a short outage means slightly stale, and staleness resets to zero the instant the dependency recovers.

The trade is availability for freshness, and it is per-read. For a value that must be live — a payment authorization, a stock level at checkout — stale is unacceptable and you should fail. For the large majority of reads, a few ticks of staleness is invisible and infinitely better than an error.

**Serving the last-known-good value makes availability depend on your cache instead of the dependency, converting an outage into a bounded, labeled staleness.**

The fallback rewires where your availability comes from: no-fallback wires it straight to the dependency, while the fallback routes through your own cache, which the dependency can only make stale, not unavailable.

<svg role="img" aria-label="No-fallback: request depends directly on the dependency's uptime. Fallback: request depends on the cache, which the dependency refreshes" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="16" fill="var(--s1)" font-size="8">no fallback</text>
  <rect x="20" y="22" width="55" height="18" fill="none" stroke="var(--line)"/><text x="30" y="34" fill="var(--muted)" font-size="7">request</text>
  <line x1="75" y1="31" x2="120" y2="31" stroke="var(--s1)" stroke-width="1.5"/>
  <rect x="120" y="22" width="70" height="18" fill="none" stroke="var(--s1)"/><text x="128" y="34" fill="var(--muted)" font-size="7">dependency</text>
  <text x="200" y="34" fill="var(--s1)" font-size="7">down → request down</text>
  <line x1="10" y1="52" x2="290" y2="52" stroke="var(--line)" stroke-width="1"/>
  <text x="10" y="70" fill="var(--s2)" font-size="8">fallback</text>
  <rect x="20" y="76" width="55" height="18" fill="none" stroke="var(--line)"/><text x="30" y="88" fill="var(--muted)" font-size="7">request</text>
  <line x1="75" y1="85" x2="120" y2="85" stroke="var(--s2)" stroke-width="1.5"/>
  <rect x="120" y="76" width="55" height="18" fill="var(--s2)" opacity="0.3" stroke="var(--s2)"/><text x="132" y="88" fill="var(--ink)" font-size="7">cache</text>
  <line x1="175" y1="85" x2="205" y2="85" stroke="var(--muted)" stroke-width="1" stroke-dasharray="2 2"/>
  <rect x="205" y="76" width="70" height="18" fill="none" stroke="var(--line)"/><text x="213" y="88" fill="var(--muted)" font-size="7">dependency</text>
  <text x="120" y="110" fill="var(--muted)" font-size="7">down → cache goes stale, request still served</text>
</svg>
^ No-fallback puts the dependency in the request's critical path; the fallback puts the cache there and demotes the dependency to a background refresher, so its outage only ages the cache.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/ship-inter-20/degrade.py

The fixture is an uptime pattern: three up, four down, three up.

```json filename=modules/ship-and-operate/code/ship-inter-20/uptime.json:1-4 COMPLETE
{
  "_meta": "A service that reads a value from a downstream dependency once per tick. status[t] is 1 if the dependency is up at tick t and 0 if it is down (an outage). Each tick a request arrives. Without a fallback, a request during an outage fails. With a stale-cache fallback, the service serves the last value it successfully fetched (from the most recent up-tick), and the value's staleness is how many ticks old it is. The question: what availability and staleness does each policy give?",
  "status": [1, 1, 1, 0, 0, 0, 0, 1, 1, 1]
}
```

One walk over the ticks does it: track the last up-tick as the cache; no-fallback serves only when up; the fallback serves whenever the cache is warm; staleness is the age of the served value.

```python filename=modules/ship-and-operate/code/ship-inter-20/degrade.py:36-57 COMPLETE
def serve(status):
    """Walk the ticks; track the last up-tick as the cache. Return per-tick (up, served_no_fb, served_fb, staleness)."""
    last_good = None
    out = []
    for t, up in enumerate(status):
        if up:
            last_good = t
        served_no_fb = bool(up)
        served_fb = up or (last_good is not None)      # fallback serves if the cache is warm
        staleness = 0 if up else (t - last_good if last_good is not None else None)
        out.append((up, served_no_fb, served_fb, staleness))
    return out


def availability(rows, index):
    served = sum(1 for r in rows if r[index])
    return served / len(rows)


def max_staleness(rows):
    ages = [r[3] for r in rows if not r[0] and r[3] is not None]
    return max(ages) if ages else 0
```

Run `--serve` for the tick-by-tick outcome.

```text filename=--serve
SERVE — per tick: dependency status, and what each policy returns
------------------------------------------------------------------
  tick  dep    no-fallback     stale-cache fallback
   0    up     fresh           fresh
   1    up     fresh           fresh
   2    up     fresh           fresh
   3    DOWN   FAIL            stale (1 old)
   4    DOWN   FAIL            stale (2 old)
   5    DOWN   FAIL            stale (3 old)
   6    DOWN   FAIL            stale (4 old)
   7    up     fresh           fresh
   8    up     fresh           fresh
   9    up     fresh           fresh
------------------------------------------------------------------
  during the outage no-fallback returns nothing; the fallback returns the cached value.
```

Through the outage at ticks 3–6, no-fallback returns FAIL four times in a row. The fallback returns the value cached at tick 2, aging from 1 tick old to 4 ticks old as the outage drags on, then snaps back to fresh the instant the dependency recovers at tick 7. Same outage, two very different experiences for the caller: four errors, or four slightly-old-but-usable answers.

<svg role="img" aria-label="Ten ticks: no-fallback fails during the four down-ticks; the fallback serves stale values aging 1 to 4 then returns to fresh" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="16" fill="var(--muted)" font-size="8">no fallback</text>
  <g fill="var(--s2)"><rect x="20" y="22" width="18" height="12"/><rect x="45" y="22" width="18" height="12"/><rect x="70" y="22" width="18" height="12"/></g>
  <g fill="none" stroke="var(--s1)" stroke-dasharray="2 2"><rect x="95" y="22" width="18" height="12"/><rect x="120" y="22" width="18" height="12"/><rect x="145" y="22" width="18" height="12"/><rect x="170" y="22" width="18" height="12"/></g>
  <text x="97" y="47" fill="var(--s1)" font-size="7">4 FAILs</text>
  <g fill="var(--s2)"><rect x="195" y="22" width="18" height="12"/><rect x="220" y="22" width="18" height="12"/><rect x="245" y="22" width="18" height="12"/></g>
  <text x="10" y="76" fill="var(--muted)" font-size="8">stale fallback</text>
  <g fill="var(--s2)"><rect x="20" y="82" width="18" height="12"/><rect x="45" y="82" width="18" height="12"/><rect x="70" y="82" width="18" height="12"/></g>
  <g fill="var(--s1)" opacity="0.5"><rect x="95" y="82" width="18" height="12"/><rect x="120" y="82" width="18" height="12"/><rect x="145" y="82" width="18" height="12"/><rect x="170" y="82" width="18" height="12"/></g>
  <text x="97" y="107" fill="var(--s1)" font-size="7">stale 1..4, all served</text>
  <g fill="var(--s2)"><rect x="195" y="82" width="18" height="12"/><rect x="220" y="82" width="18" height="12"/><rect x="245" y="82" width="18" height="12"/></g>
</svg>
^ The outage window is four failed slots for no-fallback and four served-but-stale slots for the fallback; both are fresh before and after.

## Build

The summary view reports each policy's availability and the fallback's worst-case staleness.

```python filename=modules/ship-and-operate/code/ship-inter-20/degrade.py:75-82 COMPLETE
def summary_view(data):
    rows = serve(data["status"])
    print("SUMMARY — availability and worst-case staleness per policy")
    print("-" * 66)
    print("  no fallback:    availability %3.0f%%   (fails every down-tick)" % (100 * availability(rows, 1)))
    print("  stale fallback: availability %3.0f%%   worst staleness %d ticks" % (100 * availability(rows, 2), max_staleness(rows)))
    print("-" * 66)
    print("  the fallback trades a bounded staleness for the availability the outage would have cost.")
```

Roll it up with `--summary`.

```text filename=--summary
SUMMARY — availability and worst-case staleness per policy
------------------------------------------------------------------
  no fallback:    availability  60%   (fails every down-tick)
  stale fallback: availability 100%   worst staleness 4 ticks
------------------------------------------------------------------
  the fallback trades a bounded staleness for the availability the outage would have cost.
```

No fallback: 60% availability, exactly the dependency's uptime — its outage is your outage. Stale fallback: 100% availability, with a worst-case staleness of 4 ticks, which is the length of the outage. That is the whole trade on one line: you buy back the 40% of availability the outage would have cost, and you pay for it in staleness that is capped by how long the outage lasts and disappears when it ends.

<svg role="img" aria-label="No-fallback availability 60 percent, stale-fallback availability 100 percent with worst staleness 4 ticks" viewBox="0 0 300 110" width="300" height="110">
  <line x1="90" y1="12" x2="90" y2="70" stroke="var(--grid)" stroke-width="1"/>
  <line x1="90" y1="70" x2="285" y2="70" stroke="var(--grid)" stroke-width="1"/>
  <rect x="90" y="20" width="117" height="14" fill="var(--s1)"/><text x="210" y="31" fill="var(--muted)" font-size="8">no fallback 60%</text>
  <rect x="90" y="42" width="195" height="14" fill="var(--s2)"/><text x="150" y="53" fill="var(--panel)" font-size="8">fallback 100%</text>
  <text x="90" y="88" fill="var(--muted)" font-size="8">cost of the +40%: worst staleness 4 ticks (= outage length), gone at recovery</text>
</svg>
^ The fallback bar reaches full availability where no-fallback stops at the dependency's uptime — bought with a staleness bounded by the outage.

## Definition of done

The self-test pins the trade: no fallback loses availability, the fallback serves every request, it serves some stale values, worst staleness is bounded by the outage length, and up-tick reads are always fresh.

```python filename=modules/ship-and-operate/code/ship-inter-20/degrade.py:92-104 COMPLETE
    no_fallback_loses = availability(rows, 1) < 1.0
    print("  no-fallback availability is below 100%% = %s (%.0f%%)" % (no_fallback_loses, 100 * availability(rows, 1)))

    fallback_full = availability(rows, 2) == 1.0
    print("  the stale-cache fallback serves every request = %s (%.0f%%)" % (fallback_full, 100 * availability(rows, 2)))

    fallback_serves_stale = any(not r[0] and r[3] and r[3] > 0 for r in rows)
    print("  the fallback serves some stale values during the outage = %s" % fallback_serves_stale)

    staleness_bounded = max_staleness(rows) <= outage
    print("  worst staleness is bounded by the outage length = %s (%d <= %d)" % (staleness_bounded, max_staleness(rows), outage))

    fresh_when_up = all(r[3] == 0 for r in rows if r[0])
    print("  when the dependency is up, served values are fresh (0 stale) = %s" % fresh_when_up)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — no fallback loses availability during the outage; the fallback serves all with bounded staleness
------------------------------------------------------------------------------------------------------------
  no-fallback availability is below 100% = True (60%)
  the stale-cache fallback serves every request = True (100%)
  the fallback serves some stale values during the outage = True
  worst staleness is bounded by the outage length = True (4 <= 4)
  when the dependency is up, served values are fresh (0 stale) = True
------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  no_fallback_loses=True  fallback_full=True  fallback_serves_stale=True  staleness_bounded=True  fresh_when_up=True
```

**Done means the trade is quantified: the fallback lifts availability from 60% to 100% at a cost of at most 4 ticks of staleness, exactly the outage length, and never serves stale while the dependency is up.**

## Boss fight

The fallback served all requests here. Predict what happens if the dependency is down at the very start, before any successful read. It is tempting to think the fallback always saves you.

It cannot serve what it never cached: a cold cache has no last-known-good value, so during an outage before the first success the fallback fails too, exactly like no-fallback. Graceful degradation degrades from a warm state; it does not conjure data from nothing. This is why real fallbacks are paired with a warm-up (fetch on startup before serving traffic) or a sensible default value to serve until the first real read lands. The fixture's cache is warm by tick 3; a cold-start outage is the one case the fallback does not cover, and it needs its own answer.

The mirror-image mistake is serving stale data without labeling it stale, or without a staleness cap. A value that is four ticks old is fine; a value that is four days old, served silently because the dependency has been down for days and nobody noticed, is a correctness bug wearing an availability costume. Attach the staleness to the response and enforce a maximum age past which you fail rather than serve — so "graceful degradation" degrades gracefully into an honest error instead of quietly serving ancient data forever. Availability is not worth any amount of staleness; it is worth bounded, visible staleness.

```python filename=modules/ship-and-operate/code/ship-inter-20/degrade.py:50-52 COMPLETE
def availability(rows, index):
    served = sum(1 for r in rows if r[index])
    return served / len(rows)
```

**Serve the last-known-good value when a dependency is down so an outage becomes bounded staleness instead of your own outage — but warm the cache before serving, label the staleness, and cap it so degradation ends in an honest error, not ancient data.**

## External resources

The Netflix Hystrix documentation on fallbacks — the canonical treatment of getFallback, including serving cached or default values when a dependency fails, alongside the circuit breaker.

Google's "Site Reliability Engineering," the chapters on graceful degradation and handling overload — serving degraded (stale, partial, default) responses to preserve availability, and when degradation is the right call.

The companion circuit-breaker and stale-while-revalidate cache patterns — the circuit breaker decides when to stop calling a failing dependency, and stale-while-revalidate is the HTTP-caching form of serving stale while a fresh fetch is attempted.
