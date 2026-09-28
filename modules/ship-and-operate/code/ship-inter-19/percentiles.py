"""Pool the samples to get a fleet percentile, or averaging per-shard p90s reports a number that is nowhere.

Dashboards love to compute a percentile per shard (or per host) and then average those percentiles into a
single fleet number. It reads as reasonable -- "average the p90s to get the overall p90" -- and it is wrong,
because a percentile is not a mean and does not average. Averaging p90s weights every shard equally, so a tiny
overloaded shard handling 10 requests counts as much as the healthy shard handling 90. The averaged number is
not the fleet's p90; it is not any percentile of anything; it is a blend that happens to land between the two
shard values and mean nothing.

The correct fleet percentile comes from the pooled samples: put every request's latency into one set and take
the percentile of that. Pooling weights each shard by how many requests it actually served, so the small
shard's slow requests occupy only their true share of the tail. In production you cannot ship raw samples
around, so systems merge HISTOGRAMS -- each shard reports bucket counts, the counts add up, and the percentile
is read off the summed histogram. Either way the operation is 'combine the distributions, then take the
percentile' -- never 'take the percentiles, then combine them'.

On this fixture the small_slow shard (10 requests at 200ms) has p90 200; the big_fast shard (90 requests at
10ms) has p90 10. Averaging them gives 105ms. Pooling all 100 requests gives a p90 of 10ms, because the 10
slow requests are only the top 10% of traffic. Averaging overstates the tail by more than tenfold. This
computes both.

  --percentiles   each shard's p90, the average of them, and the pooled p90
  --pool          why pooling differs: the slow shard is a minority of total traffic
  --check         the average of per-shard p90s is not the pooled p90; only pooling is correct

The samples and percentile are the fixture; every value is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "latencies.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def percentile(samples, p):
    """Nearest-rank percentile: the smallest value at or above the p-th position."""
    s = sorted(samples)
    idx = max(0, min(len(s) - 1, math.ceil(p / 100 * len(s)) - 1))
    return s[idx]


def average(xs):
    return sum(xs) / len(xs)


def pooled(shards):
    out = []
    for v in shards.values():
        out += v
    return out


# ----------------------------------------------------------------- printing

def percentiles_view(data):
    p, shards = data["percentile"], data["shards"]
    per_shard = {name: percentile(v, p) for name, v in shards.items()}
    print("PERCENTILES — per-shard p%d, their average, and the pooled p%d" % (p, p))
    print("-" * 62)
    for name, v in shards.items():
        print("  %-11s %3d requests   p%d = %dms" % (name, len(v), p, per_shard[name]))
    print("  -")
    print("  average of the p%ds:  %.0fms   <- the tempting wrong answer" % (p, average(list(per_shard.values()))))
    print("  pooled p%d:           %dms   <- the correct fleet value" % (p, percentile(pooled(shards), p)))
    print("-" * 62)
    print("  averaging counts the two shards equally; pooling counts requests.")


def pool_view(data):
    p, shards = data["percentile"], data["shards"]
    all_s = pooled(shards)
    slow = shards["small_slow"]
    print("POOL — why the slow shard barely moves the pooled p%d" % p)
    print("-" * 62)
    print("  total requests: %d   slow requests: %d (%.0f%% of traffic)" % (len(all_s), len(slow), 100 * len(slow) / len(all_s)))
    print("  the slowest %d%% of %d requests start at position %d" % (100 - p, len(all_s), math.ceil(p / 100 * len(all_s))))
    print("  the %d slow requests sit above p%d, so p%d reads the fast value %dms" % (len(slow), p, p, percentile(all_s, p)))
    print("-" * 62)
    print("  a minority shard's tail lands past p%d and does not set it." % p)


def check(data):
    print("SELF-TEST — the average of per-shard p90s is not the pooled p90; only pooling is correct")
    print("-" * 100)
    p, shards = data["percentile"], data["shards"]
    per_shard = {name: percentile(v, p) for name, v in shards.items()}
    avg = average(list(per_shard.values()))
    pool_p = percentile(pooled(shards), p)

    average_differs_from_pooled = avg != pool_p
    print("  averaging the p%ds differs from the pooled p%d = %s (%.0f vs %d)" % (p, p, average_differs_from_pooled, avg, pool_p))

    averaging_overstates = avg > pool_p
    print("  the averaged number overstates the tail = %s (%.0f > %d)" % (averaging_overstates, avg, pool_p))

    shards_unequal_size = len(shards["small_slow"]) != len(shards["big_fast"])
    print("  the shards serve different request counts = %s (%d vs %d)" % (shards_unequal_size, len(shards["small_slow"]), len(shards["big_fast"])))

    pooled_matches_majority = pool_p == percentile(shards["big_fast"], p)
    print("  the pooled p%d matches the majority shard's value = %s (%dms)" % (p, pooled_matches_majority, pool_p))

    pooled_uses_all_samples = len(pooled(shards)) == sum(len(v) for v in shards.values())
    print("  pooling uses every request's sample = %s (%d)" % (pooled_uses_all_samples, len(pooled(shards))))

    ok = average_differs_from_pooled and averaging_overstates and shards_unequal_size and pooled_matches_majority and pooled_uses_all_samples
    print("-" * 100)
    print("SELF-TEST %s  average_differs_from_pooled=%s  averaging_overstates=%s  shards_unequal_size=%s  pooled_matches_majority=%s  pooled_uses_all_samples=%s"
          % ("PASS" if ok else "FAIL", average_differs_from_pooled, averaging_overstates, shards_unequal_size, pooled_matches_majority, pooled_uses_all_samples))
    return ok


def main():
    p = argparse.ArgumentParser(description="Pool the samples (or merge histograms) to get a fleet percentile; never average per-shard percentiles.")
    p.add_argument("--percentiles", action="store_true")
    p.add_argument("--pool", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("shards=%d  percentile=p%d  total_requests=%d  file=%s  (the samples are a fixture)"
          % (len(data["shards"]), data["percentile"], sum(len(v) for v in data["shards"].values()), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.percentiles:
        percentiles_view(data)
    elif args.pool:
        pool_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
