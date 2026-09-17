---
id: cuped-inter-01
title: Subtract the pre-experiment covariate (CUPED) to shrink an eval metric's variance — more power from the same units
topic: evals-and-statistics
level: intermediate
status: ready
time: 17 min
summary: An A/B test detects a treatment effect against a background of noise, and most of that noise is not caused by the treatment — it is the pre-existing spread between units. Some users, tasks, or shards simply score higher than others for reasons that predate the experiment, and that variation sits in your metric inflating its variance, widening the confidence interval, and forcing more data to resolve a small real effect. The wasteful part is that this pre-existing spread is often known: you measured each unit in a baseline period, so the variance you fight is variance you could subtract out. CUPED does exactly that — for each unit take a pre-experiment covariate x correlated with the metric y and form an adjusted metric y' = y − θ(x − mean(x)), where θ = Cov(x,y)/Var(x). The adjustment removes the part of each unit's y its baseline already predicted while leaving the treatment effect untouched, so y' has the same mean as y (unbiased) but variance lower by the factor 1 − ρ². On a fixture where the covariate correlates 0.91 with the metric, CUPED leaves the mean at 21.25 exactly but drops the variance from 25.69 to 4.18 — a 6× effective-sample-size gain from data you already had.
eli5: You want to see if a new coaching method makes runners faster, but runners differ a lot to begin with — some were fast before you did anything. That built-in difference makes it hard to spot the coaching's effect in the noise. But you already have each runner's time from before the program. Subtract off what their old time predicts about their new time, and what's left is much less noisy — the runners are now on a level field, so a small improvement from the coaching stands out. You didn't run more races; you just used the times you already had to cancel out the differences that were never about the coaching.
---

## Why this module

The confidence interval on a treatment effect is set by the metric's variance, and most of that variance is pre-existing differences between units that have nothing to do with the treatment — so if you already measured those differences, you are fighting noise you could have removed.

An experiment estimates how much a change moved a metric, and its precision is limited by how noisy the metric is: the wider the metric's variance, the wider the confidence interval on the effect, and the more units you need to tell a real effect from zero. But decompose that variance and most of it is not experimental noise at all — it is that units differ. One user was always more active, one task was always harder, one shard always ran slower, for reasons fixed before the experiment began. That between-unit spread enters both arms of the test equally, so it does not bias the effect estimate, but it does inflate its variance, and inflated variance is exactly what forces you to collect more data. The frustrating part is that this spread is frequently *known*: you have each unit's metric from a baseline period, before any treatment. The noise you are struggling to overcome is noise you already measured and could subtract.

**A metric's variance is dominated by pre-existing, treatment-irrelevant differences between units, which widen every confidence interval — and when those differences were measured in a baseline period, they are noise you can remove rather than out-sample.**

CUPED — Controlled-experiment Using Pre-Experiment Data — removes it. Take a pre-experiment covariate x for each unit (its baseline-period metric), correlated with the experiment metric y, and form the adjusted metric y' = y − θ(x − mean(x)), where θ = Cov(x,y)/Var(x) is the slope of y on x. The subtraction cancels the portion of each unit's y that its pre-experiment level already predicted — the head start that was never about the treatment — while leaving the treatment's contribution intact. The result is unbiased: y' has exactly the same mean as y, so it estimates the same effect. But its variance is smaller by the factor 1 − ρ², where ρ is the correlation between x and y, so a covariate correlated 0.9 with the outcome cuts variance by about 80%, the precision of roughly five times the data. This module adjusts a metric by CUPED and shows the mean hold while the variance collapses.

## Concepts

**The CUPED coefficient θ** is the slope of the metric on the covariate, Cov(x,y)/Var(x) — how much of y a unit of x predicts.

```python filename=modules/evals-and-statistics/code/cuped-inter-01/cuped.py:61-63 COMPLETE
def theta(x, y):
    """The CUPED coefficient: the slope of y on x, Cov(x,y)/Var(x)."""
    return covariance(x, y) / variance(x)
```

**The adjustment** subtracts each unit's predicted head start, y' = y − θ(x − mean(x)). Because it subtracts a term with mean zero, the adjusted metric's mean is unchanged — it stays unbiased.

```python filename=modules/evals-and-statistics/code/cuped-inter-01/cuped.py:66-69 COMPLETE
def cuped_adjust(x, y):
    """The variance-reduced metric y' = y - theta*(x - mean(x)); same mean as y, lower variance."""
    t, mx = theta(x, y), mean(x)
    return [b - t * (a - mx) for a, b in zip(x, y)]
```

**The variance drops by exactly 1 − ρ².** The stronger the covariate's correlation with the metric, the more pre-existing variance it explains and removes, and the tighter the resulting confidence interval.

<svg role="img" aria-label="Metric y scatters widely around its mean; regressing on the covariate x explains most of the spread, so the residual y-prime clusters tightly around the same mean" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">y depends on the pre-period x; subtract the fit, keep the residual</text>
  <line x1="30" y1="86" x2="150" y2="86" stroke="var(--grid)"/><line x1="30" y1="20" x2="30" y2="86" stroke="var(--grid)"/>
  <text x="34" y="18" fill="var(--muted)" font-size="7">y</text><text x="140" y="98" fill="var(--muted)" font-size="7">x</text>
  <line x1="34" y1="80" x2="146" y2="26" stroke="var(--muted)" stroke-dasharray="3 2"/><text x="100" y="34" fill="var(--muted)" font-size="7">slope θ</text>
  <g fill="var(--s2)"><circle cx="46" cy="74" r="2.5"/><circle cx="66" cy="66" r="2.5"/><circle cx="86" cy="52" r="2.5"/><circle cx="106" cy="44" r="2.5"/><circle cx="126" cy="30" r="2.5"/></g>
  <text x="170" y="30" fill="var(--muted)" font-size="7">raw y: wide spread</text>
  <line x1="180" y1="40" x2="290" y2="40" stroke="var(--grid)"/>
  <g fill="var(--s1)"><circle cx="220" cy="40" r="2.5"/><circle cx="235" cy="38" r="2.5"/><circle cx="250" cy="42" r="2.5"/><circle cx="265" cy="39" r="2.5"/><circle cx="280" cy="41" r="2.5"/></g>
  <text x="190" y="58" fill="var(--muted)" font-size="7">y′ = residual: tight around the mean</text>
</svg>
^ The raw metric y varies widely because it tracks the pre-period x; subtracting the fitted line θ·(x − mean x) leaves the residual y′, which clusters tightly around the same mean — the between-unit spread removed, the effect kept.

**Subtract each unit's baseline-predicted level from its metric: the mean is unchanged (still unbiased) but the variance drops by 1 − ρ², so a correlated covariate buys statistical power from data you already collected.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/cuped-inter-01/cuped.py

The fixture is eight units, each with a pre-experiment covariate and an experiment metric that tracks it.

```json filename=modules/evals-and-statistics/code/cuped-inter-01/cuped.json:3-4 COMPLETE
  "x_pre": [10.0, 12.0, 8.0, 14.0, 11.0, 9.0, 13.0, 7.0],
  "y_exp": [23.0, 23.0, 18.0, 26.0, 24.0, 16.0, 28.0, 12.0]
```

Run `--adjust` to apply CUPED.

```text filename=--adjust
ADJUST — raw metric y vs CUPED-adjusted y' = y - theta*(x - mean(x))
------------------------------------------------------------
  theta (slope of y on x) = 2.0238
  x (pre)    y (exp)    y' (adjusted)
  10.0       23.0       24.0119
  12.0       23.0       19.9643
  8.0        18.0       23.0595
  14.0       26.0       18.9167
  11.0       24.0       22.9881
  9.0        16.0       19.0357
  13.0       28.0       22.9405
  7.0        12.0       19.0833
------------------------------------------------------------
  mean:   y = 21.250   y' = 21.250   (unchanged: y' is unbiased)
  variance: y = 25.688   y' = 4.185   (reduced)
```

The slope θ is about 2.02 — each unit of the pre-period covariate predicts roughly two units of the metric. Look at what the adjustment does to the extremes. The unit with x = 14 had the highest raw y at 26, but much of that 26 was predicted by its high baseline; after subtracting θ·(14 − 10.75), its adjusted y′ is 18.9, near the middle. The unit with x = 7 had the lowest raw y at 12, but its low baseline predicted that too, so its adjusted y′ rises to 19.1. The adjustment pulled the units toward each other by removing the head start each one's baseline already explained — and the raw high-baseline and low-baseline units end up close, because what remains is only the part *not* predicted by the baseline. Crucially the mean did not move: raw y averages 21.25 and adjusted y′ averages 21.25, to the digit. The transform is a rotation that squeezes the spread without shifting the center, so it estimates the same quantity — it just estimates it far more precisely, with the variance down from 25.69 to 4.19.

<svg role="img" aria-label="The raw metric spreads from 12 to 28 while the CUPED-adjusted metric clusters near 19 to 24, both centered at 21.25" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">values on the number line (both centered at 21.25)</text>
  <line x1="20" y1="40" x2="290" y2="40" stroke="var(--grid)"/>
  <line x1="155" y1="20" x2="155" y2="86" stroke="var(--ink)" stroke-dasharray="2 2"/><text x="140" y="18" fill="var(--muted)" font-size="7">mean 21.25</text>
  <text x="6" y="34" fill="var(--muted)" font-size="7">raw y</text>
  <g fill="var(--s2)"><circle cx="40" cy="34" r="3"/><circle cx="95" cy="34" r="3"/><circle cx="120" cy="34" r="3"/><circle cx="175" cy="34" r="3"/><circle cx="185" cy="34" r="3"/><circle cx="205" cy="34" r="3"/><circle cx="240" cy="34" r="3"/><circle cx="270" cy="34" r="3"/></g>
  <text x="6" y="64" fill="var(--muted)" font-size="7">y′ CUPED</text>
  <g fill="var(--s1)"><circle cx="120" cy="64" r="3"/><circle cx="130" cy="64" r="3"/><circle cx="150" cy="64" r="3"/><circle cx="160" cy="64" r="3"/><circle cx="170" cy="64" r="3"/><circle cx="180" cy="64" r="3"/><circle cx="195" cy="64" r="3"/></g>
  <text x="6" y="92" fill="var(--muted)" font-size="8">same center, far tighter spread — variance 25.7 → 4.2</text>
</svg>
^ The raw metric spreads across the line while the CUPED-adjusted metric clusters near the center, both averaging 21.25 — the spread removed is the pre-existing between-unit variance, and the center (the estimate) is untouched.

## Build

The variance drop is not arbitrary — it is exactly what the covariate's correlation predicts. Run `--reduce`.

```text filename=--reduce
REDUCE — variance reduction and the power gain
----------------------------------------------------------
  correlation rho(x, y)      = 0.9149
  variance of y              = 25.6875
  variance of y' (CUPED)     = 4.1845
  reduction factor           = 0.1629   (equals 1 - rho^2 = 0.1629)
  effective sample-size gain = 6.1x  (1 / (1 - rho^2))
```

The covariate correlates 0.9149 with the metric, so ρ² = 0.837, and the variance should fall to 1 − 0.837 = 0.163 of its original — which is exactly the measured reduction factor, 4.1845 / 25.6875 = 0.1629. This is an identity, not an approximation: subtracting the least-squares fit of y on x always leaves residual variance equal to Var(y)·(1 − ρ²), because ρ² is by definition the fraction of variance the linear fit explains. The practical payoff is the last line. A confidence interval's width scales with the square root of variance over sample size, so cutting the variance to 16% of its value is the same precision you would have gotten by collecting 1/0.163 ≈ 6.1 times as many units. That is a real, free multiplier on your experiment's power: the same eval, the same units, a confidence interval more than twice as tight, purely from regressing out a baseline you already had. It is why large-scale experimentation platforms apply CUPED by default — and why the single most valuable covariate is usually the same metric measured in the pre-period, which tends to be the most strongly correlated predictor of itself.

<svg role="img" aria-label="The metric variance falls from 25.69 to 4.18, a factor of 1 minus rho-squared equals 0.16, equivalent to 6.1 times the sample size" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">variance (bar); ρ = 0.91</text>
  <line x1="60" y1="18" x2="60" y2="78" stroke="var(--grid)"/>
  <text x="6" y="34" fill="var(--muted)" font-size="8">raw y</text>
  <rect x="60" y="26" width="220" height="14" fill="var(--s2)"/><text x="230" y="37" fill="var(--panel)" font-size="7">25.69</text>
  <text x="6" y="60" fill="var(--muted)" font-size="8">y′ CUPED</text>
  <rect x="60" y="52" width="36" height="14" fill="var(--s1)"/><text x="100" y="63" fill="var(--muted)" font-size="7">4.18 = ×(1−ρ²) = ×0.16</text>
  <text x="6" y="90" fill="var(--muted)" font-size="8">16% of the variance = the precision of ~6× the units, from data already collected</text>
</svg>
^ CUPED cuts the metric variance to 16% of its raw value — exactly the 1 − ρ² the correlation implies — which is the confidence-interval width of roughly six times as many units, gained without any new data.

## Definition of done

The self-test pins the unbiasedness and the exact reduction: the CUPED mean equals the raw mean, the variance is lower, the reduction factor equals 1 − ρ², θ is the slope, and the effective sample size rises.

```python filename=modules/evals-and-statistics/code/cuped-inter-01/cuped.py:110-123 COMPLETE
    mean_unchanged = abs(mean(yp) - mean(y)) < 1e-9
    print("  the CUPED mean equals the raw mean (unbiased) = %s (%.4f)" % (mean_unchanged, mean(yp)))

    variance_reduced = variance(yp) < variance(y)
    print("  the CUPED variance is lower than the raw variance = %s (%.4f < %.4f)" % (variance_reduced, variance(yp), variance(y)))

    matches_identity = abs(variance(yp) / variance(y) - (1 - rho ** 2)) < 1e-9
    print("  the reduction factor equals 1 - rho^2 exactly = %s (%.4f vs %.4f)" % (matches_identity, variance(yp) / variance(y), 1 - rho ** 2))

    theta_is_slope = abs(theta(x, y) - covariance(x, y) / variance(x)) < 1e-12
    print("  theta is the slope Cov(x,y)/Var(x) = %s (%.4f)" % (theta_is_slope, theta(x, y)))

    effective_n_rises = 1 / (1 - rho ** 2) > 1.0
    print("  the effective sample size rises = %s (%.1fx)" % (effective_n_rises, 1 / (1 - rho ** 2)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the adjusted mean is unchanged (unbiased); the variance drops by exactly 1 - rho^2; effective N rises
----------------------------------------------------------------------------------------------------------------
  the CUPED mean equals the raw mean (unbiased) = True (21.2500)
  the CUPED variance is lower than the raw variance = True (4.1845 < 25.6875)
  the reduction factor equals 1 - rho^2 exactly = True (0.1629 vs 0.1629)
  theta is the slope Cov(x,y)/Var(x) = True (2.0238)
  the effective sample size rises = True (6.1x)
```

**Done means variance reduction is proven exact and unbiased: CUPED leaves the metric's mean at 21.25 (identical to the raw metric, so the effect estimate is unchanged) while dropping the variance from 25.69 to 4.19 — a factor of 0.163 that equals 1 − ρ² for the 0.91-correlated covariate, an effective-sample-size gain of 6.1× from data collected before the experiment ran.**

## Boss fight

Predict the two ways CUPED silently breaks its unbiasedness guarantee. It is tempting to reach for any correlated variable and any θ.

The first trap is that the covariate must be pre-experiment — measured *before* treatment could have influenced it — or CUPED introduces bias instead of just removing variance. The entire unbiasedness argument rests on x being independent of the treatment assignment: if x were affected by the experiment (a metric measured during the experiment, or one downstream of the treatment), then subtracting θ·x would subtract part of the treatment effect itself, biasing the estimate toward zero. This is the same rule as never conditioning on a post-treatment variable in causal inference. So the covariate has to be a genuine baseline — last week's number, a pre-registration attribute — and "correlated with the outcome" is necessary but not sufficient; "correlated *and* unaffected by the treatment" is the requirement. A tempting high-correlation covariate that the treatment also moved will quietly shrink your effect.

```python filename=modules/evals-and-statistics/code/cuped-inter-01/cuped.py:57-58 COMPLETE
def correlation(x, y):
    return covariance(x, y) / (variance(x) ** 0.5 * variance(y) ** 0.5)
```

The second trap is that θ is estimated, not known, and estimating it on the same data you analyze can reintroduce bias and overstate the gain in small samples. The 1 − ρ² reduction is a population identity; in a finite sample you plug in an estimated θ̂ and an estimated ρ̂, and both carry sampling error. With few units, θ̂ can overfit — it will always reduce the *in-sample* variance somewhat even if x and y are truly uncorrelated, so a naive reduction factor computed on the same data flatters itself, and the "effective sample size gain" is optimistic. The disciplined versions estimate θ on a separate slice or pool it across a stable history, and they account for the degrees of freedom spent estimating it, so the reported variance reduction is honest out of sample. And CUPED only helps to the extent a good pre-period covariate exists: for a brand-new unit with no history, or a metric with no correlated baseline, ρ is near zero and the technique does nothing. So the honest picture is that CUPED is a large, free power gain *when* you have a pre-experiment covariate that is strongly correlated with the outcome and untouched by the treatment, and estimated with enough data that θ is not itself overfit — three conditions, each of which the small clean fixture here satisfies and real experiments must check.

**CUPED subtracts a pre-experiment covariate's predicted contribution to shrink an eval metric's variance by 1 − ρ² without changing its mean, turning a correlated baseline into an effective-sample-size multiplier — but the covariate must be measured before treatment and unaffected by it (a post-treatment covariate biases the estimate toward zero), and θ is estimated, so on small samples fit it out-of-sample and discount the gain, because CUPED delivers its free power only with a strongly-correlated, treatment-independent, well-estimated baseline.**

## External resources

The CUPED paper (Deng, Xu, Kohavi, Walker, "Improving the Sensitivity of Online Controlled Experiments by Utilizing Pre-Experiment Data") — the derivation of the y − θ(x − x̄) adjustment, the 1 − ρ² variance reduction, and the guidance on choosing and estimating the covariate.

Any reference on variance reduction in experiments — control variates, regression adjustment (ANCOVA), and stratification — the family CUPED belongs to, and the requirement that adjustment covariates be pre-treatment.

The companion "pair the comparison on the same cases" and "bootstrap a confidence interval" modules — pairing is a related variance-reduction technique (removing case-difficulty variance by matching), and the bootstrap is how you would put an honest interval on the CUPED-adjusted effect, so together they cover reducing and then quantifying experimental noise.
