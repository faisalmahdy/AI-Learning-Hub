---
id: evals-inter-10
title: Measure calibration, not just accuracy — two models can tie on accuracy while one's confidence is a lie
topic: evals-and-statistics
level: intermediate
status: ready
time: 23 min
summary: A model's confidence is a promise: "90% confident" should mean right 90% of the time. Accuracy cannot see whether that promise holds. Two models score identical 0.70 accuracy, but one is calibrated (ECE 0.00) and one is overconfident (ECE 0.20) — and auto-accepting at 0.9 gives 90%-correct answers from the first and 70% from the second.
eli5: If a weather forecaster says "90% chance of rain," it should rain on about 9 of every 10 such days. A forecaster who shouts "90%!" every day but is only right 70% of the time has the same batting average as an honest one — but you can't trust their numbers. To catch that, you check whether the confidence matches how often they're right.
---

## Why this module

A confidence score is a promise, and accuracy is blind to whether the promise is kept.

When a model outputs "0.9 confident," it is claiming it will be right about 90% of the time on predictions like this one. That claim is enormously useful — it is what lets you auto-accept the confident predictions, route the unsure ones to a human, rank results by certainty, or set a threshold for action. But the claim can be true or false independent of how accurate the model is overall. A model can be exactly as accurate as another and have confidence scores that are pure theater — high numbers it has not earned. Accuracy averages over all predictions and never inspects the relationship between a prediction's confidence and its correctness, so it cannot tell an honest confidence from a lie.

This matters the instant you do anything with the confidence. Suppose you auto-accept every prediction above 0.9 and send the rest to review. With a calibrated model, the accepted pile is 90% correct — exactly what 0.9 promised. With an overconfident model that stamps 0.9 on everything, the accepted pile is only as good as its overall accuracy, and you have automated away your quality control based on a number that means nothing. Same accuracy on the eval, wildly different behavior in production, and the accuracy metric flagged nothing.

The tool that sees this is calibration, measured as expected calibration error. We will take two models with the identical accuracy — 0.70, a dead tie — and show that one has calibration error 0.00 and the other 0.20, and that the difference is the difference between a confidence threshold that works and one that lies.

**Confidence is a claim about correctness rate, and accuracy cannot audit that claim; a model can match another's accuracy while its confidences are worthless.**

## Concepts

Calibration is the agreement between confidence and observed accuracy. A model is calibrated if, among all the predictions where it said 0.9, it is right about 90% of the time; among those where it said 0.6, about 60%; and so on across the range. Perfect calibration is the diagonal line: predicted probability equals observed frequency. Miscalibration is deviation from that line — overconfidence when accuracy falls below the confidence, underconfidence when it exceeds it.

You measure it by binning. Sort the predictions into confidence buckets — say five bins from 0 to 1 — and in each bin compare the average confidence to the actual accuracy of the predictions in that bin. A calibrated model shows near-zero gaps in every bin: the 0.9 bin is 90% accurate, the 0.5 bin 50% accurate. An overconfident model shows large positive gaps in its high-confidence bins: it claimed 0.9 but delivered 0.7, a gap of 0.2. The reliability diagram is just this comparison plotted — confidence on one axis, accuracy on the other, and how far each bin sits from the diagonal.

Expected calibration error collapses those per-bin gaps into one number: the sample-weighted average of the absolute gap between confidence and accuracy across bins. Weighting by how many predictions fall in each bin means a large gap in a rarely-used confidence range counts less than a small gap where most predictions live. ECE of 0 is perfect calibration; larger ECE is worse. It is the standard scalar summary of the reliability diagram, and it is completely orthogonal to accuracy — you can hold accuracy fixed and move ECE from 0 to its maximum by shuffling which predictions got which confidence.

The reason accuracy and calibration are independent is that accuracy asks "how often is the model right?" while calibration asks "does the model know when it is right?" A model can be right 70% of the time and know exactly which 70% is shaky versus solid (calibrated), or be right 70% of the time and claim certainty about all of it (overconfident). Both are 70% accurate. Only the first has usable confidence, and only calibration distinguishes them.

**Calibration asks whether the model knows when it is right, which is orthogonal to how often it is right; ECE measures it as the weighted gap between confidence and accuracy, bin by bin.**

## Worked example

The fixture is two models' predictions on the same twenty items, each with the confidence reported and whether it was correct.

```json filename=modules/evals-and-statistics/code/evals-inter-10/predictions.json:7-9 COMPLETE
 "accept_threshold": 0.9,
 "n_bins": 5,
 "models": {
```

An accept threshold of 0.9 — predictions above it are auto-accepted — and five confidence bins for the ECE. Look at the two models' headline numbers.

```text filename=modules/evals-and-statistics/code/evals-inter-10/calibration.py --models
MODELS — two models on the same 20 items
--------------------------------------------------
  A_calibrated     accuracy 0.70   confidences used: [0.5, 0.9]
  B_overconfident  accuracy 0.70   confidences used: [0.9]
--------------------------------------------------
  identical accuracy -- accuracy alone rates them a tie.
```

Both are 70% accurate — a tie on the only number most evals report. But look at the confidences they used: model A spread its bets, saying 0.5 on some and 0.9 on others; model B stamped 0.9 on everything. That difference is invisible to accuracy and is the whole story. The reliability computation bins the predictions by confidence.

<svg role="img" aria-label="Two metrics for the two models: accuracy is a tie at 0.70 for both, but expected calibration error is 0.00 for A and 0.20 for B" viewBox="0 0 460 160" width="460" height="160">
  <rect x="0" y="0" width="460" height="160" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">accuracy (a tie) vs ECE (not a tie)</text>
  <text x="60" y="44" font-family="var(--mono)" font-size="10" fill="var(--ink)">accuracy</text>
  <rect x="150" y="36" width="100" height="14" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="256" y="47" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">A 0.70</text>
  <rect x="150" y="54" width="100" height="14" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="256" y="65" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">B 0.70</text>
  <text x="60" y="104" font-family="var(--mono)" font-size="10" fill="var(--ink)">ECE</text>
  <rect x="150" y="96" width="2" height="14" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="160" y="107" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">A 0.00</text>
  <rect x="150" y="114" width="80" height="14" fill="var(--s2)" stroke="var(--line)"/><text x="236" y="125" font-family="var(--mono)" font-size="9" fill="var(--ink)">B 0.20</text>
  <text x="60" y="148" font-family="var(--mono)" font-size="9" fill="var(--muted)">accuracy says identical; ECE says A's confidence is trustworthy and B's is not</text>
</svg>
^ The two models are indistinguishable on accuracy and a fifth of the scale apart on calibration — the metric you did not plot is the one that matters here.

```python filename=modules/evals-and-statistics/code/evals-inter-10/calibration.py:44-56 COMPLETE
def bins(preds, n_bins):
    """Group predictions into n_bins confidence buckets; return (lo, hi, count, mean_conf, accuracy) each."""
    out = []
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        # last bin is closed on the right so conf==1.0 lands somewhere
        members = [p for p in preds if lo <= p["conf"] < hi or (b == n_bins - 1 and p["conf"] == hi)]
        if not members:
            continue
        mean_conf = sum(p["conf"] for p in members) / len(members)
        acc = accuracy(members)
        out.append((lo, hi, len(members), mean_conf, acc))
    return out
```

ECE weights each bin's confidence-versus-accuracy gap by how many predictions it holds.

```python filename=modules/evals-and-statistics/code/evals-inter-10/calibration.py:59-65 COMPLETE
def ece(preds, n_bins):
    """Expected calibration error: sample-weighted mean gap between confidence and accuracy per bin."""
    total = len(preds)
    err = 0.0
    for lo, hi, count, mean_conf, acc in bins(preds, n_bins):
        err += (count / total) * abs(mean_conf - acc)
    return round(err, 4)
```

Predict before running: model A's 0.9 bin should be 90% accurate and its 0.5 bin 50%, so gaps near zero and ECE near zero. Model B's single 0.9 bin holds all twenty predictions at 70% accuracy, a gap of 0.2. Run it.

```text filename=modules/evals-and-statistics/code/evals-inter-10/calibration.py --reliability
RELIABILITY — per-bin confidence vs accuracy, and ECE
----------------------------------------------------------
  A_calibrated (ECE 0.00):
    conf~0.50  acc 0.50  n=10  gap +0.00
    conf~0.90  acc 0.90  n=10  gap +0.00
  B_overconfident (ECE 0.20):
    conf~0.90  acc 0.70  n=20  gap +0.20
----------------------------------------------------------
  A's accuracy tracks its confidence; B claims 0.9 but delivers 0.70.
```

Model A's bins sit exactly on the diagonal: it says 0.5 and is right half the time, says 0.9 and is right 90% of the time, gaps of zero, ECE 0.00. Model B has one bin — everything at 0.9 — and that bin is only 70% accurate, a gap of +0.20, so ECE 0.20. The +0.20 gap is model B's overconfidence made numeric: it claims twenty points more certainty than it delivers, on every single prediction.

<svg role="img" aria-label="Reliability diagram: confidence on the x-axis, accuracy on the y-axis, the diagonal is perfect calibration; model A's points sit on the diagonal, model B's point sits well below it" viewBox="0 0 460 210" width="460" height="210">
  <rect x="0" y="0" width="460" height="210" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">reliability: confidence (x) vs accuracy (y)</text>
  <line x1="60" y1="180" x2="60" y2="40" stroke="var(--line)"/>
  <line x1="60" y1="180" x2="420" y2="180" stroke="var(--line)"/>
  <line x1="60" y1="180" x2="420" y2="40" stroke="var(--grid)" stroke-dasharray="4 3"/><text x="300" y="60" font-family="var(--mono)" font-size="9" fill="var(--muted)">perfect (y=x)</text>
  <text x="30" y="44" font-family="var(--mono)" font-size="9" fill="var(--muted)">1.0</text><text x="34" y="184" font-family="var(--mono)" font-size="9" fill="var(--muted)">0</text>
  <text x="410" y="196" font-family="var(--mono)" font-size="9" fill="var(--muted)">1.0</text>
  <circle cx="240" cy="110" r="5" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="248" y="108" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">A 0.5→0.5</text>
  <circle cx="384" cy="54" r="5" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="300" y="50" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">A 0.9→0.9</text>
  <circle cx="384" cy="96" r="5" fill="var(--s2)" stroke="var(--ink)"/><text x="300" y="112" font-family="var(--mono)" font-size="9" fill="var(--s2)">B 0.9→0.7</text>
  <line x1="384" y1="54" x2="384" y2="96" stroke="var(--s2)" stroke-dasharray="2 2"/><text x="392" y="80" font-family="var(--mono)" font-size="8" fill="var(--s2)">gap 0.2</text>
</svg>
^ Model A's points land on the diagonal — confidence equals accuracy; model B's point drops 0.2 below it, the overconfidence the ECE measures.

Now the consequence. Accuracy-above-threshold keeps only the predictions at or over the accept threshold and measures their accuracy.

```python filename=modules/evals-and-statistics/code/evals-inter-10/calibration.py:68-72 COMPLETE
def accuracy_above(preds, threshold):
    """Accuracy of just the predictions the model reported at or above the accept threshold."""
    kept = [p for p in preds if p["conf"] >= threshold]
    if not kept:
        return None, 0
    return accuracy(kept), len(kept)
```

<svg role="img" aria-label="Auto-accepting at 0.9: model A's accepted predictions are 90% accurate, model B's are 70% accurate" viewBox="0 0 460 150" width="460" height="150">
  <rect x="0" y="0" width="460" height="150" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="22" font-family="var(--mono)" font-size="11" fill="var(--muted)">accuracy of predictions auto-accepted at conf ≥ 0.9</text>
  <line x1="60" y1="120" x2="440" y2="120" stroke="var(--line)"/>
  <rect x="100" y="39" width="90" height="81" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="118" y="33" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">0.90</text><text x="112" y="138" font-family="var(--mono)" font-size="9" fill="var(--muted)">A (calibrated)</text>
  <rect x="280" y="57" width="90" height="63" fill="var(--s2)" stroke="var(--line)"/><text x="298" y="51" font-family="var(--mono)" font-size="11" fill="var(--ink)">0.70</text><text x="278" y="138" font-family="var(--mono)" font-size="9" fill="var(--muted)">B (overconfident)</text>
</svg>
^ The same 0.9 threshold, applied to two equally-accurate models, yields a 90%-correct accepted pile from A and a 70%-correct one from B — because B's 0.9 is a lie.

## Build

Reproduce the two ECEs and the threshold gap. Pure standard library, so 0.00, 0.20, 0.90, and 0.70 come out exactly.

Run `--models` for the tie, `--reliability` for the bins and ECE, `--check` for the gate. The self-test pins the whole point: equal accuracy, unequal ECE, A calibrated, and the accept threshold delivering different quality from the two.

```python filename=modules/evals-and-statistics/code/evals-inter-10/calibration.py:111-116 COMPLETE
    ece_a, ece_b = ece(a, n_bins), ece(b, n_bins)
    calibration_differs = ece_b > ece_a + 0.1
    print("  their calibration error is very different = %s (A %.2f vs B %.2f)" % (calibration_differs, ece_a, ece_b))

    a_calibrated = ece_a < 0.05
    print("  model A is well calibrated = %s (ECE %.2f)" % (a_calibrated, ece_a))
```

The `same_accuracy` check just above these — `accuracy(a) == accuracy(b)` — is what makes the module's point land. It insists the two models are a genuine tie on accuracy, exactly equal, so that everything else the self-test finds is invisible to the accuracy number. If the accuracies differed, a skeptic could say "just pick the more accurate one" and the calibration lesson would be muddied. Equal accuracy forces the decision onto calibration. Here is the full gate.

```text filename=modules/evals-and-statistics/code/evals-inter-10/calibration.py --check
SELF-TEST — equal accuracy, unequal calibration; the accept threshold means different things
------------------------------------------------------------------------------------------
  the two models have identical overall accuracy = True (0.70 = 0.70)
  their calibration error is very different = True (A 0.00 vs B 0.20)
  model A is well calibrated = True (ECE 0.00)
  auto-accepting at 0.9 gives worse answers from B = True (A 0.90 vs B 0.70 above threshold)
------------------------------------------------------------------------------------------
SELF-TEST PASS  same_accuracy=True  calibration_differs=True  a_calibrated=True  threshold_lies=True
```

Four True flags. Same_accuracy: the models tie at 0.70. Calibration_differs: their ECEs are 0.00 and 0.20, a fifth of the whole scale apart. A_calibrated: model A's confidences are honest. Threshold_lies: auto-accepting at 0.9 gets 90% from A and 70% from B. The last flag is the one with teeth in production — the confidence threshold you built your pipeline on means one thing for a calibrated model and something else entirely for an overconfident one.

**The self-test forces the two models to exactly equal accuracy, so every difference it then finds is one accuracy could never have shown you.**

## Definition of done

You are done when you reproduce the ECEs and can explain why accuracy could never separate these models.

Concretely: `--reliability` shows model A's bins on the diagonal (ECE 0.00) and model B's single bin 0.20 below it; `--check` prints PASS with four True flags. You can define calibration as agreement between confidence and observed accuracy, describe the binning that measures it, and state ECE as the sample-weighted mean gap. You can explain why calibration is orthogonal to accuracy — one asks how often the model is right, the other whether it knows when — and you can name the concrete harm of ignoring it: any confidence threshold, routing rule, or ranking built on an uncalibrated model's scores is built on sand.

The habit to carry: whenever a model's confidence feeds a decision — a threshold, a triage, a ranking — report calibration alongside accuracy, and never trust a confidence number until a reliability diagram says it means what it claims. Accuracy tells you if the model is good; calibration tells you if you can believe its confidence.

## Boss fight

The instructive failure is a triage system that quietly stops triaging.

A team builds a classifier that auto-approves cases above 0.95 confidence and sends the rest to human review. It launches on a calibrated model: the 0.95+ cases are 95% correct, the humans handle the genuinely uncertain ones, everyone is happy. A later model update improves accuracy by two points — a clear win on the eval — but the new model is overconfident, stamping 0.95+ on nearly everything. Now almost every case auto-approves, the human queue empties, and the error rate on approved cases climbs to the model's overall error rate, because 0.95 no longer means 95%. The accuracy metric went up; the system got worse. No one caught it, because no one measured calibration on the update.

Your turn, two moves. First, make model B underconfident instead of overconfident and watch ECE catch that too. Change B's predictions to confidence 0.5 while keeping 70% accuracy, and predict: the gap is now |0.5 − 0.7| = 0.2 in the other direction, ECE still 0.20, but now the harm is inverted — you would send confident, correct predictions to needless human review, wasting reviewer time. Calibration error is symmetric; both directions cost you. Second, probe the binning. With five bins, predictions at 0.5 and 0.9 fall in clearly separate bins — but what if a model reports 0.58 and 0.62, which straddle a bin boundary? Predict how the ECE could change if you shifted the bin edges, and confirm the known weakness: ECE depends on the binning, and a model can look better or worse by luck of where the boundaries fall. That is why adaptive binning (equal-mass bins) and proper scoring rules like the Brier score exist — they measure the same thing with less dependence on arbitrary edges.

## External resources

Guo et al., "On Calibration of Modern Neural Networks" (2017), is the standard reference: it introduces ECE in the form used here, shows that accurate modern networks are often badly overconfident, and demonstrates temperature scaling as a fix.

For the proper-scoring-rule view that avoids binning entirely, the Brier score and the reliability/resolution decomposition (Murphy) measure calibration and sharpness together; any forecasting-verification text covers it.

For the LLM-specific version — whether a model's stated confidence or token probabilities match its correctness — search the recent literature on "LLM calibration" and "selective prediction," which applies exactly this reliability-diagram machinery to model confidence and to confidence-thresholded abstention.
