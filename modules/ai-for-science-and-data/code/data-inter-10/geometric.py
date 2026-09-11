"""Average growth factors with the geometric mean -- the arithmetic mean compounds to the wrong total.

Growth multiplies, it does not add. A quantity that grows by a factor each period -- an investment, a
user base, a model's loss ratio between runs -- ends at the PRODUCT of its factors, not their sum. So
when you summarize "typical growth" by averaging the factors the ordinary way, you get a number that,
compounded over the periods, overshoots the truth, often wildly. The arithmetic mean answers "what
single factor has the same SUM as these?" -- a question compounding never asks.

The right average is the geometric mean: the n-th root of the product of the factors. It is the single
constant factor that, applied every period, reproduces the actual end value exactly, because it is
defined by the product the way the arithmetic mean is defined by the sum. And by the AM-GM inequality
the arithmetic mean is always greater than or equal to the geometric mean, with equality only when
every factor is identical -- so averaging factors arithmetically overstates compound growth whenever
the factors vary at all.

On this fixture 100 grows by 2.0, 0.5, 1.5, 0.8 and ends at 120 -- a 1.2x total over four periods.
The arithmetic mean of the factors is 1.2, which sounds like +20% PER PERIOD and, compounded four
times, predicts 207.4 -- nearly double the truth. The geometric mean is 1.0466 (+4.66% per period),
and compounded four times it lands on 120.0 exactly. This computes the true end value and what each
mean predicts.

  --growth     the starting value, the factors, and the true end value period by period
  --means      the arithmetic vs geometric mean factor, and the end value each one predicts
  --check      only the geometric mean reproduces the true end value; the arithmetic mean overstates it

The start and factors are the fixture; every mean and prediction is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "growth.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def product(xs):
    p = 1.0
    for x in xs:
        p *= x
    return p


def arithmetic_mean(xs):
    return sum(xs) / len(xs)


def geometric_mean(xs):
    """The n-th root of the product -- the constant factor that reproduces the compounded result."""
    return product(xs) ** (1 / len(xs))


def compound(start, factor, n):
    """Apply a single constant factor n times to a starting value."""
    return start * factor ** n


def true_end(start, factors):
    """The actual end value: apply the real factors in sequence."""
    value = start
    for f in factors:
        value *= f
    return value


# ----------------------------------------------------------------- printing

def growth_view(data):
    start, factors = data["start"], data["factors"]
    print("GROWTH — the value compounding period by period")
    print("-" * 44)
    value = start
    print("  start            %8.2f" % value)
    for i, f in enumerate(factors, 1):
        value *= f
        print("  period %d  x%-5.2f %8.2f" % (i, f, value))
    print("-" * 44)
    print("  end value %.2f = %.2f x product(%s) = %.2f x %.2f"
          % (value, start, factors, start, product(factors)))


def means_view(data):
    start, factors = data["start"], data["factors"]
    n = len(factors)
    am, gm = arithmetic_mean(factors), geometric_mean(factors)
    end = true_end(start, factors)
    print("MEANS — arithmetic vs geometric factor, and what each predicts over %d periods" % n)
    print("-" * 66)
    print("  true end value:                       %8.2f" % end)
    print("  arithmetic mean factor %.4f -> predicts %8.2f  (off by %+.2f)"
          % (am, compound(start, am, n), compound(start, am, n) - end))
    print("  geometric  mean factor %.4f -> predicts %8.2f  (off by %+.2f)"
          % (gm, compound(start, gm, n), compound(start, gm, n) - end))
    print("-" * 66)
    print("  the arithmetic mean compounds to nearly double the truth; the geometric mean lands on it.")


def check(data):
    print("SELF-TEST — only the geometric mean reproduces the true end value; the arithmetic mean overstates it")
    print("-" * 92)
    start, factors = data["start"], data["factors"]
    n = len(factors)
    am, gm = arithmetic_mean(factors), geometric_mean(factors)
    end = true_end(start, factors)

    geo_reproduces = abs(compound(start, gm, n) - end) < 1e-6
    print("  the geometric mean compounds to the true end value = %s (%.4f vs %.4f)"
          % (geo_reproduces, compound(start, gm, n), end))

    arith_overstates = compound(start, am, n) > end
    print("  the arithmetic mean overstates the compounded result = %s (%.2f vs %.2f)"
          % (arith_overstates, compound(start, am, n), end))

    am_ge_gm = am >= gm
    print("  the arithmetic mean is >= the geometric mean (AM-GM) = %s (%.4f >= %.4f)" % (am_ge_gm, am, gm))

    arith_not_reproduce = abs(compound(start, am, n) - end) > 1.0
    print("  the arithmetic mean does NOT reproduce the end value = %s (off by %.2f)"
          % (arith_not_reproduce, compound(start, am, n) - end))

    ok = geo_reproduces and arith_overstates and am_ge_gm and arith_not_reproduce
    print("-" * 92)
    print("SELF-TEST %s  geo_reproduces=%s  arith_overstates=%s  am_ge_gm=%s  arith_not_reproduce=%s"
          % ("PASS" if ok else "FAIL", geo_reproduces, arith_overstates, am_ge_gm, arith_not_reproduce))
    return ok


def main():
    p = argparse.ArgumentParser(description="Average growth factors with the geometric mean, not the arithmetic mean.")
    p.add_argument("--growth", action="store_true")
    p.add_argument("--means", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("start=%.2f  factors=%s  file=%s  (the start and factors are a fixture)"
          % (data["start"], data["factors"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.growth:
        growth_view(data)
    elif args.means:
        means_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
