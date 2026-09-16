---
id: data-inter-12
title: Range restriction attenuates correlation — a real relationship looks weak when you study only a slice
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 21 min
summary: Correlation depends on the range of x you measure over. A genuine relationship that is strong across the full range measures far weaker inside a narrow slice, because restricting the range shrinks x's variation toward the noise. On ten points, the full-range correlation is 0.92; restricted to the middle four, it drops to 0.31 — same points, same relationship, narrower window.
eli5: If you look at how height relates to age across all kids from 2 to 18, it's obviously strong. But if you only look at 10-year-olds, they're all about the same height, so age barely seems to matter — you cut out the range where the pattern shows. Narrowing what you look at can hide a real connection.
---

## Why this module

A correlation you compute on a pre-selected subgroup systematically understates the real relationship, and you will constantly be handed pre-selected subgroups.

Correlation measures how much y moves with x relative to how much each of them varies. That "relative to how much x varies" is the catch: shrink the range of x and you shrink the variation the correlation has to work with, so even a strong, real relationship measures weaker. Study the relationship across the full range and it is obvious; study it inside a narrow slice — only the top performers, only admitted students, only high earners, only the cases that passed some earlier filter — and the same relationship looks faint or absent, because inside the slice x barely moves and the noise dominates what little movement there is.

This is not a subtle statistical artifact; it is one of the main reasons real correlations get underestimated in practice, and it hides behind reasonable-sounding study designs. "SAT scores barely predict college GPA" is the textbook example: measured among admitted students, whose SAT range is narrow by construction because low scorers were not admitted, the correlation is heavily attenuated compared to the full applicant pool. The study was not wrong about its subgroup; it just measured a range-restricted correlation and reported it as if it were the general one. Any time the group you measure was selected on x, or on something correlated with x, you are looking through a keyhole that hides most of the variation.

The relationship itself does not change when you restrict the range — the underlying slope, the true association, is the same. Only the measured correlation drops, because correlation is a standardized quantity that divides by the spread of x, and you shrank that spread. So a weak correlation on a restricted sample is not evidence of a weak relationship; it may be a strong relationship viewed through too narrow a window.

We will compute the correlation on ten points with a clear linear relationship, then on just the middle four. The full-range correlation is 0.92 — unmistakably strong. The restricted correlation is 0.31 — weak enough to dismiss. Same points, same relationship; only the range examined changed.

**Correlation is standardized by the spread of x, so restricting x's range shrinks the measured correlation even though the underlying relationship is unchanged — a real association looks weak when studied on a narrow slice.**

## Concepts

The mechanism is in the definition. The correlation coefficient is the covariance of x and y divided by the product of their standard deviations — it standardizes the joint variation by how much each variable varies on its own. The relationship contributes a signal (covariance) and the noise contributes scatter; the correlation is roughly signal over total spread. When you restrict the range of x, you cut down the covariance and the spread of x together, but not proportionally: the noise in y stays the same size while the range of x shrinks, so the noise becomes a larger share of what is left, and the ratio — the correlation — falls. Inside a narrow enough slice, the noise is all there is, and the correlation approaches zero.

The clearest way to see it: a strong correlation looks like a tight upward line across a wide range. Zoom into a small horizontal window of that line, and within the window the points look like a formless cloud, because the small real rise across the narrow window is swamped by the vertical scatter that was always there. The line did not stop existing; you just cropped out the part of the range where its rise was large compared to the scatter. Correlation reads the cropped cloud as "no relationship" even though the full picture is nearly a straight line.

<svg role="img" aria-label="Measured correlation rises as the range of x kept widens: near zero for a tight window, climbing toward 0.92 at the full range" viewBox="0 0 460 170" width="460" height="170">
  <rect x="0" y="0" width="460" height="170" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">measured r vs how much of x's range you keep</text>
  <line x1="50" y1="140" x2="440" y2="140" stroke="var(--line)"/>
  <line x1="50" y1="40" x2="50" y2="140" stroke="var(--line)"/>
  <text x="24" y="45" font-family="var(--mono)" font-size="9" fill="var(--muted)">1.0</text>
  <text x="60" y="156" font-family="var(--mono)" font-size="8" fill="var(--muted)">narrow slice</text><text x="360" y="156" font-family="var(--mono)" font-size="8" fill="var(--muted)">full range</text>
  <polyline points="80,128 180,118 280,86 410,52" fill="none" stroke="var(--acc-ink)" stroke-width="2"/>
  <circle cx="80" cy="128" r="4" fill="var(--s2)"/><text x="86" y="126" font-family="var(--mono)" font-size="8" fill="var(--s2)">0.1 (x 6-7)</text>
  <circle cx="180" cy="118" r="4" fill="var(--s2)"/><text x="150" y="112" font-family="var(--mono)" font-size="8" fill="var(--s2)">0.31 (x 5-8)</text>
  <circle cx="280" cy="86" r="4" fill="var(--acc-line)"/><text x="250" y="80" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">~0.7 (x 3-9)</text>
  <circle cx="410" cy="52" r="5" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="330" y="46" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">0.92 (full)</text>
</svg>
^ The measured correlation is a direct function of the range kept — widen the window and it climbs back toward the true value, which is why a restricted correlation is only a lower bound.

This makes range restriction a selection-bias problem in disguise. Whenever the sample you analyze was chosen by a process that limits the range of x — admissions that cut low scorers, hiring that cuts weak candidates, a screen that keeps only the extreme cases — the correlation you compute on the survivors is attenuated relative to the population you actually care about. And the direction is always the same: restriction can only weaken a correlation, never strengthen it, so a restricted correlation is a lower bound on the true one, not an estimate of it.

The fix, when you have it, is to correct for the restriction: if you know how much the range was narrowed, statistical corrections (the classic Thorndike formulas) can recover an estimate of the unrestricted correlation. When you cannot correct, the discipline is interpretive — never read a correlation from a range-restricted sample as the general relationship, and always ask whether the sample was selected on x. A weak correlation from a selected group is not evidence of a weak effect; it is evidence you looked at too narrow a slice.

**Correlation is signal over spread, and restricting x's range shrinks the spread while the noise stays put, so the ratio falls — restriction can only attenuate, making a restricted correlation a lower bound on the true one.**

## Worked example

The fixture is ten points with a clear relationship and a restriction range.

```json filename=modules/ai-for-science-and-data/code/data-inter-12/points.json:7-9 COMPLETE
  "restrict_lo": 5,
  "restrict_hi": 8,
  "points": [
```

Ten points; the restricted view keeps only x in [5, 8]. Look at the full set and which points survive the restriction.

```text filename=modules/ai-for-science-and-data/code/data-inter-12/restriction.py --points
POINTS — 10 points; the restricted view keeps x in [5,8]
----------------------------------------------
  x= 1  y= 2
  x= 2  y= 1
  x= 3  y= 4
  x= 4  y= 3
  x= 5  y= 7  <- kept
  x= 6  y= 5  <- kept
  x= 7  y= 8  <- kept
  x= 8  y= 7  <- kept
  x= 9  y=10
  x=10  y= 9
```

Across all ten, y climbs with x from around 2 up to around 9 — a clear rise. The four kept points, x from 5 to 8, have y values 7, 5, 8, 7 — bouncing around with no obvious trend, because within that narrow window the real rise is small and the scatter is not. The correlation is the standardized covariance.

```python filename=modules/ai-for-science-and-data/code/data-inter-12/restriction.py:38-48 COMPLETE
def pearson(points):
    """Correlation of (x, y): covariance over the product of the spreads."""
    n = len(points)
    mx = sum(p[0] for p in points) / n
    my = sum(p[1] for p in points) / n
    cov = sum((x - mx) * (y - my) for x, y in points)
    vx = sum((x - mx) ** 2 for x, y in points)
    vy = sum((y - my) ** 2 for x, y in points)
    if vx == 0 or vy == 0:
        return 0.0
    return round(cov / math.sqrt(vx * vy), 4)
```

Restriction just keeps the slice.

```python filename=modules/ai-for-science-and-data/code/data-inter-12/restriction.py:51-53 COMPLETE
def restrict(points, lo, hi):
    """Keep only the points whose x falls in [lo, hi] -- the narrow slice you actually studied."""
    return [p for p in points if lo <= p[0] <= hi]
```

Predict: the full ten points, rising clearly, should correlate strongly — around 0.9. The middle four, a cloud, should correlate weakly — a few tenths. Run it.

```text filename=modules/ai-for-science-and-data/code/data-inter-12/restriction.py --correlate
CORRELATE — full range vs restricted range
------------------------------------------------
  full range (x 1-10):   r = +0.9228  (strong)
  restricted (x 5-8):    r = +0.3078  (weak)
------------------------------------------------
  same relationship; restricting the range of x attenuated it.
```

Full range: 0.92, a strong correlation anyone would report as a clear relationship. Restricted: 0.31, weak enough that a study would likely conclude "little to no association." Same underlying points, the same rise of y with x — the only difference is that the restricted view cropped out the wide range where the relationship was visible and kept only a narrow window where the scatter dominates. A researcher who only had access to the x-in-[5,8] subgroup would measure 0.31 and be badly wrong about the general relationship.

<svg role="img" aria-label="Correlation: full range 0.92, restricted range 0.31" viewBox="0 0 460 140" width="460" height="140">
  <rect x="0" y="0" width="460" height="140" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="22" font-family="var(--mono)" font-size="11" fill="var(--muted)">measured correlation r</text>
  <line x1="60" y1="110" x2="440" y2="110" stroke="var(--line)"/>
  <rect x="100" y="35" width="120" height="75" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="130" y="29" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">0.92</text><text x="98" y="126" font-family="var(--mono)" font-size="9" fill="var(--muted)">full range</text>
  <rect x="280" y="85" width="120" height="25" fill="var(--s2)" stroke="var(--line)"/><text x="310" y="79" font-family="var(--mono)" font-size="11" fill="var(--s2)">0.31</text><text x="278" y="126" font-family="var(--mono)" font-size="9" fill="var(--muted)">restricted x∈[5,8]</text>
</svg>
^ The same relationship reads as strong across the full range and weak inside the narrow slice — a threefold drop from cropping the range alone.

<svg role="img" aria-label="A scatter of ten points rising left to right, with a box around the middle four (x 5 to 8); inside the box the points look like a cloud with no clear trend" viewBox="0 0 460 210" width="460" height="210">
  <rect x="0" y="0" width="460" height="210" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">y vs x: strong overall, a cloud inside the restricted window</text>
  <line x1="40" y1="180" x2="440" y2="180" stroke="var(--line)"/>
  <line x1="40" y1="40" x2="40" y2="180" stroke="var(--line)"/>
  <line x1="55" y1="170" x2="425" y2="55" stroke="var(--acc-line)" stroke-dasharray="4 3"/><text x="330" y="60" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">full trend r=0.92</text>
  <rect x="180" y="70" width="130" height="90" fill="none" stroke="var(--s2)" stroke-dasharray="3 2"/><text x="188" y="84" font-family="var(--mono)" font-size="8" fill="var(--s2)">restricted x∈[5,8]: r=0.31</text>
  <g fill="var(--ink)">
    <circle cx="55" cy="160" r="4"/><circle cx="92" cy="170" r="4"/><circle cx="129" cy="140" r="4"/><circle cx="166" cy="150" r="4"/>
    <circle cx="203" cy="110" r="4" fill="var(--s2)"/><circle cx="240" cy="130" r="4" fill="var(--s2)"/><circle cx="277" cy="100" r="4" fill="var(--s2)"/><circle cx="314" cy="110" r="4" fill="var(--s2)"/>
    <circle cx="351" cy="70" r="4"/><circle cx="388" cy="80" r="4"/>
  </g>
  <text x="40" y="198" font-family="var(--mono)" font-size="8" fill="var(--muted)">full range shows the line; the boxed window alone looks trendless</text>
</svg>
^ The ten points trace a clear upward line, but the four inside the restriction box look like a formless cloud — the same relationship, viewed through a window too narrow to show its rise.

## Build

Reproduce the two correlations. Pure standard library, deterministic points, so 0.9228 and 0.3078 come out exactly.

Run `--points` for the data, `--correlate` for the two coefficients, `--check` for the gate. The self-test pins the whole point: full is strong, restricted is weak, restriction attenuates, and the restricted set is the same points.

```python filename=modules/ai-for-science-and-data/code/data-inter-12/restriction.py:91-94 COMPLETE
    full_strong = full > 0.8
    print("  the full-range correlation is strong = %s (r = %+.4f)" % (full_strong, full))

    restricted_weak = rest < 0.4
    print("  the restricted-range correlation is weak = %s (r = %+.4f)" % (restricted_weak, rest))
```

The `same_points` check, below, is what makes this a lesson about the range rather than about the data. It confirms the restricted set is literally a subset of the full set — not different points, not re-measured values, just fewer of the same ones. That proves the correlation dropped purely because the range of x narrowed, not because anything about the relationship or the measurements changed. Without it, a skeptic could say the restricted points were simply noisier; the subset check rules that out.

```python filename=modules/ai-for-science-and-data/code/data-inter-12/restriction.py:97-101 COMPLETE
    restriction_attenuates = rest < full
    print("  restricting the range attenuates the correlation = %s (%+.4f -> %+.4f)" % (restriction_attenuates, full, rest))

    same_points = set(map(tuple, restrict(pts, lo, hi))).issubset(set(map(tuple, pts)))
    print("  the restricted set is a subset of the same points = %s (nothing changed but the range)" % same_points)
```

```text filename=modules/ai-for-science-and-data/code/data-inter-12/restriction.py --check
SELF-TEST — the full-range correlation is strong; restricting the range attenuates it to weak
----------------------------------------------------------------------------------------
  the full-range correlation is strong = True (r = +0.9228)
  the restricted-range correlation is weak = True (r = +0.3078)
  restricting the range attenuates the correlation = True (+0.9228 -> +0.3078)
  the restricted set is a subset of the same points = True (nothing changed but the range)
----------------------------------------------------------------------------------------
SELF-TEST PASS  full_strong=True  restricted_weak=True  restriction_attenuates=True  same_points=True
```

Four True flags. Full_strong: the real relationship is strong across the full range. Restricted_weak: the same relationship measures weak on the slice. Restriction_attenuates: restricting lowered the correlation. Same_points: the restricted set is the identical points, so only the range changed. The last flag is the control — it isolates range as the cause and rules out "the subgroup was just noisier."

**The same-points check proves the restricted set is a subset of the full data, so the correlation dropped from narrowing the range alone, not from different or noisier points.**

## Definition of done

You are done when you reproduce 0.92 and 0.31 and can explain the attenuation.

Concretely: `--correlate` shows the full-range correlation strong and the restricted one weak; `--check` prints PASS with four True flags. You can explain why correlation depends on the range of x — it standardizes covariance by the spread of x, and restricting the range shrinks that spread faster than it shrinks the noise. You can state the direction — restriction can only attenuate, so a restricted correlation is a lower bound on the true one — and name the selection-bias origin: any sample chosen on x is range-restricted. And you can name the fix or its absence: correct for restriction if you know its extent, otherwise never read a restricted correlation as the general relationship.

The habit to carry: before trusting a correlation, ask whether the sample was selected on x or on something related to x, and if so, treat the correlation as an underestimate. A weak correlation from a pre-filtered group — admitted, hired, promoted, surviving — is the classic range-restriction signature, not evidence of a weak effect.

## Boss fight

The instructive failure is a hiring test declared useless because it "doesn't predict performance."

A company uses an aptitude test in hiring and later checks whether test scores predict on-the-job performance. Among employees, the correlation is a feeble 0.1, so the test is scrapped as worthless. But the employees are exactly the people who scored well enough to be hired — the low scorers were never hired, so the range of test scores among employees is severely restricted. The 0.1 is a range-restricted correlation; the test's correlation with performance across the full applicant pool could be 0.5 or more. By measuring only among the hired, the company cropped out the range where the test's predictive power was visible and concluded the test was useless — a conclusion that, corrected for restriction, reverses. This exact mistake has invalidated real validity studies until the restriction was accounted for.

Your turn, two moves. First, tighten the window and watch the correlation vanish. Restrict to x in [6, 7] — just two points — and predict: with almost no range in x left, the correlation becomes meaningless (undefined or wildly unstable on two points), because you have removed essentially all the variation the correlation needs. The narrower the slice, the more attenuated, down to zero information. Second, widen it back and watch the correlation recover. Restrict to x in [3, 9] — seven of the ten points — and predict the correlation lands between the 0.31 of the tight window and the 0.92 of the full range, because you have restored most but not all of the range. That monotonic recovery is the signature: the correlation you measure is a direct function of how much of x's range you kept, which is why the honest report always states the range the correlation was measured over, and why a correlation from a restricted range is never the general one.

## External resources

Any psychometrics or research-methods text covers range restriction and the Thorndike correction formulas; the topic is standard in the validity-study literature precisely because selection on the predictor is so common.

Sackett and Yang's "Correction for range restriction: An expanded typology" catalogs the kinds of restriction (direct on x, indirect through a correlated variable) and how each attenuates and is corrected — the rigorous treatment of the hiring-test case.

For the intuition, any discussion of the correlation coefficient's dependence on sample variance makes the point: because r divides by the spread of x, it is not a property of the relationship alone but of the relationship and the range you measured it over.
