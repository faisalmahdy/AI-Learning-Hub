---
id: predint-inter-01
title: Use a prediction interval for a new point, not the confidence band for the line — the confidence band can be narrower than the noise and misses most observations
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: A fitted regression line has two kinds of uncertainty around it, drawn as two bands, and confusing them makes a process look far more precise than it is. The confidence interval asks where the true average response is at a given x; its width comes only from how well the data pins down the line, so it shrinks toward zero as the sample grows. The prediction interval asks where a single new observation will land, which is the line's uncertainty plus the irreducible scatter of individual points around it — so it adds the residual variance and never shrinks below about one residual standard deviation, however much data you collect. On the fixture ten points scatter around a line fitted as y = 1.948x + 1.287 with a residual standard deviation of 1.158. The confidence half-width at the center is 0.733 — only 0.63 times the noise, narrower than the scatter of the points themselves — and it contains just 50% of the observations, far below the nominal 95%. The prediction half-width is 2.430, about 2.1 times the noise, and contains 100% of them. Quoting the confidence band as "where the next measurement will fall" is the error: it describes the precision of the average, not the range of individuals, and at any realistic sample size it is far too narrow to hold a new point. The rule: report a confidence interval for a mean and a prediction interval for a new observation, and never read the confidence band as the spread of the data.
eli5: Imagine you measured the average height of ten-year-olds and got it very precisely — you're quite sure the average is close to 140 cm, give or take a hair, because you measured thousands of kids. But that tight range is about the average, not about any one kid: the next ten-year-old you meet could easily be 125 or 155 cm, because kids vary a lot around the average no matter how well you know it. If you told a tailor "make this suit to fit within a hair of 140 cm because that's how sure I am," most kids wouldn't fit. There are two different questions — how well do I know the average, and how spread out are the individuals — and the answer to the first keeps getting tighter with more data while the answer to the second stays wide.
---

## Why this module

You fit a line to data, and your software hands you a shaded band around it. It is tempting to read that band as "the data lives in here" — a summary of where points fall. If the band is the confidence interval, that reading is wrong, and wrong in a direction that flatters you: the confidence band is usually much tighter than the actual scatter of the data, so treating it as the range of observations claims a precision the process does not have.

The reason is that two very different questions get the same picture. One asks how well the data locates the average line; the other asks where a single new point will fall. The first answer shrinks as you collect more data — the average becomes ever more certain. The second cannot shrink past the noise, because individual points scatter by that much no matter how well you know the line.

This module fits a line to ten scattered points and draws both bands. The confidence band comes out narrower than the noise itself and contains only half the points; the prediction band is more than three times wider and contains all of them. Then it shows why one shrinks with sample size and the other floors at the noise, and which to quote for which claim.

**The confidence band answers "where is the average," not "where is a point," and reading it as the second understates the spread by exactly the scatter the average calculation was designed to average away.**

## Concepts

Write the two intervals side by side and the difference is one term. At a point x, both are the fitted value plus or minus a multiple of the residual standard deviation times a square root. The confidence interval for the mean uses the square root of one-over-n plus a term for distance from the center. The prediction interval uses that same thing plus one — a leading 1 under the root.

That leading 1 is the entire story. It is the variance of a single new point's scatter around the true line, the irreducible noise that every individual observation carries. The confidence interval leaves it out because it is not asking about an individual; it is asking about the average, and averaging cancels that scatter. The prediction interval puts it in because a new observation is one draw, not an average, so it wears the full noise.

The consequence for sample size is the practical punchline. The confidence interval's width is all in the one-over-n term, so as n grows it goes to zero — infinite data locates the mean exactly. The prediction interval's width is dominated by that leading 1, which does not depend on n at all, so it converges to the residual standard deviation times the multiplier and stops. You can make the confidence band as thin as you like with enough data; you can never make the prediction band thinner than the noise.

So at a realistic sample size the confidence band can be — and here is — narrower than the cloud of points it is drawn through. A band narrower than the noise cannot possibly contain most of the individual points, because the points scatter by more than the band is wide.

<svg role="img" aria-label="A fitted line through scattered points with two bands. A narrow confidence band hugs the line, with several points falling outside it. A wide prediction band surrounds all the points. The scatter of the points is clearly wider than the confidence band" viewBox="0 0 640 260">
<line x1="60" y1="220" x2="600" y2="60" stroke="var(--ink)" stroke-width="2"/>
<path d="M 60 232 L 600 72 L 600 48 L 60 208 Z" fill="var(--s2)" opacity="0.18"/>
<line x1="60" y1="208" x2="600" y2="48" stroke="var(--s2)" stroke-width="1" stroke-dasharray="4 3"/>
<line x1="60" y1="232" x2="600" y2="72" stroke="var(--s2)" stroke-width="1" stroke-dasharray="4 3"/>
<path d="M 60 255 L 600 95 L 600 25 L 60 185 Z" fill="var(--s1)" opacity="0.12"/>
<line x1="60" y1="185" x2="600" y2="25" stroke="var(--s1)" stroke-width="1" stroke-dasharray="6 3"/>
<line x1="60" y1="255" x2="600" y2="95" stroke="var(--s1)" stroke-width="1" stroke-dasharray="6 3"/>
<circle cx="120" cy="195" r="3.5" fill="var(--ink)"/>
<circle cx="180" cy="210" r="3.5" fill="var(--ink)"/>
<circle cx="240" cy="150" r="3.5" fill="var(--ink)"/>
<circle cx="300" cy="165" r="3.5" fill="var(--ink)"/>
<circle cx="360" cy="100" r="3.5" fill="var(--ink)"/>
<circle cx="420" cy="130" r="3.5" fill="var(--ink)"/>
<circle cx="480" cy="88" r="3.5" fill="var(--ink)"/>
<circle cx="540" cy="80" r="3.5" fill="var(--ink)"/>
<text x="470" y="200" fill="var(--s2)" font-size="11">confidence band (narrow)</text>
<text x="120" y="55" fill="var(--s1)" font-size="11">prediction band (wide)</text>
</svg>
^ The confidence band hugs the line and lets points fall outside it; only the prediction band, wider than the scatter, contains them.

**The prediction interval is the confidence interval plus one residual standard deviation of scatter, and that one added term is both why it is wide and why it, not the confidence band, is where a new point falls.**

## Worked example

The fixture is ten points scattered around a line, with a multiplier for an approximate 95% interval.

```json filename=modules/ai-for-science-and-data/code/predint-inter-01/predint.json:3-5 COMPLETE
  "x": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
  "y": [4.2, 3.6, 7.8, 8.4, 12.5, 11.9, 15.4, 15.7, 20.0, 20.5],
  "k": 2.0
```

An ordinary least-squares fit gives the line and, crucially, the residual standard deviation — the scatter of points around it.

```python filename=modules/ai-for-science-and-data/code/predint-inter-01/predint.py:32-42 COMPLETE
def fit(x, y):
    """Ordinary least squares: return slope, intercept, residual sd, x-mean, and Sxx."""
    n = len(x)
    xbar, ybar = sum(x) / n, sum(y) / n
    sxx = sum((xi - xbar) ** 2 for xi in x)
    sxy = sum((xi - xbar) * (yi - ybar) for xi, yi in zip(x, y))
    slope = sxy / sxx
    intercept = ybar - slope * xbar
    sse = sum((yi - (intercept + slope * xi)) ** 2 for xi, yi in zip(x, y))
    resid_sd = (sse / (n - 2)) ** 0.5
    return slope, intercept, resid_sd, xbar, sxx
```

The confidence half-width uses one-over-n plus the distance term — the uncertainty in the line alone.

```python filename=modules/ai-for-science-and-data/code/predint-inter-01/predint.py:45-47 COMPLETE
def confidence_halfwidth(x0, n, resid_sd, xbar, sxx, k):
    """Half-width of the interval for the MEAN response at x0 -- uncertainty in the line only."""
    return k * resid_sd * (1.0 / n + (x0 - xbar) ** 2 / sxx) ** 0.5
```

The prediction half-width is identical but for the leading 1 — the residual scatter of a single new point.

```python filename=modules/ai-for-science-and-data/code/predint-inter-01/predint.py:50-52 COMPLETE
def prediction_halfwidth(x0, n, resid_sd, xbar, sxx, k):
    """Half-width for a NEW observation at x0 -- the line's uncertainty PLUS the residual scatter (the extra 1)."""
    return k * resid_sd * (1.0 + 1.0 / n + (x0 - xbar) ** 2 / sxx) ** 0.5
```

The confidence band, at the center of the data, is narrower than the noise and holds only half the points.

```text filename=predint.py --confidence
CONFIDENCE — the band for the true average line
------------------------------------------------------------
  residual sd (scatter of points) = 1.158
  confidence half-width at center = 0.733  (0.63 x the noise)
  points inside the confidence band = 50% (5 of 10)
------------------------------------------------------------
  the band is narrower than the noise, so it covers far fewer than the nominal 95% of points
```

The prediction band, wider by the added scatter, holds all of them.

```text filename=predint.py --prediction
PREDICTION — the band for a new observation
------------------------------------------------------------
  residual sd (scatter of points) = 1.158
  prediction half-width at center = 2.430  (2.10 x the noise)
  points inside the prediction band = 100% (10 of 10)
------------------------------------------------------------
  the band adds the residual scatter, so it contains almost every point
```

The confidence half-width 0.733 is 0.63 of the residual standard deviation 1.158; the prediction half-width 2.430 is 2.10 of it. A band 0.63 as wide as the noise cannot cover the points, and it does not — 5 of 10 fall outside. A band 2.10 as wide covers all ten. The figure shows both bands drawn through the actual points.

<svg role="img" aria-label="A scatter of ten points with the fitted line. The confidence band, half-width 0.733, is narrow and five points fall outside it. The prediction band, half-width 2.430, is wide and all ten points fall inside it" viewBox="0 0 640 270">
<line x1="60" y1="225" x2="600" y2="65" stroke="var(--ink)" stroke-width="2"/>
<path d="M 60 233 L 600 73 L 600 57 L 60 217 Z" fill="var(--s2)" opacity="0.2"/>
<path d="M 60 262 L 600 102 L 600 28 L 60 188 Z" fill="var(--s1)" opacity="0.12"/>
<circle cx="105" cy="205" r="3.5" fill="var(--ink)"/>
<circle cx="160" cy="235" r="3.5" fill="var(--s2)"/>
<circle cx="215" cy="170" r="3.5" fill="var(--s2)"/>
<circle cx="270" cy="185" r="3.5" fill="var(--ink)"/>
<circle cx="325" cy="120" r="3.5" fill="var(--s2)"/>
<circle cx="380" cy="150" r="3.5" fill="var(--s2)"/>
<circle cx="435" cy="105" r="3.5" fill="var(--ink)"/>
<circle cx="490" cy="118" r="3.5" fill="var(--ink)"/>
<circle cx="545" cy="72" r="3.5" fill="var(--ink)"/>
<circle cx="580" cy="70" r="3.5" fill="var(--s2)"/>
<text x="330" y="250" fill="var(--s2)" font-size="10">confidence ±0.733: 5 of 10 inside</text>
<text x="120" y="45" fill="var(--s1)" font-size="10">prediction ±2.430: 10 of 10 inside</text>
</svg>
^ The points marked in the accent color fall outside the confidence band; every point is inside the prediction band.

**The confidence band's 50% coverage is the diagnosis: an interval that is supposed to be a 95% statement about something is holding half the data, because it is a 95% statement about the mean, not about the points.**

## Build

The self-test pins the two facts that separate the intervals: the prediction band is much wider, and — the sharp form — the confidence half-width is below the noise while the prediction half-width is above it.

```python filename=modules/ai-for-science-and-data/code/predint-inter-01/predint.py:108-118 COMPLETE
    prediction_wider = pi > 2 * ci
    print("  the prediction band is much wider than the confidence band = %s (%.3f vs %.3f)" % (prediction_wider, pi, ci))

    confidence_below_noise = ci < sd
    print("  the confidence half-width is narrower than the noise = %s (%.3f < %.3f)" % (confidence_below_noise, ci, sd))

    prediction_above_noise = pi > sd
    print("  the prediction half-width exceeds the noise = %s (%.3f > %.3f)" % (prediction_above_noise, pi, sd))

    confidence_undercovers = ci_frac < 0.7
    print("  the confidence band covers far fewer than the nominal 95%% of points = %s (%.0f%%)" % (confidence_undercovers, 100 * ci_frac))
```

Running the check confirms all five flags.

```text filename=predint.py --check
SELF-TEST — the confidence band is narrower than the noise and covers far fewer than 95% of points, while the prediction band contains almost all of them
----------------------------------------------------------------------------------------------------------------
  the prediction band is much wider than the confidence band = True (2.430 vs 0.733)
  the confidence half-width is narrower than the noise = True (0.733 < 1.158)
  the prediction half-width exceeds the noise = True (2.430 > 1.158)
  the confidence band covers far fewer than the nominal 95% of points = True (50%)
  the prediction band contains almost all the points = True (100%)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  prediction_wider=True  confidence_below_noise=True  prediction_above_noise=True  confidence_undercovers=True  prediction_contains_most=True
```

**Comparing each half-width to the noise is the cleanest test: the confidence band being below the residual sd is a mathematical guarantee that it cannot cover the individual points, whatever the nominal percentage on it says.**

## Definition of done

You are done when you quote a confidence interval for a statement about a mean or a fitted value, and a prediction interval for a statement about an individual new observation, and never let a confidence band stand in for the spread of the data.

The two are one keystroke apart in most statistics software — a `interval="confidence"` versus `interval="prediction"` flag — so the discipline is not computation but knowing which question you are answering. "What is the average yield at this dose?" or "how precisely have I located the line?" is a confidence interval. "What yield will the next batch give?" or "will a new part pass spec?" is a prediction interval. The tell that you want prediction, not confidence, is that your claim is about a single realized outcome, and single outcomes carry the full residual noise. And watch the sample-size behavior: as data accumulates the confidence band collapses toward the line while the prediction band settles at the noise floor, so a very tight confidence band on a large dataset is not evidence that new points will fall in a tight range.

<svg role="img" aria-label="Two curves against increasing sample size n. The confidence half-width falls from 0.73 at n=10 toward zero as n grows. The prediction half-width falls slightly from 2.43 and levels off at about 2.32, the noise floor, never approaching zero" viewBox="0 0 640 250">
<line x1="60" y1="210" x2="600" y2="210" stroke="var(--line)" stroke-width="1"/>
<line x1="60" y1="40" x2="60" y2="210" stroke="var(--line)" stroke-width="1"/>
<text x="330" y="240" fill="var(--muted)" font-size="11" text-anchor="middle">sample size n increases &#8594;</text>
<line x1="60" y1="70" x2="600" y2="70" stroke="var(--grid)" stroke-width="1" stroke-dasharray="3 3"/>
<text x="52" y="74" fill="var(--muted)" font-size="9" text-anchor="end">noise floor</text>
<polyline points="110,64 250,66 420,68 560,69" fill="none" stroke="var(--s1)" stroke-width="2"/>
<text x="430" y="58" fill="var(--s1)" font-size="10">prediction: floors at the noise (2.43 → 2.32)</text>
<polyline points="110,150 250,185 420,200 560,206" fill="none" stroke="var(--s2)" stroke-width="2"/>
<text x="300" y="200" fill="var(--s2)" font-size="10">confidence: shrinks toward 0 (0.73 → 0)</text>
<circle cx="110" cy="150" r="3.5" fill="var(--s2)"/>
<circle cx="110" cy="64" r="3.5" fill="var(--s1)"/>
<text x="110" y="224" fill="var(--muted)" font-size="9" text-anchor="middle">n=10</text>
</svg>
^ More data drives the confidence band to zero but leaves the prediction band at the noise floor — so no sample size makes the confidence band a valid range for a new point.

**A confidence interval that keeps shrinking with data is doing its job; the mistake is expecting the prediction interval to shrink with it, because the scatter of individuals is a property of the world, not of your sample size.**

## Boss fight

Your turn: move away from the center and watch both bands widen, but not equally. Evaluate the half-widths at x = 10, the edge of the data, instead of at the center. The distance term (x − x̄)² / Sxx grows, so both bands get wider there — but it adds the same amount under both square roots, so it matters far more to the already-narrow confidence band than to the prediction band that is dominated by its leading 1. The confidence band fans out noticeably toward the edges (which is the classic bow-tie shape), while the prediction band barely changes. This is why a confidence band looks dramatic near the edges and a prediction band looks nearly flat: the same geometry, scaled by how much room the added term has to matter.

Then push n to imagine the large-sample limit. Hold the residual sd fixed and let n grow: the confidence half-width, all one-over-n, heads to zero, so with enough data the confidence band becomes a hairline on the fitted value. The prediction half-width, k times sd times the square root of one-plus-almost-zero, settles at k times the residual sd — here about 2.32 — and stops. A reviewer who reports "our model predicts the outcome to within 0.07 units" from a huge dataset has quoted the collapsing confidence band as if it were the prediction band, and their next real observation will miss that range most of the time. The size of the dataset bought them a precise line; it bought them nothing about the noise around it, and only the prediction interval keeps that distinction honest.

**The confidence band shrinking to a hairline on a large dataset is the trap's most convincing form, because the precision is real — about the average — and the error is only in claiming it for the next individual, which carries a noise no amount of data removes.**

## External resources

Any regression textbook's treatment of "confidence versus prediction intervals" derives the two formulas and the leading 1 that distinguishes them — the algebra behind this module's two half-width functions.

The documentation for statistical software's regression prediction (for example R's `predict(..., interval="confidence")` versus `"prediction"`, or the equivalent in statsmodels) states the distinction operationally and is the practical place the choice is made.

Writing on the "bow-tie" shape of regression bands and on why prediction intervals do not vanish with sample size is a good companion for the boss-fight intuitions about the edges and the large-sample limit.
