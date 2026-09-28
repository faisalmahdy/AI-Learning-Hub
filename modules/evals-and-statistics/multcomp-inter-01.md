---
id: multcomp-inter-01
title: Test 20 metrics at 0.05 and a false winner is more likely than not — the threshold is per-test, the risk is per-family
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: A 0.05 significance threshold is a promise about one test — if nothing is really going on, a 5% chance of clearing the bar by luck. That promise is per-test and does not survive repetition. Run the same 0.05 test on 20 independent metrics of an unchanged system and the chance that at least one clears the bar by luck is not 5% but 1-(0.95)^20 = 0.64, so on a 20-metric dashboard comparing a change that does nothing you should expect about one significant result (20 × 0.05 = 1), and finding one is not evidence of an effect — it is exactly what noise produces. This is the multiple-comparisons problem, and it compounds across metrics, segments, model variants, and repeated peeks at the same experiment. The fix is to control error across the family, not per test: the Bonferroni correction requires each test to clear alpha/n (here 0.0025) to hold the family-wise false-positive rate at alpha. On a fixture of 20 p-values from an A/A test (same system versus itself, so every win is false), naive 0.05 testing flags metric_01 at p=0.0375 — one false positive, exactly the ~1 predicted — while Bonferroni's 0.0025 bar correctly flags none.
eli5: If you flip a fair coin and it lands heads, that's not surprising. But if you flip twenty coins and ask "did ANY of them land heads five times in a row?", now a rare-looking event is actually pretty likely — because you gave luck twenty chances instead of one. Testing twenty metrics for a "win" is the same: each metric is one coin, and with enough coins something is bound to look special by chance even when nothing changed. So before you get excited that one metric moved, you have to remember how many metrics you checked — the more you looked, the higher the bar each result has to clear to count.
---

## Why this module

Every experiment dashboard shows many numbers, and the more numbers it shows, the more likely one of them looks like a win that isn't. The 0.05 you trust for a single test silently stops meaning what you think the moment there are twenty tests — and the failure looks exactly like a discovery.

A significance threshold of 0.05 is a promise about one test: if nothing is really going on, there is a 5% chance the test clears the bar by luck, a false positive. That promise is per-test, and it does not survive being repeated. Run the same 0.05 test on 20 independent metrics of an unchanged system and the chance that at least one clears the bar by luck is not 5% — it is 1 minus the chance all 20 stay under, 1-(0.95)^20 = 0.64. So on a dashboard of 20 metrics comparing a change that does nothing, you should expect about one significant result (20 × 0.05 = 1), and finding one is not evidence of an effect — it is exactly what pure noise produces. The error is treating a per-test false-positive rate as if it were the rate for the whole family of tests you actually ran.

This is the multiple-comparisons problem, and it is everywhere in evaluation: many metrics, many segments, many model variants, many days of peeking at the same experiment — each additional look is another draw at the 5% lottery, and the family-wise error rate (the chance of any false positive) climbs toward certainty. The fix is to control error across the family, not per test. The Bonferroni correction is the simplest: to hold the family-wise false-positive rate at alpha, require each test to clear alpha/n instead of alpha — here 0.05/20 = 0.0025. It is conservative and less blunt procedures exist, but the principle is fixed: the more comparisons you make, the higher the bar each one must clear. This module runs 20 A/A p-values through both and shows the false winner appear and vanish.

**A 0.05 threshold bounds the false-positive rate of a single test, but across n tests the chance of at least one false positive is 1-(1-alpha)^n, so a multi-metric comparison must control error over the whole family — otherwise an expected ~1 false winner per 20 metrics gets reported as a real effect.**

## Concepts

**The family-wise error rate** is the chance of at least one false positive across all n tests. For independent tests each at level alpha it is 1 minus the chance all n avoid a false positive — and it rises fast with n.

```python filename=modules/evals-and-statistics/code/multcomp-inter-01/multcomp.py:43-45 COMPLETE
def family_wise_error(alpha, n):
    """Chance of AT LEAST ONE false positive across n independent tests each at level alpha: 1 - (1-alpha)^n."""
    return 1 - (1 - alpha) ** n
```

**The Bonferroni threshold** is the repair: divide alpha by the number of tests, so each test must clear alpha/n. This holds the family-wise rate at (at most) alpha, at the cost of a much stricter per-test bar.

```python filename=modules/evals-and-statistics/code/multcomp-inter-01/multcomp.py:48-50 COMPLETE
def bonferroni_threshold(alpha, n):
    """The per-test bar that holds the family-wise false-positive rate at alpha: alpha / n."""
    return alpha / n
```

<svg role="img" aria-label="A curve of the family-wise error rate rising with the number of tests, from 0.05 at one test toward near-certainty, passing 0.64 at twenty tests" viewBox="0 0 300 128" width="300" height="128">
  <text x="6" y="12" fill="var(--muted)" font-size="8">chance of ≥1 false positive climbs with the number of tests</text>
  <line x1="34" y1="104" x2="290" y2="104" stroke="var(--line)"/>
  <line x1="34" y1="20" x2="34" y2="104" stroke="var(--line)"/>
  <text x="28" y="24" fill="var(--muted)" font-size="7" text-anchor="end">1.0</text>
  <text x="28" y="66" fill="var(--muted)" font-size="7" text-anchor="end">0.5</text>
  <text x="28" y="104" fill="var(--muted)" font-size="7" text-anchor="end">0</text>
  <polyline points="34,100 60,74 86,57 112,45 138,38 164,33 190,30 216,27 242,25 268,24" fill="none" stroke="var(--s1)"/>
  <line x1="112" y1="45" x2="112" y2="104" stroke="var(--s2)" stroke-dasharray="2 2"/>
  <circle cx="112" cy="45" r="3" fill="var(--s2)"/>
  <text x="98" y="118" fill="var(--muted)" font-size="7">n=20</text>
  <text x="120" y="42" fill="var(--muted)" font-size="7">0.64</text>
  <text x="240" y="118" fill="var(--muted)" font-size="7">n → tests</text>
</svg>
^ With one test the false-positive chance is the nominal 0.05; by 20 tests the chance of at least one false positive has climbed to 0.64, and it approaches certainty as more comparisons are added.

**The per-test false-positive rate stays 5%, but the family-wise rate is 1-(1-alpha)^n and passes one-half well before 20 tests — so error has to be budgeted across the family, which Bonferroni does by tightening each test's bar to alpha/n.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/multcomp-inter-01/multcomp.py

The fixture is 20 p-values from an A/A test — the same system compared to itself, so there is no true effect and every win is false by construction. Under the null a p-value is uniform on [0,1]; these are 20 such draws.

```json filename=modules/evals-and-statistics/code/multcomp-inter-01/multcomp.json:3-6 COMPLETE
  "alpha": 0.05,
  "metric_pvalues": {
    "metric_01": 0.0375,
    "metric_02": 0.0580,
```

Run `--naive`, testing each metric independently at 0.05.

```text filename=--naive
NAIVE — every metric tested independently at alpha=0.05 (A/A test: no true effect)
------------------------------------------------------------------
  metric_01   p=0.0375  <- SIGNIFICANT (p<0.05)
  metric_02   p=0.0580
  metric_03   p=0.0699
  metric_04   p=0.0724
  metric_05   p=0.0907
  metric_06   p=0.1238
  metric_07   p=0.1508
  metric_08   p=0.2232
  metric_09   p=0.3238
  metric_10   p=0.3657
  metric_11   p=0.3967
  metric_12   p=0.4245
  metric_13   p=0.4336
  metric_14   p=0.5074
  metric_15   p=0.5359
  metric_16   p=0.5771
  metric_17   p=0.6274
  metric_18   p=0.6509
  metric_19   p=0.8269
  metric_20   p=0.9477
------------------------------------------------------------------
  1 metric(s) flagged 'significant': ['metric_01'] -- but the system did not change, so these are false positives.
```

metric_01 comes in at p=0.0375, under 0.05, and the naive procedure stamps it significant. If this were a real experiment you would now write "metric_01 improved significantly" in the launch review, ship the change, and attribute a permanent win to what is provably nothing — the system was compared to itself. Notice the shape of the p-values: they run from 0.0375 up to 0.9477, spread across the whole interval, which is exactly what the null produces (uniform p-values), and out of twenty of them one dipped below 0.05. That is not bad luck to be explained; it is the expected outcome, because 20 × 0.05 = 1. The mistake is not that metric_01 got an unlucky draw — it is asking twenty questions and getting excited about the one that answered yes.

## Build

Controlling error across the family makes the same p-values report the truth. Run `--correct`.

```text filename=--correct
CORRECT — control error across the whole family of 20 tests
------------------------------------------------------------------
  family-wise error rate (chance of >=1 false positive) = 1-(1-0.05)^20 = 0.6415
  so with no real effect you EXPECT about 1.0 false 'wins' (20 x 0.05)
  Bonferroni threshold = 0.05/20 = 0.0025
  metrics clearing the Bonferroni bar: none
------------------------------------------------------------------
  smallest p-value is 0.0375, above 0.0025 -- correctly, no metric is called significant.
```

The family-wise error rate spells out why the naive result was meaningless: with 20 tests, the chance of at least one false positive under the null was 0.64, so seeing one significant metric was more likely than not seeing one. Bonferroni tightens the bar to 0.05/20 = 0.0025, and now the smallest p-value in the whole set, metric_01's 0.0375, is an order of magnitude short — no metric clears it, and the honest conclusion "nothing changed" is restored. The correction did not analyze metric_01 specially; it just applied a threshold set by how many tests were run, and whether a p-value clears a threshold is one comparison.

```python filename=modules/evals-and-statistics/code/multcomp-inter-01/multcomp.py:53-55 COMPLETE
def flagged(pvalues, threshold):
    """The metrics whose p-value clears (is below) the threshold."""
    return [m for m, p in sorted(pvalues.items()) if p < threshold]
```

<svg role="img" aria-label="The 20 p-values on a 0 to 1 axis, with the 0.05 naive threshold and the much stricter 0.0025 Bonferroni threshold marked; metric_01 falls between them" viewBox="0 0 300 110" width="300" height="110">
  <text x="6" y="12" fill="var(--muted)" font-size="8">metric_01 clears 0.05 but not the Bonferroni 0.0025 bar</text>
  <line x1="20" y1="60" x2="290" y2="60" stroke="var(--line)"/>
  <text x="20" y="76" fill="var(--muted)" font-size="7">0</text><text x="278" y="76" fill="var(--muted)" font-size="7">1.0</text>
  <line x1="33" y1="40" x2="33" y2="80" stroke="var(--s1)"/><text x="20" y="34" fill="var(--s1)" font-size="7">0.05</text>
  <line x1="27" y1="46" x2="27" y2="74" stroke="var(--s2)"/><text x="26" y="94" fill="var(--s2)" font-size="7">0.0025 (Bonf.)</text>
  <circle cx="30" cy="60" r="3" fill="var(--ink)"/><text x="24" y="26" fill="var(--muted)" font-size="6">metric_01</text>
  <line x1="30" y1="28" x2="30" y2="56" stroke="var(--muted)" stroke-dasharray="1 1"/>
  <circle cx="36" cy="60" r="2" fill="var(--muted)"/><circle cx="39" cy="60" r="2" fill="var(--muted)"/><circle cx="40" cy="60" r="2" fill="var(--muted)"/><circle cx="44" cy="60" r="2" fill="var(--muted)"/><circle cx="53" cy="60" r="2" fill="var(--muted)"/><circle cx="61" cy="60" r="2" fill="var(--muted)"/><circle cx="80" cy="60" r="2" fill="var(--muted)"/><circle cx="107" cy="60" r="2" fill="var(--muted)"/><circle cx="119" cy="60" r="2" fill="var(--muted)"/><circle cx="127" cy="60" r="2" fill="var(--muted)"/><circle cx="135" cy="60" r="2" fill="var(--muted)"/><circle cx="157" cy="60" r="2" fill="var(--muted)"/><circle cx="165" cy="60" r="2" fill="var(--muted)"/><circle cx="176" cy="60" r="2" fill="var(--muted)"/><circle cx="189" cy="60" r="2" fill="var(--muted)"/><circle cx="203" cy="60" r="2" fill="var(--muted)"/><circle cx="243" cy="60" r="2" fill="var(--muted)"/><circle cx="276" cy="60" r="2" fill="var(--muted)"/>
</svg>
^ The 20 p-values spread across the interval as the null predicts; only metric_01 falls left of the naive 0.05 line, and even it sits well right of the Bonferroni 0.0025 line, so the family-wise correction flags nothing.

## Definition of done

The self-test pins the false positive, the family-wise arithmetic, the expected count, and the correction that flags none.

```python filename=modules/evals-and-statistics/code/multcomp-inter-01/multcomp.py:95-107 COMPLETE
    naive_false_positive = len(naive_hits) >= 1
    print("  naive 0.05 testing flags a 'winner' on an A/A test = %s (%s)" % (naive_false_positive, naive_hits))

    fwer = family_wise_error(alpha, n)
    fwer_exceeds_half = fwer > 0.5
    print("  the family-wise error rate for %d tests exceeds 1/2 = %s (%.4f)" % (n, fwer_exceeds_half, fwer))

    expected_one = abs(n * alpha - 1.0) < 1e-9
    print("  the expected number of false positives is exactly 1 = %s (%d x %.2f)" % (expected_one, n, alpha))

    thr = bonferroni_threshold(alpha, n)
    bonferroni_none = len(flagged(pv, thr)) == 0
    print("  Bonferroni (bar %.4f) flags no metric = %s" % (thr, bonferroni_none))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — an A/A test yields a false positive under naive 0.05 testing; the family-wise error exceeds 1/2; Bonferroni flags none
--------------------------------------------------------------------------------------------------------------------------
  naive 0.05 testing flags a 'winner' on an A/A test = True (['metric_01'])
  the family-wise error rate for 20 tests exceeds 1/2 = True (0.6415)
  the expected number of false positives is exactly 1 = True (20 x 0.05)
  Bonferroni (bar 0.0025) flags no metric = True
  the Bonferroni bar is stricter than the per-test bar = True (0.0025 < 0.05)
```

**Done means the failure and the fix are both proven on the A/A p-values: naive 0.05 testing flags metric_01 (a false positive on a system that did not change), the family-wise error rate for 20 tests is 0.6415 with an expected 1.0 false wins, and the Bonferroni bar of 0.0025 — stricter than 0.05 — flags no metric, restoring the correct "no effect" conclusion.**

## Boss fight

Predict two ways this is subtler than "divide alpha by the number of metrics," because both the counting and the correction hide choices.

The first trap is that the family is usually larger than the metrics on the screen, and the worst inflation comes from looks you do not think of as tests. Peeking at a running experiment is the classic case: checking a single metric every day for two weeks and stopping the moment it crosses 0.05 is not one test at 0.05 — it is fourteen correlated tests with an early-stopping rule, and its true false-positive rate is far above 0.05, which is why sequential designs (alpha-spending, group-sequential boundaries, or always-valid confidence sequences) exist to let you look repeatedly without inflating error. The same hidden multiplicity hides in segments (the effect "in mobile users in Canada" found after slicing a dozen ways), in trying several test statistics, and in re-running after adding data. The count n that goes into any correction must include every comparison you actually made, including the ones you made informally by looking — and a result found by slicing after the fact is a hypothesis to test on fresh data, not a finding.

<svg role="img" aria-label="A single metric checked once per day for two weeks, each daily look a separate 0.05 draw, so the fourteen looks together are a family of tests even though only one metric is involved" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">one metric, checked daily — fourteen looks are fourteen tests</text>
  <text x="10" y="40" fill="var(--muted)" font-size="7">day:</text>
  <g transform="translate(36,30)">
  <rect x="0" y="0" width="14" height="14" fill="var(--panel)" stroke="var(--line)"/><rect x="17" y="0" width="14" height="14" fill="var(--panel)" stroke="var(--line)"/><rect x="34" y="0" width="14" height="14" fill="var(--panel)" stroke="var(--line)"/><rect x="51" y="0" width="14" height="14" fill="var(--panel)" stroke="var(--line)"/><rect x="68" y="0" width="14" height="14" fill="var(--panel)" stroke="var(--line)"/><rect x="85" y="0" width="14" height="14" fill="var(--panel)" stroke="var(--line)"/><rect x="102" y="0" width="14" height="14" fill="var(--s2)" stroke="var(--line)"/><rect x="119" y="0" width="14" height="14" fill="var(--panel)" stroke="var(--line)"/><rect x="136" y="0" width="14" height="14" fill="var(--panel)" stroke="var(--line)"/><rect x="153" y="0" width="14" height="14" fill="var(--panel)" stroke="var(--line)"/><rect x="170" y="0" width="14" height="14" fill="var(--panel)" stroke="var(--line)"/><rect x="187" y="0" width="14" height="14" fill="var(--panel)" stroke="var(--line)"/><rect x="204" y="0" width="14" height="14" fill="var(--panel)" stroke="var(--line)"/><rect x="221" y="0" width="14" height="14" fill="var(--panel)" stroke="var(--line)"/>
  </g>
  <text x="130" y="66" fill="var(--s2)" font-size="7">stop here: "significant!"</text>
  <line x1="145" y1="46" x2="145" y2="58" stroke="var(--s2)"/>
  <text x="10" y="86" fill="var(--muted)" font-size="7">stopping at the first day it crosses 0.05 is not one test at 0.05 — it is fourteen</text>
</svg>
^ Checking a single metric every day and stopping the moment it crosses 0.05 is a hidden family of fourteen correlated tests, so its true false-positive rate is far above 0.05 — the multiplicity you must correct for includes looks over time, not just metrics on the screen.

The second trap is that Bonferroni answers only one of two different questions, and using it when you want the other is its own mistake. Controlling the family-wise error rate — the chance of any false positive — is right when a single false claim is costly (a launch you cannot walk back, a safety metric). But it grows so strict with n that on a hundred metrics it will miss real effects; when you are screening many hypotheses and can tolerate a known fraction of false leads, you instead control the false-discovery rate — the expected fraction of your "wins" that are false — with a procedure like Benjamini-Hochberg, which is far more powerful. On this A/A fixture the distinction does not matter (nothing is real, so both flag none), but on a real screen it decides how many true effects you keep. And neither correction rescues an underpowered test: if each metric barely has the sample size to detect a real effect at 0.05, tightening the bar to 0.0025 guarantees you miss it, so the honest move when you must test many things is to plan the power and the correction together, not to bolt Bonferroni onto an experiment sized for one comparison.

**The count that drives any multiple-comparisons correction must include every look — peeks over time, segments, and post-hoc slices, not just the metrics on the dashboard — and the correction must match the goal: Bonferroni/family-wise control when one false positive is costly, Benjamini-Hochberg/false-discovery control when screening many hypotheses, with the test's power planned for the corrected bar rather than the nominal 0.05.**

## External resources

Any statistics reference on the multiple-comparisons problem — the family-wise error rate, Bonferroni and Holm corrections, and the Benjamini-Hochberg false-discovery-rate procedure, with the distinction between controlling FWER and FDR.

Writing on optional stopping and "peeking" in A/B testing — why repeatedly checking a running experiment inflates the false-positive rate, and the sequential/always-valid methods (alpha-spending, confidence sequences) that make continuous monitoring valid.

The companion equivalence-testing and stratification modules in this topic — together they cover the ways a naive read of an experiment misleads: declaring a false win from many looks (here), mistaking "not significant" for "no difference" (equivalence), and comparing on the wrong population mix (stratification).
