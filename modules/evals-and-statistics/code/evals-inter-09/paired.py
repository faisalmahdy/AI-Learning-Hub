"""Compare two systems on the SAME cases with a paired test -- an unpaired test drowns the signal in case difficulty.

You ran systems A and B on the same twelve eval cases. On every single case B scored a little higher
than A -- two to four points, every time. Yet the cases themselves swing wildly: some are easy and
everyone scores in the nineties, some are brutal and everyone scores in the forties. Now you ask the
statistics question: is B really better, or did it get lucky?

There are two ways to run the test, and they disagree. The unpaired (two-sample) test throws A's
twelve scores in one pile and B's in another and compares the piles. But each pile has enormous
spread -- because it mixes easy cases and hard cases -- and that spread swamps the small, steady gap
between the systems. The unpaired test shrugs: not significant, could be noise. The paired test looks
at the twelve DIFFERENCES instead, one per case, B minus A. Case difficulty cancels out of a
difference -- a hard case is hard for both -- so the differences are tiny and consistent, and the
paired test sees the gap clearly: B wins, decisively.

Same numbers, two tests, opposite verdicts. The case-to-case variance that the paired test cancels is
exactly what the unpaired test mistakes for uncertainty about which system is better. This computes
both tests and their 95% confidence intervals for the A-to-B difference and shows one interval
crossing zero while the other does not.

  --scores     the per-case scores for A and B, and each case's B-minus-A difference
  --tests      the unpaired vs paired 95% interval for the mean difference
  --check      the unpaired interval includes 0 (inconclusive); the paired interval excludes it (B wins)

The per-case scores are the fixture; every mean, variance, and interval is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "scores.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mean(xs):
    return sum(xs) / len(xs)


def variance(xs):
    """Sample variance (n-1 denominator)."""
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


# ------------------------------------------------------------- the two tests

def unpaired_interval(a, b, t_crit):
    """Two-sample 95% interval for mean(B) - mean(A): treats A and B as independent piles."""
    diff = mean(b) - mean(a)
    se = (variance(a) / len(a) + variance(b) / len(b)) ** 0.5
    half = t_crit * se
    return diff, se, (round(diff - half, 3), round(diff + half, 3))


def paired_interval(a, b, t_crit):
    """Paired 95% interval for the mean of the per-case differences B - A: case difficulty cancels."""
    diffs = [bi - ai for ai, bi in zip(a, b)]
    d = mean(diffs)
    se = (variance(diffs) / len(diffs)) ** 0.5
    half = t_crit * se
    return d, se, (round(d - half, 3), round(d + half, 3))


def includes_zero(interval):
    return interval[0] <= 0 <= interval[1]


# ----------------------------------------------------------------- printing

def scores_view(data):
    cases = data["cases"]
    print("SCORES — A and B on the same cases, with the per-case difference B-A")
    print("-" * 52)
    print("  case    A     B    B-A")
    for c in cases:
        print("  %s  %3d   %3d   %+d" % (c["case"], c["A"], c["B"], c["B"] - c["A"]))
    print("-" * 52)
    a = [c["A"] for c in cases]
    b = [c["B"] for c in cases]
    print("  mean A = %.2f   mean B = %.2f   mean diff = %+.2f" % (mean(a), mean(b), mean(b) - mean(a)))
    print("  B beats A on %d of %d cases; the gap is small but never reverses."
          % (sum(1 for c in cases if c["B"] > c["A"]), len(cases)))


def tests_view(data):
    cases = data["cases"]
    a = [c["A"] for c in cases]
    b = [c["B"] for c in cases]
    tc = data["t_crit_95"]
    du, seu, iu = unpaired_interval(a, b, tc["df22_unpaired"])
    dp, sep, ip = paired_interval(a, b, tc["df11_paired"])
    print("TESTS — 95% interval for the mean B-A difference, two ways")
    print("-" * 62)
    print("  unpaired (two-sample): diff %+.2f  SE %.2f  95%% CI %s" % (du, seu, iu))
    print("  paired   (per case):   diff %+.2f  SE %.2f  95%% CI %s" % (dp, sep, ip))
    print("-" * 62)
    print("  the unpaired interval straddles 0; the paired one sits entirely above it.")


def check(data):
    print("SELF-TEST — the unpaired interval includes 0 (inconclusive); the paired one excludes it (B wins)")
    print("-" * 78)
    cases = data["cases"]
    a = [c["A"] for c in cases]
    b = [c["B"] for c in cases]
    tc = data["t_crit_95"]

    du, seu, iu = unpaired_interval(a, b, tc["df22_unpaired"])
    dp, sep, ip = paired_interval(a, b, tc["df11_paired"])

    same_point_estimate = abs(du - dp) < 1e-9
    print("  both tests estimate the same mean difference = %s (%.3f)" % (same_point_estimate, du))

    unpaired_inconclusive = includes_zero(iu)
    print("  the unpaired interval includes 0 (calls it a wash) = %s (%s)" % (unpaired_inconclusive, iu))

    paired_significant = not includes_zero(ip) and ip[0] > 0
    print("  the paired interval excludes 0 above (B wins) = %s (%s)" % (paired_significant, ip))

    variance_cancels = sep < seu / 5
    print("  pairing shrinks the standard error = %s (paired SE %.2f vs unpaired %.2f)" % (variance_cancels, sep, seu))

    ok = same_point_estimate and unpaired_inconclusive and paired_significant and variance_cancels
    print("-" * 78)
    print("SELF-TEST %s  same_point_estimate=%s  unpaired_inconclusive=%s  paired_significant=%s  variance_cancels=%s"
          % ("PASS" if ok else "FAIL", same_point_estimate, unpaired_inconclusive, paired_significant, variance_cancels))
    return ok


def main():
    p = argparse.ArgumentParser(description="Compare two systems on the same cases with a paired test.")
    p.add_argument("--scores", action="store_true")
    p.add_argument("--tests", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("cases=%d  file=%s  (the per-case scores are a fixture; every statistic is computed)"
          % (len(data["cases"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.scores:
        scores_view(data)
    elif args.tests:
        tests_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
