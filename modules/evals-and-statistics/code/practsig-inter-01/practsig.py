"""Report the effect size and its interval against a decision threshold, not just the p-value -- a big enough sample makes a trivial effect 'significant'.

A p-value below 0.05 is treated as the finish line: the result is 'significant', so ship it. But statistical significance answers only one narrow question -- is the effect distinguishable from zero? -- and it answers even that in a way that depends on sample size. The standard error of an estimate shrinks as the sample grows, and the test statistic is the effect divided by that standard error, so for ANY real effect, however tiny, a large enough sample drives the statistic past the significance threshold. Significance is thus partly a statement about how much data you collected, not only about how big the effect is. Collect enough and a 0.1% lift that no user would ever notice becomes 'statistically significant'.

The question significance does NOT answer is the one that actually decides an action: is the effect big enough to matter? That is practical significance, and it is measured against a domain threshold -- the smallest effect worth the cost of shipping, maintaining, and complicating the product. A result can be statistically significant (the interval excludes zero) and practically negligible (the whole interval sits below the threshold) at the same time; those are not in tension, they are answers to different questions. Reading significance as importance conflates them, and at large sample sizes that conflation ships a stream of real-but-meaningless changes, each with a p-value to defend it.

The fix is to report and decide on the EFFECT SIZE and its confidence interval, compared to a pre-set practical threshold -- not on the p-value alone. The confidence interval carries both pieces of information at once: whether it excludes zero (statistical significance) and where it sits relative to the threshold (practical significance). An interval that excludes zero but lies entirely below the threshold is a real effect too small to act on; an interval straddling the threshold means the test cannot yet tell whether the effect is big enough, which is a call for more data, not a ship decision.

The rule: judge a result by its effect size and confidence interval against a pre-set practical threshold, not by statistical significance alone, because the test statistic grows with sample size for any nonzero effect -- so a large enough sample makes a trivially small effect statistically significant while it remains far below the size worth acting on.

On this fixture the true effect is a 0.2 percentage-point lift and the practical threshold is 1 percentage point. At n=1000 the effect is not significant; at n=1,000,000 the identical 0.2pp effect is significant (p well below 0.05) with a confidence interval that excludes zero yet lies entirely below the 1pp threshold. This computes both.

  --measure   for each sample size: the effect, its standard error, z, p-value, and confidence interval
  --compare   how significance flips with n while the effect size and its practical importance do not
  --check     a large sample makes a below-threshold effect significant; the effect size and interval show it is not worth shipping

baseline_rate, effect, practical_threshold, and sample_sizes are the fixture; every standard error, z, p-value, and interval is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "practsig.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def standard_error(p, n):
    """SE of the difference between two proportions, each arm rate p and size n."""
    return math.sqrt(2 * p * (1 - p) / n)


def z_stat(effect, se):
    return effect / se


def p_value(z):
    """Two-sided p-value from a z-statistic (normal approximation)."""
    return math.erfc(abs(z) / math.sqrt(2))


def conf_interval(effect, se):
    """95% confidence interval for the effect."""
    return effect - 1.96 * se, effect + 1.96 * se


def significant(z):
    return abs(z) >= 1.96


# ----------------------------------------------------------------- printing

def pp(x):
    """Format a proportion as percentage points."""
    return "%.3fpp" % (x * 100)


def measure_view(data):
    p, eff, thr = data["baseline_rate"], data["effect"], data["practical_threshold"]
    print("MEASURE — the same %s effect at each sample size (threshold %s)" % (pp(eff), pp(thr)))
    print("-" * 78)
    print("  n           SE          z       p-value    95% CI                significant?")
    for n in data["sample_sizes"]:
        se = standard_error(p, n)
        z = z_stat(eff, se)
        lo, hi = conf_interval(eff, se)
        print("  %-10d  %-10.5f  %-6.3f  %-9.5f  [%s, %s]   %s"
              % (n, se, z, p_value(z), pp(lo), pp(hi), significant(z)))


def compare_view(data):
    p, eff, thr = data["baseline_rate"], data["effect"], data["practical_threshold"]
    print("COMPARE — significance changes with n; effect size and importance do not")
    print("-" * 70)
    for n in data["sample_sizes"]:
        se = standard_error(p, n)
        z = z_stat(eff, se)
        lo, hi = conf_interval(eff, se)
        verdict = "SIGNIFICANT" if significant(z) else "not significant"
        practical = "worth shipping" if eff >= thr else "below threshold -- not worth shipping"
        print("  n=%-8d effect %s (%s), CI [%s, %s], %s" % (n, pp(eff), verdict, pp(lo), pp(hi), practical))
    print("-" * 70)
    print("  the effect is %s at every n; only significance changed, driven by sample size" % pp(eff))


def check(data):
    print("SELF-TEST — a large sample makes a below-threshold effect significant; the effect size and interval show it is not worth shipping")
    print("-" * 128)
    p, eff, thr = data["baseline_rate"], data["effect"], data["practical_threshold"]
    small_n, large_n = min(data["sample_sizes"]), max(data["sample_sizes"])
    se_s, se_l = standard_error(p, small_n), standard_error(p, large_n)
    z_s, z_l = z_stat(eff, se_s), z_stat(eff, se_l)
    lo_l, hi_l = conf_interval(eff, se_l)

    effect_below_threshold = eff < thr
    print("  the true effect is below the practical threshold = %s (%s < %s)" % (effect_below_threshold, pp(eff), pp(thr)))

    small_n_not_significant = not significant(z_s)
    print("  at n=%d the effect is NOT significant = %s (z=%.3f, p=%.4f)" % (small_n, small_n_not_significant, z_s, p_value(z_s)))

    large_n_significant = significant(z_l)
    print("  at n=%d the identical effect IS significant = %s (z=%.3f, p=%.5f)" % (large_n, large_n_significant, z_l, p_value(z_l)))

    effect_unchanged = True  # effect is a fixture constant, identical at both n
    print("  the effect size is identical at both sample sizes = %s (%s)" % (effect_unchanged, pp(eff)))

    ci_excludes_zero = lo_l > 0
    print("  at large n the CI excludes zero (statistically significant) = %s ([%s, %s])" % (ci_excludes_zero, pp(lo_l), pp(hi_l)))

    ci_below_threshold = hi_l < thr
    print("  at large n the whole CI lies below the practical threshold = %s (%s < %s)" % (ci_below_threshold, pp(hi_l), pp(thr)))

    se_shrinks_with_n = se_l < se_s
    print("  the standard error shrinks as n grows (the whole cause) = %s (%.5f < %.5f)" % (se_shrinks_with_n, se_l, se_s))

    ok = (effect_below_threshold and small_n_not_significant and large_n_significant and effect_unchanged
          and ci_excludes_zero and ci_below_threshold and se_shrinks_with_n)
    print("-" * 128)
    print("SELF-TEST %s  effect_below_threshold=%s  small_n_not_significant=%s  large_n_significant=%s  ci_excludes_zero=%s  ci_below_threshold=%s  se_shrinks_with_n=%s"
          % ("PASS" if ok else "FAIL", effect_below_threshold, small_n_not_significant, large_n_significant, ci_excludes_zero, ci_below_threshold, se_shrinks_with_n))
    return ok


def main():
    p = argparse.ArgumentParser(description="Practical vs statistical significance: judge a result by its effect size and confidence interval against a pre-set practical threshold, not by statistical significance alone, because the test statistic grows with sample size for any nonzero effect -- so a large enough sample makes a trivially small effect statistically significant while it remains far below the size worth acting on.")
    p.add_argument("--measure", action="store_true")
    p.add_argument("--compare", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("baseline_rate=%.2f  effect=%s  practical_threshold=%s  sample_sizes=%s  file=%s  (all are a fixture)"
          % (data["baseline_rate"], pp(data["effect"]), pp(data["practical_threshold"]), data["sample_sizes"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.measure:
        measure_view(data)
    elif args.compare:
        compare_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
