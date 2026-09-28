"""Correct for multiple comparisons, or testing enough metrics guarantees a false winner from pure luck.

A single significance test at alpha=0.05 accepts a 5% chance of a false positive: if two models are truly
identical, one time in twenty the test still says "different" by luck. That 5% is a budget for ONE test. The
moment you compare the models on many metrics -- accuracy, latency, refusal rate, cost, a dozen task
subscores -- and declare a win if ANY of them is significant, you are running the 5% gamble many times and
keeping the luckiest outcome. The chance that at least one of ten independent null tests trips 0.05 is not 5%;
it is 1-(1-0.05)^10 = 40%. Test enough things and a false positive is not a risk, it is the expected result.

The fix is to spend the 5% budget across the whole family of tests, not per test. Bonferroni is the simplest
form: to keep the family-wise error at alpha across m tests, require each individual test to clear alpha/m. With
ten metrics the per-test threshold drops from 0.05 to 0.005, and the probability that any of the ten trips it
falls back to about 5%. You did not run fewer tests; you raised the bar each one must clear so the whole battery
together still only risks 5%. The alternative -- reporting the one metric that happened to be significant out of
twenty -- is how a tie gets written up as a win.

On this fixture two identical models are compared on 10 metrics, 2000 times. Declaring a win on any uncorrected
metric produces a false positive in 38.5% of the runs -- eight times the nominal 5%. With Bonferroni's alpha/m
threshold the false-positive rate falls to 4.5%, back under 5%. This computes both.

  --rate       the family-wise false-positive rate, uncorrected vs Bonferroni, against the nominal alpha
  --trial      one trial's 10 null p-values and which "significant" hits survive the Bonferroni threshold
  --check      the uncorrected rate blows past alpha; Bonferroni holds it under alpha; the threshold is alpha/m

The metric count, alpha, and seed are the fixture; every p-value is drawn under the null. Stdlib only.
"""
import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "multiplecomparisons.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def null_pvalues(metrics, seed):
    """Under the null hypothesis each test's p-value is uniform on [0,1]."""
    rng = random.Random(seed)
    return [rng.random() for _ in range(metrics)]


def any_significant(pvalues, threshold):
    """A family 'wins' if at least one metric clears the threshold."""
    return any(p < threshold for p in pvalues)


def fwer(metrics, alpha, trials, base_seed, corrected):
    """Fraction of trials with at least one false positive. corrected=True uses the alpha/m Bonferroni threshold."""
    threshold = alpha / metrics if corrected else alpha
    hits = sum(any_significant(null_pvalues(metrics, base_seed + i), threshold) for i in range(trials))
    return hits / trials


# ----------------------------------------------------------------- printing

def rate_view(data):
    m, a, tr, bs = data["metrics"], data["alpha"], data["trials"], data["base_seed"]
    unc = fwer(m, a, tr, bs, False)
    bon = fwer(m, a, tr, bs, True)
    theory = 1 - (1 - a) ** m
    print("RATE — family-wise false-positive rate over %d trials (%d metrics, alpha %.2f)" % (tr, m, a))
    print("-" * 66)
    print("  nominal per-test alpha:      %.3f" % a)
    print("  uncorrected (any metric):    %.3f   (theory %.3f — %.0fx alpha)" % (unc, theory, unc / a))
    print("  bonferroni (alpha/m=%.4f): %.3f   (back under alpha)" % (a / m, bon))
    print("-" * 66)
    print("  testing %d metrics and keeping any hit turns a 5%% risk into a %.0f%% one." % (m, 100 * unc))


def trial_view(data):
    m, a, es = data["metrics"], data["alpha"], data["example_seed"]
    ps = null_pvalues(m, es)
    thr = a / m
    print("TRIAL — one run's %d null p-values (seed %d), thresholds alpha=%.3f and alpha/m=%.4f" % (m, es, a, thr))
    print("-" * 66)
    print("  p-values: %s" % ["%.3f" % p for p in ps])
    unc_hits = [round(p, 3) for p in ps if p < a]
    bon_hits = [round(p, 3) for p in ps if p < thr]
    print("  significant uncorrected (p<%.3f):   %s  -> %s" % (a, unc_hits, "FALSE POSITIVE" if unc_hits else "no win"))
    print("  significant bonferroni  (p<%.4f):  %s  -> %s" % (thr, bon_hits, "win" if bon_hits else "correctly no win"))
    print("-" * 66)
    print("  the models are identical; the uncorrected 'hits' are luck the tighter threshold rejects.")


def check(data):
    print("SELF-TEST — the uncorrected rate blows past alpha; Bonferroni holds it under alpha; threshold is alpha/m")
    print("-" * 104)
    m, a, tr, bs = data["metrics"], data["alpha"], data["trials"], data["base_seed"]
    unc = fwer(m, a, tr, bs, False)
    bon = fwer(m, a, tr, bs, True)
    theory_unc = 1 - (1 - a) ** m
    theory_bon = 1 - (1 - a / m) ** m

    uncorrected_above_alpha = unc > 3 * a
    print("  uncorrected family-wise error far exceeds alpha = %s (%.3f > %.3f)" % (uncorrected_above_alpha, unc, 3 * a))

    bonferroni_theory_controls = theory_bon <= a
    print("  Bonferroni's family-wise error (theory 1-(1-a/m)^m) is <= alpha = %s (%.4f <= %.3f)" % (bonferroni_theory_controls, theory_bon, a))

    bonferroni_far_below_uncorrected = bon < unc / 3
    print("  Bonferroni's error rate collapses below the uncorrected one = %s (%.3f < %.3f)" % (bonferroni_far_below_uncorrected, bon, unc / 3))

    matches_theory = abs(unc - theory_unc) < 0.02 and abs(bon - theory_bon) < 0.02
    print("  both rates match their theory within noise = %s (unc %.3f~%.3f, bon %.3f~%.3f)" % (matches_theory, unc, theory_unc, bon, theory_bon))

    unc_again = fwer(m, a, tr, bs, False)
    deterministic = unc == unc_again
    print("  the seeded simulation is reproducible = %s (%.4f)" % (deterministic, unc))

    ok = uncorrected_above_alpha and bonferroni_theory_controls and bonferroni_far_below_uncorrected and matches_theory and deterministic
    print("-" * 104)
    print("SELF-TEST %s  uncorrected_above_alpha=%s  bonferroni_theory_controls=%s  bonferroni_far_below_uncorrected=%s  matches_theory=%s  deterministic=%s"
          % ("PASS" if ok else "FAIL", uncorrected_above_alpha, bonferroni_theory_controls, bonferroni_far_below_uncorrected, matches_theory, deterministic))
    return ok


def main():
    p = argparse.ArgumentParser(description="Multiple comparisons inflate the family-wise false-positive rate; Bonferroni's alpha/m threshold controls it.")
    p.add_argument("--rate", action="store_true")
    p.add_argument("--trial", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("metrics=%d  alpha=%.2f  trials=%d  seed=%d  file=%s  (the parameters are a fixture; models are identical)"
          % (data["metrics"], data["alpha"], data["trials"], data["base_seed"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.rate:
        rate_view(data)
    elif args.trial:
        trial_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
