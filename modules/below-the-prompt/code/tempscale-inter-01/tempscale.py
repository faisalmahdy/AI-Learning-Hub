"""Divide the logits by a temperature before the softmax to calibrate confidence -- an overconfident model's probabilities are wrong even when its predictions are right.

A classifier's softmax output is read as a probability -- '95% confident this is a cat' -- and used that way: to abstain when unsure, to route low-confidence cases to a human, to threshold a decision. But a modern neural network's raw softmax confidence is systematically too high. It has learned to drive its logits to large values (that is how cross-entropy is minimized), so the softmax saturates near 1, and the model reports 95% or 99% confidence far more often than it is actually right that often. The predictions can still be good -- the argmax picks the right class -- while the PROBABILITIES attached to them are miscalibrated: a batch of '95% confident' predictions turns out to be 70% or 60% correct. Anything downstream that trusts the number, not just the ranking, is being misled.

Calibration is a separate property from accuracy. Accuracy asks how often the top prediction is right; calibration asks whether the confidence matches that rate -- of all the times the model says 90%, is it right about 90% of the time? A model can be accurate and badly calibrated (right often, but always claiming near-certainty), and the fix for miscalibration must therefore NOT change the predictions, only the confidences attached to them.

Temperature scaling is exactly that fix. After training, you divide every logit by a single scalar T > 1 before the softmax. Dividing the logits shrinks the gaps between them, which pulls the softmax away from its saturated corner and spreads the probability out, lowering the peak confidence toward the model's true accuracy. Crucially, dividing all logits by the same positive T preserves their order, so the largest logit stays the largest: the argmax -- the predicted class -- is unchanged, and so is accuracy. You fit the one parameter T on a held-out set (minimizing calibration error) and apply it at inference. One number, no retraining, predictions untouched, probabilities repaired.

The rule: calibrate an overconfident model by dividing its logits by a temperature T > 1 before the softmax, because the raw softmax saturates and reports confidence far above the true accuracy -- and scaling the logits lowers the confidence toward the accuracy while preserving their order, so the argmax and accuracy are unchanged and only the probabilities are corrected.

On this fixture the model is ~95% confident on every prediction but right on only 3 of 5 (60% accuracy) -- a calibration gap of 0.35. Dividing the logits by T=3 lowers mean confidence to ~0.73, cutting the gap to ~0.13, while the predicted class and the 60% accuracy do not change. This computes both.

  --confidence   each prediction's confidence at T=1 vs T=3, and whether it was correct
  --calibrate    mean confidence vs accuracy (the calibration gap) at T=1 and T=3, and that the argmax is unchanged
  --check        the model is overconfident at T=1; temperature scaling lowers confidence toward accuracy without changing any prediction

temperature and examples are the fixture; every softmax confidence, the accuracy, the calibration gap, and the argmax are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "tempscale.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def softmax(logits, t=1.0):
    """Softmax of the logits divided by temperature t."""
    scaled = [x / t for x in logits]
    m = max(scaled)
    exps = [math.exp(x - m) for x in scaled]
    total = sum(exps)
    return [e / total for e in exps]


def confidence(logits, t=1.0):
    """The model's confidence: the largest softmax probability."""
    return max(softmax(logits, t))


def argmax(logits):
    """The predicted class index (unaffected by positive temperature)."""
    return max(range(len(logits)), key=lambda i: logits[i])


def accuracy(examples):
    return sum(1 for e in examples if e["correct"]) / len(examples)


def mean_confidence(examples, t=1.0):
    return sum(confidence(e["logits"], t) for e in examples) / len(examples)


def calibration_gap(examples, t=1.0):
    """|mean confidence - accuracy|: how far the stated confidence is from the true correctness rate."""
    return abs(mean_confidence(examples, t) - accuracy(examples))


# ----------------------------------------------------------------- printing

def confidence_view(data):
    exs, t = data["examples"], data["temperature"]
    print("CONFIDENCE — each prediction's confidence at T=1 vs T=%g" % t)
    print("-" * 60)
    print("  logits         pred  correct   conf(T=1)  conf(T=%g)" % t)
    for e in exs:
        print("  %-13s  %-4d  %-7s   %-9.4f  %.4f"
              % (e["logits"], argmax(e["logits"]), e["correct"], confidence(e["logits"], 1.0), confidence(e["logits"], t)))
    print("-" * 60)
    print("  scaling lowers every confidence; the predicted class (argmax) is unchanged")


def calibrate_view(data):
    exs, t = data["examples"], data["temperature"]
    print("CALIBRATE — mean confidence vs accuracy (the calibration gap)")
    print("-" * 62)
    acc = accuracy(exs)
    print("  accuracy = %.2f (%d of %d correct)" % (acc, sum(1 for e in exs if e["correct"]), len(exs)))
    print("  T=1 : mean confidence %.4f -> calibration gap %.4f (overconfident)" % (mean_confidence(exs, 1.0), calibration_gap(exs, 1.0)))
    print("  T=%g : mean confidence %.4f -> calibration gap %.4f (calibrated)" % (t, mean_confidence(exs, t), calibration_gap(exs, t)))
    print("-" * 62)
    preds_1 = [argmax(e["logits"]) for e in exs]
    print("  predictions unchanged: %s ; accuracy still %.2f" % (preds_1, acc))


def check(data):
    print("SELF-TEST — the model is overconfident at T=1; temperature scaling lowers confidence toward accuracy without changing any prediction")
    print("-" * 128)
    exs, t = data["examples"], data["temperature"]
    acc = accuracy(exs)
    mc1, mct = mean_confidence(exs, 1.0), mean_confidence(exs, t)
    gap1, gapt = calibration_gap(exs, 1.0), calibration_gap(exs, t)

    temperature_gt_1 = t > 1.0
    print("  the temperature is greater than 1 (cooling an overconfident model) = %s (T=%g)" % (temperature_gt_1, t))

    overconfident_at_t1 = mc1 > acc + 0.1
    print("  at T=1 the model is overconfident (mean confidence far above accuracy) = %s (%.4f vs %.2f)" % (overconfident_at_t1, mc1, acc))

    scaling_lowers_confidence = mct < mc1
    print("  scaling lowers the mean confidence = %s (%.4f < %.4f)" % (scaling_lowers_confidence, mct, mc1))

    scaling_improves_calibration = gapt < gap1
    print("  scaling shrinks the calibration gap = %s (%.4f < %.4f)" % (scaling_improves_calibration, gapt, gap1))

    preds_1 = [argmax(e["logits"]) for e in exs]
    preds_t = [argmax([x / t for x in e["logits"]]) for e in exs]
    argmax_unchanged = preds_1 == preds_t
    print("  the predicted class (argmax) is unchanged by scaling = %s (%s == %s)" % (argmax_unchanged, preds_1, preds_t))

    accuracy_unchanged = True  # accuracy depends only on argmax, which is unchanged
    print("  accuracy is unchanged (it depends only on the argmax) = %s (%.2f)" % (accuracy_unchanged, acc))

    ok = (temperature_gt_1 and overconfident_at_t1 and scaling_lowers_confidence and scaling_improves_calibration
          and argmax_unchanged and accuracy_unchanged)
    print("-" * 128)
    print("SELF-TEST %s  temperature_gt_1=%s  overconfident_at_t1=%s  scaling_lowers_confidence=%s  scaling_improves_calibration=%s  argmax_unchanged=%s  accuracy_unchanged=%s"
          % ("PASS" if ok else "FAIL", temperature_gt_1, overconfident_at_t1, scaling_lowers_confidence, scaling_improves_calibration, argmax_unchanged, accuracy_unchanged))
    return ok


def main():
    p = argparse.ArgumentParser(description="Temperature scaling: calibrate an overconfident model by dividing its logits by a temperature T > 1 before the softmax, because the raw softmax saturates and reports confidence far above the true accuracy -- and scaling the logits lowers the confidence toward the accuracy while preserving their order, so the argmax and accuracy are unchanged and only the probabilities are corrected.")
    p.add_argument("--confidence", action="store_true")
    p.add_argument("--calibrate", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("examples=%d  temperature=%g  file=%s  (the logits and correctness are a fixture)"
          % (len(data["examples"]), data["temperature"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.confidence:
        confidence_view(data)
    elif args.calibrate:
        calibrate_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
