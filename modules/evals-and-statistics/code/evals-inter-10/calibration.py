"""Measure calibration, not just accuracy -- two models can be equally accurate and one's confidence is a lie.

A model that outputs a confidence is making a promise: "90% confident" should mean right 90% of the
time. Calibration is whether that promise holds. And it is invisible to accuracy: two models can score
the identical accuracy while one's confidences are honest and the other's are noise. The moment you do
anything with the confidence -- auto-accept above a threshold, route low-confidence cases to a human,
rank by certainty -- an uncalibrated model betrays you, and the accuracy number gave no warning.

The measure is expected calibration error (ECE). Bin the predictions by their reported confidence; in
each bin, compare the average confidence to the actual accuracy of that bin. A calibrated model's
accuracy tracks its confidence bin for bin, so the gaps are near zero. An overconfident model claims
high confidence it has not earned, so its high-confidence bins are far less accurate than they claim.
ECE is the sample-weighted average of those gaps.

On this fixture two models answer the same 20 items with the SAME accuracy, 0.70. Model A is
calibrated: its 0.9-confidence predictions are right 90% of the time and its 0.5 predictions 50%, for
ECE 0.00. Model B says 0.9 on everything but is right only 70%, for ECE 0.20. Accuracy rates them a
tie; calibration shows B's confidence is worthless -- and so auto-accepting at 0.9 gives 90%-correct
answers from A and only 70%-correct from B. This computes accuracy, the per-bin reliability, and ECE.

  --models     the two models, their accuracy, and their confidence spread
  --reliability the per-bin confidence vs accuracy for each model, and its ECE
  --check      accuracy is equal; ECE is not -- and the accept threshold means different things

The predictions are the fixture; every accuracy, bin, and ECE is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "predictions.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def accuracy(preds):
    return sum(1 for p in preds if p["correct"]) / len(preds)


def bins(preds, n_bins):
    """Group predictions into n_bins confidence buckets; return (lo, hi, count, mean_conf, accuracy) each."""
    out = []
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        # last bin is closed on the right so conf==1.0 lands somewhere
        members = [p for p in preds if lo <= p["conf"] < hi or (b == n_bins - 1 and p["conf"] == hi)]
        if not members:
            continue
        mean_conf = sum(p["conf"] for p in members) / len(members)
        acc = accuracy(members)
        out.append((lo, hi, len(members), mean_conf, acc))
    return out


def ece(preds, n_bins):
    """Expected calibration error: sample-weighted mean gap between confidence and accuracy per bin."""
    total = len(preds)
    err = 0.0
    for lo, hi, count, mean_conf, acc in bins(preds, n_bins):
        err += (count / total) * abs(mean_conf - acc)
    return round(err, 4)


def accuracy_above(preds, threshold):
    """Accuracy of just the predictions the model reported at or above the accept threshold."""
    kept = [p for p in preds if p["conf"] >= threshold]
    if not kept:
        return None, 0
    return accuracy(kept), len(kept)


# ----------------------------------------------------------------- printing

def models_view(data):
    print("MODELS — two models on the same 20 items")
    print("-" * 50)
    for name, preds in data["models"].items():
        confs = sorted(set(p["conf"] for p in preds))
        print("  %-16s accuracy %.2f   confidences used: %s" % (name, accuracy(preds), confs))
    print("-" * 50)
    print("  identical accuracy -- accuracy alone rates them a tie.")


def reliability_view(data):
    n_bins = data["n_bins"]
    print("RELIABILITY — per-bin confidence vs accuracy, and ECE")
    print("-" * 58)
    for name, preds in data["models"].items():
        print("  %s (ECE %.2f):" % (name, ece(preds, n_bins)))
        for lo, hi, count, mean_conf, acc in bins(preds, n_bins):
            gap = mean_conf - acc
            print("    conf~%.2f  acc %.2f  n=%-2d  gap %+.2f" % (mean_conf, acc, count, gap))
    print("-" * 58)
    print("  A's accuracy tracks its confidence; B claims 0.9 but delivers 0.70.")


def check(data):
    print("SELF-TEST — equal accuracy, unequal calibration; the accept threshold means different things")
    print("-" * 90)
    n_bins, thr = data["n_bins"], data["accept_threshold"]
    a, b = data["models"]["A_calibrated"], data["models"]["B_overconfident"]

    same_accuracy = accuracy(a) == accuracy(b)
    print("  the two models have identical overall accuracy = %s (%.2f = %.2f)"
          % (same_accuracy, accuracy(a), accuracy(b)))

    ece_a, ece_b = ece(a, n_bins), ece(b, n_bins)
    calibration_differs = ece_b > ece_a + 0.1
    print("  their calibration error is very different = %s (A %.2f vs B %.2f)" % (calibration_differs, ece_a, ece_b))

    a_calibrated = ece_a < 0.05
    print("  model A is well calibrated = %s (ECE %.2f)" % (a_calibrated, ece_a))

    acc_a_thr, n_a = accuracy_above(a, thr)
    acc_b_thr, n_b = accuracy_above(b, thr)
    threshold_lies = acc_b_thr < acc_a_thr
    print("  auto-accepting at %.1f gives worse answers from B = %s (A %.2f vs B %.2f above threshold)"
          % (thr, threshold_lies, acc_a_thr, acc_b_thr))

    ok = same_accuracy and calibration_differs and a_calibrated and threshold_lies
    print("-" * 90)
    print("SELF-TEST %s  same_accuracy=%s  calibration_differs=%s  a_calibrated=%s  threshold_lies=%s"
          % ("PASS" if ok else "FAIL", same_accuracy, calibration_differs, a_calibrated, threshold_lies))
    return ok


def main():
    p = argparse.ArgumentParser(description="Measure calibration, not just accuracy.")
    p.add_argument("--models", action="store_true")
    p.add_argument("--reliability", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("models=%s  accept_threshold=%.1f  n_bins=%d  file=%s  (the predictions are a fixture)"
          % (list(data["models"]), data["accept_threshold"], data["n_bins"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.models:
        models_view(data)
    elif args.reliability:
        reliability_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
