---
id: lrdecay-inter-01
title: Decay the learning rate — or the noise keeps kicking the optimizer around the minimum and it never settles
topic: below-the-prompt
level: intermediate
status: ready
time: 17 min
summary: A constant learning rate is fine for making progress but wrong for finishing. Real training uses noisy gradients — each minibatch estimates the true gradient, off by a random amount — so even sitting exactly at the minimum, the next step is a random kick away. With a fixed rate that kick never shrinks, so the optimizer does not converge; it orbits the minimum inside a "noise ball" whose radius is set by the learning rate, and the loss plateaus at a floor. Decaying the rate shrinks the kicks over training: a cosine schedule starts at the full rate for speed and eases toward zero for precision, so late steps are tiny and the noise ball collapses. On a noisy descent of x² (minimum at 0), a constant rate leaves an average final loss of 0.0259 (stuck in the noise ball) while a cosine decay to near zero leaves 0.0025, about ten times lower.
eli5: Imagine trying to park a shopping cart exactly on a mark, but the floor keeps giving it random shoves. If you keep pushing with big shoves of your own, the cart lands near the mark but the random floor-shoves keep knocking it off — it never settles. If you make your shoves gentler and gentler as you get close, the random knocks matter less and less, and the cart finally comes to rest on the mark. Shrinking the learning rate is making your shoves gentler as training finishes.
---

## Why this module

A learning rate large enough to travel the loss landscape quickly is too large to sit still at the bottom, because the gradient noise that a big step tolerates early keeps knocking the optimizer out of the minimum at the end.

Training never sees the true gradient. Each minibatch gives a noisy estimate — the true direction plus a random error — so the update is a good step plus a random step. Early in training the good step dominates and you make real progress. But approach the minimum and the true gradient shrinks toward zero while the noise does not, so near the bottom the update is almost pure noise: a random kick of size proportional to the learning rate. With the rate held constant, that kick never shrinks. The optimizer cannot come to rest; it orbits the minimum inside a ball whose radius the learning rate sets, and the loss stops improving at a floor well above the true minimum — not because the optimizer failed to find the bottom, but because every step toward the bottom is undone by a random step of the same size back out.

**With noisy gradients a constant learning rate cannot converge to the minimum — the noise kicks the optimizer around inside a ball whose radius the rate sets, so the loss plateaus at a floor above the minimum.**

Decaying the learning rate shrinks the kicks as training goes on. A cosine schedule starts at the full rate — big steps to cross the landscape quickly early — and eases it toward zero by the end, so late steps are tiny and the noise ball collapses to a point. Now the optimizer settles into the minimum instead of orbiting it, and the final loss is far lower. The high rate early buys speed and the low rate late buys precision; a constant rate can have only one. This module descends a noisy loss both ways and shows the decayed schedule reach a loss the constant one cannot.

## Concepts

**Noisy gradients** are the reality of minibatch training: each step's gradient is the true gradient plus a random error, so an update is a good step plus a random step.

**The noise ball** is where a constant-rate optimizer ends up: near the minimum the true gradient vanishes but the noise does not, so the optimizer bounces inside a ball whose radius scales with the learning rate.

**A constant learning rate holds the ball's radius fixed**, so the loss plateaus at a floor set by the rate and cannot improve further, however long you train.

```python filename=modules/below-the-prompt/code/lrdecay-inter-01/lrdecay.py:43-47 COMPLETE
def lr_at(t, steps, lr0, decay):
    """Learning rate at step t: constant lr0, or a cosine schedule from lr0 down to ~0."""
    if not decay:
        return lr0
    return lr0 * 0.5 * (1 + math.cos(math.pi * t / steps))
```

**A cosine (or linear) decay** eases the rate from its full value toward zero, so the noise ball shrinks as training proceeds and the optimizer settles.

**Speed early, precision late.** The high initial rate crosses the landscape fast; the low final rate resolves the minimum. A single constant rate is forced to choose between the two and gets neither fully.

**The learning rate has two jobs — travel far early, settle precisely late — that pull in opposite directions, so a schedule that decays over training beats any constant rate at the final loss.**

<svg role="img" aria-label="Under a constant rate the optimizer bounces in a wide ring around the minimum; under decay the ring shrinks and it settles on the minimum" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">position near the minimum (center dot)</text>
  <text x="8" y="40" fill="var(--s2)" font-size="8">constant</text>
  <circle cx="90" cy="60" r="30" fill="none" stroke="var(--s2)" stroke-width="1" stroke-dasharray="3 3"/>
  <circle cx="90" cy="60" r="2" fill="var(--ink)"/>
  <circle cx="72" cy="50" r="2" fill="var(--s2)"/><circle cx="108" cy="66" r="2" fill="var(--s2)"/><circle cx="95" cy="82" r="2" fill="var(--s2)"/><circle cx="78" cy="72" r="2" fill="var(--s2)"/>
  <text x="66" y="102" fill="var(--muted)" font-size="7">wide noise ball</text>
  <text x="180" y="40" fill="var(--s1)" font-size="8">decayed</text>
  <circle cx="235" cy="60" r="30" fill="none" stroke="var(--grid)" stroke-width="1" stroke-dasharray="2 4"/>
  <circle cx="235" cy="60" r="8" fill="none" stroke="var(--s1)" stroke-width="1"/>
  <circle cx="235" cy="60" r="2" fill="var(--ink)"/><circle cx="238" cy="62" r="2" fill="var(--s1)"/><circle cx="232" cy="58" r="2" fill="var(--s1)"/>
  <text x="205" y="102" fill="var(--muted)" font-size="7">ball collapses to the center</text>
</svg>
^ A constant rate keeps the optimizer scattered in a wide ring around the minimum; decaying the rate shrinks that ring over training until the points cluster on the center.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/lrdecay-inter-01/lrdecay.py

The fixture is a noisy descent of x²: the starting rate, the noise scale, and the run length.

```json filename=modules/below-the-prompt/code/lrdecay-inter-01/lrdecay.json:1-8 COMPLETE
{
  "_meta": "A noisy (SGD-style) descent on the simple loss x^2, whose minimum is at x=0. The true gradient is 2x, but each step uses a NOISY gradient 2x + gaussian(0, sigma) to model the minibatch noise of real training. With a CONSTANT learning rate, the noise keeps kicking x around the minimum and it never settles: it bounces inside a 'noise ball' whose size is set by the learning rate, so the loss plateaus at a floor. DECAYING the learning rate (cosine schedule, from lr0 down to ~0) shrinks the step size over training, so the noise ball shrinks too and x settles much closer to the minimum, reaching a far lower final loss. steps is the run length, lr0 the starting rate, sigma the gradient-noise scale; trials averages over independent noise seeds; window is how many final steps to average the loss over.",
  "steps": 300,
  "lr0": 0.1,
  "sigma": 1.0,
  "trials": 200,
  "window": 30,
  "base_seed": 0
}
```

Each step takes a noisy gradient and applies the scheduled learning rate; the final loss is averaged over the last window of steps.

```python filename=modules/below-the-prompt/code/lrdecay-inter-01/lrdecay.py:50-60 COMPLETE
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
```

Run `--loss` to compare the two schedules' final loss.

```text filename=--loss
LOSS — average final loss over 200 trials (minimum is 0)
------------------------------------------------------------
  constant learning rate:   0.0259   (stuck in the noise ball)
  cosine-decayed rate:      0.0025   (10.2x lower -- settled)
------------------------------------------------------------
  same start, same noise; only the schedule differs, and decay settles closer to 0.
```

Both runs start at the same x, feel the same gradient noise, and use the same initial rate — the only difference is that one holds the rate constant and the other decays it. The constant rate leaves an average final loss of 0.0259: the optimizer reached the neighborhood of the minimum early and then spent the rest of training bouncing inside its noise ball, unable to improve. The cosine decay leaves 0.0025, ten times lower, because as the rate eased toward zero the kicks shrank and x settled toward the true minimum at 0. The decayed run did not find a better minimum; it found the same one more precisely, which the constant rate's undying noise made impossible.

<svg role="img" aria-label="Constant learning rate leaves an average final loss of 0.0259; cosine decay leaves 0.0025, ten times lower" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">average final loss (minimum = 0)</text>
  <line x1="70" y1="20" x2="70" y2="78" stroke="var(--grid)" stroke-width="1"/>
  <line x1="70" y1="78" x2="285" y2="78" stroke="var(--grid)" stroke-width="1"/>
  <rect x="70" y="26" width="200" height="16" fill="var(--s2)"/><text x="74" y="38" fill="var(--panel)" font-size="8">constant: 0.0259 (noise ball)</text>
  <rect x="70" y="50" width="19" height="16" fill="var(--s1)"/><text x="93" y="62" fill="var(--muted)" font-size="8">cosine decay: 0.0025 (settled)</text>
  <text x="70" y="94" fill="var(--muted)" font-size="8">same minimum; decay resolves it 10x more precisely</text>
</svg>
^ The constant-rate bar sits ten times higher than the decayed one, though both descend the same loss — the gap is the noise ball the constant rate never escapes.

## Build

Why does one settle and the other not? Run `--schedule`.

```text filename=--schedule
SCHEDULE — learning rate over training (lr0 0.10)
------------------------------------------------------------
  step        constant   cosine
  0    (  0%)  0.1000     0.1000
  74   ( 25%)  0.1000     0.0857
  149  ( 50%)  0.1000     0.0505
  224  ( 75%)  0.1000     0.0150
  299  (100%)  0.1000     0.0000
------------------------------------------------------------
  constant holds lr0 all the way; cosine eases from lr0 down to nearly 0.
```

The constant schedule holds 0.10 from the first step to the last, so its noise ball is the same size at step 299 as at step 0 — the optimizer is exactly as jittery when it should be settling as when it started. The cosine schedule starts at the same 0.10, matching the constant rate's early speed, then eases through 0.086, 0.050, 0.015 and finally to 0.0000, so by the end the steps are negligible and the noise ball has collapsed. Both explored the landscape at full speed early — the decay costs nothing in the first half — and only the decayed one converts that into a precise landing at the end. The shape (cosine here, linear or step schedules elsewhere) matters less than the fact of easing the rate toward zero.

<svg role="img" aria-label="The constant schedule is a flat line at 0.10; the cosine schedule starts at 0.10 and curves down to 0" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">learning rate over training</text>
  <line x1="30" y1="20" x2="30" y2="90" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="90" x2="285" y2="90" stroke="var(--grid)" stroke-width="1"/><text x="250" y="102" fill="var(--muted)" font-size="7">step →</text>
  <line x1="30" y1="30" x2="270" y2="30" stroke="var(--s2)" stroke-width="2"/><text x="200" y="26" fill="var(--s2)" font-size="7">constant 0.10</text>
  <path d="M30 30 Q150 34 270 88" fill="none" stroke="var(--s1)" stroke-width="2"/><text x="120" y="70" fill="var(--s1)" font-size="7">cosine → 0</text>
  <text x="24" y="34" fill="var(--muted)" font-size="7">0.1</text><text x="26" y="90" fill="var(--muted)" font-size="7">0</text>
  <text x="30" y="106" fill="var(--muted)" font-size="8">both start at 0.10; only the cosine eases toward zero so the noise ball collapses</text>
</svg>
^ The constant line stays high the whole run, keeping the noise ball wide; the cosine curve starts equally high then decays to zero, shrinking the ball to a point by the end.

## Definition of done

The self-test pins it: the decayed schedule reaches a lower final loss by a real margin, the constant rate is flat, and the cosine starts at the full rate and ends near zero.

```python filename=modules/below-the-prompt/code/lrdecay-inter-01/lrdecay.py:101-114 COMPLETE
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
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the constant rate plateaus in a noise ball; decaying the rate settles to a far lower loss
--------------------------------------------------------------------------------------------------------
  the decayed schedule reaches a lower final loss = True (0.0025 < 0.0259)
  the decayed loss is several times lower (a real gap) = True (0.0259 > 5*0.0025)
  the constant schedule holds lr0 throughout = True (0.10)
  the cosine schedule starts at the full rate = True (0.1000)
  the cosine schedule ends near zero = True (0.00000 < 0.0020)
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  decay_lower=True  decay_much_lower=True  constant_is_flat=True  cosine_starts_full=True  cosine_ends_near_zero=True
```

**Done means the settling is proven: with identical starts and noise, the constant rate plateaus at an average final loss of 0.0259 while the cosine decay — full 0.10 at the start, 0.0000 at the end — reaches 0.0025, ten times lower, because the shrinking rate collapsed the noise ball.**

## Boss fight

Decaying to zero minimized the noise ball. Predict what decaying too fast costs, and how this pairs with warmup at the other end of training. It is tempting to decay aggressively from the very first step.

Decay too fast and you trade away the exploration the high rate was for. If the rate collapses early, the optimizer settles precisely — into wherever it happened to be, which may be a poor region it had not finished escaping. The whole point of the high early rate is to travel far and cross past bad local structure before committing; cut it short and you converge quickly to a worse minimum, precisely resolved but in the wrong place. This is why the standard shape keeps the rate high for a while (a plateau or a slow initial descent) and does most of the decay later — cosine, which is flat-ish at both ends, does this naturally. The schedule is balancing the same two jobs: enough time at high rate to find a good basin, then enough decay to settle inside it.

At the other end sits warmup, and the two are complementary halves of the schedule. Warmup ramps the rate UP from near zero over the first steps, because the very first updates — on freshly initialized weights, or with an optimizer whose variance estimates have not yet stabilized — are unreliable, and a full rate there can diverge. Decay ramps the rate DOWN at the end so the optimizer can settle. The canonical large-model schedule is warmup-then-decay: up from zero to the peak over the first few percent of training, then a cosine (or linear) glide back down to near zero. Warmup protects the fragile beginning, the peak buys exploration, and the decay buys the precise landing — three phases of one curve, and dropping any of them leaves loss on the table. The learning rate is not a constant to tune but a trajectory to design.

```python filename=modules/below-the-prompt/code/lrdecay-inter-01/lrdecay.py:56-58 COMPLETE
        grad = 2 * x + r.gauss(0, sigma)
        x -= lr_at(t, steps, lr0, decay) * grad
        losses.append(x * x)
```

**A constant learning rate cannot converge under gradient noise — it orbits the minimum in a ball its rate sizes — so decay the rate toward zero over training to shrink that ball and settle, keeping it high early for exploration; pair the decay with warmup at the start, making the learning rate a designed trajectory (up, hold, down), not a single tuned number.**

## External resources

"SGDR: Stochastic Gradient Descent with Warm Restarts" (Loshchilov and Hutter) — the paper introducing cosine annealing (and warm restarts), the schedule most large training runs now use.

Any large-model training report's learning-rate section (for example the GPT-3, Chinchilla, or Llama papers) — the concrete warmup-then-cosine-decay schedules, peak rates, and decay-to fractions used in practice.

The companion "warm up the learning rate" and "Adam divides each gradient by its own running RMS" modules — warmup is the rising half of the schedule this module's decay completes, and Adam's per-parameter scaling is the other half of how the effective step is set.
