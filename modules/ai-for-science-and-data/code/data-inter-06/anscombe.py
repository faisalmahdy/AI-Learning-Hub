#!/usr/bin/env python3
"""Anscombe's quartet: four datasets with identical statistics and opposite shapes.

Four datasets. Same mean of x, same mean of y, same variance, same correlation, same
least-squares regression line -- agreeing to two decimal places. And when you plot them,
one is a clean line, one is a parabola, one is a line with a wild outlier, and one is a
vertical stack of points whose entire correlation comes from a single far-out point. This
is Anscombe's 1973 demonstration that summary statistics do not describe a dataset; they
compress it, and compression discards exactly the structure -- curvature, outliers,
leverage -- that decides whether a linear fit means anything.

The failure this guards against is trusting the numbers without seeing the shape. All four
quartet members would pass a check that says 'strong linear correlation, slope 0.5', and a
model or decision built on that would be right for d1, fooled by a curve in d2, dragged by
an outlier in d3, and entirely fabricated in d4. This computes the shared statistics and a
shape diagnostic that tells the four apart.

  --stats       mean, variance, correlation, and regression line for all four -- watch them match
  --shape       a shape diagnostic (max residual from the shared line) that separates them
  --check       the summary stats are identical; the shapes are not

Stdlib only. Deterministic. The data is the published Anscombe quartet.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "anscombe.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))["datasets"]


# ------------------------------------------------------------- statistics

def mean(xs):
    return sum(xs) / len(xs)


def variance(xs):
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / len(xs)


def correlation(xs, ys):
    mx, my = mean(xs), mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return cov / (sx * sy)


def regression(xs, ys):
    """Least-squares slope and intercept for y = intercept + slope * x."""
    mx, my = mean(xs), mean(ys)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return slope, my - slope * mx


# ------------------------------------------------------------- shape diagnostic

def max_abs_residual(xs, ys):
    """The largest deviation of a point from the fitted line -- big for outliers/curves."""
    slope, intercept = regression(xs, ys)
    return max(abs(y - (intercept + slope * x)) for x, y in zip(xs, ys))


def distinct_x(xs):
    """How many distinct x values -- 2 for d4 (a vertical line plus one point)."""
    return len(set(xs))


# ----------------------------------------------------------------- printing

def stats_view(data):
    print("STATS — the four datasets share their summary statistics (2 decimals)")
    print("-" * 66)
    print("  set  mean_x  mean_y  var_x  var_y  corr   line")
    for name in sorted(data):
        xs, ys = data[name]["x"], data[name]["y"]
        s, i = regression(xs, ys)
        print("  %-4s %6.2f  %6.2f  %5.2f  %5.2f  %.3f  y=%.2f+%.2fx"
              % (name, mean(xs), mean(ys), variance(xs), variance(ys), correlation(xs, ys), i, s))
    print("-" * 66)
    print("  every column is identical to two decimals -- the numbers say the sets are the same.")


def shape_view(data):
    print("SHAPE — diagnostics that tell the identical-looking datasets apart")
    print("-" * 66)
    print("  set  max_residual  distinct_x  what it really is")
    kinds = {"d1": "clean linear", "d2": "a parabola (curved)", "d3": "linear + one outlier",
             "d4": "vertical line + one leverage point"}
    for name in sorted(data):
        xs, ys = data[name]["x"], data[name]["y"]
        print("  %-4s %11.2f  %10d  %s" % (name, max_abs_residual(xs, ys), distinct_x(xs), kinds[name]))
    print("-" * 66)
    print("  same regression line, wildly different residual shapes -- only a plot shows it.")


def check(data):
    print("SELF-TEST — the summary statistics are identical; the shapes are not")
    print("-" * 66)
    names = sorted(data)

    def stat_tuple(name):
        xs, ys = data[name]["x"], data[name]["y"]
        s, i = regression(xs, ys)
        return (round(mean(xs), 2), round(mean(ys), 2), round(variance(xs), 2),
                round(variance(ys), 2), round(correlation(xs, ys), 2), round(s, 2), round(i, 2))

    tuples = [stat_tuple(n) for n in names]
    stats_identical = all(t == tuples[0] for t in tuples)
    print("  all four share (mean_x, mean_y, var_x, var_y, corr, slope, intercept) = %s" % stats_identical)
    print("     %s" % str(tuples[0]))

    strong_corr = all(round(correlation(data[n]["x"], data[n]["y"]), 2) == 0.82 for n in names)
    print("  all four report the same strong correlation (0.82) = %s" % strong_corr)

    residuals = [round(max_abs_residual(data[n]["x"], data[n]["y"]), 2) for n in names]
    shapes_differ = len(set(residuals)) > 1
    print("  but the max-residual shape diagnostic differs across them = %s (%s)" % (shapes_differ, residuals))

    d4_degenerate = distinct_x(data["d4"]["x"]) == 2
    print("  d4 is a degenerate shape (only 2 distinct x) hidden by the stats = %s" % d4_degenerate)

    ok = stats_identical and strong_corr and shapes_differ and d4_degenerate
    print("-" * 66)
    print("SELF-TEST %s  stats_identical=%s  strong_corr=%s  shapes_differ=%s  d4_degenerate=%s"
          % ("PASS" if ok else "FAIL", stats_identical, strong_corr, shapes_differ, d4_degenerate))
    return ok


def main():
    p = argparse.ArgumentParser(description="Anscombe's quartet: identical stats, different shapes.")
    p.add_argument("--stats", action="store_true")
    p.add_argument("--shape", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("datasets=%d  file=%s  (the published Anscombe quartet)" % (len(data), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.stats:
        stats_view(data)
    elif args.shape:
        shape_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
