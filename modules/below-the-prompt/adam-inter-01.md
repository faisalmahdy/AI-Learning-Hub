---
id: adam-inter-01
title: Divide each gradient by its own running RMS — or one learning rate is too big for steep params and too small for flat
topic: below-the-prompt
level: intermediate
status: ready
time: 18 min
summary: Plain SGD multiplies every gradient by one global learning rate, so a parameter's step is proportional to its gradient's magnitude — and in a deep network gradient magnitudes vary wildly across parameters. A learning rate large enough to move the flat directions is far too large for the steep ones (they overshoot), and one small enough to keep the steep directions stable leaves the flat ones crawling. No single scalar suits both. Adam gives each parameter its own effective step by dividing its gradient by a running estimate of that gradient's root-mean-square: for a constant gradient of any magnitude, the second moment converges to the gradient squared, so the update becomes just the learning rate, independent of scale. On a fixture with a steep gradient of 10 and a flat gradient of 0.1 — a 100x gap — SGD steps them 0.1 and 0.001 (100x apart) while Adam steps both by 0.010000, exactly the learning rate.
eli5: Imagine pushing a light cart and a heavy cart with the same shove. The same push sends the light cart flying and barely moves the heavy one — one strength can't suit both. Adam is like measuring how each cart has been responding and adjusting your push so both roll the same distance. It divides out how strong each cart's reaction is, so a single setting finally moves everything by the same useful amount.
---

## Why this module

A single learning rate has to serve every parameter, but the steep parameters want a small step and the flat ones want a large step, so whatever one number you pick is wrong for most of the network.

SGD's update is the learning rate times the gradient, so the step a parameter takes is proportional to its gradient's magnitude. That would be fine if every parameter had a similar gradient scale, but deep networks are not like that: some directions in the loss are steep, with large gradients, and some are flat, with tiny ones, and the ratio between them can be orders of magnitude. Now the single learning rate is trapped. Set it large enough that the flat parameters make progress, and the steep ones take enormous steps, overshoot the minimum, and diverge. Set it small enough that the steep parameters stay stable, and the flat ones barely move and training crawls. You are forced to tune to the worst-behaved direction and accept slow progress everywhere else.

**SGD's step is proportional to the gradient magnitude, so with one global learning rate the steep parameters overshoot or the flat ones crawl — no single scalar suits gradients that span orders of magnitude.**

Adam breaks the coupling by giving each parameter its own effective step. It tracks two running averages per parameter — the mean of the gradient and the mean of the gradient squared — and divides the first by the square root of the second. For a constant gradient of any size, the second moment converges to the gradient squared, so the ratio converges to the gradient over its own magnitude, plus or minus one, and the step becomes simply the learning rate, independent of scale. Steep and flat parameters both move about one learning rate per step. This module computes the SGD and Adam updates for a steep and a flat parameter and shows Adam normalize the 100x gap to nothing.

## Concepts

The **gradient magnitude** varies enormously across a network's parameters — steep directions have large gradients, flat ones have tiny gradients — and their ratio can be many orders of magnitude.

**SGD's step is the learning rate times the gradient**, so it inherits that variation directly: a parameter with a 100x larger gradient takes a 100x larger step.

```python filename=modules/below-the-prompt/code/adam-inter-01/adam.py:44-46 COMPLETE
def sgd_update(grad, lr):
    """SGD: the step is the learning rate times the gradient."""
    return lr * grad
```

**The first and second moments** are running averages of the gradient and of the gradient squared. The second moment estimates the gradient's root-mean-square per parameter.

**Adam's update** is the first moment over the square root of the second, times the learning rate. Dividing by the RMS cancels the gradient's magnitude, so the step size stops depending on how steep the direction is.

**The result is scale invariance.** A constant gradient produces a step of about the learning rate whether the gradient is 10 or 0.1, so one learning rate finally suits every parameter — Adam does not remove the learning rate, it removes the gradient scale from the step.

**Adam turns one learning rate that had to fit the worst direction into one that fits every direction, by normalizing each parameter's gradient by its own running magnitude before taking the step.**

<svg role="img" aria-label="A steep gradient 10 divided by its RMS 10 gives 1; a flat gradient 0.1 divided by its RMS 0.1 gives 1; both become the same normalized step" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">Adam step = lr × gradient ÷ √(second moment)</text>
  <text x="8" y="40" fill="var(--s2)" font-size="8">steep</text>
  <text x="40" y="40" fill="var(--muted)" font-size="9" font-family="monospace">10 ÷ 10 = 1</text>
  <text x="150" y="40" fill="var(--muted)" font-size="9" font-family="monospace">→ step = lr×1</text>
  <text x="8" y="70" fill="var(--s1)" font-size="8">flat</text>
  <text x="40" y="70" fill="var(--muted)" font-size="9" font-family="monospace">0.1 ÷ 0.1 = 1</text>
  <text x="150" y="70" fill="var(--muted)" font-size="9" font-family="monospace">→ step = lr×1</text>
  <text x="20" y="98" fill="var(--muted)" font-size="8">each gradient divided by its own RMS becomes ±1, so both steps are the learning rate</text>
</svg>
^ Dividing each gradient by its own root-mean-square sends both the steep 10 and the flat 0.1 to ±1, so their steps are identical at the learning rate — the magnitude cancels itself.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/adam-inter-01/adam.py

The fixture is a steep and a flat gradient, plus Adam's hyperparameters.

```json filename=modules/below-the-prompt/code/adam-inter-01/adam.json:1-9 COMPLETE
{
  "_meta": "Two parameters with very different but constant gradient magnitudes: a STEEP parameter whose gradient is 10 every step, and a FLAT parameter whose gradient is 0.1 every step. Plain SGD updates each by learning_rate * gradient, so the steep parameter moves 100x farther per step than the flat one — one global learning rate cannot suit both (large enough to move the flat one overshoots the steep one, small enough for the steep one crawls on the flat one). Adam divides each parameter's gradient by a running estimate of its own root-mean-square, so a constant gradient of any size produces an update magnitude of about the learning rate. beta1/beta2 are Adam's decay rates, eps its denominator floor, steps how many updates to run before reporting the settled update.",
  "steep_grad": 10.0,
  "flat_grad": 0.1,
  "lr": 0.01,
  "beta1": 0.9,
  "beta2": 0.999,
  "eps": 1e-8,
  "steps": 50
}
```

Adam keeps the two moments, bias-corrects them, and divides; the settled update is what it converges to on a constant gradient.

```python filename=modules/below-the-prompt/code/adam-inter-01/adam.py:49-60 COMPLETE
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
```

Run `--steps` for each optimizer's per-step update.

```text filename=--steps
STEPS — per-step update for the steep (grad 10.0) and flat (grad 0.1) parameters
--------------------------------------------------------------
  optimizer   steep update   flat update
  SGD         0.10000        0.00100
  Adam        0.01000        0.01000
--------------------------------------------------------------
  SGD's step tracks the gradient; Adam's step is ~the learning rate 0.010 for both.
```

SGD steps the steep parameter by 0.1 and the flat one by 0.001 — a 100x difference that exactly mirrors the 100x gradient gap. To keep the 0.1 step from overshooting you would lower the learning rate, but then the flat parameter's already-tiny 0.001 step shrinks further. Adam steps both by 0.01000, precisely the learning rate. The steep parameter's large gradient was divided out by its large RMS; the flat parameter's small gradient by its small RMS; both land on the same step. One learning rate now moves every parameter by the same useful amount.

<svg role="img" aria-label="SGD steps the steep parameter 0.1 and the flat one 0.001, a 100x gap; Adam steps both 0.01" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="12" fill="var(--muted)" font-size="8">per-step update magnitude (log-ish scale)</text>
  <text x="8" y="34" fill="var(--s2)" font-size="8">SGD</text>
  <rect x="60" y="26" width="200" height="12" fill="var(--s2)"/><text x="263" y="36" fill="var(--muted)" font-size="7">steep 0.1</text>
  <rect x="60" y="42" width="20" height="12" fill="var(--s2)"/><text x="83" y="52" fill="var(--muted)" font-size="7">flat 0.001 (crawls)</text>
  <text x="8" y="80" fill="var(--s1)" font-size="8">Adam</text>
  <rect x="60" y="72" width="80" height="12" fill="var(--s1)"/><text x="143" y="82" fill="var(--muted)" font-size="7">steep 0.01</text>
  <rect x="60" y="88" width="80" height="12" fill="var(--s1)"/><text x="143" y="98" fill="var(--muted)" font-size="7">flat 0.01</text>
  <text x="60" y="114" fill="var(--muted)" font-size="8">SGD's two bars differ 100x; Adam's are identical at the learning rate</text>
</svg>
^ SGD's steep and flat bars differ by 100x, so one learning rate cannot suit both; Adam's two bars are the same length, both equal to the learning rate.

## Build

The ratio makes the normalization exact. Run `--ratio`.

```text filename=--ratio
RATIO — steep-to-flat update magnitude, SGD vs Adam
--------------------------------------------------------------
  gradient ratio steep/flat:  100x
  SGD update ratio:           100.0x   (steep moves 100x farther)
  Adam update ratio:          1.000x   (both move about the same)
--------------------------------------------------------------
  SGD inherits the 100x gradient gap; Adam normalizes it away to ~1x.
```

The gradients differ by 100x, and SGD's updates differ by exactly 100x — it passes the gradient scale straight through into the step. Adam's updates differ by 1.000x: the scale is gone. This is the property that makes Adam robust to how you initialize, scale, or normalize a network — whatever gradient magnitudes each parameter ends up with, Adam divides them out and moves everything at the learning-rate scale. It is why a single default learning rate like 0.001 works across wildly different models and layers, where SGD needs the learning rate re-tuned whenever the gradient scale shifts.

<svg role="img" aria-label="The gradient ratio and SGD update ratio are both 100x; the Adam update ratio is 1x" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">steep-to-flat ratio (want: 1x, not 100x)</text>
  <line x1="70" y1="20" x2="70" y2="80" stroke="var(--grid)" stroke-width="1"/>
  <line x1="70" y1="80" x2="285" y2="80" stroke="var(--grid)" stroke-width="1"/>
  <rect x="70" y="24" width="200" height="14" fill="var(--muted)"/><text x="74" y="35" fill="var(--panel)" font-size="8">gradient gap: 100x</text>
  <rect x="70" y="42" width="200" height="14" fill="var(--s2)"/><text x="74" y="53" fill="var(--panel)" font-size="8">SGD update: 100x (inherits it)</text>
  <rect x="70" y="60" width="4" height="14" fill="var(--s1)"/><text x="78" y="71" fill="var(--muted)" font-size="8">Adam update: 1x (normalized)</text>
  <text x="70" y="96" fill="var(--muted)" font-size="8">SGD keeps the 100x gap; Adam collapses it to a single unit</text>
</svg>
^ The gradient gap and SGD's update gap are both the full 100x bar; Adam's update ratio is a sliver at 1x — the scale has been divided out.

## Definition of done

The self-test pins it: SGD's step ratio equals the gradient ratio, Adam's updates both equal the learning rate, their ratio is 1, and Adam's update is unchanged when the gradient is 100x larger.

```python filename=modules/below-the-prompt/code/adam-inter-01/adam.py:94-107 COMPLETE
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
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — SGD's step scales with the gradient; Adam's step is the learning rate regardless of scale
--------------------------------------------------------------------------------------------------------
  SGD's step ratio equals the gradient ratio = True (100x)
  Adam's steep update is about the learning rate = True (0.010000 ~ 0.010)
  Adam's flat update is about the learning rate = True (0.010000 ~ 0.010)
  Adam's steep and flat updates are the same size = True (ratio 1.0000)
  Adam gives the same update for a gradient 100x larger = True
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  sgd_scales_with_grad=True  adam_steep_is_lr=True  adam_flat_is_lr=True  adam_normalizes=True  adam_scale_invariant=True
```

**Done means the normalization is proven: SGD's steep-to-flat step ratio is the full 100x gradient gap while Adam's is 1.000x, both Adam updates equal the 0.01 learning rate, and Adam returns the same update for a gradient 100x larger — the scale is divided out.**

## Boss fight

Adam's scale invariance came from dividing by the gradient's own RMS. Predict the cost of that division, and whether Adam is therefore always better than SGD. It is tempting to conclude Adam strictly dominates and SGD is obsolete.

The scale invariance that helps also throws information away. By dividing out the gradient magnitude, Adam ignores how large the gradient actually is — a parameter with a strong, informative gradient and one with a weak, noisy gradient get the same-sized step. That normalization speeds early training and makes tuning forgiving, but it can hurt final generalization: on many vision benchmarks well-tuned SGD with momentum reaches a better test accuracy than Adam, because the magnitude information Adam discards carries a useful regularizing signal, and Adam's per-parameter steps can settle into sharper minima. This is why large-model training often uses AdamW (Adam with decoupled weight decay) rather than plain Adam, and why some pipelines switch from Adam early to SGD late. Adam is not strictly better; it trades some final performance for robustness and speed of tuning.

The subtler traps are in the machinery you just implemented. The `eps` in the denominator is not cosmetic: it stops division by zero when a gradient is genuinely tiny, and it sets the largest step a near-zero-gradient parameter can take — too small and dead parameters never move, too large and they get kicked by noise. The bias correction (`1 - beta**t`) matters most in the first steps, when the moments start at zero and would otherwise badly underestimate the true gradient scale; drop it and early updates are wrong. And Adam keeps two extra numbers per parameter, so it costs three times the optimizer memory of SGD — a real budget line for a large model. Adam's robustness is bought with memory, with two hyperparameters you are usually right to leave at their defaults, and with an `eps` and bias correction that are load-bearing, not decoration.

```python filename=modules/below-the-prompt/code/adam-inter-01/adam.py:57-59 COMPLETE
        m_hat = m / (1 - b1 ** t)
        v_hat = v / (1 - b2 ** t)
        upd = lr * m_hat / (math.sqrt(v_hat) + eps)
```

**Adam divides each parameter's gradient by a running estimate of its own RMS, so the step becomes the learning rate regardless of gradient scale and one learning rate suits every parameter — but that scale invariance discards magnitude information (well-tuned SGD can generalize better), costs 2x the optimizer memory, and depends on the eps floor and bias correction being right, so prefer AdamW and keep the defaults.**

## External resources

The paper "Adam: A Method for Stochastic Optimization" (Kingma and Ba) — the original algorithm with the moment estimates, bias correction, and the convergence and hyperparameter analysis.

"Decoupled Weight Decay Regularization" (Loshchilov and Hutter, AdamW) — why L2 weight decay interacts badly with Adam's per-parameter scaling and how decoupling it fixes the generalization gap.

The companion "warm up the learning rate" and "scale the initial weights by 1/√fan_in" modules — warmup tames Adam's early large steps before the moment estimates settle, and initialization sets the gradient scales that Adam then normalizes away.
