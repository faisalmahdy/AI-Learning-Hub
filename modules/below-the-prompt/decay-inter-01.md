---
id: decay-inter-01
title: Add weight decay — or the model fits the training noise and the weight lands far from the truth
topic: below-the-prompt
level: intermediate
status: ready
time: 19 min
summary: A model minimizes a loss on training data, and the training signal is always noisy. Minimizing the training loss alone drives the weights to whatever fits that noise exactly — including the part that is not real — so the weight ends up large and specific to the training set and generalizes badly. Nothing in "minimize the training loss" pushes back. Weight decay adds a penalty proportional to the squared weight, λw², so the optimizer pays for large weights and settles for a smaller one that fits training a little worse but generalizes better. For a one-weight model the balance is exact: fitting a target t under decay λ lands the weight at t/(1+λ). On a fixture where the noisy target is 12 but the weight should be 6, no decay lands on 12 (noise fully fit, test error 36); λ=1 lands on 6 (test error 0); λ=4 lands on 2.4 (underfit, test error 12.96) — a U-shape with the best generalization at a moderate λ.
eli5: If you tried to draw a straight road by connecting every bump and pothole in a rough survey, your road would zig-zag to match noise that isn't really there. Weight decay is a gentle rule that says "keep it simple unless the data really insists," so your line stays smooth and matches the real road better — even though it fits the bumpy survey slightly worse.
---

## Why this module

Fitting the training data as well as possible is the wrong goal, because the training data contains noise, and a model that fits the noise has learned something false.

The optimizer minimizes the loss on the examples it is given. Those examples are noisy — measurement error, sampling luck, label mistakes — so the target the loss points at is the true signal plus noise. Minimize that loss alone and the weights move to fit all of it, noise included. The result is a weight that is larger and more specific than the real relationship warrants: it nails the training set and misses on new data, because it memorized the wobble instead of the trend. The training loss cannot tell you this is happening — from its point of view, fitting the noise is success.

**Minimizing training loss chases the noise as eagerly as the signal, so the best training fit is often a worse model.**

Weight decay adds a counterweight: a penalty proportional to the squared weight, λw², so a large weight has to earn its size against a cost. Each gradient step now pulls the weight toward zero unless the data pulls back hard enough, so the model settles for a smaller weight that fits training slightly worse and generalizes better. This module fits a one-weight model at several decay strengths and shows the generalization U-shape.

## Concepts

The **training loss** here is (w − t)², driving the weight toward the noisy training target t. The **test error** is (w − true)², measuring the weight against the value that actually generalizes.

**Weight decay** adds λw² to the loss, where λ is the decay strength. The combined loss is (w − t)² + λw², and its gradient carries an extra 2λw term that pushes the weight toward zero every step.

For this one-weight model the minimum has a **closed form**: t/(1+λ). At λ = 0 the weight is t — the noisy target, fully fit. As λ grows, the factor 1/(1+λ) shrinks the weight toward zero. The decay does not know which part of t is signal and which is noise; it simply shrinks, and the bet is that the true relationship is smaller and gentler than the noisy data suggests — usually a good bet.

The strength λ is a **dial with a sweet spot**. Too little and the weight fits the noise (overfitting). Too much and the weight is crushed below even the true value (underfitting), throwing away real signal. The test error traces a U: high at λ = 0, lowest at a moderate λ, high again as λ grows.

**Weight decay shrinks the weight by 1/(1+λ) toward zero, trading a worse training fit for a smaller weight — and the right λ is the one that shrinks past the noise but not past the signal.**

The gradient step is a tug-of-war: the fit term pulls the weight toward the noisy target while the decay term pulls it toward zero, and λ sets how hard the second rope pulls.

<svg role="img" aria-label="A weight on a line pulled right toward the noisy target by the fit term and left toward zero by the decay term, settling between them" viewBox="0 0 300 100" width="300" height="100">
  <line x1="20" y1="55" x2="285" y2="55" stroke="var(--grid)" stroke-width="1"/>
  <text x="15" y="72" fill="var(--muted)" font-size="8">0</text>
  <text x="270" y="72" fill="var(--muted)" font-size="8">12 (target)</text>
  <circle cx="150" cy="55" r="6" fill="var(--ink)"/><text x="135" y="42" fill="var(--ink)" font-size="8">weight</text>
  <line x1="144" y1="55" x2="60" y2="55" stroke="var(--s2)" stroke-width="2"/><text x="70" y="88" fill="var(--s2)" font-size="7">decay pulls to 0 (∝ λ)</text>
  <line x1="156" y1="55" x2="250" y2="55" stroke="var(--s1)" stroke-width="2"/><text x="175" y="30" fill="var(--s1)" font-size="7">fit pulls to target</text>
</svg>
^ The weight settles where the two pulls balance — at t/(1+λ) — so raising λ strengthens the leftward decay pull and moves the resting point closer to zero.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/decay-inter-01/decay.py

The fixture sets a noisy training target of 12, a true value of 6, and several decay strengths.

```json filename=modules/below-the-prompt/code/decay-inter-01/decay.json:1-8 COMPLETE
{
  "_meta": "A one-weight model fit to a NOISY training target by gradient descent. noisy_target is what the training data says the weight should be (12), but it is corrupted by noise; true_value is where the weight should really sit to generalize (6). Weight decay adds a penalty lambda*w^2 to the loss, pulling the weight toward 0. lambdas are the decay strengths to try. The question: which lambda lands the weight nearest the true value, and does no decay overfit the noise?",
  "noisy_target": 12.0,
  "true_value": 6.0,
  "lambdas": [0.0, 0.5, 1.0, 2.0, 4.0],
  "lr": 0.05,
  "steps": 300
}
```

Training is gradient descent on the combined loss; the gradient adds the decay term 2λw to the fit term. The errors and the closed form are one line each.

```python filename=modules/below-the-prompt/code/decay-inter-01/decay.py:41-58 COMPLETE
def train(target, lam, lr, steps):
    """Gradient descent on (w - target)^2 + lam*w^2; the gradient is 2(w-target) + 2*lam*w."""
    w = 0.0
    for _ in range(steps):
        w -= lr * (2 * (w - target) + 2 * lam * w)
    return w


def train_error(w, target):
    return (w - target) ** 2


def test_error(w, true_value):
    return (w - true_value) ** 2


def closed_form(target, lam):
    """The minimizer of (w-target)^2 + lam*w^2 is target/(1+lam)."""
    return target / (1 + lam)
```

The fit view trains at each λ and prints the resulting weight alongside its training and test error.

```python filename=modules/below-the-prompt/code/decay-inter-01/decay.py:65-73 COMPLETE
    t, tv, lr, steps = data["noisy_target"], data["true_value"], data["lr"], data["steps"]
    print("FIT — weight per lambda (noisy target %.0f, true value %.0f)" % (t, tv))
    print("-" * 64)
    print("  lambda   weight    train err   test err")
    for lam in data["lambdas"]:
        w = train(t, lam, lr, steps)
        print("  %5.1f    %5.2f     %7.2f    %7.2f" % (lam, w, train_error(w, t), test_error(w, tv)))
    print("-" * 64)
    print("  no decay fits the noisy target; decay shrinks the weight toward 0.")
```

Run `--fit` and read the weight and both errors per λ.

```text filename=--fit
FIT — weight per lambda (noisy target 12, true value 6)
----------------------------------------------------------------
  lambda   weight    train err   test err
    0.0    12.00        0.00      36.00
    0.5     8.00       16.00       4.00
    1.0     6.00       36.00       0.00
    2.0     4.00       64.00       4.00
    4.0     2.40       92.16      12.96
----------------------------------------------------------------
  no decay fits the noisy target; decay shrinks the weight toward 0.
```

At λ = 0 the weight is exactly 12 — a perfect training fit (train error 0) and the worst test error (36), because it fit the noise. As λ grows, the weight shrinks: 8, 6, 4, 2.4. Training error climbs the whole way, since every weight fits the noisy target worse. But test error falls to zero at λ = 1, where the weight lands on the true value 6, then rises again. The best training fit is the worst model, and vice versa.

<svg role="img" aria-label="As lambda rises, the weight shrinks from 12 through 6 to 2.4, crossing the true value 6 at lambda 1" viewBox="0 0 300 130" width="300" height="130">
  <line x1="30" y1="15" x2="30" y2="105" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="105" x2="285" y2="105" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="55" x2="285" y2="55" stroke="var(--ink)" stroke-width="1" stroke-dasharray="3 2"/>
  <text x="230" y="52" fill="var(--ink)" font-size="8">true value 6</text>
  <polyline points="45,15 105,45 165,55 225,75 275,88" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <circle cx="45" cy="15" r="3" fill="var(--s1)"/><text x="48" y="14" fill="var(--s1)" font-size="7">12 (fits noise)</text>
  <circle cx="165" cy="55" r="3" fill="var(--s2)"/><text x="150" y="70" fill="var(--s2)" font-size="7">6 at λ=1</text>
  <circle cx="275" cy="88" r="3" fill="var(--s1)"/><text x="245" y="100" fill="var(--s1)" font-size="7">2.4 (underfit)</text>
  <text x="90" y="122" fill="var(--muted)" font-size="8">λ: 0 → 4 (weight shrinks toward 0)</text>
</svg>
^ The weight starts at the noisy 12, is pulled down as λ grows, passes exactly through the true value 6 at λ = 1, and keeps shrinking past it into underfitting.

## Build

Look at test error alone with `--curve`.

```text filename=--curve
CURVE — test error across lambda (the generalization U-shape)
----------------------------------------------------------------
  lambda  0.0  test err  36.00  ####################################
  lambda  0.5  test err   4.00  ####
  lambda  1.0  test err   0.00  
  lambda  2.0  test err   4.00  ####
  lambda  4.0  test err  12.96  #############
----------------------------------------------------------------
  lowest test error at lambda 1.0 -- an interior value, not 0 or the max.
```

The test error is a clean U: 36 at no decay, down to 0 at λ = 1, back up to 12.96 at λ = 4. The minimum is at a moderate λ, not at either extreme. This is the whole story of regularization strength — no decay overfits, too much underfits, and the job is to find the bottom of the U. The bars make the shape unmistakable: tall, short, empty, short, tall.

<svg role="img" aria-label="Test error U-shape: 36 at lambda 0, dropping to 0 at lambda 1, rising to 13 at lambda 4" viewBox="0 0 300 120" width="300" height="120">
  <line x1="30" y1="15" x2="30" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="95" x2="285" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <polyline points="50,20 110,82 170,93 230,82 275,60" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <circle cx="50" cy="20" r="3" fill="var(--s1)"/><text x="35" y="16" fill="var(--s1)" font-size="7">36</text>
  <circle cx="170" cy="93" r="3" fill="var(--s2)"/><text x="158" y="90" fill="var(--s2)" font-size="7">0 (best)</text>
  <circle cx="275" cy="60" r="3" fill="var(--s1)"/><text x="262" y="56" fill="var(--s1)" font-size="7">13</text>
  <text x="45" y="110" fill="var(--muted)" font-size="8">underfit ← λ → overfit reversed: high at both ends, low in the middle</text>
</svg>
^ Test error falls then rises across λ — the regularization U — with the generalizing minimum sitting at an interior strength, invisible to training loss alone.

## Definition of done

The self-test pins the mechanism: no decay fits the noise exactly, more decay shrinks the weight monotonically, the best test error is at an interior λ, moderate decay beats no decay, and every weight matches the closed form t/(1+λ).

```python filename=modules/below-the-prompt/code/decay-inter-01/decay.py:101-113 COMPLETE
    no_decay_fits_noise = abs(ws[0.0] - t) < 1e-6
    print("  with no decay the weight equals the noisy target = %s (%.2f)" % (no_decay_fits_noise, ws[0.0]))

    decay_shrinks_weight = all(ws[lams[i + 1]] < ws[lams[i]] for i in range(len(lams) - 1))
    print("  more decay shrinks the weight monotonically = %s" % decay_shrinks_weight)

    best_test_is_interior = best_lam != lams[0] and best_lam != lams[-1]
    print("  the best test error is at an interior lambda = %s (lambda %.1f)" % (best_test_is_interior, best_lam))

    moderate_beats_no_decay = tes[best_lam] < tes[0.0]
    print("  moderate decay beats no decay on test error = %s (%.2f < %.2f)" % (moderate_beats_no_decay, tes[best_lam], tes[0.0]))

    matches_closed_form = all(abs(ws[lam] - closed_form(t, lam)) < 1e-4 for lam in lams)
    print("  each weight matches the closed form t/(1+lambda) = %s" % matches_closed_form)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — no decay overfits the noise; moderate decay generalizes best; too much underfits
----------------------------------------------------------------------------------------------------
  with no decay the weight equals the noisy target = True (12.00)
  more decay shrinks the weight monotonically = True
  the best test error is at an interior lambda = True (lambda 1.0)
  moderate decay beats no decay on test error = True (0.00 < 36.00)
  each weight matches the closed form t/(1+lambda) = True
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  no_decay_fits_noise=True  decay_shrinks_weight=True  best_test_is_interior=True  moderate_beats_no_decay=True  matches_closed_form=True
```

**Done means the trade is exhibited, not asserted: the no-decay weight fits the noise for test error 36, and moderate decay lands the weight on the truth for test error 0, exactly at t/(1+λ).**

## Boss fight

Weight decay improved generalization here by shrinking the weight. Predict whether adding weight decay always improves the test error. It is tempting to treat it as free improvement.

It is not; it is a bias-variance trade with a wrong side. Weight decay reduces variance (the weight is pulled toward a stable, small value) at the cost of bias (it is pulled away from the true value). When the true weight is genuinely large and the data is clean, decay only adds bias and hurts — the U-shape's minimum can sit at λ = 0. The improvement here comes from the true value (6) being smaller than the noisy fit (12), so shrinking toward zero happens to move toward the truth. Decay helps when the truth is closer to zero than the noisy fit is, which is common but not guaranteed; λ must be tuned on held-out data, never assumed.

The mirror-image mistake is confusing weight decay with L2 regularization added to the loss when using an adaptive optimizer like Adam. For plain gradient descent they are identical, but with Adam the two differ: adding λw² to the loss lets the adaptive scaling distort the penalty, while "decoupled" weight decay (AdamW) applies the shrink directly to the weight, which is why AdamW exists and is the modern default. The clean t/(1+λ) picture is the decoupled one.

```python filename=modules/below-the-prompt/code/decay-inter-01/decay.py:57-58 COMPLETE
def closed_form(target, lam):
    """The minimizer of (w-target)^2 + lam*w^2 is target/(1+lam)."""
    return target / (1 + lam)
```

**Add weight decay to shrink weights toward zero and trade a worse training fit for better generalization — but tune λ on held-out data, because it helps only when the truth is closer to zero than the noisy fit, and use decoupled decay (AdamW) with adaptive optimizers.**

## External resources

Krogh and Hertz, "A Simple Weight Decay Can Improve Generalization" (1991) — the original analysis tying weight decay to reduced overfitting, formalizing the shrink this module computes.

Loshchilov and Hutter, "Decoupled Weight Decay Regularization" (2019) — the AdamW paper, and the exact distinction in the boss fight between L2-in-the-loss and decoupled weight decay.

Any machine-learning course's bias-variance and regularization chapter — the U-shaped test-error curve, ridge regression's t/(1+λ) shrinkage, and why the regularization strength is a tuned hyperparameter.
