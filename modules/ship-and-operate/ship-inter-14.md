---
id: ship-inter-14
title: Coalesce concurrent misses with single-flight — or a hot key's expiry stampedes the origin
topic: ship-and-operate
level: intermediate
status: ready
time: 21 min
summary: A hot cache key serves thousands of requests from memory until it expires; then, during the refill window, every arriving request misses and launches its own origin fetch — one lookup per request instead of one per TTL, all at once, which takes down the origin the cache was protecting. Single-flight makes the first miss the only miss: it starts one fetch and every request arriving during it waits for the shared result. On 8 requests hitting an expired key with a 5-unit refill, naive fires 7 origin fetches; single-flight fires 1, and all 8 are still served.
eli5: Everyone in the office wants coffee from the same pot. If the pot is empty, one sensible person brews a new pot and everyone waits for it. The bad version is that all twenty people independently rush out to brew their own pot the instant they see it empty — twenty pots for one craving. Single-flight is "one person brews, the rest wait."
---

## Why this module

A cache protects the origin right up until the popular key expires, and then, for a moment, it does the opposite — it aims the whole herd at the origin at once.

A hot key is served thousands of times a second straight from cache memory, and the origin behind it — a database, an upstream API, an expensive computation — never feels that traffic. That is the entire point of the cache. Then the key's time-to-live runs out and it expires. There is now a window between the expiry and the first successful refill, and during that window the cache is empty for that key. Every request that arrives in the window looks in the cache, finds nothing, and does the obvious thing: fetch from the origin and repopulate.

If the refill takes any real time — a slow query, a remote call — many requests arrive during that window, and each one independently launches its own origin fetch. A key that cost the origin one lookup per TTL now costs it one lookup per request, and they all land in the same brief instant. That synchronized pile-on is a cache stampede, also called a thundering herd or a dogpile, and it is vicious precisely because it strikes the hottest keys at the highest traffic — the origin, sized for the trickle of misses a cache normally passes through, is hit with the full request rate and often falls over. The cache failed at the one moment it mattered.

Single-flight fixes it by making the first miss the only miss. When a request finds the key empty, it marks the key as in-flight and starts exactly one origin fetch. Every other request that arrives while that fetch is running does not start its own — it attaches to the in-flight fetch and waits for the same result. When the fetch completes, it populates the cache and all the waiters are served from that single result. The origin sees one lookup per refill no matter how large the herd, and no request is dropped; the waiters are made to wait a moment, not turned away.

On the fixture, eight requests hit an expired key while a refill takes 5 time units: six arrive together at the instant of expiry and two more during the refill. Without single-flight, seven of the eight miss and each hits the origin — seven origin fetches for one value. With single-flight, the first request fetches and the other seven attach to it — one origin fetch, and all eight requests are served.

**A cache stampede is many concurrent requests all missing a just-expired hot key and each fetching the origin, which aims the full request rate at the origin the cache was protecting; single-flight starts one fetch per refill and makes every concurrent miss wait for that shared result, so the origin sees one lookup and every request is still served.**

## Concepts

The stampede exists because a miss is not instantaneous. If refilling the cache were free, the first request would fill it and the next would hit — no window, no herd. The window is exactly the refill latency, and its danger scales with the request rate: at R requests per second and a refill that takes L seconds, roughly R times L requests fall into the window and each fires an origin fetch. So the busiest keys (high R) with the slowest origins (high L) suffer the worst stampedes — which is the worst possible combination, because those are the keys the cache was most needed for. The naive refill treats each miss as independent when they are in fact all asking the identical question at the identical moment.

<svg role="img" aria-label="Request rate times refill latency gives the number of requests in the window; a longer refill or higher rate means a bigger herd" viewBox="0 0 470 175" width="470" height="175">
  <rect x="0" y="0" width="470" height="175" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">herd size = request rate x refill latency</text>
  <text x="30" y="52" font-family="var(--mono)" font-size="9" fill="var(--muted)">short refill</text>
  <rect x="30" y="58" width="70" height="22" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <g fill="var(--acc-line)"><circle cx="42" cy="69" r="3"/><circle cx="58" cy="69" r="3"/><circle cx="74" cy="69" r="3"/></g>
  <text x="110" y="73" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">small window → few duplicate misses</text>
  <text x="30" y="112" font-family="var(--mono)" font-size="9" fill="var(--muted)">long refill</text>
  <rect x="30" y="118" width="240" height="22" fill="var(--s2)" opacity="0.3" stroke="var(--s2)"/>
  <g fill="var(--s2)"><circle cx="42" cy="129" r="3"/><circle cx="58" cy="129" r="3"/><circle cx="74" cy="129" r="3"/><circle cx="90" cy="129" r="3"/><circle cx="106" cy="129" r="3"/><circle cx="122" cy="129" r="3"/><circle cx="138" cy="129" r="3"/><circle cx="154" cy="129" r="3"/><circle cx="170" cy="129" r="3"/><circle cx="186" cy="129" r="3"/><circle cx="202" cy="129" r="3"/><circle cx="218" cy="129" r="3"/></g>
  <text x="30" y="158" font-family="var(--mono)" font-size="8" fill="var(--s2)">slow origin + hot key → the worst stampede, exactly where the cache mattered most</text>
</svg>
^ The number of requests caught in the empty window is the request rate times the refill latency, so the hottest keys behind the slowest origins — the ones the cache most protects — suffer the largest stampedes.

Single-flight recognizes that identity. The insight is that N concurrent misses on the same key are N requests for one value, so they need one computation, not N. Marking the key in-flight turns the first miss into a shared work item that the others subscribe to instead of duplicating. This is deduplication in time: the same idea as caching (don't recompute what you already have) extended to the moment before you have it (don't concurrently compute what someone is already computing). The waiters block until the shared fetch resolves and then all receive its result, so correctness is unchanged — everyone gets the value they would have fetched, just from one fetch.

The key detail is scoping the coalescing per key, not globally. The in-flight marker is keyed by the cache key, so concurrent misses on different keys still proceed in parallel — single-flight collapses the herd on key X to one fetch and the herd on key Y to one fetch, independently. It does not serialize unrelated work; it only prevents duplicate work on the same item. This is why it is cheap and always-on-safe: it never reduces the concurrency of genuinely distinct requests, only of redundant ones. Production implementations (Go's singleflight, request coalescing in CDNs and cache libraries) keep a map from key to in-flight promise and hand every duplicate caller the same promise.

Single-flight is one of a family of stampede defenses, and knowing where it sits helps. It is the direct fix for the concurrent-duplicate problem. Complementary techniques attack the window differently: probabilistic early expiration has a request refresh the key slightly before it expires (so the refill happens while the old value is still served, no empty window), and serving-stale-while-revalidating returns the expired value to waiters while one request refreshes in the background (so no one even waits). These compose with single-flight and trade a little staleness for zero stampede and zero wait. But the core move — never let two requests recompute the same key at the same time — is single-flight, and it is the one to reach for first.

**A stampede is duplicate work: N concurrent misses on one key are N requests for one value, and the window is the refill latency times the request rate; single-flight deduplicates in time by making the first miss a shared fetch the rest wait on, scoped per key so distinct requests still run in parallel.**

## Worked example

The fixture is a set of request arrival times against a just-expired key and a refill duration.

```json filename=modules/ship-and-operate/code/ship-inter-14/requests.json:3-4 COMPLETE
  "refill": 5,
  "arrivals": [0, 0, 0, 0, 0, 0, 3, 7]
```

The key is cold. Six requests arrive together at t=0 (the expiry instant), one at t=3 (still inside the 5-unit refill), and one at t=7 (after the first refill would have completed at t=5). The simulator walks requests in arrival order: a request is a hit if some fetch has completed by its time, a coalesced wait if a fetch is in flight (single-flight only), otherwise a fresh origin fetch.

```python filename=modules/ship-and-operate/code/ship-inter-14/stampede.py:40-55 COMPLETE
def simulate(arrivals, refill, single_flight):
    """Walk requests in arrival order over a cold key; return each request's outcome."""
    completed = []          # completion times of fetches that have finished populating the cache
    inflight = []           # (start, end) of a fetch currently running (single-flight only)
    outcomes = []
    for t in sorted(arrivals):
        if any(c <= t for c in completed):
            outcomes.append({"t": t, "outcome": "hit"})
        elif single_flight and any(s <= t < e for s, e in inflight):
            outcomes.append({"t": t, "outcome": "wait"})     # attached to the in-flight fetch
        else:
            end = t + refill
            completed.append(end)
            inflight.append((t, end))
            outcomes.append({"t": t, "outcome": "fetch"})
    return outcomes
```

The only difference between the two policies is the middle branch: naive skips it (every miss falls through to a fetch), single-flight takes it (a miss during an in-flight fetch waits). Predict: naive fires a fetch for every request that arrives before t=5 — that is seven of them — while single-flight fires one at t=0 and coalesces the rest. Run the trace.

```text filename=modules/ship-and-operate/code/ship-inter-14/stampede.py --trace
NAIVE (no coalescing)   (refill 5)
----------------------------------------------------
  t=0   MISS -> origin fetch
  t=0   MISS -> origin fetch
  t=0   MISS -> origin fetch
  t=0   MISS -> origin fetch
  t=0   MISS -> origin fetch
  t=0   MISS -> origin fetch
  t=3   MISS -> origin fetch
  t=7   HIT (cached)
  origin fetches: 7   requests served: 8

SINGLE-FLIGHT   (refill 5)
----------------------------------------------------
  t=0   MISS -> origin fetch
  t=0   wait for in-flight fetch
  t=0   wait for in-flight fetch
  t=0   wait for in-flight fetch
  t=0   wait for in-flight fetch
  t=0   wait for in-flight fetch
  t=3   wait for in-flight fetch
  t=7   HIT (cached)
  origin fetches: 1   requests served: 8
```

Naive fires seven origin fetches: the six requests at t=0 and the one at t=3, all of which arrive before the first refill completes at t=5, so each sees an empty cache and fetches. Only the t=7 request, arriving after a refill completed, hits. That is the stampede — seven identical lookups for one value, all in the first three time units. Single-flight fires one fetch at t=0; the other five t=0 requests and the t=3 request all find the fetch in flight and wait for it, and the t=7 request hits the now-populated cache. Same eight requests served, seven fewer origin calls.

<svg role="img" aria-label="Timeline: naive fires seven origin-fetch arrows during the refill window, single-flight fires one and marks the rest as waiting on it" viewBox="0 0 470 200" width="470" height="200">
  <rect x="0" y="0" width="470" height="200" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">origin fetches during the refill window (t=0..5)</text>
  <rect x="40" y="30" width="230" height="150" fill="var(--acc-soft)" opacity="0.3"/>
  <text x="46" y="44" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">refill window</text>
  <text x="30" y="68" font-family="var(--mono)" font-size="9" fill="var(--s2)">naive</text>
  <g stroke="var(--s2)" stroke-width="2"><line x1="45" y1="75" x2="45" y2="105"/><line x1="55" y1="75" x2="55" y2="105"/><line x1="65" y1="75" x2="65" y2="105"/><line x1="75" y1="75" x2="75" y2="105"/><line x1="85" y1="75" x2="85" y2="105"/><line x1="95" y1="75" x2="95" y2="105"/><line x1="185" y1="75" x2="185" y2="105"/></g>
  <text x="110" y="95" font-family="var(--mono)" font-size="8" fill="var(--s2)">7 fetches hammer the origin</text>
  <text x="30" y="140" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">single-flight</text>
  <line x1="45" y1="147" x2="45" y2="177" stroke="var(--acc-line)" stroke-width="3"/>
  <text x="52" y="163" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">1 fetch;</text>
  <g fill="var(--muted)"><circle cx="55" cy="172" r="2"/><circle cx="65" cy="172" r="2"/><circle cx="75" cy="172" r="2"/><circle cx="85" cy="172" r="2"/><circle cx="95" cy="172" r="2"/><circle cx="185" cy="172" r="2"/></g>
  <text x="110" y="176" font-family="var(--mono)" font-size="8" fill="var(--muted)">the rest wait (dots), served from it</text>
</svg>
^ Naive sends seven fetch arrows at the origin inside the refill window; single-flight sends one and marks the other seven requests as waiters on it, so the origin is hit once.

## Build

Reproduce the stampede. Pure standard library, deterministic, so the 7-versus-1 fetch counts come out exactly.

Run `--trace` for the per-request outcomes, `--load` for the summary, `--check` for the gate. The load view is the one-line verdict.

```text filename=modules/ship-and-operate/code/ship-inter-14/stampede.py --load
LOAD — origin fetches and requests served per policy (8 requests)
------------------------------------------------------
  policy          origin fetches   requests served
  naive                        7                 8
  single-flight                1                 8
------------------------------------------------------
  single-flight collapses the herd's fetches to one, serving everyone.
```

The fetch and served counts are simple tallies of the outcomes.

```python filename=modules/ship-and-operate/code/ship-inter-14/stampede.py:58-63 COMPLETE
def fetches(outcomes):
    return sum(1 for o in outcomes if o["outcome"] == "fetch")


def served(outcomes):
    return sum(1 for o in outcomes if o["outcome"] in ("hit", "wait", "fetch"))
```

The `served` count includes waiters and fetchers alike — the point that single-flight serves everyone, it does not shed load.

<svg role="img" aria-label="Bar chart: naive fires 7 origin fetches, single-flight fires 1, both serving all 8 requests" viewBox="0 0 470 165" width="470" height="165">
  <rect x="0" y="0" width="470" height="165" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">origin fetches for one value (8 requests, all served)</text>
  <line x1="60" y1="135" x2="450" y2="135" stroke="var(--line)"/>
  <rect x="90" y="40" width="90" height="95" fill="var(--s2)"/>
  <text x="105" y="33" font-family="var(--mono)" font-size="9" fill="var(--s2)">naive: 7</text>
  <text x="98" y="70" font-family="var(--mono)" font-size="8" fill="var(--panel)">6 wasted</text>
  <rect x="290" y="122" width="90" height="13" fill="var(--acc-line)"/>
  <text x="300" y="115" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">single-flight: 1</text>
  <text x="150" y="152" font-family="var(--mono)" font-size="8" fill="var(--muted)">served: 8 / 8</text>
  <text x="330" y="152" font-family="var(--mono)" font-size="8" fill="var(--muted)">served: 8 / 8</text>
</svg>
^ Naive fires 7 origin fetches for one value against single-flight's 1, yet both serve all 8 requests — the six-fetch difference is pure duplicate work removed, not load shed.

The self-test pins the stampede, its collapse to one fetch, and that no request was dropped.

```python filename=modules/ship-and-operate/code/ship-inter-14/stampede.py:99-102 COMPLETE
    naive_stampedes = fetches(naive) > 1
    print("  naive fires more than one origin fetch for one value = %s (%d fetches)" % (naive_stampedes, fetches(naive)))

    singleflight_one = fetches(sf) == 1
    print("  single-flight fires exactly one origin fetch = %s (%d fetch)" % (singleflight_one, fetches(sf)))
```

Two more flags close the loop: that every request is served under both policies, and that the exact number single-flight coalesces is the herd naive would have stampeded, minus the one real fetch.

```python filename=modules/ship-and-operate/code/ship-inter-14/stampede.py:108-113 COMPLETE
    all_served = served(sf) == len(arr) and served(naive) == len(arr)
    print("  every request is served under both (waiters are not dropped) = %s (%d/%d)" % (all_served, served(sf), len(arr)))

    coalesced = sum(1 for o in sf if o["outcome"] == "wait")
    herd_coalesced = coalesced == fetches(naive) - 1
    print("  the requests naive would have stampeded are coalesced = %s (%d waited)" % (herd_coalesced, coalesced))
```

```text filename=modules/ship-and-operate/code/ship-inter-14/stampede.py --check
SELF-TEST — naive stampedes the origin with one fetch per miss; single-flight collapses them to one
----------------------------------------------------------------------------------------------------
  naive fires more than one origin fetch for one value = True (7 fetches)
  single-flight fires exactly one origin fetch = True (1 fetch)
  single-flight cuts origin load below naive = True (1 vs 7)
  every request is served under both (waiters are not dropped) = True (8/8)
  the requests naive would have stampeded are coalesced = True (6 waited)
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  naive_stampedes=True  singleflight_one=True  singleflight_reduces=True  all_served=True  herd_coalesced=True
```

Five True flags. Naive_stampedes: naive fires 7 origin fetches for one value. Singleflight_one: single-flight fires exactly 1. Singleflight_reduces: 1 versus 7. All_served: all 8 requests are served under both — single-flight is not load shedding, it serves everyone. Herd_coalesced: the 6 t=0 duplicates (and the t=3 one) that naive would have stampeded are absorbed as waits. The all-served flag is the one that separates this from a rejection scheme: the herd is not turned away, it is merged.

**The all-served flag is the distinction — single-flight cuts origin fetches from 7 to 1 while still serving all 8 requests, so it removes duplicate work without removing any request, unlike load shedding which protects the origin by dropping requests.**

## Definition of done

You are done when you reproduce the stampede and its collapse, and can explain why coalescing is safe.

Concretely: `--trace` shows naive firing 7 fetches (every request before t=5) and single-flight firing 1 with 7 waits and hits; `--load` shows 7 versus 1 origin fetches with 8 served both ways; `--check` prints PASS with five True flags. You can explain that the stampede window is the refill latency and its size is that latency times the request rate, that single-flight deduplicates in time by making concurrent misses on one key share a fetch, and that scoping the in-flight marker per key keeps distinct requests parallel. You can name the complements — early expiration and stale-while-revalidate — and what they trade.

The habit to carry: put single-flight (request coalescing) in front of any expensive origin behind a cache, especially for hot keys, so a key's expiry costs one refill and not one-per-request. When an origin shows periodic load spikes synchronized with cache TTLs, or falls over exactly when a popular item expires, suspect a stampede and coalesce the misses. A cache without stampede protection is a cache that betrays you at peak.

## Boss fight

The instructive failure is a homepage feed that takes down the database every few minutes on the dot.

A site caches its computed homepage feed with a 5-minute TTL, and the database shows a brutal load spike every 5 minutes exactly. At each TTL boundary the cached feed expires, and in the second or two it takes to recompute, thousands of in-flight page loads all miss and all run the expensive feed query at once — a stampede synchronized to the TTL. The database saturates, the recompute slows, which widens the window, which pulls in even more duplicate queries. The fix is single-flight on the feed key: the first request after expiry recomputes while the rest wait for it, so each TTL boundary costs one query instead of thousands, and the periodic spikes flatten. Adding stale-while-revalidate on top removes even the wait, serving the slightly-old feed until the single refresh lands.

Your turn, two moves. First, show the danger scales with the window. Raise the refill from 5 to a larger value and confirm naive's fetch count climbs (more requests fall inside the longer window) while single-flight stays at 1 — the stampede grows with refill latency, the coalesced cost does not. Second, add a second, unrelated hot key with its own arrivals and confirm single-flight coalesces each key's herd independently (two fetches total, one per key, not one global fetch) — proving the per-key scoping keeps distinct work parallel while still killing duplicates.

## External resources

Go's golang.org/x/sync/singleflight is the canonical implementation and its documentation states the guarantee exactly — duplicate concurrent calls for the same key share one execution and all receive its result — which is the mechanism this module models.

The Wikipedia and engineering-blog literature on "cache stampede" (also "thundering herd" and "dogpile") covers the three standard defenses — locking/coalescing, probabilistic early expiration, and serving stale while revalidating — and when to combine them.

The paper "Optimal Probabilistic Cache Stampede Prevention" (Vattani, Chierichetti, Lowenstein, 2015) analyzes early-expiration refresh formally, and reading it alongside single-flight shows the two complementary ways to attack the refill window — remove the duplicates, or remove the empty window.
