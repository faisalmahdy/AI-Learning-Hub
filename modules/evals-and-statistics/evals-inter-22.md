---
id: evals-inter-22
title: Test the difference, not whether the two error bars overlap — or you call a real win a tie
topic: evals-and-statistics
level: intermediate
status: ready
time: 17 min
summary: The tempting shortcut when comparing two systems is visual — draw each one's confidence interval and, if the bars overlap, call it a tie. It feels rigorous but it is the wrong test, biased toward declaring no difference. Significance is a property of the difference, and the difference has its own standard error that is smaller than the two bars suggest, because independent errors add in quadrature: the standard error of A−B is sqrt(SE_a² + SE_b²), not SE_a + SE_b. The overlap test implicitly uses the larger linear sum, so it demands the bars be farther apart than significance requires and misses real wins. On a fixture where A scores 0.80 and B scores 0.87 each with SE 0.02, the 95% intervals [0.761, 0.839] and [0.831, 0.909] overlap — the eyeball says tie — but the difference 0.07 has SE 0.0283, sits 2.47 SEs from zero, and its interval [0.015, 0.125] excludes zero: the difference is significant.
eli5: Two runners' finish-time ranges can overlap a little and yet one is really faster — because the question isn't whether their ranges touch, it's how sure you are about the GAP between them, and you can be surer about the gap than about either runner's exact time. Comparing the two error bars by eye throws that away and makes you call a real winner a tie. Measure the gap directly instead.
---

## Why this module

Comparing two systems by glancing at whether their error bars overlap answers the wrong question, and it answers it in a way that systematically hides real differences.

The instinct is reasonable: each system has a confidence interval, so overlapping intervals must mean the two are statistically indistinguishable. But significance is not a property of the two intervals separately — it is a property of their difference, and the difference carries its own uncertainty that is *smaller* than the two individual bars imply. Independent errors add in quadrature, not linearly: the standard error of A minus B is `sqrt(SE_a² + SE_b²)`, which is always less than `SE_a + SE_b`. The overlap test behaves as if the relevant margin were the linear sum — it requires the bars to be a full sum-of-margins apart before it will admit a difference — so it sets the bar too high and calls genuine wins ties. There is a whole zone where the intervals visibly overlap yet the difference is significant, and the eyeball test lives entirely on the wrong side of it.

**Significance belongs to the difference, whose standard error is sqrt(SE_a² + SE_b²) — smaller than the summed margins the overlap test implicitly uses — so overlapping intervals do not mean the difference is insignificant.**

The correct test computes the difference of the means and divides by its own standard error; if that exceeds the 95% multiplier — equivalently, if the difference's confidence interval excludes zero — the difference is significant, regardless of whether the original intervals overlapped. This module scores two systems whose intervals overlap, then tests the difference directly and shows it is significant, exposing the overlap heuristic as the wrong tool.

## Concepts

A **system's confidence interval** is `mean ± z·SE` — the plausible range for that one system's true score. Two such intervals answer questions about each system separately.

The **overlap heuristic** declares "no significant difference" when the two intervals share any range. It is intuitive and wrong, because it never looks at the difference directly.

The **difference's standard error** is `sqrt(SE_a² + SE_b²)`. Independent errors combine in quadrature, so this is smaller than `SE_a + SE_b` — you know the gap more precisely than you know either endpoint.

**The correct test** asks whether the difference of the means exceeds `z·sqrt(SE_a² + SE_b²)`, i.e. whether the difference's own interval excludes zero. This is the question you meant to ask.

**The overlap test is biased toward "no difference."** Because it implicitly uses the larger linear sum of margins, it requires more separation than significance does, so its errors run one way: it turns real wins into ties, never the reverse.

```python filename=modules/evals-and-statistics/code/evals-inter-22/overlap.py:43-52 COMPLETE
def interval(system, z):
    """A system's confidence interval: mean +/- z*se."""
    return system["mean"] - z * system["se"], system["mean"] + z * system["se"]


def intervals_overlap(a, b, z):
    """Do the two confidence intervals share any range?"""
    lo_a, hi_a = interval(a, z)
    lo_b, hi_b = interval(b, z)
    return hi_a >= lo_b and hi_b >= lo_a
```

**Whether two error bars overlap is the wrong test: the difference has a tighter standard error than the bars show, so test the gap directly rather than eyeballing the overlap.**

<svg role="img" aria-label="The overlap test uses SE_a plus SE_b linearly at 0.04, but the difference's true error adds in quadrature to 0.028, a smaller margin" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">margin the difference is judged against</text>
  <line x1="60" y1="20" x2="60" y2="74" stroke="var(--grid)" stroke-width="1"/>
  <line x1="60" y1="74" x2="285" y2="74" stroke="var(--grid)" stroke-width="1"/>
  <rect x="60" y="26" width="180" height="16" fill="var(--s2)"/><text x="64" y="38" fill="var(--panel)" font-size="8">overlap uses SE_a + SE_b = 0.040</text>
  <rect x="60" y="50" width="127" height="16" fill="var(--s1)"/><text x="64" y="62" fill="var(--panel)" font-size="8">true SE = √(SE_a²+SE_b²) = 0.028</text>
  <text x="60" y="92" fill="var(--muted)" font-size="8">the real margin is smaller, so significance needs less separation than overlap demands</text>
</svg>
^ The overlap test judges the gap against the long linear-sum margin; the difference's real margin is the shorter quadrature one, which is why overlap demands too much separation.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/evals-inter-22/overlap.py

The fixture is two systems, each a mean and a standard error, plus the 95% multiplier.

```json filename=modules/evals-and-statistics/code/evals-inter-22/overlap.json:1-7 COMPLETE
{
  "_meta": "Two systems' eval scores as a mean and a standard error each. A common shortcut is to draw each system's 95% confidence interval (mean +/- 1.96*SE) and, if the two intervals OVERLAP, conclude the difference is not significant. That shortcut is wrong. The right test is on the DIFFERENCE of the means, whose standard error is sqrt(SE_a^2 + SE_b^2) -- smaller than the sum of the two individual margins, because independent errors add in quadrature, not linearly. So two intervals can overlap while the difference's own interval excludes zero, meaning the difference IS significant. z is the 95% multiplier. This fixture is tuned so the two CIs overlap yet the difference is significant.",
  "system_a": {"mean": 0.80, "se": 0.02},
  "system_b": {"mean": 0.87, "se": 0.02},
  "z": 1.96
}
```

The difference's standard error adds in quadrature; the difference is significant when it clears z of those.

```python filename=modules/evals-and-statistics/code/evals-inter-22/overlap.py:55-62 COMPLETE
def diff_se(a, b):
    """Standard error of the difference: independent errors add in quadrature."""
    return math.sqrt(a["se"] ** 2 + b["se"] ** 2)


def diff_significant(a, b, z):
    """Is the difference significant? Its interval excludes zero iff |diff| > z * diff_se."""
    return abs(b["mean"] - a["mean"]) > z * diff_se(a, b)
```

Run `--intervals` to see the two bars and whether they overlap.

```text filename=--intervals
INTERVALS — each system's 95% interval (mean +/- 1.96*SE)
------------------------------------------------------------
  A: mean 0.80  SE 0.02  ->  [0.761, 0.839]
  B: mean 0.87  SE 0.02  ->  [0.831, 0.909]
  intervals overlap: True
------------------------------------------------------------
  the bars overlap, so the eyeball test would call this a tie.
```

System A's interval runs to 0.839, system B's starts at 0.831, so they overlap in the sliver from 0.831 to 0.839. A reviewer eyeballing these two bars sees them touch and concludes the systems are statistically indistinguishable — a tie. That conclusion is about to be wrong, and the reason is that the overlap between two intervals is not the quantity that determines whether their difference is significant.

<svg role="img" aria-label="System A's interval 0.761 to 0.839 and system B's 0.831 to 0.909 overlap slightly between 0.831 and 0.839" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">95% intervals on the score axis</text>
  <line x1="20" y1="80" x2="285" y2="80" stroke="var(--grid)" stroke-width="1"/>
  <text x="20" y="94" fill="var(--muted)" font-size="7">0.76</text><text x="255" y="94" fill="var(--muted)" font-size="7">0.91</text>
  <line x1="30" y1="34" x2="170" y2="34" stroke="var(--s1)" stroke-width="3"/><circle cx="100" cy="34" r="3" fill="var(--s1)"/><text x="100" y="28" fill="var(--s1)" font-size="7">A 0.80</text>
  <line x1="150" y1="52" x2="290" y2="52" stroke="var(--s2)" stroke-width="3"/><circle cx="220" cy="52" r="3" fill="var(--s2)"/><text x="215" y="47" fill="var(--s2)" font-size="7">B 0.87</text>
  <rect x="150" y="30" width="20" height="26" fill="var(--muted)" opacity="0.4"/><text x="130" y="70" fill="var(--muted)" font-size="7">overlap</text>
  <text x="20" y="98" fill="var(--muted)" font-size="8">the bars touch in a thin band — the eyeball verdict is 'tie'</text>
</svg>
^ The two intervals overlap in the shaded band, so comparing the bars by eye reads as a tie — the verdict this module is about to overturn.

## Build

Now test the difference itself. Run `--difference`.

```text filename=--difference
DIFFERENCE — the test that actually answers the question
------------------------------------------------------------
  difference B - A:            0.070
  SE of difference sqrt(a^2+b^2): 0.0283   (< SE_a + SE_b = 0.040)
  difference in SEs:           2.47   (> 95% cutoff 1.96)
  difference interval:         [0.015, 0.125]  excludes 0: True
```

The difference is 0.07, and its standard error is `sqrt(0.02² + 0.02²) = 0.0283` — notice that is smaller than the linear sum `0.02 + 0.02 = 0.04` that the overlap test effectively used. Dividing, the difference sits 2.47 standard errors from zero, past the 1.96 cutoff, and its own 95% interval `[0.015, 0.125]` excludes zero. So the difference is significant: B really does beat A at the 95% level. The overlap test said tie; the correct test says win, and the entire discrepancy is the gap between adding the margins linearly (what overlap does) and in quadrature (what the difference actually has).

<svg role="img" aria-label="The difference interval 0.015 to 0.125 sits entirely to the right of zero, so the difference is significant" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">95% interval of the difference B - A</text>
  <line x1="30" y1="60" x2="285" y2="60" stroke="var(--grid)" stroke-width="1"/>
  <line x1="55" y1="24" x2="55" y2="72" stroke="var(--s2)" stroke-width="1" stroke-dasharray="3 3"/><text x="48" y="20" fill="var(--s2)" font-size="7">0</text>
  <line x1="95" y1="45" x2="255" y2="45" stroke="var(--s1)" stroke-width="3"/><circle cx="140" cy="45" r="3" fill="var(--s1)"/><text x="120" y="39" fill="var(--s1)" font-size="7">diff 0.07</text>
  <text x="88" y="84" fill="var(--muted)" font-size="7">0.015</text><text x="240" y="84" fill="var(--muted)" font-size="7">0.125</text>
  <text x="30" y="96" fill="var(--muted)" font-size="8">the whole interval is right of the dashed zero line — a significant win</text>
</svg>
^ The difference's interval lies entirely to the right of zero, so the gap is significant — the direct test the overlapping bars could not deliver.

## Definition of done

The self-test pins the contradiction: the intervals overlap, the difference is significant, the two tests disagree, the difference's SE is smaller than the summed margins, and the difference clears the cutoff.

```python filename=modules/evals-and-statistics/code/evals-inter-22/overlap.py:99-113 COMPLETE
    overlap = intervals_overlap(a, b, z)
    print("  the two 95%% confidence intervals overlap = %s" % overlap)

    significant = diff_significant(a, b, z)
    print("  the difference is significant (its interval excludes zero) = %s" % significant)

    overlap_test_disagrees = overlap and significant
    print("  the overlap test and the difference test disagree = %s (overlap says tie, difference says win)" % overlap_test_disagrees)

    diff_se_smaller = diff_se(a, b) < a["se"] + b["se"]
    print("  the difference's SE is smaller than the summed margins = %s (%.4f < %.3f)" % (diff_se_smaller, diff_se(a, b), a["se"] + b["se"]))

    d_sigmas = abs(b["mean"] - a["mean"]) / diff_se(a, b)
    difference_clears_cutoff = d_sigmas > z
    print("  the difference is more than %.2f SEs from zero = %s (%.2f)" % (z, difference_clears_cutoff, d_sigmas))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the intervals overlap yet the difference is significant, so the overlap test is wrong here
--------------------------------------------------------------------------------------------------------
  the two 95% confidence intervals overlap = True
  the difference is significant (its interval excludes zero) = True
  the overlap test and the difference test disagree = True (overlap says tie, difference says win)
  the difference's SE is smaller than the summed margins = True (0.0283 < 0.040)
  the difference is more than 1.96 SEs from zero = True (2.47)
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  overlap=True  significant=True  overlap_test_disagrees=True  diff_se_smaller=True  difference_clears_cutoff=True
```

**Done means the disagreement is proven: the 95% intervals overlap, yet the difference of 0.07 has SE 0.0283 (smaller than the 0.04 summed margins), sits 2.47 SEs from zero, and its interval [0.015, 0.125] excludes zero — so the overlap test called a significant win a tie.**

## Boss fight

Overlap was too conservative here. Predict whether non-overlapping bars, conversely, always mean a significant difference, and what the right visual is if you must show error bars. It is tempting to flip the rule and trust non-overlap as proof of significance.

Non-overlap is the safe direction but not a clean rule either. If two 95% intervals do not overlap, the difference is always significant at 0.05 (and then some), so non-overlap is sufficient — but it is stricter than necessary, so it too can mislead in the other direction: bars that just barely fail to overlap correspond to a difference well past significance, and bars that overlap can still be significant, as here. The honest statement is asymmetric: non-overlapping 95% CIs imply significance, but overlapping ones imply nothing. If you want a visual whose overlap *does* map to significance, plot the confidence interval of the difference and check whether it crosses zero — that is the picture that answers the question — or use the rule of thumb that for equal SEs, 95% CIs may overlap by up to about 29% of their average arm and the difference is still significant at 0.05.

The deeper habit is to compute the comparison you actually care about rather than reading it off a chart of the parts. Two error bars are a display of two estimates; the difference is a third quantity with its own estimate and its own error, and it deserves its own interval. This generalizes: whenever you want to know about a combination of measured quantities — a difference, a ratio, a sum — propagate the uncertainty into that combination rather than eyeballing the inputs, because independent errors combine in quadrature and the combined quantity is often known more precisely (or, for ratios near zero, far less precisely) than the inputs suggest. The chart of the parts is not the test of the whole.

```python filename=modules/evals-and-statistics/code/evals-inter-22/overlap.py:86-89 COMPLETE
    print("  difference B - A:            %.3f" % d)
    print("  SE of difference sqrt(a^2+b^2): %.4f   (< SE_a + SE_b = %.3f)" % (sd, a["se"] + b["se"]))
    print("  difference in SEs:           %.2f   (%s 95%% cutoff %.2f)" % (d / sd, ">" if d / sd > z else "<=", z))
    print("  difference interval:         [%.3f, %.3f]  excludes 0: %s" % (d - z * sd, d + z * sd, (d - z * sd) > 0))
```

**Overlapping confidence intervals do not mean no difference — the difference has its own standard error, sqrt(SE_a² + SE_b²), smaller than the summed margins — so test the gap directly (its interval against zero); non-overlap does imply significance but is stricter than needed, and the general rule is to propagate uncertainty into the quantity you care about, not eyeball the parts.**

## External resources

Cumming and Finch's "Inference by Eye" — the paper quantifying when confidence intervals may overlap and the difference still be significant, with the ~29% overlap rule of thumb for equal standard errors.

Any statistics text's section on the standard error of a difference and error propagation — the quadrature formula `sqrt(SE_a² + SE_b²)` and why independent errors combine that way.

The companion "two systems, thirty cases — the interval that decides whether B beat A" and "pair the comparison on the same cases" modules — both compute the interval of the difference directly, which is exactly the test this module argues for over eyeballing overlap.
