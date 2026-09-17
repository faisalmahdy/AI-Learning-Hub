---
id: aatest-inter-01
title: Run an A/A test to validate the pipeline — both arms identical should be significant only ~α of the time, and more means the apparatus is broken
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: Before you trust an A/B test to tell you whether a change worked, you have to trust the machinery that measures it — the randomization, the metric, the variance estimate, the stopping rule — and an A/A test checks all of it at once. It splits traffic exactly like an A/B test but serves both arms the same experience, so the true difference is exactly zero and there is nothing to detect. That makes it a null control for the whole pipeline: because there is no real effect, every result the pipeline calls "significant" is a false positive, and a correctly built pipeline produces false positives at precisely the rate you chose, α (say 5%). So you run the A/A many times and measure how often it declares a winner — about 5% means the apparatus is calibrated and its A/B verdicts can be trusted; much higher means something is wrong, and you found it before it corrupted a real decision. The most common thing it catches is an underestimated variance — a standard error computed too small (treating correlated observations as independent, pooling at the wrong unit, or using the standard error of the mean where the difference's is needed) inflates every test statistic so that pure noise crosses the threshold far more than α of the time. On a fixture of eight A/A differences, the correct standard error flags none (a 0% false-positive rate consistent with α) while a standard error half as large pushes two of the eight past the 1.96 threshold — a 25% false-positive rate that exposes the broken pipeline.
eli5: Before you use a bathroom scale to track whether a diet is working, you'd want to know the scale is honest. So you step on it twice in a row without changing anything — same you, same moment — and it should read the same both times. If it says 150 then 158 then 149, the scale is broken, and any "weight loss" it reports later is just noise. An A/A test is that trick for experiments: you run a comparison where both sides are secretly identical, so there's truly no difference to find. A trustworthy measurement setup will almost never cry "significant difference!" on identical sides — only about as often as its built-in error rate allows. If it keeps finding big differences between two things that are exactly the same, the setup itself is faulty, and you've caught it before betting a real decision on it.
---

## Why this module

Every A/B result is the output of a measurement pipeline, and a result is only as trustworthy as that pipeline. The randomization has to actually be random and balanced; the metric has to be computed correctly; the variance estimate has to reflect the true noise; the stopping rule has to not peek. A bug in any one of these produces confident, official-looking p-values that are wrong, and nothing about a single A/B number tells you whether the machine that produced it is sound.

The problem is that you usually cannot check an A/B pipeline against a known answer, because you do not know the true effect of your change — that is the whole reason you ran the test. There is one case where you do know the true answer with certainty: when the two arms are identical, the effect is exactly zero. That is what an A/A test manufactures, and it is why it is the one experiment whose correct outcome you can state in advance.

Knowing the answer is zero turns the A/A test into a calibration instrument. Run it repeatedly and count how often the pipeline claims a significant difference; since there is none, that count is the pipeline's false-positive rate, which should equal the α you set. A rate near α certifies the machinery; a rate well above α means the machinery is manufacturing significance from noise, and you have measured the defect directly rather than guessing at it. This module runs a batch of A/A differences through a correct and a broken pipeline and compares their false-positive rates.

**An A/B result is only as good as its pipeline, and the one experiment with a known answer is an A/A test — arms identical, true effect zero — so its false-positive rate is a direct, in-advance calibration of the whole apparatus.**

## Concepts

The mechanism is that under a true null, p-values are uniformly distributed, so the fraction below α is α — by construction. This is not an approximation or a rule of thumb; it is the definition of a well-calibrated test. An A/A test realizes the null exactly (the arms really are the same), so a correct pipeline's A/A false-positive rate is α, and any deviation upward is a measurable failure of calibration. The A/A test does not test your product; it tests your test.

The failure it most often exposes is an underestimated variance, because that is the easiest error to make and the hardest to see. Every significance test is a ratio of an observed difference to its standard error, and if the standard error is too small the ratio is too big. Halve the standard error and every z-score doubles, so differences that were comfortably inside the noise band leap across the threshold. The usual causes are all forms of pretending you have more independent information than you do: counting correlated impressions as independent, analyzing at the wrong unit, or using the standard error of a mean where the standard error of a difference is required.

What makes the A/A test uniquely valuable is that it catches these end to end, as a single number, without your having to know which bug is present. You do not have to audit the variance formula, the randomization, and the stopping rule separately; you run identical arms and read off the false-positive rate, and if it is wrong you know something in the chain is wrong. It is the integration test for an experimentation platform, and running it before an A/B campaign is cheap insurance against trusting a broken machine.

<svg role="img" aria-label="An A/A test as a calibration loop: identical arms feed the pipeline, which reports a false-positive rate that is compared to alpha; matching alpha certifies it, exceeding alpha condemns it" viewBox="0 0 440 130">
<rect x="20" y="45" width="90" height="30" fill="var(--panel)" stroke="var(--line)"/>
<text x="65" y="64" fill="var(--ink)" font-size="9" text-anchor="middle">identical arms</text>
<line x1="110" y1="60" x2="150" y2="60" stroke="var(--muted)"/>
<rect x="150" y="45" width="90" height="30" fill="var(--panel)" stroke="var(--line)"/>
<text x="195" y="64" fill="var(--ink)" font-size="9" text-anchor="middle">pipeline</text>
<line x1="240" y1="60" x2="280" y2="60" stroke="var(--muted)"/>
<rect x="280" y="45" width="140" height="30" fill="var(--panel)" stroke="var(--line)"/>
<text x="350" y="64" fill="var(--ink)" font-size="9" text-anchor="middle">FPR vs alpha</text>
<text x="350" y="26" fill="var(--s1)" font-size="8" text-anchor="middle">= alpha: certified</text>
<text x="350" y="98" fill="var(--s2)" font-size="8" text-anchor="middle">&gt; alpha: broken</text>
</svg>
^ The A/A test is a calibration loop: identical arms in, false-positive rate out, compared against α to certify or condemn the pipeline.

**Under a true null the false-positive rate equals α by definition, so an A/A test calibrates the pipeline end to end; the defect it most often surfaces is a too-small variance, which inflates every test statistic and pushes noise past the threshold.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/aatest-inter-01. The fixture is eight A/A differences (arms identical, so noise near zero), the correct standard error, and the too-small one a broken pipeline uses.

```json filename=modules/evals-and-statistics/code/aatest-inter-01/aatest.json:3-7 COMPLETE
  "differences": [0.5, -0.8, 1.0, -0.6, 0.9, -1.1, 0.7, -0.9],
  "se": 1.0,
  "broken_se": 0.5,
  "alpha": 0.05,
  "z_critical": 1.96
```

The test statistic is the difference over its standard error.

```python filename=modules/evals-and-statistics/code/aatest-inter-01/aatest.py:32-34 COMPLETE
def z_score(diff, se):
    """The test statistic: how many standard errors the observed difference is from zero."""
    return diff / se
```

A two-sided test calls a difference significant when its z-score clears the critical value.

```python filename=modules/evals-and-statistics/code/aatest-inter-01/aatest.py:37-39 COMPLETE
def significant(diff, se, z_crit):
    """A two-sided test calls it significant when the z score exceeds the critical value."""
    return abs(z_score(diff, se)) > z_crit
```

On A/A data every significant call is a false positive, so the false-positive rate is just their fraction.

```python filename=modules/evals-and-statistics/code/aatest-inter-01/aatest.py:42-44 COMPLETE
def false_positive_rate(diffs, se, z_crit):
    """On A/A data (no real effect) every significant call is a false positive."""
    return sum(significant(d, se, z_crit) for d in diffs) / len(diffs)
```

Before running it, predict: with the correct SE of 1.0 the largest difference (1.1) gives z = 1.1, under 1.96, so none are significant; halving the SE doubles every z, so 1.0 and 1.1 become 2.0 and 2.2, over the threshold. Run `--tests`:

```text filename=aatest.py --tests
TESTS — each A/A difference (arms identical, so true effect is 0)
--------------------------------------------------------------
  diff    z (correct se=1.0)   sig?   z (broken se=0.5)   sig?
  0.5     0.50                False  1.00               False
  -0.8    -0.80               False  -1.60              False
  1.0     1.00                False  2.00               True
  -0.6    -0.60               False  -1.20              False
  0.9     0.90                False  1.80               False
  -1.1    -1.10               False  -2.20              True
  0.7     0.70                False  1.40               False
  -0.9    -0.90               False  -1.80              False
```

The prediction holds. Under the correct standard error, no A/A difference reaches significance — the noise stays inside the band. Under the broken, halved standard error, every z-score doubles, and two differences that were pure noise (1.0 and −1.1) now read as significant "effects" between two identical arms.

<svg role="img" aria-label="A/A z-scores under two standard errors against the 1.96 threshold: with the correct se all eight are inside the band; with the broken se two exceed 1.96" viewBox="0 0 440 160">
<line x1="40" y1="85" x2="410" y2="85" stroke="var(--line)"/>
<text x="30" y="40" fill="var(--muted)" font-size="8" text-anchor="middle">+2</text>
<text x="30" y="135" fill="var(--muted)" font-size="8" text-anchor="middle">-2</text>
<line x1="40" y1="55" x2="410" y2="55" stroke="var(--s2)" stroke-dasharray="3 3"/>
<line x1="40" y1="115" x2="410" y2="115" stroke="var(--s2)" stroke-dasharray="3 3"/>
<text x="405" y="51" fill="var(--s2)" font-size="7" text-anchor="end">+1.96</text>
<text x="90" y="24" fill="var(--s1)" font-size="9" text-anchor="middle">correct se</text>
<circle cx="55" cy="77" r="3" fill="var(--s1)"/>
<circle cx="70" cy="97" r="3" fill="var(--s1)"/>
<circle cx="85" cy="70" r="3" fill="var(--s1)"/>
<circle cx="100" cy="94" r="3" fill="var(--s1)"/>
<circle cx="115" cy="72" r="3" fill="var(--s1)"/>
<circle cx="130" cy="102" r="3" fill="var(--s1)"/>
<circle cx="145" cy="78" r="3" fill="var(--s1)"/>
<circle cx="160" cy="98" r="3" fill="var(--s1)"/>
<text x="300" y="24" fill="var(--s2)" font-size="9" text-anchor="middle">broken se (halved)</text>
<circle cx="245" cy="70" r="3" fill="var(--s2)"/>
<circle cx="262" cy="109" r="3" fill="var(--s2)"/>
<circle cx="279" cy="55" r="4" fill="var(--s2)"/>
<text x="279" y="48" fill="var(--s2)" font-size="7" text-anchor="middle">sig</text>
<circle cx="296" cy="103" r="3" fill="var(--s2)"/>
<circle cx="313" cy="58" r="3" fill="var(--s2)"/>
<circle cx="330" cy="121" r="4" fill="var(--s2)"/>
<text x="330" y="134" fill="var(--s2)" font-size="7" text-anchor="middle">sig</text>
<circle cx="347" cy="64" r="3" fill="var(--s2)"/>
<circle cx="364" cy="58" r="3" fill="var(--s2)"/>
</svg>
^ The same A/A noise: under the correct SE every point sits inside the ±1.96 band; the halved SE pushes two points across it into false significance.

Now the calibration number itself. Run `--fpr`:

```text filename=aatest.py --fpr
FPR — false-positive rate on A/A data vs the chosen alpha=5%
------------------------------------------------------
  correct pipeline (se=1.0):  0%
  broken pipeline  (se=0.5):  25%
------------------------------------------------------
  the correct rate sits near alpha; the broken rate is far above it
```

The correct pipeline's A/A false-positive rate is 0%, consistent with a 5% α on a small sample — the machinery is calibrated. The broken pipeline flags 25% of identical-arm comparisons as significant, five times α, which is impossible for a correct test and so is proof of a defect. That single number condemns the pipeline without anyone needing to find the exact bug first.

<svg role="img" aria-label="False-positive rates against the 5% alpha line: correct pipeline at 0%, broken pipeline at 25%, well above alpha" viewBox="0 0 440 140">
<line x1="40" y1="115" x2="410" y2="115" stroke="var(--line)"/>
<line x1="40" y1="105" x2="410" y2="105" stroke="var(--s2)" stroke-dasharray="4 3"/>
<text x="405" y="101" fill="var(--s2)" font-size="8" text-anchor="end">alpha 5%</text>
<rect x="90" y="114" width="80" height="1" fill="var(--s1)"/>
<text x="130" y="128" fill="var(--muted)" font-size="9" text-anchor="middle">correct 0%</text>
<rect x="290" y="35" width="80" height="80" fill="var(--s2)"/>
<text x="330" y="29" fill="var(--ink)" font-size="9" text-anchor="middle">25%</text>
<text x="330" y="128" fill="var(--muted)" font-size="9" text-anchor="middle">broken pipeline</text>
</svg>
^ The correct pipeline's A/A false-positive rate hugs the α line; the broken one towers five times above it, condemning the apparatus.

## Build

The self-test plants the failure and names each claim as a boolean flag. It computes both false-positive rates and checks that the arms have no true effect, that the correct pipeline's rate is at or below α, that the broken SE inflates every z-score, that the broken rate exceeds α, and that the A/A test therefore reveals the broken pipeline.

```python filename=modules/evals-and-statistics/code/aatest-inter-01/aatest.py:82-92 COMPLETE
    correct_fpr_near_alpha = correct_fpr <= a + 1e-9
    print("  correct pipeline's false-positive rate is at or below alpha = %s (%.0f%% vs %.0f%%)"
          % (correct_fpr_near_alpha, 100 * correct_fpr, 100 * a))

    broken_inflates_z = all(abs(z_score(d, bse)) >= abs(z_score(d, se)) for d in diffs)
    print("  the broken (smaller) se inflates every z score = %s" % broken_inflates_z)

    broken_fpr_above_alpha = broken_fpr > a
    print("  broken pipeline's false-positive rate exceeds alpha = %s (%.0f%%)" % (broken_fpr_above_alpha, 100 * broken_fpr))

    aa_detects_broken = broken_fpr > correct_fpr
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the correct pipeline ever over-fires or the broken one ever hides:

```text filename=aatest.py --check
SELF-TEST — a correct pipeline's A/A false-positive rate matches alpha; a too-small variance inflates it far above
--------------------------------------------------------------------------------------------------------------------
  the arms are identical, so any significance is a false positive = True
  correct pipeline's false-positive rate is at or below alpha = True (0% vs 5%)
  the broken (smaller) se inflates every z score = True
  broken pipeline's false-positive rate exceeds alpha = True (25%)
  the A/A test reveals the broken pipeline (higher FPR) = True
```

**The self-test checks the correct pipeline stays at α AND the broken one exceeds it — proving the A/A test both certifies a sound pipeline and flags a broken one, rather than merely rejecting everything.**

## Definition of done

You can explain why an A/B result is only as trustworthy as its pipeline and why you usually cannot check that pipeline against a known answer.
You can state what an A/A test is and why its true effect is exactly zero, making its correct outcome knowable in advance.
You can explain why a correct pipeline's A/A false-positive rate equals α (p-values are uniform under the null).
You can name the defect an A/A test most often catches — an underestimated variance — and how it inflates test statistics.
You can explain why the A/A test is an end-to-end integration check, catching a bug as one number without isolating which stage is wrong.

## Boss fight

An A/A false-positive rate that is too low is also a signal, in the opposite direction. If a pipeline flags far fewer than α of A/A comparisons — say 0% over hundreds of runs where 5% was expected — its variance estimate is too large, and while that will not manufacture fake wins, it will make the pipeline underpowered: real A/B effects will fail to reach significance because the inflated noise band swallows them. The lesson sharpens: the A/A false-positive rate should match α, not merely stay under it; too high means false positives, too low means missed real effects, and only a rate near α means the variance estimate is right.

Now consider what an A/A test cannot catch. It validates the null behavior — how the pipeline treats no effect — but says nothing about power, the pipeline's ability to detect a real effect when one exists. A pipeline could pass the A/A test perfectly and still be unable to detect a true 2% lift because the sample is too small or the metric too noisy. So the A/A test is necessary but not sufficient: pair it with a power analysis (or an A/B test with a known injected effect, an A/B/A) to confirm the pipeline both stays calm on nulls and reacts to real signal. Calibration and power are two separate properties, and the A/A test checks only the first.

**The A/A rate should match α, not just fall below it — too low means an over-large variance and an underpowered test — and the A/A test checks only null behavior, so it must be paired with a power check to confirm the pipeline can also detect a real effect.**

## External resources

Kohavi, Tang, and Xu's "Trustworthy Online Controlled Experiments" recommends A/A tests as a standard pipeline-validation step and catalogs the failures they expose.
Microsoft's and other experimentation platforms' engineering blogs describe running continuous A/A tests to monitor false-positive rates and detect variance-estimation and sample-ratio bugs.
The topic's own modules on sample ratio mismatch and on analysis-unit variance cover specific defects an A/A test surfaces as an inflated false-positive rate.
