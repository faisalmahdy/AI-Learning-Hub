"""Warm up the learning rate, or a full rate on the steep early gradients overshoots and diverges.

Early in training the gradients are large: the weights are far from any good setting, so the loss surface is
steep. A learning rate is a multiplier on the gradient, and a step is learning_rate times gradient. Apply the
full learning rate to a huge early gradient and the step is enormous -- it overshoots the minimum, lands
somewhere with an even larger gradient, and the next step is bigger still. The updates blow up, the weights go
to infinity or NaN, and training is dead in a handful of steps. The learning rate was not too big in general;
it was too big FOR THE LARGE GRADIENTS THAT EXIST AT THE START.

Warmup ramps the learning rate up from near zero over the first few hundred (here, few) steps, then holds it at
the target. While the gradients are large, the rate is small, so the steps are controlled and the weights move
toward the minimum instead of past it. By the time the rate reaches full target, the gradients have shrunk, so
the full rate is now safe. The same target rate that diverges when applied from step 0 converges when the first
steps are warmed up -- the schedule, not the target, is what changed.

On this fixture gradient descent runs on f(x)=x^4, whose gradient 4x^3 is enormous at the start (x0=3) and tiny
near the minimum. A constant learning rate of 0.1 overshoots immediately: x goes 3 -> -7.8 -> 182 -> diverges.
Warming the rate up over 5 steps keeps every step controlled: x decreases 3 -> 0.84 -> ... -> 0.38, bounded and
converging. This computes both.

  --trajectory   the value of x at each step for the constant rate vs the warmed-up rate
  --schedule     the learning rate at each step: flat at target vs ramping up to it
  --check        the constant rate diverges on the steep start; warmup stays bounded and converges

The starting point, target rate, and warmup length are the fixture; every step is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "warmup.json"
DIVERGED = float("inf")
LIMIT = 1e6


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def grad(x):
    """Gradient of f(x)=x^4: huge far from 0, tiny near it -- like early vs late training gradients."""
    return 4 * x ** 3


def constant_lr(t, target, warmup):
    return target


def warmup_lr(t, target, warmup):
    """Ramp linearly from a small rate up to target over `warmup` steps, then hold."""
    return target * min(1.0, (t + 1) / warmup)


def run(x0, lr_at, target, warmup, steps):
    """Gradient descent; stop and mark diverged if |x| blows past the limit."""
    x, traj = x0, [x0]
    for t in range(steps):
        x = x - lr_at(t, target, warmup) * grad(x)
        if abs(x) > LIMIT:
            traj.append(DIVERGED)
            return traj, True
        traj.append(x)
    return traj, False


def fmt(v):
    return "diverged" if v == DIVERGED else "%.3g" % v


# ----------------------------------------------------------------- printing

def trajectory_view(data):
    x0, target, warmup, steps = data["x0"], data["target_lr"], data["warmup_steps"], data["total_steps"]
    ct, cd = run(x0, constant_lr, target, warmup, steps)
    wt, wd = run(x0, warmup_lr, target, warmup, steps)
    print("TRAJECTORY — x per step on f(x)=x^4 (x0=%.1f, target lr %.2f)" % (x0, target))
    print("-" * 66)
    print("  constant lr:  %s" % "  ".join(fmt(v) for v in ct))
    print("  warmup lr:    %s" % "  ".join(fmt(v) for v in wt))
    print("-" * 66)
    print("  the constant rate blows up on the steep start; warmup stays controlled.")


def schedule_view(data):
    target, warmup, steps = data["target_lr"], data["warmup_steps"], data["total_steps"]
    print("SCHEDULE — learning rate per step")
    print("-" * 66)
    print("  step:      " + "".join("%6d" % t for t in range(steps)))
    print("  constant:  " + "".join("%6.2f" % constant_lr(t, target, warmup) for t in range(steps)))
    print("  warmup:    " + "".join("%6.2f" % warmup_lr(t, target, warmup) for t in range(steps)))
    print("-" * 66)
    print("  warmup climbs to the target over %d steps, then matches the constant rate." % warmup)


def check(data):
    print("SELF-TEST — the constant rate diverges on the steep start; warmup stays bounded and converges")
    print("-" * 100)
    x0, target, warmup, steps = data["x0"], data["target_lr"], data["warmup_steps"], data["total_steps"]
    ct, cd = run(x0, constant_lr, target, warmup, steps)
    wt, wd = run(x0, warmup_lr, target, warmup, steps)

    constant_diverges = cd
    print("  the constant rate diverges = %s (x reaches %s)" % (constant_diverges, fmt(ct[-1])))

    warmup_stays_bounded = not wd
    print("  the warmup rate stays bounded = %s (final x %s)" % (warmup_stays_bounded, fmt(wt[-1])))

    warmup_converges = warmup_stays_bounded and abs(wt[-1]) < x0
    print("  the warmup run moves toward the minimum = %s (|x| %.3g < %.1f)" % (warmup_converges, abs(wt[-1]), x0))

    warmup_early_lr_smaller = warmup_lr(0, target, warmup) < target
    print("  warmup starts below the target rate = %s (%.3f < %.2f)" % (warmup_early_lr_smaller, warmup_lr(0, target, warmup), target))

    warmup_reaches_target = abs(warmup_lr(warmup - 1, target, warmup) - target) < 1e-9
    print("  warmup reaches the full target rate = %s (step %d -> %.2f)" % (warmup_reaches_target, warmup - 1, warmup_lr(warmup - 1, target, warmup)))

    ok = constant_diverges and warmup_stays_bounded and warmup_converges and warmup_early_lr_smaller and warmup_reaches_target
    print("-" * 100)
    print("SELF-TEST %s  constant_diverges=%s  warmup_stays_bounded=%s  warmup_converges=%s  warmup_early_lr_smaller=%s  warmup_reaches_target=%s"
          % ("PASS" if ok else "FAIL", constant_diverges, warmup_stays_bounded, warmup_converges, warmup_early_lr_smaller, warmup_reaches_target))
    return ok


def main():
    p = argparse.ArgumentParser(description="Warm up the learning rate so the large early gradients do not overshoot.")
    p.add_argument("--trajectory", action="store_true")
    p.add_argument("--schedule", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("x0=%.1f  target_lr=%.2f  warmup_steps=%d  total_steps=%d  file=%s  (the schedule is a fixture)"
          % (data["x0"], data["target_lr"], data["warmup_steps"], data["total_steps"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.trajectory:
        trajectory_view(data)
    elif args.schedule:
        schedule_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
