---
id: data-inter-19
title: Divide the sample variance by n−1 — or dividing by n underestimates the spread every time
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 19 min
summary: To estimate how spread out a population is, you sample it and compute the variance — the average squared distance of the points from their mean. The obvious formula divides the sum of squared deviations by n, and it is biased: it comes out too small, systematically, on average. The reason is that you measure deviations from the sample mean, and the sample mean is the point that minimizes the sum of squared deviations for that sample — so the points are always at least as close to their own mean as to the true one, and the n divisor inherits that closeness as an underestimate. Bessel's correction divides by n−1 instead, exactly compensating for the one degree of freedom spent estimating the mean, and is unbiased. On the population 1, 4, 7 (true variance 6), enumerating all 9 samples of size 2, the n-divisor variance averages 3.0 — exactly half — while the n−1 divisor averages 6.0.
eli5: To see how spread out some numbers are, you measure how far each is from their average. But the average is picked to sit right in the middle of your few numbers, so they hug it — they look less spread out than the whole population really is. Dividing by one less than the count nudges the answer back up to make up for that hugging, so on average you get the true spread instead of one that is too small.
---

## Why this module

Estimating spread from a sample uses the data twice — once to find the center, once to measure distance from it — and the second use gets an unfair discount from the first.

The variance of a sample is the average squared deviation of its points from their mean. To compute it you first estimate the mean from the sample, then measure how far the points sit from that estimate. The catch is that the sample mean is, by construction, the single point that makes the sum of squared deviations as small as possible for that sample. So the points are always at least as close to their own mean as to the true population mean, and any formula that divides by n treats that artificially-small spread as the real thing. Averaged over all possible samples, the n-divisor variance comes out systematically below the truth — not sometimes, always in expectation.

**The sample mean minimizes squared deviations for its own sample, so measuring spread around it and dividing by n underestimates the population's spread every time.**

Bessel's correction fixes it with one character: divide by n−1 instead of n. Estimating the mean from the sample used up one degree of freedom, and dividing by the remaining n−1 exactly compensates, making the estimate unbiased. This module enumerates every sample of a tiny population, computes both divisors exactly, and shows which one hits the true variance.

## Concepts

The **population variance** is the true spread: the average squared deviation from the population mean, computed over the whole population. It is the number a sample is trying to estimate.

The **sample variance** takes the sum of squared deviations from the *sample* mean and divides by n minus a "delta degrees of freedom" (ddof). **ddof = 0** divides by n; **ddof = 1** divides by n−1, which is Bessel's correction.

The **bias** is that dividing by n gives, on average, only (n−1)/n of the true variance. The missing factor is the degree of freedom consumed by estimating the mean: with n points and one estimated parameter, only n−1 independent pieces of spread information remain.

Because the population here is tiny, the module does not estimate the expected sample variance — it **enumerates** every possible sample and averages exactly, so the bias is demonstrated as an identity, not a simulation that might be noise.

The correction's size depends on n. At n = 2 the factor is 1/2 — the n divisor is off by half. At n = 100 it is 99/100 — nearly negligible. So the correction matters most for the small samples where you can least afford a biased estimate, and fades where you need it least.

**Dividing by n−1 restores the degree of freedom spent locating the mean, turning a systematically-low estimate into an unbiased one.**

The sample points hug their own mean more tightly than they hug the true mean, so spread measured around the sample mean starts out too small.

<svg role="img" aria-label="A number line with the true mean and a sample's own mean; the sample points sit closer to their own mean than to the true one" viewBox="0 0 300 100" width="300" height="100">
  <line x1="20" y1="55" x2="285" y2="55" stroke="var(--grid)" stroke-width="1"/>
  <circle cx="80" cy="55" r="4" fill="var(--s2)"/><circle cx="130" cy="55" r="4" fill="var(--s2)"/>
  <text x="70" y="75" fill="var(--s2)" font-size="8">sample points</text>
  <line x1="105" y1="40" x2="105" y2="70" stroke="var(--s2)" stroke-width="1.5"/>
  <text x="88" y="35" fill="var(--s2)" font-size="7">sample mean</text>
  <line x1="200" y1="40" x2="200" y2="70" stroke="var(--ink)" stroke-width="1.5" stroke-dasharray="3 2"/>
  <text x="180" y="35" fill="var(--ink)" font-size="7">true mean</text>
  <text x="40" y="92" fill="var(--muted)" font-size="8">deviations from the sample mean are smaller than from the true mean</text>
</svg>
^ The sample mean sits amid the sample's own points, so their squared deviations from it are smaller than from the true mean — the shrinkage the n divisor bakes in and n−1 removes.

This is why the sample-standard-deviation key on a calculator, `numpy.var(ddof=1)`, and pandas' default all divide by n−1.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/data-inter-19/bessel.py

The fixture is a three-value population and a sample size of 2.

```json filename=modules/ai-for-science-and-data/code/data-inter-19/population.json:1-6 COMPLETE
{
  "_meta": "A tiny known population and a sample size. Because the population is small, we can enumerate EVERY possible sample of size n (drawn with replacement) and average the sample variance across all of them -- computing the expected value exactly, not estimating it. We compare two sample-variance formulas: dividing the sum of squared deviations by n, and dividing by n-1 (Bessel's correction). The question: which one, on average, equals the true population variance?",
  "population": [1, 4, 7],
  "sample_size": 2
}
```

The population variance divides by the population size; the sample variance divides by n minus ddof; all_samples enumerates every draw.

```python filename=modules/ai-for-science-and-data/code/data-inter-19/bessel.py:46-60 COMPLETE
def population_variance(pop):
    """The true variance: average squared deviation from the population mean."""
    m = mean(pop)
    return sum((x - m) ** 2 for x in pop) / len(pop)


def sample_variance(sample, ddof):
    """Sum of squared deviations from the sample mean, divided by (n - ddof). ddof=0 is /n; ddof=1 is /(n-1)."""
    m = mean(sample)
    ss = sum((x - m) ** 2 for x in sample)
    return ss / (len(sample) - ddof)


def all_samples(pop, n):
    return list(itertools.product(pop, repeat=n))
```

Run `--samples` to see all nine samples and their two variances.

```text filename=--samples
SAMPLES — every size-2 sample of [1, 4, 7], with both sample variances
------------------------------------------------------------
  sample     mean    var (/n)   var (/n-1)
  (1, 1)     1.00      0.00        0.00
  (1, 4)     2.50      2.25        4.50
  (1, 7)     4.00      9.00       18.00
  (4, 1)     2.50      2.25        4.50
  (4, 4)     4.00      0.00        0.00
  (4, 7)     5.50      2.25        4.50
  (7, 1)     4.00      9.00       18.00
  (7, 4)     5.50      2.25        4.50
  (7, 7)     7.00      0.00        0.00
------------------------------------------------------------
  the /n column runs small; the /n-1 column runs larger.
```

Every sample's n−1 variance is exactly twice its n variance, because n/(n−1) = 2/1 here. The three samples with two equal values (like (4, 4)) report zero spread — the sample saw no variation at all, even though the population has plenty. Those zeros are the bias in the raw: a size-2 sample often lands on two similar values and reports far too little spread.

<svg role="img" aria-label="Nine samples' /n variances as bars from a baseline: three are zero, four are small, two are tall; the correction doubles each" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="14" fill="var(--muted)" font-size="8">var (/n) per sample (baseline = 0)</text>
  <line x1="12" y1="60" x2="285" y2="60" stroke="var(--grid)" stroke-width="1"/>
  <rect x="15" y="58" width="8" height="2" fill="var(--s1)"/>
  <rect x="45" y="53" width="8" height="7" fill="var(--s1)"/>
  <rect x="75" y="32" width="8" height="28" fill="var(--s1)"/>
  <rect x="105" y="53" width="8" height="7" fill="var(--s1)"/>
  <rect x="135" y="58" width="8" height="2" fill="var(--s1)"/>
  <rect x="165" y="53" width="8" height="7" fill="var(--s1)"/>
  <rect x="195" y="32" width="8" height="28" fill="var(--s1)"/>
  <rect x="225" y="53" width="8" height="7" fill="var(--s1)"/>
  <rect x="255" y="58" width="8" height="2" fill="var(--s1)"/>
  <text x="63" y="30" fill="var(--s1)" font-size="7">9.0</text>
  <text x="10" y="78" fill="var(--muted)" font-size="8">three samples report zero spread (both values equal)</text>
  <text x="10" y="94" fill="var(--s2)" font-size="8">the n-1 correction scales every one of these up by 2×</text>
</svg>
^ Several small samples report zero or tiny spread; the n−1 correction scales each of those variances up by n/(n−1) to undo the systematic shrinkage.

## Build

The bias view averages each divisor's variance over every sample and lays it beside the true variance.

```python filename=modules/ai-for-science-and-data/code/data-inter-19/bessel.py:77-87 COMPLETE
    pop, n = data["population"], data["sample_size"]
    samples = all_samples(pop, n)
    avg_n = mean([sample_variance(s, 0) for s in samples])
    avg_n1 = mean([sample_variance(s, 1) for s in samples])
    sig2 = population_variance(pop)
    print("BIAS — expected sample variance (averaged over all %d samples) vs the truth" % len(samples))
    print("-" * 60)
    print("  true population variance:       %.2f" % sig2)
    print("  average of /n     variance:     %.2f   (biased low)" % avg_n)
    print("  average of /(n-1) variance:     %.2f   (unbiased)" % avg_n1)
    print("  the /n bias factor is (n-1)/n = %d/%d = %.2f, so %.2f*%.2f = %.2f" % (n - 1, n, (n - 1) / n, sig2, (n - 1) / n, sig2 * (n - 1) / n))
```

Average across all samples with `--bias`.

```text filename=--bias
BIAS — expected sample variance (averaged over all 9 samples) vs the truth
------------------------------------------------------------
  true population variance:       6.00
  average of /n     variance:     3.00   (biased low)
  average of /(n-1) variance:     6.00   (unbiased)
  the /n bias factor is (n-1)/n = 1/2 = 0.50, so 6.00*0.50 = 3.00
------------------------------------------------------------
  using the sample mean to center costs one degree of freedom.
```

The true variance is 6. Averaged over all nine samples, the n-divisor variance is 3.0 — exactly half, exactly the (n−1)/n = 1/2 factor predicted. The n−1 divisor averages 6.0, dead on the truth. The bias is not a rounding artifact or a small-sample fluke; it is an exact identity, visible here because every sample was enumerated rather than simulated.

<svg role="img" aria-label="Expected variance: n-divisor averages 3 (half), n-1 divisor averages 6 (equal to true variance 6)" viewBox="0 0 300 110" width="300" height="110">
  <line x1="70" y1="12" x2="70" y2="80" stroke="var(--grid)" stroke-width="1"/>
  <line x1="70" y1="80" x2="285" y2="80" stroke="var(--grid)" stroke-width="1"/>
  <line x1="250" y1="12" x2="250" y2="80" stroke="var(--ink)" stroke-width="1" stroke-dasharray="3 2"/>
  <text x="215" y="22" fill="var(--ink)" font-size="8">true σ²=6</text>
  <rect x="70" y="30" width="90" height="14" fill="var(--s1)"/><text x="164" y="41" fill="var(--muted)" font-size="8">/n avg 3 (biased)</text>
  <rect x="70" y="52" width="180" height="14" fill="var(--s2)"/><text x="150" y="63" fill="var(--panel)" font-size="8">/(n-1) avg 6</text>
  <text x="70" y="100" fill="var(--muted)" font-size="8">the /n bar stops halfway to the truth; /(n-1) reaches it</text>
</svg>
^ The n-divisor bar reaches only half the true variance line; the n−1 bar lands exactly on it — the correction is the gap between biased and unbiased.

## Definition of done

The self-test pins the identity: the n variance averages below the truth, the n−1 variance equals it, the n bias is exactly (n−1)/n, each n−1 variance is n/(n−1) times its n variance, and the expectation was computed by full enumeration.

```python filename=modules/ai-for-science-and-data/code/data-inter-19/bessel.py:101-113 COMPLETE
    n_divisor_biased_low = avg_n < sig2
    print("  the /n variance averages below the truth = %s (%.2f < %.2f)" % (n_divisor_biased_low, avg_n, sig2))

    n1_divisor_unbiased = abs(avg_n1 - sig2) < 1e-9
    print("  the /(n-1) variance averages exactly the truth = %s (%.2f = %.2f)" % (n1_divisor_unbiased, avg_n1, sig2))

    bias_is_n1_over_n = abs(avg_n - sig2 * (n - 1) / n) < 1e-9
    print("  the /n bias is exactly the factor (n-1)/n = %s (%.2f = %.2f*%.2f)" % (bias_is_n1_over_n, avg_n, sig2, (n - 1) / n))

    correction_scales_each = all(abs(sample_variance(s, 1) - sample_variance(s, 0) * n / (n - 1)) < 1e-9 for s in samples)
    print("  each /(n-1) variance is n/(n-1) times its /n variance = %s" % correction_scales_each)

    enumerated_all = len(samples) == len(pop) ** n
    print("  the expectation was computed by full enumeration = %s (%d samples)" % (enumerated_all, len(samples)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — dividing by n is biased low by (n-1)/n; dividing by n-1 is unbiased
----------------------------------------------------------------------------------------------------
  the /n variance averages below the truth = True (3.00 < 6.00)
  the /(n-1) variance averages exactly the truth = True (6.00 = 6.00)
  the /n bias is exactly the factor (n-1)/n = True (3.00 = 6.00*0.50)
  each /(n-1) variance is n/(n-1) times its /n variance = True
  the expectation was computed by full enumeration = True (9 samples)
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  n_divisor_biased_low=True  n1_divisor_unbiased=True  bias_is_n1_over_n=True  correction_scales_each=True  enumerated_all=True
```

**Done means the bias is an exact identity, not a simulation: averaged over all 9 samples the n divisor gives exactly 3.00 = 6.00 × 1/2 and the n−1 divisor gives exactly 6.00, the true variance.**

## Boss fight

Bessel's correction made the variance unbiased. Predict whether taking the square root of the corrected variance gives an unbiased estimate of the standard deviation. It is tempting to assume the fix carries through.

It does not, and this is the subtlety even careful people miss. The square root is a nonlinear function, and by Jensen's inequality the expected value of a square root is not the square root of the expected value — so the square root of an unbiased variance is a biased (slightly low) estimate of the standard deviation. Bessel's correction fixes the variance exactly; it does not fully fix the standard deviation. In practice the residual bias in the standard deviation is small and usually ignored, and a further correction (multiplying by a factor c₄(n)) exists for when it matters. The lesson is that unbiasedness does not survive a nonlinear transform.

The mirror-image mistake is applying the correction when you should not. If you have the *entire* population, not a sample, you divide by n — there is no mean to estimate from a subset, no degree of freedom spent, and n−1 would wrongly inflate the answer. The correction is specifically for estimating a population's spread *from a sample*; use it there and only there. The `ddof` argument exists precisely so you state which case you are in.

```python filename=modules/ai-for-science-and-data/code/data-inter-19/bessel.py:52-56 COMPLETE
def sample_variance(sample, ddof):
    """Sum of squared deviations from the sample mean, divided by (n - ddof). ddof=0 is /n; ddof=1 is /(n-1)."""
    m = mean(sample)
    ss = sum((x - m) ** 2 for x in sample)
    return ss / (len(sample) - ddof)
```

**Divide by n−1 to estimate a population's variance from a sample, and by n only when you have the whole population — the correction restores the degree of freedom spent on the mean, but it does not survive the square root into the standard deviation.**

## External resources

Any mathematical-statistics text's derivation that E[sample variance with /n] = σ²(n−1)/n — the identity this module demonstrates by enumeration, with the algebra behind the (n−1)/n factor.

The numpy `var`/`std` documentation on the `ddof` parameter, and pandas' default of `ddof=1` — the applied form of the choice, and a common source of "why don't my numbers match" bugs between libraries.

The correction factor c₄(n) for the standard deviation (control-chart and process-control literature) — the further correction named in the boss fight for the residual square-root bias.
