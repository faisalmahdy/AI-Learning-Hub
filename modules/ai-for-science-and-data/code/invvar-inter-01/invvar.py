"""Combine measurements by inverse-variance weighting, not a simple average -- a simple average of a precise measurement and a noisy one has a larger variance than the precise measurement alone, so averaging in the bad data degraded your best data.

When several independent measurements estimate one true value, each with its own uncertainty, the instinct is to average them: add the values, divide by the count. That gives every measurement the same say, which is only right when they are equally precise. When they are not, the simple average treats a measurement good to a tenth of a unit and one good to five units as equals, so the noisy one drags the estimate around.

The cost is measurable in the variance. For n independent measurements the variance of the simple average is the sum of their variances over n squared, and when one measurement is far noisier, that sum is dominated by the noisy one. The consequence is stark: a simple average of a precise measurement and a noisy one has a larger variance than the precise measurement by itself. You had a good number, you averaged in a bad one, and you ended up less certain than before.

The minimum-variance unbiased combination weights each measurement by one over its variance -- inverse-variance, or precision, weighting. The precise measurement, with the small variance, gets a large weight; the noisy one gets a small weight; and the combined variance is one over the sum of the inverse variances, which is smaller than every single measurement's variance, including the best one. Combining now helps instead of hurting, because the combination respects how much each measurement is worth.

On this fixture the true value is 100. The precise measurement reads 98 with sigma 1, the noisy one reads 110 with sigma 5. The simple average is 104 with a variance worse than the precise measurement's; the inverse-variance-weighted estimate is about 98.5 with a variance below the precise measurement's, and it lands closer to the truth. This computes both.

  --simple    the simple average: its estimate and variance, worse than the precise measurement alone
  --weighted  the inverse-variance-weighted estimate: its weights, estimate, and variance, better than any single one
  --check     the simple average is less precise than the best single measurement while the weighted estimate is more precise, and the weights favor the precise measurement

true_value and the measurements are the fixture; the two estimates, their variances, and the weights are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "invvar.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def simple_estimate(measurements):
    """The plain average and its variance: sum of variances over n squared (every measurement weighted equally)."""
    n = len(measurements)
    mean = sum(m["value"] for m in measurements) / n
    variance = sum(m["sigma"] ** 2 for m in measurements) / n ** 2
    return {"mean": mean, "variance": variance}


def inverse_variance_weights(measurements):
    """Each measurement's weight is one over its variance, normalized -- precision, not headcount."""
    raw = [1.0 / m["sigma"] ** 2 for m in measurements]
    total = sum(raw)
    return [w / total for w in raw]


def weighted_estimate(measurements):
    """The inverse-variance-weighted mean and its variance: 1 / sum of inverse variances."""
    inv = [1.0 / m["sigma"] ** 2 for m in measurements]
    mean = sum(m["value"] * w for m, w in zip(measurements, inv)) / sum(inv)
    variance = 1.0 / sum(inv)
    return {"mean": mean, "variance": variance}


def best_single_variance(measurements):
    """The variance of the single most precise measurement -- the bar a combination should beat."""
    return min(m["sigma"] ** 2 for m in measurements)


# ----------------------------------------------------------------- printing

def _sd(v):
    return v ** 0.5


def simple_view(data):
    ms = data["measurements"]
    s = simple_estimate(ms)
    best = best_single_variance(ms)
    print("SIMPLE — the plain average, every measurement weighted equally")
    print("-" * 64)
    for m in ms:
        print("  %-8s = %.1f  (sigma %.1f)" % (m["name"], m["value"], m["sigma"]))
    print("  simple average = %.4f   variance %.4f (sigma %.4f)" % (s["mean"], s["variance"], _sd(s["variance"])))
    print("  best single measurement variance %.4f (sigma %.4f)" % (best, _sd(best)))
    print("-" * 64)
    print("  the average is LESS precise than the precise measurement alone -- the noisy one dragged it")


def weighted_view(data):
    ms = data["measurements"]
    w = inverse_variance_weights(ms)
    e = weighted_estimate(ms)
    best = best_single_variance(ms)
    print("WEIGHTED — inverse-variance (precision) weighting")
    print("-" * 64)
    for m, wi in zip(ms, w):
        print("  %-8s weight %.3f  (sigma %.1f)" % (m["name"], wi, m["sigma"]))
    print("  weighted estimate = %.4f   variance %.4f (sigma %.4f)" % (e["mean"], e["variance"], _sd(e["variance"])))
    print("  best single measurement variance %.4f (sigma %.4f)" % (best, _sd(best)))
    print("-" * 64)
    print("  the estimate is MORE precise than any single measurement, and closer to the truth")


def check(data):
    print("SELF-TEST — the simple average is less precise than the best single measurement while the weighted estimate is more precise, and the weights favor the precise measurement")
    print("-" * 112)
    ms = data["measurements"]
    truth = data["true_value"]
    simple = simple_estimate(ms)
    weighted = weighted_estimate(ms)
    best = best_single_variance(ms)
    weights = inverse_variance_weights(ms)

    simple_worse_than_best = simple["variance"] > best
    print("  the simple average is LESS precise than the best single measurement = %s (var %.4f > %.4f)" % (simple_worse_than_best, simple["variance"], best))

    weighted_better_than_best = weighted["variance"] < best
    print("  the weighted estimate is MORE precise than the best single measurement = %s (var %.4f < %.4f)" % (weighted_better_than_best, weighted["variance"], best))

    weighted_beats_simple = weighted["variance"] < simple["variance"]
    print("  the weighted estimate is more precise than the simple average = %s (%.4f < %.4f)" % (weighted_beats_simple, weighted["variance"], simple["variance"]))

    precise_gets_more_weight = weights[0] > weights[1]
    print("  the precise measurement gets more weight than the noisy one = %s (%.3f vs %.3f)" % (precise_gets_more_weight, weights[0], weights[1]))

    weighted_closer_to_truth = abs(weighted["mean"] - truth) < abs(simple["mean"] - truth)
    print("  the weighted estimate lands closer to the truth = %s (|%.2f-%g|<|%.2f-%g|)" % (weighted_closer_to_truth, weighted["mean"], truth, simple["mean"], truth))

    ok = (simple_worse_than_best and weighted_better_than_best and weighted_beats_simple
          and precise_gets_more_weight and weighted_closer_to_truth)
    print("-" * 112)
    print("SELF-TEST %s  simple_worse_than_best=%s  weighted_better_than_best=%s  weighted_beats_simple=%s  precise_gets_more_weight=%s  weighted_closer_to_truth=%s"
          % ("PASS" if ok else "FAIL", simple_worse_than_best, weighted_better_than_best, weighted_beats_simple,
             precise_gets_more_weight, weighted_closer_to_truth))
    return ok


def main():
    p = argparse.ArgumentParser(description="Inverse-variance weighting: combine independent measurements of one quantity by weighting each by one over its variance, not by a simple average, because a simple average treats a precise and a noisy measurement equally -- so it can be less precise than the precise measurement alone, while inverse-variance weighting gives a combined variance smaller than any single measurement.")
    p.add_argument("--simple", action="store_true")
    p.add_argument("--weighted", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("true_value=%g  measurements=%s  file=%s  (these are a fixture)"
          % (data["true_value"], [(m["name"], m["value"], m["sigma"]) for m in data["measurements"]], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.simple:
        simple_view(data)
    elif args.weighted:
        weighted_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
