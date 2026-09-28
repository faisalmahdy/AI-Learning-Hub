---
id: leakage-inter-01
title: Exclude a feature that won't exist at prediction time — a leak scores 100% in testing and collapses in production
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: You train a model to predict a label and judge it by accuracy, and the instinct is to feed it every feature you have and keep whatever raises the score. The trap is that some features carry information about the label that will not actually be available at the moment you need a prediction: a value recorded only after the outcome is known, a proxy that exists because the outcome happened — a late-fee flag that predicts default but is set as a consequence of default — or a field that, traced back, just re-encodes the label. During development these features make accuracy look wonderful, because in the historical data they genuinely do predict the label — they were derived from it. This is data leakage, and it is a mirage: the feature predicts the label in your test set only because the test set already knows the outcome, and in production the value is absent, stale, or not yet determined, so the accuracy it bought disappears and the model falls back to the honest accuracy of the legitimate features — discovered in production, after the model was trusted. The defense is causal and temporal, not statistical: for every feature ask whether its value is genuinely known at the instant a prediction must be made, and whether it is a cause the label depends on rather than an effect that depends on the label; a feature that fails either test is a leak and must be excluded however much it helps the metric. On a fixture where a leak_flag feature equals the label (assigned after the outcome), a classifier using it scores 100% while the legitimate feature honestly scores 75% — a 25-point inflation, all lost in production where the flag is not yet known.
eli5: Imagine studying for a test by practicing with a stack of questions, and one of your practice cards secretly has the answer printed on the back. You get every practice question right and feel like a genius — but on the real test the cards don't have answers on the back, and suddenly you only get the ones you actually understood. The answer-on-the-back card is like a piece of information that's only there because someone already knew the outcome; it makes your practice score look perfect but teaches you nothing that helps when the answer isn't handed to you. The fix is to throw out any card that's giving away the answer, even though it made your practice score look amazing, because the real test won't have it.
---

## Why this module

A model's measured accuracy is supposed to be a promise about how it will do on data it has not seen. Data leakage breaks that promise quietly, by letting a feature smuggle the answer into training. The model looks brilliant on every test you run, ships, and then underperforms in production — and the gap is not a bug in the code or a bad hyperparameter. It is that the thing you measured was never the thing you were going to deploy into.

The mechanism is a feature whose value depends on the label instead of the other way around, or whose value simply is not known yet when a real prediction has to be made. A flag set after the outcome. A timestamp that only exists once the event occurred. An aggregate computed over a window that includes the future. In the historical dataset all of these correlate beautifully with the label, because history already contains the outcomes. The model happily leans on them, and your cross-validation — which also draws from that same outcome-knowing history — rewards it. Nothing in the numbers warns you, because the numbers are computed in the one world where the leak is valid: the past.

This module builds the smallest version of the trap. One feature is a legitimate, honestly-predictive signal; the other is a leak that equals the label. A single-threshold classifier is run on each, and the accuracies tell the story.

**A feature that is unavailable at prediction time or downstream of the label leaks the answer into training, so measured accuracy reflects the leak rather than the model — and that accuracy collapses to the legitimate-feature level the moment the model faces data where the outcome is not yet known.**

## Concepts

The fixture tags each feature with whether its value is genuinely known at prediction time. The legitimate score is; the leak flag is not, because it is assigned after the outcome.

```json filename=modules/ai-for-science-and-data/code/leakage-inter-01/leakage.json:3-6 COMPLETE
  "features": {
    "legit_score": {"available_at_prediction": true, "desc": "a score known before the outcome"},
    "leak_flag": {"available_at_prediction": false, "desc": "a flag assigned after the outcome is known"}
  },
```

The rows carry both features and the true label. Read the leak_flag column against the label column: they are identical — the flag is the label wearing a different name.

```json filename=modules/ai-for-science-and-data/code/leakage-inter-01/leakage.json:7-11 COMPLETE
  "samples": [
    {"legit_score": 0.60, "leak_flag": 1, "label": 1},
    {"legit_score": 0.50, "leak_flag": 0, "label": 0},
    {"legit_score": 0.70, "leak_flag": 1, "label": 1},
    {"legit_score": 0.40, "leak_flag": 0, "label": 0},
```

The "model" is a deterministic single-threshold classifier — predict 1 when a feature is at least some threshold, scanning for the threshold that scores best. It is the simplest thing that can turn a feature into a prediction, which is all we need to expose the leak.

```python filename=modules/ai-for-science-and-data/code/leakage-inter-01/leakage.py:32-40 COMPLETE
def best_threshold_accuracy(values, labels):
    """A deterministic single-threshold classifier: predict 1 if value >= t, pick the best t."""
    best = 0.0
    for t in sorted(set(values)) + [max(values) + 1]:
        preds = [1 if v >= t else 0 for v in values]
        acc = sum(p == l for p, l in zip(preds, labels)) / len(labels)
        if acc > best:
            best = acc
    return best
```

A pair of helpers (not shown) scores a named feature with that classifier and reads its availability flag straight from the fixture — because the availability of a feature at prediction time is a first-class part of the analysis, not a footnote.

<svg role="img" aria-label="The leak_flag column laid beside the label column showing they are identical across all eight rows, while the legit_score column only mostly agrees" viewBox="0 0 320 120">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">leak_flag equals label row for row; legit_score only mostly agrees</text>
  <text x="16" y="34" font-size="7.5" fill="var(--s2)">leak_flag</text>
  <text x="120" y="34" font-size="7.5" fill="var(--ink)">label</text>
  <text x="210" y="34" font-size="7.5" fill="var(--s1)">legit ≥ 0.45?</text>
  <g font-size="7.5">
  <text x="16" y="52" fill="var(--s2)">1 0 1 0 1 1 0 0</text>
  <text x="120" y="52" fill="var(--ink)">1 0 1 0 1 1 0 0</text>
  <text x="210" y="52" fill="var(--s1)">1 1 1 0 1 1 1 0</text>
  </g>
  <text x="16" y="76" font-size="7.5" fill="var(--muted)">leak matches label 8/8 (it IS the label) — a perfect but useless predictor</text>
  <text x="16" y="94" font-size="7.5" fill="var(--muted)">legit matches 6/8 — an honest signal that is right three times in four</text>
</svg>
^ The leak_flag column is the label column, digit for digit, so any classifier on it scores 100%; the legitimate feature's best threshold agrees six times in eight. Perfect agreement with the label is the warning sign, not the trophy.

**Accuracy alone cannot tell a leak from a real signal — the leak scores higher — so the analysis has to carry each feature's availability at prediction time as data and judge on that, not on the score.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the feature-evaluation step of a modeling pipeline, reduced to two features and eight rows so every accuracy is checkable by hand.

Run `--features` to score each feature and see its availability.

```text filename=leakage.py --features
  feature       accuracy  available at prediction?
  legit_score   75%      True
  leak_flag     100%      False   <- LEAK (known only after the outcome)
```

The leak_flag scores a perfect 100% — of course it does, it is the label. The legit_score scores 75%, an honest, useful signal that is right three times in four. If you rank features by accuracy, as feature selection routinely does, the leak wins and gets kept; the honest feature looks second-rate beside it. The availability column is the only thing that flags the trap, and it flags it hard: the leak's value is not known at prediction time.

Now `--accuracy` shows what that means for the number you would report.

```text filename=leakage.py --accuracy
  reported accuracy, using leak_flag       = 100%
  honest production accuracy, legit_score  = 75%
  inflation bought by the leak             = +25 points
```

Include the leak and you report 100% — a model that looks flawless. Exclude it, as production forces you to, and the real accuracy is 75%. The 25-point gap is pure leakage: it exists only in the test set, where the outcome is already known and the flag is already set. In production the flag does not exist yet when the prediction is due, so the model cannot use it, and it performs at 75%. The team that reported 100% will watch accuracy "mysteriously" fall by a quarter the week it ships.

<svg role="img" aria-label="Two accuracy bars: with the leak feature the model reports 100 percent, without it the honest production accuracy is 75 percent, a 25-point drop" viewBox="0 0 320 120">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">accuracy: reported (with leak) vs production (without)</text>
  <line x1="60" y1="26" x2="60" y2="100" stroke="var(--line)" stroke-width="1"/>
  <text x="10" y="46" font-size="8" fill="var(--s2)">reported</text>
  <rect x="60" y="36" width="200" height="16" fill="var(--s2)"/><text x="264" y="49" font-size="8" fill="var(--ink)">100%</text>
  <text x="10" y="76" font-size="8" fill="var(--s1)">production</text>
  <rect x="60" y="66" width="150" height="16" fill="var(--s1)"/><text x="214" y="79" font-size="8" fill="var(--ink)">75%</text>
  <rect x="210" y="66" width="50" height="16" fill="none" stroke="var(--ink)" stroke-dasharray="2 2"/><text x="212" y="78" font-size="7" fill="var(--ink)">−25 lost</text>
  <text x="10" y="112" font-size="7.5" fill="var(--muted)">the dashed slice is leakage — real in the test set, gone in production</text>
</svg>
^ The reported 100% and the production 75% differ by exactly the leak's contribution. That dashed slice is accuracy that exists only where the outcome is already known; the deployed model, predicting before the outcome, never gets it.

**The leak scores 100% versus the legitimate feature's 75%, so ranking by accuracy keeps the wrong feature — and the reported score overstates production by the full 25 points the leak added.**

## Build

The self-test asserts the trap and the tell together: the leaky feature predicts almost perfectly, is not available at prediction time, and reports a higher accuracy than the honest feature.

```python filename=modules/ai-for-science-and-data/code/leakage-inter-01/leakage.py:86-94 COMPLETE
    leak_predicts_perfectly = leak == 1.0
    print("  the leaky feature predicts the label almost perfectly = %s (%.0f%%)" % (leak_predicts_perfectly, 100 * leak))

    leak_unavailable_at_prediction = available(data, "leak_flag") is False
    print("  the leaky feature is NOT available at prediction time = %s" % leak_unavailable_at_prediction)

    leak_inflates_accuracy = leak > legit
    print("  the leak reports higher accuracy than the honest feature = %s (%.0f%% > %.0f%%)"
          % (leak_inflates_accuracy, 100 * leak, 100 * legit))
```

Then the fix: the legitimate feature is available, and excluding the leak drops the accuracy to that honest score.

```python filename=modules/ai-for-science-and-data/code/leakage-inter-01/leakage.py:96-100 COMPLETE
    legit_available = available(data, "legit_score") is True
    print("  the legitimate feature IS available at prediction time = %s" % legit_available)

    production_matches_legit = round(100 * legit) < round(100 * leak)
    print("  production accuracy (leak excluded) drops to the honest score = %s (%.0f%%, not %.0f%%)"
          % (production_matches_legit, 100 * legit, 100 * leak))
```

Running the check confirms every clause.

```text filename=leakage.py --check
  the leaky feature predicts the label almost perfectly = True (100%)
  the leaky feature is NOT available at prediction time = True
  the leak reports higher accuracy than the honest feature = True (100% > 75%)
  the legitimate feature IS available at prediction time = True
  production accuracy (leak excluded) drops to the honest score = True (75%, not 100%)
```

**The check pairs the leak's perfect score with its unavailability at prediction time — the two facts that together define leakage — and shows the honest accuracy that survives once the leak is removed.**

## Definition of done

Done means the leak is shown to inflate accuracy precisely because it encodes an outcome not knowable at prediction time, and the honest production accuracy is what remains after excluding it. The two clauses that matter most are the pairing: high accuracy alone is not the crime, and unavailability alone is not the crime — a leak is a feature that is both suspiciously predictive and downstream of or later than the label, and it is that conjunction the check enforces.

Two things make this hard in practice and worth naming. First, most real leaks are subtler than a feature that equals the label. They hide in preprocessing done before the train/test split (scaling or imputing using statistics computed over the whole dataset, so test-set information bleeds into training), in time-series features that aggregate over a window including the future, in an ID that happens to correlate with the label because of how the data was collected, or in a "helpful" enrichment joined from a table that was itself populated after the outcome. The single-feature case here is the clean illustration; the discipline it teaches — trace each feature to when and how its value comes to exist — is what catches the subtle ones. Second, the reliable defense is procedural: split the data by time when predictions are made in time order (train on the past, test on the future, so a leak from the future cannot help), fit every preprocessing step inside the training fold only, and for each surviving feature ask the blunt question "would I have this value, with this meaning, at the instant I must predict?" A feature that cannot answer yes is excluded regardless of its accuracy — because the accuracy it offers is measured in a world the model will never deploy into.

<svg role="img" aria-label="A timeline showing the prediction moment before the outcome: legit_score exists before the prediction and is usable, leak_flag is set after the outcome and is not usable at prediction time" viewBox="0 0 320 120">
  <line x1="20" y1="60" x2="300" y2="60" stroke="var(--line)" stroke-width="1"/>
  <line x1="120" y1="30" x2="120" y2="90" stroke="var(--ink)" stroke-width="1.5" stroke-dasharray="4 3"/>
  <text x="96" y="24" font-size="7.5" fill="var(--ink)">predict here</text>
  <line x1="230" y1="40" x2="230" y2="80" stroke="var(--muted)" stroke-width="1"/>
  <text x="212" y="34" font-size="7.5" fill="var(--muted)">outcome</text>
  <circle cx="70" cy="60" r="3" fill="var(--s1)"/><text x="40" y="76" font-size="7" fill="var(--s1)">legit_score ✓</text>
  <circle cx="260" cy="60" r="3" fill="var(--s2)"/><text x="236" y="76" font-size="7" fill="var(--s2)">leak_flag ✗</text>
  <text x="20" y="110" font-size="7.5" fill="var(--muted)">a feature set after the prediction moment cannot be an input to that prediction</text>
</svg>
^ The prediction happens before the outcome. legit_score exists to its left and is a valid input; leak_flag is set to the right of the outcome, so it cannot be an input at prediction time no matter how well it correlates in hindsight.

**Done means a feature is judged a leak by the conjunction of high predictiveness and unavailability-at-prediction-time and excluded on that basis, with time-based splits and fold-internal preprocessing as the procedural defenses — so the reported accuracy is one the deployed model can actually keep.**

## Boss fight

A churn model scores 98% accuracy in every offline evaluation, the team ships it, and in production it is barely better than guessing. Investigating, you find one of its strongest features is "days_since_last_support_ticket_about_cancellation." Assuming the offline evaluation code has no bug, what happened, and how would you prevent the next one?

It is leakage: a customer opens a cancellation support ticket because they are churning, so "days_since_last_support_ticket_about_cancellation" is downstream of the outcome the model is trying to predict. In the historical training and test data, that feature is present and highly predictive — customers who churned overwhelmingly have such a ticket — so offline accuracy is inflated to 98%. But at the moment the model must predict whether a customer will churn, either the ticket has not been filed yet (the prediction is meant to be early, before churn) or filing it is itself the churn signal you were supposed to predict, so the feature is absent or useless when it matters. Production accuracy therefore collapses to whatever the legitimate, pre-outcome features support. To prevent the next one, make availability a gate in feature selection rather than trusting accuracy: for every feature, establish when and why its value comes to exist and exclude anything set at or after the outcome, or not known at the prediction cutoff. Enforce it structurally — split the data by time so training uses only information available before each prediction point, fit all preprocessing inside the training fold, and audit any feature that predicts "too well" as a leakage suspect first rather than a triumph. A feature that lifts offline accuracy by a suspiciously large margin is more often a leak than a breakthrough, and the question to ask is not "how much does it help?" but "would I have it, with this meaning, at prediction time?"

## External resources

The literature on leakage in predictive modeling (Kaufman et al., "Leakage in Data Mining," and the many Kaggle post-mortems where a leaderboard-winning feature turned out to be a leak) — a taxonomy of leakage sources, from target leakage to train/test contamination in preprocessing, and the practices that prevent each.

Documentation on leakage-safe pipelines in ML tooling (scikit-learn Pipelines and ColumnTransformer fit inside cross-validation folds, and time-series split utilities) — the mechanics of fitting every transform on training data only and splitting by time, so future or outcome-derived information cannot reach the model during training.
