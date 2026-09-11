#!/usr/bin/env python3
"""The mean describes no typical request -- but it is the only right total.

Costs, latencies, and token counts are almost never symmetric. They pile up at the
small end and trail off into a thin tail of huge values, and on that shape the mean
and the median answer two different questions and disagree loudly. The mean here is
64 cents; the median is 3 cents; not one of the twenty requests costs anywhere near
64 cents. So "the average request costs 64 cents" is true arithmetic and a false
picture of a typical request -- 80% of requests cost less than that, and the average
is dragged up by four whales. Yet the mean is not wrong; it is answering a different
question. This measures which summary answers which, and the budgeting bug that
comes from swapping them.

The rule the numbers force: the mean is the right estimator for a TOTAL (sum equals
mean times count, exactly), and the median is the right estimator for a TYPICAL
value. Use the median to describe spend per request; use the mean -- never the
median -- to forecast the bill. Confuse them and you either scare finance with a
"typical" cost nobody pays, or you under-budget the real bill by an order of
magnitude because the median ignores the tail that owns most of the money.

  --summary     mean vs median, fraction below the mean, and the tail's share
  --budget      forecast the total with mean*N vs median*N against the real bill
  --check       right-skewed; most below the mean; median under-forecasts; mean is exact

Stdlib only. Deterministic.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "costs.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))["costs"]


# ---------------------------------------------------------- the statistics

def mean(xs):
    return sum(xs) / len(xs)


def median(xs):
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def frac_below(xs, threshold):
    return sum(1 for x in xs if x < threshold) / len(xs)


def top_decile_share(xs):
    """What fraction of the total sum comes from the largest 10% of items."""
    s = sorted(xs, reverse=True)
    k = max(1, len(s) // 10)
    return sum(s[:k]) / sum(s)


# ------------------------------------------------------------- the forecast

def forecast_total(per_request_estimate, n):
    """Project the whole bill from a per-request number times the request count."""
    return per_request_estimate * n


# ----------------------------------------------------------------- printing

def summary_view(xs):
    m, md = mean(xs), median(xs)
    print("SUMMARY — one skewed distribution, two summaries that disagree")
    print("-" * 66)
    print("  n            = %d requests" % len(xs))
    print("  mean         = $%.2f  (the total split evenly)" % m)
    print("  median       = $%.2f  (the middle request)" % md)
    print("  mean / median= %.0fx  (right-skew: the mean is dragged up by the tail)" % (m / md))
    print("  below mean   = %.0f%% of requests cost less than the mean" % (100 * frac_below(xs, m)))
    print("  top 10%% share= %.0f%% of all spend is in the largest 10%% of requests" % (100 * top_decile_share(xs)))
    print("-" * 66)
    print("  the mean is a real number no typical request pays; the median is typical")
    print("  but blind to the tail that holds most of the money.")


def budget_view(xs):
    n = len(xs)
    true_total = sum(xs)
    by_mean = forecast_total(mean(xs), n)
    by_median = forecast_total(median(xs), n)
    print("BUDGET — forecast the whole bill from a per-request summary")
    print("-" * 66)
    print("  true total (sum of all requests) = $%.2f" % true_total)
    print("  forecast with mean*N             = $%.2f  (off by $%.2f)" % (by_mean, abs(by_mean - true_total)))
    print("  forecast with median*N           = $%.2f  (off by $%.2f)" % (by_median, abs(by_median - true_total)))
    print("-" * 66)
    print("  mean*N recovers the total exactly by construction; median*N under-budgets")
    print("  %.0fx low, because it throws away the tail that is most of the bill." % (true_total / by_median))


def check(xs):
    print("SELF-TEST — the mean is exact for totals; the median is right for typical")
    print("-" * 66)
    m, md = mean(xs), median(xs)
    n = len(xs)

    right_skew = m > md * 5
    print("  right-skewed: mean >> median = %s ($%.2f vs $%.2f)" % (right_skew, m, md))

    most_below = frac_below(xs, m) > 0.5
    print("  most requests cost less than the mean = %s (%.0f%%)" % (most_below, 100 * frac_below(xs, m)))

    tail_heavy = top_decile_share(xs) > 0.5
    print("  top 10%% of requests hold most of the spend = %s (%.0f%%)" % (tail_heavy, 100 * top_decile_share(xs)))

    mean_exact = abs(forecast_total(m, n) - sum(xs)) < 1e-9
    print("  mean*N equals the true total exactly = %s" % mean_exact)

    median_underforecasts = forecast_total(md, n) < sum(xs) / 5
    print("  median*N under-forecasts the bill badly = %s ($%.2f vs $%.2f)"
          % (median_underforecasts, forecast_total(md, n), sum(xs)))

    ok = right_skew and most_below and tail_heavy and mean_exact and median_underforecasts
    print("-" * 66)
    print("SELF-TEST %s  skew=%s  most_below=%s  tail_heavy=%s  mean_exact=%s  median_low=%s"
          % ("PASS" if ok else "FAIL", right_skew, most_below, tail_heavy, mean_exact, median_underforecasts))
    return ok


def main():
    p = argparse.ArgumentParser(description="Heavy tails: mean for totals, median for typical.")
    p.add_argument("--summary", action="store_true")
    p.add_argument("--budget", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    xs = load()
    print("costs=%d  file=%s  (per-request dollars are a fixture)" % (len(xs), DATA.name))
    print("")

    if args.check:
        return 0 if check(xs) else 1
    if args.summary:
        summary_view(xs)
    elif args.budget:
        budget_view(xs)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
