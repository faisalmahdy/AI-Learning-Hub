---
id: did-inter-01
title: Difference-in-differences — a before/after change hides the time trend, a treated-vs-control gap hides the pre-existing difference
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: You want the effect of a treatment applied to one group — a policy that hit one state, a feature shipped to one region — but you could not randomize, so you have four numbers: the treated group before and after, and a control group before and after. The two obvious estimates are each wrong in a different way. The before/after change on the treated group (after − before) also contains the time trend that would have moved the group with no treatment at all, so it is the effect plus the trend. The cross-sectional comparison (treated − control, after) also contains the gap the groups already had before anything happened, so it is the effect plus the pre-existing difference. Difference-in-differences uses all four numbers: (after_treated − before_treated) − (after_control − before_control). The control group's before-to-after change is the common time trend, uncontaminated by a treatment it never received, and subtracting it from the treated group's change removes the trend and leaves the effect — valid under the parallel-trends assumption that, absent the treatment, the treated group would have changed by the same amount as the control. On the fixture the treated group goes 100 to 130 and the control 80 to 95: the control's change of 15 is the trend, so the treated group's counterfactual after value is 100 + 15 = 115 and its actual 130 makes the true effect 15. The before/after estimate is 30 (overstated by the trend of 15), the cross-sectional estimate is 35 (overstated by the pre-existing gap of 20), and difference-in-differences is 15. The rule: with no randomization, one difference cannot separate the effect from a confound, but two differences can cancel a confound that moves both groups the same way.
eli5: Suppose you give one class a new study app and want to know if it helped. If you just compare that class's test scores before and after, the scores might have risen because everyone gets better over a semester — app or not. If you just compare that class to another class after, the two classes might have started at different levels. So you do both: see how much the app class improved, see how much a no-app class improved over the same time, and subtract. The no-app class shows you how much improvement was just "the semester happening," and whatever extra the app class gained on top of that is the app's real effect. Two comparisons cancel out the things that would fool either one alone.
---

## Why this module

The cleanest way to measure an effect is a randomized experiment, but a great deal of the time you cannot run one. The treatment already happened, to a group you did not choose — a law passed in one region, a price change in one market, a feature turned on for one cohort. You are left with observational data and a strong temptation to reach for the single comparison that is right in front of you.

Both single comparisons are biased, and in opposite, recognizable ways. Knowing which confound each one smuggles in is what tells you that neither alone can be trusted — and that combining them cancels the confound.

**With no randomization, a single difference cannot separate the treatment effect from a confound that moves alongside it; two differences can.**

## Concepts

Set up the four numbers as a two-by-two: treated and control groups, each measured before and after the treatment. The treatment reached only the treated group, only in the after period.

The first tempting estimate is the before/after change of the treated group: after_treated minus before_treated. Its flaw is time. Outcomes drift for reasons that have nothing to do with the treatment — the economy, the season, a general trend — and the treated group would have followed that drift anyway. So this estimate is the treatment effect plus the time trend, and you cannot tell how much of the change was which.

The second tempting estimate is the cross-section after the treatment: after_treated minus after_control. Its flaw is that the groups were never identical. They had a gap before the treatment existed — different baselines, different composition — and comparing them afterward carries that gap forward. So this estimate is the effect plus the pre-existing difference.

Difference-in-differences takes both differences and subtracts them: (after_treated − before_treated) − (after_control − before_control). Read the second term as the answer to "how much would the treated group have changed on its own?" The control group got no treatment, so its before-to-after change is a clean estimate of the common time trend. Subtract that trend from the treated group's change and the trend cancels, leaving the effect. Equivalently, the control's change lets you build the counterfactual — what the treated group's after value would have been without treatment — and the effect is how far the actual after value sits above it.

The catch is the assumption that licenses the subtraction: parallel trends. Difference-in-differences is correct only if, absent the treatment, the treated group would have moved by the same amount as the control. The data before the treatment can make that plausible, but it can never prove it for the after period, so parallel trends is an argument you make, not a fact the numbers give you.

**Difference-in-differences cancels a confound that shifts both groups equally, but only under parallel trends — the unprovable claim that the control's change is the trend the treated group would also have followed.**

<svg role="img" aria-label="Three estimates of the effect against the true value of 15. The before/after estimate is 30, the cross-sectional estimate is 35, and difference-in-differences is 15, sitting exactly on the true line." viewBox="0 0 440 160">
<rect x="0" y="0" width="440" height="160" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">three estimates of the effect (true value = 15)</text>
<line x1="50" y1="130" x2="420" y2="130" stroke="var(--line)"></line>
<line x1="50" y1="95" x2="420" y2="95" stroke="var(--grid)" stroke-dasharray="3 3"></line>
<text x="424" y="98" fill="var(--muted)" font-size="9">15</text>
<rect x="80" y="60" width="46" height="70" fill="var(--s1)"></rect>
<text x="82" y="54" fill="var(--s1)" font-size="9">before/after 30</text>
<rect x="180" y="48" width="46" height="82" fill="var(--s1)"></rect>
<text x="184" y="42" fill="var(--s1)" font-size="9">cross-sec 35</text>
<rect x="300" y="95" width="46" height="35" fill="var(--s2)"></rect>
<text x="306" y="89" fill="var(--s2)" font-size="9">DiD 15</text>
</svg>
^ Both single-difference estimates overshoot the true effect — by different amounts, because they carry different confounds — while difference-in-differences lands on it.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/ai-for-science-and-data/code/did-inter-01/did.py

The fixture is the two-by-two: treated 100 → 130, control 80 → 95.

```json filename=modules/ai-for-science-and-data/code/did-inter-01/did.json:3-6 COMPLETE
  "before_treated": 100,
  "after_treated": 130,
  "before_control": 80,
  "after_control": 95
```

Each naive estimate is one difference.

```python filename=modules/ai-for-science-and-data/code/did-inter-01/did.py:32-34 COMPLETE
def treated_change(d):
    """The treated group's before-to-after change: the treatment effect PLUS the time trend."""
    return d["after_treated"] - d["before_treated"]
```

```python filename=modules/ai-for-science-and-data/code/did-inter-01/did.py:37-39 COMPLETE
def control_change(d):
    """The control group's before-to-after change: the common time trend, with no treatment."""
    return d["after_control"] - d["before_control"]
```

```text filename=did.py --naive
NAIVE — the two obvious estimates, each biased
----------------------------------------------------------------
  before/after (treated): 130 - 100 = 30
      = effect + time trend (trend is the control's change, 15)
  cross-section (after):  130 - 95 = 35
      = effect + pre-existing gap (20)
----------------------------------------------------------------
  one estimate absorbs the time trend, the other the pre-existing gap
```

The before/after estimate is 30 — but 15 of that is the time trend (the control moved 15 with no treatment), so it overstates. The cross-sectional estimate is 35 — but 20 of that is the pre-existing gap (treated started at 100, control at 80), so it overstates too, and by a different amount. Two estimates, two different wrong answers, neither obviously wrong on its own.

<svg role="img" aria-label="A two-by-two of the four measurements. Treated row: before 100, after 130. Control row: before 80, after 95. A horizontal arrow marks the before/after difference on the treated row; a vertical arrow marks the after cross-section; both are labeled as biased." viewBox="0 0 440 170">
<rect x="0" y="0" width="440" height="170" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">the four numbers, and the two biased comparisons</text>
<text x="150" y="46" fill="var(--muted)" font-size="10">before</text>
<text x="280" y="46" fill="var(--muted)" font-size="10">after</text>
<text x="30" y="78" fill="var(--ink)" font-size="11">treated</text>
<text x="155" y="78" fill="var(--ink)" font-size="12">100</text>
<text x="285" y="78" fill="var(--ink)" font-size="12">130</text>
<text x="30" y="118" fill="var(--ink)" font-size="11">control</text>
<text x="160" y="118" fill="var(--muted)" font-size="12">80</text>
<text x="288" y="118" fill="var(--muted)" font-size="12">95</text>
<line x1="180" y1="74" x2="280" y2="74" stroke="var(--s1)"></line>
<text x="185" y="66" fill="var(--s1)" font-size="9">before/after = 30 (+ trend)</text>
<line x1="298" y1="84" x2="298" y2="112" stroke="var(--s1)"></line>
<text x="308" y="102" fill="var(--s1)" font-size="9">cross-section = 35 (+ gap)</text>
</svg>
^ The horizontal comparison carries the time trend, the vertical one carries the pre-existing gap; each single difference confounds the effect with one bias.

## Build

Difference-in-differences subtracts the two changes.

```python filename=modules/ai-for-science-and-data/code/did-inter-01/did.py:52-54 COMPLETE
def did(d):
    """Difference-in-differences: treated change minus control change -- both biases cancel."""
    return treated_change(d) - control_change(d)
```

```text filename=did.py --did
DID — difference-in-differences
----------------------------------------------------------------
  treated change  = 130 - 100 = 30
  control change  = 95 - 80 = 15   (the time trend)
  DiD = 30 - 15 = 15
  counterfactual after_treated (no treatment) = 100 + 15 = 115
  effect = 130 - 115 = 15
----------------------------------------------------------------
  subtracting the control's change removes the trend, leaving the effect (under parallel trends)
```

The control's change of 15 is the time trend, so the treated group would have reached 100 + 15 = 115 without any treatment. It actually reached 130, so the effect is 15 — exactly what difference-in-differences reports. The trend cancelled; the pre-existing gap never entered, because both terms are within-group changes that the starting levels drop out of.

<svg role="img" aria-label="A line plot. The control line rises from 80 to 95. The treated line rises from 100 to 130. A dashed counterfactual line rises from 100 parallel to the control, to 115. The gap between the treated after point 130 and the counterfactual 115 is labeled effect = 15." viewBox="0 0 440 180">
<rect x="0" y="0" width="440" height="180" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">parallel trends: the counterfactual and the effect</text>
<text x="70" y="165" fill="var(--muted)" font-size="9">before</text>
<text x="330" y="165" fill="var(--muted)" font-size="9">after</text>
<line x1="90" y1="150" x2="360" y2="130" stroke="var(--muted)"></line>
<text x="364" y="132" fill="var(--muted)" font-size="9">control 80&#8594;95</text>
<line x1="90" y1="110" x2="360" y2="50" stroke="var(--s2)"></line>
<text x="364" y="52" fill="var(--s2)" font-size="9">treated 100&#8594;130</text>
<line x1="90" y1="110" x2="360" y2="90" stroke="var(--s1)" stroke-dasharray="4 3"></line>
<text x="300" y="104" fill="var(--s1)" font-size="9">counterfactual &#8594;115</text>
<line x1="360" y1="50" x2="360" y2="90" stroke="var(--ink)"></line>
<text x="366" y="74" fill="var(--ink)" font-size="9">effect 15</text>
</svg>
^ The dashed counterfactual runs from the treated baseline parallel to the control's trend; the vertical gap between it and the actual treated endpoint is the difference-in-differences effect.

The self-test shows both naive estimates missing and difference-in-differences landing on the truth.

```python filename=modules/ai-for-science-and-data/code/did-inter-01/did.py:94-100 COMPLETE
    beforeafter_overstates = treated_change(d) != truth
    print("  before/after estimate misses the true effect = %s (%d vs %d, off by the trend %d)"
          % (beforeafter_overstates, treated_change(d), truth, control_change(d)))

    crosssection_overstates = cross_section(d) != truth
    print("  cross-sectional estimate misses the true effect = %s (%d vs %d, off by the pre-gap %d)"
          % (crosssection_overstates, cross_section(d), truth, pre_gap(d)))
```

```text filename=did.py --check
SELF-TEST — both naive estimates miss the true effect while difference-in-differences recovers it, and it equals the treated change minus the control's time trend
----------------------------------------------------------------------------------------------------------------
  before/after estimate misses the true effect = True (30 vs 15, off by the trend 15)
  cross-sectional estimate misses the true effect = True (35 vs 15, off by the pre-gap 20)
  difference-in-differences recovers the true effect = True (15 == 15)
  DiD equals the treated change minus the control's time trend = True (30 - 15)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  beforeafter_overstates=True  crosssection_overstates=True  did_recovers=True  did_removes_trend=True
```

**The two naive estimates disagree with each other (30 vs 35), which is itself the tell: if a before/after and a cross-section give different answers, each is carrying a different confound, and neither is the effect.**

## Definition of done

You can name the confound in each single difference — the time trend in the before/after change, the pre-existing gap in the cross-section — and say why each inflates or deflates its estimate.

You can compute difference-in-differences from the four numbers and explain why subtracting the control's change removes the trend while the starting levels (and thus the pre-existing gap) drop out.

You can state the parallel-trends assumption precisely and say why it is an argument, not something the after-period data can verify.

You can describe the diagnostic value of the two naive estimates disagreeing: it signals that confounds are present, so the single-difference numbers should not be reported as the effect.

## Boss fight

A state raised its minimum wage and employment there fell 3% over the next year. An opponent cites the 3% as proof the policy killed jobs; a supporter notes that a neighboring state with no change saw employment fall 4% over the same year.

First: turn this into a difference-in-differences. What is the treated group's change, the control group's change, and the DiD estimate — and does it support the opponent's or the supporter's reading?

Then: the whole argument rests on parallel trends. State exactly what has to be true about the two states for the DiD to be valid, and describe one check you could run on data from the years before the wage change to make parallel trends more or less plausible. Why does that check support the assumption without ever proving it?

Finally: suppose the neighboring state was chosen because it is adjacent, but its economy is dominated by a different industry that happened to have a bad year. Explain how that violates parallel trends and which direction it would bias the DiD estimate, and what it would mean to pick a better control (or several) instead of the one nearest on a map.

## External resources

The classic Card and Krueger minimum-wage study is the canonical applied difference-in-differences and is worth reading precisely for how much of it is devoted to defending parallel trends rather than computing the estimate.

Any econometrics treatment of difference-in-differences (for example the relevant chapter of Mostly Harmless Econometrics) derives the estimator as a double difference and spells out the parallel-trends identifying assumption and the event-study checks used to argue for it.
