"""Test the difference, not whether the two error bars overlap, or you call a real win a tie.

The tempting shortcut when comparing two systems is visual: draw each one's confidence interval and check whether
they overlap. If the bars overlap, call it a tie; if they are clearly apart, call it a win. It feels rigorous --
you did use the intervals -- but it is the wrong test, and it is biased toward declaring no difference. The
significance of a difference is a property of the DIFFERENCE, and the difference has its own standard error that
is SMALLER than the two individual error bars suggest, because independent errors add in quadrature: the standard
error of A minus B is sqrt(SE_a^2 + SE_b^2), not SE_a + SE_b. The overlap test implicitly uses the larger,
linear sum, so it demands the bars be farther apart than significance actually requires, and it misses real wins
that sit in the gap between "bars overlap" and "difference significant".

The correct test computes the difference of the means and divides by its own standard error, sqrt(SE_a^2 +
SE_b^2). If that ratio exceeds the 95% multiplier -- equivalently, if the difference's confidence interval
excludes zero -- the difference is significant, whether or not the two original intervals happened to overlap.
The two questions are simply different: "do the intervals overlap" asks about each estimate separately; "is the
difference significant" asks about the gap directly, and only the second is the test you meant to run.

On this fixture system A scores 0.80 and B scores 0.87, each with a standard error of 0.02. Their 95% intervals
are [0.761, 0.839] and [0.831, 0.909] -- they OVERLAP between 0.831 and 0.839, so the eyeball test says 'tie'.
But the difference is 0.07 with a standard error of 0.0283, which is 2.47 standard errors from zero, and its
interval [0.015, 0.125] excludes zero: the difference IS significant. This computes both.

  --intervals  each system's 95% interval and whether they overlap
  --difference the difference, its standard error, its z, and its interval against zero
  --check      the intervals overlap yet the difference is significant, so the overlap test is wrong here

The means, standard errors, and multiplier are the fixture; every statistic is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "overlap.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def interval(system, z):
    """A system's confidence interval: mean +/- z*se."""
    return system["mean"] - z * system["se"], system["mean"] + z * system["se"]


def intervals_overlap(a, b, z):
    """Do the two confidence intervals share any range?"""
    lo_a, hi_a = interval(a, z)
    lo_b, hi_b = interval(b, z)
    return hi_a >= lo_b and hi_b >= lo_a


def diff_se(a, b):
    """Standard error of the difference: independent errors add in quadrature."""
    return math.sqrt(a["se"] ** 2 + b["se"] ** 2)


def diff_significant(a, b, z):
    """Is the difference significant? Its interval excludes zero iff |diff| > z * diff_se."""
    return abs(b["mean"] - a["mean"]) > z * diff_se(a, b)


# ----------------------------------------------------------------- printing

def intervals_view(data):
    a, b, z = data["system_a"], data["system_b"], data["z"]
    la, ha = interval(a, z)
    lb, hb = interval(b, z)
    print("INTERVALS — each system's 95%% interval (mean +/- %.2f*SE)" % z)
    print("-" * 60)
    print("  A: mean %.2f  SE %.2f  ->  [%.3f, %.3f]" % (a["mean"], a["se"], la, ha))
    print("  B: mean %.2f  SE %.2f  ->  [%.3f, %.3f]" % (b["mean"], b["se"], lb, hb))
    print("  intervals overlap: %s" % intervals_overlap(a, b, z))
    print("-" * 60)
    print("  the bars overlap, so the eyeball test would call this a tie.")


def difference_view(data):
    a, b, z = data["system_a"], data["system_b"], data["z"]
    d = b["mean"] - a["mean"]
    sd = diff_se(a, b)
    print("DIFFERENCE — the test that actually answers the question")
    print("-" * 60)
    print("  difference B - A:            %.3f" % d)
    print("  SE of difference sqrt(a^2+b^2): %.4f   (< SE_a + SE_b = %.3f)" % (sd, a["se"] + b["se"]))
    print("  difference in SEs:           %.2f   (%s 95%% cutoff %.2f)" % (d / sd, ">" if d / sd > z else "<=", z))
    print("  difference interval:         [%.3f, %.3f]  excludes 0: %s" % (d - z * sd, d + z * sd, (d - z * sd) > 0))
    print("-" * 60)
    print("  the difference is %.2f SEs from zero -- significant -- despite the overlapping bars." % (d / sd))


def check(data):
    print("SELF-TEST — the intervals overlap yet the difference is significant, so the overlap test is wrong here")
    print("-" * 104)
    a, b, z = data["system_a"], data["system_b"], data["z"]

    overlap = intervals_overlap(a, b, z)
    print("  the two 95%% confidence intervals overlap = %s" % overlap)

    significant = diff_significant(a, b, z)
    print("  the difference is significant (its interval excludes zero) = %s" % significant)

    overlap_test_disagrees = overlap and significant
    print("  the overlap test and the difference test disagree = %s (overlap says tie, difference says win)" % overlap_test_disagrees)

    diff_se_smaller = diff_se(a, b) < a["se"] + b["se"]
    print("  the difference's SE is smaller than the summed margins = %s (%.4f < %.3f)" % (diff_se_smaller, diff_se(a, b), a["se"] + b["se"]))

    d_sigmas = abs(b["mean"] - a["mean"]) / diff_se(a, b)
    difference_clears_cutoff = d_sigmas > z
    print("  the difference is more than %.2f SEs from zero = %s (%.2f)" % (z, difference_clears_cutoff, d_sigmas))

    ok = overlap and significant and overlap_test_disagrees and diff_se_smaller and difference_clears_cutoff
    print("-" * 104)
    print("SELF-TEST %s  overlap=%s  significant=%s  overlap_test_disagrees=%s  diff_se_smaller=%s  difference_clears_cutoff=%s"
          % ("PASS" if ok else "FAIL", overlap, significant, overlap_test_disagrees, diff_se_smaller, difference_clears_cutoff))
    return ok


def main():
    p = argparse.ArgumentParser(description="Overlapping confidence intervals do not mean no significant difference; test the difference, whose SE adds in quadrature.")
    p.add_argument("--intervals", action="store_true")
    p.add_argument("--difference", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    a, b = data["system_a"], data["system_b"]
    print("A(mean %.2f, SE %.2f)  B(mean %.2f, SE %.2f)  z=%.2f  file=%s  (the scores are a fixture)"
          % (a["mean"], a["se"], b["mean"], b["se"], data["z"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.intervals:
        intervals_view(data)
    elif args.difference:
        difference_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
