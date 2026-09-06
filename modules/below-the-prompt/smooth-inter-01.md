---
id: smooth-inter-01
title: Smooth the one-hot target — or cross-entropy has no finite optimum and drives the model to unbounded confidence
topic: below-the-prompt
level: intermediate
status: ready
time: 18 min
summary: Cross-entropy against a hard one-hot label asks for the impossible. The loss is minimized only when the softmax equals the target, and a one-hot target like [1,0,0,0] is a distribution the softmax can never produce — it needs the correct logit infinitely far above the rest. So there is no finite optimum: every increase in the correct logit lowers the loss a little more, all the way to infinity, and training keeps pushing the weights up, the confidence toward 1.0 on everything, and the probabilities out of calibration. Label smoothing replaces the target with (1−ε) on the correct class and ε spread uniformly — a distribution the softmax can actually reach at a finite logit gap. On 4 classes with ε=0.1, the hard target's cross-entropy keeps falling (0.74 at gap 1 toward 0) with confidence marching to 1.0, while the smoothed target bottoms out at gap 3.611 with loss 0.349 (exactly its entropy) and confidence 0.925 (exactly 1−ε+ε/K), rising again past that.
eli5: If a teacher only ever accepts "100% sure" as the right answer, a student learns to shout every answer with total certainty, even the shaky ones — there is no score high enough to stop them pushing. If the teacher instead says "aim for about 92% sure, and leave a little doubt for the other options," the student has a target they can actually hit and stops there, staying honest about how sure they really are. Smoothing the label is telling the model to leave a little doubt.
---

## Why this module

Training a classifier with a one-hot label sets a target the softmax can never reach, so the loss has no bottom — the model chases it by growing more and more confident forever, and its probabilities stop telling the truth.

Cross-entropy `H(target, softmax(logits))` is minimized exactly when the predicted softmax equals the target distribution. A one-hot label like `[1, 0, 0, 0]` is a distribution with a zero in every wrong slot and a one in the right one — and a softmax, being a ratio of positive exponentials, can only *approach* that in the limit where the correct logit is infinitely larger than the rest. There is no finite set of weights that achieves it. So every gradient step finds it can still lower the loss by pushing the correct logit up and the others down, and it never stops: the weights drift outward without bound, the top probability creeps toward 1.0 on every example including the uncertain ones, and a model that should say 0.9 says 0.999. The loss function itself is asking for overconfidence.

**A one-hot target is a distribution the softmax can only reach at infinite logits, so cross-entropy against it has no finite optimum and rewards ever-growing, ever-more-overconfident weights.**

Label smoothing fixes the target, not the model. Replace the one-hot with `(1−ε)` on the correct class and `ε` spread uniformly over all classes — a distribution with no zeros, which the softmax *can* produce at a finite logit gap. Now the loss bottoms out at that gap, the confidence there is capped at the smoothed target instead of driven to 1, and the minimum loss is the target's entropy rather than zero — the price of admitting the label is not perfectly certain. This module sweeps the logit gap and shows the hard loss falling forever while the smoothed loss finds a finite floor.

## Concepts

The **logit gap** is how far the correct class's logit sits above the others; it sets the softmax confidence, which rises toward 1 as the gap grows.

A **hard (one-hot) target** puts all mass on the correct class. Cross-entropy against it is minimized only at an infinite gap, so it has **no finite optimum** — training never converges to a resting confidence.

The **softmax can never equal a one-hot** because every output is a positive exponential ratio, strictly between 0 and 1. It approaches the one-hot only as logits diverge.

**Label smoothing** sets the target to `(1−ε)` on the correct class and `ε/K` on each of the K classes. This is a reachable distribution, so cross-entropy against it has a **finite optimal gap** and a finite minimum equal to the smoothed target's entropy.

**Calibrated confidence** is the payoff: at the smoothed optimum the model's top probability equals `1−ε+ε/K`, a deliberate cap below 1, so its confidence reflects real uncertainty instead of the runaway certainty a hard target forces.

```python filename=modules/below-the-prompt/code/smooth-inter-01/labelsmoothing.py:43-47 COMPLETE
def softmax(logits):
    m = max(logits)
    ex = [math.exp(l - m) for l in logits]
    s = sum(ex)
    return [e / s for e in ex]
```

**A reachable target is what gives cross-entropy a finite optimum: the one-hot has none and pushes confidence to 1, while the smoothed target caps confidence at a calibrated value the softmax can actually hit.**

<svg role="img" aria-label="The one-hot target has zeros the softmax can only approach at infinite logits; the smoothed target has nonzero mass on every class, which the softmax reaches at a finite gap" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="12" fill="var(--muted)" font-size="8">target probability per class (K=4)</text>
  <text x="8" y="40" fill="var(--s2)" font-size="8">one-hot</text>
  <rect x="55" y="20" width="26" height="30" fill="var(--s2)"/><text x="60" y="40" fill="var(--panel)" font-size="8">1.0</text>
  <rect x="83" y="48" width="26" height="2" fill="var(--grid)"/><rect x="111" y="48" width="26" height="2" fill="var(--grid)"/><rect x="139" y="48" width="26" height="2" fill="var(--grid)"/>
  <text x="172" y="40" fill="var(--muted)" font-size="8">zeros → need infinite logits</text>
  <text x="8" y="92" fill="var(--s1)" font-size="8">smoothed</text>
  <rect x="55" y="70" width="26" height="28" fill="var(--s1)"/><text x="58" y="88" fill="var(--panel)" font-size="7">.925</text>
  <rect x="83" y="93" width="26" height="5" fill="var(--s1)"/><rect x="111" y="93" width="26" height="5" fill="var(--s1)"/><rect x="139" y="93" width="26" height="5" fill="var(--s1)"/>
  <text x="172" y="92" fill="var(--muted)" font-size="8">.025 each → reachable at finite gap</text>
  <text x="30" y="114" fill="var(--muted)" font-size="8">the softmax can hit the smoothed bars; it can only approach the one-hot's zeros</text>
</svg>
^ The one-hot's wrong classes are exactly zero, which the softmax reaches only in the infinite-logit limit; the smoothed target gives each a small nonzero mass the softmax matches at a finite gap.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/smooth-inter-01/labelsmoothing.py

The fixture is a 4-class example, correct class 0, with a smoothing epsilon and a sweep of logit gaps.

```json filename=modules/below-the-prompt/code/smooth-inter-01/labelsmoothing.json:1-7 COMPLETE
{
  "_meta": "A single classification example with K classes; the correct class is index 0. The model's logits are [gap, 0, 0, ...]: the correct logit is `gap` above the others, so a bigger gap means more confidence. We compare training against a HARD one-hot target [1,0,0,0] versus a SMOOTHED target that puts (1-eps) on the correct class and spreads eps uniformly, i.e. eps/K on every class. Cross-entropy H(target, softmax(logits)) is minimized when softmax equals the target. The hard target [1,0,0,0] needs softmax = [1,0,0,0], which requires the correct logit to be infinitely larger than the rest: no finite gap achieves it, so the loss keeps dropping as the gap grows and the model is pushed to unbounded overconfidence. The smoothed target is a finite distribution the softmax CAN reach at a finite gap, so its loss has a real minimum and the model's confidence is capped at the target. gaps is the sweep to print.",
  "classes": 4,
  "correct": 0,
  "epsilon": 0.1,
  "gaps": [1, 2, 3, 4, 6, 10]
}
```

The smoothed target spreads epsilon uniformly; cross-entropy is the usual sum; the optimal gap is where the softmax exactly matches the smoothed target.

```python filename=modules/below-the-prompt/code/smooth-inter-01/labelsmoothing.py:59-71 COMPLETE
def smoothed_target(k, correct, eps):
    """(1-eps) on the correct class, eps spread uniformly (eps/k on every class)."""
    return [(1 - eps) + eps / k if i == correct else eps / k for i in range(k)]


def cross_entropy(target, logits):
    p = softmax(logits)
    return -sum(t * math.log(pi) for t, pi in zip(target, p) if t > 0)


def optimal_gap(k, eps):
    """The gap whose softmax exactly equals the smoothed target: ln(correct_target / other_target)."""
    return math.log(((1 - eps) + eps / k) / (eps / k))
```

Run `--loss` to sweep the gap.

```text filename=--loss
LOSS — cross-entropy vs correct-logit gap (4 classes, eps 0.1)
--------------------------------------------------------------
  gap    confidence   hard CE     smoothed CE
  1.0    0.4754       0.7437      0.8187
  2.0    0.7112       0.3408      0.4908
  3.0    0.8700       0.1392      0.3642
  4.0    0.9479       0.0535      0.3535
  6.0    0.9926       0.0074      0.4574
  10.0   0.9999       0.0001      0.7501
```

The hard-target column falls monotonically — 0.74, 0.34, 0.14, 0.05, 0.007, 0.0001 — heading to zero as the gap grows, and the confidence column marches with it to 0.9999. There is no gap at which the hard loss stops improving, so gradient descent never stops widening it. The smoothed column tells a different story: it falls to 0.3535 at gap 4, then *turns back up* — 0.4574 at gap 6, 0.7501 at gap 10. It has a bottom, and past that bottom, being more confident makes the loss worse.

<svg role="img" aria-label="Hard cross-entropy falls monotonically toward zero as the gap grows; smoothed cross-entropy falls to a minimum near gap 3.6 then rises again" viewBox="0 0 300 130" width="300" height="130">
  <text x="10" y="12" fill="var(--muted)" font-size="8">cross-entropy vs logit gap</text>
  <line x1="30" y1="20" x2="30" y2="105" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="105" x2="285" y2="105" stroke="var(--grid)" stroke-width="1"/><text x="250" y="118" fill="var(--muted)" font-size="7">gap →</text>
  <polyline points="45,32 70,62 95,88 120,98 170,103 270,105" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <text x="150" y="100" fill="var(--s1)" font-size="8">hard → 0 (no bottom)</text>
  <polyline points="45,26 70,55 95,72 108,74 120,73 170,60 270,20" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <circle cx="110" cy="74" r="3" fill="var(--s2)"/><text x="98" y="90" fill="var(--s2)" font-size="8">smoothed min at g*≈3.6</text>
  <text x="200" y="34" fill="var(--s2)" font-size="8">rises again</text>
  <text x="30" y="126" fill="var(--muted)" font-size="8">the hard curve never turns up; the smoothed curve has a real minimum</text>
</svg>
^ The hard curve slides down forever toward zero; the smoothed curve dips to a minimum near gap 3.6 and climbs back up, so it has a finite optimum the hard one lacks.

## Build

Where exactly is that bottom, and what confidence does it correspond to? Run `--optimum`.

```text filename=--optimum
OPTIMUM — the smoothed target's finite optimal gap
--------------------------------------------------------------
  optimal gap g*:              3.611
  loss at g*:                  0.3488   (= entropy of the smoothed target 0.3488)
  confidence at g*:            0.9250   (= 1-eps+eps/K, the target, not 1.0)
  hard target's optimal gap:   infinite (loss keeps falling, confidence -> 1.0)
```

The smoothed loss bottoms out at a gap of 3.611, and three facts lock together there. The minimum loss is 0.3488, exactly the entropy of the smoothed target — cross-entropy can never beat the target's own entropy, and smoothing raised that floor above zero on purpose. The confidence at the optimum is 0.9250, exactly `1−ε+ε/K = 0.9 + 0.025`, the smoothed target's mass on the correct class — the model is trained to be 92.5% sure, not 100%. And the hard target has no such row: its optimum is at infinity, its confidence limit is 1.0. Smoothing converted a bottomless loss into one with a finite floor and a calibrated cap.

<svg role="img" aria-label="At the optimal gap the smoothed loss equals the target entropy 0.3488 and the confidence equals the target 0.925, versus the hard target driving confidence to 1.0" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="12" fill="var(--muted)" font-size="8">confidence the target trains the model toward</text>
  <line x1="30" y1="20" x2="30" y2="92" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="92" x2="285" y2="92" stroke="var(--grid)" stroke-width="1"/>
  <rect x="30" y="28" width="230" height="20" fill="var(--s1)"/><text x="150" y="42" fill="var(--panel)" font-size="8">hard target: → 1.0000 (overconfident)</text>
  <rect x="30" y="58" width="212" height="20" fill="var(--s2)"/><text x="120" y="72" fill="var(--panel)" font-size="8">smoothed: 0.9250 (calibrated)</text>
  <line x1="242" y1="24" x2="242" y2="82" stroke="var(--ink)" stroke-width="1" stroke-dasharray="2 2"/><text x="216" y="102" fill="var(--muted)" font-size="7">smoothed cap</text>
  <text x="30" y="116" fill="var(--muted)" font-size="8">the hard bar runs to full certainty; the smoothed bar stops at the target 0.925</text>
</svg>
^ The hard target trains confidence all the way to 1.0; the smoothed target stops it at 0.925, the deliberate cap that keeps the probability honest.

## Definition of done

The self-test pins all five facts: the hard loss is still falling at a huge gap, the smoothed loss has a real minimum at g*, that minimum equals the target's entropy, the confidence there is the calibrated target, and the hard target overshoots it.

```python filename=modules/below-the-prompt/code/smooth-inter-01/labelsmoothing.py:112-127 COMPLETE
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
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the hard loss never bottoms out; the smoothed loss has a finite minimum at a calibrated confidence
----------------------------------------------------------------------------------------------------------------
  hard cross-entropy still falling at a huge gap (no finite optimum) = True (0.0000 < 0.0535)
  smoothed cross-entropy is lower at g* than on either side (a real minimum) = True
  the minimum loss equals the smoothed target's entropy = True (0.3488 = 0.3488)
  confidence at g* equals the target 1-eps+eps/K, not 1 = True (0.9250 = 0.9250)
  the hard target drives confidence above the calibrated target = True (1.0000 > 0.9250)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  hard_keeps_falling=True  smoothed_has_minimum=True  optimum_is_entropy=True  confidence_calibrated=True  hard_more_confident=True
```

**Done means the finite optimum is proven: the hard loss is still dropping at gap 20 (no bottom), the smoothed loss minimizes at gap 3.611 with value 0.3488 = the target's entropy and confidence 0.9250 = 1−ε+ε/K, while the hard target's confidence runs to 1.0.**

## Boss fight

Smoothing capped confidence at 0.925 with ε=0.1. Predict what ε too large does, and whether smoothing is always the right fix. It is tempting to crank ε up for even better calibration.

Too much smoothing throws away real signal. The optimal confidence is `1−ε+ε/K`, so a large ε caps the model's certainty low even when the evidence genuinely warrants near-certainty — set ε=0.5 and the best the model may claim on an easy, unambiguous example is around 62%, which is its own miscalibration in the opposite direction. Smoothing trades a sliver of the model's ability to be confident for protection against being *over*confident, and the right ε (commonly 0.1) is small: enough to stop the runaway to 1.0, not so much that the model can no longer be sure of things it should be sure of. There is a genuine cost — smoothing slightly worsens the raw log-likelihood on the training labels by design, because it is fitting a deliberately blurred target.

The deeper point is why the runaway matters at all. On a finite training set the model can eventually classify every example correctly; with a hard target, once it is right, the only way left to lower the loss is to become more confident, so training spends its late phase inflating logits on examples it already gets right — memorizing confidence rather than learning. That is overfitting expressed as calibration: the model's probabilities grow detached from real-world frequencies. Smoothing removes the incentive by giving the loss a floor the model reaches at moderate confidence, which is why it tends to improve calibration and generalization together. It is a cousin of the other regularizers here — weight decay pulls the weights toward zero, smoothing pulls the *target* away from the corner — and like them it is about refusing to let the model chase a perfect fit off a cliff.

```python filename=modules/below-the-prompt/code/smooth-inter-01/labelsmoothing.py:64-66 COMPLETE
def cross_entropy(target, logits):
    p = softmax(logits)
    return -sum(t * math.log(pi) for t, pi in zip(target, p) if t > 0)
```

**A one-hot target has no finite optimum and drives confidence to 1.0; label smoothing sets a reachable target so the loss bottoms at the target's entropy and confidence caps at 1−ε+ε/K — pick ε small (≈0.1), because too much smoothing forbids the model from being confident about things it should be sure of.**

## External resources

The paper "Rethinking the Inception Architecture for Computer Vision" (Szegedy et al.) — where label smoothing was introduced, with the argument that a one-hot target encourages the largest logit to grow unboundedly and hurts generalization.

"When Does Label Smoothing Help?" (Müller, Kornblith, Hinton) — the calibration analysis, including how smoothing tightens the clusters of correct-class logits and improves calibration, plus where it can hurt (distillation).

The companion "add weight decay" and "temperature and top-p shape the softmax" modules — weight decay is the other regularizer against a perfect fit, and temperature is the inference-time dial on the same softmax whose training-time confidence smoothing controls.
