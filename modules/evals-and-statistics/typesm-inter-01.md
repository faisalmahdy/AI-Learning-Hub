---
id: typesm-inter-01
title: A significant result from an underpowered study exaggerates the effect and can flip its sign — Type M and Type S errors
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: A small study that reaches statistical significance feels like the good outcome — you were worried the sample was too small, and it cleared the bar anyway. It is the opposite. The estimator is unbiased: over every possible run the estimated difference averages to the true effect, here 0.50, with errors symmetric around it. The distortion comes from the filter we put after it — we only report, act on, or believe an estimate once it is significant, and conditioning on significance is a selection that keeps the noisy extremes. When the true effect (0.50) is small next to the noise of one run (standard error 1.00), the design is underpowered: it clears the two-sided bar only 7.9% of the time, and the only way to clear it is a large-magnitude estimate. So the runs that survive the filter are all large — the mean estimate among significant results is 2.39 in magnitude, 4.8 times the truth, a Type M (magnitude) error — and because the estimate straddles zero, 8.7% of the significant results point the wrong way, a Type S (sign) error. The face-value reading, "we measured the effect at ~2.4 and it's significant, so the effect is about 2.4," is a selection artifact; a low-power significant estimate bounds nothing and certifies neither magnitude nor direction. The fix is to know the power of the design before you trust a significant number: raise power (more units, less noise) and both errors collapse — at standard error 0.50 power is 17% and Type M falls to 2.5, at 0.25 power is 52% and Type M is 1.4, at 0.10 power is 99.9% and Type M is 1.0 with sign errors gone.
eli5: Imagine you weigh a feather on a bathroom scale that jumps around by a whole pound every time you step on it. The feather really weighs almost nothing, and if you weighed it a thousand times the readings would average out to almost nothing — the scale is honest on average. But suppose you decide to only believe a reading when it's above two pounds. The only way this feather ever shows above two pounds is when the scale jumps way up by luck — so every reading you "believe" says the feather is heavy, and once in a while the scale even jumps to a negative-looking wobble that makes it seem the feather pushed up. Believing only the big readings turns an honest scale into one that always overstates, and sometimes gets the direction backwards. That's what "significant, but from a tiny study" does.
---

## Why this module

You ran a small comparison — two model variants, a modest number of cases — and you were braced for an inconclusive result. Instead the difference came back statistically significant. The natural reaction is relief: the effect was real enough to show through even a small sample, so it must be at least as big as measured, probably bigger.

That reaction is exactly backwards, and this module is about why. The estimator that produced your number is unbiased — run the study endlessly and its estimates average to the truth. Nothing is wrong with the measurement. What is wrong is the step you take next: you only trust the estimate because it is significant, and that filter, applied to an underpowered study, systematically keeps the estimates that noise blew up.

The result is two named errors. The reported effect is several times the true effect — a Type M, or magnitude, error — and a meaningful fraction of significant results have the wrong sign entirely — a Type S, or sign, error. On the fixture here the true effect is 0.50, but the average significant estimate is 2.39 in magnitude, and 8.7% of significant results point the wrong way.

**A significant result from an underpowered study is not reassurance that the effect is real and large — it is a near-guarantee that whatever you report is exaggerated, and a real risk that it is even the wrong sign.**

## Concepts

Start from the sampling distribution: if the true difference between the two arms is `true_effect` and one run measures it with `standard_error` of noise, the estimate you get is a draw from a normal distribution centered at the truth. Averaged over all possible runs, the estimate equals the truth. The estimator is unbiased, and that is not in dispute here.

Significance is a filter on that distribution. A two-sided test at 95% calls a run significant when the estimate is more than `z_threshold` standard errors from zero — here more than 1.96. Power is the fraction of the sampling distribution that lands past that bar. When the true effect is large relative to the noise, almost every run clears the bar and power is near one. When the true effect is small relative to the noise, the bar sits far out in the tails and power is tiny.

The trap lives in that second case. If only a small slice of runs clears the bar, that slice is not a representative sample of the estimator — it is the tails. Every estimate in it is large, because being large is what let it clear the bar. So the mean estimate conditional on significance is far bigger than the true effect: the exaggeration ratio, or Type M error, is the reported magnitude divided by the truth.

And the bar is two-sided. When the effect is small, the sampling distribution straddles zero, so a nonzero slice of the significant runs sits in the far tail on the wrong side of zero — a large estimate with the opposite sign from the truth. The fraction of significant runs that point the wrong way is the Type S error.

The figure shows the whole mechanism: an unbiased bell centered at the small true effect, the two significance bars far out in the tails, and the two shaded slivers — the correct-sign survivors and the wrong-sign survivors — that are all a low-power study ever gets to report.

<svg role="img" aria-label="A normal sampling distribution centered near zero at the true effect, with two significance bars far out in the tails and small shaded regions beyond them; the right tail is the correct-sign survivors, the left tail the wrong-sign survivors" viewBox="0 0 640 300">
<line x1="40" y1="240" x2="600" y2="240" stroke="var(--line)" stroke-width="1"/>
<line x1="320" y1="60" x2="320" y2="248" stroke="var(--grid)" stroke-width="1" stroke-dasharray="3 3"/>
<text x="320" y="262" fill="var(--muted)" font-size="11" text-anchor="middle">0</text>
<path d="M 40 240 C 200 240 250 80 340 80 C 430 80 480 240 600 240" fill="none" stroke="var(--ink)" stroke-width="2"/>
<line x1="196" y1="70" x2="196" y2="248" stroke="var(--s2)" stroke-width="1.5"/>
<line x1="484" y1="70" x2="484" y2="248" stroke="var(--s2)" stroke-width="1.5"/>
<text x="196" y="262" fill="var(--s2)" font-size="11" text-anchor="middle">-1.96</text>
<text x="484" y="262" fill="var(--s2)" font-size="11" text-anchor="middle">+1.96</text>
<path d="M 484 240 C 520 240 545 200 600 240 Z" fill="var(--s1)" opacity="0.55"/>
<path d="M 40 240 C 90 220 150 236 196 240 Z" fill="var(--s2)" opacity="0.55"/>
<text x="352" y="76" fill="var(--muted)" font-size="11" text-anchor="middle">true effect 0.50 (unbiased mean)</text>
<text x="556" y="196" fill="var(--muted)" font-size="10" text-anchor="middle">correct-sign</text>
<text x="556" y="208" fill="var(--muted)" font-size="10" text-anchor="middle">survivors</text>
<text x="96" y="212" fill="var(--muted)" font-size="10" text-anchor="middle">wrong-sign</text>
</svg>
^ The estimator is centered on the truth, but significance keeps only the two tails past ±1.96 — all large in magnitude, and the left sliver has the wrong sign.

**Power is not just the chance of detecting an effect; it is the quality of every estimate you keep, because conditioning on significance turns low power into large-magnitude, sometimes wrong-signed, survivors.**

## Worked example

The fixture is one two-arm comparison with a small true effect and noisy measurement.

```json filename=modules/evals-and-statistics/code/typesm-inter-01/typesm.json:3-8 COMPLETE
  "true_effect": 0.5,
  "standard_error": 1.0,
  "z_threshold": 1.96,
  "grid_lo": -12.0,
  "grid_hi": 12.0,
  "grid_step": 0.002
```

Rather than simulate random runs, we integrate the sampling distribution on a fixed grid, so every number is deterministic. A run counts as significant when its estimate clears the two-sided bar.

```python filename=modules/evals-and-statistics/code/typesm-inter-01/typesm.py:49-51 COMPLETE
def is_significant(estimate, data):
    """A run is 'significant' when its estimate clears the two-sided bar |estimate| > z*se."""
    return abs(estimate) > data["z_threshold"] * data["standard_error"]
```

Look first at the whole sampling distribution, before any filter. The estimator is unbiased and the study is badly underpowered.

```text filename=typesm.py --sample
SAMPLE — the sampling distribution of the estimate (all possible runs)
--------------------------------------------------------
  true effect            = 0.5000
  standard error (1 run) = 1.0000
  mean estimate over ALL runs = 0.5000  (unbiased: equals the truth)
  significance bar |estimate| > 1.9600
  power = P(significant)  = 0.0792
```

The mean over all runs is exactly 0.5000 — the estimator has no bias. But only 7.9% of runs clear the bar. Now filter to just those significant runs, the ones you would actually report, and the picture inverts.

```text filename=typesm.py --filter
FILTER — only the runs that reached significance (the ones we would report)
--------------------------------------------------------
  true effect                    = 0.5000
  mean estimate | significant    = 1.9936
  mean |estimate| | significant  = 2.3937
  exaggeration ratio (Type M)    = 4.7874  (reported magnitude / truth)
  wrong-sign rate  (Type S)      = 0.0875  (8.7% point the wrong way)
```

The same honest estimator, seen only through the significance filter, reports an average magnitude of 2.39 against a truth of 0.50 — 4.8 times too big — and 8.7% of the significant results have the wrong sign. The number line makes the gap concrete: the truth sits just right of zero, the reported significant estimate sits far out, and a thin wrong-sign slice sits symmetrically on the left.

<svg role="img" aria-label="A number line with zero in the center, the true effect marked just right of zero at 0.5, the mean significant estimate marked far to the right at about 2.4, and a small wrong-sign marker far to the left at about minus 2.4" viewBox="0 0 640 200">
<line x1="40" y1="110" x2="600" y2="110" stroke="var(--line)" stroke-width="1"/>
<line x1="320" y1="70" x2="320" y2="150" stroke="var(--grid)" stroke-width="1" stroke-dasharray="3 3"/>
<text x="320" y="166" fill="var(--muted)" font-size="11" text-anchor="middle">0</text>
<circle cx="345" cy="110" r="5" fill="var(--s1)"/>
<text x="345" y="96" fill="var(--muted)" font-size="11" text-anchor="middle">truth 0.50</text>
<circle cx="520" cy="110" r="6" fill="var(--ink)"/>
<text x="520" y="96" fill="var(--muted)" font-size="11" text-anchor="middle">reported 2.39</text>
<circle cx="120" cy="110" r="5" fill="var(--s2)"/>
<text x="120" y="96" fill="var(--muted)" font-size="11" text-anchor="middle">wrong-sign -2.39</text>
<line x1="345" y1="128" x2="520" y2="128" stroke="var(--s1)" stroke-width="1.5"/>
<text x="432" y="142" fill="var(--muted)" font-size="10" text-anchor="middle">Type M gap: 4.8x</text>
<text x="120" y="142" fill="var(--muted)" font-size="10" text-anchor="middle">Type S: 8.7%</text>
</svg>
^ The reported significant estimate (2.39) sits nearly five times as far from zero as the truth (0.50), and a small wrong-signed population sits mirror-image on the left.

**The estimator averaged 0.50 over all runs and 2.39 over the significant ones — same estimator, and the only difference is that the second average conditions on clearing the bar.**

## Build

The whole result comes from integrating the sampling distribution and then splitting it at the significance bar. First lay the distribution down as weighted grid points.

```python filename=modules/evals-and-statistics/code/typesm-inter-01/typesm.py:38-46 COMPLETE
def grid(data):
    """The sampling distribution of the estimate as (value, weight) pairs, normalized to sum 1."""
    lo, hi, step = data["grid_lo"], data["grid_hi"], data["grid_step"]
    mu, sigma = data["true_effect"], data["standard_error"]
    n = int(round((hi - lo) / step)) + 1
    pts = [lo + i * step for i in range(n)]
    raw = [normal_pdf(x, mu, sigma) * step for x in pts]
    total = sum(raw)
    return [(x, w / total) for x, w in zip(pts, raw)]
```

Then the summary computes the unconditional mean over the whole grid, the power as the weight past the bar, and — over just the significant points — the conditional mean, the exaggeration ratio, and the wrong-sign weight.

```python filename=modules/evals-and-statistics/code/typesm-inter-01/typesm.py:54-68 COMPLETE
def summarize(data):
    """Power, unconditional mean, and the significance-conditional mean / exaggeration / sign-error."""
    g = grid(data)
    truth = data["true_effect"]
    uncond_mean = sum(w * x for x, w in g)
    sig = [(x, w) for x, w in g if is_significant(x, data)]
    power = sum(w for _, w in sig)
    cond_mean = sum(w * x for x, w in sig) / power
    cond_absmean = sum(w * abs(x) for x, w in sig) / power
    exaggeration = cond_absmean / abs(truth)
    wrong_sign = sum(w for x, w in sig if (x > 0) != (truth > 0)) / power
    return {
        "uncond_mean": uncond_mean, "power": power, "cond_mean": cond_mean,
        "cond_absmean": cond_absmean, "exaggeration": exaggeration, "wrong_sign": wrong_sign,
    }
```

The two quantities differ only by the `if is_significant` filter on the second sum. That single condition is the entire distance between an unbiased 0.50 and an inflated 2.39.

**Nothing in this code models a biased estimator; the bias is manufactured entirely by summarizing over the significant subset instead of the whole distribution.**

## Definition of done

You are done when you check the power of a design before you trust a significant estimate from it, and treat a significant result from a low-power design as uninformative about magnitude and unreliable about direction.

The cure is power itself. Hold the true effect at 0.50 and shrink the standard error — more units, less measurement noise — and the two errors collapse together. At standard error 0.50 the power rises to 17% and the exaggeration ratio falls from 4.8 to 2.5; at 0.25, power is 52% and exaggeration is 1.4; at 0.10, power is 99.9% and the exaggeration is 1.0 with sign errors gone entirely.

<svg role="img" aria-label="A chart with power increasing along the horizontal axis and two curves falling toward their floors: the Type M exaggeration ratio dropping from about 4.8 toward 1, and the Type S sign-error rate dropping from about 9 percent toward 0" viewBox="0 0 640 300">
<line x1="60" y1="240" x2="600" y2="240" stroke="var(--line)" stroke-width="1"/>
<line x1="60" y1="40" x2="60" y2="240" stroke="var(--line)" stroke-width="1"/>
<text x="330" y="276" fill="var(--muted)" font-size="11" text-anchor="middle">power (chance of significance) increases &#8594;</text>
<text x="150" y="60" fill="var(--ink)" font-size="11">Type M exaggeration</text>
<polyline points="90,70 190,150 360,205 560,232" fill="none" stroke="var(--ink)" stroke-width="2"/>
<circle cx="90" cy="70" r="4" fill="var(--ink)"/>
<circle cx="190" cy="150" r="4" fill="var(--ink)"/>
<circle cx="360" cy="205" r="4" fill="var(--ink)"/>
<circle cx="560" cy="232" r="4" fill="var(--ink)"/>
<text x="90" y="60" fill="var(--muted)" font-size="10" text-anchor="middle">4.8x</text>
<text x="560" y="224" fill="var(--muted)" font-size="10" text-anchor="middle">1.0x</text>
<text x="150" y="120" fill="var(--s2)" font-size="11">Type S wrong-sign</text>
<polyline points="90,110 190,224 360,239 560,240" fill="none" stroke="var(--s2)" stroke-width="2" stroke-dasharray="5 3"/>
<text x="90" y="104" fill="var(--muted)" font-size="10" text-anchor="middle">8.7%</text>
<text x="150" y="240" fill="var(--muted)" font-size="10">power .08  .17  .52  .999</text>
</svg>
^ Both errors are artifacts of low power: raise power and the exaggeration ratio falls to 1.0 and the sign-error rate to 0.

**"We found a significant effect in a small study" is not a finding to celebrate — it is a prompt to ask what the power was, because at low power the significance certifies nothing you actually care about.**

## Boss fight

Here is the self-test. It asserts that the estimator is unbiased over all runs, that the study is underpowered, and yet that conditioning on significance exaggerates the effect and admits sign errors — the coexistence that is the whole point.

```python filename=modules/evals-and-statistics/code/typesm-inter-01/typesm.py:105-118 COMPLETE
    estimator_unbiased = abs(s["uncond_mean"] - truth) < 1e-6
    print("  averaged over all runs the estimate equals the truth = %s (%.6f vs %.4f)" % (estimator_unbiased, s["uncond_mean"], truth))

    power_is_low = s["power"] < 0.30
    print("  the study is underpowered = %s (power %.4f)" % (power_is_low, s["power"]))

    significant_exaggerates = s["exaggeration"] > 2.0
    print("  a significant estimate exaggerates the effect = %s (%.2fx the truth)" % (significant_exaggerates, s["exaggeration"]))

    sign_errors_occur = s["wrong_sign"] > 0.0
    print("  some significant estimates have the wrong sign = %s (%.4f)" % (sign_errors_occur, s["wrong_sign"]))

    significance_certifies_nothing = significant_exaggerates and sign_errors_occur
    print("  so 'significant' certifies neither magnitude nor direction = %s" % significance_certifies_nothing)
```

Running the check confirms all five flags at once.

```text filename=typesm.py --check
SELF-TEST — the estimator is unbiased overall, yet conditional on significance it exaggerates the effect and admits sign errors
----------------------------------------------------------------------------------------------------------------
  averaged over all runs the estimate equals the truth = True (0.500000 vs 0.5000)
  the study is underpowered = True (power 0.0792)
  a significant estimate exaggerates the effect = True (4.79x the truth)
  some significant estimates have the wrong sign = True (0.0875)
  so 'significant' certifies neither magnitude nor direction = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  estimator_unbiased=True  power_is_low=True  significant_exaggerates=True  sign_errors_occur=True  significance_certifies_nothing=True
```

Your turn: raise the true effect toward the noise — set `true_effect` to 2.0 with `standard_error` still 1.0 — and rerun. Power climbs, the exaggeration ratio drops toward 1.0, and `power_is_low` flips to False. Watch the self-test fail, and notice that it fails because the pathology it was testing for has been cured by power. That is the point: the errors are not a property of the estimator, they are a property of running a filter over a distribution that barely reaches the bar.

**The bug is not in any line of arithmetic — it is in believing a significant number without first asking whether the design had the power to produce an honest one.**

## External resources

Gelman and Carlin's "Beyond Power Calculations: Assessing Type S (Sign) and Type M (Magnitude) Errors" (Perspectives on Psychological Science, 2014) is the source of these two names and the design-analysis framing used here.

Gelman's blog writing on "the statistical significance filter" gives the same argument informally and connects it to why underpowered-but-significant literatures fail to replicate.

Button and colleagues' "Power failure: why small sample size undermines the reliability of neuroscience" (Nature Reviews Neuroscience, 2013) documents the exaggeration effect across a real field and is a good companion for seeing the consequences at scale.
