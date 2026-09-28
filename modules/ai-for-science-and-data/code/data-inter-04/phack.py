#!/usr/bin/env python3
"""Test 20 hypotheses at p<0.05 and a false 'discovery' is more likely than not.

A p-value below 0.05 means: if there were no real effect, data this extreme would show
up less than 5% of the time. Run one test, that is a reasonable bar. Run twenty, and 5%
of twenty is one -- you EXPECT a false positive by chance alone, even when every
hypothesis is null. Worse, the chance of getting at least one spurious 'significant'
result across 20 independent null tests is 1 - 0.95^20 = 64%. So a significant finding
selected from many tests is not evidence; it is what noise does when you look at it
enough times. This is the multiple-comparisons problem, and p-hacking is exploiting it,
knowingly or not.

The fix is to correct the threshold for the number of tests. Bonferroni divides alpha by
the number of tests, so the family-wise error rate -- the chance of ANY false positive --
stays at alpha, not 64%. Here 20 null p-values, two below 0.05 by chance, all fail the
corrected bar. This measures the naive discoveries, the probability that they are noise,
and the corrected result.

  --naive       the 'significant' results at p<0.05, and how many chance predicts
  --fwer        the probability of at least one false positive as tests pile up
  --correct     the Bonferroni-corrected threshold, and what survives it
  --check       chance predicts ~1 false positive; FWER > 50%; correction rejects all

Stdlib only. Deterministic -- the p-values are the fixture.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "pvalues.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the statistics

def discoveries(pvalues, threshold):
    """Indices of tests that clear a significance threshold."""
    return [i for i, p in enumerate(pvalues) if p < threshold]


def expected_false_positives(n, alpha):
    """Under all-null, the number of tests expected to cross alpha by chance."""
    return n * alpha


def family_wise_error(n, alpha):
    """P(at least one false positive) across n independent null tests."""
    return 1 - (1 - alpha) ** n


def bonferroni_threshold(n, alpha):
    """Divide alpha by the number of tests so the family-wise error stays at alpha."""
    return alpha / n


# ----------------------------------------------------------------- printing

def naive_view(data):
    pvals, alpha = data["pvalues"], data["alpha"]
    n = len(pvals)
    hits = discoveries(pvals, alpha)
    print("NAIVE — 'significant' at p < %.2f, across %d all-null tests" % (alpha, n))
    print("-" * 66)
    for i in hits:
        print("  test %2d: p = %.3f  <-- called significant" % (i, pvals[i]))
    print("-" * 66)
    print("  found %d 'discoveries'; chance alone predicts %.1f false positive(s)."
          % (len(hits), expected_false_positives(n, alpha)))
    print("  every hypothesis here is null -- these are noise.")


def fwer_view(data):
    alpha = data["alpha"]
    print("FWER — probability of at least one false positive as tests pile up (alpha=%.2f)" % alpha)
    print("-" * 66)
    print("  tests   P(>= 1 false positive)")
    for n in (1, 5, 10, 20, 50):
        print("  %-6d  %.0f%%" % (n, 100 * family_wise_error(n, alpha)))
    print("-" * 66)
    print("  at 20 tests a spurious 'significant' result is more likely than not.")


def correct_view(data):
    pvals, alpha = data["pvalues"], data["alpha"]
    n = len(pvals)
    thr = bonferroni_threshold(n, alpha)
    naive = discoveries(pvals, alpha)
    corrected = discoveries(pvals, thr)
    print("CORRECT — Bonferroni: divide alpha by the number of tests")
    print("-" * 66)
    print("  naive threshold      = %.4f  -> %d 'discoveries' %s" % (alpha, len(naive), naive))
    print("  Bonferroni threshold = %.4f  -> %d discoveries %s" % (thr, len(corrected), corrected))
    print("  smallest p-value is %.3f, still above %.4f" % (min(pvals), thr))
    print("-" * 66)
    print("  correcting for 20 tests holds the family-wise error at %.2f, not %.0f%%."
          % (alpha, 100 * family_wise_error(n, alpha)))


def check(data):
    print("SELF-TEST — chance predicts the false positives; FWER is high; correction rejects all")
    print("-" * 66)
    pvals, alpha = data["pvalues"], data["alpha"]
    n = len(pvals)

    naive = discoveries(pvals, alpha)
    finds_by_chance = len(naive) >= 1
    print("  naive p<%.2f finds 'significant' results = %s (%d of %d)"
          % (alpha, finds_by_chance, len(naive), n))

    exp = expected_false_positives(n, alpha)
    consistent_with_noise = len(naive) <= exp + 2
    print("  the count matches chance (expected %.1f false positives) = %s" % (exp, consistent_with_noise))

    fwer = family_wise_error(n, alpha)
    fwer_high = fwer > 0.5
    print("  P(>=1 false positive) exceeds 50%% = %s (%.0f%%)" % (fwer_high, 100 * fwer))

    thr = bonferroni_threshold(n, alpha)
    corrected = discoveries(pvals, thr)
    correction_rejects = len(corrected) == 0
    print("  Bonferroni correction rejects every discovery = %s (threshold %.4f)"
          % (correction_rejects, thr))

    ok = finds_by_chance and consistent_with_noise and fwer_high and correction_rejects
    print("-" * 66)
    print("SELF-TEST %s  finds_by_chance=%s  consistent_with_noise=%s  fwer_high=%s  correction_rejects=%s"
          % ("PASS" if ok else "FAIL", finds_by_chance, consistent_with_noise, fwer_high, correction_rejects))
    return ok


def main():
    p = argparse.ArgumentParser(description="Multiple comparisons, p-hacking, and correcting the threshold.")
    p.add_argument("--naive", action="store_true")
    p.add_argument("--fwer", action="store_true")
    p.add_argument("--correct", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("tests=%d  alpha=%.2f  file=%s  (p-values are a fixture; every hypothesis is null)"
          % (len(data["pvalues"]), data["alpha"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.naive:
        naive_view(data)
    elif args.fwer:
        fwer_view(data)
    elif args.correct:
        correct_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
