"""Significance is not size -- with enough data a trivial difference gets a tiny p-value that means nothing.

A p-value answers one narrow question: if there were truly no difference, how surprising is data this
extreme? It does not answer the question people actually care about: how big is the difference, and does
it matter? Those come apart completely as the sample grows. The test statistic for a two-group comparison
scales with the square root of n, so holding the real difference fixed and pouring in more data drives the
p-value toward zero -- not because the effect got bigger, but because the estimate got precise enough to
resolve an effect that was always there and always tiny. At large n, a difference far too small to care
about is reported as 'highly significant', and a reader who treats the p-value as a measure of importance
concludes the opposite of the truth.

The fix is to report effect size, not just significance. Cohen's d -- the difference in units of the
standard deviation -- measures how big the gap is, and it does not change with n: it is a property of the
populations, not the sample size. A d of 0.1 is trivial whether you measured 10 points or a million;
only its p-value moves. So a claim needs both numbers: the effect size says whether it matters, the
p-value (with a confidence interval) says whether you have the data to believe it is real. Significance
without size is the classic large-n trap.

On this fixture two groups differ by 1 point on a scale with a standard deviation of 10 -- a Cohen's d of
0.1, trivially small. As n grows from 10 to 10000, the effect size stays exactly 0.1 while the two-sided
p-value falls from 0.823 (nowhere near significant) to 1.5e-12 (wildly significant). Same negligible
effect; the p-value is measuring the sample size, not the importance. This computes both.

  --table      the p-value and effect size at each sample size
  --effect     the effect size is constant while the p-value collapses with n
  --check      p shrinks with n while Cohen's d stays fixed and trivial; large n makes a nothing significant

The two means, the standard deviation, and the sample sizes are the fixture; every p is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "groups.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def cohens_d(mean1, mean2, sd):
    """Effect size: the difference in standard-deviation units -- independent of sample size."""
    return abs(mean1 - mean2) / sd


def t_statistic(mean1, mean2, sd, n):
    """Two-sample statistic with equal n and sd -- grows with sqrt(n) for a fixed difference."""
    se = sd * math.sqrt(2.0 / n)
    return abs(mean1 - mean2) / se


def two_sided_p(z):
    """Two-sided p-value under a normal approximation, via the error function (stdlib)."""
    phi = 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0)))
    return 2.0 * (1.0 - phi)


def row(data, n):
    d = cohens_d(data["mean1"], data["mean2"], data["sd"])
    t = t_statistic(data["mean1"], data["mean2"], data["sd"], n)
    return {"n": n, "d": d, "t": t, "p": two_sided_p(t)}


# ----------------------------------------------------------------- printing

def table_view(data):
    print("TABLE — a %g-point difference (sd %g) at growing sample sizes"
          % (abs(data["mean1"] - data["mean2"]), data["sd"]))
    print("-" * 58)
    print("  n        effect size d   t-stat    p-value      significant?")
    for n in data["sample_sizes"]:
        r = row(data, n)
        sig = "yes" if r["p"] < 0.05 else "no"
        print("  %-7d  %11.3f   %7.3f   %.3g%s   %s"
              % (r["n"], r["d"], r["t"], r["p"], " " * max(0, 9 - len("%.3g" % r["p"])), sig))
    print("-" * 58)
    print("  the effect size never moves; only the p-value does.")


def effect_view(data):
    print("EFFECT — Cohen's d is a population fact; the p-value is a sample-size fact")
    print("-" * 58)
    ds = [row(data, n)["d"] for n in data["sample_sizes"]]
    ps = [row(data, n)["p"] for n in data["sample_sizes"]]
    print("  sample sizes:   %s" % data["sample_sizes"])
    print("  effect size d:  %s   (constant)" % [round(x, 3) for x in ds])
    print("  p-value:        %s   (collapses)" % ["%.2g" % x for x in ps])
    print("-" * 58)
    print("  d=%.2f is 'small' by convention (<0.2); it is trivial at every n." % ds[0])


def check(data):
    print("SELF-TEST — the p-value shrinks with n while the effect size stays fixed and trivial")
    print("-" * 92)
    rows = [row(data, n) for n in data["sample_sizes"]]
    ps = [r["p"] for r in rows]
    ds = [r["d"] for r in rows]

    p_shrinks_with_n = all(ps[i] > ps[i + 1] for i in range(len(ps) - 1))
    print("  the p-value falls monotonically as n grows = %s (%s)" % (p_shrinks_with_n, ["%.2g" % x for x in ps]))

    effect_constant = max(ds) - min(ds) < 1e-12
    print("  Cohen's d is identical at every sample size = %s (%.3f)" % (effect_constant, ds[0]))

    effect_trivial = ds[0] < 0.2
    print("  the effect size is trivially small (d < 0.2) = %s (%.3f)" % (effect_trivial, ds[0]))

    small_n_not_significant = ps[0] > 0.05
    print("  at the smallest n the difference is not significant = %s (p=%.3f)" % (small_n_not_significant, ps[0]))

    large_n_significant = ps[-1] < 0.001
    print("  at the largest n the same nothing is 'highly significant' = %s (p=%.2g)" % (large_n_significant, ps[-1]))

    ok = p_shrinks_with_n and effect_constant and effect_trivial and small_n_not_significant and large_n_significant
    print("-" * 92)
    print("SELF-TEST %s  p_shrinks_with_n=%s  effect_constant=%s  effect_trivial=%s  small_n_not_significant=%s  large_n_significant=%s"
          % ("PASS" if ok else "FAIL", p_shrinks_with_n, effect_constant, effect_trivial, small_n_not_significant, large_n_significant))
    return ok


def main():
    p = argparse.ArgumentParser(description="Significance is not size: a trivial effect gets a tiny p-value at large n.")
    p.add_argument("--table", action="store_true")
    p.add_argument("--effect", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("mean1=%g  mean2=%g  sd=%g  sizes=%s  file=%s  (the means, sd, and sizes are a fixture)"
          % (data["mean1"], data["mean2"], data["sd"], data["sample_sizes"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.table:
        table_view(data)
    elif args.effect:
        effect_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
