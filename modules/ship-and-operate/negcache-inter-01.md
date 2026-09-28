---
id: negcache-inter-01
title: Cache the misses too, not just the hits — repeated lookups of a key that doesn't exist hit the origin every single time
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: A read-through cache has a simple rule — return the cached value if present, otherwise call the origin and cache what it returns — and buried in it is an assumption that every lookup eventually finds a value worth caching. Real traffic breaks that assumption: a large fraction of lookups are for keys that do not exist — a mistyped URL, a deleted record, an id that was never issued, a scraper walking a numeric range, a bot probing endpoints. For each of those the origin answers "not found", and a not-found is not a value, so the naive cache stores nothing. Because nothing was stored, the next lookup of the same missing key misses the cache again and calls the origin again — a missing key requested a thousand times is a thousand origin calls. The cache faithfully protects the origin from repeated hits but does nothing for repeated misses, so a burst of missing-key requests, accidental or malicious, sails straight through the cache to the backing store it was meant to shield. This is cache penetration, and it turns the cache from a shield into a sieve for the one traffic pattern most likely to be hostile. Negative caching closes the gap by caching absence as a first-class result: when the origin returns "not found", store a marker — "this key does not exist" — under that key, usually with a short time-to-live, so a repeated lookup of a missing key is served from cache like any hit and every distinct key costs at most one origin call. On a fixture whose lookups include a missing key x requested four times and y twice, a hits-only cache makes 8 origin calls while a negative cache makes 4 — one per distinct key.
eli5: Imagine a librarian who remembers where books are so she doesn't have to walk to the back room every time someone asks. But when someone asks for a book the library doesn't own, she walks all the way to the back, finds nothing, comes back and says "we don't have it" — and she doesn't write that down. So the next person who asks for that same missing book sends her walking to the back room again, and again, and again. If a prankster keeps asking for books that don't exist, she spends all day walking for nothing. The fix is simple: she writes down "we don't have that one" too, so the second time someone asks, she can say "nope" without the trip. Remembering the misses, not just the hits, is what keeps her from being run ragged.
---

## Why this module

A cache earns its keep by answering repeated questions without bothering the origin. The read-through pattern is almost reflexive: look in the cache, and on a miss, fetch from the origin and store the result for next time. It works beautifully for the keys that exist — the first request pays the origin cost, every request after is cheap. The trouble is the quiet assumption underneath it: that the fetch returns something to store.

A great deal of real traffic asks for keys that do not exist. Users mistype URLs, follow links to deleted records, and request ids that were never issued; bots and scrapers walk ranges of keys probing for anything that responds. For every one of these the origin's answer is "not found" — and the naive cache treats that as nothing to cache. So the miss is not remembered, the next identical lookup misses the cache too, and it calls the origin again. The cache that was supposed to shield the origin is transparent to exactly this traffic.

That transparency is dangerous, because missing-key traffic is often the most repetitive and the most hostile. A misconfigured client or a deliberate attacker can hammer one nonexistent key and every request lands on the database. This module runs a lookup stream with repeated missing keys through both a hits-only cache and a negative cache and counts the origin calls.

**A cache that stores only hits leaves the origin exposed to repeated lookups of non-existent keys — each one misses and re-fetches — so missing-key traffic bypasses the cache entirely; negative caching stores the "not found" too, capping every key at one origin call.**

## Concepts

The fixture is the set of keys that actually exist in the origin and a sequence of lookups — including a missing key x requested four times and a missing key y twice.

```json filename=modules/ship-and-operate/code/negcache-inter-01/negcache.json:3-4 COMPLETE
  "store": ["a", "b"],
  "lookups": ["a", "x", "x", "x", "a", "y", "y", "b", "x"]
```

The hits-only cache stores a result only when the origin found a value. A missing key finds nothing, so nothing is cached, and its next lookup goes to the origin again.

```python filename=modules/ship-and-operate/code/negcache-inter-01/negcache.py:32-42 COMPLETE
def run_hits_only(store, lookups):
    """Cache only positive results; a missing key is never cached, so it re-hits the origin."""
    cache, origin_hits = set(), []
    for k in lookups:
        if k in cache:
            origin_hits.append(False)
            continue
        origin_hits.append(True)          # go to the origin
        if k in store:
            cache.add(k)                  # cache the hit only
    return origin_hits
```

The negative cache stores the origin's answer whether it is a hit or a miss — the value for a present key, an "absent" marker for a missing one. Either way the key is now cached, so the next lookup is served without touching the origin.

```python filename=modules/ship-and-operate/code/negcache-inter-01/negcache.py:45-54 COMPLETE
def run_negative(store, lookups):
    """Cache both results; a 'not found' is stored so the next lookup is served from cache."""
    cache, origin_hits = {}, []
    for k in lookups:
        if k in cache:
            origin_hits.append(False)
            continue
        origin_hits.append(True)          # go to the origin
        cache[k] = (k in store)           # cache the hit AND the miss
    return origin_hits
```

The only difference is the last line: the hits-only cache caches on `k in store`, the negative cache caches unconditionally. That one line is the whole fix.

<svg role="img" aria-label="For the missing key x requested four times, the hits-only cache sends all four to the origin while the negative cache sends only the first and serves the other three from cache" viewBox="0 0 320 130">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">missing key x, requested 4 times</text>
  <text x="10" y="40" font-size="8" fill="var(--s2)">hits-only</text>
  <g font-size="7.5">
  <rect x="70" y="30" width="26" height="14" fill="var(--s2)"/><text x="76" y="40" fill="var(--panel)">origin</text>
  <rect x="100" y="30" width="26" height="14" fill="var(--s2)"/><text x="106" y="40" fill="var(--panel)">origin</text>
  <rect x="130" y="30" width="26" height="14" fill="var(--s2)"/><text x="136" y="40" fill="var(--panel)">origin</text>
  <rect x="160" y="30" width="26" height="14" fill="var(--s2)"/><text x="166" y="40" fill="var(--panel)">origin</text>
  <text x="196" y="40" fill="var(--ink)">4 origin calls</text>
  </g>
  <text x="10" y="72" font-size="8" fill="var(--s1)">negative</text>
  <g font-size="7.5">
  <rect x="70" y="62" width="26" height="14" fill="var(--s1)"/><text x="76" y="72" fill="var(--panel)">origin</text>
  <rect x="100" y="62" width="26" height="14" fill="none" stroke="var(--line)"/><text x="108" y="72" fill="var(--muted)">cache</text>
  <rect x="130" y="62" width="26" height="14" fill="none" stroke="var(--line)"/><text x="138" y="72" fill="var(--muted)">cache</text>
  <rect x="160" y="62" width="26" height="14" fill="none" stroke="var(--line)"/><text x="168" y="72" fill="var(--muted)">cache</text>
  <text x="196" y="72" fill="var(--ink)">1 origin call</text>
  </g>
  <text x="10" y="104" font-size="7.5" fill="var(--muted)">the miss stored on the first lookup serves the next three</text>
</svg>
^ For a single missing key hit four times, the hits-only cache makes four origin calls — it never remembers the "not found" — while the negative cache makes one and serves the rest from the stored absence marker. The gap grows with every repeat.

**The hits-only cache stores results only on a hit; the negative cache stores the "not found" too — one line of difference that decides whether repeated missing-key lookups reach the origin.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the read-through cache in front of a backing store, reduced to nine lookups so every origin call is countable by hand.

Run `--lookups` to see each request and where it lands.

```text filename=negcache.py --lookups
  #   key  exists  hits-only  negative
  0   a    yes     o          o
  1   x    no      o          o
  2   x    no      o          .
  3   x    no      o          .
  4   a    yes     .          .
  5   y    no      o          o
  6   y    no      o          .
  7   b    yes     o          o
  8   x    no      o          .
```

Follow the missing key x across rows 1, 2, 3, and 8. Under the hits-only cache every one is an `o` — an origin call — because the miss is never remembered. Under the negative cache only row 1 is an `o`; rows 2, 3, and 8 are `.`, served from the stored absence. The existing key a shows the pattern both caches already share: row 0 fetches, row 4 is served from cache. Negative caching simply extends that same courtesy to the misses.

Now `--origin` totals it.

```text filename=negcache.py --origin
  hits-only cache (positive only)  = 8 origin call(s)
  negative cache (positive+absent) = 4 origin call(s)
  calls saved by negative caching  = 4
```

The hits-only cache makes 8 origin calls out of 9 lookups — it caches only the one repeat of a (row 4) and sends everything else, every missing-key lookup included, to the origin. The negative cache makes 4: exactly one per distinct key (a, x, y, b). The four saved calls are all the repeated missing-key lookups the hits-only cache let through. On this tiny stream the difference is 4; on a real stream with one nonexistent key hammered a million times, it is the difference between one origin call and a million.

<svg role="img" aria-label="Origin call totals: hits-only cache makes 8 calls, negative cache makes 4, with the 4 saved calls being the repeated missing-key lookups" viewBox="0 0 320 110">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">origin calls over 9 lookups (4 distinct keys)</text>
  <text x="10" y="42" font-size="8.5" fill="var(--s2)">hits-only</text>
  <rect x="78" y="32" width="176" height="16" fill="var(--s2)"/><text x="150" y="44" font-size="8" fill="var(--panel)">8 calls</text>
  <text x="10" y="72" font-size="8.5" fill="var(--s1)">negative</text>
  <rect x="78" y="62" width="88" height="16" fill="var(--s1)"/><text x="112" y="74" font-size="8" fill="var(--panel)">4 calls</text>
  <text x="172" y="74" font-size="8" fill="var(--ink)">4 saved (the repeated misses)</text>
  <text x="10" y="98" font-size="7.5" fill="var(--muted)">negative caching caps the origin at one call per distinct key</text>
</svg>
^ Hits-only makes 8 origin calls, negative makes 4 — one per distinct key. Every call the negative cache avoids is a repeated lookup of a missing key that the hits-only cache forwarded to the origin.

**Hits-only forwards all 8 uncached lookups; negative caching cuts it to 4, one origin call per distinct key — the saved calls are precisely the repeated missing-key lookups.**

## Build

The self-test first establishes the premise: the stream really does look up some non-existent key more than once, and under the hits-only cache those missing keys reach the origin more than once each.

```python filename=modules/ship-and-operate/code/negcache-inter-01/negcache.py:99-107 COMPLETE
    counts = {k: lookups.count(k) for k in lookups}
    repeated_missing = [k for k in set(lookups) if k not in store and counts[k] > 1]
    repeated_missing_keys = len(repeated_missing) > 0
    print("  some non-existent key is looked up more than once = %s (%s)" % (repeated_missing_keys, sorted(repeated_missing)))

    missing_origin_calls = sum(1 for k, h in zip(lookups, ho_hits) if h and k not in store)
    hitsonly_rehits_origin = missing_origin_calls > len(set(k for k in lookups if k not in store))
    print("  hits-only: missing keys reach the origin more than once each = %s (%d origin calls for missing keys)"
          % (hitsonly_rehits_origin, missing_origin_calls))
```

Then the fix: a repeated missing key costs the negative cache exactly one origin call, negative caching makes fewer origin calls overall, and it bottoms out at one call per distinct key.

```python filename=modules/ship-and-operate/code/negcache-inter-01/negcache.py:109-117 COMPLETE
    mkey = sorted(repeated_missing)[0]
    mkey_origin_neg = sum(1 for k, h in zip(lookups, ng_hits) if h and k == mkey)
    negcache_caches_misses = mkey_origin_neg == 1
    print("  negative caching serves repeat lookups of missing key %r from cache = %s (%d origin call)" % (mkey, negcache_caches_misses, mkey_origin_neg))

    negcache_fewer_origin_calls = ng < ho
    print("  negative caching makes fewer origin calls = %s (%d < %d)" % (negcache_fewer_origin_calls, ng, ho))

    negcache_one_per_key = ng == distinct
```

Running the check confirms every clause.

```text filename=negcache.py --check
  some non-existent key is looked up more than once = True (['x', 'y'])
  hits-only: missing keys reach the origin more than once each = True (6 origin calls for missing keys)
  negative caching serves repeat lookups of missing key 'x' from cache = True (1 origin call)
  negative caching makes fewer origin calls = True (4 < 8)
  negative caching costs exactly one origin call per distinct key = True (4 == 4)
```

**The check ties the origin exposure to repeated missing-key lookups the hits-only cache forwards, and shows negative caching collapsing each missing key to a single origin call — the exposure removed at its source.**

## Definition of done

Done means the hits-only cache provably re-hits the origin for repeated missing keys and negative caching caps every distinct key at one origin call. The "one call per distinct key" clause is the strong statement: it says the negative cache's origin load depends only on how many distinct keys are seen, not on how many times each is requested — so no volume of repeats for any key, present or absent, can amplify origin load.

Two operational cautions keep negative caching from creating its own problems. First, time-to-live: negative entries should usually expire faster than positive ones, because absence is more likely to change than presence — a key that does not exist now (a record about to be created, a just-registered username) may exist shortly, and a long negative TTL would serve a stale "not found" and hide the new value. A short negative TTL bounds that staleness while still absorbing a burst. Second, memory and poisoning: caching every missing key means an attacker can try to fill the cache with junk keys to evict real entries, so negative caches want bounded size with eviction, and for adversarial missing-key floods a probabilistic filter (a Bloom filter of keys known to exist) in front of the cache can reject most nonexistent keys before they even reach it. These are refinements; the core property stands — cache the absence, and repeated misses stop reaching the origin.

<svg role="img" aria-label="A negative cache entry with a short TTL: it absorbs a burst of missing-key lookups, then expires so a key that later comes into existence is not hidden" viewBox="0 0 320 110">
  <line x1="20" y1="70" x2="300" y2="70" stroke="var(--line)" stroke-width="1"/>
  <text x="14" y="20" font-size="7.5" fill="var(--muted)">negative entry lifetime (short TTL)</text>
  <rect x="40" y="44" width="120" height="12" fill="var(--s1)"/><text x="46" y="53" font-size="7" fill="var(--panel)">absorbs the burst</text>
  <line x1="160" y1="40" x2="160" y2="74" stroke="var(--ink)" stroke-width="1.5"/><text x="150" y="88" font-size="7" fill="var(--ink)">expires</text>
  <text x="176" y="53" font-size="7.5" fill="var(--s2)">re-checks origin — a now-created key is seen</text>
  <text x="14" y="104" font-size="7.5" fill="var(--muted)">short negative TTL: shield the origin, but do not hide a key that later exists</text>
</svg>
^ A short negative TTL absorbs a burst of missing-key lookups and then expires, so if the key comes into existence the cache re-checks the origin rather than serving a stale "not found" forever. Absence is cached, but only briefly.

**Done means repeated missing-key lookups reach the origin under hits-only caching and cost one origin call under negative caching, with a short negative TTL and bounded size keeping the absence cache from serving stale misses or being poisoned.**

## Boss fight

A product API sits behind a cache in front of a database. During normal traffic the database is nearly idle, but twice now the database has been driven to overload while the cache hit rate looked "fine" at around 95%. Logs show a flood of requests for product ids that return 404. Why does a 95% hit rate coincide with database overload, and how would you fix it?

It is cache penetration: the flood is for non-existent ids, and the cache only stores hits, so every one of those 404 lookups misses the cache and reaches the database. The 95% hit rate is measured over all traffic and is dominated by the normal, existing-key requests that cache well — it hides the fact that the 404 traffic has a 0% hit rate, because a "not found" is never cached and every repeat of a bad id is a fresh database query. A relatively small but highly repetitive flood of nonexistent ids (a broken client walking an id range, a scraper, or a deliberate penetration attack) therefore lands entirely on the database while the aggregate hit rate barely moves. The fix is negative caching: when the database returns "not found" for an id, cache that absence under the id with a short TTL, so repeated requests for the same bad id are served from the cache and the database sees each bad id at most once per TTL. Give negative entries a shorter TTL than positive ones so a product that gets created shortly after being probed is not hidden, and bound the negative cache's size with eviction so the flood cannot evict real entries; for a determined attack, add a Bloom filter of existing ids in front so most nonexistent ids are rejected before any lookup. Also stop trusting the aggregate hit rate as a health signal — track the origin/database call rate directly and alert on it, since that is the number that was actually climbing while the hit rate looked fine.

## External resources

Writeups on cache penetration and negative caching in caching layers and CDNs (Redis and Memcached patterns for caching nulls, CDN negative-TTL settings, and the Bloom-filter defense against penetration attacks) — the production treatment of caching "not found" with a short TTL and guarding against missing-key floods.

DNS negative caching (RFC 2308) as the canonical prior art — how resolvers cache NXDOMAIN responses with an SOA-controlled TTL so repeated lookups of a nonexistent name do not re-query the authoritative server, the same mechanism this module models for a general read-through cache.
