---
id: weightavg-inter-01
title: Evaluate with an average of the weights, not the last step — SGD orbits the minimum, so the final iterate is a noisy sample and its average is the center
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: Train with SGD at a learning rate that does not shrink to zero and there is always gradient noise, so the optimizer never converges to a point — it reaches a stationary distribution and orbits the minimum, kicked in a different direction each step. The loss stops improving on average but the weights keep moving, so the last iterate is wherever the final kick left it: one sample from the orbit, off the true minimum by a random amount. Evaluating the last checkpoint measures that noisy point, its score wobbles step to step for no real reason, and the weights you ship are just the most recent, not the best. Averaging cancels the noise: the kicks are centered on the minimum, so the mean of the late iterates lands near it even though no single iterate does — the same reason the mean of noisy measurements beats any one — and the averaged weights sit lower on the loss and in a flatter, better-generalizing region. Two cheap forms are a stochastic weight average (the plain mean of the iterates after a burn-in) and an exponential moving average. This is distinct from decaying the learning rate: decay shrinks the orbit by shrinking every step, trading away exploration; averaging keeps the large steps and recovers the center for free as a side computation. On a fixture where SGD orbits the minimum at zero with a large constant step and deterministic noise, the last iterate lands at 0.1975 (loss 0.0390) while the SWA average is 0.0111 (loss 0.0001) and the EMA 0.0278 (loss 0.0008).
eli5: Imagine trying to stand exactly on a spot on the floor while a crowd keeps bumping you from all sides. You never actually stay on the spot — you are always shoved a little off it, in a different direction each moment. If someone takes a photo at one random instant, you look off the spot, and a different instant would show you off it a different way. But if you mark where you are many times and take the average of all those marks, the average lands right on the spot, because the bumps push you every which way and cancel out. Training a model with noisy steps is like that: the final position is one random shove off the target, and the average of the late positions is the target itself.
---

## Why this module

Training ends and you take the weights from the last step to evaluate and ship. That is the obvious thing to do — the last step is the most trained — and it quietly assumes the optimizer has settled onto the minimum by the end. With stochastic gradient descent at a realistic learning rate, it has not.

The reason is that SGD's gradient is noisy: it is computed on a mini-batch, not the whole dataset, so each step points in a slightly wrong direction, and the size of that error does not go to zero unless the learning rate does. As long as the steps stay large, the optimizer cannot come to rest at the minimum — it reaches the bottom of the bowl and then keeps getting kicked around it, orbiting rather than converging. The average loss flattens out, but the weights keep wandering.

So the last iterate is not "the answer" — it is one snapshot of a moving point, off the true minimum by whatever the final kick happened to be. Ship it and you have shipped a random member of the orbit; evaluate it and the number jiggles from checkpoint to checkpoint for no reason connected to real progress. The best weights you visited are somewhere in the orbit, and the last step is not them.

**SGD with a non-vanishing learning rate does not converge to the minimum; it orbits, so the last iterate is a noisy sample off the minimum — and taking the last checkpoint ships a random member of the orbit rather than the best weights.**

## Concepts

Picture the loss as a bowl and the iterate as a marble in it. With noiseless full-batch descent the marble rolls to the bottom and stops. With noisy SGD at a fixed step size, the marble reaches the bottom and then the noise keeps knocking it up the sides, so it circulates in a cloud around the minimum whose width is set by the noise and the step size. Every checkpoint is one position in that cloud.

<svg role="img" aria-label="A parabola (loss bowl) with several iterate points scattered around the bottom, none exactly at the minimum. The last iterate is marked off to one side; the average of the points sits at the bottom of the bowl, on the minimum." viewBox="0 0 440 150">
<path d="M50 30 Q 220 200 390 30" fill="none" stroke="var(--line)"/>
<line x1="220" y1="20" x2="220" y2="135" stroke="var(--grid)" stroke-dasharray="3 3"/>
<text x="220" y="147" fill="var(--muted)" font-size="8" text-anchor="middle">minimum</text>
<circle cx="185" cy="108" r="3" fill="var(--muted)"/><circle cx="255" cy="108" r="3" fill="var(--muted)"/><circle cx="205" cy="118" r="3" fill="var(--muted)"/><circle cx="240" cy="115" r="3" fill="var(--muted)"/>
<circle cx="270" cy="100" r="4" fill="var(--s2)"/><text x="285" y="98" fill="var(--s2)" font-size="8">last iterate</text>
<circle cx="220" cy="122" r="4" fill="var(--s1)"/><text x="150" y="126" fill="var(--s1)" font-size="8" text-anchor="end">average</text>
</svg>
^ Noisy SGD orbits the bottom of the loss bowl: each iterate is a point in the cloud, the last one off to a side, while the average of the iterates sits at the minimum.

Averaging works for the same reason averaging any noisy measurement works. The kicks that create the orbit have no preferred direction — they push away from the minimum every which way — so they are centered on the minimum, and the mean of many iterates cancels the kicks and lands near the center. No single iterate is at the minimum, but their average is, just as no single noisy thermometer reading is the true temperature but their mean is close to it.

<svg role="img" aria-label="Arrows pointing outward in all directions from a central minimum, representing the noise kicks. A summation shows the arrows cancelling to a near-zero average at the center." viewBox="0 0 440 130">
<circle cx="120" cy="65" r="3" fill="var(--ink)"/>
<line x1="120" y1="65" x2="160" y2="45" stroke="var(--muted)"/><line x1="120" y1="65" x2="150" y2="95" stroke="var(--muted)"/><line x1="120" y1="65" x2="85" y2="50" stroke="var(--muted)"/><line x1="120" y1="65" x2="90" y2="90" stroke="var(--muted)"/><line x1="120" y1="65" x2="120" y2="35" stroke="var(--muted)"/>
<text x="120" y="118" fill="var(--muted)" font-size="8" text-anchor="middle">kicks centered on the minimum</text>
<text x="235" y="68" fill="var(--muted)" font-size="9">average -&gt;</text>
<circle cx="360" cy="65" r="3" fill="var(--ink)"/>
<circle cx="360" cy="65" r="6" fill="none" stroke="var(--s1)"/>
<text x="360" y="118" fill="var(--s1)" font-size="8" text-anchor="middle">cancels to the center</text>
</svg>
^ The orbit's kicks have no preferred direction, so they are centered on the minimum and their average cancels them — the mean of the iterates lands at the center the individual iterates miss.

Two cheap implementations capture this. A stochastic weight average keeps the plain mean of the weights over the late steps, after a burn-in that discards the early transient. An exponential moving average keeps a decaying running average that tracks the recent weights, weighting newer ones more. Both are side computations — they never touch the training trajectory, just accumulate a shadow copy of the weights — and both cost almost nothing, one extra buffer and an update per step. And the averaged point tends to sit not just lower but in a flatter part of the bowl, which is associated with better generalization.

This is a different fix from decaying the learning rate, and it is worth keeping them apart. Decay shrinks the orbit by shrinking every step — the marble is knocked less far — but that trades away the exploration large steps buy and slows late progress to a crawl. Averaging leaves the steps large, keeps the exploration, and recovers the center for free from the trajectory you were already running. In practice both are used together; averaging is nearly free and almost always helps.

**Averaging the late iterates cancels the zero-mean noise of the orbit, so the mean lands at the minimum the individual iterates miss — via a plain tail average (SWA) or an exponential moving average, as a near-free side computation — distinct from LR decay, which shrinks the orbit at the cost of exploration.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/weightavg-inter-01. The fixture is a one-dimensional noisy optimization: a quadratic loss with its minimum at zero, a constant learning rate, and a deterministic per-step gradient noise.

```json filename=modules/below-the-prompt/code/weightavg-inter-01/weightavg.json:3-8 COMPLETE
  "x0": 3.0,
  "lr": 0.25,
  "noise_amp": 1.5,
  "steps": 60,
  "burn_in": 30,
  "ema_beta": 0.9
```

The trajectory is SGD on the quadratic with the true gradient plus the step's noise.

```python filename=modules/below-the-prompt/code/weightavg-inter-01/weightavg.py:38-47 COMPLETE
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
```

The stochastic weight average is the mean of the iterates after the burn-in.

```python filename=modules/below-the-prompt/code/weightavg-inter-01/weightavg.py:54-57 COMPLETE
def swa(xs, burn_in):
    """Stochastic weight average: the plain mean of the iterates after a burn-in."""
    tail = xs[burn_in:]
    return sum(tail) / len(tail)
```

The exponential moving average is a decaying running average of the iterates.

```python filename=modules/below-the-prompt/code/weightavg-inter-01/weightavg.py:60-65 COMPLETE
def ema(xs, beta):
    """Exponential moving average of the iterates."""
    e = xs[0]
    for x in xs[1:]:
        e = beta * e + (1 - beta) * x
    return e
```

Before running it, predict: with a large step and steady noise, the iterate will not settle at zero — it will bounce around it. Run `--trajectory`:

```text filename=weightavg.py --trajectory
TRAJECTORY — the last 8 iterates (minimum is at 0.0)
--------------------------------------------
  step 53   x = +0.0002
  step 54   x = -0.3167
  step 55   x = +0.0814
  step 56   x = +0.2957
  step 57   x = -0.1577
  step 58   x = -0.2551
  step 59   x = +0.2234
  step 60   x = +0.1975
--------------------------------------------
  the iterate orbits the minimum; it does not settle on it
```

The prediction holds. The last eight iterates swing from +0.30 to −0.32 and back — the iterate is orbiting zero, not resting on it, long after the loss has stopped improving. Step 53 happened to land almost exactly on zero, step 56 was off by 0.30; which one you ship is pure luck of when training stopped. The last iterate, step 60, is at +0.1975 — a typical member of the orbit, not a special converged point.

Now compare the last iterate to the two averages. Run `--average`:

```text filename=weightavg.py --average
ESTIMATE — last iterate vs averaged weights
------------------------------------------------
  last iterate   x = +0.1975   loss = 0.0390
  SWA (tail avg) x = +0.0111   loss = 0.0001
  EMA            x = +0.0278   loss = 0.0008
------------------------------------------------
  the average sits near the minimum; the last iterate is a noisy sample off it
```

The averages are dramatically closer to the minimum. The last iterate sits at 0.1975 with a loss of 0.0390; the SWA average is 0.0111, a loss of 0.0001 — nearly four hundred times lower — and the EMA is 0.0278, loss 0.0008. The individual iterates each miss zero by up to 0.3, but their mean is within 0.01 of it, because the up-kicks and down-kicks cancel. Same trajectory, same training run; the only difference is whether you read off the last point or the average of the orbit.

<svg role="img" aria-label="A plot of the iterate over the last training steps, oscillating between about -0.3 and +0.3 around zero, with the last point marked at +0.2. A flat line at the SWA average near 0.01 and another near the EMA at 0.03 run through the middle of the oscillation." viewBox="0 0 440 140">
<line x1="45" y1="70" x2="410" y2="70" stroke="var(--grid)" stroke-dasharray="3 3"/>
<text x="30" y="73" fill="var(--muted)" font-size="8" text-anchor="middle">0</text>
<path d="M60 70 L 95 108 L 130 58 L 165 40 L 200 88 L 235 100 L 270 47 L 305 52 L 340 95 L 375 55" fill="none" stroke="var(--muted)"/>
<circle cx="375" cy="55" r="4" fill="var(--s2)"/><text x="378" y="48" fill="var(--s2)" font-size="8">last iterate</text>
<line x1="45" y1="68" x2="405" y2="68" stroke="var(--s1)"/><text x="150" y="64" fill="var(--s1)" font-size="8">SWA average (near 0)</text>
<text x="220" y="130" fill="var(--muted)" font-size="8" text-anchor="middle">late training steps -&gt;</text>
</svg>
^ The iterate oscillates around zero and the last point is off to one side; the SWA average runs through the center of the oscillation, near the minimum.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that the iterate orbits (the tail has real spread), that the SWA average is closer to the minimum than the last iterate, that the last iterate's loss is many times the average's, that the SWA average has lower loss than the last iterate, and that the EMA does too.

```python filename=modules/below-the-prompt/code/weightavg-inter-01/weightavg.py:102-116 COMPLETE
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
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the iterate ever stopped orbiting or an average ever failed to beat the last iterate:

```text filename=weightavg.py --check
SELF-TEST — the iterate orbits the minimum; the average and EMA are far closer and far lower-loss than the last iterate
----------------------------------------------------------------------------------------------------------------
  the iterate orbits (does not converge to a point) = True (tail spread 0.6360)
  the SWA average is closer to the minimum than the last iterate = True (|0.0111| < |0.1975|)
  the last iterate's loss is many times the average's = True (0.0390 vs 0.0001)
  the SWA average has lower loss than the last iterate = True (0.0001 < 0.0390)
  the EMA also has lower loss than the last iterate = True (0.0008 < 0.0390)
```

**The self-test first confirms the iterate genuinely orbits (a real tail spread), because averaging only helps when there is noise to cancel — then that both averages beat the last iterate, so a pass certifies the win comes from cancelling a real orbit, not from a trajectory that had already converged.**

## Definition of done

You can explain why SGD with a non-vanishing learning rate orbits the minimum instead of converging to it.
You can explain why the last iterate is a noisy sample and why its evaluation score wobbles.
You can explain why averaging the late iterates cancels the noise and lands near the minimum.
You can describe SWA and EMA as cheap side computations and why they need a burn-in or a decay.
You can distinguish weight averaging from learning-rate decay and say why both are used.

## Boss fight

Suppose you average the weights of two independently trained models, or two very different points early in one run. Reason about whether averaging still helps. It can badly hurt: weight averaging works only when the points being averaged lie in the same low-loss basin, so that the straight line between them stays low — the late iterates of one run do, because they are all orbiting one minimum, but two independent runs generally land in different basins, and the midpoint between two basins can sit on a high-loss ridge, giving a model worse than either. This is the linear-mode-connectivity condition: averaging is valid within a basin, not across unrelated solutions. It is also why SWA averages only after a burn-in — the early, far-from-minimum iterates are effectively in a different region and would drag the average off. Model soups that average many fine-tunes work precisely because they start from a shared pretrained initialization, keeping the fine-tunes in one basin. The rule: average points that share a basin; averaging across basins is not guaranteed to mean anything.

Now the trap specific to layers with their own running statistics. If the model has batch-normalization layers, their running mean and variance are not parameters the optimizer updates, so they are not part of the weight average — and the averaged weights are paired with batch-norm statistics that were computed for the individual iterates, not for the average, so they are mismatched and the model can behave badly at inference. The standard fix for SWA is to do one extra pass over the training data with the averaged weights to recompute the batch-norm statistics before evaluating. The general lesson is that "the weights" you average are only the optimizer's parameters; any auxiliary state a layer keeps (normalization statistics, and to a degree the optimizer's own moment estimates) has to be reconciled with the averaged weights separately, or the average is applied to only half the model's state.

**Weight averaging is valid only within one loss basin (linear mode connectivity), so average late iterates of one run or fine-tunes from a shared init, never unrelated solutions or the early transient; and because normalization running statistics are not averaged parameters, recompute them for the averaged weights (an extra data pass) rather than inheriting the iterates'.**

## External resources

Izmailov et al., "Averaging Weights Leads to Wider Optima and Better Generalization" (2018), introduces stochastic weight averaging, the flat-minimum argument, and the batch-norm recomputation step.
Polyak and Juditsky's iterate averaging is the classical result that averaging SGD iterates achieves optimal convergence, and exponential moving averages of weights are standard in modern training (and in diffusion models especially).
Wortsman et al., "Model Soups" (2022), extends averaging to many fine-tuned models from a shared initialization; the topic's own module on learning-rate decay covers the neighboring fix — shrinking the orbit rather than averaging over it.
