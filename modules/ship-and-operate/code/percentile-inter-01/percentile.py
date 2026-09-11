"""Compute the fleet p99 from the merged samples -- averaging the per-host p99s is not a percentile and understates the tail.

A percentile is a rank statistic: the p99 of a set of latencies is the value at the 99th-of-100 position when they are
sorted, the number that 99% of requests came in under. That definition is about ONE pooled set of measurements. It does
not distribute over a partition of the data, because rank is not linear: the mean of two groups equals the grouped mean
(means average), but the p99 of two groups does NOT equal the average of their p99s, and usually is not any simple
function of them. So when a service runs on many hosts and each host reports its own p99, you cannot combine those
numbers by averaging -- doing so answers a question nobody asked ('the average of our hosts' tail cutoffs') and silently
under-reports the real fleet tail, because a slow host's tail gets diluted by the fast hosts' low p99s instead of
counted as the slow requests it actually is.

The correct fleet percentile is computed from the pooled requests: merge every host's samples into one set and take the
percentile of that -- or, equivalently and cheaply, sum the hosts' histograms bucket by bucket and read the percentile
off the combined histogram. Histograms are mergeable (bucket counts add), which is exactly why real metrics systems ship
histograms or mergeable sketches (t-digest, HDR histogram) per host and combine THOSE, never per-host percentiles. The
rule: aggregate the distributions, then take the percentile; never take the percentiles, then aggregate.

On this fixture two hosts serve all 100 requests at 10ms and a third serves 90 at 10ms and 10 at 1000ms. Each fast host
has p99 = 10 and the slow host has p99 = 1000, so the mean of the three p99s is (10+10+1000)/3 = 340ms -- which looks
like a merely-elevated tail. But the true fleet p99, from all 300 requests (290 at 10ms, 10 at 1000ms), is 1000ms: one
request in a hundred really waits a full second, and the averaged number hid two-thirds of that. The fleet median stays
10ms, so a median-only dashboard shows nothing wrong at all. This computes both the wrong and the right aggregation.

  --aggregate  each host's p99, the (wrong) mean-of-p99s, and the (right) p99 of the merged histogram -- 340 vs 1000
  --merge      sum the histograms and read percentiles off the pool; the median hides the tail the p99 exposes
  --check      averaging per-host p99s understates the true fleet p99, which the merged histogram recovers; median hides it

The per-host histograms are the fixture; every percentile is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "percentile.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def hist_percentile(hist, q):
    """Nearest-rank percentile of a {latency_ms: count} histogram: the value at rank ceil(q/100 * total)."""
    values = sorted(int(v) for v in hist)
    total = sum(hist.values())
    rank = max(1, math.ceil(q / 100 * total))
    cum = 0
    for v in values:
        cum += hist[str(v)]
        if cum >= rank:
            return v
    return values[-1]


def merge_hists(hosts):
    """Sum the per-host histograms bucket by bucket -- the correct way to combine, because counts are additive."""
    merged = {}
    for h in hosts:
        for bucket, count in h["hist"].items():
            merged[bucket] = merged.get(bucket, 0) + count
    return merged


def mean_of_host_percentiles(hosts, q):
    """The WRONG aggregation: take each host's percentile, then average those numbers."""
    ps = [hist_percentile(h["hist"], q) for h in hosts]
    return sum(ps) / len(ps)


def fleet_percentile(hosts, q):
    """The RIGHT aggregation: merge the histograms, then take the percentile of the pool."""
    return hist_percentile(merge_hists(hosts), q)


# ----------------------------------------------------------------- printing

def aggregate_view(data):
    hosts = data["hosts"]
    print("AGGREGATE — per-host p99, averaged vs merged")
    print("-" * 60)
    print("  host      requests   p99 (ms)")
    for h in hosts:
        print("  %-8s  %-9d  %d" % (h["name"], sum(h["hist"].values()), hist_percentile(h["hist"], 99)))
    print("-" * 60)
    avg = mean_of_host_percentiles(hosts, 99)
    true = fleet_percentile(hosts, 99)
    print("  mean of the per-host p99s (WRONG) = %.1f ms" % avg)
    print("  p99 of the merged samples  (RIGHT) = %d ms" % true)
    print("  averaging hid %.1f ms of tail -- it under-reports by %.1fx" % (true - avg, true / avg))


def merge_view(data):
    hosts = data["hosts"]
    merged = merge_hists(hosts)
    total = sum(merged.values())
    print("MERGE — sum the histograms, then read percentiles off the pool")
    print("-" * 60)
    print("  merged histogram (latency ms -> requests): %s" % {int(k): merged[k] for k in sorted(merged, key=int)})
    print("  total requests = %d" % total)
    print("-" * 60)
    for q in (50, 90, 99):
        print("  fleet p%-2d = %d ms" % (q, hist_percentile(merged, q)))
    print("  the median is 10 ms -- a median-only dashboard shows nothing wrong, but 1% of requests wait 1000 ms.")


def check(data):
    print("SELF-TEST — averaging per-host p99s understates the true fleet p99, which the merged histogram recovers; median hides it")
    print("-" * 120)
    hosts = data["hosts"]

    host_p99s = [hist_percentile(h["hist"], 99) for h in hosts]
    host_p99s_are = host_p99s == [10, 10, 1000]
    print("  the per-host p99s are two fast and one slow = %s (%s)" % (host_p99s_are, host_p99s))

    avg = mean_of_host_percentiles(hosts, 99)
    true = fleet_percentile(hosts, 99)
    avg_understates = avg < true
    print("  the mean of per-host p99s is below the true fleet p99 = %s (%.1f < %d)" % (avg_understates, avg, true))

    merged_recovers_true = fleet_percentile(hosts, 99) == 1000
    print("  the merged histogram gives the true fleet p99 = %s (%d ms)" % (merged_recovers_true, true))

    understated_by_2x = true / avg > 2
    print("  averaging under-reports the tail by more than 2x = %s (%.1fx)" % (understated_by_2x, true / avg))

    median_hides_tail = fleet_percentile(hosts, 50) == 10 and true == 1000
    print("  the fleet median hides the tail the p99 exposes = %s (p50=%d, p99=%d)"
          % (median_hides_tail, fleet_percentile(hosts, 50), true))

    ok = host_p99s_are and avg_understates and merged_recovers_true and understated_by_2x and median_hides_tail
    print("-" * 120)
    print("SELF-TEST %s  host_p99s_are=%s  avg_understates=%s  merged_recovers_true=%s  understated_by_2x=%s  median_hides_tail=%s"
          % ("PASS" if ok else "FAIL", host_p99s_are, avg_understates, merged_recovers_true, understated_by_2x, median_hides_tail))
    return ok


def main():
    p = argparse.ArgumentParser(description="Percentile aggregation: a percentile is a rank statistic and does not average, so the fleet p99 must be computed from the merged samples (or summed histograms), never from the mean of per-host p99s, which dilutes a slow host's tail and under-reports the real fleet latency.")
    p.add_argument("--aggregate", action="store_true")
    p.add_argument("--merge", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("hosts=%s  file=%s  (the per-host histograms are a fixture)"
          % ([(h["name"], sum(h["hist"].values())) for h in data["hosts"]], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.aggregate:
        aggregate_view(data)
    elif args.merge:
        merge_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
