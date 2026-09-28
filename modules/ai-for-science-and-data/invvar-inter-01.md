---
id: invvar-inter-01
title: Combine measurements by inverse-variance weighting — a simple average of a precise and a noisy measurement is less precise than the precise one alone
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: When several independent measurements estimate one true value, each with its own uncertainty, the instinct is to average them — add the values, divide by the count. That gives every measurement an equal say, which is only right when they are equally precise. When they are not, the simple average treats a measurement good to a tenth of a unit and one good to five units as equals, so the noisy one drags the estimate around, and the cost shows up in the variance: for n measurements the variance of the simple average is the sum of their variances over n squared, dominated by the noisy one. The consequence is stark — a simple average of a precise measurement and a noisy one has a larger variance than the precise measurement by itself, so averaging in the bad data made you less certain than you already were. On the fixture the truth is 100; the precise measurement reads 98 with sigma 1 and the noisy one reads 110 with sigma 5, and the simple average is 104 with variance 6.5 (sigma 2.55) — worse than the precise measurement's variance of 1. The minimum-variance unbiased combination weights each measurement by one over its variance: the precise one gets weight 0.962, the noisy one 0.038, the estimate is 98.46 with variance 0.96 (sigma 0.98) — below every single measurement, including the best — and it lands closer to the truth. The rule: to combine measurements of one quantity, weight each by its precision (inverse variance), because a simple average lets a noisy measurement degrade a precise one, while inverse-variance weighting always beats even the best single measurement.
eli5: Suppose two people guess the temperature: one has a good thermometer and says 98 degrees, the other has a broken thermometer and says 110. If you just split the difference and say 104, you have let the broken thermometer pull your answer way off — you would have done better trusting the good thermometer alone and saying 98. The smart move is to trust each guess in proportion to how good their thermometer is: give the good thermometer almost all the say and the broken one barely any, landing near 98. Then your combined guess is actually better than either person's on their own, because you used the good measurement fully and let the bad one nudge you only a tiny bit.
---

## Why this module

Combining measurements is everywhere: two sensors reading the same value, several lab replicates, a meta-analysis pooling studies, a Kalman filter fusing a prediction with an observation. The default move is to average them, and averaging feels safe — surely more data cannot hurt.

It can. Averaging assumes the things you average are interchangeable, and measurements of different precision are not. A simple average gives a measurement you trust to a hair the same weight as one you barely trust at all, so the untrustworthy one gets to drag the result and inflate its uncertainty. Add a bad enough measurement to a good one, average them, and you come out less certain than you were with the good one alone — you paid for more data and it made you worse.

This module measures that directly. The precise measurement has variance 1; the simple average of it with a noisy measurement has variance 6.5 — worse. Then it weights each measurement by its precision instead, and the combined variance drops to 0.96, below even the precise measurement, and the estimate moves closer to the truth. The whole difference is whether the combination respects how much each measurement is worth.

**Averaging measurements of unequal precision lets the noisy ones vote as loudly as the precise ones, so the simple average can be less certain than the single best measurement — more data made worse by giving the worst of it equal weight.**

## Concepts

A measurement of a quantity comes with a variance — the square of its standard deviation — that says how much it would scatter if you repeated it. Combining measurements is choosing weights that sum to one and taking the weighted sum of the values; the simple average is the special case of equal weights. The question is which weights give the combined estimate the smallest variance.

For the simple average of n independent measurements, the variance is the sum of their variances divided by n squared. Read that carefully: dividing by n squared helps, but the numerator is the sum of variances, so one large variance dominates it. With a precise measurement (variance 1) and a noisy one (variance 25), the simple average's variance is (1 + 25) / 4 = 6.5 — six and a half times worse than the precise measurement, because the noisy measurement's 25 is still in the sum and only halved twice.

That is the failure in one line: the simple average of a precise and a noisy measurement is less precise than the precise measurement standing alone. Averaging did not combine information, it diluted the good measurement with the bad one. Any procedure that can do worse than throwing away half your data is doing something wrong, and what it is doing wrong is equal weighting.

The fix is to weight each measurement by its precision — one over its variance. The precise measurement, with the small variance, has a large inverse variance and gets most of the weight; the noisy one gets a little. This inverse-variance weighting is the minimum-variance unbiased linear combination — no other weights give a smaller variance — and its combined variance is one over the sum of the inverse variances. That quantity is always smaller than any single measurement's variance, so inverse-variance weighting always improves on even the best measurement, exactly the property the simple average lost.

<svg role="img" aria-label="A number line around the true value 100. The precise measurement sits at 98 with a narrow error bar. The noisy measurement sits at 110 with a wide error bar. The simple average sits at 104, pulled toward the noisy one, with a medium-wide error bar. The truth is marked at 100." viewBox="0 0 640 200">
<line x1="40" y1="150" x2="600" y2="150" stroke="var(--line)" stroke-width="1"/>
<line x1="320" y1="40" x2="320" y2="158" stroke="var(--grid)" stroke-width="1" stroke-dasharray="3 3"/>
<text x="320" y="176" fill="var(--muted)" font-size="10" text-anchor="middle">truth = 100</text>
<line x1="240" y1="70" x2="256" y2="70" stroke="var(--s1)" stroke-width="2"/>
<circle cx="248" cy="70" r="4" fill="var(--s1)"/>
<text x="248" y="60" fill="var(--muted)" font-size="10" text-anchor="middle">precise 98 ±1</text>
<line x1="440" y1="100" x2="600" y2="100" stroke="var(--s2)" stroke-width="2"/>
<circle cx="520" cy="100" r="4" fill="var(--s2)"/>
<text x="520" y="90" fill="var(--muted)" font-size="10" text-anchor="middle">noisy 110 ±5</text>
<line x1="360" y1="130" x2="440" y2="130" stroke="var(--ink)" stroke-width="2"/>
<circle cx="400" cy="130" r="4" fill="var(--ink)"/>
<text x="400" y="120" fill="var(--muted)" font-size="10" text-anchor="middle">simple avg 104 ±2.55</text>
</svg>
^ The simple average sits between the two measurements, pulled off the truth toward the noisy one, and its error bar is wider than the precise measurement's — the average is both biased toward noise and less certain.

**The variance of the simple average carries the noisy measurement's full variance in its numerator, so it cannot beat the precise measurement, while inverse-variance weighting down-weights the noise and its combined variance drops below every single measurement.**

## Worked example

The fixture is a precise and a noisy measurement of a true value of 100.

```json filename=modules/ai-for-science-and-data/code/invvar-inter-01/invvar.json:3-7 COMPLETE
  "true_value": 100.0,
  "measurements": [
    {"name": "precise", "value": 98.0, "sigma": 1.0},
    {"name": "noisy", "value": 110.0, "sigma": 5.0}
  ]
```

The simple average weights both equally, and its variance is the sum of variances over n squared.

```python filename=modules/ai-for-science-and-data/code/invvar-inter-01/invvar.py:30-35 COMPLETE
def simple_estimate(measurements):
    """The plain average and its variance: sum of variances over n squared (every measurement weighted equally)."""
    n = len(measurements)
    mean = sum(m["value"] for m in measurements) / n
    variance = sum(m["sigma"] ** 2 for m in measurements) / n ** 2
    return {"mean": mean, "variance": variance}
```

Inverse-variance weights are one over each variance, normalized.

```python filename=modules/ai-for-science-and-data/code/invvar-inter-01/invvar.py:38-42 COMPLETE
def inverse_variance_weights(measurements):
    """Each measurement's weight is one over its variance, normalized -- precision, not headcount."""
    raw = [1.0 / m["sigma"] ** 2 for m in measurements]
    total = sum(raw)
    return [w / total for w in raw]
```

The weighted estimate uses those weights, and its variance is one over the sum of inverse variances.

```python filename=modules/ai-for-science-and-data/code/invvar-inter-01/invvar.py:45-50 COMPLETE
def weighted_estimate(measurements):
    """The inverse-variance-weighted mean and its variance: 1 / sum of inverse variances."""
    inv = [1.0 / m["sigma"] ** 2 for m in measurements]
    mean = sum(m["value"] * w for m, w in zip(measurements, inv)) / sum(inv)
    variance = 1.0 / sum(inv)
    return {"mean": mean, "variance": variance}
```

The simple average comes out less precise than the precise measurement alone.

```text filename=invvar.py --simple
SIMPLE — the plain average, every measurement weighted equally
----------------------------------------------------------------
  precise  = 98.0  (sigma 1.0)
  noisy    = 110.0  (sigma 5.0)
  simple average = 104.0000   variance 6.5000 (sigma 2.5495)
  best single measurement variance 1.0000 (sigma 1.0000)
----------------------------------------------------------------
  the average is LESS precise than the precise measurement alone -- the noisy one dragged it
```

Variance 6.5 against the precise measurement's 1.0 — the average is six and a half times less certain. The weighted estimate flips it.

```text filename=invvar.py --weighted
WEIGHTED — inverse-variance (precision) weighting
----------------------------------------------------------------
  precise  weight 0.962  (sigma 1.0)
  noisy    weight 0.038  (sigma 5.0)
  weighted estimate = 98.4615   variance 0.9615 (sigma 0.9806)
  best single measurement variance 1.0000 (sigma 1.0000)
----------------------------------------------------------------
  the estimate is MORE precise than any single measurement, and closer to the truth
```

The precise measurement takes 96.2% of the weight, the noisy one 3.8%, and the combined variance 0.96 is below the precise measurement's 1.0 — combining now helps. The figure compares the three variances.

<svg role="img" aria-label="A bar chart of variance for four things: the noisy measurement at 25, the simple average at 6.5, the precise measurement at 1.0, and the inverse-variance-weighted estimate at 0.96. A dashed line marks the precise measurement's variance of 1; the simple average is above it, the weighted estimate below it." viewBox="0 0 640 240">
<line x1="60" y1="200" x2="600" y2="200" stroke="var(--line)" stroke-width="1"/>
<line x1="60" y1="192" x2="600" y2="192" stroke="var(--grid)" stroke-width="1" stroke-dasharray="4 3"/>
<text x="608" y="196" fill="var(--muted)" font-size="9">var 1.0</text>
<rect x="90" y="40" width="80" height="160" fill="var(--s2)" opacity="0.6"/>
<text x="130" y="216" fill="var(--muted)" font-size="10" text-anchor="middle">noisy</text>
<text x="130" y="32" fill="var(--muted)" font-size="10" text-anchor="middle">25.0</text>
<rect x="220" y="158" width="80" height="42" fill="var(--ink)"/>
<text x="260" y="216" fill="var(--muted)" font-size="10" text-anchor="middle">simple avg</text>
<text x="260" y="150" fill="var(--muted)" font-size="10" text-anchor="middle">6.5</text>
<rect x="350" y="186" width="80" height="14" fill="var(--muted)"/>
<text x="390" y="216" fill="var(--muted)" font-size="10" text-anchor="middle">precise</text>
<text x="390" y="178" fill="var(--muted)" font-size="10" text-anchor="middle">1.0</text>
<rect x="480" y="187" width="80" height="13" fill="var(--s1)"/>
<text x="520" y="216" fill="var(--muted)" font-size="10" text-anchor="middle">weighted</text>
<text x="520" y="179" fill="var(--s1)" font-size="10" text-anchor="middle">0.96</text>
</svg>
^ The simple average's variance (6.5) sits well above the precise measurement's (1.0); only the inverse-variance-weighted estimate (0.96) drops below it.

**Weighting the precise measurement at 0.962 and the noisy one at 0.038 is the whole fix — the simple average's fatal choice was 0.5 and 0.5, giving the noisy measurement a hundred times more say than its precision warranted.**

## Build

The self-test pins the reversal: the simple average is less precise than the best single measurement, while the weighted estimate is more precise than it — and more precise than the simple average.

```python filename=modules/ai-for-science-and-data/code/invvar-inter-01/invvar.py:103-110 COMPLETE
    simple_worse_than_best = simple["variance"] > best
    print("  the simple average is LESS precise than the best single measurement = %s (var %.4f > %.4f)" % (simple_worse_than_best, simple["variance"], best))

    weighted_better_than_best = weighted["variance"] < best
    print("  the weighted estimate is MORE precise than the best single measurement = %s (var %.4f < %.4f)" % (weighted_better_than_best, weighted["variance"], best))

    weighted_beats_simple = weighted["variance"] < simple["variance"]
    print("  the weighted estimate is more precise than the simple average = %s (%.4f < %.4f)" % (weighted_beats_simple, weighted["variance"], simple["variance"]))
```

The remaining flags confirm the weights favor the precise measurement and the weighted estimate lands closer to the truth. All five pass.

```text filename=invvar.py --check
SELF-TEST — the simple average is less precise than the best single measurement while the weighted estimate is more precise, and the weights favor the precise measurement
----------------------------------------------------------------------------------------------------------------
  the simple average is LESS precise than the best single measurement = True (var 6.5000 > 1.0000)
  the weighted estimate is MORE precise than the best single measurement = True (var 0.9615 < 1.0000)
  the weighted estimate is more precise than the simple average = True (0.9615 < 6.5000)
  the precise measurement gets more weight than the noisy one = True (0.962 vs 0.038)
  the weighted estimate lands closer to the truth = True (|98.46-100|<|104.00-100|)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  simple_worse_than_best=True  weighted_better_than_best=True  weighted_beats_simple=True  precise_gets_more_weight=True  weighted_closer_to_truth=True
```

**"Simple worse than best, weighted better than best" is the entire lesson in two flags: the same two measurements make you less certain under equal weighting and more certain under precision weighting.**

## Definition of done

You are done when you combine independent measurements of one quantity by inverse-variance weighting — each measurement weighted by one over its variance, with the combined variance one over the sum of the inverse variances — whenever the measurements' precisions differ and you know them.

This is the same operation under many names, so recognize it: the fixed-effect meta-analysis weights studies by inverse variance; the Kalman filter's update is an inverse-variance blend of the prediction and the observation; the best linear unbiased estimator (BLUE) for a mean under known, unequal variances is exactly this. The prerequisites are that the measurements are unbiased and independent, and that you know each variance (at least up to a common factor, since only relative precisions set the weights). Two cautions. If the variances are wrong — you trust a measurement more than it deserves — the weighting misplaces the estimate, so the weights are only as good as the uncertainties feeding them; when you do not know the precisions, you must estimate them or fall back to the simple average as the honest default. And if the measurements are correlated, plain inverse-variance weighting is not optimal — the correlations belong in the combination (a full covariance-weighted, or generalized-least-squares, estimate), because two correlated measurements carry less independent information than their separate variances suggest.

<svg role="img" aria-label="A diagram: several measurements each with a variance feed into a weighting box where weight equals one over variance, producing a combined estimate whose variance is one over the sum of the inverse variances, smaller than any input." viewBox="0 0 640 190">
<rect x="30" y="40" width="120" height="30" fill="var(--panel)" stroke="var(--line)" stroke-width="1.5" rx="5"/>
<text x="90" y="59" fill="var(--ink)" font-size="10" text-anchor="middle">x1, variance v1</text>
<rect x="30" y="110" width="120" height="30" fill="var(--panel)" stroke="var(--line)" stroke-width="1.5" rx="5"/>
<text x="90" y="129" fill="var(--ink)" font-size="10" text-anchor="middle">x2, variance v2</text>
<line x1="150" y1="55" x2="240" y2="80" stroke="var(--line)" stroke-width="1"/>
<line x1="150" y1="125" x2="240" y2="100" stroke="var(--line)" stroke-width="1"/>
<rect x="240" y="66" width="160" height="48" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="320" y="86" fill="var(--ink)" font-size="10" text-anchor="middle">weight each by 1/variance</text>
<text x="320" y="102" fill="var(--muted)" font-size="10" text-anchor="middle">(precision weighting)</text>
<line x1="400" y1="90" x2="450" y2="90" stroke="var(--line)" stroke-width="1"/>
<polygon points="450,90 442,85 442,95" fill="var(--line)"/>
<rect x="450" y="66" width="170" height="48" fill="var(--panel)" stroke="var(--ink)" stroke-width="1.5" rx="6"/>
<text x="535" y="86" fill="var(--ink)" font-size="10" text-anchor="middle">combined estimate,</text>
<text x="535" y="102" fill="var(--muted)" font-size="10" text-anchor="middle">variance = 1 / Σ(1/vᵢ)</text>
</svg>
^ Weight each measurement by its precision and the combined variance is one over the sum of the inverse variances — provably below every input's variance.

**Inverse-variance weighting is the one combination that always improves on the best single measurement, so when precisions differ and are known, a simple average is not a safe default but a choice to throw precision away.**

## Boss fight

Your turn: make the noisy measurement noisier and watch the simple average get catastrophically worse while the weighted estimate barely moves. Raise the noisy measurement's sigma to 20 and rerun both views. The simple average's variance climbs toward (1 + 400) / 4 ≈ 100 — a hundred times worse than the precise measurement — because a wilder noisy measurement drags an equal-weighted average even harder. The weighted estimate barely changes: the noisy measurement's weight, one over 400, is now negligible, so precision weighting has all but discarded it and the combined variance stays just under 1. This is the tell for how much equal weighting costs: it scales with the worst measurement's variance, while precision weighting scales with the best measurement's. The gap between them widens without bound as the measurements' precisions diverge.

Then break the assumption that makes the weights right. Suppose you did not actually know the noisy measurement's sigma and guessed it was 1, the same as the precise one — you trusted a bad measurement as much as a good one. Now inverse-variance weighting reduces to the simple average, and you are back to variance 6.5, because the weights are only as good as the variances you feed them. This is the real discipline: precision weighting is optimal given correct uncertainties, and its power is entirely borrowed from knowing how much to trust each measurement. A confidently wrong uncertainty is worse than an honest "I do not know," because it makes the estimator place false confidence exactly where it should be cautious — which is why estimating and validating your measurement uncertainties is as much of the job as the weighting formula itself.

**Inverse-variance weighting turns knowing each measurement's precision into a combined estimate better than any of them, but the whole benefit is borrowed from those precisions — feed it a wrong uncertainty and it confidently weights toward the wrong number, so the weights are only ever as trustworthy as the variances behind them.**

## External resources

Any meta-analysis reference (for example the Cochrane Handbook on fixed-effect models) derives the inverse-variance weighting used to pool studies, and is the most common place practitioners meet this formula.

Treatments of the best linear unbiased estimator (BLUE) and the Gauss-Markov setting show that inverse-variance weighting is the minimum-variance unbiased combination under known, unequal variances, and generalize it to correlated measurements via the covariance matrix.

Introductions to the Kalman filter present its measurement update as an inverse-variance blend of a prediction and an observation, which is this module's two-measurement case run recursively over time.
