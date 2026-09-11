"""The LLM judge is a noisy instrument, so a model gap inside its grading noise is not real -- re-grade to shrink it.

An LLM judge does not return the same verdict every time. Grade one answer twice and it can pass once and fail once,
because the judge samples a token stream just like the model under test. That makes every eval score a MEASUREMENT with
its own error, not a fact read off a ruler. Score model A at 0.70 and model B at 0.78 and the 0.08 gap looks like a win
-- but if grading each answer once carries enough judge-to-judge variance that the score of a single model wobbles by
0.10, the 0.08 gap is inside the instrument's noise and could vanish or reverse on a re-grade. The comparison is not
between two models; it is between two noisy readings, and the reading noise came from the grader.

There are two independent noise sources in an eval, and this one is the forgotten half. Sampling different ITEMS moves
the score (the usual confidence interval), but re-running the SAME judge on the SAME items also moves it, and averaging
more items does nothing for grader noise -- only averaging more GRADINGS does. Grade each item R times and average, and
the grader-induced standard error of a model's score shrinks like 1/sqrt(R): four gradings halve it, nine cut it to a
third. So the fix for a gap drowned in grader noise is not a bigger test set; it is more gradings per item, or a less
random judge (lower temperature), until the difference clears the judge's own error band.

On this fixture two models truly differ by 0.08 (0.70 vs 0.78) on 40 items, and the judge injects an average per-grade
variance of 0.20. With a single grading per item the standard error of the DIFFERENCE is 0.10, so the two-sigma noise
band is 0.20 -- far wider than the 0.08 gap, which is therefore unresolvable. Averaging enough gradings per item shrinks
the band below the gap. This computes both.

  --noise    the two scores, the grader-induced SEM of each, and the noise band on their difference at 1 grading
  --average  how the difference's noise band shrinks as 1/sqrt(replicates), and the gradings needed to resolve the gap
  --check    the gap is inside the grader noise at R=1; the SEM shrinks like 1/sqrt(R); enough gradings clear the band

The scores, item count, and grader variance are the fixture; every standard error is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "judgenoise.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def grader_sem(grader_var, n_items, replicates):
    """Grader-induced standard error of one model's mean score: sqrt(per-grade var / (items * gradings))."""
    return math.sqrt(grader_var / (n_items * replicates))


def diff_sem(a, b, n_items, replicates):
    """Standard error of the A-B score difference from grader noise (the two models graded independently)."""
    va = grader_sem(a["grader_var"], n_items, replicates) ** 2
    vb = grader_sem(b["grader_var"], n_items, replicates) ** 2
    return math.sqrt(va + vb)


def noise_band(a, b, n_items, replicates, sigmas=2.0):
    """The +/- band (sigmas * SEM) the difference must clear to be called real, not grader noise."""
    return sigmas * diff_sem(a, b, n_items, replicates)


def min_replicates(a, b, n_items, gap, sigmas=2.0, cap=200):
    """The fewest gradings per item that make the gap clear the noise band."""
    for r in range(1, cap + 1):
        if gap >= noise_band(a, b, n_items, r, sigmas):
            return r
    return None


# ----------------------------------------------------------------- printing

def noise_view(data):
    a, b, n = data["model_a"], data["model_b"], data["n_items"]
    r = data["replicates"]
    gap = b["true_score"] - a["true_score"]
    band = noise_band(a, b, n, r)
    print("NOISE — the model gap against the judge's own grading noise (%d gradings per item)" % r)
    print("-" * 66)
    print("  model A score            = %.3f   grader SEM = %.3f" % (a["true_score"], grader_sem(a["grader_var"], n, r)))
    print("  model B score            = %.3f   grader SEM = %.3f" % (b["true_score"], grader_sem(b["grader_var"], n, r)))
    print("  observed gap  B - A      = %.3f" % gap)
    print("  grader noise band (2sig) = %.3f   -> gap %s the band" % (band, "clears" if gap >= band else "is INSIDE"))
    print("-" * 66)
    print("  the gap is smaller than the noise the judge injects, so a re-grade could erase or reverse it.")


def average_view(data):
    a, b, n = data["model_a"], data["model_b"], data["n_items"]
    gap = b["true_score"] - a["true_score"]
    print("AVERAGE — the difference's noise band shrinks like 1/sqrt(gradings)")
    print("-" * 58)
    print("  gap to resolve = %.3f" % gap)
    for r in (1, 4, 9, 16):
        band = noise_band(a, b, n, r)
        print("  %2d gradings/item -> noise band %.3f   %s" % (r, band, "gap clears it" if gap >= band else "gap buried"))
    need = min_replicates(a, b, n, gap)
    print("-" * 58)
    print("  need %d gradings per item for the gap to clear the two-sigma grader band." % need)


def check(data):
    print("SELF-TEST — the gap is inside the grader noise at one grading; the SEM shrinks like 1/sqrt(R); enough gradings clear it")
    print("-" * 118)
    a, b, n = data["model_a"], data["model_b"], data["n_items"]
    gap = b["true_score"] - a["true_score"]

    gap_positive = gap > 0
    print("  the two models truly differ = %s (gap %.3f)" % (gap_positive, gap))

    buried_at_one = gap < noise_band(a, b, n, 1)
    print("  at 1 grading the gap is inside the grader noise band = %s (%.3f < %.3f)" % (buried_at_one, gap, noise_band(a, b, n, 1)))

    sem1, sem4 = diff_sem(a, b, n, 1), diff_sem(a, b, n, 4)
    sqrt_law = abs(sem1 / sem4 - 2.0) < 1e-9
    print("  quadrupling the gradings halves the SEM (1/sqrt(R)) = %s (%.4f -> %.4f)" % (sqrt_law, sem1, sem4))

    need = min_replicates(a, b, n, gap)
    resolves = gap >= noise_band(a, b, n, need)
    print("  averaging %d gradings per item clears the band = %s (band %.3f <= gap %.3f)" % (need, resolves, noise_band(a, b, n, need), gap))

    perfect_judge_zero_noise = grader_sem(0.0, n, 1) == 0.0 and gap >= noise_band({"grader_var": 0.0}, {"grader_var": 0.0}, n, 1)
    print("  a perfectly consistent judge (grader_var 0) adds no noise and resolves at R=1 = %s" % perfect_judge_zero_noise)

    ok = gap_positive and buried_at_one and sqrt_law and resolves and perfect_judge_zero_noise
    print("-" * 118)
    print("SELF-TEST %s  gap_positive=%s  buried_at_one=%s  sqrt_law=%s  resolves=%s  perfect_judge_zero_noise=%s"
          % ("PASS" if ok else "FAIL", gap_positive, buried_at_one, sqrt_law, resolves, perfect_judge_zero_noise))
    return ok


def main():
    p = argparse.ArgumentParser(description="An LLM judge is a stochastic instrument, so a model gap inside its grading-noise band is not real; average more gradings per item (SEM shrinks like 1/sqrt(R)) or lower the judge's temperature.")
    p.add_argument("--noise", action="store_true")
    p.add_argument("--average", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("n_items=%d  A=%.2f  B=%.2f  grader_var=%.2f  replicates=%d  file=%s  (the setup is a fixture)"
          % (data["n_items"], data["model_a"]["true_score"], data["model_b"]["true_score"],
             data["model_a"]["grader_var"], data["replicates"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.noise:
        noise_view(data)
    elif args.average:
        average_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
