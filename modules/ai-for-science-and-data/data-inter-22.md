---
id: data-inter-22
title: Count independent units, not measurements — repeated looks at the same subject fake a tiny standard error
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 18 min
summary: Significance rests on how much independent information you have. Twenty measurements sound like twenty data points, but if they are five measurements each of four subjects, they are four independent looks sampled five times over — measurements of the same subject are correlated, so the fifth reading adds far less than the first. Treating all twenty as independent (pseudoreplication) inflates the sample size, and since the standard error falls like one over the square root of N, an inflated N shrinks the error, tightens the interval, and pushes the p-value down. On a fixture with a grand mean of 13 tested against a reference of 11, the naive standard error (N=20) is 0.607, putting the mean 3.3 standard errors away — significant — while the correct standard error (4 subjects) is 1.291, putting it only 1.5 away — not significant. The naive analysis manufactured a result the data does not contain.
eli5: If you ask one friend the same question five times and write down five answers, you don't have five opinions — you have one friend's opinion, five times. Counting it as five makes you feel far more sure of the group than you should be. To know what a crowd really thinks, count how many different people you asked, not how many times you asked. Repeated measurements of the same subject are the same friend answering again.
---

## Why this module

Twenty numbers feel like twenty pieces of evidence, but if they are repeated looks at four subjects they carry only four subjects' worth of independent information — and counting them as twenty makes every conclusion look far surer than the data allows.

A significance test asks how far a result sits from chance, measured in standard errors, and the standard error shrinks as the sample size grows — specifically like one over the square root of N. That makes N the lever on the whole conclusion. The trap is that N means the number of *independent* observations, and repeated measurements of the same subject are not independent: the second reading of a subject is highly predictable from the first, so it adds far less new information. Pool five measurements each from four subjects and call it N = 20, and you have inflated the count by five, shrunk the standard error by a factor of about the square root of five, and made the result look five-fold more certain than it is. This is pseudoreplication, and it turns correlated repeats into fake statistical power.

**The standard error falls like one over the square root of the sample size, so counting correlated repeats as independent observations inflates N, shrinks the error, and fabricates certainty the data does not hold.**

The fix is to count the independent units, not the measurements. If the four subjects are what vary independently, reduce each subject to its mean and compute the standard error from those four numbers — sd of the means over the square root of four. The correct standard error is larger, honestly reflecting four independent units rather than twenty, and the confidence interval it produces is wide enough to tell the truth. This module computes both and shows the same mean cross the significance line under the naive count and fall back under the honest one.

## Concepts

**Independent observations** are the units that vary freely from one another. A test's N is the count of these, and the standard error assumes every counted observation is one.

**Correlated repeats** are multiple measurements of the same unit. They are not independent — one predicts the next — so each adds less than a full observation's worth of information.

**Pseudoreplication** is counting correlated repeats as independent observations. It inflates N, and because the standard error is sd over the square root of N, an inflated N understates the error.

**The independent units here are the subjects.** Four subjects measured five times give four independent numbers, not twenty; the honest standard error divides by the square root of four, not twenty.

**The whole error lives in which N you divide by.** Both analyses use the same data; the naive one takes sd over the square root of the measurement count, the correct one takes the sd of subject means over the square root of the subject count.

```python filename=modules/ai-for-science-and-data/code/data-inter-22/pseudorep.py:51-60 COMPLETE
def naive_se(subjects):
    """Treat every measurement as independent: sd over all N measurements / sqrt(N)."""
    m = all_measurements(subjects)
    return statistics.stdev(m) / len(m) ** 0.5


def correct_se(subjects):
    """The independent units are the subjects: sd of the subject means / sqrt(number of subjects)."""
    means = subject_means(subjects)
    return statistics.stdev(means) / len(means) ** 0.5
```

**A standard error is only as small as your independent sample size allows, so the unit of replication must be the thing that varies independently — the subject — not each repeated measurement of it.**

<svg role="img" aria-label="Twenty measurements group into four subjects; the naive count is 20 rows but the independent count is 4 clusters" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">20 measurements, but 4 independent subjects</text>
  <g fill="var(--s2)"><rect x="20" y="24" width="9" height="9"/><rect x="31" y="24" width="9" height="9"/><rect x="42" y="24" width="9" height="9"/><rect x="53" y="24" width="9" height="9"/><rect x="64" y="24" width="9" height="9"/></g><text x="80" y="32" fill="var(--muted)" font-size="7">s1 (one subject)</text>
  <g fill="var(--s2)"><rect x="20" y="38" width="9" height="9"/><rect x="31" y="38" width="9" height="9"/><rect x="42" y="38" width="9" height="9"/><rect x="53" y="38" width="9" height="9"/><rect x="64" y="38" width="9" height="9"/></g><text x="80" y="46" fill="var(--muted)" font-size="7">s2</text>
  <g fill="var(--s2)"><rect x="20" y="52" width="9" height="9"/><rect x="31" y="52" width="9" height="9"/><rect x="42" y="52" width="9" height="9"/><rect x="53" y="52" width="9" height="9"/><rect x="64" y="52" width="9" height="9"/></g><text x="80" y="60" fill="var(--muted)" font-size="7">s3</text>
  <g fill="var(--s2)"><rect x="20" y="66" width="9" height="9"/><rect x="31" y="66" width="9" height="9"/><rect x="42" y="66" width="9" height="9"/><rect x="53" y="66" width="9" height="9"/><rect x="64" y="66" width="9" height="9"/></g><text x="80" y="74" fill="var(--muted)" font-size="7">s4</text>
  <text x="180" y="42" fill="var(--s1)" font-size="8">naive N = 20 (rows)</text>
  <text x="180" y="60" fill="var(--s1)" font-size="8">honest N = 4 (subjects)</text>
  <text x="20" y="98" fill="var(--muted)" font-size="8">each row is one subject answering five times — five rows, one independent unit</text>
</svg>
^ The twenty squares are real measurements, but they come in four rows of one subject each, so the independent count is four — dividing the error by the square root of twenty pretends the rows are the units.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/data-inter-22/pseudorep.py

The fixture is four subjects, each measured five times, and a reference value to test the mean against.

```json filename=modules/ai-for-science-and-data/code/data-inter-22/pseudorep.json:3-10 COMPLETE
  "subjects": {
    "s1": [8, 9, 10, 11, 12],
    "s2": [10, 11, 12, 13, 14],
    "s3": [12, 13, 14, 15, 16],
    "s4": [14, 15, 16, 17, 18]
  },
  "reference": 11
}
```

The distance of the mean from the reference, in standard errors, is what a test reports — and it depends entirely on which standard error you feed it.

```python filename=modules/ai-for-science-and-data/code/data-inter-22/pseudorep.py:63-65 COMPLETE
def sigmas_from(subjects, se, ref):
    """How many standard errors the grand mean sits from the reference value."""
    return abs(statistics.mean(all_measurements(subjects)) - ref) / se
```

Run `--se` to compare the two standard errors.

```text filename=--se
SE — standard error: all measurements vs independent subjects
------------------------------------------------------------
  grand mean:                13.0
  naive  (N=20 measurements): SE 0.607
  correct(k= 4 subjects):     SE 1.291  (2.1x larger)
------------------------------------------------------------
  the naive SE divides by sqrt(20); the honest one divides by sqrt(4).
```

Both analyses agree the grand mean is 13. But the naive standard error divides the spread by the square root of 20 and gets 0.607, while the correct one takes the four subject means, spreads them, and divides by the square root of 4, getting 1.291 — more than twice as large. Neither number is arithmetically wrong; they answer different questions. The naive one answers "how precisely do I know the mean of these twenty numbers," which is not the question — it treats five repeats as five subjects. The correct one answers "how precisely do I know the mean across subjects," which is what a claim about subjects requires.

<svg role="img" aria-label="The naive standard error 0.607 is less than half the correct standard error 1.291" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">standard error of the mean of 13</text>
  <line x1="60" y1="20" x2="60" y2="74" stroke="var(--grid)" stroke-width="1"/>
  <line x1="60" y1="74" x2="285" y2="74" stroke="var(--grid)" stroke-width="1"/>
  <rect x="60" y="26" width="60" height="16" fill="var(--s2)"/><text x="124" y="38" fill="var(--muted)" font-size="8">naive: 0.607 (÷√20)</text>
  <rect x="60" y="50" width="128" height="16" fill="var(--s1)"/><text x="192" y="62" fill="var(--muted)" font-size="8">correct: 1.291 (÷√4)</text>
  <text x="60" y="92" fill="var(--muted)" font-size="8">counting 20 instead of 4 makes the error look less than half its true size</text>
</svg>
^ The naive bar is under half the correct one — inflating the count from 4 subjects to 20 measurements is exactly what shrank the error to less than half its honest size.

## Build

A standard error only matters through the test it feeds. Run `--test`.

```text filename=--test
TEST — distance of the mean from the reference 11, in standard errors
------------------------------------------------------------
  naive:    3.30 SE  ->  SIGNIFICANT (>2)
  correct:  1.55 SE  ->  NOT significant (<2)
------------------------------------------------------------
  the same mean is 'significant' pseudoreplicated and not significant counted honestly.
```

The mean of 13 sits 2 above the reference of 11. Divided by the naive standard error of 0.607, that is 3.3 standard errors — past the rough 2-SE line, so the naive analysis declares a significant difference from the reference. Divided by the correct standard error of 1.291, it is only 1.5 standard errors — inside the noise, not significant. Same data, same mean, same reference: pseudoreplication moved the result from "no effect" to "significant effect" purely by miscounting the sample size. The honest four subjects simply do not pin the mean tightly enough to distinguish 13 from 11.

<svg role="img" aria-label="The mean is 3.3 naive standard errors from the reference, past the significance line, but only 1.5 correct standard errors, inside it" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">distance from reference, in standard errors</text>
  <line x1="30" y1="72" x2="285" y2="72" stroke="var(--grid)" stroke-width="1"/>
  <line x1="185" y1="20" x2="185" y2="72" stroke="var(--s2)" stroke-width="1" stroke-dasharray="3 3"/><text x="163" y="18" fill="var(--s2)" font-size="7">2 SE line</text>
  <rect x="30" y="28" width="215" height="14" fill="var(--s2)"/><text x="34" y="39" fill="var(--panel)" font-size="8">naive 3.3 SE → significant</text>
  <rect x="30" y="50" width="100" height="14" fill="var(--s1)"/><text x="134" y="61" fill="var(--muted)" font-size="8">correct 1.5 SE → not</text>
  <text x="30" y="92" fill="var(--muted)" font-size="8">the naive bar crosses the significance line; the honest one stops short</text>
</svg>
^ The naive bar reaches 3.3 SE and clears the significance line, while the honest bar stops at 1.5 SE, short of it — the same mean on opposite sides of significance.

## Definition of done

The self-test pins it: the naive SE understates by over 2x, the independent units are the subjects, the naive test looks significant, and the correct test does not.

```python filename=modules/ai-for-science-and-data/code/data-inter-22/pseudorep.py:99-112 COMPLETE
    naive_understates = naive_se(subs) < correct_se(subs)
    print("  the naive standard error is smaller than the correct one = %s (%.3f < %.3f)" % (naive_understates, naive_se(subs), correct_se(subs)))

    understated_by_2x = correct_se(subs) / naive_se(subs) > 2
    print("  the naive SE understates by more than 2x = %s (%.2fx)" % (understated_by_2x, correct_se(subs) / naive_se(subs)))

    independent_units_are_subjects = k < n
    print("  the independent units are the %d subjects, not the %d measurements = %s" % (k, n, independent_units_are_subjects))

    naive_looks_significant = sigmas_from(subs, naive_se(subs), ref) > 2
    print("  the naive test crosses 2 SE (looks significant) = %s (%.2f SE)" % (naive_looks_significant, sigmas_from(subs, naive_se(subs), ref)))

    correct_not_significant = sigmas_from(subs, correct_se(subs), ref) < 2
    print("  the correct test is under 2 SE (not significant) = %s (%.2f SE)" % (correct_not_significant, sigmas_from(subs, correct_se(subs), ref)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the naive SE understates; the independent units are the subjects; the naive test fakes significance
----------------------------------------------------------------------------------------------------------------
  the naive standard error is smaller than the correct one = True (0.607 < 1.291)
  the naive SE understates by more than 2x = True (2.13x)
  the independent units are the 4 subjects, not the 20 measurements = True
  the naive test crosses 2 SE (looks significant) = True (3.30 SE)
  the correct test is under 2 SE (not significant) = True (1.55 SE)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  naive_understates=True  understated_by_2x=True  independent_units_are_subjects=True  naive_looks_significant=True  correct_not_significant=True
```

**Done means the fabricated significance is proven: the same mean of 13 against a reference of 11 is 3.3 naive standard errors away (significant) and 1.5 correct ones (not), because the naive SE of 0.607 counts 20 measurements where only 4 subjects are independent.**

## Boss fight

Averaging each subject fixed it here. Predict when that simple fix is enough and when it is not, and where else pseudoreplication hides. It is tempting to think "just average within each unit" always solves it.

Averaging to the independent unit is the right instinct and often enough, but it throws away the within-subject information, which is wasteful when the measurements per subject vary in number or when you want to model the within-subject variation too. The general tool is a mixed-effects (hierarchical) model, which explicitly represents both levels — variation between subjects and variation within them — and computes standard errors that account for the correlation without discarding data. The design effect, roughly `1 + (m − 1)·ρ` for m measurements at intra-cluster correlation ρ, quantifies exactly how much your effective sample size shrinks: at ρ near 1 the m repeats collapse toward a single observation, at ρ near 0 they are nearly independent and little is lost. So the fix scales with the correlation: average when clusters are the unit of interest, model hierarchically when you need both levels, and always report the effective sample size, not the raw count.

The subtler danger is that pseudoreplication hides wherever a hidden unit ties observations together, not just obvious repeats. Measurements from the same instrument, plot, batch, classroom, or day share a common influence and are correlated; pixels in one image, words in one document, trials from one session — all are clusters masquerading as independent rows. The question to ask of every dataset is "what is the unit that varies independently, and does my N count that unit or something nested inside it?" A dataset of a million rows can carry the independent information of a dozen units, and no amount of rows fixes a shortage of units. Counting rows when you should be counting clusters is how a confidently tiny p-value comes from almost no independent evidence at all.

```python filename=modules/ai-for-science-and-data/code/data-inter-22/pseudorep.py:43-48 COMPLETE
def all_measurements(subjects):
    return [x for vals in subjects.values() for x in vals]


def subject_means(subjects):
    return [statistics.mean(vals) for vals in subjects.values()]
```

**Count the independent units — subjects, sites, sessions, batches — not the measurements, because correlated repeats inflate N and shrink the standard error into false significance; average to the unit or fit a hierarchical model, size the loss with the design effect, and always ask whether a hidden cluster ties your rows together.**

## External resources

Hurlbert's "Pseudoreplication and the Design of Ecological Field Experiments" — the paper that named pseudoreplication and catalogued the ways correlated observations get miscounted as independent.

Any text on mixed-effects / hierarchical models (for example the `lme4` documentation or Gelman and Hill) — the general tool for standard errors that respect clustering, plus the design-effect formula for how much effective sample size a cluster costs.

The companion "the law of small numbers" and "significance is not size" modules — small independent samples produce the most extreme rates, and a tiny p-value from an inflated N is significance without either size or real evidence.
