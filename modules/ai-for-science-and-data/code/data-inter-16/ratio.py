"""Dividing two unrelated variables by a common quantity makes their ratios correlate -- spurious correlation.

You have three quantities and you form two ratios that share a denominator: crime per capita and doctors
per capita (both divided by population), or expenses as a fraction of revenue and salaries as a fraction of
revenue (both over revenue). You plot the two ratios, see a correlation, and conclude the numerators are
related. They need not be. Dividing two independent numerators by the same denominator injects a shared
factor -- one over the denominator -- into both ratios, and that shared factor makes them move together
even when the things on top have nothing to do with each other. When the denominator is small both ratios
are large, when it is large both are small, and that common swing shows up as correlation. This is Pearson's
spurious correlation of ratios, known since 1897 and still catching people out.

The tell is that the correlation lives in the denominator, not the numerators. Correlate the raw numerators
and there is nothing. Correlate the two ratios with the SAME denominator and a correlation appears. Correlate
them with DIFFERENT denominators (each numerator over its own unrelated divisor) and it vanishes again --
proving the shared denominator, not any real relationship, produced it. So a correlation between two ratios
is not evidence the numerators are related; you have to check the numerators directly, or the shared divisor
will manufacture a relationship out of thin air.

On this fixture X and Y are uncorrelated numerators (correlation 0.00). Dividing both by the same Z gives
ratios that correlate 0.971 -- a strong spurious correlation. Dividing X by Z and Y by a different divisor W
gives 0.03 -- gone. Same numerators; only the shared denominator created the correlation. This computes it.

  --data       the three columns and the ratios formed from them
  --correlate  the correlation of the numerators, the same-denominator ratios, and different-denominator ratios
  --check      the numerators are uncorrelated but the shared-denominator ratios are, and different denominators are not

The columns are the fixture; every correlation is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "columns.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mean(xs):
    return sum(xs) / len(xs)


def correlation(xs, ys):
    mx, my = mean(xs), mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    vy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return round(cov / (vx * vy), 3) if vx and vy else 0.0


def ratio(num, den):
    return [round(n / d, 3) for n, d in zip(num, den)]


# ----------------------------------------------------------------- printing

def data_view(data):
    x, y, z, w = data["X"], data["Y"], data["Z"], data["W"]
    print("DATA — three columns and the ratios over a shared denominator Z")
    print("-" * 58)
    print("  X:    %s" % x)
    print("  Y:    %s" % y)
    print("  Z:    %s   (shared denominator)" % z)
    print("  X/Z:  %s" % ratio(x, z))
    print("  Y/Z:  %s" % ratio(y, z))
    print("-" * 58)
    print("  when Z is small both ratios are large, and vice versa.")


def correlate_view(data):
    x, y, z, w = data["X"], data["Y"], data["Z"], data["W"]
    print("CORRELATE — correlation of numerators vs ratios")
    print("-" * 58)
    print("  numerators        X   vs Y   : %+.3f" % correlation(x, y))
    print("  same denominator  X/Z vs Y/Z : %+.3f" % correlation(ratio(x, z), ratio(y, z)))
    print("  diff denominator  X/Z vs Y/W : %+.3f" % correlation(ratio(x, z), ratio(y, w)))
    print("-" * 58)
    print("  the correlation appears only with the shared denominator.")


def check(data):
    print("SELF-TEST — uncorrelated numerators, but a shared denominator makes the ratios correlate")
    print("-" * 96)
    x, y, z, w = data["X"], data["Y"], data["Z"], data["W"]
    r_num = correlation(x, y)
    r_same = correlation(ratio(x, z), ratio(y, z))
    r_diff = correlation(ratio(x, z), ratio(y, w))

    numerators_uncorrelated = abs(r_num) < 0.1
    print("  the raw numerators are uncorrelated = %s (%.3f)" % (numerators_uncorrelated, r_num))

    shared_denom_correlated = r_same > 0.7
    print("  the same-denominator ratios are strongly correlated = %s (%.3f)" % (shared_denom_correlated, r_same))

    spurious_gap = r_same - abs(r_num) > 0.7
    print("  the ratio correlation dwarfs the numerator correlation = %s (%.3f vs %.3f)" % (spurious_gap, r_same, r_num))

    diff_denom_not_correlated = abs(r_diff) < 0.2
    print("  different denominators remove the correlation = %s (%.3f)" % (diff_denom_not_correlated, r_diff))

    positive_spurious = r_same > 0
    print("  the spurious correlation is positive (shared 1/Z) = %s" % positive_spurious)

    ok = numerators_uncorrelated and shared_denom_correlated and spurious_gap and diff_denom_not_correlated and positive_spurious
    print("-" * 96)
    print("SELF-TEST %s  numerators_uncorrelated=%s  shared_denom_correlated=%s  spurious_gap=%s  diff_denom_not_correlated=%s  positive_spurious=%s"
          % ("PASS" if ok else "FAIL", numerators_uncorrelated, shared_denom_correlated, spurious_gap, diff_denom_not_correlated, positive_spurious))
    return ok


def main():
    p = argparse.ArgumentParser(description="Spurious correlation: a shared denominator correlates two unrelated ratios.")
    p.add_argument("--data", action="store_true")
    p.add_argument("--correlate", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("n=%d  file=%s  (the columns are a fixture)" % (len(data["X"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.data:
        data_view(data)
    elif args.correlate:
        correlate_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
