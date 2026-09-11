---
id: warmup-inter-01
title: Warm up the learning rate — or a full rate on the steep early gradients overshoots and diverges
topic: below-the-prompt
level: intermediate
status: ready
time: 19 min
summary: Early in training the gradients are large — the weights are far from any good setting, so the loss surface is steep. A step is learning_rate × gradient, so applying the full learning rate to a huge early gradient makes an enormous step that overshoots, lands somewhere steeper, and takes a bigger step next — the weights blow up to infinity in a handful of steps. The rate was not too big in general; it was too big for the large gradients that exist at the start. Warmup ramps the rate from near zero up to the target over the first steps, so while gradients are large the steps stay small, and by the time the rate is full the gradients have shrunk. On f(x)=x⁴, a constant rate of 0.1 goes x: 3 → −7.8 → 182 → diverges, while warming the rate over 5 steps keeps x decreasing 3 → 0.84 → … → 0.38.
eli5: If you are far from a target and take a giant step, you can leap right over it and land somewhere worse, then leap even farther the next time until you fly off. Better to take tiny steps at first while you are far and the ground is steep, and only lengthen your stride once you are close and things are gentle. Warmup is starting with small steps and growing them.
---

## Why this module

The learning rate that trains a model well once it is underway can destroy it in the first few steps, because the gradients at the start are far larger than the gradients later.

A step of gradient descent moves the weights by learning_rate times the gradient. At the start of training the weights are random and far from any good configuration, so the loss surface is steep and the gradients are big. Multiply a big gradient by the full learning rate and the step is enormous — it overshoots the minimum entirely and lands in a region that is steeper still, so the next gradient is bigger, the next step bigger, and within a handful of iterations the weights are infinity or NaN. Training is dead before it began. The learning rate was tuned for the modest gradients of steady-state training; it is simply too large for the violent gradients of step one.

**A learning rate is safe only relative to the size of the gradients it multiplies, and the early gradients are the largest they will ever be.**

Warmup is the fix: ramp the learning rate from near zero up to the target over the first steps, so the rate is small exactly while the gradients are large. By the time it reaches full target, the weights have settled and the gradients have shrunk, so the full rate is now safe. This module runs gradient descent both ways on a steep toy loss and shows the constant rate diverge while warmup stays controlled.

## Concepts

The **learning rate** scales each step: new weight = old − learning_rate × gradient. The **gradient** is large when the loss is steep, which is the situation at initialization.

The toy loss is **f(x) = x⁴**, whose gradient is 4x³. That gradient is enormous far from the minimum (at x = 3 it is 108) and tiny near it (at x = 0.4 it is about 0.26) — a clean stand-in for the large-early, small-late gradients of real training.

The failure is **overshoot into divergence**. When learning_rate × gradient exceeds roughly twice the distance to the minimum, the step jumps past the minimum to a point farther away, where the gradient is larger, so the next step is larger — a positive feedback loop that runs to infinity. It is not slow drift; it is explosion in a few steps.

**Warmup** is a schedule: learning_rate at step t ramps linearly from a small value up to the target over `warmup` steps, then holds at the target. The schedule changes when the rate is applied, not what the target is.

**Warmup does not lower the learning rate — it delays it, keeping steps small while gradients are large and releasing the full rate once gradients are safe.**

The two danger factors move in opposite directions over training, and warmup shapes the rate to stay under their product.

<svg role="img" aria-label="Gradient magnitude starts high and falls; a constant rate is flat and high early; warmup rises as the gradient falls so their product stays bounded" viewBox="0 0 300 120" width="300" height="120">
  <line x1="30" y1="15" x2="30" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="95" x2="285" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <path d="M40,20 Q90,80 160,88 T285,92" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="45" y="30" fill="var(--s1)" font-size="8">gradient (falls)</text>
  <polyline points="40,82 90,60 140,42 190,30 285,30" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
  <text x="150" y="55" fill="var(--s2)" font-size="8">warmup rate (rises)</text>
  <text x="60" y="112" fill="var(--muted)" font-size="8">small rate × big gradient early, big rate × small gradient late</text>
</svg>
^ The gradient is largest at the start and decays; warmup makes the rate smallest at the start and rise, so the step size (their product) never spikes the way a flat rate's does.

The key insight is that the same target rate is fine later and fatal early. The problem is purely the pairing of a full rate with the first, largest gradients, and warmup breaks exactly that pairing.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/warmup-inter-01/warmup.py

The fixture is a starting point, a target rate, and a warmup length.

```json filename=modules/below-the-prompt/code/warmup-inter-01/warmup.json:1-6 COMPLETE
{
  "_meta": "Gradient descent on the toy loss f(x) = x^4 (minimum at 0), whose gradient 4x^3 is HUGE far from the minimum and tiny near it -- a stand-in for the large gradients at the start of training. x0 is the starting point (far out, steep). target_lr is the full learning rate. warmup_steps is how many steps a warmup schedule takes to ramp the learning rate linearly from a small value up to target_lr. total_steps is how long to run. The question: does a full learning rate from step 0 survive the steep start?",
  "x0": 3.0,
  "target_lr": 0.1,
  "warmup_steps": 5,
  "total_steps": 8
}
```

The gradient is huge far out; the two schedules differ only in the rate they return at each step; the run loop steps and flags divergence.

```python filename=modules/below-the-prompt/code/warmup-inter-01/warmup.py:42-65 COMPLETE
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
```

The trajectory view runs both schedules from the same start and prints x at every step.

```python filename=modules/below-the-prompt/code/warmup-inter-01/warmup.py:74-83 COMPLETE
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
```

Run `--trajectory` and watch x under each schedule.

```text filename=--trajectory
TRAJECTORY — x per step on f(x)=x^4 (x0=3.0, target lr 0.10)
------------------------------------------------------------------
  constant lr:  3  -7.8  182  diverged
  warmup lr:    3  0.84  0.745  0.646  0.56  0.49  0.443  0.408  0.381
------------------------------------------------------------------
  the constant rate blows up on the steep start; warmup stays controlled.
```

The constant rate is dead in three steps: 3 overshoots to −7.8 (past the minimum and farther out), which overshoots to 182, which overflows. The warmup rate takes a controlled first step to 0.84 — already close to the minimum — and then decreases smoothly toward zero. Same loss, same target rate; only the first few steps' rate differed.

<svg role="img" aria-label="Constant learning rate sends x to 3, -7.8, 182, then off the chart; warmup keeps x descending from 3 toward 0" viewBox="0 0 300 140" width="300" height="140">
  <line x1="30" y1="70" x2="285" y2="70" stroke="var(--grid)" stroke-width="1"/>
  <text x="5" y="73" fill="var(--muted)" font-size="8">x=0</text>
  <polyline points="40,45 90,120 140,15" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="145" y="15" fill="var(--s1)" font-size="8">constant → ∞</text>
  <circle cx="40" cy="45" r="2.5" fill="var(--s1)"/><circle cx="90" cy="120" r="2.5" fill="var(--s1)"/><circle cx="140" cy="15" r="2.5" fill="var(--s1)"/>
  <polyline points="40,45 90,64 140,66 190,67 240,68 275,68" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
  <text x="200" y="62" fill="var(--s2)" font-size="8">warmup → 0</text>
  <circle cx="40" cy="45" r="2.5" fill="var(--s2)"/><circle cx="90" cy="64" r="2.5" fill="var(--s2)"/>
  <text x="90" y="135" fill="var(--muted)" font-size="8">step →  (constant oscillates wider each step; warmup settles)</text>
</svg>
^ The constant-rate points swing to ever-larger magnitude and leave the chart; the warmup points step down toward zero and stay there.

## Build

Why did warmup survive the same target rate? Run `--schedule`.

```text filename=--schedule
SCHEDULE — learning rate per step
------------------------------------------------------------------
  step:           0     1     2     3     4     5     6     7
  constant:    0.10  0.10  0.10  0.10  0.10  0.10  0.10  0.10
  warmup:      0.02  0.04  0.06  0.08  0.10  0.10  0.10  0.10
------------------------------------------------------------------
  warmup climbs to the target over 5 steps, then matches the constant rate.
```

The constant schedule applies 0.10 at step 0, when the gradient is 108, for a step of about 10.8 — a wild overshoot. The warmup schedule applies 0.02 at step 0, for a controlled step of about 2.2, landing near the minimum where gradients are small. It then ramps — 0.04, 0.06, 0.08 — reaching the full 0.10 at step 4, by which point x is already near the minimum and 0.10 is perfectly safe. Both end at the identical target rate; warmup only changed the first four steps.

<svg role="img" aria-label="The constant rate is flat at 0.10; the warmup rate ramps from 0.02 up to 0.10 over five steps then holds" viewBox="0 0 300 120" width="300" height="120">
  <line x1="30" y1="15" x2="30" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="95" x2="285" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <text x="5" y="30" fill="var(--muted)" font-size="8">0.10</text>
  <line x1="30" y1="28" x2="285" y2="28" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="200" y="24" fill="var(--s1)" font-size="8">constant (flat)</text>
  <polyline points="40,82 75,68 110,54 145,40 180,28 215,28 250,28 280,28" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
  <text x="45" y="78" fill="var(--s2)" font-size="8">warmup ramps</text>
  <text x="120" y="112" fill="var(--muted)" font-size="8">small rate while gradients are large, full rate once they shrink</text>
</svg>
^ Warmup's rate is low exactly across the first steps, where the constant rate's full value multiplies a huge gradient into an overshoot; both converge to the same target afterward.

## Definition of done

The self-test pins the divergence and the fix: the constant rate diverges, the warmup rate stays bounded and moves toward the minimum, its early rate is below target, and it does reach the full target.

```python filename=modules/below-the-prompt/code/warmup-inter-01/warmup.py:104-116 COMPLETE
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
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the constant rate diverges on the steep start; warmup stays bounded and converges
----------------------------------------------------------------------------------------------------
  the constant rate diverges = True (x reaches diverged)
  the warmup rate stays bounded = True (final x 0.381)
  the warmup run moves toward the minimum = True (|x| 0.381 < 3.0)
  warmup starts below the target rate = True (0.020 < 0.10)
  warmup reaches the full target rate = True (step 4 -> 0.10)
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  constant_diverges=True  warmup_stays_bounded=True  warmup_converges=True  warmup_early_lr_smaller=True  warmup_reaches_target=True
```

**Done means the divergence is exhibited, not asserted: the same target rate of 0.10 sends x to infinity from step 0 but leaves it bounded and decreasing when the first steps are warmed up.**

## Boss fight

Warmup saved the run here. Predict whether you could get the same safety by just lowering the target rate to 0.02 permanently instead of warming up. It is tempting to think a small rate everywhere is simpler and just as good.

It is safe but slow, and that trade is why warmup exists. A permanent 0.02 never overshoots, but once the gradients shrink, 0.02 crawls — it would take many more steps to reach the minimum than 0.10 does, and real training runs are long and expensive. Warmup gets the safety of a small early rate and the speed of a large steady-state rate, by using each where it belongs. Lowering the target throws away the speed to buy the safety; warmup buys both. This is also why warmup is usually paired with a decay schedule afterward — small, then full, then tapering as you fine-tune near the optimum.

The mirror-image mistake is warming up for too few steps or too many. Too few and the rate is still climbing while gradients are still large — you overshoot late instead of early. Too many and you waste a long stretch of training at a needlessly small rate. The warmup length is a knob tuned to how long the gradients stay large, which depends on the model and the initialization; it is not a fixed constant.

```python filename=modules/below-the-prompt/code/warmup-inter-01/warmup.py:51-53 COMPLETE
def warmup_lr(t, target, warmup):
    """Ramp linearly from a small rate up to target over `warmup` steps, then hold."""
    return target * min(1.0, (t + 1) / warmup)
```

**Warm the learning rate up so the small early rate meets the large early gradients and the full rate meets the small later ones — a permanently small rate is safe but slow, and warmup keeps the speed.**

## External resources

Goyal et al., "Accurate, Large Minibatch SGD" (2017) — the paper that popularized learning-rate warmup for large-batch training, with the constant-vs-warmup divergence this module models.

The original Transformer paper, "Attention Is All You Need" (2017), section 5.3 — its learning-rate schedule is warmup followed by inverse-square-root decay, the standard pairing named in the boss fight.

Any deep-learning course's treatment of learning-rate schedules (warmup, cosine decay, one-cycle) — why the rate is a schedule, not a constant, and how warmup and decay divide the training run.
