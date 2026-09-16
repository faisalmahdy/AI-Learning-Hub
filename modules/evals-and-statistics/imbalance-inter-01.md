---
id: imbalance-inter-01
title: On an imbalanced test set, accuracy rewards the do-nothing classifier — score the rare class with recall, F1, balance
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: Accuracy is the fraction of predictions that are correct and the default metric everyone reaches for, but it is almost useless when the classes are imbalanced, because it lets a classifier score well by ignoring the rare class entirely. If 95% of examples are negative — the normal case for fraud, disease, or defect detection — a classifier that predicts "negative" for everything is 95% accurate while catching zero positives; it has learned nothing and is worthless for the task, yet accuracy calls it strong. Worse, accuracy can rank that do-nothing classifier above a genuinely useful one, because a real model that catches most positives pays for it with some false positives, each a wrong answer the do-nothing model never risks. The fix is to score the rare class directly: recall (of the actual positives, how many caught) is 0 for the do-nothing classifier, F1 (the harmonic mean of precision and recall) is 0 whenever either is 0, and balanced accuracy (averaging true-positive and true-negative rates) gives the rare class equal weight so the baseline scores 0.5 not 0.95. On a fixture of 50 positives and 950 negatives, the majority-negative classifier scores accuracy 0.95 but recall 0, F1 0, and balanced accuracy 0.5, while the real model scores accuracy 0.94 (lower than the baseline) but recall 0.80, F1 0.57, and balanced accuracy 0.87 — accuracy ranks the useless model first, every rare-class metric ranks the real model far ahead.
eli5: Imagine a test to spot the one kid in a class of twenty who is left-handed. A lazy guesser who always says "right-handed" is right 19 times out of 20 — 95% accurate! — but never finds a single left-handed kid, which was the whole point. A real detector that finds most left-handed kids but occasionally mislabels a right-handed one might be "only" 94% accurate, and yet it's enormously more useful. If you grade only on overall correctness, the lazy guesser wins and you'd pick the useless one. You have to grade specifically on "did it find the thing we were looking for," which is what recall and F1 measure.
---

## Why this module

Reporting a classifier's accuracy feels like reporting its quality, and for balanced problems it roughly is. For the rare-event problems that dominate real machine learning — fraud, disease, abuse, defects — accuracy is not just uninformative but actively misleading: it hands its highest score to a model that does nothing, and it can rank that do-nothing model above the one you should actually ship. A single accuracy number can hide a complete failure at the only task that mattered.

Accuracy is the fraction of predictions that are correct, and it is the default metric everyone reaches for. It is also almost useless when the classes are imbalanced, because it lets a classifier score well by ignoring the rare class entirely. If 95% of your examples are negative — the normal case for fraud, disease, defect detection, any rare-event problem — then a classifier that predicts "negative" for everything is 95% accurate while catching zero positives. It has done nothing, learned nothing, and is worthless for the task (which is to find the positives), yet accuracy calls it a strong model. Worse, accuracy can rank that do-nothing classifier above a genuinely useful one: a real model that catches most positives but pays for it with some false positives can have lower accuracy than the majority-class baseline, because each false positive is a wrong answer that the do-nothing model never risks.

The fix is to score the rare class directly, with metrics that do not let the majority class drown it out. Recall — of the actual positives, how many did we catch — exposes the do-nothing classifier immediately: its recall is 0. Precision — of our positive predictions, how many were right — measures the false-positive cost. F1 combines the two as their harmonic mean, which is 0 whenever either is 0, so a classifier that catches nothing scores F1 = 0 no matter how high its accuracy. Balanced accuracy averages the true-positive rate and the true-negative rate, giving the rare class equal weight, so the do-nothing baseline scores 0.5 (chance) rather than 0.95. This module scores a do-nothing baseline and a real model both ways.

**Accuracy on an imbalanced test set rewards predicting the majority class, so a do-nothing classifier scores high (and can outrank a useful model) while catching none of the rare positives — score the rare class with recall, precision, F1, and balanced accuracy, which a do-nothing classifier fails.**

## Concepts

**Accuracy** counts every correct prediction equally, so on a 95%-negative set the negatives dominate it and a model can score 0.95 by getting only the easy majority right.

```python filename=modules/evals-and-statistics/code/imbalance-inter-01/imbalance.py:44-45 COMPLETE
def accuracy(c):
    return (c["tp"] + c["tn"]) / (c["tp"] + c["fp"] + c["fn"] + c["tn"])
```

**Recall** asks only about the rare class — of the real positives, how many were caught — so a classifier that predicts no positives scores 0 no matter how many negatives it gets right.

```python filename=modules/evals-and-statistics/code/imbalance-inter-01/imbalance.py:52-53 COMPLETE
def recall(c):
    return c["tp"] / (c["tp"] + c["fn"]) if (c["tp"] + c["fn"]) else 0.0
```

<svg role="img" aria-label="A test set of 1000 examples with 950 negatives and 50 positives; predicting all-negative gets the 950 negatives right and all 50 positives wrong, scoring 95% accuracy while catching no positives" viewBox="0 0 300 112" width="300" height="112">
  <text x="6" y="12" fill="var(--muted)" font-size="8">1000 examples: 950 negative, 50 positive (rare)</text>
  <rect x="20" y="24" width="228" height="16" fill="var(--s1)"/><text x="24" y="36" fill="var(--panel)" font-size="7">950 negatives</text>
  <rect x="248" y="24" width="12" height="16" fill="var(--s2)"/><text x="240" y="52" fill="var(--muted)" font-size="6">50 pos</text>
  <text x="20" y="72" fill="var(--muted)" font-size="8">"always negative": all 950 negatives right, all 50 positives missed</text>
  <rect x="20" y="80" width="228" height="12" fill="var(--s1)"/><text x="24" y="90" fill="var(--panel)" font-size="7">correct</text>
  <rect x="248" y="80" width="12" height="12" fill="none" stroke="var(--s2)"/>
  <text x="20" y="106" fill="var(--muted)" font-size="8">accuracy 950/1000 = 0.95, but recall 0/50 = 0</text>
</svg>
^ Because the negatives are 95% of the set, a classifier that predicts all-negative gets nearly everything right (accuracy 0.95) purely by conceding the rare class — its recall on the 50 positives is 0.

**Accuracy weights every example equally so the majority class dominates it; recall isolates the rare class, so it drops to 0 for exactly the do-nothing classifier accuracy scores highest.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/imbalance-inter-01/imbalance.py

The fixture is 50 positives and 950 negatives, with a do-nothing baseline and a real model as confusion counts.

```json filename=modules/evals-and-statistics/code/imbalance-inter-01/imbalance.json:3-8 COMPLETE
  "positives": 50,
  "negatives": 950,
  "classifiers": {
    "majority_negative": {"tp": 0, "fp": 0, "fn": 50, "tn": 950},
    "real_model": {"tp": 40, "fp": 50, "fn": 10, "tn": 900}
  }
```

Run `--accuracy` to score both.

```text filename=--accuracy
ACCURACY — imbalanced test set: 50 positives, 950 negatives
------------------------------------------------------------------
  classifier          tp   fp   fn   tn    accuracy
  majority_negative   0    0    50   950   0.9500
  real_model          40   50   10   900   0.9400
------------------------------------------------------------------
  accuracy's top model: majority_negative -- the do-nothing baseline, which catches ZERO positives.
```

Accuracy ranks the do-nothing baseline first, 0.95 to 0.94. Read the confusion counts to see why. The majority classifier predicts negative always: it gets all 950 negatives right (true negatives) and all 50 positives wrong (false negatives), for 950/1000 = 0.95, and its tp and fp are both 0 — it never predicts positive, so it can never be wrong about a positive prediction. The real model catches 40 of the 50 positives, but to do so it also raises 50 false alarms on negatives, and those 50 false positives are 50 wrong answers, dragging its accuracy to 940/1000 = 0.94. So the model that actually does the job scores *lower*, because accuracy charges it for the false positives that are the unavoidable price of finding positives, while giving the do-nothing model a perfect record on a task it declined to attempt. Anyone selecting a model by accuracy on this test set would ship the useless one.

<svg role="img" aria-label="The positive column of each classifier: the do-nothing model has no positive predictions at all, the real model catches 40 of 50 true positives at the cost of 50 false positives" viewBox="0 0 300 110" width="300" height="110">
  <text x="6" y="12" fill="var(--muted)" font-size="8">of the 50 real positives, who caught them?</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">do-nothing</text>
  <rect x="80" y="24" width="180" height="14" fill="none" stroke="var(--line)"/><text x="86" y="34" fill="var(--muted)" font-size="7">0 caught — no positive predictions at all</text>
  <text x="10" y="64" fill="var(--muted)" font-size="7">real model</text>
  <rect x="80" y="54" width="144" height="14" fill="var(--s2)"/><text x="86" y="64" fill="var(--panel)" font-size="7">40 true positives</text>
  <rect x="226" y="54" width="34" height="14" fill="none" stroke="var(--s1)"/><text x="228" y="64" fill="var(--muted)" font-size="6">10 missed</text>
  <text x="10" y="94" fill="var(--muted)" font-size="7">real model's cost: 50 false positives (why its accuracy dips to 0.94)</text>
  <rect x="80" y="82" width="60" height="8" fill="var(--s1)"/>
</svg>
^ The do-nothing model catches none of the 50 positives, while the real model catches 40 (missing 10) and pays 50 false positives for it — the false positives are exactly what accuracy punishes and what makes the useful model score lower.

## Build

Scoring the rare class directly flips the ranking to the right one. Run `--metrics`.

```text filename=--metrics
METRICS — score the rare (positive) class directly
--------------------------------------------------------------------
  classifier          precision  recall   F1       balanced_acc
  majority_negative   0.000      0.000    0.000    0.500
  real_model          0.444      0.800    0.571    0.874
```

Every rare-class metric ranks the real model far above the baseline. The majority classifier scores 0 on precision, recall, and F1 — it catches nothing, so there is nothing right about its (nonexistent) positive predictions — and its balanced accuracy is 0.5, exactly chance, which is the honest score for a coin that always says "negative." The real model scores recall 0.80 (it found 40 of 50 positives), precision 0.444 (of its 90 positive predictions, 40 were right), F1 0.571 (their harmonic mean), and balanced accuracy 0.874. The contrast between accuracy and F1 is the whole lesson: accuracy said 0.95 vs 0.94, a near-tie favoring the useless model; F1 says 0.00 vs 0.571, a blowout favoring the real one. F1 does this because it is a harmonic mean — if either precision or recall is 0, F1 is 0, so a model cannot hide a total failure on one of them behind a high score on the other.

```python filename=modules/evals-and-statistics/code/imbalance-inter-01/imbalance.py:60-62 COMPLETE
def f1(c):
    p, r = precision(c), recall(c)
    return 2 * p * r / (p + r) if (p + r) else 0.0
```

<svg role="img" aria-label="Grouped bars comparing the two classifiers on accuracy, F1, and balanced accuracy: accuracy is nearly tied and favors the do-nothing model, while F1 and balanced accuracy strongly favor the real model" viewBox="0 0 300 124" width="300" height="124">
  <text x="6" y="12" fill="var(--muted)" font-size="8">accuracy hides it; F1 and balanced accuracy expose it</text>
  <line x1="34" y1="98" x2="290" y2="98" stroke="var(--line)"/>
  <text x="28" y="30" fill="var(--muted)" font-size="7" text-anchor="end">1.0</text>
  <text x="28" y="98" fill="var(--muted)" font-size="7" text-anchor="end">0</text>
  <g transform="translate(60,0)">
  <text x="6" y="112" fill="var(--muted)" font-size="7">accuracy</text>
  <rect x="0" y="30" width="16" height="68" fill="var(--s1)"/><rect x="18" y="31" width="16" height="67" fill="var(--s2)"/>
  </g>
  <g transform="translate(150,0)">
  <text x="16" y="112" fill="var(--muted)" font-size="7">F1</text>
  <rect x="0" y="98" width="16" height="0.5" fill="var(--s1)"/><rect x="18" y="59" width="16" height="39" fill="var(--s2)"/>
  </g>
  <g transform="translate(230,0)">
  <text x="0" y="112" fill="var(--muted)" font-size="7">balanced</text>
  <rect x="0" y="64" width="16" height="34" fill="var(--s1)"/><rect x="18" y="38" width="16" height="60" fill="var(--s2)"/>
  </g>
  <text x="60" y="124" fill="var(--s1)" font-size="7">■ do-nothing</text><text x="150" y="124" fill="var(--s2)" font-size="7">■ real model</text>
</svg>
^ On accuracy the two bars are nearly equal and the do-nothing model (left) is slightly taller; on F1 and balanced accuracy the do-nothing model collapses to near zero and 0.5 while the real model stands well above — the rare-class metrics rank the models correctly.

## Definition of done

The self-test pins the high-but-useless accuracy, the zero recall/F1, and the reversed ranking that the rare-class metrics correct.

```python filename=modules/evals-and-statistics/code/imbalance-inter-01/imbalance.py:102-113 COMPLETE
    maj_accuracy_high = abs(accuracy(maj) - 0.95) < 1e-9
    print("  the do-nothing classifier's accuracy is 0.95 = %s (%.4f)" % (maj_accuracy_high, accuracy(maj)))

    maj_useless = recall(maj) == 0.0 and f1(maj) == 0.0
    print("  yet it has zero recall and zero F1 (catches no positives) = %s" % maj_useless)

    accuracy_prefers_donothing = accuracy(maj) > accuracy(real)
    print("  accuracy ranks the do-nothing classifier ABOVE the real model = %s (%.4f > %.4f)"
          % (accuracy_prefers_donothing, accuracy(maj), accuracy(real)))

    f1_prefers_real = f1(real) > f1(maj)
    print("  F1 ranks the real model far above = %s (%.3f vs %.3f)" % (f1_prefers_real, f1(real), f1(maj)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the majority classifier has 0.95 accuracy but 0 recall/F1; accuracy prefers it; F1 and balance prefer the real model
--------------------------------------------------------------------------------------------------------------------------------
  the do-nothing classifier's accuracy is 0.95 = True (0.9500)
  yet it has zero recall and zero F1 (catches no positives) = True
  accuracy ranks the do-nothing classifier ABOVE the real model = True (0.9500 > 0.9400)
  F1 ranks the real model far above = True (0.571 vs 0.000)
  balanced accuracy also prefers the real model = True (0.874 vs 0.500)
```

**Done means the paradox and its fix are proven on real counts: the do-nothing classifier scores accuracy 0.95 but recall 0 and F1 0, accuracy ranks it above the real model (0.95 > 0.94), and F1 (0.571 vs 0.000) and balanced accuracy (0.874 vs 0.500) rank the real model far ahead — so on an imbalanced test set the metric must score the rare class, not overall correctness.**

## Boss fight

Predict two ways the fix is more than "use F1," because the right metric depends on the costs and the whole distribution, not just on avoiding accuracy.

The first trap is that F1 and balanced accuracy are not interchangeable, and neither is universally correct — the metric must match the relative cost of the two errors. F1 weights precision and recall equally, but real problems rarely do: missing a case of a serious disease (a false negative) is far worse than a false alarm (a false positive), so you would weight recall higher (Fβ with β > 1), while a spam filter that must not eat real mail weights precision higher (β < 1). Balanced accuracy weights the two classes equally regardless of their sizes, which is right when you care about both classes symmetrically but wrong when the rare class is the only one that matters. And a single-threshold metric hides that a classifier is a whole curve of precision/recall trade-offs as you move the decision threshold — which is why threshold-independent summaries like the area under the precision–recall curve (preferred over ROC-AUC under heavy imbalance, because ROC can look deceptively good) describe the model's behavior across operating points rather than at one arbitrary cut. The point is not "F1 is the right metric"; it is that you must choose a metric that encodes your actual costs and, ideally, look at the full trade-off curve rather than one number.

The second trap is that imbalance corrupts more than the metric — it corrupts training and the meaning of a "positive" too, so fixing only the report is not enough. A model trained by minimizing average error on a 95%-negative set is under the same pressure the accuracy metric describes: predicting the majority is a strong local optimum, so imbalance is handled at training time with class weights, resampling (oversampling the minority, undersampling the majority), or loss functions that focus on hard/rare cases — not just by changing the evaluation. The evaluation itself must also use a test set whose base rate matches production (the companion stratification module): F1 and precision depend on the actual positive rate, so measuring on an artificially balanced test set reports a precision the model will never achieve in the wild. And the deepest version connects to base rates directly — precision is just the positive predictive value from the base-rate module, so a rare positive class caps achievable precision no matter how good the model is, and a stakeholder expecting "99% precise" from a 1%-prevalence detector is asking for something the arithmetic forbids. So handling imbalance means: train for it, evaluate at the production base rate, choose a cost-matched metric, and set precision expectations against what the base rate allows.

**The remedy is not a single metric but a matched one: weight the errors by their real costs (Fβ, or a cost-sensitive score) and read the whole precision–recall curve rather than one threshold, evaluate on a test set at the production base rate (or precision is fiction), and handle imbalance at training time (class weights, resampling) as well — because on a rare class the base rate itself caps achievable precision, so accuracy, the metric, the threshold, the training, and the expectations all have to account for the imbalance together.**

## External resources

Any machine-learning reference on evaluation metrics for imbalanced classification — the confusion matrix, precision/recall/F1 and Fβ, balanced accuracy, and precision–recall versus ROC curves under class imbalance.

Writing on the accuracy paradox and cost-sensitive learning — why accuracy misleads on skewed classes, how class weights and resampling address imbalance at training time, and how to pick a metric that reflects error costs.

The companion base-rate and stratification modules in this topic — precision is the positive predictive value the base-rate module computes, so the rare class caps it, and evaluating at the production base rate (stratification) is required for precision and F1 to mean anything.
