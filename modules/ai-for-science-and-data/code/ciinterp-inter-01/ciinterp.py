"""A 95% confidence interval is a statement about the procedure, not about the one interval you computed -- about 95% of the intervals the method produces across repeated experiments contain the true value, but any single computed interval either contains the true value or does not, with no probability in between.

A confidence interval is the sample mean plus or minus z times the standard error. The natural reading of '95% confidence interval' is 'there is a 95% probability the true value is inside this interval,' and it is wrong. Once the interval is computed it is a fixed range, and the true value is a fixed number: the true value is inside it or it is not. There is no 95% about a fixed range and a fixed number -- the probability is 1 or 0, you just do not know which.

The 95% lives one level up, in the method. If you ran the experiment many times, each run drawing a different sample and producing a different interval, about 95% of those intervals would cover the true value and about 5% would miss. The confidence is the coverage rate of the procedure over repetitions, not a credence about the particular interval in front of you.

The distinction has teeth when an interval misses. A miss is not a low-probability event within that interval; it is an interval that flatly does not contain the truth. Saying 'there is a 95% chance the truth is in here' about a missing interval is not merely loose -- it is false, because the truth is entirely outside it.

On this fixture the true value is 100, each experiment has a standard error of 1.0, and the interval is the mean plus or minus 1.96. Across twenty experiments, nineteen intervals contain 100 -- 95% coverage -- and one, from a sample mean of 102.3, is 100.34 to 104.26, which excludes 100 completely. The 95% describes the nineteen-of-twenty, not any single interval. This computes it.

  --intervals  each experiment's interval and whether it contains the true value
  --coverage   the fraction of intervals that contain the truth, and the interval that misses
  --check      about 95% of the intervals contain the true value, at least one misses entirely, and the missing interval definitely excludes the truth rather than containing it with some probability

the true value, standard error, z, and the sample means are the fixture; each interval, its containment, and the coverage are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "ciinterp.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def interval(mean, se, z):
    """The confidence interval for one experiment: mean plus or minus z standard errors."""
    half = z * se
    return (mean - half, mean + half)


def contains(iv, value):
    """Whether a computed interval contains the value -- a yes/no fact, not a probability."""
    lo, hi = iv
    return lo <= value <= hi


def coverage(sample_means, se, z, true_value):
    """The fraction of the produced intervals that contain the true value: the procedure's coverage."""
    hits = sum(1 for m in sample_means if contains(interval(m, se, z), true_value))
    return hits / len(sample_means)


# ----------------------------------------------------------------- printing

def intervals_view(d):
    tv, se, z = d["true_value"], d["standard_error"], d["z"]
    print("INTERVALS — each experiment's 95%% interval (true value = %d)" % tv)
    print("-" * 64)
    for i, m in enumerate(d["sample_means"], start=1):
        lo, hi = interval(m, se, z)
        ok = contains((lo, hi), tv)
        print("  exp %2d: mean %.1f  -> [%.2f, %.2f]  contains %d? %s" % (i, m, lo, hi, tv, ok))
    print("-" * 64)
    print("  each interval either contains the true value or does not -- no 95%% about any one")


def coverage_view(d):
    tv, se, z = d["true_value"], d["standard_error"], d["z"]
    cov = coverage(d["sample_means"], se, z, tv)
    misses = [m for m in d["sample_means"] if not contains(interval(m, se, z), tv)]
    print("COVERAGE — across %d experiments" % len(d["sample_means"]))
    print("-" * 64)
    print("  intervals containing the truth: %d of %d  (%.0f%%)" % (round(cov * len(d["sample_means"])), len(d["sample_means"]), cov * 100))
    for m in misses:
        lo, hi = interval(m, se, z)
        print("  MISS: mean %.1f -> [%.2f, %.2f] does NOT contain %d" % (m, lo, hi, tv))
    print("-" * 64)
    print("  the 95% is this coverage across intervals, not a probability inside the missing one")


def check(d):
    print("SELF-TEST — about 95% of intervals contain the true value, at least one misses entirely, and the missing interval definitely excludes the truth")
    print("-" * 112)
    tv, se, z = d["true_value"], d["standard_error"], d["z"]
    means = d["sample_means"]

    cov = coverage(means, se, z, tv)
    coverage_near_95 = abs(cov - 0.95) < 1e-9
    print("  coverage across the intervals is 95%% = %s (%.2f)" % (coverage_near_95, cov))

    intervals = [interval(m, se, z) for m in means]
    containments = [contains(iv, tv) for iv in intervals]
    one_misses = not all(containments)
    print("  at least one interval does not contain the true value = %s (%d miss)" % (one_misses, containments.count(False)))

    missing = [iv for iv, c in zip(intervals, containments) if not c][0]
    miss_definitely_excludes = not contains(missing, tv)
    print("  the missing interval definitely excludes the truth (not 95%% inside) = %s (%s, %d outside)" % (miss_definitely_excludes, ("[%.2f, %.2f]" % missing), tv))

    each_binary = all(c in (True, False) for c in containments)
    print("  each interval's containment is a yes/no fact, not a probability = %s" % each_binary)

    ok = (coverage_near_95 and one_misses and miss_definitely_excludes and each_binary)
    print("-" * 112)
    print("SELF-TEST %s  coverage_near_95=%s  one_misses=%s  miss_definitely_excludes=%s  each_binary=%s"
          % ("PASS" if ok else "FAIL", coverage_near_95, one_misses, miss_definitely_excludes, each_binary))
    return ok


def main():
    p = argparse.ArgumentParser(description="Confidence interval interpretation: a 95% confidence interval is a property of the procedure -- about 95% of the intervals it produces across repeated experiments contain the true value -- not a probability about any single computed interval, which either contains the true value or does not; when an interval misses, the truth is definitely outside it, so 'a 95% chance the truth is inside' is false for that interval, not merely imprecise.")
    p.add_argument("--intervals", action="store_true")
    p.add_argument("--coverage", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    d = load()
    print("true_value=%d  standard_error=%.1f  z=%.2f  experiments=%d  file=%s"
          % (d["true_value"], d["standard_error"], d["z"], len(d["sample_means"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(d) else 1
    if args.intervals:
        intervals_view(d)
    elif args.coverage:
        coverage_view(d)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
