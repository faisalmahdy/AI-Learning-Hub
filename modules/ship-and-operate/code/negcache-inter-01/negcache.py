"""Cache the misses too, not just the hits -- otherwise repeated lookups of a key that does not exist hit the origin every single time.

A read-through cache has a simple rule: return the cached value if present, otherwise call the origin and cache what it returns. Buried in that rule is an assumption -- that every lookup eventually finds a value worth caching. Real traffic breaks it. A large fraction of lookups are for keys that do not exist: a mistyped URL, a deleted record, an id that was never issued, a scraper walking a numeric range, a bot probing for endpoints. For each of those the origin answers 'not found', and a not-found is not a value, so the naive cache stores nothing.

That gap is the whole problem. Because nothing was stored, the next lookup of the same missing key misses the cache again and calls the origin again. A missing key requested a thousand times is a thousand origin calls -- the cache faithfully protects the origin from repeated hits but does nothing for repeated misses. When a burst of missing-key requests arrives, accidental or malicious, it sails straight through the cache to the backing store, which is exactly the store you were trying to shield. This is cache penetration, and it turns the cache from a shield into a sieve for the one traffic pattern most likely to be hostile.

Negative caching closes the gap by caching absence as a first-class result. When the origin returns 'not found', store a marker -- 'this key does not exist' -- under that key, usually with a short time-to-live. Now a repeated lookup of a missing key is served from the cache like any hit, and every distinct key, present or absent, costs at most one origin call. The cache protects the origin from repeated misses exactly as it already protected it from repeated hits.

The rule: cache negative results (the 'not found' answers), not only positive ones, because a cache that stores only hits lets every repeat lookup of a non-existent key fall through to the origin -- so a flood of missing-key requests bypasses the cache entirely, while negative caching caps every key at one origin call.

On this fixture the lookups include a missing key x requested four times and y twice. Without negative caching the origin is called 8 times (every missing-key lookup goes through); with negative caching it is called 4 times -- once per distinct key. This computes both.

  --lookups   each lookup in order and whether it reaches the origin under each policy
  --origin    the origin-call counts: hits-only cache vs negative cache, and the calls saved
  --check     without negative caching repeated missing-key lookups all hit the origin; with it every key costs one origin call

store and lookups are the fixture; the origin-call counts and per-lookup decisions are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "negcache.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


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


def origin_calls(origin_hits):
    return sum(1 for h in origin_hits if h)


# ----------------------------------------------------------------- printing

def lookups_view(data):
    store, lookups = set(data["store"]), data["lookups"]
    ho = run_hits_only(store, lookups)
    ng = run_negative(store, lookups)
    print("LOOKUPS — each request and whether it reaches the origin (o = origin call, . = served from cache)")
    print("-" * 74)
    print("  #   key  exists  hits-only  negative")
    for i, (k, h, n) in enumerate(zip(lookups, ho, ng)):
        print("  %-2d  %-3s  %-6s  %-9s  %s" % (i, k, "yes" if k in store else "no ", "o" if h else ".", "o" if n else "."))
    print("-" * 74)
    print("  the missing key x hits the origin 4 times hits-only, once with negative caching")


def origin_view(data):
    store, lookups = set(data["store"]), data["lookups"]
    ho = origin_calls(run_hits_only(store, lookups))
    ng = origin_calls(run_negative(store, lookups))
    distinct = len(set(lookups))
    print("ORIGIN — origin calls under each policy (%d lookups, %d distinct keys)" % (len(lookups), distinct))
    print("-" * 60)
    print("  hits-only cache (positive only)  = %d origin call(s)" % ho)
    print("  negative cache (positive+absent) = %d origin call(s)" % ng)
    print("  calls saved by negative caching  = %d" % (ho - ng))
    print("-" * 60)
    print("  negative caching caps the origin at one call per distinct key (%d)" % distinct)


def check(data):
    print("SELF-TEST — without negative caching repeated missing-key lookups all hit the origin; with it every key costs one origin call")
    print("-" * 122)
    store, lookups = set(data["store"]), data["lookups"]
    ho_hits = run_hits_only(store, lookups)
    ng_hits = run_negative(store, lookups)
    ho, ng = origin_calls(ho_hits), origin_calls(ng_hits)
    distinct = len(set(lookups))

    counts = {k: lookups.count(k) for k in lookups}
    repeated_missing = [k for k in set(lookups) if k not in store and counts[k] > 1]
    repeated_missing_keys = len(repeated_missing) > 0
    print("  some non-existent key is looked up more than once = %s (%s)" % (repeated_missing_keys, sorted(repeated_missing)))

    missing_origin_calls = sum(1 for k, h in zip(lookups, ho_hits) if h and k not in store)
    hitsonly_rehits_origin = missing_origin_calls > len(set(k for k in lookups if k not in store))
    print("  hits-only: missing keys reach the origin more than once each = %s (%d origin calls for missing keys)"
          % (hitsonly_rehits_origin, missing_origin_calls))

    mkey = sorted(repeated_missing)[0]
    mkey_origin_neg = sum(1 for k, h in zip(lookups, ng_hits) if h and k == mkey)
    negcache_caches_misses = mkey_origin_neg == 1
    print("  negative caching serves repeat lookups of missing key %r from cache = %s (%d origin call)" % (mkey, negcache_caches_misses, mkey_origin_neg))

    negcache_fewer_origin_calls = ng < ho
    print("  negative caching makes fewer origin calls = %s (%d < %d)" % (negcache_fewer_origin_calls, ng, ho))

    negcache_one_per_key = ng == distinct
    print("  negative caching costs exactly one origin call per distinct key = %s (%d == %d)" % (negcache_one_per_key, ng, distinct))

    ok = (repeated_missing_keys and hitsonly_rehits_origin and negcache_caches_misses
          and negcache_fewer_origin_calls and negcache_one_per_key)
    print("-" * 122)
    print("SELF-TEST %s  repeated_missing_keys=%s  hitsonly_rehits_origin=%s  negcache_caches_misses=%s  negcache_fewer_origin_calls=%s  negcache_one_per_key=%s"
          % ("PASS" if ok else "FAIL", repeated_missing_keys, hitsonly_rehits_origin, negcache_caches_misses, negcache_fewer_origin_calls, negcache_one_per_key))
    return ok


def main():
    p = argparse.ArgumentParser(description="Negative caching: cache negative results (the 'not found' answers), not only positive ones, because a cache that stores only hits lets every repeat lookup of a non-existent key fall through to the origin -- so a flood of missing-key requests bypasses the cache entirely, while negative caching caps every key at one origin call.")
    p.add_argument("--lookups", action="store_true")
    p.add_argument("--origin", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("store=%s  lookups=%s  file=%s  (the store and lookup sequence are a fixture)"
          % (data["store"], data["lookups"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.lookups:
        lookups_view(data)
    elif args.origin:
        origin_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
