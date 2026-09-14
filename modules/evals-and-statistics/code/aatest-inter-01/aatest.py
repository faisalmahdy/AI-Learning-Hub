"""Run an A/A test to validate the pipeline -- both arms get the identical treatment, so a correct pipeline flags a significant difference only about alpha of the time, and a higher rate proves the measurement apparatus is broken.

Before you trust an A/B test to tell you whether a change worked, you have to trust the machinery that measures it: the randomization, the metric, the variance estimate, the stopping rule. An A/A test checks all of that at once. It splits traffic exactly like an A/B test but serves both arms the same experience, so the true difference is exactly zero and there is nothing to detect.

That makes the A/A test a null control for the whole pipeline. Because there is no real effect, every result the pipeline calls 'significant' is a false positive, and a correctly built pipeline produces false positives at precisely the rate you chose -- alpha, say 5%. So you run the A/A many times and measure how often it declares a winner. If that rate is about 5%, the apparatus is calibrated and its A/B verdicts can be trusted. If it is much higher, something is wrong, and you have found it before it corrupted a real decision.

The most common thing it catches is an underestimated variance. If the pipeline computes a standard error that is too small -- treating correlated observations as independent, pooling at the wrong unit, or using the standard error of the mean where it should use the standard error of the difference -- then every test statistic is inflated, and differences that are pure noise cross the significance threshold far more than alpha of the time. The A/A test surfaces this as a false-positive rate well above 5%, a number no amount of staring at a single A/B result would reveal.

The rule: run an A/A test -- both arms identical -- to validate the experiment pipeline before trusting A/B results, because with no real effect a correct pipeline's false-positive rate equals alpha, and a rate far above alpha exposes a broken pipeline (usually an underestimated variance) that would otherwise manufacture significant A/B wins from noise.

On this fixture eight A/A differences (arms identical, so noise around zero) are tested two ways. With the correct standard error none cross the 1.96 threshold -- a false-positive rate of 0%, consistent with alpha; with a standard error half as large, the inflated z scores push two of the eight past the threshold -- a 25% false-positive rate that flags the pipeline as broken. This computes both.

  --tests    each A/A difference with its z score and significance under the correct vs the broken pipeline
  --fpr      the false-positive rate of each pipeline against the chosen alpha
  --check    a correct pipeline's A/A false-positive rate matches alpha; a too-small variance inflates it far above

differences, se, broken_se, alpha, and z_critical are the fixture; the z scores, significances, and false-positive rates are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "aatest.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def z_score(diff, se):
    """The test statistic: how many standard errors the observed difference is from zero."""
    return diff / se


def significant(diff, se, z_crit):
    """A two-sided test calls it significant when the z score exceeds the critical value."""
    return abs(z_score(diff, se)) > z_crit


def false_positive_rate(diffs, se, z_crit):
    """On A/A data (no real effect) every significant call is a false positive."""
    return sum(significant(d, se, z_crit) for d in diffs) / len(diffs)


# ----------------------------------------------------------------- printing

def tests_view(data):
    diffs, se, bse, zc = data["differences"], data["se"], data["broken_se"], data["z_critical"]
    print("TESTS — each A/A difference (arms identical, so true effect is 0)")
    print("-" * 62)
    print("  diff    z (correct se=%.1f)   sig?   z (broken se=%.1f)   sig?" % (se, bse))
    for d in diffs:
        print("  %-5.1f   %-17.2f   %-5s  %-16.2f   %s"
              % (d, z_score(d, se), significant(d, se, zc), z_score(d, bse), significant(d, bse, zc)))
    print("-" * 62)
    print("  the broken pipeline's smaller se doubles every z and crosses the threshold more")


def fpr_view(data):
    diffs, se, bse, zc, a = data["differences"], data["se"], data["broken_se"], data["z_critical"], data["alpha"]
    print("FPR — false-positive rate on A/A data vs the chosen alpha=%.0f%%" % (100 * a))
    print("-" * 54)
    print("  correct pipeline (se=%.1f):  %.0f%%" % (se, 100 * false_positive_rate(diffs, se, zc)))
    print("  broken pipeline  (se=%.1f):  %.0f%%" % (bse, 100 * false_positive_rate(diffs, bse, zc)))
    print("-" * 54)
    print("  the correct rate sits near alpha; the broken rate is far above it")


def check(data):
    print("SELF-TEST — a correct pipeline's A/A false-positive rate matches alpha; a too-small variance inflates it far above")
    print("-" * 116)
    diffs, se, bse, zc, a = data["differences"], data["se"], data["broken_se"], data["z_critical"], data["alpha"]

    correct_fpr = false_positive_rate(diffs, se, zc)
    broken_fpr = false_positive_rate(diffs, bse, zc)

    aa_has_no_true_effect = True  # arms are identical by construction
    print("  the arms are identical, so any significance is a false positive = %s" % aa_has_no_true_effect)

    correct_fpr_near_alpha = correct_fpr <= a + 1e-9
    print("  correct pipeline's false-positive rate is at or below alpha = %s (%.0f%% vs %.0f%%)"
          % (correct_fpr_near_alpha, 100 * correct_fpr, 100 * a))

    broken_inflates_z = all(abs(z_score(d, bse)) >= abs(z_score(d, se)) for d in diffs)
    print("  the broken (smaller) se inflates every z score = %s" % broken_inflates_z)

    broken_fpr_above_alpha = broken_fpr > a
    print("  broken pipeline's false-positive rate exceeds alpha = %s (%.0f%%)" % (broken_fpr_above_alpha, 100 * broken_fpr))

    aa_detects_broken = broken_fpr > correct_fpr
    print("  the A/A test reveals the broken pipeline (higher FPR) = %s" % aa_detects_broken)

    ok = (aa_has_no_true_effect and correct_fpr_near_alpha and broken_inflates_z
          and broken_fpr_above_alpha and aa_detects_broken)
    print("-" * 116)
    print("SELF-TEST %s  aa_has_no_true_effect=%s  correct_fpr_near_alpha=%s  broken_inflates_z=%s  broken_fpr_above_alpha=%s  aa_detects_broken=%s"
          % ("PASS" if ok else "FAIL", aa_has_no_true_effect, correct_fpr_near_alpha,
             broken_inflates_z, broken_fpr_above_alpha, aa_detects_broken))
    return ok


def main():
    p = argparse.ArgumentParser(description="A/A test: run an A/A test -- both arms identical -- to validate the experiment pipeline before trusting A/B results, because with no real effect a correct pipeline's false-positive rate equals alpha, and a rate far above alpha exposes a broken pipeline (usually an underestimated variance) that would otherwise manufacture significant A/B wins from noise.")
    p.add_argument("--tests", action="store_true")
    p.add_argument("--fpr", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("A/A tests=%d  se=%.1f  broken_se=%.1f  alpha=%.2f  file=%s  (these are a fixture)"
          % (len(data["differences"]), data["se"], data["broken_se"], data["alpha"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.tests:
        tests_view(data)
    elif args.fpr:
        fpr_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
