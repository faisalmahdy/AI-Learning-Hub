#!/usr/bin/env python3
"""Can you trust the judge? Measure it against the gold labels before you do.

One LLM judge graded the same 30 answers PASS/FAIL. We have the gold labels
too. This script reports how much the judge agrees with the gold, corrected
for the agreement it would get by luck, plus which way it is biased.

  --confusion    the 2x2 table: where judge and gold agree and disagree
  --agreement    raw agreement, and why it flatters the judge (the stamp)
  --kappa        Cohen's kappa: agreement above chance, and the stamp at 0
  --calibrated   the full report: kappa with a bootstrap CI, the failure-catch
                 rate, and the leniency bias
  --check        re-derive kappa two ways, prove a rubber-stamp judge scores
                 kappa=0 (this catches the balanced-chance bug), seed-determinism

Stdlib only. No network, no API keys, no model calls. The judge column is a
fixture in labels.json, so every run prints identical numbers; the bootstrap
is seeded. Swap labels.json for your own judge's calls and gold labels; that
is the whole exercise.
"""
import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LABELS_FILE = HERE / "labels.json"

SEED = 0
BOOT = 10000


def load_labels():
    data = json.loads(LABELS_FILE.read_text(encoding="utf-8"))
    return data["cases"]


def percentile(sorted_xs, q):
    if not sorted_xs:
        return 0.0
    k = int(round((q / 100.0) * (len(sorted_xs) - 1)))
    return sorted_xs[k]


# ------------------------------------------------------------- the 2x2 table

def confusion(cases):
    """Count the four cells. Returns (both_pass, gold_pass_judge_fail,
    gold_fail_judge_pass, both_fail)."""
    tp = fp = fn = tn = 0   # named from the gold's point of view: 'positive' = PASS
    for c in cases:
        g, j = c["human"], c["judge"]
        if g == "PASS" and j == "PASS":
            tp += 1
        elif g == "PASS" and j == "FAIL":
            fn += 1          # gold passed, judge failed it (a false alarm)
        elif g == "FAIL" and j == "PASS":
            fp += 1          # gold failed, judge passed it (a miss)
        else:
            tn += 1
    return tp, fn, fp, tn


def raw_agreement(cases):
    """Fraction of cases where judge and gold gave the same verdict."""
    same = sum(1 for c in cases if c["human"] == c["judge"])
    return same / len(cases)


# ---------------------------------------------------------- Cohen's kappa

def chance_agreement(cases):
    """p_e: the agreement two raters would reach by luck, from the ACTUAL rate
    at which each says PASS. NOT 0.5 -- that assumes a balanced base rate."""
    n = len(cases)
    gold_pass = sum(1 for c in cases if c["human"] == "PASS") / n
    judge_pass = sum(1 for c in cases if c["judge"] == "PASS") / n
    gold_fail = 1 - gold_pass
    judge_fail = 1 - judge_pass
    return judge_pass * gold_pass + judge_fail * gold_fail


def cohen_kappa(cases):
    p_o = raw_agreement(cases)
    p_e = chance_agreement(cases)
    if p_e >= 1.0:
        return 1.0
    return (p_o - p_e) / (1 - p_e)


def naive_kappa(cases):
    """The balanced-chance bug: assume two verdicts means chance = 0.5.
    Inflates kappa whenever the base rate is skewed. Kept only so --check can
    show it fails the rubber-stamp test the correct one passes."""
    p_o = raw_agreement(cases)
    p_e = 0.5
    return (p_o - p_e) / (1 - p_e)


# ------------------------------------------------------------- bias + recall

def leniency(cases):
    """How many more PASSes the judge hands out than the gold. Positive = the
    judge is lenient (passes answers the gold failed)."""
    judge_pass = sum(1 for c in cases if c["judge"] == "PASS")
    gold_pass = sum(1 for c in cases if c["human"] == "PASS")
    return judge_pass, gold_pass, judge_pass - gold_pass


def failure_catch_rate(cases):
    """Of the answers the gold FAILED, what fraction did the judge also fail?
    This is the number a lenient judge quietly tanks."""
    gold_fail = [c for c in cases if c["human"] == "FAIL"]
    caught = sum(1 for c in gold_fail if c["judge"] == "FAIL")
    return caught, len(gold_fail)


def stamp_cases(cases):
    """A rubber-stamp judge that says PASS to everything, over the same gold."""
    return [{"human": c["human"], "judge": "PASS"} for c in cases]


# ----------------------------------------------------------- bootstrap on kappa

def bootstrap_kappa_ci(cases, rng):
    """Resample the 30 cases with replacement, recompute kappa, 10000 times."""
    n = len(cases)
    boots = []
    for _ in range(BOOT):
        resample = [cases[rng.randrange(n)] for _ in range(n)]
        # a resample can be all-agree or degenerate; guard p_e == 1
        boots.append(cohen_kappa(resample))
    boots.sort()
    return percentile(boots, 2.5), percentile(boots, 97.5)


# ------------------------------------------------------------------- printing

def show_confusion(cases):
    tp, fn, fp, tn = confusion(cases)
    print("CONFUSION (rows = gold, cols = judge)")
    print("-" * 60)
    print("                judge PASS   judge FAIL")
    print("  gold PASS         %2d           %2d      <- %d false alarms" % (tp, fn, fn))
    print("  gold FAIL         %2d           %2d      <- %d misses" % (fp, tn, fp))
    print("-" * 60)
    print("  agree on %d of %d cases" % (tp + tn, len(cases)))
    return tp, fn, fp, tn


def show_agreement(cases):
    p_o = raw_agreement(cases)
    stamp = stamp_cases(cases)
    p_o_stamp = raw_agreement(stamp)
    print("RAW AGREEMENT")
    print("-" * 60)
    print("  judge vs gold                 = %.4f" % p_o)
    print("  always-PASS stamp vs gold     = %.4f  (free, for saying nothing)" % p_o_stamp)
    print("-" * 60)
    print("  the judge's %.3f only looks good until you see the stamp gets" % p_o)
    print("  %.3f for a verdict with no skill in it." % p_o_stamp)
    return p_o, p_o_stamp


def show_kappa(cases):
    p_o = raw_agreement(cases)
    p_e = chance_agreement(cases)
    k = cohen_kappa(cases)
    stamp = stamp_cases(cases)
    print("COHEN'S KAPPA (agreement above chance)")
    print("-" * 60)
    print("  observed agreement p_o        = %.4f" % p_o)
    print("  chance agreement  p_e         = %.4f  (from the real PASS rates)" % p_e)
    print("  kappa = (p_o - p_e)/(1 - p_e) = %.4f" % k)
    print("  same kappa for the stamp      = %.4f  (no skill -> zero, as it must)"
          % cohen_kappa(stamp))
    return k


def show_calibrated(cases):
    tp, fn, fp, tn = confusion(cases)
    p_o = raw_agreement(cases)
    k = cohen_kappa(cases)
    rng = random.Random(SEED)
    lo, hi = bootstrap_kappa_ci(cases, rng)
    jp, gp, lean = leniency(cases)
    caught, total_fail = failure_catch_rate(cases)
    print("CALIBRATION REPORT — judge vs %d gold labels" % len(cases))
    print("-" * 60)
    print("  raw agreement                 = %.4f" % p_o)
    print("  Cohen's kappa                 = %.4f" % k)
    print("  kappa 95%% CI (bootstrap)      = [%.4f, %.4f]  seed=%d, B=%d"
          % (lo, hi, SEED, BOOT))
    print("  failure-catch rate            = %d/%d = %.4f  (gold FAILs the judge caught)"
          % (caught, total_fail, caught / total_fail))
    print("  leniency: judge passes %d, gold passes %d  (+%d, the judge is lenient)"
          % (jp, gp, lean))
    print("-" * 60)
    if k < 0.4:
        band = "poor-to-fair"
    elif k < 0.6:
        band = "moderate"
    elif k < 0.8:
        band = "substantial"
    else:
        band = "near-perfect"
    print("  VERDICT: kappa %.2f is %s, and the judge misses %d of %d bad answers."
          % (k, band, total_fail - caught, total_fail))
    print("  Trust it for triage, not for a released number, and never above its CI.")
    return k, (lo, hi)


def check(cases):
    print("SELF-TEST — cross-derive kappa, prove the stamp scores zero, seed check")
    print("-" * 60)
    # kappa two ways: the formula, and straight off the confusion counts.
    tp, fn, fp, tn = confusion(cases)
    n = len(cases)
    p_o_counts = (tp + tn) / n
    row_pass = (tp + fn) / n       # gold PASS rate
    col_pass = (tp + fp) / n       # judge PASS rate
    p_e_counts = row_pass * col_pass + (1 - row_pass) * (1 - col_pass)
    k_counts = (p_o_counts - p_e_counts) / (1 - p_e_counts)
    k_formula = cohen_kappa(cases)
    print("  kappa via formula             = %.6f" % k_formula)
    print("  kappa via confusion counts    = %.6f" % k_counts)
    agree = abs(k_formula - k_counts) < 1e-9
    print("  routes agree                  = %s" % agree)

    # The assertion that catches the balanced-chance bug.
    stamp = stamp_cases(cases)
    k_stamp_correct = cohen_kappa(stamp)
    k_stamp_naive = naive_kappa(stamp)
    print("  rubber-stamp kappa, correct   = %.4f  (must be 0)" % k_stamp_correct)
    print("  rubber-stamp kappa, p_e=0.5   = %.4f  (the bug: not 0 -> inflated)"
          % k_stamp_naive)
    stamp_ok = abs(k_stamp_correct) < 1e-9

    # Same seed -> identical CI.
    lo1, hi1 = bootstrap_kappa_ci(cases, random.Random(SEED))
    lo2, hi2 = bootstrap_kappa_ci(cases, random.Random(SEED))
    deterministic = (lo1, hi1) == (lo2, hi2)
    print("  kappa CI run 1                = [%.4f, %.4f]" % (lo1, hi1))
    print("  kappa CI run 2 (same seed)    = [%.4f, %.4f]" % (lo2, hi2))
    print("  deterministic under seed      = %s" % deterministic)
    print("-" * 60)
    ok = agree and stamp_ok and deterministic
    print("SELF-TEST %s  routes_agree=%s  stamp_zero=%s  deterministic=%s"
          % ("PASS" if ok else "FAIL", agree, stamp_ok, deterministic))
    return ok


def main():
    parser = argparse.ArgumentParser(description="Calibrate an LLM judge against gold labels.")
    parser.add_argument("--confusion", action="store_true")
    parser.add_argument("--agreement", action="store_true")
    parser.add_argument("--kappa", action="store_true")
    parser.add_argument("--calibrated", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    cases = load_labels()
    print("cases=%d  file=%s  judge column is a fixture (no model call)"
          % (len(cases), LABELS_FILE.name))
    print("")

    if args.check:
        return 0 if check(cases) else 1
    if args.confusion:
        show_confusion(cases)
    elif args.agreement:
        show_agreement(cases)
    elif args.kappa:
        show_kappa(cases)
    elif args.calibrated:
        show_calibrated(cases)
    else:
        parser.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
