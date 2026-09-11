"""Decay the learning rate, or the noise keeps kicking the optimizer around the minimum and it never settles.

A constant learning rate is fine for making progress but wrong for finishing. Real training uses noisy gradients
-- each minibatch gives an estimate of the true gradient, off by some random amount -- so even sitting exactly at
the minimum, the next step is a random kick away from it. With a fixed learning rate the size of that kick never
shrinks, so the optimizer does not converge to the minimum; it orbits it, bouncing around inside a 'noise ball'
whose radius is set by the learning rate. The loss stops improving at a floor well above the true minimum, not
because the optimizer cannot find the bottom, but because every step it takes toward the bottom is followed by a
random step of the same size back out.

Decaying the learning rate shrinks the kicks over the course of training. A cosine schedule starts at the full
rate -- big steps to travel quickly across the loss landscape early -- and eases it down toward zero by the end,
so late in training the steps are tiny and the noise ball collapses. Now the optimizer settles into the minimum
instead of orbiting it, and the final loss is far lower. The high rate early buys speed; the low rate late buys
precision; a constant rate can have only one of the two. This is why essentially every large training run pairs a
warmup with a decay schedule rather than holding the rate fixed.

On this fixture the loss is x^2 (minimum at 0) descended with noisy gradients. A constant learning rate leaves an
average final loss of 0.0259 -- the optimizer stuck in its noise ball. A cosine decay to near zero leaves 0.0025,
about ten times lower, because the shrinking steps let it settle. This computes both.

  --loss       the average final loss under a constant rate vs a cosine-decayed rate
  --schedule   the learning rate at several points: constant stays flat, cosine eases to ~0
  --check      the constant rate plateaus in a noise ball; decaying the rate settles to a far lower loss

The loss, noise, and schedule are the fixture; every trajectory is computed. Stdlib only.
"""
import argparse
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "lrdecay.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def lr_at(t, steps, lr0, decay):
    """Learning rate at step t: constant lr0, or a cosine schedule from lr0 down to ~0."""
    if not decay:
        return lr0
    return lr0 * 0.5 * (1 + math.cos(math.pi * t / steps))


def final_loss(seed, data, decay):
    """Descend x^2 with noisy gradients; return the mean loss over the last `window` steps."""
    r = random.Random(seed)
    x, losses = 1.0, []
    steps, lr0, sigma = data["steps"], data["lr0"], data["sigma"]
    for t in range(steps):
        grad = 2 * x + r.gauss(0, sigma)
        x -= lr_at(t, steps, lr0, decay) * grad
        losses.append(x * x)
    w = data["window"]
    return sum(losses[-w:]) / w


def avg_final_loss(data, decay):
    """Mean final loss over `trials` independent noise seeds."""
    base, trials = data["base_seed"], data["trials"]
    return sum(final_loss(base + i, data, decay) for i in range(trials)) / trials


# ----------------------------------------------------------------- printing

def loss_view(data):
    const = avg_final_loss(data, decay=False)
    decayed = avg_final_loss(data, decay=True)
    print("LOSS — average final loss over %d trials (minimum is 0)" % data["trials"])
    print("-" * 60)
    print("  constant learning rate:   %.4f   (stuck in the noise ball)" % const)
    print("  cosine-decayed rate:      %.4f   (%.1fx lower -- settled)" % (decayed, const / decayed))
    print("-" * 60)
    print("  same start, same noise; only the schedule differs, and decay settles closer to 0.")


def schedule_view(data):
    steps, lr0 = data["steps"], data["lr0"]
    print("SCHEDULE — learning rate over training (lr0 %.2f)" % lr0)
    print("-" * 60)
    print("  step        constant   cosine")
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        t = int(frac * (steps - 1))
        print("  %-4d (%3.0f%%)  %.4f     %.4f" % (t, 100 * frac, lr_at(t, steps, lr0, False), lr_at(t, steps, lr0, True)))
    print("-" * 60)
    print("  constant holds lr0 all the way; cosine eases from lr0 down to nearly 0.")


def check(data):
    print("SELF-TEST — the constant rate plateaus in a noise ball; decaying the rate settles to a far lower loss")
    print("-" * 104)
    const = avg_final_loss(data, decay=False)
    decayed = avg_final_loss(data, decay=True)
    steps, lr0 = data["steps"], data["lr0"]

    decay_lower = decayed < const
    print("  the decayed schedule reaches a lower final loss = %s (%.4f < %.4f)" % (decay_lower, decayed, const))

    decay_much_lower = const > 5 * decayed
    print("  the decayed loss is several times lower (a real gap) = %s (%.4f > 5*%.4f)" % (decay_much_lower, const, decayed))

    constant_is_flat = lr_at(0, steps, lr0, False) == lr_at(steps - 1, steps, lr0, False) == lr0
    print("  the constant schedule holds lr0 throughout = %s (%.2f)" % (constant_is_flat, lr0))

    cosine_starts_full = abs(lr_at(0, steps, lr0, True) - lr0) < 1e-9
    print("  the cosine schedule starts at the full rate = %s (%.4f)" % (cosine_starts_full, lr_at(0, steps, lr0, True)))

    cosine_ends_near_zero = lr_at(steps - 1, steps, lr0, True) < 0.02 * lr0
    print("  the cosine schedule ends near zero = %s (%.5f < %.4f)" % (cosine_ends_near_zero, lr_at(steps - 1, steps, lr0, True), 0.02 * lr0))

    ok = decay_lower and decay_much_lower and constant_is_flat and cosine_starts_full and cosine_ends_near_zero
    print("-" * 104)
    print("SELF-TEST %s  decay_lower=%s  decay_much_lower=%s  constant_is_flat=%s  cosine_starts_full=%s  cosine_ends_near_zero=%s"
          % ("PASS" if ok else "FAIL", decay_lower, decay_much_lower, constant_is_flat, cosine_starts_full, cosine_ends_near_zero))
    return ok


def main():
    p = argparse.ArgumentParser(description="Decaying the learning rate shrinks SGD's noise ball so the optimizer settles into the minimum instead of orbiting it.")
    p.add_argument("--loss", action="store_true")
    p.add_argument("--schedule", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("steps=%d  lr0=%.2f  sigma=%.1f  trials=%d  file=%s  (the setup is a fixture)"
          % (data["steps"], data["lr0"], data["sigma"], data["trials"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.loss:
        loss_view(data)
    elif args.schedule:
        schedule_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
