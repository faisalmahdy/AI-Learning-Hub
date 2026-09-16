#!/usr/bin/env python3
"""The base-rate fallacy: a 99% detector that is mostly wrong when it fires.

A detector with 99% sensitivity and 95% specificity sounds excellent, and on a
balanced test set it is. Point it at a population where the thing it detects is rare
-- 1% prevalence -- and something breaks that no amount of detector quality fixes: of
everything it flags, only 17% are real. The other 83% are false alarms, because 5% of
a huge negative population dwarfs 99% of a tiny positive one. This is the base-rate
fallacy, and it governs every rare-event classifier: fraud, disease screening,
content moderation, anomaly detection. Precision is not a property of the detector; it
is a property of the detector AND the prevalence.

There is a second trap alongside it: accuracy. When positives are 1% of the
population, a detector that flags NOTHING is 99% accurate -- better, by accuracy, than
the real detector that actually finds the positives. Accuracy rewards predicting the
majority class, so on rare events it is not just uninformative, it actively prefers a
useless model. This measures the confusion matrix, the precision the base rate
allows, and the accuracy trap.

  --matrix      the confusion matrix and every rate for the base scenario
  --sweep       precision (PPV) as prevalence rises -- the detector never changes
  --accuracy    the real detector vs a flag-nothing baseline, by accuracy and by recall
  --check       PPV from the matrix; accuracy prefers the useless model; PPV << sensitivity

Stdlib only. Deterministic.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "screen.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the confusion matrix

def confusion(population, prevalence, sensitivity, specificity):
    """Return TP, FN, FP, TN for a detector on this population and prevalence."""
    positives = population * prevalence
    negatives = population - positives
    tp = positives * sensitivity
    fn = positives - tp
    tn = negatives * specificity
    fp = negatives - tn
    return tp, fn, fp, tn


def precision(tp, fp):
    """PPV: of everything flagged, the fraction that is truly positive."""
    return tp / (tp + fp) if (tp + fp) else 0.0


def recall(tp, fn):
    return tp / (tp + fn) if (tp + fn) else 0.0


def accuracy(tp, fn, fp, tn):
    return (tp + tn) / (tp + fn + fp + tn)


# ----------------------------------------------------------------- printing

def matrix_view(data):
    tp, fn, fp, tn = confusion(data["population"], data["prevalence"], data["sensitivity"], data["specificity"])
    print("MATRIX — %d people, %.0f%% prevalence, %.0f%% sensitive, %.0f%% specific"
          % (data["population"], 100 * data["prevalence"], 100 * data["sensitivity"], 100 * data["specificity"]))
    print("-" * 66)
    print("  true positives  (real, flagged)   = %6.0f" % tp)
    print("  false negatives (real, missed)    = %6.0f" % fn)
    print("  false positives (fine, flagged)   = %6.0f" % fp)
    print("  true negatives  (fine, cleared)   = %6.0f" % tn)
    print("-" * 66)
    print("  precision (PPV) = %.1f%%  <- of everything flagged, this fraction is real"
          % (100 * precision(tp, fp)))
    print("  recall          = %.1f%%   accuracy = %.1f%%"
          % (100 * recall(tp, fn), 100 * accuracy(tp, fn, fp, tn)))


def sweep_view(data):
    print("SWEEP — same detector (99%/95%), precision as prevalence rises")
    print("-" * 66)
    print("  prevalence   flagged   true   false   precision")
    for prev in data["sweep_prevalences"]:
        tp, fn, fp, tn = confusion(data["population"], prev, data["sensitivity"], data["specificity"])
        print("  %-11s  %7.0f  %5.0f  %6.0f   %.1f%%"
              % ("%.1f%%" % (100 * prev), tp + fp, tp, fp, 100 * precision(tp, fp)))
    print("-" * 66)
    print("  the detector is identical at every row; only the base rate moved.")


def accuracy_view(data):
    pop, prev = data["population"], data["prevalence"]
    tp, fn, fp, tn = confusion(pop, prev, data["sensitivity"], data["specificity"])
    # flag-nothing baseline: predicts negative for everyone.
    b_tp, b_fn, b_fp, b_tn = 0.0, pop * prev, 0.0, pop - pop * prev
    print("ACCURACY — the real detector vs a model that flags NOTHING (prevalence %.0f%%)" % (100 * prev))
    print("-" * 66)
    print("  real detector:  accuracy = %.2f%%   recall = %.0f%%   found %.0f of %.0f"
          % (100 * accuracy(tp, fn, fp, tn), 100 * recall(tp, fn), tp, tp + fn))
    print("  flag nothing:   accuracy = %.2f%%   recall = %.0f%%   found 0 of %.0f"
          % (100 * accuracy(b_tp, b_fn, b_fp, b_tn), 100 * recall(b_tp, b_fn), b_fn))
    print("-" * 66)
    print("  by accuracy, the useless model wins -- accuracy rewards the majority class.")


def check(data):
    print("SELF-TEST — precision tracks the base rate; accuracy prefers the useless model")
    print("-" * 66)
    pop, prev = data["population"], data["prevalence"]
    tp, fn, fp, tn = confusion(pop, prev, data["sensitivity"], data["specificity"])

    # 1. Precision from the matrix is low despite a high-sensitivity detector.
    ppv = precision(tp, fp)
    ppv_low = ppv < 0.20
    print("  precision is low at 1%% prevalence = %s (%.1f%% flagged are real)" % (ppv_low, 100 * ppv))

    # 2. PPV is far below sensitivity -- the base rate, not the detector, set it.
    base_rate_dominates = ppv < data["sensitivity"] / 4
    print("  precision << sensitivity = %s (%.1f%% vs %.0f%%)"
          % (base_rate_dominates, 100 * ppv, 100 * data["sensitivity"]))

    # 3. The flag-nothing model has HIGHER accuracy than the real detector.
    det_acc = accuracy(tp, fn, fp, tn)
    nothing_acc = (pop - pop * prev) / pop  # all negatives correct, all positives missed
    accuracy_trap = nothing_acc > det_acc
    print("  flag-nothing accuracy beats the detector = %s (%.2f%% > %.2f%%)"
          % (accuracy_trap, 100 * nothing_acc, 100 * det_acc))

    # 4. ...yet flag-nothing finds none of the positives.
    nothing_useless = recall(0.0, pop * prev) == 0.0
    print("  ...but flag-nothing has 0%% recall (finds nothing) = %s" % nothing_useless)

    ok = ppv_low and base_rate_dominates and accuracy_trap and nothing_useless
    print("-" * 66)
    print("SELF-TEST %s  ppv_low=%s  base_rate_dominates=%s  accuracy_trap=%s  nothing_useless=%s"
          % ("PASS" if ok else "FAIL", ppv_low, base_rate_dominates, accuracy_trap, nothing_useless))
    return ok


def main():
    p = argparse.ArgumentParser(description="The base-rate fallacy and the accuracy trap on rare events.")
    p.add_argument("--matrix", action="store_true")
    p.add_argument("--sweep", action="store_true")
    p.add_argument("--accuracy", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("population=%d  prevalence=%.1f%%  sensitivity=%.0f%%  specificity=%.0f%%  file=%s"
          % (data["population"], 100 * data["prevalence"], 100 * data["sensitivity"],
             100 * data["specificity"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.matrix:
        matrix_view(data)
    elif args.sweep:
        sweep_view(data)
    elif args.accuracy:
        accuracy_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
