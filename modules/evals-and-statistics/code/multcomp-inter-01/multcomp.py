"""Test 20 metrics at 0.05 and a false 'winner' is more likely than not -- the threshold is per-test, the risk is per-family.

A significance threshold of 0.05 is a promise about ONE test: if nothing is really going on, there is a 5% chance the
test clears the bar by luck (a false positive). That promise is per-test, and it does not survive being repeated. Run
the same 0.05 test on 20 independent metrics of an unchanged system and the chance that AT LEAST ONE of them clears the
bar by luck is not 5% -- it is 1 minus the chance all 20 stay under, 1-(0.95)^20 = 0.64. So on a dashboard of 20
metrics comparing a change that does nothing, you should EXPECT about one 'significant' result (20 x 0.05 = 1), and
finding one is not evidence of an effect -- it is exactly what pure noise produces. The error is treating a per-test
false-positive rate as if it were the rate for the whole family of tests you actually ran.

This is the multiple-comparisons problem, and it is everywhere in evaluation: many metrics, many segments, many model
variants, many days of peeking at the same experiment -- each additional look is another draw at the 5% lottery, and the
family-wise error rate (the chance of ANY false positive) climbs toward certainty. The fix is to control error across
the family, not per test. The Bonferroni correction is the simplest: to hold the family-wise false-positive rate at
alpha, require each test to clear alpha/n instead of alpha -- here 0.05/20 = 0.0025. It is conservative (it can miss real
effects), and less blunt procedures exist (Benjamini-Hochberg controls the false-discovery rate instead), but the
principle is the same: the more comparisons you make, the higher the bar each one must clear.

On this fixture the same system is compared to itself on 20 metrics, so every 'win' is false by construction. The naive
0.05 test flags metric_01 (p=0.0375) as significant -- one false positive, exactly the ~1 the math predicts. The
family-wise error rate is 0.64, so seeing at least one was more likely than not. Bonferroni's 0.0025 threshold flags
none, correctly reporting no effect. This computes all of it.

  --naive    each metric tested at 0.05 independently -- one metric clears the bar, a false positive on an A/A test
  --correct  the family-wise error rate for 20 tests, and the Bonferroni threshold that flags none of them
  --check    an A/A test yields a false positive under naive 0.05 testing; the family-wise error exceeds 1/2; Bonferroni flags none

The p-values and alpha are the fixture; every rate and threshold is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "multcomp.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def family_wise_error(alpha, n):
    """Chance of AT LEAST ONE false positive across n independent tests each at level alpha: 1 - (1-alpha)^n."""
    return 1 - (1 - alpha) ** n


def bonferroni_threshold(alpha, n):
    """The per-test bar that holds the family-wise false-positive rate at alpha: alpha / n."""
    return alpha / n


def flagged(pvalues, threshold):
    """The metrics whose p-value clears (is below) the threshold."""
    return [m for m, p in sorted(pvalues.items()) if p < threshold]


# ----------------------------------------------------------------- printing

def naive_view(data):
    pv, alpha = data["metric_pvalues"], data["alpha"]
    print("NAIVE — every metric tested independently at alpha=%.2f (A/A test: no true effect)" % alpha)
    print("-" * 66)
    hits = flagged(pv, alpha)
    for m, p in sorted(pv.items(), key=lambda kv: kv[1]):
        mark = "  <- SIGNIFICANT (p<%.2f)" % alpha if p < alpha else ""
        print("  %-11s p=%.4f%s" % (m, p, mark))
    print("-" * 66)
    print("  %d metric(s) flagged 'significant': %s -- but the system did not change, so these are false positives." % (len(hits), hits))


def correct_view(data):
    pv, alpha = data["metric_pvalues"], data["alpha"]
    n = len(pv)
    print("CORRECT — control error across the whole family of %d tests" % n)
    print("-" * 66)
    fwer = family_wise_error(alpha, n)
    print("  family-wise error rate (chance of >=1 false positive) = 1-(1-%.2f)^%d = %.4f" % (alpha, n, fwer))
    print("  so with no real effect you EXPECT about %.1f false 'wins' (%d x %.2f)" % (n * alpha, n, alpha))
    thr = bonferroni_threshold(alpha, n)
    hits = flagged(pv, thr)
    print("  Bonferroni threshold = %.2f/%d = %.4f" % (alpha, n, thr))
    print("  metrics clearing the Bonferroni bar: %s" % (hits if hits else "none"))
    print("-" * 66)
    print("  smallest p-value is %.4f, above %.4f -- correctly, no metric is called significant." % (min(pv.values()), thr))


def check(data):
    print("SELF-TEST — an A/A test yields a false positive under naive 0.05 testing; the family-wise error exceeds 1/2; Bonferroni flags none")
    print("-" * 122)
    pv, alpha = data["metric_pvalues"], data["alpha"]
    n = len(pv)

    naive_hits = flagged(pv, alpha)
    naive_false_positive = len(naive_hits) >= 1
    print("  naive 0.05 testing flags a 'winner' on an A/A test = %s (%s)" % (naive_false_positive, naive_hits))

    fwer = family_wise_error(alpha, n)
    fwer_exceeds_half = fwer > 0.5
    print("  the family-wise error rate for %d tests exceeds 1/2 = %s (%.4f)" % (n, fwer_exceeds_half, fwer))

    expected_one = abs(n * alpha - 1.0) < 1e-9
    print("  the expected number of false positives is exactly 1 = %s (%d x %.2f)" % (expected_one, n, alpha))

    thr = bonferroni_threshold(alpha, n)
    bonferroni_none = len(flagged(pv, thr)) == 0
    print("  Bonferroni (bar %.4f) flags no metric = %s" % (thr, bonferroni_none))

    bonferroni_stricter = thr < alpha
    print("  the Bonferroni bar is stricter than the per-test bar = %s (%.4f < %.2f)" % (bonferroni_stricter, thr, alpha))

    ok = naive_false_positive and fwer_exceeds_half and expected_one and bonferroni_none and bonferroni_stricter
    print("-" * 122)
    print("SELF-TEST %s  naive_false_positive=%s  fwer_exceeds_half=%s  expected_one=%s  bonferroni_none=%s  bonferroni_stricter=%s"
          % ("PASS" if ok else "FAIL", naive_false_positive, fwer_exceeds_half, expected_one, bonferroni_none, bonferroni_stricter))
    return ok


def main():
    p = argparse.ArgumentParser(description="Multiple comparisons: a 0.05 threshold bounds the false-positive rate of ONE test, but testing many metrics makes at least one false positive likely (family-wise error 1-(1-alpha)^n); control error across the family (Bonferroni alpha/n, or Benjamini-Hochberg) rather than per test.")
    p.add_argument("--naive", action="store_true")
    p.add_argument("--correct", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("metrics=%d  alpha=%.2f  min_p=%.4f  file=%s  (the p-values are a fixture: an A/A test with no true effect)"
          % (len(data["metric_pvalues"]), data["alpha"], min(data["metric_pvalues"].values()), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.naive:
        naive_view(data)
    elif args.correct:
        correct_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
