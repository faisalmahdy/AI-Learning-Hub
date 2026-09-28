---
id: evals-inter-11
title: Noisy gold labels cap measured accuracy at 1−k — a perfect model cannot score 100%
topic: evals-and-statistics
level: intermediate
status: ready
time: 21 min
summary: An eval scores agreement with the gold label, but if a fraction k of labels are wrong, a correct model is penalized on every mislabeled item. Measured accuracy is capped at 1−k. With 10% label noise the ceiling is 0.90, a perfect model measures exactly 0.90, and a true 0.05 accuracy gap measures as 0.04 — real improvements are masked near the ceiling.
eli5: If the answer key itself has mistakes, then a student who gets everything right still "misses" the questions the key got wrong. So no one can score 100% — the best possible score is however much of the key is correct. And two great students look almost the same, because the key can't tell them apart on the questions it has wrong.
---

## Why this module

The score your eval reports is not your model's accuracy — it is your model's agreement with an answer key that is itself imperfect, and that imperfection sets a hard ceiling you cannot climb past by improving the model.

Gold labels come from somewhere: human annotators who disagree and err, a previous model that generated them, a heuristic that is mostly right. A fraction of them are simply wrong. And your eval scores a model by how often it matches the label. So on every mislabeled item, a model that produces the *correct* answer is marked wrong — penalized precisely for being right, because the reference it is compared against is wrong. The eval cannot tell "the model erred" from "the label erred"; it only sees disagreement, and it charges the model for all of it.

That puts a ceiling on the measured score. If a fraction k of labels are wrong, then even a flawless model — one that is right on every single item — disagrees with the label on the k that are mislabeled, and scores 1 − k. Not 1. The best measurable accuracy is bounded by the quality of the answer key, and no amount of model improvement can exceed it. A reported accuracy at or above 1 − k does not mean the model is superhuman; it means either the labels are cleaner than you think or the model is somehow exploiting the label noise.

There is a second, subtler cost: compression. Near the ceiling, each real gain in the model's true accuracy moves the measured score by less than the gain itself, because part of every improvement lands on items the label got wrong, where being more correct earns nothing. So genuine improvements shrink in the measurement, and telling two strong models apart gets harder exactly when they are both good — the regime you most care about.

We will score three models against a 10%-noisy answer key. The good model (95% true) measures 0.860, the better model (99%) measures 0.892, and the perfect model measures exactly 0.900 — the ceiling. A true accuracy gap of 0.05 shows up as 0.04. The labels, not the models, set the numbers.

**An eval measures agreement with the labels, not truth, so noisy labels cap the score at 1−k — a perfect model scores 1−k, and real gains near the ceiling measure smaller than they are.**

## Concepts

Write down what "measured accuracy" actually is. The eval counts an item correct when the model's answer matches the label. Under the standard assumption that the model's errors and the label's errors are independent, that happens in two ways: the model is right and the label is right (probability a × (1−k)), or the model is wrong and the label is wrong in the *same* way, so they coincidentally agree (probability (1−a) × k). Add them: measured = a(1−k) + (1−a)k. That formula is the whole module.

Read off its two features. Setting a = 1 gives measured = 1 − k: the ceiling, the score of a perfect model. And the derivative of measured with respect to a is (1−k) − k = 1 − 2k, which for any real noise rate is less than 1: every unit of true accuracy gained shows up as only 1 − 2k units of measured accuracy gained. At 10% noise that factor is 0.8, so a real 0.05 improvement measures as 0.04. The measurement systematically understates both the level (via the ceiling) and the gains (via the compression), and both effects get worse as k grows.

The ceiling is the part that breaks intuitions about "how good is good enough." If your labels are 5% noisy, a measured 0.95 is a perfect model — there is nowhere left to go, and further measured improvement is impossible without cleaner labels. If your labels are 10% noisy and you report 0.92, you are within 0.08 of the absolute maximum the eval can ever show, and the model might be anywhere from very good to perfect; the eval cannot resolve it. Past a point, the bottleneck stops being the model and becomes the label quality, and pouring effort into the model buys measured gains that the noise floor eats.

The fix is not a cleverer metric — the compression and ceiling are properties of the noisy comparison itself — but cleaner or redundant labels: multiple annotators with adjudication, higher-quality references, or explicitly estimating k and correcting for it. And the discipline of knowing your label noise rate, so that when a model's measured score approaches 1 − k you recognize you have hit the wall and stop attributing the plateau to the model. A measured score means nothing without knowing the quality of what it was measured against.

**Measured = a(1−k) + (1−a)k, so the ceiling is 1−k and every gain is scaled by 1−2k; past the noise floor, label quality, not the model, is the bottleneck.**

## Worked example

The fixture is a label noise rate and three models of increasing true accuracy.

```json filename=modules/evals-and-statistics/code/evals-inter-11/eval.json:7-12 COMPLETE
  "label_noise": 0.1,
  "models": {
    "good": 0.95,
    "better": 0.99,
    "perfect": 1.0
  }
```

Ten percent of labels are wrong. The models are 95%, 99%, and 100% truly accurate. The measured accuracy is the agreement formula.

```python filename=modules/evals-and-statistics/code/evals-inter-11/labelnoise.py:39-41 COMPLETE
def measured_accuracy(true_acc, k):
    """Agreement with a noisy label: right when both right, or both wrong the same way. Capped at 1-k."""
    return round(true_acc * (1 - k) + (1 - true_acc) * k, 4)
```

The ceiling is one minus the noise.

```python filename=modules/evals-and-statistics/code/evals-inter-11/labelnoise.py:44-45 COMPLETE
def ceiling(k):
    return round(1 - k, 4)
```

Look at each model's true accuracy against what the eval measures.

```text filename=modules/evals-and-statistics/code/evals-inter-11/labelnoise.py --models
MODELS — true accuracy vs what a 10%-noisy eval measures
----------------------------------------------------
  good     true 0.95   measured 0.860
  better   true 0.99   measured 0.892
  perfect  true 1.00   measured 0.900
----------------------------------------------------
  every measured score is below the true one -- the noise costs each model points.
```

Every measured score is well below the true one. The good model's real 0.95 shows as 0.860; the perfect model's 1.00 shows as 0.900. Now the ceiling view makes the two consequences explicit.

<svg role="img" aria-label="Each model's true accuracy bar and its lower measured bar, all measured bars below the 0.90 ceiling line" viewBox="0 0 460 180" width="460" height="180">
  <rect x="0" y="0" width="460" height="180" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">true (light) vs measured (dark), ceiling at 0.90</text>
  <line x1="50" y1="150" x2="440" y2="150" stroke="var(--line)"/>
  <line x1="50" y1="55" x2="440" y2="55" stroke="var(--acc-ink)" stroke-dasharray="4 3"/><text x="360" y="51" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">ceiling 0.90</text>
  <line x1="50" y1="40" x2="440" y2="40" stroke="var(--grid)" stroke-dasharray="2 2"/><text x="20" y="44" font-family="var(--mono)" font-size="8" fill="var(--muted)">1.0</text>
  <g stroke="var(--line)">
    <rect x="90" y="45" width="34" height="105" fill="var(--acc-soft)"/><rect x="124" y="66" width="34" height="84" fill="var(--s1)"/>
    <rect x="220" y="41" width="34" height="109" fill="var(--acc-soft)"/><rect x="254" y="59" width="34" height="91" fill="var(--s1)"/>
    <rect x="350" y="40" width="34" height="110" fill="var(--acc-soft)"/><rect x="384" y="55" width="34" height="95" fill="var(--acc-line)"/>
  </g>
  <text x="96" y="166" font-family="var(--mono)" font-size="8" fill="var(--muted)">good .95/.86</text>
  <text x="222" y="166" font-family="var(--mono)" font-size="8" fill="var(--muted)">better .99/.89</text>
  <text x="352" y="166" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">perfect 1.0/.90</text>
</svg>
^ Each model's measured bar sits below its true bar and below the 0.90 ceiling; the perfect model's measured bar rests exactly on the ceiling line.

```text filename=modules/evals-and-statistics/code/evals-inter-11/labelnoise.py --ceiling
CEILING — the highest possible measured score is 1 - k = 0.90
------------------------------------------------------------
  a perfect model (true 1.00) measures 0.900  (= the ceiling 0.90)
  good -> perfect: true gap 0.050, measured gap 0.040  (compressed by 1-2k = 0.80)
------------------------------------------------------------
  no model can measure above the ceiling; gains near it shrink in the measurement.
```

The perfect model measures 0.900, exactly the ceiling — a flawless model cannot score above 90% against 10%-noisy labels. And the gap from good to perfect, truly 0.05, measures as 0.040: the improvement is real but the eval shows only four-fifths of it, scaled by the 1 − 2k = 0.80 factor. If you were choosing between the good and perfect models on this eval, a 0.05 true difference has been squeezed to 0.04, and a fifth of your signal disappeared into the label noise.

<svg role="img" aria-label="The good-to-perfect gap: a true gap of 0.05 shown wide, and the measured gap of 0.04 shown narrower, compressed by the 0.8 factor" viewBox="0 0 460 130" width="460" height="130">
  <rect x="0" y="0" width="460" height="130" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="22" font-family="var(--mono)" font-size="11" fill="var(--muted)">good→perfect gap: true vs measured</text>
  <text x="30" y="52" font-family="var(--mono)" font-size="10" fill="var(--ink)">true</text>
  <rect x="120" y="42" width="250" height="16" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="376" y="55" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">0.050</text>
  <text x="30" y="92" font-family="var(--mono)" font-size="10" fill="var(--ink)">measured</text>
  <rect x="120" y="82" width="200" height="16" fill="var(--s2)" stroke="var(--line)"/><text x="326" y="95" font-family="var(--mono)" font-size="10" fill="var(--s2)">0.040</text>
  <text x="120" y="120" font-family="var(--mono)" font-size="9" fill="var(--muted)">a fifth of the real improvement (×0.8) is eaten by the label noise</text>
</svg>
^ The real 0.05 improvement measures as 0.04 — the label noise scales every gain by 1−2k, so a fifth of the signal is lost before you can see it.

<svg role="img" aria-label="Measured accuracy versus true accuracy: a line that would reach 1.0 if labels were clean but flattens to a ceiling at 0.90, with the three models plotted below it" viewBox="0 0 460 200" width="460" height="200">
  <rect x="0" y="0" width="460" height="200" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">measured vs true accuracy (10% label noise)</text>
  <line x1="50" y1="170" x2="50" y2="40" stroke="var(--line)"/>
  <line x1="50" y1="170" x2="430" y2="170" stroke="var(--line)"/>
  <text x="20" y="45" font-family="var(--mono)" font-size="9" fill="var(--muted)">1.0</text><text x="410" y="185" font-family="var(--mono)" font-size="9" fill="var(--muted)">true 1.0</text>
  <line x1="50" y1="170" x2="410" y2="50" stroke="var(--grid)" stroke-dasharray="4 3"/><text x="300" y="60" font-family="var(--mono)" font-size="9" fill="var(--muted)">if labels were clean (y=x)</text>
  <line x1="50" y1="62" x2="430" y2="62" stroke="var(--acc-ink)" stroke-dasharray="3 2"/><text x="330" y="58" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">ceiling 0.90</text>
  <line x1="50" y1="150" x2="410" y2="62" stroke="var(--s1)" stroke-width="2"/><text x="120" y="120" font-family="var(--mono)" font-size="9" fill="var(--ink)">measured (slope 1−2k)</text>
  <circle cx="360" cy="76" r="4" fill="var(--s2)"/><text x="330" y="92" font-family="var(--mono)" font-size="8" fill="var(--s2)">good 0.86</text>
  <circle cx="398" cy="65" r="4" fill="var(--s2)"/>
  <circle cx="410" cy="62" r="5" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="330" y="46" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">perfect 0.90 = ceiling</text>
</svg>
^ The clean-label line would climb to 1.0, but the measured line rises at slope 1−2k and flattens against the 0.90 ceiling — the perfect model lands on the ceiling, not at 1.0.

## Build

Reproduce the measured scores. Pure arithmetic, so 0.860, 0.892, 0.900 and the 0.040 gap come out exactly.

Run `--models` for the scores, `--ceiling` for the two consequences, `--check` for the gate. The self-test pins all four: no score exceeds the ceiling, a perfect model hits it, real gains compress, and the ranking is still preserved.

```python filename=modules/evals-and-statistics/code/evals-inter-11/labelnoise.py:84-88 COMPLETE
    all_below_ceiling = all(measured_accuracy(a, k) <= cap + 1e-9 for a in models.values())
    print("  no model measures above the ceiling 1-k = %s (cap %.2f)" % (all_below_ceiling, cap))

    perfect_hits_ceiling = abs(measured_accuracy(1.0, k) - cap) < 1e-9
    print("  a perfect model measures exactly the ceiling, not 1.0 = %s (%.3f)" % (perfect_hits_ceiling, measured_accuracy(1.0, k)))
```

The `perfect_hits_ceiling` check is the one that turns the abstract ceiling into a concrete, falsifiable claim: it asserts that a truly perfect model measures *exactly* 1 − k, to within floating-point error, not merely "less than 1." That exactness is the point — the ceiling is not a fuzzy tendency, it is the precise value 1 − k, and a perfect model lands on it every time. The gain-compression check completes the picture.

```python filename=modules/evals-and-statistics/code/evals-inter-11/labelnoise.py:90-96 COMPLETE
    lo = min(models, key=lambda n: models[n])
    hi = max(models, key=lambda n: models[n])
    true_gap = models[hi] - models[lo]
    meas_gap = measured_accuracy(models[hi], k) - measured_accuracy(models[lo], k)
    gains_compress = meas_gap < true_gap - 1e-9
    print("  a real accuracy gain measures smaller than it is = %s (true %.3f -> measured %.3f)"
          % (gains_compress, round(true_gap, 4), round(meas_gap, 4)))
```

```text filename=modules/evals-and-statistics/code/evals-inter-11/labelnoise.py --check
SELF-TEST — measured is capped at 1-k; a perfect model scores 1-k; real gains measure smaller
----------------------------------------------------------------------------------------
  no model measures above the ceiling 1-k = True (cap 0.90)
  a perfect model measures exactly the ceiling, not 1.0 = True (0.900)
  a real accuracy gain measures smaller than it is = True (true 0.050 -> measured 0.040)
  the better model still ranks higher (order preserved) = True
----------------------------------------------------------------------------------------
SELF-TEST PASS  all_below_ceiling=True  perfect_hits_ceiling=True  gains_compress=True  ranking_preserved=True
```

Four True flags. All_below_ceiling: nothing measures above 1 − k. Perfect_hits_ceiling: a perfect model lands exactly on it. Gains_compress: a real 0.05 gain measures as 0.04. Ranking_preserved: the better model still scores higher, so the eval is not useless — it still orders models correctly here, it just understates the levels and gaps. That last flag matters: label noise degrades your measurement without necessarily inverting your ranking, which is why it is easy to miss.

**The perfect-hits-ceiling check asserts a truly perfect model measures exactly 1−k, making the ceiling a precise falsifiable value rather than a vague tendency.**

## Definition of done

You are done when you reproduce the scores and can explain the ceiling and the compression.

Concretely: `--models` shows the perfect model measuring 0.900 against 10%-noisy labels; `--check` prints PASS with four True flags. You can write the measured-accuracy formula a(1−k) + (1−a)k and derive both the ceiling (set a = 1) and the compression slope (differentiate: 1 − 2k). You can explain why a correct model is penalized on a mislabeled item, and why a measured score at or above 1 − k means your labels are the bottleneck, not your model. And you can name the fix — cleaner or redundant labels, or estimating and correcting for k — rather than a different metric.

The habit to carry: know your label noise rate, and interpret every accuracy against the ceiling it implies. When a model's measured accuracy plateaus near 1 − k, stop blaming the model and start auditing the labels; when comparing two strong models, remember their true gap is larger than the measured one and budget more evaluation data or better labels to resolve it.

## Boss fight

The instructive failure is a team that spends a quarter chasing accuracy points that the answer key had already made unreachable.

A team's model measures 91% on a benchmark whose labels, unbeknownst to them, are about 8% noisy — a ceiling of 92%. They set a goal of 95% and spend months on model improvements. Measured accuracy crawls from 91% to 91.8% and stalls, and every experiment looks like a failure, because the ceiling is 92% and they are pressed against it. The model may genuinely be improving — its true accuracy climbing from 96% to 99% — but the noisy labels compress and cap all of it into a fraction of a point of measured gain. The correct move, invisible without knowing k, was to clean the labels: re-annotate the benchmark, and the "stuck" model reveals the gains that were there all along. They optimized the model when the bottleneck was the ruler.

Your turn, two moves. First, find where the model stops mattering. With 10% noise, compute the true accuracy at which a model reaches, say, 0.88 measured — solve 0.88 = a(0.9) + (1−a)(0.1) for a — and you get a ≈ 0.975, so once the model is 97.5% accurate it is within 0.02 of the ceiling and further model gains are nearly invisible. That number tells you when to switch from improving the model to improving the labels. Second, watch the noise rate dominate. Double the label noise to 20% and predict: the ceiling drops to 0.80, the perfect model now measures 0.80, and the compression factor falls to 1 − 2(0.2) = 0.6, so the same 0.05 true gap now measures as 0.03. The dirtier the labels, the lower the ceiling and the harder it is to tell good models apart — which is why benchmark label quality is not a detail but the thing that decides whether the benchmark can measure the models you care about at all.

## External resources

The measurement-error and "noisy labels" literature in machine learning quantifies exactly this; surveys on learning with label noise derive the same a(1−k) + (1−a)k relationship and its consequences for evaluation.

For the benchmark-quality angle, work auditing popular benchmarks for label errors — for example "Pervasive Label Errors in Test Sets" (Northcutt et al.) — measures real k on datasets like ImageNet and shows how it distorts model rankings, the empirical face of this module's ceiling.

For the fix, the inter-annotator-agreement and adjudication literature (multiple raters, majority or expert adjudication, Cohen's and Fleiss' kappa) is how practitioners drive k down and estimate what remains, so a measured score can be interpreted against a known ceiling.
