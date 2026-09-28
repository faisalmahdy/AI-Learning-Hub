"""Divide each gradient by its own running RMS, or one learning rate is too big for steep params and too small for flat.

Plain SGD multiplies every gradient by one global learning rate, so a parameter's step is proportional to its
gradient's magnitude. That is a problem when different parameters have wildly different gradient scales -- and in
a deep network they do: some directions are steep (large gradients), some flat (tiny gradients). Pick a learning
rate large enough to make progress on the flat directions and it is far too large for the steep ones, which
overshoot and diverge. Pick one small enough to keep the steep directions stable and the flat ones barely move.
No single scalar suits both, so SGD makes you tune the learning rate to the worst-behaved direction and crawl
everywhere else.

Adam gives each parameter its own effective step by dividing its gradient by a running estimate of that gradient's
root-mean-square. It keeps two running averages per parameter: the mean of the gradient (first moment) and the
mean of the gradient squared (second moment). The update is the first moment over the square root of the second,
times the learning rate. For a constant gradient of ANY magnitude, the second moment converges to the gradient
squared, so the ratio converges to the gradient over its own absolute value -- plus or minus one -- and the step
becomes simply the learning rate, independent of scale. Steep and flat parameters both move about one learning
rate per step. Adam does not remove the learning rate; it normalizes the gradient magnitude out of the step, so
one learning rate finally suits every parameter.

On this fixture the steep gradient is 10 and the flat one is 0.1 -- a 100x scale gap. SGD steps them 0.1 and
0.001, a 100x difference. Adam steps them both by 0.010000, exactly the learning rate, a ratio of 1. This
computes both.

  --steps      the SGD update vs the Adam update for the steep and flat parameters
  --ratio      the ratio of steep-to-flat update magnitude under SGD vs under Adam
  --check      SGD's step scales with the gradient; Adam's step is the learning rate regardless of scale

The gradients and hyperparameters are the fixture; every update is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "adam.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def sgd_update(grad, lr):
    """SGD: the step is the learning rate times the gradient."""
    return lr * grad


def adam_update(grad, data):
    """Adam on a constant gradient: the settled per-step update after `steps` updates."""
    lr, b1, b2, eps, steps = data["lr"], data["beta1"], data["beta2"], data["eps"], data["steps"]
    m = v = 0.0
    upd = 0.0
    for t in range(1, steps + 1):
        m = b1 * m + (1 - b1) * grad
        v = b2 * v + (1 - b2) * grad * grad
        m_hat = m / (1 - b1 ** t)
        v_hat = v / (1 - b2 ** t)
        upd = lr * m_hat / (math.sqrt(v_hat) + eps)
    return upd


# ----------------------------------------------------------------- printing

def steps_view(data):
    steep, flat, lr = data["steep_grad"], data["flat_grad"], data["lr"]
    print("STEPS — per-step update for the steep (grad %.1f) and flat (grad %.1f) parameters" % (steep, flat))
    print("-" * 62)
    print("  optimizer   steep update   flat update")
    print("  SGD         %.5f        %.5f" % (sgd_update(steep, lr), sgd_update(flat, lr)))
    print("  Adam        %.5f        %.5f" % (adam_update(steep, data), adam_update(flat, data)))
    print("-" * 62)
    print("  SGD's step tracks the gradient; Adam's step is ~the learning rate %.3f for both." % lr)


def ratio_view(data):
    steep, flat, lr = data["steep_grad"], data["flat_grad"], data["lr"]
    sgd_ratio = sgd_update(steep, lr) / sgd_update(flat, lr)
    adam_ratio = adam_update(steep, data) / adam_update(flat, data)
    print("RATIO — steep-to-flat update magnitude, SGD vs Adam")
    print("-" * 62)
    print("  gradient ratio steep/flat:  %.0fx" % (steep / flat))
    print("  SGD update ratio:           %.1fx   (steep moves %.0fx farther)" % (sgd_ratio, sgd_ratio))
    print("  Adam update ratio:          %.3fx   (both move about the same)" % adam_ratio)
    print("-" * 62)
    print("  SGD inherits the 100x gradient gap; Adam normalizes it away to ~1x.")


def check(data):
    print("SELF-TEST — SGD's step scales with the gradient; Adam's step is the learning rate regardless of scale")
    print("-" * 104)
    steep, flat, lr = data["steep_grad"], data["flat_grad"], data["lr"]

    sgd_scales_with_grad = abs(sgd_update(steep, lr) / sgd_update(flat, lr) - steep / flat) < 1e-9
    print("  SGD's step ratio equals the gradient ratio = %s (%.0fx)" % (sgd_scales_with_grad, sgd_update(steep, lr) / sgd_update(flat, lr)))

    adam_steep_is_lr = abs(adam_update(steep, data) - lr) < 1e-3 * lr
    print("  Adam's steep update is about the learning rate = %s (%.6f ~ %.3f)" % (adam_steep_is_lr, adam_update(steep, data), lr))

    adam_flat_is_lr = abs(adam_update(flat, data) - lr) < 1e-3 * lr
    print("  Adam's flat update is about the learning rate = %s (%.6f ~ %.3f)" % (adam_flat_is_lr, adam_update(flat, data), lr))

    adam_normalizes = abs(adam_update(steep, data) / adam_update(flat, data) - 1.0) < 1e-3
    print("  Adam's steep and flat updates are the same size = %s (ratio %.4f)" % (adam_normalizes, adam_update(steep, data) / adam_update(flat, data)))

    adam_scale_invariant = abs(adam_update(steep, data) - adam_update(steep * 100, data)) < 1e-6
    print("  Adam gives the same update for a gradient 100x larger = %s" % adam_scale_invariant)

    ok = sgd_scales_with_grad and adam_steep_is_lr and adam_flat_is_lr and adam_normalizes and adam_scale_invariant
    print("-" * 104)
    print("SELF-TEST %s  sgd_scales_with_grad=%s  adam_steep_is_lr=%s  adam_flat_is_lr=%s  adam_normalizes=%s  adam_scale_invariant=%s"
          % ("PASS" if ok else "FAIL", sgd_scales_with_grad, adam_steep_is_lr, adam_flat_is_lr, adam_normalizes, adam_scale_invariant))
    return ok


def main():
    p = argparse.ArgumentParser(description="Adam divides each gradient by its running RMS, normalizing the step so one learning rate suits parameters of any gradient scale.")
    p.add_argument("--steps", action="store_true")
    p.add_argument("--ratio", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("steep_grad=%.1f  flat_grad=%.1f  lr=%.3f  steps=%d  file=%s  (the gradients are a fixture)"
          % (data["steep_grad"], data["flat_grad"], data["lr"], data["steps"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.steps:
        steps_view(data)
    elif args.ratio:
        ratio_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
