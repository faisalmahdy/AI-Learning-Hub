"""Smooth the one-hot target, or cross-entropy has no finite optimum and drives the model to unbounded confidence.

Cross-entropy against a hard one-hot label asks the model for the impossible. The loss H(target, softmax) is
minimized only when the softmax equals the target, and a one-hot target like [1, 0, 0, 0] is a distribution the
softmax can never actually produce: it would need the correct logit infinitely far above the rest. So there is no
finite set of weights that minimizes the loss -- every increase in the correct logit lowers it a little more, all
the way to a gap of infinity. Training never says "confident enough"; it keeps pushing the correct logit up and
the others down, so the weights grow without bound, the model becomes overconfident (its top probability creeps
to 1.0 on everything), and its probabilities stop meaning anything -- a 0.999 that should be 0.9.

Label smoothing replaces the one-hot target with a distribution the softmax can actually reach: put (1-eps) on the
correct class and spread eps uniformly, so every class including the right one gets a finite, nonzero target. Now
the loss is minimized at a FINITE gap -- the gap whose softmax exactly matches the smoothed target -- and at that
point the model's confidence is capped at the target, not driven to 1. The minimum loss is no longer 0 but the
entropy of the smoothed target, which is the price of admitting the label is not perfectly certain. The weights
have a finite resting place, and the top probability stays calibrated.

On this fixture 4 classes, eps=0.1: the hard target's cross-entropy keeps falling as the gap grows (0.74 at gap 1
down toward 0), never bottoming out, with confidence marching to 1.0. The smoothed target bottoms out at gap
3.611 with loss 0.349 (exactly its entropy) and confidence 0.925 (exactly 1-eps+eps/K); push the gap past that and
the smoothed loss RISES again. This computes both.

  --loss       cross-entropy vs the correct-logit gap, hard target vs smoothed, and the confidence at each gap
  --optimum    the smoothed target's finite optimal gap, its loss (= entropy), and its calibrated confidence
  --check      the hard loss never bottoms out; the smoothed loss has a finite minimum at a calibrated confidence

The classes, epsilon, and gaps are the fixture; every loss is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "labelsmoothing.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def softmax(logits):
    m = max(logits)
    ex = [math.exp(l - m) for l in logits]
    s = sum(ex)
    return [e / s for e in ex]


def logits_for(gap, k, correct):
    """The correct class gets logit `gap`, every other class gets 0."""
    return [gap if i == correct else 0.0 for i in range(k)]


def hard_target(k, correct):
    return [1.0 if i == correct else 0.0 for i in range(k)]


def smoothed_target(k, correct, eps):
    """(1-eps) on the correct class, eps spread uniformly (eps/k on every class)."""
    return [(1 - eps) + eps / k if i == correct else eps / k for i in range(k)]


def cross_entropy(target, logits):
    p = softmax(logits)
    return -sum(t * math.log(pi) for t, pi in zip(target, p) if t > 0)


def optimal_gap(k, eps):
    """The gap whose softmax exactly equals the smoothed target: ln(correct_target / other_target)."""
    return math.log(((1 - eps) + eps / k) / (eps / k))


# ----------------------------------------------------------------- printing

def loss_view(data):
    k, c, eps, gaps = data["classes"], data["correct"], data["epsilon"], data["gaps"]
    hard, smooth = hard_target(k, c), smoothed_target(k, c, eps)
    print("LOSS — cross-entropy vs correct-logit gap (%d classes, eps %.1f)" % (k, eps))
    print("-" * 62)
    print("  gap    confidence   hard CE     smoothed CE")
    for g in gaps:
        lg = logits_for(g, k, c)
        print("  %-5.1f  %.4f       %.4f      %.4f" % (g, softmax(lg)[c], cross_entropy(hard, lg), cross_entropy(smooth, lg)))
    print("-" * 62)
    print("  hard CE keeps falling (confidence -> 1); smoothed CE turns back up past its optimum.")


def optimum_view(data):
    k, c, eps = data["classes"], data["correct"], data["epsilon"]
    gstar = optimal_gap(k, eps)
    smooth = smoothed_target(k, c, eps)
    lg = logits_for(gstar, k, c)
    entropy = -sum(t * math.log(t) for t in smooth)
    print("OPTIMUM — the smoothed target's finite optimal gap")
    print("-" * 62)
    print("  optimal gap g*:              %.3f" % gstar)
    print("  loss at g*:                  %.4f   (= entropy of the smoothed target %.4f)" % (cross_entropy(smooth, lg), entropy))
    print("  confidence at g*:            %.4f   (= 1-eps+eps/K, the target, not 1.0)" % softmax(lg)[c])
    print("  hard target's optimal gap:   infinite (loss keeps falling, confidence -> 1.0)")
    print("-" * 62)
    print("  smoothing gives the loss a finite floor and the confidence a finite cap.")


def check(data):
    print("SELF-TEST — the hard loss never bottoms out; the smoothed loss has a finite minimum at a calibrated confidence")
    print("-" * 112)
    k, c, eps = data["classes"], data["correct"], data["epsilon"]
    hard, smooth = hard_target(k, c), smoothed_target(k, c, eps)
    gstar = optimal_gap(k, eps)

    hard_keeps_falling = cross_entropy(hard, logits_for(20, k, c)) < cross_entropy(hard, logits_for(4, k, c))
    print("  hard cross-entropy still falling at a huge gap (no finite optimum) = %s (%.4f < %.4f)" % (hard_keeps_falling, cross_entropy(hard, logits_for(20, k, c)), cross_entropy(hard, logits_for(4, k, c))))

    smoothed_has_minimum = cross_entropy(smooth, logits_for(gstar, k, c)) < cross_entropy(smooth, logits_for(2, k, c)) and cross_entropy(smooth, logits_for(gstar, k, c)) < cross_entropy(smooth, logits_for(20, k, c))
    print("  smoothed cross-entropy is lower at g* than on either side (a real minimum) = %s" % smoothed_has_minimum)

    entropy = -sum(t * math.log(t) for t in smooth)
    optimum_is_entropy = abs(cross_entropy(smooth, logits_for(gstar, k, c)) - entropy) < 1e-9
    print("  the minimum loss equals the smoothed target's entropy = %s (%.4f = %.4f)" % (optimum_is_entropy, cross_entropy(smooth, logits_for(gstar, k, c)), entropy))

    target_conf = (1 - eps) + eps / k
    confidence_calibrated = abs(softmax(logits_for(gstar, k, c))[c] - target_conf) < 1e-9
    print("  confidence at g* equals the target 1-eps+eps/K, not 1 = %s (%.4f = %.4f)" % (confidence_calibrated, softmax(logits_for(gstar, k, c))[c], target_conf))

    hard_more_confident = softmax(logits_for(20, k, c))[c] > target_conf
    print("  the hard target drives confidence above the calibrated target = %s (%.4f > %.4f)" % (hard_more_confident, softmax(logits_for(20, k, c))[c], target_conf))

    ok = hard_keeps_falling and smoothed_has_minimum and optimum_is_entropy and confidence_calibrated and hard_more_confident
    print("-" * 112)
    print("SELF-TEST %s  hard_keeps_falling=%s  smoothed_has_minimum=%s  optimum_is_entropy=%s  confidence_calibrated=%s  hard_more_confident=%s"
          % ("PASS" if ok else "FAIL", hard_keeps_falling, smoothed_has_minimum, optimum_is_entropy, confidence_calibrated, hard_more_confident))
    return ok


def main():
    p = argparse.ArgumentParser(description="Label smoothing replaces the unreachable one-hot target with a finite distribution, giving cross-entropy a finite optimum and calibrated confidence.")
    p.add_argument("--loss", action="store_true")
    p.add_argument("--optimum", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("classes=%d  correct=%d  epsilon=%.1f  gaps=%s  file=%s  (the setup is a fixture)"
          % (data["classes"], data["correct"], data["epsilon"], data["gaps"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.loss:
        loss_view(data)
    elif args.optimum:
        optimum_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
