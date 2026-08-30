"""Track the p99, not the mean -- the average latency hides the tail regression that hits 1 in 20 users.

A latency number in a dashboard is almost always the mean, and the mean is the one statistic that
cannot see the tail. Ninety-five percent of your requests are fast, a few percent are slow, and the
mean drowns those few percent in the many fast ones. So when the slow tail gets much slower -- the
exact failure your users feel -- the mean barely twitches and the dashboard stays green. Meanwhile one
in twenty users waits nearly a second on every request and churns.

Percentiles see what the mean cannot. The p99 is the latency that 99% of requests come in under, so it
is a direct readout of the tail: if p99 is 900ms, the slowest 1% of requests take at least that long.
SLOs are written on percentiles ("p99 under 500ms") precisely because that is what bounds the worst
experience, and the mean does not bound anything.

On this fixture the same endpoint is measured before and after a regression. Both samples are 95%
fast requests at 50ms; the regression pushes the slow 5% from 200ms out to 900ms. The mean creeps from
57.5 to 92.5 -- still comfortably under a 150ms mean-based alert, so a mean monitor stays silent. But
the p99 jumps from 200 to 900, smashing through the 500ms SLO. This computes the mean and the
percentiles for both samples and shows which monitor catches the regression and which sleeps through it.

  --samples    the two latency samples and their shape
  --stats      the mean, p50, p90, p99 for each sample, against the SLO and the mean alert
  --check      the mean stays under its alert while the p99 breaches the SLO -- averaging hid the tail

The latency samples and thresholds are the fixture; every statistic is computed. Stdlib only.
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


def mean(xs):
    return round(sum(xs) / len(xs), 2)


def percentile(xs, p):
    """Nearest-rank percentile: the smallest value that at least p% of the sample come in under."""
    s = sorted(xs)
    rank = math.ceil(p / 100 * len(s))
    return s[rank - 1]


# ----------------------------------------------------------------- printing

def samples_view(data):
    print("SAMPLES — two 100-request latency samples for the same endpoint (ms)")
    print("-" * 58)
    for name, xs in data["samples"].items():
        fast = sum(1 for x in xs if x <= 50)
        slow = len(xs) - fast
        slowest = max(xs)
        print("  %-10s %d fast (50ms) + %d slow (%dms)" % (name, fast, slow, slowest))
    print("-" * 58)
    print("  95% of requests are identical across the two; only the slow 5% changed.")


def stats_view(data):
    slo, alert = data["slo_p99_ms"], data["mean_alert_ms"]
    print("STATS — mean vs percentiles; SLO p99<%d, mean alert>%d" % (slo, alert))
    print("-" * 62)
    print("  sample      mean    p50   p90    p99    mean alert   SLO p99")
    for name, xs in data["samples"].items():
        m = mean(xs)
        p99 = percentile(xs, 99)
        mflag = "FIRES" if m > alert else "quiet"
        sflag = "BREACH" if p99 > slo else "ok"
        print("  %-10s %5.1f  %4d  %4d  %5d    %-9s    %s"
              % (name, m, percentile(xs, 50), percentile(xs, 90), p99, mflag, sflag))
    print("-" * 62)
    print("  the mean alert never fires; the p99 breaches the SLO after the regression.")


def check(data):
    print("SELF-TEST — the mean stays under its alert while the p99 breaches the SLO (averaging hid the tail)")
    print("-" * 92)
    slo, alert = data["slo_p99_ms"], data["mean_alert_ms"]
    base, regr = data["samples"]["baseline"], data["samples"]["regressed"]

    m_base, m_regr = mean(base), mean(regr)
    mean_under_alert = m_regr <= alert  # the regressed mean is still below the alert threshold
    print("  the mean stays under its alert after the regression = %s (%.1f -> %.1f, alert %d)"
          % (mean_under_alert, m_base, m_regr, alert))

    p99_base, p99_regr = percentile(base, 99), percentile(regr, 99)
    p99_breaches = p99_base <= slo < p99_regr
    print("  the p99 goes from within-SLO to breaching = %s (%d -> %d, SLO %d)"
          % (p99_breaches, p99_base, p99_regr, slo))

    p50_unchanged = percentile(base, 50) == percentile(regr, 50)
    print("  even the median is unchanged -- only the tail moved = %s (p50 %d)"
          % (p50_unchanged, percentile(regr, 50)))

    tail_moves_more = (p99_regr - p99_base) > 10 * (m_regr - m_base)
    print("  the p99 moved far more than the mean = %s (p99 +%d vs mean +%.1f)"
          % (tail_moves_more, p99_regr - p99_base, m_regr - m_base))

    ok = mean_under_alert and p99_breaches and p50_unchanged and tail_moves_more
    print("-" * 92)
    print("SELF-TEST %s  mean_under_alert=%s  p99_breaches=%s  p50_unchanged=%s  tail_moves_more=%s"
          % ("PASS" if ok else "FAIL", mean_under_alert, p99_breaches, p50_unchanged, tail_moves_more))
    return ok


def main():
    p = argparse.ArgumentParser(description="Track the p99, not the mean -- averaging hides the latency tail.")
    p.add_argument("--samples", action="store_true")
    p.add_argument("--stats", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("samples=%s  slo_p99=%dms  mean_alert=%dms  file=%s  (the latency samples are a fixture)"
          % (list(data["samples"]), data["slo_p99_ms"], data["mean_alert_ms"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.samples:
        samples_view(data)
    elif args.stats:
        stats_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
