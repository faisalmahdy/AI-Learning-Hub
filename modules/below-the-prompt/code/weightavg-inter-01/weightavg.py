"""Evaluate with an average of the weights across the late training steps -- a stochastic weight average or an exponential moving average -- not the weights from the single last step, because SGD with gradient noise and a non-vanishing learning rate orbits the minimum rather than landing on it, so the last iterate is a noisy sample and its average is the center.

Train a model with SGD at a learning rate that does not shrink to zero and there is always gradient noise -- from the mini-batch sampling, from data order -- so the optimizer never converges to a point. It reaches a stationary distribution and then orbits the minimum, each step kicked in a different direction. The loss stops improving on average, but the weights keep moving.

The last iterate is therefore wherever the final kick happened to leave it: one sample from that orbit, off the true minimum by a random amount. Evaluating the last checkpoint measures that noisy point, so the reported score wobbles from step to step for no real reason, and the weights you ship are not the best weights you visited -- just the most recent.

Averaging cancels the noise. The kicks that make the orbit are centered on the minimum, so the average of the late iterates lands near the minimum even though no single iterate does -- the same reason the mean of noisy measurements beats any one measurement. The averaged weights sit lower on the loss than a typical late iterate, and they tend to fall in a flatter region, which generalizes better. Two cheap forms: a stochastic weight average (the plain mean of the iterates after a burn-in) and an exponential moving average (a decaying running average that tracks the recent iterates).

This is a different fix from decaying the learning rate. Decay shrinks the orbit by shrinking every step, which quiets the endpoint but trades away the exploration large steps give and slows progress. Averaging keeps the large steps and their exploration and recovers the center for free, as a cheap side computation that never touches the training trajectory itself. In practice both are used, and averaging is nearly free.

On this fixture SGD orbits the minimum at zero with a large constant step and deterministic noise; the last iterate is well off zero with a real loss, while the tail average and the EMA sit close to zero with far lower loss. This computes all three.

  --trajectory  the last few iterates, showing the orbit around the minimum
  --average     the last iterate vs the tail (SWA) average vs the EMA, and their losses
  --check       the iterate orbits and the last one is off the minimum; the average and EMA are far closer and lower-loss

x0, lr, noise_amp, steps, burn_in, ema_beta are the fixture; the trajectory, the last iterate, the SWA average, the EMA, and their losses are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "weightavg.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def noise(t, amp):
    """A fixed, deterministic per-step gradient noise -- reproducible, centered near zero over time."""
    return amp * math.sin(t * 1.7)


def trajectory(data):
    """SGD on f(x)=x^2 (minimum at 0) with a constant lr and deterministic gradient noise."""
    x = data["x0"]
    lr, amp = data["lr"], data["noise_amp"]
    xs = [x]
    for t in range(data["steps"]):
        grad = 2 * x + noise(t, amp)      # true gradient 2x, plus the step's noise
        x = x - lr * grad
        xs.append(x)
    return xs


def loss(x):
    return x * x


def swa(xs, burn_in):
    """Stochastic weight average: the plain mean of the iterates after a burn-in."""
    tail = xs[burn_in:]
    return sum(tail) / len(tail)


def ema(xs, beta):
    """Exponential moving average of the iterates."""
    e = xs[0]
    for x in xs[1:]:
        e = beta * e + (1 - beta) * x
    return e


# ----------------------------------------------------------------- printing

def trajectory_view(data):
    xs = trajectory(data)
    print("TRAJECTORY — the last 8 iterates (minimum is at 0.0)")
    print("-" * 44)
    for t in range(len(xs) - 8, len(xs)):
        print("  step %-3d  x = %+.4f" % (t, xs[t]))
    print("-" * 44)
    print("  the iterate orbits the minimum; it does not settle on it")


def average_view(data):
    xs = trajectory(data)
    last = xs[-1]
    a = swa(xs, data["burn_in"])
    e = ema(xs, data["ema_beta"])
    print("ESTIMATE — last iterate vs averaged weights")
    print("-" * 48)
    print("  last iterate   x = %+.4f   loss = %.4f" % (last, loss(last)))
    print("  SWA (tail avg) x = %+.4f   loss = %.4f" % (a, loss(a)))
    print("  EMA            x = %+.4f   loss = %.4f" % (e, loss(e)))
    print("-" * 48)
    print("  the average sits near the minimum; the last iterate is a noisy sample off it")


def check(data):
    print("SELF-TEST — the iterate orbits the minimum; the average and EMA are far closer and far lower-loss than the last iterate")
    print("-" * 112)
    xs = trajectory(data)
    last = xs[-1]
    a = swa(xs, data["burn_in"])
    e = ema(xs, data["ema_beta"])

    tail = xs[data["burn_in"]:]
    spread = max(tail) - min(tail)
    iterate_orbits = spread > 0.5
    print("  the iterate orbits (does not converge to a point) = %s (tail spread %.4f)" % (iterate_orbits, spread))

    swa_near_minimum = abs(a) < abs(last)
    print("  the SWA average is closer to the minimum than the last iterate = %s (|%.4f| < |%.4f|)" % (swa_near_minimum, a, last))

    last_iterate_much_worse = loss(last) >= 5 * loss(a)
    print("  the last iterate's loss is many times the average's = %s (%.4f vs %.4f)" % (last_iterate_much_worse, loss(last), loss(a)))

    swa_lower_loss = loss(a) < loss(last)
    print("  the SWA average has lower loss than the last iterate = %s (%.4f < %.4f)" % (swa_lower_loss, loss(a), loss(last)))

    ema_lower_loss = loss(e) < loss(last)
    print("  the EMA also has lower loss than the last iterate = %s (%.4f < %.4f)" % (ema_lower_loss, loss(e), loss(last)))

    ok = (iterate_orbits and swa_near_minimum and last_iterate_much_worse and swa_lower_loss and ema_lower_loss)
    print("-" * 112)
    print("SELF-TEST %s  iterate_orbits=%s  swa_near_minimum=%s  last_iterate_much_worse=%s  swa_lower_loss=%s  ema_lower_loss=%s"
          % ("PASS" if ok else "FAIL", iterate_orbits, swa_near_minimum, last_iterate_much_worse, swa_lower_loss, ema_lower_loss))
    return ok


def main():
    p = argparse.ArgumentParser(description="Weight averaging: evaluate with an average of the weights across the late training steps (SWA or EMA), not the single last step, because SGD with gradient noise and a non-vanishing learning rate orbits the minimum rather than landing on it -- so the last iterate is a noisy sample and its average is the center.")
    p.add_argument("--trajectory", action="store_true")
    p.add_argument("--average", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("x0=%.1f  lr=%.2f  noise_amp=%.1f  steps=%d  burn_in=%d  file=%s  (these are a fixture)"
          % (data["x0"], data["lr"], data["noise_amp"], data["steps"], data["burn_in"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.trajectory:
        trajectory_view(data)
    elif args.average:
        average_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
