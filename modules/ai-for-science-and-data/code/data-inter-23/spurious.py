"""Correlate the changes, not the levels, or two unrelated trending series look strongly correlated.

Two time series that both trend will correlate with each other whether or not they have anything to do with one
another. A trend is a series that wanders and stays -- a random walk, a growing population, a rising price -- and
any two trends line up by accident far more often than two flat, noisy series do: if both happen to drift upward
over the window, their levels track; if one drifts up and the other down, they track negatively. Either way the
correlation coefficient comes out large, and it means nothing, because neither series caused the other. This is
spurious correlation from trend, and it is why "X and Y both rose over the decade, correlation 0.9" is not
evidence of any link -- almost everything that grows correlates with almost everything else that grows.

The tell, and the fix, is to look at the CHANGES instead of the levels. A random walk's value carries the whole
history of its wandering, so two walks' levels share the accident of where they drifted. But the step-to-step
CHANGES -- the first differences -- are just the independent random increments, with the trend removed. The
differences of two independent walks are uncorrelated, correctly reporting no relationship. Differencing strips
out the shared drift that faked the correlation and leaves the actual, unrelated, noise. When a relationship
survives differencing it may be real; a relationship that lives only in the levels is trend lining up with trend.

On this fixture two independent random walks have a level correlation of -0.886 -- strong, and entirely spurious.
Their first differences correlate at -0.079 -- essentially zero, the truth. Averaged over 200 independent pairs,
the mean absolute level correlation is 0.42 while the mean absolute difference correlation is 0.12: the spurious
effect is systematic. This computes both.

  --pair       one pair of independent walks: their level correlation vs their first-difference correlation
  --average    the mean absolute correlation over many independent pairs, levels vs differences
  --check      independent walks correlate spuriously in levels; differencing reveals no relationship

The seeds and sizes are the fixture; every correlation is computed. Stdlib only.
"""
import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "spurious.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def walk(seed, n):
    """A random walk: the running sum of n random +/-1 steps from the given seed."""
    r = random.Random(seed)
    w = [0.0]
    for _ in range(n):
        w.append(w[-1] + r.choice([-1, 1]))
    return w


def diffs(series):
    """First differences: the step-to-step changes, with the trend removed."""
    return [series[i + 1] - series[i] for i in range(len(series) - 1)]


def correlation(x, y):
    mx = sum(x) / len(x)
    my = sum(y) / len(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = (sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y)) ** 0.5
    return num / den if den else 0.0


def avg_abs_correlation(n, trials, on_diffs):
    """Mean absolute correlation over `trials` independent walk pairs; on_diffs uses first differences."""
    total = 0.0
    for i in range(trials):
        a, b = walk(2 * i, n), walk(2 * i + 1, n)
        if on_diffs:
            a, b = diffs(a), diffs(b)
        total += abs(correlation(a, b))
    return total / trials


# ----------------------------------------------------------------- printing

def pair_view(data):
    a, b = walk(data["seed_a"], data["n"]), walk(data["seed_b"], data["n"])
    print("PAIR — two independent random walks (seeds %d, %d)" % (data["seed_a"], data["seed_b"]))
    print("-" * 60)
    print("  correlation of LEVELS (the walk values):      %+.3f   (large -- spurious)" % correlation(a, b))
    print("  correlation of CHANGES (first differences):   %+.3f   (near zero -- the truth)" % correlation(diffs(a), diffs(b)))
    print("-" * 60)
    print("  the walks share nothing but a trend; only the levels correlate.")


def average_view(data):
    n, trials = data["n"], data["trials"]
    lv = avg_abs_correlation(n, trials, on_diffs=False)
    dv = avg_abs_correlation(n, trials, on_diffs=True)
    print("AVERAGE — mean |correlation| over %d independent walk pairs" % trials)
    print("-" * 60)
    print("  levels:        %.3f   (%.1fx larger -- systematic spurious correlation)" % (lv, lv / dv))
    print("  differences:   %.3f   (near zero -- no relationship, correctly)" % dv)
    print("-" * 60)
    print("  the spurious level correlation is not a fluke; differencing removes it every time.")


def check(data):
    print("SELF-TEST — independent walks correlate spuriously in levels; differencing reveals no relationship")
    print("-" * 104)
    sa, sb, n, trials = data["seed_a"], data["seed_b"], data["n"], data["trials"]
    a, b = walk(sa, n), walk(sb, n)
    cl = correlation(a, b)
    cd = correlation(diffs(a), diffs(b))

    levels_spurious = abs(cl) > 0.5
    print("  the pair's LEVEL correlation is large = %s (%+.3f)" % (levels_spurious, cl))

    diffs_near_zero = abs(cd) < 0.2
    print("  the pair's DIFFERENCE correlation is near zero = %s (%+.3f)" % (diffs_near_zero, cd))

    lv = avg_abs_correlation(n, trials, on_diffs=False)
    dv = avg_abs_correlation(n, trials, on_diffs=True)

    avg_levels_inflated = lv > 0.3
    print("  the average |level correlation| is inflated = %s (%.3f)" % (avg_levels_inflated, lv))

    avg_diffs_low = dv < 0.2
    print("  the average |difference correlation| is small = %s (%.3f)" % (avg_diffs_low, dv))

    differencing_removes_it = lv > 2 * dv
    print("  differencing more than halves the spurious correlation = %s (%.3f > 2*%.3f)" % (differencing_removes_it, lv, dv))

    ok = levels_spurious and diffs_near_zero and avg_levels_inflated and avg_diffs_low and differencing_removes_it
    print("-" * 104)
    print("SELF-TEST %s  levels_spurious=%s  diffs_near_zero=%s  avg_levels_inflated=%s  avg_diffs_low=%s  differencing_removes_it=%s"
          % ("PASS" if ok else "FAIL", levels_spurious, diffs_near_zero, avg_levels_inflated, avg_diffs_low, differencing_removes_it))
    return ok


def main():
    p = argparse.ArgumentParser(description="Two independent trending series correlate spuriously in levels; correlating first differences removes the trend and shows no relationship.")
    p.add_argument("--pair", action="store_true")
    p.add_argument("--average", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("seed_a=%d  seed_b=%d  n=%d  trials=%d  file=%s  (the walks are a fixture)"
          % (data["seed_a"], data["seed_b"], data["n"], data["trials"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.pair:
        pair_view(data)
    elif args.average:
        average_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
