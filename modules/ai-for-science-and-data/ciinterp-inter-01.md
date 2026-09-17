---
id: ciinterp-inter-01
title: A 95% confidence interval is about the procedure, not the one interval — it either contains the truth or it doesn't
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: A confidence interval is the sample mean plus or minus z times the standard error, and the natural reading of "95% confidence interval" — there is a 95% probability the true value is inside this interval — is wrong. Once the interval is computed it is a fixed range and the true value is a fixed number, so the true value is inside it or it is not; the probability is 1 or 0, you just do not know which. The 95% lives one level up, in the method: if you ran the experiment many times, each run drawing a different sample and producing a different interval, about 95% of those intervals would cover the true value and about 5% would miss. The confidence is the coverage rate of the procedure over repetitions, not a credence about the particular interval in front of you. The distinction has teeth when an interval misses: a miss is not a low-probability event within that interval, it is an interval that flatly does not contain the truth, so "there is a 95% chance the truth is in here" about a missing interval is not merely loose but false. On the fixture the true value is 100, each experiment has a standard error of 1.0, and the interval is the mean ± 1.96; across twenty experiments nineteen intervals contain 100 (95% coverage) and one, from a sample mean of 102.3, is 100.34 to 104.26, which excludes 100 completely. The 95% describes the nineteen-of-twenty, not any single interval. The rule: confidence is a property of the interval-making procedure across repeated samples, and any one interval you hold is simply right or wrong about the parameter.
eli5: Imagine a machine that makes rings and tries to toss each one around a fixed peg, and it succeeds 95% of the time. That 95% describes the machine's aim over many throws. Now look at one ring lying on the ground: it is either around the peg or it is not — there is no "95% around the peg" for a ring that has already landed. Saying a single confidence interval has a 95% chance of holding the true value is like saying a ring that clearly missed still has a 95% chance of being on the peg. The 95% was always about the machine's habit across many tries, not about the one ring in your hand.
---

## Why this module

Confidence intervals are how uncertainty gets reported — in papers, dashboards, A/B tests — and they are almost universally read the wrong way, including by people who compute them correctly. The wrong reading, "95% chance the true value is in this interval," feels like exactly what an interval should tell you, which is why it is so sticky.

It is worth getting right because the wrong reading licenses bad decisions. If you believe a single interval has a 95% chance of holding the truth, you treat every interval as equally trustworthy and you have no language for the ones that miss — and about one in twenty does. The correct reading keeps the uncertainty where it belongs: in the method, not the number.

**Confidence is a property of the procedure that makes intervals, not a probability attached to the one interval you are looking at.**

## Concepts

Start with what is random and what is fixed. The true value of the thing you are estimating is fixed — it has some definite value you do not know. Your sample is random: draw a different sample and you get a different sample mean, hence a different interval. So before you run the experiment, the interval is a random object, and it makes sense to ask how often such intervals cover the truth. After you run it, the interval is a fixed range of numbers, and the truth is a fixed number, and one of two things is now permanently true: the truth is inside, or it is outside.

The "95%" is a statement about the random object, the procedure. A 95% confidence procedure is one whose intervals cover the true value 95% of the time across repeated samples. That is a property you could verify by simulation: run the experiment thousands of times and count what fraction of the intervals contain the truth. It should be about 95%.

It is not a statement about your one interval, because your one interval is no longer random. Asking "what is the probability the truth is in [100.34, 104.26]" is asking about two fixed numbers and a fixed range; the answer is 1 or 0, not 0.95. You do not know which, but "you do not know" is a statement about your knowledge, not a 95% probability living in the interval.

The gap becomes undeniable at a miss. Across many intervals, about 5% do not contain the truth. For one of those, the truth is entirely outside the range. Telling yourself "there is still a 95% chance the truth is in this one" is not a harmless approximation — it is asserting something false about a specific interval that provably excludes the answer. The 95% never protected any individual interval; it only ever described the batch.

**Before sampling, an interval is random and covers the truth 95% of the time; after sampling, it is fixed and simply does or does not contain the truth — the 95% belongs to the first situation, not the second.**

<svg role="img" aria-label="Two panels. Before sampling: many possible intervals fanned out, 95% of them would cover the truth line. After sampling: one fixed interval, either on the truth or off it, no probability." viewBox="0 0 320 150">
<rect x="0" y="0" width="320" height="150" fill="var(--panel)"></rect>
<text x="12" y="16" fill="var(--ink)" font-size="11">before sampling: the 95% lives here</text>
<line x1="90" y1="24" x2="90" y2="70" stroke="var(--ink)"></line>
<line x1="60" y1="30" x2="120" y2="30" stroke="var(--s2)"></line>
<line x1="72" y1="40" x2="132" y2="40" stroke="var(--s2)"></line>
<line x1="55" y1="50" x2="115" y2="50" stroke="var(--s2)"></line>
<line x1="100" y1="60" x2="160" y2="60" stroke="var(--s1)"></line>
<text x="150" y="44" fill="var(--muted)" font-size="8">~95% cover the line</text>
<text x="12" y="96" fill="var(--ink)" font-size="11">after sampling: no probability, just in or out</text>
<line x1="90" y1="104" x2="90" y2="140" stroke="var(--ink)"></line>
<line x1="62" y1="122" x2="122" y2="122" stroke="var(--s2)"></line>
<text x="150" y="125" fill="var(--muted)" font-size="8">this one: contains the truth (fact)</text>
</svg>
^ The 95% describes the fan of intervals you might have drawn; once you have drawn one, it is a single fixed range that either contains the truth or does not.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/ai-for-science-and-data/code/ciinterp-inter-01/ciinterp.py

The fixture is twenty repeated experiments estimating a true value of 100.

```json filename=modules/ai-for-science-and-data/code/ciinterp-inter-01/ciinterp.json:3-6 COMPLETE
  "true_value": 100,
  "standard_error": 1.0,
  "z": 1.96,
  "sample_means": [99.2, 100.5, 98.8, 101.1, 100.0, 99.5, 100.8, 98.6, 101.3, 99.9, 100.3, 99.1, 101.0, 98.9, 100.6, 99.7, 101.4, 100.2, 99.4, 102.3]
```

Each experiment's interval is the mean plus or minus 1.96 standard errors, and containment is a plain yes/no.

```python filename=modules/ai-for-science-and-data/code/ciinterp-inter-01/ciinterp.py:30-33 COMPLETE
def interval(mean, se, z):
    """The confidence interval for one experiment: mean plus or minus z standard errors."""
    half = z * se
    return (mean - half, mean + half)
```

```python filename=modules/ai-for-science-and-data/code/ciinterp-inter-01/ciinterp.py:36-39 COMPLETE
def contains(iv, value):
    """Whether a computed interval contains the value -- a yes/no fact, not a probability."""
    lo, hi = iv
    return lo <= value <= hi
```

```python filename=modules/ai-for-science-and-data/code/ciinterp-inter-01/ciinterp.py:42-45 COMPLETE
def coverage(sample_means, se, z, true_value):
    """The fraction of the produced intervals that contain the true value: the procedure's coverage."""
    hits = sum(1 for m in sample_means if contains(interval(m, se, z), true_value))
    return hits / len(sample_means)
```

```text filename=ciinterp.py --coverage
COVERAGE — across 20 experiments
----------------------------------------------------------------
  intervals containing the truth: 19 of 20  (95%)
  MISS: mean 102.3 -> [100.34, 104.26] does NOT contain 100
----------------------------------------------------------------
  the 95% is this coverage across intervals, not a probability inside the missing one
```

Nineteen of the twenty intervals contain 100 — that is the 95%, a fact about the collection. One does not: the experiment with sample mean 102.3 produces [100.34, 104.26], a range entirely above 100. The 95% is the 19-of-20; it is not a property any single one of these twenty intervals carries.

<svg role="img" aria-label="Twenty horizontal interval bars stacked vertically, each centered on its sample mean, with a vertical line at the true value 100. Nineteen bars cross the line; the last bar sits entirely to the right of it and does not cross." viewBox="0 0 320 180">
<rect x="0" y="0" width="320" height="180" fill="var(--panel)"></rect>
<text x="12" y="16" fill="var(--ink)" font-size="12">20 intervals, true value = 100 (vertical line)</text>
<line x1="160" y1="24" x2="160" y2="168" stroke="var(--ink)"></line>
<line x1="130" y1="30" x2="196" y2="30" stroke="var(--s2)"></line>
<line x1="150" y1="38" x2="216" y2="38" stroke="var(--s2)"></line>
<line x1="118" y1="46" x2="184" y2="46" stroke="var(--s2)"></line>
<line x1="164" y1="54" x2="230" y2="54" stroke="var(--s2)"></line>
<line x1="137" y1="62" x2="203" y2="62" stroke="var(--s2)"></line>
<line x1="127" y1="70" x2="193" y2="70" stroke="var(--s2)"></line>
<line x1="152" y1="78" x2="218" y2="78" stroke="var(--s2)"></line>
<line x1="116" y1="86" x2="182" y2="86" stroke="var(--s2)"></line>
<line x1="167" y1="94" x2="233" y2="94" stroke="var(--s2)"></line>
<line x1="134" y1="102" x2="200" y2="102" stroke="var(--s2)"></line>
<line x1="140" y1="110" x2="206" y2="110" stroke="var(--s2)"></line>
<line x1="124" y1="118" x2="190" y2="118" stroke="var(--s2)"></line>
<line x1="154" y1="126" x2="220" y2="126" stroke="var(--s2)"></line>
<line x1="120" y1="134" x2="186" y2="134" stroke="var(--s2)"></line>
<line x1="142" y1="142" x2="208" y2="142" stroke="var(--s2)"></line>
<line x1="200" y1="152" x2="266" y2="152" stroke="var(--s1)"></line>
<text x="204" y="150" fill="var(--s1)" font-size="8">miss</text>
</svg>
^ Nineteen intervals straddle the true-value line; the one drawn apart sits wholly to its right, containing no probability that the truth is inside — it simply is not.

## Build

The coverage is the procedure's, and the missing interval excludes the truth outright.

```python filename=modules/ai-for-science-and-data/code/ciinterp-inter-01/ciinterp.py:83-89 COMPLETE
    coverage_near_95 = abs(cov - 0.95) < 1e-9
    print("  coverage across the intervals is 95%% = %s (%.2f)" % (coverage_near_95, cov))

    intervals = [interval(m, se, z) for m in means]
    containments = [contains(iv, tv) for iv in intervals]
    one_misses = not all(containments)
    print("  at least one interval does not contain the true value = %s (%d miss)" % (one_misses, containments.count(False)))
```

```python filename=modules/ai-for-science-and-data/code/ciinterp-inter-01/ciinterp.py:91-93 COMPLETE
    missing = [iv for iv, c in zip(intervals, containments) if not c][0]
    miss_definitely_excludes = not contains(missing, tv)
    print("  the missing interval definitely excludes the truth (not 95%% inside) = %s (%s, %d outside)" % (miss_definitely_excludes, ("[%.2f, %.2f]" % missing), tv))
```

```text filename=ciinterp.py --check
SELF-TEST — about 95% of intervals contain the true value, at least one misses entirely, and the missing interval definitely excludes the truth
----------------------------------------------------------------------------------------------------------------
  coverage across the intervals is 95% = True (0.95)
  at least one interval does not contain the true value = True (1 miss)
  the missing interval definitely excludes the truth (not 95% inside) = True ([100.34, 104.26], 100 outside)
  each interval's containment is a yes/no fact, not a probability = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  coverage_near_95=True  one_misses=True  miss_definitely_excludes=True  each_binary=True
```

<svg role="img" aria-label="A number line with the true value 100 marked. The missing interval spans 100.34 to 104.26, drawn entirely to the right of 100, with a gap between 100 and the interval's left end." viewBox="0 0 320 120">
<rect x="0" y="0" width="320" height="120" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">the interval that missed (mean 102.3)</text>
<line x1="30" y1="70" x2="300" y2="70" stroke="var(--line)"></line>
<line x1="70" y1="55" x2="70" y2="85" stroke="var(--ink)"></line>
<text x="56" y="100" fill="var(--ink)" font-size="9">truth 100</text>
<line x1="120" y1="70" x2="270" y2="70" stroke="var(--s1)" stroke-width="3"></line>
<text x="150" y="60" fill="var(--s1)" font-size="9">[100.34, 104.26]</text>
<text x="80" y="46" fill="var(--muted)" font-size="9">gap: truth is outside</text>
</svg>
^ The missing interval and the true value do not touch — there is no sense in which the truth is "95% inside" a range it lies entirely outside of.

**miss_definitely_excludes is the sentence that breaks the wrong intuition: for the interval that missed, the probability the truth is inside is zero, not 0.95, so the 95% was never about a single interval.**

## Definition of done

You can say what is random (the sample, hence the interval before you compute it) and what is fixed (the true value, and the interval after you compute it), and why that distinction decides where the 95% lives.

You can state the correct interpretation — 95% of intervals from this procedure cover the truth across repeated samples — and why it is not a probability about your one computed interval.

You can explain why the wrong reading fails hardest at a miss: the truth is definitely outside the missing interval, so "95% chance inside" is false, not approximate.

You can describe how you would verify a procedure's coverage (simulate many samples, count the fraction of intervals containing the known truth) and why that experiment is about the method, not any interval.

## Boss fight

A dashboard reports "conversion lift 2.1%, 95% CI [0.1%, 4.1%]" and a PM concludes "so there's a 95% chance the true lift is between 0.1% and 4.1%, and only a 5% chance it's outside." A colleague counters that the true lift is a fixed number and the statement is meaningless.

First: explain what is right and wrong in each of their claims. In what sense is the PM's number the correct one to act on, and in what sense is the colleague's objection correct about what the interval literally says?

Then: the PM wants a statement that really is "95% probability the parameter is in this range." That is a different object — a Bayesian credible interval, not a frequentist confidence interval. Explain what extra ingredient a credible interval requires that a confidence interval does not, and why, given that ingredient, it can make the probability statement the confidence interval cannot.

Finally: across a quarter the team ships 40 features, each evaluated with a 95% CI, and acts on every interval as if it certainly contained the truth. Estimate how many of those 40 intervals you would expect to miss, and explain why "95% coverage" means this is not bad luck or a broken method but the guaranteed long-run behavior — and what that implies about treating any single interval as certain.

## External resources

Any mathematical-statistics text's chapter on interval estimation defines the confidence level as the coverage probability of the procedure and explicitly warns against the "probability the parameter is in this interval" reading — the exact correction this module makes.

Comparisons of confidence intervals and Bayesian credible intervals (for example in Bayesian data analysis references) are the natural next step: they show what the credible interval assumes (a prior) that lets it make the probability statement about a single interval that the confidence interval cannot.
