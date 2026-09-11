"""Put a Wilson interval on a pass rate, or the normal approximation claims certainty from ten trials.

You run an eval, the model passes 10 of 10, and you want a confidence interval on its true pass rate. The
textbook interval is the normal (Wald) one: p +/- z*sqrt(p(1-p)/n). Plug in p = 1.0 and it returns [1.0, 1.0]
-- zero width. The interval claims you are certain the true pass rate is exactly 100%, from ten trials. That is
absurd: ten passes is entirely consistent with a true rate of 85% or 90%. The Wald interval collapses because
its width is driven by p(1-p), which is zero at p = 0 or p = 1, so at an extreme the formula reports no
uncertainty exactly when the sample is least informative. The same defect makes it run OUTSIDE [0, 1] for
small samples -- a "confidence interval" for a probability that includes negative probabilities.

The Wilson score interval fixes both. It inverts the test around the hypothesized rate rather than the
observed one, which pulls the center toward 0.5 and keeps the interval strictly inside [0, 1], with a sensible
non-zero width even at a perfect or zero score. For 10/10 it reports something like [0.72, 1.0] -- honest
uncertainty -- instead of a false point. Wald and Wilson nearly agree when n is large and p is mid-range;
they diverge exactly where evals live: small n and rates near 0 or 1. Reach for Wilson by default.

On this fixture 10/10 gives a Wald interval of zero width (false certainty) and a Wilson interval with real
width; 1/3 gives a Wald interval whose lower bound is negative (impossible for a probability) while Wilson
stays in [0, 1]. This computes both.

  --intervals   the Wald and Wilson 95% intervals for each case
  --flaws       where Wald breaks: zero width at a perfect score, bounds outside [0,1] at small n
  --check       Wald gives zero width at 10/10 and escapes [0,1] at 1/3; Wilson stays honest on both

The trials and z are the fixture; every interval is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "trials.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def wald(k, n, z):
    """Normal-approximation interval: p +/- z*sqrt(p(1-p)/n). Can hit zero width or leave [0,1]."""
    p = k / n
    half = z * math.sqrt(p * (1 - p) / n)
    return (p - half, p + half)


def wilson(k, n, z):
    """Wilson score interval: inverts the test around the hypothesized rate; stays inside [0,1]."""
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (center - half, center + half)


def width(interval):
    return interval[1] - interval[0]


# ----------------------------------------------------------------- printing

def intervals_view(data):
    z = data["z"]
    print("INTERVALS — Wald vs Wilson 95%% intervals (z=%.2f)" % z)
    print("-" * 66)
    print("  k/n       point    Wald                 Wilson")
    for c in data["cases"]:
        n, k = c["n"], c["k"]
        wl, wu = wald(k, n, z)
        sl, su = wilson(k, n, z)
        print("  %2d/%-2d     %.2f    [%+.2f, %+.2f]     [%.2f, %.2f]" % (k, n, k / n, wl, wu, sl, su))
    print("-" * 66)
    print("  Wald collapses at 10/10 and goes negative at 1/3; Wilson stays in [0,1].")


def flaws_view(data):
    z = data["z"]
    print("FLAWS — where the Wald interval breaks")
    print("-" * 66)
    for c in data["cases"]:
        n, k = c["n"], c["k"]
        wl, wu = wald(k, n, z)
        notes = []
        if width((wl, wu)) < 1e-9:
            notes.append("ZERO WIDTH (false certainty)")
        if wl < 0 or wu > 1:
            notes.append("OUTSIDE [0,1]")
        print("  %2d/%-2d  Wald [%+.2f, %+.2f]  width %.2f  %s" % (k, n, wl, wu, width((wl, wu)), "  ".join(notes) if notes else "ok"))
    print("-" * 66)
    print("  the breaks happen at the extremes and small n -- exactly where evals sit.")


def check(data):
    print("SELF-TEST — Wald gives zero width at 10/10 and escapes [0,1] at 1/3; Wilson stays honest on both")
    print("-" * 104)
    z = data["z"]
    by = {(c["n"], c["k"]): c for c in data["cases"]}

    wl_perfect = wald(10, 10, z)
    wald_zero_width_at_perfect = width(wl_perfect) < 1e-9
    print("  Wald has zero width at 10/10 = %s ([%.2f, %.2f])" % (wald_zero_width_at_perfect, wl_perfect[0], wl_perfect[1]))

    wl_small = wald(1, 3, z)
    wald_escapes_unit = wl_small[0] < 0 or wl_small[1] > 1
    print("  Wald leaves [0,1] at 1/3 = %s (lower %.2f)" % (wald_escapes_unit, wl_small[0]))

    sl_perfect = wilson(10, 10, z)
    wilson_nonzero_at_perfect = width(sl_perfect) > 0.05
    print("  Wilson keeps real width at 10/10 = %s ([%.2f, %.2f])" % (wilson_nonzero_at_perfect, sl_perfect[0], sl_perfect[1]))

    wilson_within_unit = all(0 <= wilson(c["k"], c["n"], z)[0] and wilson(c["k"], c["n"], z)[1] <= 1 for c in data["cases"])
    print("  every Wilson interval stays in [0,1] = %s" % wilson_within_unit)

    wilson_contains_point = all(wilson(c["k"], c["n"], z)[0] <= c["k"] / c["n"] <= wilson(c["k"], c["n"], z)[1] for c in data["cases"])
    print("  every Wilson interval contains its point estimate = %s" % wilson_contains_point)

    ok = wald_zero_width_at_perfect and wald_escapes_unit and wilson_nonzero_at_perfect and wilson_within_unit and wilson_contains_point
    print("-" * 104)
    print("SELF-TEST %s  wald_zero_width_at_perfect=%s  wald_escapes_unit=%s  wilson_nonzero_at_perfect=%s  wilson_within_unit=%s  wilson_contains_point=%s"
          % ("PASS" if ok else "FAIL", wald_zero_width_at_perfect, wald_escapes_unit, wilson_nonzero_at_perfect, wilson_within_unit, wilson_contains_point))
    return ok


def main():
    p = argparse.ArgumentParser(description="Use the Wilson score interval for a pass rate, not the normal approximation.")
    p.add_argument("--intervals", action="store_true")
    p.add_argument("--flaws", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("cases=%d  z=%.2f  file=%s  (the trials are a fixture)" % (len(data["cases"]), data["z"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.intervals:
        intervals_view(data)
    elif args.flaws:
        flaws_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
