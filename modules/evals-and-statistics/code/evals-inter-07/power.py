#!/usr/bin/env python3
"""A null result from a small eval is not 'no difference' -- compute the detectable effect first.

You run 20 cases on system A and system B, B scores a little higher, the confidence interval on
the difference includes zero, and you conclude the systems are equivalent. That conclusion is
usually wrong, because a 20-case eval is nearly blind: the interval is so wide that only a
gigantic difference could have cleared it, and a real, useful improvement sits comfortably
inside the noise. Absence of a significant result is not evidence of no effect; it is often
just evidence that the eval was too small to see one.

The number that decides this is the minimum detectable effect (MDE): the smallest true
difference a given sample size could reliably distinguish from zero, roughly the half-width of
the confidence interval on the difference. It shrinks with the square root of n. Here two
systems truly differ by 6 points; at n = 20 the MDE is 27 points, so the true effect is four
times smaller than anything the eval could detect and the null result is uninformative -- and
at n = 500 the MDE drops to about 5 points, below the true effect, so the same real difference
becomes visible. This computes the MDE at several sample sizes and shows which ones can and
cannot detect the known effect, so a null is read correctly: powered, or just too small.

  --power     the minimum detectable effect at each sample size, vs the true effect
  --verdict   at each n, whether the eval can detect the true difference -- and how to read a null
  --check     the small eval cannot detect the true effect (its null is uninformative); a large one can

The true rates and sample sizes are the fixture; every standard error and MDE is computed. Stdlib.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "eval.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the power calculation

def se_difference(pa, pb, n):
    """Standard error of the difference in two pass rates, each measured on n cases."""
    return math.sqrt(pa * (1 - pa) / n + pb * (1 - pb) / n)


def mde(pa, pb, n, z):
    """Minimum detectable effect: the CI half-width, the smallest difference this n can resolve."""
    return z * se_difference(pa, pb, n)


def can_detect(pa, pb, n, z):
    """Can an eval of this size distinguish the true effect from zero?"""
    return abs(pb - pa) > mde(pa, pb, n, z)


# ----------------------------------------------------------------- printing

def power_view(data):
    pa, pb, z = data["rate_a"], data["rate_b"], data["z"]
    effect = abs(pb - pa)
    print("POWER — minimum detectable effect by sample size (true effect %.0f pts)" % (100 * effect))
    print("-" * 66)
    print("  n per system   std error   MDE (pts)   can detect the %.0f-pt effect?" % (100 * effect))
    for n in data["sample_sizes"]:
        print("  %-14d %-11.4f %-11.1f %s"
              % (n, se_difference(pa, pb, n), 100 * mde(pa, pb, n, z),
                 "yes" if can_detect(pa, pb, n, z) else "NO (underpowered)"))
    print("-" * 66)
    print("  the MDE shrinks with sqrt(n); a null result only means 'equal' once the MDE is below the effect.")


def verdict_view(data):
    pa, pb, z = data["rate_a"], data["rate_b"], data["z"]
    effect = abs(pb - pa)
    print("VERDICT — how to read a null (non-significant) result at each n")
    print("-" * 66)
    for n in data["sample_sizes"]:
        m = mde(pa, pb, n, z)
        if can_detect(pa, pb, n, z):
            read = "powered: a null would truly mean no meaningful effect"
        else:
            read = "UNDERPOWERED: a null means nothing -- MDE %.0f pts > effect %.0f" % (100 * m, 100 * effect)
        print("  n=%-5d MDE=%.0f pts -> %s" % (n, 100 * m, read))
    print("-" * 66)
    print("  same true effect throughout; only the eval's size changes what a null can mean.")


def check(data):
    print("SELF-TEST — the small eval cannot detect the true effect; a large one can")
    print("-" * 66)
    pa, pb, z = data["rate_a"], data["rate_b"], data["z"]
    effect = abs(pb - pa)
    small = data["small_n"]
    large = data["large_n"]

    small_blind = not can_detect(pa, pb, small, z)
    print("  the small eval (n=%d) CANNOT detect the %.0f-pt effect = %s (MDE %.0f pts)"
          % (small, 100 * effect, small_blind, 100 * mde(pa, pb, small, z)))

    small_underpowered = mde(pa, pb, small, z) > 2 * effect
    print("  the small eval's MDE is far larger than the true effect = %s (%.0f vs %.0f pts)"
          % (small_underpowered, 100 * mde(pa, pb, small, z), 100 * effect))

    large_detects = can_detect(pa, pb, large, z)
    print("  the large eval (n=%d) CAN detect the same effect = %s (MDE %.0f pts)"
          % (large, large_detects, 100 * mde(pa, pb, large, z)))

    # the MDE strictly shrinks as n grows -- more data, finer resolution
    mdes = [mde(pa, pb, n, z) for n in sorted(data["sample_sizes"])]
    mde_shrinks = all(mdes[i] > mdes[i + 1] for i in range(len(mdes) - 1))
    print("  the MDE strictly shrinks as n grows = %s" % mde_shrinks)

    ok = small_blind and small_underpowered and large_detects and mde_shrinks
    print("-" * 66)
    print("SELF-TEST %s  small_blind=%s  small_underpowered=%s  large_detects=%s  mde_shrinks=%s"
          % ("PASS" if ok else "FAIL", small_blind, small_underpowered, large_detects, mde_shrinks))
    return ok


def main():
    p = argparse.ArgumentParser(description="Read a null eval result through its minimum detectable effect.")
    p.add_argument("--power", action="store_true")
    p.add_argument("--verdict", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("rate_a=%.2f  rate_b=%.2f  true_effect=%.0f pts  z=%.2f  file=%s  (rates and sizes are a fixture)"
          % (data["rate_a"], data["rate_b"], 100 * abs(data["rate_b"] - data["rate_a"]), data["z"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.power:
        power_view(data)
    elif args.verdict:
        verdict_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
