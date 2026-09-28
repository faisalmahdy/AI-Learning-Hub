"""Jitter each cache entry's TTL -- entries created together with the same fixed TTL all expire at once and flood the origin with a synchronized wave of refetches.

A cache entry lives for its time-to-live and then expires, and the next request for it misses and refetches from the origin. In steady state those refetches trickle in, spread across time as entries were created at different moments, and the origin handles them comfortably. The danger is when many entries are created at the same moment: a cache warmed at deploy, a traffic spike that populates the cache in one burst, a batch load. If they all share the same TTL, they were born together and they die together.

At the instant that shared TTL elapses, every one of those entries expires simultaneously. The next requests all miss at once, and the origin receives the entire set of refetches in a single bucket -- a synchronized expiry stampede whose peak is the number of entries, hitting a backend that was sized for the gentle steady-state trickle. It is a self-inflicted thundering herd on a fixed schedule: the more successful the cache warm, the bigger the simultaneous wave when it expires, and it recurs every TTL because the refetched entries are all written back together with the same TTL again.

The fix is to stop giving entries identical lifetimes. Add a small random jitter to each entry's TTL -- base_ttl plus a random offset within a window -- so entries created together expire scattered across that window instead of at one instant. The peak refetch load flattens from the whole set to roughly the set divided by the window, and because each refetch re-jitters, the population stays desynchronized rather than re-clumping. It is the caching cousin of adding jitter to retry backoff: the same cure (break the synchronization) for the same disease (correlated events piling into one moment).

The rule: jitter each cache entry's TTL rather than using one fixed value, because entries populated together with identical TTLs expire together and flood the origin with a synchronized refetch wave -- spreading the TTL over a window flattens the peak to about the entry count divided by the window.

On this fixture 12 entries are populated at once. With a fixed TTL all 12 expire in the same bucket, a peak of 12 refetches at once; jittering the TTL over a 4-bucket window spreads them to 3 per bucket, a peak of 3. This computes both.

  --expiry    each entry's expiry bucket under a fixed TTL vs a jittered TTL
  --peak      the peak refetches in any one bucket, fixed vs jittered
  --check     a fixed TTL synchronizes expiry into one bucket; jitter spreads it and flattens the peak

n_entries, base_ttl, and jitter_window are the fixture; the expiry buckets and peaks are computed. Stdlib only.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "ttljitter.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def fixed_expiry(n, base):
    """Every entry gets the same TTL, so every entry expires in the same bucket."""
    return [base for _ in range(n)]


def jittered_expiry(n, base, window):
    """Each entry gets base + a deterministic offset within the window, spreading expiries."""
    return [base + (i % window) for i in range(n)]


def peak(expiries):
    """The most refetches landing in any single bucket."""
    return max(Counter(expiries).values())


# ----------------------------------------------------------------- printing

def expiry_view(data):
    n, base, window = data["n_entries"], data["base_ttl"], data["jitter_window"]
    fx = Counter(fixed_expiry(n, base))
    jt = Counter(jittered_expiry(n, base, window))
    print("EXPIRY — refetches per time bucket (%d entries populated together)" % n)
    print("-" * 56)
    buckets = sorted(set(fx) | set(jt))
    print("  bucket   fixed   jittered")
    for b in buckets:
        print("  %-7d  %-5d   %d" % (b, fx.get(b, 0), jt.get(b, 0)))
    print("-" * 56)
    print("  fixed TTL piles every refetch into one bucket; jitter spreads them")


def peak_view(data):
    n, base, window = data["n_entries"], data["base_ttl"], data["jitter_window"]
    fp = peak(fixed_expiry(n, base))
    jp = peak(jittered_expiry(n, base, window))
    print("PEAK — worst-case refetches in a single bucket")
    print("-" * 50)
    print("  fixed TTL    peak = %d" % fp)
    print("  jittered TTL peak = %d  (window %d)" % (jp, window))
    print("-" * 50)
    print("  jitter flattens the peak to about entries / window = %d" % -(-n // window))


def check(data):
    print("SELF-TEST — a fixed TTL synchronizes expiry into one bucket; jitter spreads it and flattens the peak")
    print("-" * 112)
    n, base, window = data["n_entries"], data["base_ttl"], data["jitter_window"]
    fx = fixed_expiry(n, base)
    jt = jittered_expiry(n, base, window)
    fp, jp = peak(fx), peak(jt)

    fixed_synchronized = len(set(fx)) == 1
    print("  fixed TTL: all entries expire in one bucket = %s (%d)" % (fixed_synchronized, fx[0]))

    fixed_peak_is_n = fp == n
    print("  fixed TTL: the peak equals the whole entry count = %s (%d)" % (fixed_peak_is_n, fp))

    jittered_spreads = len(set(jt)) == window
    print("  jittered TTL: expiries spread across the window = %s (%d buckets)" % (jittered_spreads, len(set(jt))))

    jitter_lowers_peak = jp < fp
    print("  jittered TTL: the peak is lower than fixed = %s (%d < %d)" % (jitter_lowers_peak, jp, fp))

    peak_matches_expectation = jp == -(-n // window)
    print("  jittered peak is about entries / window = %s (%d)" % (peak_matches_expectation, jp))

    ok = (fixed_synchronized and fixed_peak_is_n and jittered_spreads and jitter_lowers_peak and peak_matches_expectation)
    print("-" * 112)
    print("SELF-TEST %s  fixed_synchronized=%s  fixed_peak_is_n=%s  jittered_spreads=%s  jitter_lowers_peak=%s  peak_matches_expectation=%s"
          % ("PASS" if ok else "FAIL", fixed_synchronized, fixed_peak_is_n, jittered_spreads, jitter_lowers_peak, peak_matches_expectation))
    return ok


def main():
    p = argparse.ArgumentParser(description="Cache TTL jitter: jitter each cache entry's TTL rather than using one fixed value, because entries populated together with identical TTLs expire together and flood the origin with a synchronized refetch wave -- spreading the TTL over a window flattens the peak to about the entry count divided by the window.")
    p.add_argument("--expiry", action="store_true")
    p.add_argument("--peak", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("n_entries=%d  base_ttl=%d  jitter_window=%d  file=%s  (all fixture)"
          % (data["n_entries"], data["base_ttl"], data["jitter_window"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.expiry:
        expiry_view(data)
    elif args.peak:
        peak_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
