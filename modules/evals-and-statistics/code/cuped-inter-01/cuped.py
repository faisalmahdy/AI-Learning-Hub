"""Subtract the pre-experiment covariate (CUPED) to shrink an eval metric's variance -- more power from the same units.

An A/B test or eval detects a treatment effect against a background of noise, and most of that noise is not caused by
the treatment at all: it is the pre-existing spread between units. Some users, tasks, or shards simply score higher than
others for reasons that predate the experiment, and that variation sits in your metric inflating its variance, widening
the confidence interval, and forcing you to collect more data to resolve a real but small effect. The wasteful part is
that this pre-existing spread is often KNOWN -- you measured each unit before the experiment, in a baseline period -- so
the variance you are struggling against is variance you could have subtracted out.

CUPED does exactly that. For each unit take a pre-experiment covariate x (its baseline-period metric) correlated with
the experiment metric y, and form an adjusted metric y' = y - theta*(x - mean(x)), where theta = Cov(x,y)/Var(x) is the
slope of y on x. The subtraction removes the part of each unit's y that its pre-experiment level already predicted --
the treatment-irrelevant head start -- while leaving the treatment effect untouched. The adjusted metric has the SAME
mean as the original, so it estimates the same quantity without bias; but its variance is lower by the factor
(1 - rho^2), where rho is the correlation between x and y. A covariate correlated 0.9 with the outcome cuts the variance
by about 80%, which is the same precision you would get from roughly five times as many units. You bought statistical
power with data you already had.

On this fixture the pre-period covariate correlates about 0.91 with the experiment metric. Adjusting by CUPED leaves the
mean at 21.250 exactly but drops the variance from 25.69 to 4.18 -- a reduction matching (1 - rho^2) = 0.16, which is an
effective-sample-size multiplier of about 6. This computes both.

  --adjust   each unit's x, y, and CUPED-adjusted y'; the mean (unchanged) and variance (reduced)
  --reduce   the variance before and after, the reduction factor, and that it equals 1 - rho^2 (the power gain)
  --check    the adjusted mean is unchanged (unbiased); the variance drops by exactly 1 - rho^2; effective N rises

The pre-period and experiment metrics are the fixture; every statistic is computed exactly. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "cuped.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mean(v):
    return sum(v) / len(v)


def variance(v):
    """Population variance (divide by n), so the CUPED variance identity holds exactly."""
    m = mean(v)
    return sum((a - m) ** 2 for a in v) / len(v)


def covariance(x, y):
    mx, my = mean(x), mean(y)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / len(x)


def correlation(x, y):
    return covariance(x, y) / (variance(x) ** 0.5 * variance(y) ** 0.5)


def theta(x, y):
    """The CUPED coefficient: the slope of y on x, Cov(x,y)/Var(x)."""
    return covariance(x, y) / variance(x)


def cuped_adjust(x, y):
    """The variance-reduced metric y' = y - theta*(x - mean(x)); same mean as y, lower variance."""
    t, mx = theta(x, y), mean(x)
    return [b - t * (a - mx) for a, b in zip(x, y)]


# ----------------------------------------------------------------- printing

def adjust_view(data):
    x, y = data["x_pre"], data["y_exp"]
    yp = cuped_adjust(x, y)
    print("ADJUST — raw metric y vs CUPED-adjusted y' = y - theta*(x - mean(x))")
    print("-" * 60)
    print("  theta (slope of y on x) = %.4f" % theta(x, y))
    print("  x (pre)    y (exp)    y' (adjusted)")
    for a, b, c in zip(x, y, yp):
        print("  %-8.1f   %-8.1f   %.4f" % (a, b, c))
    print("-" * 60)
    print("  mean:   y = %.3f   y' = %.3f   (unchanged: y' is unbiased)" % (mean(y), mean(yp)))
    print("  variance: y = %.3f   y' = %.3f   (reduced)" % (variance(y), variance(yp)))


def reduce_view(data):
    x, y = data["x_pre"], data["y_exp"]
    yp = cuped_adjust(x, y)
    rho = correlation(x, y)
    print("REDUCE — variance reduction and the power gain")
    print("-" * 58)
    print("  correlation rho(x, y)      = %.4f" % rho)
    print("  variance of y              = %.4f" % variance(y))
    print("  variance of y' (CUPED)     = %.4f" % variance(yp))
    print("  reduction factor           = %.4f   (equals 1 - rho^2 = %.4f)" % (variance(yp) / variance(y), 1 - rho ** 2))
    print("  effective sample-size gain = %.1fx  (1 / (1 - rho^2))" % (1 / (1 - rho ** 2)))
    print("-" * 58)
    print("  the tighter variance is the same precision as many more units, at no extra data cost.")


def check(data):
    print("SELF-TEST — the adjusted mean is unchanged (unbiased); the variance drops by exactly 1 - rho^2; effective N rises")
    print("-" * 112)
    x, y = data["x_pre"], data["y_exp"]
    yp = cuped_adjust(x, y)
    rho = correlation(x, y)

    mean_unchanged = abs(mean(yp) - mean(y)) < 1e-9
    print("  the CUPED mean equals the raw mean (unbiased) = %s (%.4f)" % (mean_unchanged, mean(yp)))

    variance_reduced = variance(yp) < variance(y)
    print("  the CUPED variance is lower than the raw variance = %s (%.4f < %.4f)" % (variance_reduced, variance(yp), variance(y)))

    matches_identity = abs(variance(yp) / variance(y) - (1 - rho ** 2)) < 1e-9
    print("  the reduction factor equals 1 - rho^2 exactly = %s (%.4f vs %.4f)" % (matches_identity, variance(yp) / variance(y), 1 - rho ** 2))

    theta_is_slope = abs(theta(x, y) - covariance(x, y) / variance(x)) < 1e-12
    print("  theta is the slope Cov(x,y)/Var(x) = %s (%.4f)" % (theta_is_slope, theta(x, y)))

    effective_n_rises = 1 / (1 - rho ** 2) > 1.0
    print("  the effective sample size rises = %s (%.1fx)" % (effective_n_rises, 1 / (1 - rho ** 2)))

    ok = mean_unchanged and variance_reduced and matches_identity and theta_is_slope and effective_n_rises
    print("-" * 112)
    print("SELF-TEST %s  mean_unchanged=%s  variance_reduced=%s  matches_identity=%s  theta_is_slope=%s  effective_n_rises=%s"
          % ("PASS" if ok else "FAIL", mean_unchanged, variance_reduced, matches_identity, theta_is_slope, effective_n_rises))
    return ok


def main():
    p = argparse.ArgumentParser(description="CUPED variance reduction: subtract a pre-experiment covariate to lower an eval metric's variance by 1 - rho^2 without bias, gaining statistical power from data you already had.")
    p.add_argument("--adjust", action="store_true")
    p.add_argument("--reduce", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("units=%d  file=%s  (the pre-period and experiment metrics are a fixture)" % (len(data["x_pre"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.adjust:
        adjust_view(data)
    elif args.reduce:
        reduce_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
