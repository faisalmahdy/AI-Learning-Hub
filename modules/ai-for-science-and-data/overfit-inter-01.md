---
id: overfit-inter-01
title: Judge a model on held-out data, not the data it was fit to — a flexible model memorizes the noise and scores a perfect training error that means nothing
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: Training data is signal plus noise — the signal is the real relationship you want the model to learn, the noise is the random part that will not recur. A flexible enough model can pass through every training point exactly, driving its training error to zero, but doing so means it has fit the noise as well as the signal, memorizing quirks specific to this one sample. Its training error is then a badly optimistic estimate of its true error: near zero on the points it memorized, large on points it has never seen. A simpler model that cannot bend to every point has a larger training error, because it does not chase the noise — and that is the point, it captures the signal and leaves the noise alone, so its error on new data is close to its training error and far below the flexible model's. Ranked by training error the memorizer wins every time, because memorizing is exactly what minimizes training error; the ranking that matters — which model does better on data it has not seen — can be the reverse, and the only way to see it is to hold out a test set. The gap between a model's training error and its test error is the tell: small means the training error was honest, large means the model overfit and the training number was a mirage. On a fixture from a y = 2x line with noise, a memorizer scores a training error of 0.00 but a test error of 2.93, while a least-squares line has a training error of 2.88 yet a test error of 0.60 — the in-sample winner is the out-of-sample loser.
eli5: Imagine studying for a test by memorizing the answers to last year's exact exam paper. If someone quizzes you on that same old paper, you get 100% — you look like a genius. But that score is a lie, because you didn't learn the subject, you learned that one answer key. When the real test comes with new questions, you fall apart. A friend who actually studied the ideas might score a bit worse on the old paper (they didn't memorize it) but does great on the new questions, because they learned the thing that carries over. The only honest way to tell who really knows the material is to test both of you on questions neither has seen. Models are the same: one that "memorizes" the practice data can score a perfect practice grade and still be useless on new data, so you always have to check it on held-out examples it never saw.
---

## Why this module

The purpose of a model is to work on data you have not collected yet — tomorrow's patients, next quarter's transactions, the next image. But you only have today's data to build it from, and today's data is not the pure relationship you want to capture; it is that relationship plus a layer of noise that is specific to this particular sample and will not repeat. Any evaluation that scores the model on the same data it learned from is measuring memory, not understanding.

That distinction is the whole subject. A model with enough flexibility can always reduce its error on the training set toward zero by contorting itself to pass through every point — and since the points carry noise, passing through them exactly means fitting the noise. The result looks spectacular in-sample and fails out-of-sample, because the memorized noise is worthless on any point that was not in the training set.

This is why training error cannot be the thing you optimize or compare on. It systematically rewards the model that memorizes hardest, which is the opposite of what you want. The fix is procedural and non-negotiable: hold out a portion of the data, never let the model see it during fitting, and score on that. This module fits two models — a flexible memorizer and a simple line — and shows the training error and the held-out error telling opposite stories.

**Training data is signal plus noise, so a flexible model that fits it perfectly has memorized the noise; its training error is optimistic and only held-out data reveals whether the model learned the signal.**

## Concepts

The core quantity is the generalization gap: the difference between a model's error on data it has seen and its error on data it has not. A small gap means the training error was an honest preview of real performance. A large gap means the model overfit — its training score was inflated by memorization, and the real number is the larger test one. Watching the gap, not the training error, is what keeps you honest.

Model flexibility is the knob that trades these off. A too-simple model cannot even fit the signal — it underfits, with high error on both train and test. A too-flexible model fits signal and noise alike — it overfits, with near-zero train error and high test error. The sweet spot has enough flexibility to capture the signal and not so much that it captures the noise, and you find it by watching test error, which falls then rises as flexibility increases, not train error, which only ever falls.

The reason this must be a procedure and not a judgment call is that the bias is one-directional and invisible from the inside. Training error always understates true error for a fitted model, never overstates it, because the model was optimized against exactly those points. You cannot correct for it by being careful or by looking harder at the training fit; the information about generalization is simply not in the training error. It is only in data the model did not touch, which is why holding out a test set is a step you perform, not a mindset you adopt.

<svg role="img" aria-label="Error versus model flexibility: training error falls steadily as flexibility rises, while test error falls then rises, forming a U with its minimum at moderate flexibility" viewBox="0 0 440 170">
<line x1="40" y1="140" x2="410" y2="140" stroke="var(--line)"/>
<line x1="40" y1="20" x2="40" y2="140" stroke="var(--line)"/>
<text x="225" y="162" fill="var(--muted)" font-size="10" text-anchor="middle">model flexibility</text>
<text x="22" y="80" fill="var(--muted)" font-size="10" text-anchor="middle">error</text>
<path d="M60 40 C 150 90, 260 125, 400 132" fill="none" stroke="var(--s1)"/>
<text x="360" y="126" fill="var(--s1)" font-size="9">train</text>
<path d="M60 60 C 150 120, 220 118, 260 110 S 360 60, 400 34" fill="none" stroke="var(--s2)"/>
<text x="360" y="52" fill="var(--s2)" font-size="9">test</text>
<line x1="235" y1="20" x2="235" y2="140" stroke="var(--muted)" stroke-dasharray="3 3"/>
<text x="235" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">sweet spot</text>
<text x="90" y="30" fill="var(--muted)" font-size="8">underfit</text>
<text x="360" y="150" fill="var(--muted)" font-size="8" text-anchor="middle">overfit</text>
</svg>
^ Training error falls forever with flexibility, but test error dips then climbs — the sweet spot is at the bottom of the test-error U, invisible if you watch only training error.

**The generalization gap — test error minus train error — measures overfitting; flexibility trades underfitting for overfitting, and because training error is optimistic by construction, only held-out data can locate the right amount.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/overfit-inter-01. The fixture is five noisy training points from the line y = 2x, plus three held-out test inputs with their true (noiseless) targets.

```json filename=modules/ai-for-science-and-data/code/overfit-inter-01/overfit.json:4-7 COMPLETE
  "train_x": [0, 1, 2, 3, 4],
  "train_y": [3, -1, 7, 3, 11],
  "test_x": [0.9, 2.1, 3.9],
  "test_true": [1.8, 4.2, 7.8]
```

The simple model is a least-squares line — it cannot bend to every point.

```python filename=modules/ai-for-science-and-data/code/overfit-inter-01/overfit.py:34-42 COMPLETE
def fit_line(xs, ys):
    """Least-squares line: slope = cov(x,y)/var(x), intercept through the means."""
    n = len(xs)
    xbar = sum(xs) / n
    ybar = sum(ys) / n
    cov = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / n
    var = sum((x - xbar) ** 2 for x in xs) / n
    slope = cov / var
    return slope, ybar - slope * xbar
```

The flexible model is a memorizer — it returns the nearest training point's y, so it is exact on any point it has seen.

```python filename=modules/ai-for-science-and-data/code/overfit-inter-01/overfit.py:50-53 COMPLETE
def memorizer_predict(train_x, train_y, x):
    """A flexible model: return the y of the nearest training x (exact on any point it has seen)."""
    best = min(range(len(train_x)), key=lambda i: (abs(train_x[i] - x), train_x[i]))
    return train_y[best]
```

Both are scored by mean absolute error.

```python filename=modules/ai-for-science-and-data/code/overfit-inter-01/overfit.py:56-57 COMPLETE
def mae(preds, targets):
    return sum(abs(p - t) for p, t in zip(preds, targets)) / len(targets)
```

Before running it, predict: the memorizer should have zero training error (it returns the stored y for each training point) but large test error; the line should have nonzero training error but small test error. Run `--score`:

```text filename=overfit.py --score
SCORE — mean absolute error on the data fit vs held-out data
----------------------------------------------------------
  model         train MAE    test MAE
  memorizer     0.00         2.93
  simple line   2.88         0.60  (y = 2.00 x + 0.60)
```

The prediction holds. The memorizer scores a perfect 0.00 on training — it memorized every point — and 2.93 on held-out data. The line scores 2.88 on training, worse than the memorizer, but 0.60 on held-out data, nearly five times better. Note the line even recovered the true slope of 2.00 despite the noise; it captured the signal the memorizer buried.

<svg role="img" aria-label="Bars of mean absolute error: on training the memorizer is zero and the line is about 2.9; on test the memorizer is about 2.9 and the line is about 0.6" viewBox="0 0 440 170">
<line x1="40" y1="130" x2="410" y2="130" stroke="var(--line)"/>
<text x="120" y="150" fill="var(--muted)" font-size="10" text-anchor="middle">training set</text>
<text x="320" y="150" fill="var(--muted)" font-size="10" text-anchor="middle">held-out test</text>
<rect x="70" y="128" width="40" height="2" fill="var(--s2)"/>
<text x="90" y="122" fill="var(--ink)" font-size="9" text-anchor="middle">mem 0.0</text>
<rect x="130" y="42" width="40" height="88" fill="var(--s1)"/>
<text x="150" y="36" fill="var(--ink)" font-size="9" text-anchor="middle">line 2.9</text>
<rect x="270" y="42" width="40" height="88" fill="var(--s2)"/>
<text x="290" y="36" fill="var(--ink)" font-size="9" text-anchor="middle">mem 2.9</text>
<rect x="330" y="112" width="40" height="18" fill="var(--s1)"/>
<text x="350" y="106" fill="var(--ink)" font-size="9" text-anchor="middle">line 0.6</text>
</svg>
^ On training the memorizer looks perfect and the line poor; on held-out data the verdict flips — the line generalizes, the memorizer does not.

Now the gap that names the overfitting. Run `--gap`:

```text filename=overfit.py --gap
GAP — the train-to-test error gap for each model
--------------------------------------------------
  memorizer    train 0.00 -> test 2.93   gap 2.93
  simple line  train 2.88 -> test 0.60   gap -2.28
--------------------------------------------------
  a large gap is the signature of overfitting
```

The memorizer's error jumps by 2.93 from train to test — a huge positive gap, the signature of overfitting. The line's error actually falls from train to test (a negative gap, an artifact of this small sample), so it shows no overfitting at all: its training error was an honest, even pessimistic, preview.

<svg role="img" aria-label="Two arrows from train error to test error: the memorizer rises steeply from zero to about 2.9, the line stays low moving from about 2.9 down to 0.6" viewBox="0 0 440 150">
<text x="70" y="20" fill="var(--muted)" font-size="9" text-anchor="middle">train</text>
<text x="360" y="20" fill="var(--muted)" font-size="9" text-anchor="middle">test</text>
<line x1="70" y1="130" x2="360" y2="40" stroke="var(--s2)"/>
<circle cx="70" cy="130" r="4" fill="var(--s2)"/>
<circle cx="360" cy="40" r="4" fill="var(--s2)"/>
<text x="215" y="78" fill="var(--s2)" font-size="9" text-anchor="middle">memorizer: gap +2.9</text>
<line x1="70" y1="42" x2="360" y2="112" stroke="var(--s1)"/>
<circle cx="70" cy="42" r="4" fill="var(--s1)"/>
<circle cx="360" cy="112" r="4" fill="var(--s1)"/>
<text x="215" y="102" fill="var(--s1)" font-size="9" text-anchor="middle">line: no overfitting gap</text>
</svg>
^ The memorizer's error climbs steeply from train to test; the line's stays low, so only the memorizer carries the overfitting gap.

## Build

The self-test plants the failure and names each claim as a boolean flag. It scores both models on both sets and checks that the memorizer's training error is zero, that it wins in-sample and loses out-of-sample so the ranking reverses, and that the memorizer carries the larger train-to-test gap.

```python filename=modules/ai-for-science-and-data/code/overfit-inter-01/overfit.py:100-112 COMPLETE
    memorizer_train_perfect = mt == 0.0
    print("  memorizer: training error is zero (it memorized the points) = %s (%.2f)" % (memorizer_train_perfect, mt))

    memorizer_wins_in_sample = mt < lt
    print("  in-sample the memorizer beats the line = %s (%.2f < %.2f)" % (memorizer_wins_in_sample, mt, lt))

    line_wins_out_of_sample = le < me
    print("  out-of-sample the line beats the memorizer = %s (%.2f < %.2f)" % (line_wins_out_of_sample, le, me))

    ranking_reverses = memorizer_wins_in_sample and line_wins_out_of_sample
    print("  the ranking reverses from train to test = %s" % ranking_reverses)

    memorizer_gap_larger = (me - mt) > (le - lt)
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the ranking ever stops reversing or the memorizer stops carrying the larger gap:

```text filename=overfit.py --check
SELF-TEST — the memorizer wins in-sample and loses out-of-sample; the ranking reverses on held-out data
----------------------------------------------------------------------------------------------------------------
  memorizer: training error is zero (it memorized the points) = True (0.00)
  in-sample the memorizer beats the line = True (0.00 < 2.88)
  out-of-sample the line beats the memorizer = True (0.60 < 2.93)
  the ranking reverses from train to test = True
  the memorizer's train-to-test gap is the larger one = True (2.93 vs -2.28)
```

**The self-test asserts the ranking reverses — the in-sample winner is the out-of-sample loser — which is the sharpest possible statement that training error compares models backwards, not merely that it is a little off.**

## Definition of done

You can explain why training data is signal plus noise and why fitting it exactly means fitting the noise.
You can state that training error is optimistic by construction — it never overstates true error for a fitted model — and why that bias cannot be corrected from the training fit alone.
You can define the generalization gap and use it, not the training error, to detect overfitting.
You can describe the underfitting-to-overfitting trade-off as model flexibility rises, and say which error (test, not train) locates the sweet spot.
You can explain why holding out a test set is a procedure you must perform, and predict that comparing models by training error rewards the one that memorizes.

## Boss fight

The single held-out set here is the minimum, and it has a weakness worth reasoning about: with only three test points, the line's measured 0.60 is itself a noisy estimate, and on a different split the numbers would move. This is why serious evaluation uses cross-validation — rotate which points are held out, so every point is tested on once and the error estimate averages over several splits. The lesson generalizes: one held-out set removes the memorization bias but leaves sampling noise in the estimate; cross-validation attacks that noise. The principle is unchanged — never score on data used to fit — just applied repeatedly.

Now beware the subtler leak. Suppose you use the test set not just to score the final model but to choose between many models or tune a knob — pick the flexibility that scores best on the test set. You have now fit a decision to the test set, and it has quietly become training data; its error is optimistic again for the same reason. This is why practitioners keep a third split, a validation set for choosing, and a test set touched exactly once at the end. Any data you make a decision against stops being held out, so the "never score on data you fit to" rule extends to "never decide against data you will report on".

**One held-out set removes the memorization bias but not sampling noise — cross-validation averages that away — and the moment you tune or select against the test set it becomes training data, so choosing needs its own validation split and the test set is spent only once.**

## External resources

Any introductory statistical-learning text (for example "An Introduction to Statistical Learning") develops the train/test split, the bias-variance trade-off, and cross-validation as the core of honest model evaluation.
The scikit-learn documentation on cross-validation explains the validation/test distinction and why tuning against the test set leaks.
The topic's own modules on data leakage and on extrapolation cover adjacent ways a model's measured accuracy can overstate what it will do in production.
