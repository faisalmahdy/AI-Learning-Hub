"""Correlation is not transitive: A can correlate strongly and positively with B, B strongly and positively with C, and yet A correlate negatively with C -- so 'A tracks B, and B tracks C, therefore A tracks C' is a false inference.

It is tempting to treat correlation like an ordering that chains: if A moves with B and B moves with C, surely A moves with C. Correlation does not chain, because it measures the alignment between two variables' deviations from their means, and alignment is a direction, not a rank. A can align with B, and C can align with B, while A and C align with B along partly opposing directions -- so A and C end up pulling against each other even though both genuinely track B.

There is an exact rule. Given r(A,B) and r(B,C), the third correlation r(A,C) is not determined; it is confined to an interval centered on the product r(A,B)*r(B,C), reaching a square-root term to either side: r(A,C) lies between r(A,B)*r(B,C) minus sqrt((1 - r(A,B)^2)(1 - r(B,C)^2)) and the product plus that same term. When r(A,B) and r(B,C) are only moderate, the product is small and the square-root term is large, so the lower end of the interval is negative -- a negative r(A,C) is permitted, not paradoxical.

This fixture is built to sit at that lower end. A is B plus a vector d orthogonal to B, and C is B minus that same d, which makes A and C share B's direction but carry opposite copies of d -- placing r(A,C) exactly at the theoretical minimum for the given pair of correlations. So both A-B and B-C come out strongly positive while A-C comes out negative, the sharpest possible violation of the transitive intuition.

On this fixture r(A,B) and r(B,C) are both about 0.65, the naive expectation from chaining is a positive r(A,C), and the actual r(A,C) is about -0.17 -- exactly the interval's lower bound. This computes all three.

  --corr    the three pairwise correlations, and the positive r(A,C) the transitive intuition predicts
  --bound   the interval r(A,C) is confined to given r(A,B) and r(B,C), and where the fixture lands in it
  --check   two strong positive correlations coexist with a negative third, which sits at the theoretical minimum the bound allows

a, b, c are the fixture; the correlations, the interval, and the landing point are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "transcorr.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mean(xs):
    return sum(xs) / len(xs)


def correlation(xs, ys):
    """Pearson correlation: the alignment of the two variables' deviations from their means."""
    mx, my = mean(xs), mean(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    num = sum(a * b for a, b in zip(dx, dy))
    den = math.sqrt(sum(a * a for a in dx) * sum(b * b for b in dy))
    return num / den if den else 0.0


def transitive_interval(r_ab, r_bc):
    """Given r(A,B) and r(B,C), the closed interval r(A,C) must lie in."""
    center = r_ab * r_bc
    spread = math.sqrt((1 - r_ab ** 2) * (1 - r_bc ** 2))
    return center - spread, center + spread


# ----------------------------------------------------------------- printing

def corr_view(data):
    a, b, c = data["a"], data["b"], data["c"]
    r_ab = correlation(a, b)
    r_bc = correlation(b, c)
    r_ac = correlation(a, c)
    print("CORR — the three pairwise correlations")
    print("-" * 48)
    print("  r(A,B) = %+.4f  (A tracks B, strongly)" % r_ab)
    print("  r(B,C) = %+.4f  (B tracks C, strongly)" % r_bc)
    print("  r(A,C) = %+.4f  (A vs C)" % r_ac)
    print("-" * 48)
    print("  transitive intuition predicts r(A,C) positive; it is %+.4f" % r_ac)


def bound_view(data):
    a, b, c = data["a"], data["b"], data["c"]
    r_ab = correlation(a, b)
    r_bc = correlation(b, c)
    r_ac = correlation(a, c)
    lo, hi = transitive_interval(r_ab, r_bc)
    print("BOUND — the interval r(A,C) is confined to, given r(A,B)=%.4f and r(B,C)=%.4f" % (r_ab, r_bc))
    print("-" * 56)
    print("  lowest possible r(A,C)  = %+.4f" % lo)
    print("  product r(A,B)*r(B,C)   = %+.4f  (the interval's center)" % (r_ab * r_bc))
    print("  highest possible r(A,C) = %+.4f" % hi)
    print("  actual r(A,C)           = %+.4f" % r_ac)
    print("-" * 56)
    print("  the actual value sits at the low end -- a negative r(A,C) is allowed, not a paradox")


def check(data):
    print("SELF-TEST — two strong positive correlations coexist with a negative third, which sits at the theoretical minimum the bound allows")
    print("-" * 112)
    a, b, c = data["a"], data["b"], data["c"]
    r_ab = correlation(a, b)
    r_bc = correlation(b, c)
    r_ac = correlation(a, c)
    lo, hi = transitive_interval(r_ab, r_bc)

    ab_strong_positive = r_ab > 0.5
    print("  r(A,B) is strongly positive = %s (%+.4f)" % (ab_strong_positive, r_ab))

    bc_strong_positive = r_bc > 0.5
    print("  r(B,C) is strongly positive = %s (%+.4f)" % (bc_strong_positive, r_bc))

    transitive_intuition_positive = r_ab * r_bc > 0
    print("  the transitive intuition (product) is positive = %s (%+.4f)" % (transitive_intuition_positive, r_ab * r_bc))

    ac_actually_negative = r_ac < 0
    print("  yet r(A,C) is actually negative = %s (%+.4f)" % (ac_actually_negative, r_ac))

    ac_at_theoretical_min = abs(r_ac - lo) < 1e-9
    print("  r(A,C) sits exactly at the interval's lower bound = %s (%+.4f vs %+.4f)" % (ac_at_theoretical_min, r_ac, lo))

    ok = (ab_strong_positive and bc_strong_positive and transitive_intuition_positive
          and ac_actually_negative and ac_at_theoretical_min)
    print("-" * 112)
    print("SELF-TEST %s  ab_strong_positive=%s  bc_strong_positive=%s  transitive_intuition_positive=%s  ac_actually_negative=%s  ac_at_theoretical_min=%s"
          % ("PASS" if ok else "FAIL", ab_strong_positive, bc_strong_positive, transitive_intuition_positive,
             ac_actually_negative, ac_at_theoretical_min))
    return ok


def main():
    p = argparse.ArgumentParser(description="Correlation is not transitive: A can correlate strongly and positively with B, B strongly and positively with C, and yet A correlate negatively with C, because correlation measures the alignment of two variables' deviations and alignment does not chain -- given r(A,B) and r(B,C), r(A,C) is only confined to an interval whose lower bound is negative when the two are moderate.")
    p.add_argument("--corr", action="store_true")
    p.add_argument("--bound", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("a=%s  b=%s  c=%s  file=%s  (these are a fixture)"
          % (data["a"], data["b"], data["c"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.corr:
        corr_view(data)
    elif args.bound:
        bound_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
