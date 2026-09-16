---
id: equiv-inter-01
title: To claim two models are equivalent, show the whole CI fits inside the margin — a non-significant difference is not equivalence
topic: evals-and-statistics
level: intermediate
status: ready
time: 16 min
summary: You want to replace an expensive model with a cheaper one and must show it is "as good," so you run an eval, find the accuracy gap is not statistically significant (its confidence interval includes zero), and declare them equivalent. That is the wrong test, and it fails in the most dangerous way: it is easiest to pass when the eval is weakest. A small eval gives a wide interval, and a wide interval includes zero for almost any true difference — so "not significant" is reached not by proving the models are close but by failing to measure them. The same wide interval that includes zero can also include a ten-point gap you would care about, so it is equally consistent with equivalence and with a real regression. The correct test flips the burden of proof: to claim equivalence, show the entire confidence interval lies inside a pre-set margin (the two-one-sided-tests procedure), ruling out a difference bigger than the margin in either direction. On a fixture where the gap is 0.01 with a 95% CI of [−0.08, 0.10] and the margin is 0.05, the naive test declares equivalence while the CI still admits a 0.10 gap — twice the margin — and TOST correctly refuses until a larger eval narrows the CI to [−0.03, 0.04], inside the margin.
eli5: If you want to prove two ropes are the same length, measuring once with a stretchy tape and getting "close enough, can't tell them apart" doesn't prove it — a sloppy measurement can't tell anything apart, including ropes that really are very different. To actually prove they're about the same, you need a measurement precise enough to say "the difference is smaller than this much" — small enough that you'd shrug at it. Failing to find a difference is not the same as showing there isn't one.
---

## Why this module

Establishing that two things are the same is a different claim from failing to prove they differ, and the difference matters most exactly when your evidence is thin — because a weak eval fails to prove a difference automatically, and mistaking that for equivalence rewards the worst measurements with the strongest-sounding conclusion.

The setup is common and consequential: a cheaper, faster model is available, and you want to switch if it is "as good" as the incumbent. So you evaluate both, compute the accuracy gap, and check significance. The gap is not significant — its confidence interval includes zero — and the conclusion writes itself: no significant difference, therefore equivalent, therefore switch. The logic is backwards. A significance test asks "can we rule out zero difference?" and answering "no" is not the same as answering "the difference is negligible." Worse, the test is biased toward the convenient answer: the smaller and noisier your eval, the wider the confidence interval, and the wider the interval, the more surely it includes zero. So an underpowered eval — one that measured almost nothing — passes the "not significant" bar most easily, and hands you an equivalence claim built on the absence of data rather than the presence of closeness.

**A non-significant difference means the eval could not rule out zero, not that the models are close — and because a weak eval produces a wide interval that includes zero for almost any true difference, "not significant, so equivalent" is easiest to conclude precisely when the evidence is weakest.**

The correct procedure inverts the burden of proof. First choose a margin: the largest gap you would still consider practically the same — say five points of accuracy. Then equivalence is established only if the *entire* confidence interval on the difference lies within plus-or-minus that margin. This is the two-one-sided-tests (TOST) procedure, and it means exactly what it says: you have positively ruled out a difference larger than the margin in either direction. A wide interval that spills past the margin does not establish equivalence no matter how it straddles zero — it means "inconclusive, get more data." Only when the eval is strong enough to pull both ends of the interval inside the margin have you earned the claim. This module runs both tests on the same numbers and shows them disagree.

## Concepts

**Not significant** means the confidence interval on the difference includes zero — the eval cannot rule out that the true gap is zero. It says nothing about how large the gap might be.

```python filename=modules/evals-and-statistics/code/equiv-inter-01/equiv.py:43-45 COMPLETE
def ci_includes_zero(lo, hi):
    """The difference is 'not statistically significant' when its confidence interval contains 0."""
    return lo <= 0 <= hi
```

**The equivalence margin** is the largest difference you would still call practically the same — a decision made before the eval, from what the gap would cost in production, not from the data.

**TOST equivalence** is established only when the whole confidence interval lies within [−margin, +margin], so a difference bigger than the margin is ruled out in both directions.

```python filename=modules/evals-and-statistics/code/equiv-inter-01/equiv.py:48-50 COMPLETE
def tost_equivalent(lo, hi, margin):
    """TOST: equivalence is established only if the WHOLE interval lies within [-margin, +margin]."""
    return lo >= -margin and hi <= margin
```

<svg role="img" aria-label="A margin band from minus 0.05 to 0.05 around zero; TOST equivalence requires the whole CI inside the band, while the naive test only requires the CI to touch zero" viewBox="0 0 300 100" width="300" height="100">
  <line x1="20" y1="52" x2="290" y2="52" stroke="var(--grid)"/>
  <rect x="120" y="30" width="70" height="44" fill="var(--s1)" opacity="0.2" stroke="var(--s1)"/>
  <text x="122" y="26" fill="var(--s1)" font-size="7">margin ±0.05</text>
  <line x1="155" y1="28" x2="155" y2="76" stroke="var(--ink)" stroke-dasharray="2 2"/><text x="150" y="88" fill="var(--muted)" font-size="7">0</text>
  <text x="118" y="88" fill="var(--muted)" font-size="7">−.05</text><text x="180" y="88" fill="var(--muted)" font-size="7">+.05</text>
  <text x="200" y="44" fill="var(--muted)" font-size="7">TOST: whole CI in the band</text>
  <text x="200" y="66" fill="var(--muted)" font-size="7">naive: CI merely touches 0</text>
  <text x="20" y="98" fill="var(--muted)" font-size="8">equivalence is a claim about the band; significance is only a claim about the zero line</text>
</svg>
^ Equivalence (TOST) asks whether the whole interval fits inside the ±margin band; significance asks only whether the interval touches the zero line — two different questions with two different answers.

**To claim equivalence, positively rule out a difference larger than your margin by fitting the whole confidence interval inside it — do not infer closeness from a non-significant test, which a weak eval passes by measuring nothing.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/equiv-inter-01/equiv.py

The fixture is a 0.01 gap with a wide CI from a small eval, a 0.05 margin, and a narrower CI from a larger eval.

```json filename=modules/evals-and-statistics/code/equiv-inter-01/equiv.json:3-8 COMPLETE
  "difference": 0.01,
  "ci_low": -0.08,
  "ci_high": 0.10,
  "margin": 0.05,
  "tight_ci_low": -0.03,
  "tight_ci_high": 0.04
```

Run `--assess` to apply both tests.

```text filename=--assess
ASSESS — 'not significant, so equivalent' vs TOST (whole CI within +/-0.05)
----------------------------------------------------------------------
  small eval:  gap 0.01, CI [-0.08, 0.10]
    naive (CI includes 0 -> equivalent): True
    TOST  (CI within margin -> equivalent): False
  larger eval: gap 0.01, CI [-0.03, 0.04]
    TOST  (CI within margin -> equivalent): True
```

The small eval estimates the gap at 0.01 with a confidence interval of [−0.08, 0.10]. That interval includes zero, so the naive test calls the difference not significant and concludes equivalence. But look at the interval: it stretches to 0.10, twice the 0.05 margin, so a real ten-point accuracy gap is entirely consistent with this data. The eval has not shown the models are close; it has shown it cannot tell them apart, which is a statement about the eval, not the models. TOST refuses the equivalence claim precisely because the interval reaches past the margin. Now the larger eval: same 0.01 gap, but a tighter interval of [−0.03, 0.04] — both ends inside ±0.05 — so a difference larger than the margin has been ruled out in both directions, and TOST concludes equivalence. Same point estimate, opposite verdicts, and the thing that changed was not the models but how precisely they were measured. Equivalence had to be earned with precision; the naive test handed it out for imprecision.

<svg role="img" aria-label="The wide CI from -0.08 to 0.10 spills past the margin band, so TOST says no; the narrow CI from -0.03 to 0.04 fits inside, so TOST says yes" viewBox="0 0 300 104" width="300" height="104">
  <rect x="110" y="16" width="80" height="80" fill="var(--s1)" opacity="0.15" stroke="var(--s1)"/>
  <text x="112" y="12" fill="var(--s1)" font-size="7">±0.05 margin</text>
  <line x1="150" y1="16" x2="150" y2="96" stroke="var(--ink)" stroke-dasharray="2 2"/>
  <text x="6" y="42" fill="var(--muted)" font-size="8">small eval</text>
  <line x1="62" y1="38" x2="238" y2="38" stroke="var(--s2)" stroke-width="2"/><circle cx="158" cy="38" r="2.5" fill="var(--s2)"/>
  <text x="242" y="41" fill="var(--s2)" font-size="7">spills out ✗</text>
  <text x="6" y="76" fill="var(--muted)" font-size="8">larger eval</text>
  <line x1="126" y1="72" x2="182" y2="72" stroke="var(--s1)" stroke-width="2"/><circle cx="158" cy="72" r="2.5" fill="var(--s1)"/>
  <text x="186" y="75" fill="var(--s1)" font-size="7">fits ✓</text>
  <text x="6" y="102" fill="var(--muted)" font-size="8">both CIs include 0 (naive: equivalent), but only the narrow one fits the margin (TOST: equivalent)</text>
</svg>
^ Both intervals include zero, so the naive test calls both equivalent — but only the narrow interval fits inside the ±0.05 margin, so only the larger eval earns equivalence under TOST.

## Build

How wrong is the naive verdict? Run `--range` to see what the "not significant" interval still permits.

```text filename=--range
RANGE — what the 'not significant' interval actually admits
------------------------------------------------------------
  margin of equivalence:        +/- 0.05
  CI on the gap:                [-0.08, 0.10]
  largest gap still plausible:  0.10  (2.0x the margin)
  does the CI include 0?        True
```

The interval includes zero, yes — but it also includes 0.10, a gap twice the size of the margin you declared meaningful. "Not significant" collapsed a huge range of possibilities, from a ten-point regression to a ten-point improvement, into a single reassuring word, and threw away the part that mattered: the interval never ruled out a difference you would have cared about. This is why the naive move is not merely imprecise but actively misleading — it converts "we don't know" into "they're the same," and the direction of the error is always toward a false equivalence, because more noise means a wider interval means a more confident-sounding null. The fix is not a different threshold on the same test; it is asking the right question. TOST asks "is every plausible difference smaller than the margin?" and only a precise enough eval can answer yes. When it answers no, the honest report is "inconclusive — the eval cannot yet establish equivalence," which points at the real remedy: more data, until the interval is tight enough to fit the margin or to reveal the difference that was hiding in the noise.

<svg role="img" aria-label="The confidence interval from -0.08 to 0.10 is shown against the margin; its upper end reaches 0.10, double the 0.05 margin, so a large gap is still admitted" viewBox="0 0 300 92" width="300" height="92">
  <text x="6" y="12" fill="var(--muted)" font-size="8">what the CI [-0.08, 0.10] still allows</text>
  <line x1="20" y1="50" x2="290" y2="50" stroke="var(--grid)"/>
  <line x1="150" y1="40" x2="150" y2="60" stroke="var(--ink)"/><text x="146" y="72" fill="var(--muted)" font-size="7">0</text>
  <rect x="120" y="44" width="60" height="12" fill="var(--s1)" opacity="0.25"/><text x="122" y="38" fill="var(--s1)" font-size="6">margin</text>
  <line x1="62" y1="50" x2="238" y2="50" stroke="var(--s2)" stroke-width="2"/>
  <line x1="238" y1="44" x2="238" y2="56" stroke="var(--s2)"/><text x="212" y="40" fill="var(--s2)" font-size="7">0.10 = 2× margin</text>
  <text x="6" y="88" fill="var(--muted)" font-size="8">a real gap of 0.10 sits inside this 'not significant' interval — closeness was never shown</text>
</svg>
^ The interval reaches 0.10 — double the margin — so a difference you would clearly care about is still fully consistent with the "not significant" result; the naive test hid a possible ten-point gap behind the word "equivalent."

## Definition of done

The self-test pins the disagreement: the naive test calls the small eval equivalent, a gap larger than the margin is still in the CI, TOST refuses, and only the tighter eval earns equivalence.

```python filename=modules/evals-and-statistics/code/equiv-inter-01/equiv.py:92-105 COMPLETE
    naive_calls_equivalent = ci_includes_zero(lo, hi)
    print("  the naive test (CI includes 0) calls the small eval equivalent = %s" % naive_calls_equivalent)

    big_gap_still_possible = largest_plausible_gap(lo, hi) > m
    print("  yet a gap larger than the margin is still in the CI = %s (%.2f > %.2f)" % (big_gap_still_possible, largest_plausible_gap(lo, hi), m))

    tost_refuses_wide = not tost_equivalent(lo, hi, m)
    print("  so TOST refuses to call the small eval equivalent = %s" % tost_refuses_wide)

    tost_accepts_tight = tost_equivalent(tlo, thi, m)
    print("  TOST accepts the larger eval whose CI fits the margin = %s ([%.2f, %.2f])" % (tost_accepts_tight, tlo, thi))

    naive_and_tost_disagree = naive_calls_equivalent and not tost_equivalent(lo, hi, m)
    print("  naive and TOST disagree on the small eval = %s" % naive_and_tost_disagree)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — a CI that includes 0 is not equivalence; TOST requires the whole CI inside the margin; a tighter eval earns it
--------------------------------------------------------------------------------------------------------------------------
  the naive test (CI includes 0) calls the small eval equivalent = True
  yet a gap larger than the margin is still in the CI = True (0.10 > 0.05)
  so TOST refuses to call the small eval equivalent = True
  TOST accepts the larger eval whose CI fits the margin = True ([-0.03, 0.04])
  naive and TOST disagree on the small eval = True
```

**Done means the two tests are proven to answer different questions: on the small eval the naive "not significant" test declares equivalence while the CI [−0.08, 0.10] still admits a 0.10 gap (twice the 0.05 margin), so TOST refuses — and only when a larger eval tightens the CI to [−0.03, 0.04], inside the margin, does TOST conclude equivalence, exposing "non-significant, so equivalent" as a claim a weak eval passes for free.**

## Boss fight

Predict the two ways the equivalence test itself goes wrong. It is tempting to treat the margin as a technicality and pick it after seeing the data.

The first trap is that the whole procedure hinges on the margin, and the margin is a judgment about consequences, not statistics — so it must be chosen before the eval and defended on its own terms. Set it too wide and equivalence becomes meaningless: declare a 15-point margin and you will "prove" two models equivalent that differ by a mile, because you defined a mile as close enough. Set it too narrow and no realistic eval can ever fit the interval inside it, so you can never conclude equivalence even for models that are genuinely identical. And choosing the margin *after* seeing the confidence interval — quietly widening it until the CI fits — is the equivalence-testing version of p-hacking, converting the honest "inconclusive" into a rigged "equivalent." The margin should come from what the difference would cost in production (what accuracy drop is tolerable for the latency or price you gain), be written down before the data, and survive a skeptic asking "would you accept a model that is exactly that much worse?"

```python filename=modules/evals-and-statistics/code/equiv-inter-01/equiv.py:53-55 COMPLETE
def largest_plausible_gap(lo, hi):
    """The biggest absolute difference the interval still admits -- what 'not significant' fails to rule out."""
    return max(abs(lo), abs(hi))
```

The second trap is that equivalence and difference are not exhaustive, and a single eval can land in the gap between them — or, worse, satisfy both. An interval can be too wide to fit the margin (not equivalent) yet still include zero (not different): that is the genuinely inconclusive case, and the honest verdict is "we don't know," not a default to either side. Conversely, with a large enough eval an interval can be narrow, sit entirely within the margin (TOST-equivalent), and still exclude zero (statistically significant) — a difference that is real but too small to matter, which is exactly the situation equivalence testing exists to name. So "significant" and "equivalent" are answers to orthogonal questions and you should report both: a difference can be significant-and-trivial (real but within the margin) or non-significant-and-unproven (a wide interval that establishes nothing). Reducing the eval to a single significant/not-significant bit throws away the axis — practical size — that equivalence testing was built to measure, which is the same lesson as "significance is not size," now made actionable: pick a margin, and test against it directly.

**To claim two models are equivalent, run TOST — show the whole confidence interval on their difference lies within a pre-chosen margin — because a non-significant difference only means a weak eval could not rule out zero, and a wide interval that includes zero can also include a gap far larger than you would tolerate; but the margin must be set before the data from the real cost of a difference (never widened to fit), and since equivalence and significance are orthogonal, report both, so a real-but-trivial difference and a genuinely inconclusive eval are named rather than collapsed into a single significant/not bit.**

## External resources

Any reference on equivalence testing and the two-one-sided-tests (TOST) procedure (for example Lakens' "Equivalence Tests" tutorial) — the formal method, how to choose a smallest-effect-size-of-interest margin, and the relationship between TOST and confidence intervals.

Writing on the difference between "absence of evidence" and "evidence of absence" and on non-inferiority versus equivalence trials from clinical statistics — the general logic of proving two things are close rather than failing to prove them different.

The companion "a null result from a small eval is not 'no difference'" and "test the difference, not whether the two error bars overlap" modules — the first is the warning this module makes constructive (how to actually establish closeness), and the second is its mirror image (do not falsely conclude a tie from an overlap), so the three cover both directions of comparing two systems.
