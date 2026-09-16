"""Keep a continuous predictor continuous -- don't split it into high/low -- because dichotomizing throws away the within-group variation, so the association measured on the binary version is weaker and lower-powered than on the original.

It is tempting to turn a continuous predictor into two groups: split at the median, compare 'high' to 'low', and report a clean two-group difference. The appeal is simplicity -- a t-test between two groups reads more easily than a regression coefficient on a continuous scale. But the simplicity is bought by destroying information, and the information destroyed is signal.

A continuous variable distinguishes every value from every other. Dichotomizing collapses each half to a single level, so a value just above the median and a value far above it become the same 'high', and the outcome's dependence on how far above is erased. Whatever part of the association lived in those within-group differences is simply gone from the binary variable, and the measured correlation shrinks accordingly.

The relationship does not vanish -- it is real and still detectable -- it is attenuated. The dichotomized correlation is systematically smaller than the continuous one, and in a hypothesis test that shows up as reduced power: you need a larger sample to reach the same significance, or you miss a real effect you would have caught on the continuous scale. Dichotomizing a predictor is often described as throwing away roughly a third of your data, and that is not far off.

What separates this from other attenuation is that it is a deliberate choice, not a limitation imposed on you. Range restriction is a sampling constraint; measurement error is unavoidable noise; but dichotomizing is a decision the analyst makes, usually for a readability that is not worth the power. The fix is simply not to do it: keep the variable continuous and model it as such.

The rule: keep a continuous predictor continuous rather than splitting it into high/low, because dichotomizing discards the within-group variation and attenuates the association -- lowering the correlation and the statistical power -- for a simplicity that is not worth the lost signal.

On this fixture x and y are perfectly correlated (r = 1.0). Splitting x at its median into a 0/1 variable drops the correlation with y to about 0.87 -- the relationship survives but is measurably weaker, purely from the information the split threw away. This computes both.

  --split    the continuous x, its median, and the 0/1 dichotomized version
  --corr     the correlation of continuous x with y vs the dichotomized version with y
  --check    dichotomizing lowers the correlation with the outcome; the continuous variable keeps the full signal

x and y are the fixture; the median split and the two correlations are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "dichotomize.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def median(vals):
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    return (s[mid] + s[mid - 1]) / 2 if n % 2 == 0 else s[mid]


def dichotomize(vals, cut):
    """Collapse each value to 1 if above the cut, else 0 -- the median split."""
    return [1 if v > cut else 0 for v in vals]


def correlation(a, b):
    """Pearson correlation between two equal-length lists."""
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    return cov / (va ** 0.5 * vb ** 0.5)


# ----------------------------------------------------------------- printing

def split_view(data):
    x = data["x"]
    cut = median(x)
    b = dichotomize(x, cut)
    print("SPLIT — the continuous predictor and its median dichotomization")
    print("-" * 52)
    print("  continuous x: %s" % x)
    print("  median cut:   %s" % cut)
    print("  dichotomized: %s  (1 if above the median)" % b)
    print("-" * 52)
    print("  every value within a half collapses to the same level")


def corr_view(data):
    x, y = data["x"], data["y"]
    b = dichotomize(x, median(x))
    print("CORR — correlation with the outcome y")
    print("-" * 46)
    print("  continuous x  vs y:  r = %.3f" % correlation(x, y))
    print("  dichotomized  vs y:  r = %.3f" % correlation(b, y))
    print("-" * 46)
    print("  the split lowers the correlation -- attenuated, not gone")


def check(data):
    print("SELF-TEST — dichotomizing lowers the correlation with the outcome; the continuous variable keeps the full signal")
    print("-" * 116)
    x, y = data["x"], data["y"]
    cut = median(x)
    b = dichotomize(x, cut)

    r_cont = correlation(x, y)
    r_dich = correlation(b, y)

    binary_has_two_levels = len(set(b)) == 2
    print("  the dichotomized variable has only two levels = %s (%s)" % (binary_has_two_levels, sorted(set(b))))

    within_group_variation_lost = len(set(x)) > len(set(b))
    print("  x's distinct values (%d) collapse to %d levels = %s" % (len(set(x)), len(set(b)), within_group_variation_lost))

    dichotomized_weaker = r_dich < r_cont
    print("  the dichotomized correlation is weaker than the continuous = %s (%.3f < %.3f)" % (dichotomized_weaker, r_dich, r_cont))

    relationship_survives = r_dich > 0
    print("  the relationship survives the split (attenuated, not destroyed) = %s (%.3f)" % (relationship_survives, r_dich))

    continuous_keeps_full = r_cont >= r_dich
    print("  the continuous variable keeps at least as much signal = %s" % continuous_keeps_full)

    ok = (binary_has_two_levels and within_group_variation_lost and dichotomized_weaker
          and relationship_survives and continuous_keeps_full)
    print("-" * 116)
    print("SELF-TEST %s  binary_has_two_levels=%s  within_group_variation_lost=%s  dichotomized_weaker=%s  relationship_survives=%s  continuous_keeps_full=%s"
          % ("PASS" if ok else "FAIL", binary_has_two_levels, within_group_variation_lost,
             dichotomized_weaker, relationship_survives, continuous_keeps_full))
    return ok


def main():
    p = argparse.ArgumentParser(description="Dichotomization: keep a continuous predictor continuous rather than splitting it into high/low, because dichotomizing discards the within-group variation and attenuates the association -- lowering the correlation and the statistical power -- for a simplicity that is not worth the lost signal.")
    p.add_argument("--split", action="store_true")
    p.add_argument("--corr", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("n=%d  file=%s  (x and y are a fixture)" % (len(data["x"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.split:
        split_view(data)
    elif args.corr:
        corr_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
