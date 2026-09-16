---
id: dichotomize-inter-01
title: Keep a continuous predictor continuous — splitting it into high/low throws away the within-group variation and weakens the association
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: It is tempting to turn a continuous predictor into two groups — split at the median, compare "high" to "low", report a clean two-group difference — because a t-test between two groups reads more easily than a regression coefficient on a continuous scale. But the simplicity is bought by destroying information, and the information destroyed is signal. A continuous variable distinguishes every value from every other; dichotomizing collapses each half to a single level, so a value just above the median and a value far above it become the same "high", and the outcome's dependence on how far above is erased. Whatever part of the association lived in those within-group differences is gone from the binary variable, and the measured correlation shrinks accordingly. The relationship does not vanish — it is real and still detectable — it is attenuated, and in a hypothesis test that shows up as reduced power: you need a larger sample for the same significance, or you miss a real effect you would have caught on the continuous scale (dichotomizing a predictor is often described as throwing away roughly a third of your data). What separates this from other attenuation is that it is a deliberate choice, not a limitation imposed on you — range restriction is a sampling constraint and measurement error is unavoidable noise, but dichotomizing is a decision the analyst makes, usually for a readability not worth the power. On a fixture where x and y are perfectly correlated (r = 1.0), splitting x at its median drops the correlation with y to about 0.87.
eli5: Imagine you're studying whether taller kids can reach higher on a wall. You measure everyone's exact height and how high they reach, and the relationship is crystal clear. But then, to make the report "simpler," you decide to just label each kid "short" or "tall" based on whether they're above the class median, and throw away the exact heights. Now a kid who is barely above average and a kid who is the tallest in the school are both just "tall" — even though the very tall kid reaches much higher. You've blurred together kids who are quite different, so the neat pattern between height and reach gets fuzzier and harder to see, even though it's still really there. Turning precise numbers into two crude buckets always loses some of the story, and the part it loses is exactly the part that shows the pattern.
---

## Why this module

Continuous data carries more information than categorical data, and an analysis's power to detect a relationship depends on how much of that information it uses. A continuous predictor records not just which side of some line a subject falls on but exactly where it falls, and that "exactly where" is often where much of the relationship with the outcome lives. Any transformation that discards it discards signal, and dichotomizing discards a lot of it at once.

The reason people do it anyway is presentation. "The high group scored 12 points more than the low group" is a sentence anyone understands; "each unit of the predictor is associated with a 0.4-point increase" asks the reader to think in slopes. So the continuous variable gets split at the median into two tidy groups, a two-sample test is run, and the result is reported as a clean comparison. The tidiness is real; the cost is hidden.

The cost is that the split merges subjects who genuinely differ. Everyone above the median becomes one undifferentiated "high", so the model can no longer see that the outcome keeps rising with the predictor within that group — it only sees "high versus low". The association measured on the crude two-level version is weaker than the one in the data, and a test on it has less power. This module correlates a continuous predictor with an outcome, then dichotomizes it and correlates again, showing the drop.

**A continuous predictor's exact values carry signal about the outcome, and dichotomizing into high/low merges subjects who differ, discarding that within-group signal — so the measured association is attenuated and the test loses power, all for presentational tidiness.**

## Concepts

The mechanism is the loss of within-group variation. Before the split, the predictor varies across its whole range and every bit of that variation can line up with variation in the outcome. After the split, all variation within the "low" half and within the "high" half is set to zero — each half is a single value — so only the coarse difference between the two halves remains. The association can only use the between-group part of the variation and must throw away the within-group part, which is why the correlation falls.

It helps to see this as a family resemblance with the topic's other attenuation results while noting the difference. Range restriction weakens a correlation by studying only a slice of the predictor's range; measurement error weakens it by adding noise to the predictor. Dichotomization weakens it by a third route — coarsening the predictor to two levels — and the three share an outcome (an attenuated estimate) but differ in cause. The distinguishing feature of dichotomization is agency: the first two are things that happen to your data, while dichotomization is something you do to it, which makes it the one that is simply avoidable.

The practical consequence is statistical power, which is the framing that makes the cost concrete. A weaker measured association needs a larger sample to reach significance, so dichotomizing a predictor is equivalent to discarding a substantial fraction of your subjects — the classic estimate is that a median split costs roughly the power of throwing away a third of the data. Framed that way, the trade is obviously bad: no one would delete a third of their hard-won observations to make a table read more nicely, but dichotomizing does exactly that in effect.

<svg role="img" aria-label="Three routes to an attenuated correlation: range restriction (study a slice), measurement error (add noise), and dichotomization (coarsen to two levels), the last marked as a deliberate choice" viewBox="0 0 440 120">
<text x="220" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">three routes to an attenuated association</text>
<rect x="15" y="30" width="130" height="60" fill="var(--panel)" stroke="var(--line)"/>
<text x="80" y="50" fill="var(--ink)" font-size="9" text-anchor="middle">range restriction</text>
<text x="80" y="66" fill="var(--muted)" font-size="8" text-anchor="middle">study a slice</text>
<text x="80" y="82" fill="var(--muted)" font-size="8" text-anchor="middle">(a limitation)</text>
<rect x="155" y="30" width="130" height="60" fill="var(--panel)" stroke="var(--line)"/>
<text x="220" y="50" fill="var(--ink)" font-size="9" text-anchor="middle">measurement error</text>
<text x="220" y="66" fill="var(--muted)" font-size="8" text-anchor="middle">add noise</text>
<text x="220" y="82" fill="var(--muted)" font-size="8" text-anchor="middle">(unavoidable)</text>
<rect x="295" y="30" width="130" height="60" fill="var(--panel)" stroke="var(--s2)"/>
<text x="360" y="50" fill="var(--ink)" font-size="9" text-anchor="middle">dichotomization</text>
<text x="360" y="66" fill="var(--muted)" font-size="8" text-anchor="middle">coarsen to 2 levels</text>
<text x="360" y="82" fill="var(--s2)" font-size="8" text-anchor="middle">(a choice — avoidable)</text>
</svg>
^ All three attenuate the association, but only dichotomization is a deliberate choice the analyst makes — which is what makes it the avoidable one.

**Dichotomization zeroes the within-group variation and leaves only the between-group part, so the association is attenuated; it shares that outcome with range restriction and measurement error but is distinguished by being a deliberate, avoidable choice, and its real cost is power — equivalent to discarding a large fraction of the data.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/dichotomize-inter-01. The fixture is a continuous predictor and an outcome that rise together perfectly.

```json filename=modules/ai-for-science-and-data/code/dichotomize-inter-01/dichotomize.json:3-4 COMPLETE
  "x": [1, 2, 3, 4, 5, 6],
  "y": [1, 2, 3, 4, 5, 6]
```

Dichotomizing collapses each value to 1 above the cut, else 0 — the median split.

```python filename=modules/ai-for-science-and-data/code/dichotomize-inter-01/dichotomize.py:41-43 COMPLETE
def dichotomize(vals, cut):
    """Collapse each value to 1 if above the cut, else 0 -- the median split."""
    return [1 if v > cut else 0 for v in vals]
```

The cut is the median of the predictor.

```python filename=modules/ai-for-science-and-data/code/dichotomize-inter-01/dichotomize.py:34-38 COMPLETE
def median(vals):
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    return (s[mid] + s[mid - 1]) / 2 if n % 2 == 0 else s[mid]
```

The correlation is the standard Pearson coefficient.

```python filename=modules/ai-for-science-and-data/code/dichotomize-inter-01/dichotomize.py:46-53 COMPLETE
def correlation(a, b):
    """Pearson correlation between two equal-length lists."""
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    return cov / (va ** 0.5 * vb ** 0.5)
```

First, see what the split does to the predictor. Run `--split`:

```text filename=dichotomize.py --split
SPLIT — the continuous predictor and its median dichotomization
----------------------------------------------------
  continuous x: [1, 2, 3, 4, 5, 6]
  median cut:   3.5
  dichotomized: [0, 0, 0, 1, 1, 1]  (1 if above the median)
----------------------------------------------------
  every value within a half collapses to the same level
```

The six distinct values become two. The 1, 2, and 3 all become 0; the 4, 5, and 6 all become 1. The information that 6 is much larger than 4, and that 1 is much smaller than 3, is gone — each half is now a single indistinguishable level.

<svg role="img" aria-label="A number line with six distinct x values 1 through 6 collapsing under a median split at 3.5 into two levels: 1,2,3 to low and 4,5,6 to high" viewBox="0 0 440 130">
<text x="220" y="20" fill="var(--muted)" font-size="9" text-anchor="middle">continuous: six distinct values</text>
<line x1="40" y1="40" x2="400" y2="40" stroke="var(--line)"/>
<circle cx="70" cy="40" r="4" fill="var(--ink)"/><text x="70" y="30" fill="var(--muted)" font-size="8" text-anchor="middle">1</text>
<circle cx="130" cy="40" r="4" fill="var(--ink)"/><text x="130" y="30" fill="var(--muted)" font-size="8" text-anchor="middle">2</text>
<circle cx="190" cy="40" r="4" fill="var(--ink)"/><text x="190" y="30" fill="var(--muted)" font-size="8" text-anchor="middle">3</text>
<circle cx="250" cy="40" r="4" fill="var(--ink)"/><text x="250" y="30" fill="var(--muted)" font-size="8" text-anchor="middle">4</text>
<circle cx="310" cy="40" r="4" fill="var(--ink)"/><text x="310" y="30" fill="var(--muted)" font-size="8" text-anchor="middle">5</text>
<circle cx="370" cy="40" r="4" fill="var(--ink)"/><text x="370" y="30" fill="var(--muted)" font-size="8" text-anchor="middle">6</text>
<line x1="220" y1="30" x2="220" y2="50" stroke="var(--s2)" stroke-dasharray="3 2"/>
<text x="220" y="62" fill="var(--s2)" font-size="8" text-anchor="middle">median 3.5</text>
<text x="220" y="88" fill="var(--muted)" font-size="9" text-anchor="middle">dichotomized: two levels</text>
<circle cx="130" cy="105" r="6" fill="var(--s1)"/><text x="130" y="123" fill="var(--s1)" font-size="8" text-anchor="middle">low (0)</text>
<circle cx="310" cy="105" r="6" fill="var(--s1)"/><text x="310" y="123" fill="var(--s1)" font-size="8" text-anchor="middle">high (1)</text>
</svg>
^ Six distinguishable values collapse to two levels; the differences within each half — the within-group variation — are erased.

Now the effect on the association. Predict: the continuous correlation is 1.0 (x equals y), and the dichotomized one is lower. Run `--corr`:

```text filename=dichotomize.py --corr
CORR — correlation with the outcome y
----------------------------------------------
  continuous x  vs y:  r = 1.000
  dichotomized  vs y:  r = 0.878
----------------------------------------------
  the split lowers the correlation -- attenuated, not gone
```

The prediction holds. A perfect correlation of 1.0 falls to 0.878 purely from binarizing the predictor — nothing about the data changed, only how much of the predictor the analysis was allowed to see. The relationship is still strong and obvious, but it is measurably weaker, and on noisier real data that gap is the difference between detecting an effect and missing it.

<svg role="img" aria-label="Two correlation bars: continuous x with y at 1.0, dichotomized with y at 0.88, the second shorter" viewBox="0 0 440 140">
<line x1="40" y1="115" x2="410" y2="115" stroke="var(--line)"/>
<rect x="90" y="30" width="80" height="85" fill="var(--s1)"/>
<text x="130" y="24" fill="var(--ink)" font-size="10" text-anchor="middle">continuous 1.00</text>
<rect x="280" y="40" width="80" height="75" fill="var(--s2)"/>
<text x="320" y="34" fill="var(--ink)" font-size="10" text-anchor="middle">dichotomized 0.88</text>
<text x="225" y="135" fill="var(--muted)" font-size="9" text-anchor="middle">same data — the split alone lowers the correlation with the outcome</text>
</svg>
^ The perfect correlation drops to 0.88 from the median split alone; the lost 0.12 is the within-group signal the split discarded.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that the dichotomized variable has two levels, that x's distinct values collapse, that the dichotomized correlation is weaker than the continuous, that the relationship survives (attenuated, not destroyed), and that the continuous variable keeps at least as much signal.

```python filename=modules/ai-for-science-and-data/code/dichotomize-inter-01/dichotomize.py:95-102 COMPLETE
    within_group_variation_lost = len(set(x)) > len(set(b))
    print("  x's distinct values (%d) collapse to %d levels = %s" % (len(set(x)), len(set(b)), within_group_variation_lost))

    dichotomized_weaker = r_dich < r_cont
    print("  the dichotomized correlation is weaker than the continuous = %s (%.3f < %.3f)" % (dichotomized_weaker, r_dich, r_cont))

    relationship_survives = r_dich > 0
    print("  the relationship survives the split (attenuated, not destroyed) = %s (%.3f)" % (relationship_survives, r_dich))

    continuous_keeps_full = r_cont >= r_dich
    print("  the continuous variable keeps at least as much signal = %s" % continuous_keeps_full)
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if dichotomizing ever stops attenuating or the continuous version ever loses to it:

```text filename=dichotomize.py --check
SELF-TEST — dichotomizing lowers the correlation with the outcome; the continuous variable keeps the full signal
--------------------------------------------------------------------------------------------------------------------
  the dichotomized variable has only two levels = True ([0, 1])
  x's distinct values (6) collapse to 2 levels = True
  the dichotomized correlation is weaker than the continuous = True (0.878 < 1.000)
  the relationship survives the split (attenuated, not destroyed) = True (0.878)
  the continuous variable keeps at least as much signal = True
```

**The self-test asserts the relationship survives the split as well as that it weakens — pinning the effect as attenuation, not destruction, so the fix is "keep it continuous", not "the variable is useless".**

## Definition of done

You can explain why continuous data carries more information than a binary split and why that information is often signal about the outcome.
You can state the mechanism — dichotomizing zeroes within-group variation and leaves only the between-group difference — and why that lowers the correlation.
You can place dichotomization among the topic's attenuation results and name what distinguishes it: it is a deliberate, avoidable choice, not a data limitation.
You can translate the attenuation into power terms — a weaker association needs a larger sample — and cite the "roughly a third of the data" rule of thumb.
You can state the fix (keep the variable continuous and model it as such) and rebut the usual justification (presentational tidiness).

## Boss fight

Consider dichotomizing at an extreme cut instead of the median — say, keep only the top 10% as "high" and the rest as "low". This is even worse for power in one sense (the "high" group is tiny, so the comparison is noisy) but it also illustrates a subtler point: where you put the cut changes the answer, and a cut chosen after looking at the data is a form of the multiple-comparisons and researcher-degrees-of-freedom problem. Trying several cutpoints and reporting the one with the smallest p-value manufactures false positives on top of the power loss. The lesson deepens: dichotomizing not only throws away signal, it opens a garden of forking paths in the choice of cutpoint that a continuous analysis never has.

Now consider the one case where dichotomizing is defensible: when the underlying relationship really is a step, not a gradient. If the outcome genuinely does not change with the predictor within each side of a threshold — a dose below which nothing happens and above which the full effect appears — then the two-level model matches reality and loses little. The lesson tightens: the sin is dichotomizing a genuinely continuous relationship to force it into two groups; when the mechanism truly is a threshold, a binary split can be the correct model, and the way to know is domain knowledge about the mechanism, not the convenience of a two-group table.

**Choosing the cutpoint after seeing the data adds a forking-paths false-positive risk on top of the power loss; and dichotomizing is defensible only when the true relationship is genuinely a threshold step, not a gradient — a judgment that must come from the mechanism, not from wanting a tidy two-group comparison.**

## External resources

Frank Harrell's "Regression Modeling Strategies" and his widely-cited notes on "dichotomania" argue against splitting continuous predictors and quantify the power loss.
The methods literature (e.g., MacCallum et al., "On the practice of dichotomization of quantitative variables") documents the attenuation and the cutpoint-selection hazards in detail.
The topic's own modules on range restriction and on measurement error in a predictor cover the two other routes to an attenuated association that this deliberate one is contrasted against.
