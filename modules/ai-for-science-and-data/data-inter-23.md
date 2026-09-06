---
id: data-inter-23
title: Correlate the changes, not the levels — or two unrelated trending series look strongly correlated
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 18 min
summary: Two time series that both trend will correlate whether or not they have anything to do with each other. A trend is a series that wanders and stays — a random walk, a growing population, a rising price — and any two trends line up by accident far more often than two flat noisy series do, so the correlation coefficient comes out large and means nothing. This is why "X and Y both rose over the decade, correlation 0.9" is not evidence of a link. The fix is to correlate the changes (first differences) instead of the levels: a random walk's differences are just its independent increments with the trend removed, so two independent walks' differences are uncorrelated. On a fixture of two independent random walks, the levels correlate at −0.886 (strong, entirely spurious) while the first differences correlate at −0.079 (essentially zero); averaged over 200 independent pairs, mean |level correlation| is 0.42 versus 0.12 for differences.
eli5: Two people wandering randomly around a park can end up drifting the same general direction for a while, and if you only look at where they are, it looks like they're walking together. But if you watch each step they take, the steps are unrelated — one zigs while the other zags. Judging "are they walking together?" by their positions fools you; judging by their steps tells the truth. Trending data is the same: compare the steps, not the positions.
---

## Why this module

A big correlation between two trending series feels like strong evidence, but trends line up by accident, so the number tells you the two series both drifted — not that either has anything to do with the other.

A trend is a series whose value carries its history: each point is near the last, so the series wanders somewhere and stays there rather than returning to a mean. Random walks, stock prices, populations, cumulative totals — all trend. Now correlate two of them. If both happened to drift upward over your window, their levels rise together and the correlation is strongly positive; if one drifted up and the other down, strongly negative. It comes out large either way, and it is meaningless, because the two series never interacted — they just each went somewhere and the going-somewhere lined up. Two flat, mean-reverting noise series almost never correlate by accident; two trends almost always show *some* apparent correlation, because there are only so many directions to drift and any two drifts partly align. This is spurious correlation from trend, and it is why almost everything that grows correlates with almost everything else that grows.

**Two trending series correlate by accident far more often than two stationary ones, so a large correlation between levels tells you both series trended — not that they are related.**

The fix is to correlate the *changes* instead of the levels. A random walk's step-to-step differences are exactly its independent increments, with the accumulated drift subtracted away, so the differences of two independent walks are uncorrelated — they correctly report no relationship. Differencing strips out the shared drift that faked the correlation and leaves the actual, unrelated noise; a relationship that survives differencing may be real, while one that lives only in the levels is trend lining up with trend. This module correlates two independent walks both ways and shows the spurious level correlation vanish under differencing.

## Concepts

A **trending (non-stationary) series** wanders and stays — its mean is not constant. A random walk, the running sum of independent steps, is the canonical example.

**Correlating levels** measures whether two series' values track. For trending series this is dominated by whether their drifts aligned, so it reports large correlations that carry no information about a relationship.

**First differences** are the step-to-step changes. For a random walk they are the independent increments with the trend removed, turning a non-stationary series into a stationary one.

```python filename=modules/ai-for-science-and-data/code/data-inter-23/spurious.py:52-54 COMPLETE
def diffs(series):
    """First differences: the step-to-step changes, with the trend removed."""
    return [series[i + 1] - series[i] for i in range(len(series) - 1)]
```

**Correlating differences** measures whether the two series' *changes* move together. Independent walks have independent increments, so their difference correlation is near zero — the truth.

**Differencing is the discriminator.** A correlation that survives it is a candidate for real; one that disappears was trend aligning with trend, not a relationship.

**A correlation between levels of trending series is not evidence of a link, because trends align by accident; correlate the first differences, which remove the trend, to see whether the series are actually related.**

<svg role="img" aria-label="Two walks drift in opposite directions so their levels track negatively, but their step-to-step changes are unrelated" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">two independent walks: levels drift apart, steps unrelated</text>
  <line x1="20" y1="60" x2="285" y2="60" stroke="var(--grid)" stroke-width="1" stroke-dasharray="2 3"/>
  <polyline points="25,58 55,50 85,42 115,36 145,30 175,26 205,22 260,18" fill="none" stroke="var(--s1)" stroke-width="1.5"/><text x="262" y="20" fill="var(--s1)" font-size="7">A ↑</text>
  <polyline points="25,62 55,70 85,76 115,84 145,88 175,92 205,96 260,100" fill="none" stroke="var(--s2)" stroke-width="1.5"/><text x="262" y="102" fill="var(--s2)" font-size="7">B ↓</text>
  <text x="30" y="76" fill="var(--muted)" font-size="7">A drifts up, B drifts down → levels correlate strongly (negatively)</text>
  <text x="30" y="90" fill="var(--muted)" font-size="7">but each wiggle (step) is independent → differences correlate ~0</text>
</svg>
^ One walk happens to drift up and the other down, so their levels track in opposite directions and correlate strongly — yet the individual steps that make up each walk are unrelated, which differencing exposes.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/data-inter-23/spurious.py

The fixture is two independent random walks (different seeds) plus a trial count for averaging.

```json filename=modules/ai-for-science-and-data/code/data-inter-23/spurious.json:1-6 COMPLETE
{
  "_meta": "Two INDEPENDENT random walks -- each is a running sum of random +/-1 steps drawn from its own seed, so neither has anything to do with the other. A random walk trends: it wanders up or down and stays there, because each value is the previous one plus a step. When you correlate the LEVELS (the walk values) of two independent walks, you get a large correlation anyway, because both are trending and two trends line up by accident far more often than two flat noise series do -- a spurious correlation. The fix is to correlate the CHANGES (first differences, step to step) instead: the differences of a random walk are just its independent steps, so the differences of two independent walks are uncorrelated, correctly showing no relationship. seed_a and seed_b make one illustrative pair; trials averages |correlation| over many independent pairs to show the effect is systematic, not a fluke.",
  "seed_a": 131,
  "seed_b": 1131,
  "n": 40,
  "trials": 200
}
```

A walk is a running sum of independent steps; its differences recover those steps.

```python filename=modules/ai-for-science-and-data/code/data-inter-23/spurious.py:43-49 COMPLETE
def walk(seed, n):
    """A random walk: the running sum of n random +/-1 steps from the given seed."""
    r = random.Random(seed)
    w = [0.0]
    for _ in range(n):
        w.append(w[-1] + r.choice([-1, 1]))
    return w
```

Run `--pair` to correlate one pair both ways.

```text filename=--pair
PAIR — two independent random walks (seeds 131, 1131)
------------------------------------------------------------
  correlation of LEVELS (the walk values):      -0.886   (large -- spurious)
  correlation of CHANGES (first differences):   -0.079   (near zero -- the truth)
------------------------------------------------------------
  the walks share nothing but a trend; only the levels correlate.
```

These two walks were generated from unrelated seeds — there is no mechanism connecting them. Yet their levels correlate at −0.886, a correlation strong enough that, seen in real data, an analyst would confidently report a relationship: as one goes up the other goes down, almost in lockstep. It is an illusion. One walk happened to drift down while the other drifted up over these 40 steps, and correlating their positions measured that accidental opposition. Correlate their step-to-step changes and the number collapses to −0.079: the increments are independent, as they truly are. The level correlation was an artifact of two trends pointing opposite ways; the difference correlation is the truth that they are unrelated.

<svg role="img" aria-label="The level correlation of two independent walks is minus 0.886, the difference correlation minus 0.079" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">|correlation| of two INDEPENDENT walks (truth: 0)</text>
  <line x1="60" y1="20" x2="60" y2="78" stroke="var(--grid)" stroke-width="1"/>
  <line x1="60" y1="78" x2="285" y2="78" stroke="var(--grid)" stroke-width="1"/>
  <rect x="60" y="26" width="199" height="16" fill="var(--s2)"/><text x="64" y="38" fill="var(--panel)" font-size="8">levels: 0.886 (spurious)</text>
  <rect x="60" y="50" width="18" height="16" fill="var(--s1)"/><text x="84" y="62" fill="var(--muted)" font-size="8">differences: 0.079 (the truth)</text>
  <text x="60" y="94" fill="var(--muted)" font-size="8">both series are unrelated; only the level correlation pretends otherwise</text>
</svg>
^ The level bar runs almost the full width though the walks are unrelated; the difference bar is a sliver near zero, the honest measure of no relationship.

## Build

One pair could be luck. Run `--average` over many independent pairs.

```text filename=--average
AVERAGE — mean |correlation| over 200 independent walk pairs
------------------------------------------------------------
  levels:        0.424   (3.5x larger -- systematic spurious correlation)
  differences:   0.123   (near zero -- no relationship, correctly)
------------------------------------------------------------
  the spurious level correlation is not a fluke; differencing removes it every time.
```

Across 200 independent pairs of walks — no pair sharing anything — the mean absolute correlation of levels is 0.424, while the mean absolute correlation of differences is 0.123. The level correlation is 3.5 times larger, systematically, purely from trend. That 0.42 is the expected size of a completely spurious correlation between two unrelated trending series: not a rare unlucky draw, the typical case. This is the quantitative statement of "everything that trends correlates with everything else that trends," and it is why regressing one trending series on another (a spurious regression) routinely produces impressive-looking coefficients and R-squareds from nothing. Differencing brings the average down to 0.12, close to the zero the truth demands.

<svg role="img" aria-label="Averaged over 200 pairs, mean absolute level correlation is 0.42 and mean absolute difference correlation is 0.12" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">mean |correlation| over 200 unrelated pairs</text>
  <line x1="70" y1="20" x2="70" y2="78" stroke="var(--grid)" stroke-width="1"/>
  <line x1="70" y1="78" x2="285" y2="78" stroke="var(--grid)" stroke-width="1"/>
  <rect x="70" y="26" width="170" height="16" fill="var(--s2)"/><text x="74" y="38" fill="var(--panel)" font-size="8">levels: 0.42</text>
  <rect x="70" y="50" width="49" height="16" fill="var(--s1)"/><text x="123" y="62" fill="var(--muted)" font-size="8">differences: 0.12</text>
  <text x="70" y="94" fill="var(--muted)" font-size="8">0.42 is the typical spurious correlation from trend alone — not a fluke</text>
</svg>
^ The level bar sits at 0.42 for series that are unrelated by construction, three-and-a-half times the differenced 0.12 — the spurious correlation is the systematic rule, not an outlier.

## Definition of done

The self-test pins it: the pair's level correlation is large, its difference correlation near zero, the average level correlation is inflated, the average difference correlation is small, and differencing more than halves it.

```python filename=modules/ai-for-science-and-data/code/data-inter-23/spurious.py:108-124 COMPLETE
    levels_spurious = abs(cl) > 0.5
    print("  the pair's LEVEL correlation is large = %s (%+.3f)" % (levels_spurious, cl))

    diffs_near_zero = abs(cd) < 0.2
    print("  the pair's DIFFERENCE correlation is near zero = %s (%+.3f)" % (diffs_near_zero, cd))

    lv = avg_abs_correlation(n, trials, on_diffs=False)
    dv = avg_abs_correlation(n, trials, on_diffs=True)

    avg_levels_inflated = lv > 0.3
    print("  the average |level correlation| is inflated = %s (%.3f)" % (avg_levels_inflated, lv))

    avg_diffs_low = dv < 0.2
    print("  the average |difference correlation| is small = %s (%.3f)" % (avg_diffs_low, dv))

    differencing_removes_it = lv > 2 * dv
    print("  differencing more than halves the spurious correlation = %s (%.3f > 2*%.3f)" % (differencing_removes_it, lv, dv))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — independent walks correlate spuriously in levels; differencing reveals no relationship
--------------------------------------------------------------------------------------------------------
  the pair's LEVEL correlation is large = True (-0.886)
  the pair's DIFFERENCE correlation is near zero = True (-0.079)
  the average |level correlation| is inflated = True (0.424)
  the average |difference correlation| is small = True (0.123)
  differencing more than halves the spurious correlation = True (0.424 > 2*0.123)
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  levels_spurious=True  diffs_near_zero=True  avg_levels_inflated=True  avg_diffs_low=True  differencing_removes_it=True
```

**Done means the spurious correlation is proven and cured: two independent walks correlate at −0.886 in levels but −0.079 in differences, and across 200 unrelated pairs the mean |level correlation| is 0.42 versus 0.12 differenced — so the level correlation measured trend, not a relationship.**

## Boss fight

Differencing killed the spurious correlation. Predict when differencing is the wrong fix, and what a real relationship between two trending series looks like. It is tempting to difference everything and trust whatever survives.

Differencing is the right move against spurious *trend* correlation, but it can throw away a real long-run relationship. Two series can be individually trending yet genuinely tied together so that they move as a pair — cointegrated, in the econometric term: their levels wander but a particular combination of them stays stationary, like a dog and its owner both wandering while the leash keeps them close. If you blindly difference, you study the steps and may miss that the levels are bound; the correct tool then is an error-correction model or a cointegration test, which models the long-run tie and the short-run changes together. So the rule is not "always difference"; it is "a level correlation between trending series is not evidence — establish stationarity, difference or test for cointegration, and only then interpret."

The broader lesson is that correlation assumes stationarity, and trending data violates it silently. The classic examples are a joke precisely because they are real correlations by the coefficient: US cheese consumption and deaths by bedsheet entanglement, divorce rates and margarine consumption — both members of each pair trended over the years, so they correlate at 0.9-plus with no possible mechanism. Before reading any correlation or regression on time series, ask whether the series are stationary; if they trend, the coefficient is measuring drift alignment until you have removed the trend or modeled it. A number that vanishes when you difference was never telling you about a relationship — it was telling you both things were going somewhere.

```python filename=modules/ai-for-science-and-data/code/data-inter-23/spurious.py:65-73 COMPLETE
def avg_abs_correlation(n, trials, on_diffs):
    """Mean absolute correlation over `trials` independent walk pairs; on_diffs uses first differences."""
    total = 0.0
    for i in range(trials):
        a, b = walk(2 * i, n), walk(2 * i + 1, n)
        if on_diffs:
            a, b = diffs(a), diffs(b)
        total += abs(correlation(a, b))
    return total / trials
```

**A large correlation between the levels of two trending series is not evidence of a relationship — trends align by accident, giving a typical spurious correlation of ~0.4 between unrelated walks — so difference the series (or test for cointegration when a real long-run tie may exist) and interpret correlation only after the trend is removed, because a coefficient that vanishes under differencing measured drift, not a link.**

## External resources

Yule's 1926 paper "Why Do We Sometimes Get Nonsense Correlations Between Time-Series?" and Granger and Newbold's work on spurious regression — the origin and the modern statement of the problem, with the differencing and cointegration remedies.

The Engle-Granger cointegration framework and error-correction models in any time-series text — the tools for the case this module's fix would over-correct, where two trending series are genuinely bound in the long run.

The companion "a shared denominator manufactures correlation" and "a fit is only valid inside its data's range" modules — both are correlations and fits that look real but come from structure rather than relationship, the same skepticism applied to ratios and to extrapolation.
