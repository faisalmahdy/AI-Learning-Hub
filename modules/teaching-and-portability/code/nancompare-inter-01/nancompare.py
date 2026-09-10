"""Test for NaN with isnan, never with equality -- not-a-number does not equal itself, so every comparison-based operation silently breaks on it.

A missing or undefined numeric value often arrives as NaN -- the IEEE-754 float for 'not a number', produced by 0.0/0.0, the log of a negative, a failed parse, or a gap in a dataset. NaN has one property that violates the intuition every other value obeys: it does not equal itself. nan == nan is False; nan != nan is True; and every ordered comparison with it -- less-than, greater-than, and their or-equal forms -- is also False, because NaN is unordered with respect to everything, itself included. This is not a bug in the language; it is the standard, and it is deliberate (an undefined result should not compare equal to another undefined result). But it means any operation built on equality or ordering does the wrong thing the moment a NaN is present, and does it silently.

Four everyday operations break. Detecting the missing value by equality fails: a filter that keeps or drops elements by comparing them to a NaN sentinel never matches, because the comparison is always False, so the NaN slips through undetected. Sorting fails: sort and sorted rely on pairwise comparisons, and since every comparison with NaN is False, the 'sorted' list comes back in an order that is not actually sorted -- the NaN lands wherever the algorithm's comparisons happened to leave it, and elements around it can be out of order. Deduplication and membership tests fail for the same reason. And arithmetic propagates: any sum, mean, min, or max that includes a NaN returns NaN, so one missing value contaminates the entire aggregate.

The portable fix is to stop using equality and ordering to reason about NaN and use the purpose-built test instead: math.isnan(x), or the equivalent trick x != x, which is true for exactly one kind of value -- NaN -- precisely because NaN is the only value not equal to itself. Detect the NaNs explicitly, filter them out (or handle them as missing), and only then sort or aggregate the clean values. The rule is the same in every language with IEEE floats: never compare to NaN, test for it.

The rule: detect NaN with a dedicated isnan test (or x != x), never by equality or ordering, and remove or handle it before sorting or aggregating, because NaN does not equal itself and is unordered with everything -- so equality-based detection misses it, comparison-based sorting misplaces it, and any arithmetic including it returns NaN, each failing silently.

On this fixture the readings are 2, 3, missing, 1. Equality-based detection finds zero NaNs (it should find one); sorting returns [2, 3, nan, 1], leaving the 1 stranded after the 3 -- not ordered; the naive sum is NaN. Testing with isnan finds the one NaN, and the clean mean is (2+3+1)/3 = 2.0. This computes both.

  --naive    equality-based NaN detection, comparison-based sorting, and the contaminated sum -- all silently wrong
  --clean    isnan-based detection, the filtered clean values, and the correct mean
  --check    NaN breaks equality, ordering, and arithmetic; isnan detects it and cleaning restores a correct result

readings_raw is the fixture; every detection, sort, sum, and clean statistic is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "nancompare.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def readings(data):
    """Turn the raw list (null marks the missing value) into floats, with the gap as NaN."""
    return [float("nan") if x is None else float(x) for x in data["readings_raw"]]


def detect_by_equality(vals):
    """Naive: try to find the missing value by comparing each element to a NaN sentinel."""
    sentinel = float("nan")
    return [i for i, x in enumerate(vals) if x == sentinel]


def detect_by_isnan(vals):
    """Correct: test each element with math.isnan."""
    return [i for i, x in enumerate(vals) if math.isnan(x)]


def is_monotonic(vals):
    """Whether the list is actually non-decreasing (adjacent pairs in order)."""
    return all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1))


def clean(vals):
    """Drop the NaNs, keeping the real readings."""
    return [x for x in vals if not math.isnan(x)]


def mean(vals):
    return sum(vals) / len(vals)


def show(vals):
    return "[" + ", ".join("nan" if math.isnan(x) else ("%g" % x) for x in vals) + "]"


# ----------------------------------------------------------------- printing

def naive_view(data):
    vals = readings(data)
    print("NAIVE — equality detection, comparison sort, and the sum, all with NaN present")
    print("-" * 66)
    print("  readings           = %s" % show(vals))
    print("  nan == nan         = %s ; nan != nan = %s" % (float("nan") == float("nan"), float("nan") != float("nan")))
    print("  detect by equality = %s indices (x == nan never matches -- misses the gap)" % detect_by_equality(vals))
    srt = sorted(vals)
    print("  sorted(readings)   = %s  monotonic? %s" % (show(srt), is_monotonic(srt)))
    print("  sum(readings)      = %s (one NaN contaminates the whole aggregate)" % ("nan" if math.isnan(sum(vals)) else "%g" % sum(vals)))


def clean_view(data):
    vals = readings(data)
    idx = detect_by_isnan(vals)
    good = clean(vals)
    print("CLEAN — isnan detection, filtered values, correct mean")
    print("-" * 56)
    print("  detect by isnan = %s indices (finds the gap)" % idx)
    print("  x != x for each = %s (true only for NaN)" % [x != x for x in vals])
    print("  clean readings  = %s" % show(good))
    print("  mean(clean)     = %g = (%s)/%d" % (mean(good), "+".join("%g" % x for x in good), len(good)))


def check(data):
    print("SELF-TEST — NaN breaks equality, ordering, and arithmetic; isnan detects it and cleaning restores a correct result")
    print("-" * 116)
    vals = readings(data)

    nan_not_equal_itself = float("nan") != float("nan")
    print("  NaN does not equal itself (nan != nan) = %s" % nan_not_equal_itself)

    equality_misses_nan = len(detect_by_equality(vals)) == 0
    print("  equality-based detection misses the NaN = %s (found %d, there is 1)" % (equality_misses_nan, len(detect_by_equality(vals))))

    isnan_finds_one = len(detect_by_isnan(vals)) == 1
    print("  isnan-based detection finds exactly the one NaN = %s (index %s)" % (isnan_finds_one, detect_by_isnan(vals)))

    sort_not_monotonic = not is_monotonic(sorted(vals))
    print("  comparison-based sort is NOT actually ordered = %s (%s)" % (sort_not_monotonic, show(sorted(vals))))

    sum_contaminated = math.isnan(sum(vals))
    print("  a sum including the NaN is NaN = %s (one gap contaminates the aggregate)" % sum_contaminated)

    xnex_only_nan = [x != x for x in vals] == [math.isnan(x) for x in vals]
    print("  the x != x trick flags exactly the NaNs = %s" % xnex_only_nan)

    clean_mean_correct = abs(mean(clean(vals)) - 2.0) < 1e-9
    print("  cleaning then averaging gives the correct mean = %s (%g == 2.0)" % (clean_mean_correct, mean(clean(vals))))

    ok = nan_not_equal_itself and equality_misses_nan and isnan_finds_one and sort_not_monotonic and sum_contaminated and xnex_only_nan and clean_mean_correct
    print("-" * 116)
    print("SELF-TEST %s  nan_not_equal_itself=%s  equality_misses_nan=%s  isnan_finds_one=%s  sort_not_monotonic=%s  sum_contaminated=%s  xnex_only_nan=%s  clean_mean_correct=%s"
          % ("PASS" if ok else "FAIL", nan_not_equal_itself, equality_misses_nan, isnan_finds_one, sort_not_monotonic, sum_contaminated, xnex_only_nan, clean_mean_correct))
    return ok


def main():
    p = argparse.ArgumentParser(description="NaN comparison: detect NaN with a dedicated isnan test (or x != x), never by equality or ordering, and remove or handle it before sorting or aggregating, because NaN does not equal itself and is unordered with everything -- so equality-based detection misses it, comparison-based sorting misplaces it, and any arithmetic including it returns NaN, each failing silently.")
    p.add_argument("--naive", action="store_true")
    p.add_argument("--clean", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("readings_raw=%s  file=%s  (the readings, with null for the missing value, are a fixture)"
          % (data["readings_raw"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.naive:
        naive_view(data)
    elif args.clean:
        clean_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
