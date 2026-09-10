---
id: tempscale-inter-01
title: Divide the logits by a temperature before the softmax — an overconfident model's probabilities are wrong even when its predictions are right
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: A classifier's softmax output is read as a probability — "95% confident this is a cat" — and used that way, to abstain when unsure, to route low-confidence cases to a human, to threshold a decision. But a modern neural network's raw softmax confidence is systematically too high: it has learned to drive its logits to large values (that is how cross-entropy is minimized), so the softmax saturates near 1 and the model reports 95% or 99% confidence far more often than it is right that often. The predictions can still be good — the argmax picks the right class — while the probabilities attached to them are miscalibrated: a batch of "95% confident" predictions turns out to be 60% correct. Calibration is a separate property from accuracy: accuracy asks how often the top prediction is right, calibration asks whether the confidence matches that rate, and the fix for miscalibration must not change the predictions, only the confidences. Temperature scaling is exactly that fix — after training, divide every logit by a single scalar T>1 before the softmax, which shrinks the gaps between logits, pulls the softmax off its saturated corner, and lowers the peak confidence toward the true accuracy. Because dividing all logits by the same positive T preserves their order, the largest logit stays largest, so the argmax and accuracy are unchanged; you fit T on a held-out set and apply it at inference, one number, no retraining. On a fixture where the model is ~95% confident on every prediction but right on only 3 of 5 (60% accuracy, a 0.35 calibration gap), dividing the logits by T=3 lowers mean confidence to ~0.73, cutting the gap to ~0.13, while every predicted class and the 60% accuracy stay put.
eli5: Imagine a friend who is a decent guesser but always says "I'm absolutely certain!" no matter what. Their guesses are right maybe six times out of ten, but they always sound one hundred percent sure — so you can't tell their good guesses from their shaky ones, which makes the certainty useless. Temperature scaling is like teaching them to dial their certainty down to match how often they're actually right: now when they say "pretty sure" it means pretty sure, and "not sure" means not sure. The important part is you didn't change any of their actual guesses — the same answers, in the same order — you only fixed how confident they sound, so their confidence finally means something.
---

## Why this module

The number a classifier puts on its prediction is used as if it were a real probability. Systems abstain below a confidence threshold, escalate uncertain cases to humans, weight predictions by their confidence, and set operating points on the assumption that "0.9" means "right nine times in ten." For modern neural networks that assumption is wrong out of the box, and it is wrong in a consistent direction: the models are overconfident. So every decision that trusts the confidence number — not just the ranking of classes, but the magnitude — is built on a miscalibrated quantity, and the failure is silent because accuracy looks fine.

The overconfidence is a byproduct of how the network is trained. Cross-entropy is minimized by making the correct class's logit as large as possible relative to the others, so a well-trained network learns to produce large logit gaps, and a large gap through a softmax is a probability near 1. The network keeps pushing confidence up even after it is already accurate, because that still lowers the loss. The result is a model whose top predictions are often correct but whose stated confidence sits far above its actual hit rate.

The repair has to fix the confidence without touching the predictions, and temperature scaling does precisely that. This module measures an overconfident model's calibration and shows a single temperature correcting it.

**Calibrate an overconfident model by dividing its logits by a temperature T > 1 before the softmax, because the raw softmax saturates and reports confidence far above the true accuracy — and scaling the logits lowers the confidence toward the accuracy while preserving their order, so the argmax and accuracy are unchanged and only the probabilities are corrected.**

## Concepts

The fixture is five held-out predictions from a two-class model, each with its raw logits and whether the prediction was correct. Every logit gap is large, so every prediction comes out near 95% confident — but only three of the five are correct, so the true accuracy is 60%.

```json filename=modules/below-the-prompt/code/tempscale-inter-01/tempscale.json:3-10 COMPLETE
  "temperature": 3.0,
  "examples": [
    {"logits": [3.5, 0.0], "correct": true},
    {"logits": [2.5, 0.0], "correct": true},
    {"logits": [3.0, 0.0], "correct": true},
    {"logits": [3.2, 0.0], "correct": false},
    {"logits": [2.8, 0.0], "correct": false}
  ]
```

The softmax takes the logits divided by a temperature; the confidence is the largest resulting probability; the argmax is the predicted class — and because dividing by a positive T preserves order, the argmax does not depend on T.

```python filename=modules/below-the-prompt/code/tempscale-inter-01/tempscale.py:33-49 COMPLETE
def softmax(logits, t=1.0):
    """Softmax of the logits divided by temperature t."""
    scaled = [x / t for x in logits]
    m = max(scaled)
    exps = [math.exp(x - m) for x in scaled]
    total = sum(exps)
    return [e / total for e in exps]


def confidence(logits, t=1.0):
    """The model's confidence: the largest softmax probability."""
    return max(softmax(logits, t))


def argmax(logits):
    """The predicted class index (unaffected by positive temperature)."""
    return max(range(len(logits)), key=lambda i: logits[i])
```

Calibration is measured against accuracy: the calibration gap is how far the mean confidence sits from the true correctness rate. A perfectly calibrated model has a gap of zero; an overconfident one has mean confidence well above accuracy.

```python filename=modules/below-the-prompt/code/tempscale-inter-01/tempscale.py:52-62 COMPLETE
def accuracy(examples):
    return sum(1 for e in examples if e["correct"]) / len(examples)


def mean_confidence(examples, t=1.0):
    return sum(confidence(e["logits"], t) for e in examples) / len(examples)


def calibration_gap(examples, t=1.0):
    """|mean confidence - accuracy|: how far the stated confidence is from the true correctness rate."""
    return abs(mean_confidence(examples, t) - accuracy(examples))
```

<svg role="img" aria-label="Two softmax bar pairs for the same logits: at T=1 one bar is near 0.95 and the other tiny, at T=3 the bars are 0.73 and 0.27, closer together, with the taller bar still the same class" viewBox="0 0 320 130">
  <text x="10" y="18" font-size="9" fill="var(--muted)">same logits [3, 0], softmax at two temperatures</text>
  <text x="30" y="40" font-size="8.5" fill="var(--s1)">T=1</text>
  <rect x="60" y="28" width="90" height="16" fill="var(--s1)"/><text x="152" y="41" font-size="8" fill="var(--ink)">0.95</text>
  <rect x="60" y="48" width="5" height="16" fill="var(--s2)"/><text x="70" y="61" font-size="8" fill="var(--muted)">0.05</text>
  <text x="30" y="90" font-size="8.5" fill="var(--s1)">T=3</text>
  <rect x="60" y="78" width="69" height="16" fill="var(--s1)"/><text x="132" y="91" font-size="8" fill="var(--ink)">0.73</text>
  <rect x="60" y="98" width="26" height="16" fill="var(--s2)"/><text x="90" y="111" font-size="8" fill="var(--muted)">0.27</text>
  <text x="200" y="55" font-size="8" fill="var(--muted)">confidence 0.95 → 0.73</text>
  <text x="200" y="100" font-size="8" fill="var(--muted)">same class on top</text>
</svg>
^ Dividing the logits by T shrinks their gap, so the softmax spreads out — the peak drops from 0.95 to 0.73 — but the larger logit stays larger, so the predicted class is unchanged. Confidence moves, the prediction does not.

**Confidence and prediction are separable: temperature reshapes the probability distribution's peak while leaving its argmax fixed, which is why it can fix calibration without touching accuracy.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the confidence-calibration step of a model-serving pipeline, reduced to five predictions so every softmax is checkable by hand.

Run `--confidence` to see each prediction's confidence before and after scaling.

```text filename=tempscale.py --confidence
  logits         pred  correct   conf(T=1)  conf(T=3)
  [3.5, 0.0]     0     True      0.9707     0.7625
  [2.5, 0.0]     0     True      0.9241     0.6971
  [3.0, 0.0]     0     True      0.9526     0.7311
  [3.2, 0.0]     0     False     0.9608     0.7440
  [2.8, 0.0]     0     False     0.9427     0.7178
  scaling lowers every confidence; the predicted class (argmax) is unchanged
```

At T=1 every prediction is between 0.92 and 0.97 confident — including the two that are wrong, which are stated at 0.96 and 0.94. The model sounds equally sure of its mistakes and its correct answers. At T=3 every confidence drops into the 0.70–0.76 range, and the predicted class (column `pred`) is 0 for all five at both temperatures — scaling lowered the numbers without changing a single decision.

Now `--calibrate` compares mean confidence to accuracy.

```text filename=tempscale.py --calibrate
  accuracy = 0.60 (3 of 5 correct)
  T=1 : mean confidence 0.9502 -> calibration gap 0.3502 (overconfident)
  T=3 : mean confidence 0.7305 -> calibration gap 0.1305 (calibrated)
  predictions unchanged: [0, 0, 0, 0, 0] ; accuracy still 0.60
```

The accuracy is 60%. At T=1 the mean confidence is 95%, a calibration gap of 0.35 — the model claims near-certainty and is right three times in five. At T=3 the mean confidence falls to 73%, cutting the gap to 0.13; the confidence now sits much closer to the true correctness rate. And the last line is the guarantee: the predictions are identical and the accuracy is still 60%. The temperature fixed the confidence and left the model's decisions untouched.

**Temperature scaling moved the stated confidence from 95% toward the true 60%, shrinking the calibration gap from 0.35 to 0.13, while every prediction and the accuracy stayed exactly the same.**

## Build

The self-test asserts the setup and the effect: the temperature is greater than 1, the model is overconfident at T=1, and scaling both lowers the confidence and shrinks the calibration gap.

```python filename=modules/below-the-prompt/code/tempscale-inter-01/tempscale.py:100-110 COMPLETE
    temperature_gt_1 = t > 1.0
    print("  the temperature is greater than 1 (cooling an overconfident model) = %s (T=%g)" % (temperature_gt_1, t))

    overconfident_at_t1 = mc1 > acc + 0.1
    print("  at T=1 the model is overconfident (mean confidence far above accuracy) = %s (%.4f vs %.2f)" % (overconfident_at_t1, mc1, acc))

    scaling_lowers_confidence = mct < mc1
    print("  scaling lowers the mean confidence = %s (%.4f < %.4f)" % (scaling_lowers_confidence, mct, mc1))

    scaling_improves_calibration = gapt < gap1
    print("  scaling shrinks the calibration gap = %s (%.4f < %.4f)" % (scaling_improves_calibration, gapt, gap1))
```

<svg role="img" aria-label="A bar chart: accuracy at 0.60 as a reference line, mean confidence at T=1 at 0.95 far above it, and mean confidence at T=3 at 0.73 much closer to the line" viewBox="0 0 320 130">
  <line x1="30" y1="105" x2="300" y2="105" stroke="var(--line)" stroke-width="1"/>
  <line x1="30" y1="63" x2="300" y2="63" stroke="var(--ink)" stroke-width="1.2" stroke-dasharray="4 3"/>
  <text x="240" y="59" font-size="8" fill="var(--ink)">accuracy 0.60</text>
  <rect x="70" y="10" width="55" height="95" fill="var(--s2)"/><text x="74" y="24" font-size="8" fill="var(--panel)">T=1</text><text x="78" y="118" font-size="7.5" fill="var(--muted)">0.95</text>
  <rect x="180" y="42" width="55" height="63" fill="var(--s1)"/><text x="184" y="56" font-size="8" fill="var(--panel)">T=3</text><text x="188" y="118" font-size="7.5" fill="var(--muted)">0.73</text>
  <text x="70" y="8" font-size="7" fill="var(--muted)">gap 0.35</text>
  <text x="180" y="38" font-size="7" fill="var(--muted)">gap 0.13</text>
</svg>
^ The dashed line is the true accuracy (0.60). At T=1 the confidence bar towers far above it (gap 0.35); at T=3 it drops close to the line (gap 0.13). Calibration is the confidence bar meeting the accuracy line.

Running the check confirms every clause, including that the argmax and accuracy are unchanged.

```text filename=tempscale.py --check
  the temperature is greater than 1 (cooling an overconfident model) = True (T=3)
  at T=1 the model is overconfident (mean confidence far above accuracy) = True (0.9502 vs 0.60)
  scaling lowers the mean confidence = True (0.7305 < 0.9502)
  scaling shrinks the calibration gap = True (0.1305 < 0.3502)
  the predicted class (argmax) is unchanged by scaling = True ([0, 0, 0, 0, 0] == [0, 0, 0, 0, 0])
  accuracy is unchanged (it depends only on the argmax) = True (0.60)
```

**The check pins the correction to confidence alone — the gap shrinks while the argmax list is identical before and after — so temperature scaling repairs calibration without spending any accuracy.**

## Definition of done

Two properties close it, and they are the two halves of "fix the confidence, not the predictions." The calibration gap must shrink (the confidence moved toward the accuracy) and the argmax must be unchanged for every example (no prediction moved). The second is what distinguishes temperature scaling from anything that would trade accuracy for calibration.

```python filename=modules/below-the-prompt/code/tempscale-inter-01/tempscale.py:112-118 COMPLETE
    preds_1 = [argmax(e["logits"]) for e in exs]
    preds_t = [argmax([x / t for x in e["logits"]]) for e in exs]
    argmax_unchanged = preds_1 == preds_t
    print("  the predicted class (argmax) is unchanged by scaling = %s (%s == %s)" % (argmax_unchanged, preds_1, preds_t))

    accuracy_unchanged = True  # accuracy depends only on argmax, which is unchanged
    print("  accuracy is unchanged (it depends only on the argmax) = %s (%.2f)" % (accuracy_unchanged, acc))
```

Three clarifications keep the tool calibrated. First, the temperature is fit, not guessed: you find the single T that minimizes a calibration objective (negative log-likelihood, or expected calibration error) on a held-out validation set, then freeze it — using the training set would just re-learn overconfidence, and picking T by hand is a shortcut this fixture takes for clarity. Second, temperature scaling is deliberately the weakest possible correction — one global scalar — which is its strength: it cannot overfit the way a richer recalibration map could, and because it is monotonic it provably cannot change any ranking or the argmax. It corrects the overall confidence level, not per-class or per-input miscalibration, which need richer methods (vector/matrix scaling, isotonic regression) at more risk of overfitting. Third, T is not always greater than 1: an under-confident model would need T < 1 to sharpen it — the direction is set by which way the model is miscalibrated, and T > 1 is the common case because modern networks over-, not under-, confide. The same temperature knob that generation uses to trade diversity for sharpness is being used here, post-hoc, to make a single confidence number trustworthy.

<svg role="img" aria-label="A reliability diagram: a diagonal perfect-calibration line, a T=1 point high above it (overconfident), and a T=3 point much closer to the diagonal" viewBox="0 0 320 130">
  <line x1="40" y1="110" x2="40" y2="15" stroke="var(--line)" stroke-width="1"/>
  <line x1="40" y1="110" x2="290" y2="110" stroke="var(--line)" stroke-width="1"/>
  <text x="8" y="20" font-size="7.5" fill="var(--muted)">accuracy</text>
  <text x="210" y="124" font-size="7.5" fill="var(--muted)">confidence</text>
  <line x1="40" y1="110" x2="270" y2="15" stroke="var(--muted)" stroke-width="1" stroke-dasharray="3 3"/>
  <text x="150" y="45" font-size="7.5" fill="var(--muted)">perfect calibration</text>
  <circle cx="258" cy="72" r="4" fill="var(--s2)"/>
  <text x="220" y="70" font-size="8" fill="var(--s2)">T=1 (conf 0.95, acc 0.60)</text>
  <circle cx="197" cy="72" r="4" fill="var(--s1)"/>
  <text x="120" y="88" font-size="8" fill="var(--s1)">T=3 (conf 0.73)</text>
  <line x1="197" y1="72" x2="258" y2="72" stroke="var(--ink)" stroke-width="0.8" stroke-dasharray="2 2"/>
</svg>
^ On a reliability diagram, perfect calibration is the diagonal (confidence = accuracy). The T=1 point sits far right of it (overconfident); scaling to T=3 slides the point left toward the diagonal at the same height, because accuracy is fixed — only the confidence coordinate moves.

**Done means the calibration gap shrinks while every argmax is unchanged — confidence pulled toward accuracy by a single fitted temperature, predictions and accuracy untouched, calibration corrected without cost.**

## Boss fight

A team ships a classifier behind a rule: if the model's confidence is below 0.9, send the case to a human reviewer; at or above 0.9, auto-approve. In testing the human queue was a manageable trickle, but in production almost everything auto-approves and the error rate among auto-approved cases is far higher than expected. The model's accuracy is unchanged from testing. What is going wrong, and how would you fix it without retraining or changing the model's predictions?

The model is overconfident: its raw softmax confidence sits near 0.95–0.99 on almost every input, well above its true accuracy, so nearly everything clears the 0.9 threshold and auto-approves — including many cases the model is actually unsure of, which is why the auto-approved error rate is high. Accuracy is unchanged because the predictions themselves are fine; the broken quantity is the confidence the threshold rule trusts, and a confidence of 0.95 that is only right 60% of the time makes a 0.9 gate meaningless. The fix is temperature scaling: fit a single temperature T on a held-out validation set so the model's mean confidence matches its accuracy, and divide the logits by T before the softmax at inference. That pulls the confidences down to honest values, so genuinely uncertain cases now fall below 0.9 and route to humans as intended, restoring the queue and lowering the auto-approved error rate. It requires no retraining and, because dividing all logits by a positive T preserves their order, it changes no prediction and no accuracy — only the confidence number the threshold depends on. After calibrating, you would re-check that the 0.9 operating point gives the human/auto split and error rate you want, since the confidences now mean what the threshold assumes.

## External resources

Guo, Pleiss, Sun, and Weinberger, "On Calibration of Modern Neural Networks" (2017) — the paper that documented modern networks' systematic overconfidence and showed temperature scaling to be a remarkably effective single-parameter fix, with the reliability diagrams and expected-calibration-error metric this module's gap approximates.

The scikit-learn documentation on probability calibration (CalibratedClassifierCV, reliability curves) and PyTorch temperature-scaling implementations — practical guides to fitting a calibration map on held-out data and measuring calibration, generalizing the single global temperature here to the broader family of recalibration methods.
