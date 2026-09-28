---
id: itt-inter-01
title: Analyze by intention-to-treat, not per-protocol — adherers beat non-adherers even on a placebo, so comparing them confounds the drug with health
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: A randomized trial assigns patients to treatment or control at random, which balances every hidden trait across the arms and is what makes the comparison causal — but who actually takes the assigned pill is not random. Healthier, more organized, more health-conscious patients adhere, and those same traits improve outcomes on their own, so adherence is a downstream, self-selected variable, and conditioning on it re-introduces exactly the confounding that randomization removed. The proof lives in the placebo arm: patients given a sugar pill who adhered to it did better than those who did not, with a pill that does nothing, so that gap is pure selection — the adhering type is healthier. Any analysis that compares people who took the drug to people who did not (per-protocol or as-treated) is therefore measuring the drug's effect plus that health gap and reports a number larger than the drug earns. Intention-to-treat sidesteps it by analyzing patients by the arm they were randomized into regardless of what they took: randomization made the arms' health-type mixes identical, so their difference is unconfounded, at the price of estimating real-world effectiveness (which includes non-adherence) rather than the effect on perfect-takers. On a fixture where the treatment arm's adherers beat its non-adherers by 30, the control arm's adherers beat its non-adherers by 20 on a placebo — so 20 of that 30 is adherence selection and only 10 is drug — while intention-to-treat compares the full arms and reports 5.
eli5: Imagine testing whether a vitamin makes kids taller. You hand out vitamins, and at the end you compare the kids who took them every day to the kids who forgot. The daily-takers are taller — vitamin works! But wait: the kids who remember to take a vitamin every day are also the kids with organized parents, good routines, healthy meals, and regular sleep, and all of that makes kids taller by itself. To prove it, you can run the same test with a fake sugar vitamin: the kids who dutifully take the fake one also come out taller than the forgetful kids — even though it's just sugar. So "took it faithfully" is really a badge of a healthy, organized life, not proof the pill did anything. The fair way is to compare everyone you gave the real vitamin to against everyone you gave the fake one to, forgetful kids included, because you handed those out at random.
---

## Why this module

Randomization is the whole engine of a controlled trial. By assigning patients to arms by coin flip, it makes the two groups statistically identical in every respect — measured and unmeasured, known and unknown — so that any difference in outcome can be attributed to the one thing that differs, the assignment. Every causal claim from a trial rests on not breaking that balance.

Adherence breaks it, quietly. Whether a patient actually takes the pill they were handed is not decided by the coin flip; it is decided by the patient, and the decision correlates with everything that makes a patient do well — health literacy, stability, the absence of confounding illness, plain conscientiousness. The instant you split patients by adherence, your groups are no longer the randomized groups; they are self-selected groups that differ in all those traits, and the balance randomization bought is gone.

The tell that this is real, not hypothetical, is the placebo arm. If adherence were just a proxy for "got the drug," adherent placebo patients should do no better than non-adherent ones — the placebo does nothing. They do better anyway, sometimes dramatically, which can only mean adherence itself marks a healthier patient. This module lays out a trial's outcomes by arm and adherence and compares the per-protocol and intention-to-treat estimates.

**Randomization balances the arms, but adherence is self-selected and correlated with health, so splitting patients by adherence discards that balance — proven by adherent placebo patients outperforming non-adherent ones.**

## Concepts

The key idea is that adherence is a post-randomization variable, and conditioning on anything measured after randomization can reintroduce confounding. Randomization guarantees the arms are comparable at the moment of assignment; it guarantees nothing about subgroups defined by what happened afterward. Adherence, response, side effects, dropout — all are post-randomization, all self-selected, and slicing on any of them forfeits the trial's one guarantee.

Intention-to-treat keeps the guarantee by refusing to slice. It analyzes every patient in the arm they were assigned to, counting non-adherers and even dropouts under their original assignment. This feels wrong at first — you are attributing to the drug the outcomes of people who never took it — but that is exactly the point: because both arms contain the same mix of would-adhere and would-not-adhere patients, their difference isolates the effect of assignment cleanly, with the selection balanced on both sides.

The cost is a shift in what is being measured. Intention-to-treat estimates effectiveness — the effect of prescribing the drug in a world where some people won't take it — not efficacy, the effect on those who take it perfectly. That is usually the more decision-relevant number: a drug that works wonderfully but that patients won't take is not much use. And crucially, ITT is conservative — non-adherence dilutes it toward zero — so it never inflates the effect, whereas per-protocol systematically does. When you must estimate efficacy, the honest tools are instrumental-variable methods, not a naive adherer comparison.

<svg role="img" aria-label="Randomization balances the arms at assignment; the per-protocol analysis slices on post-randomization adherence, unbalancing the arms, while intention-to-treat keeps the whole assigned arms" viewBox="0 0 440 140">
<rect x="20" y="30" width="120" height="30" fill="var(--panel)" stroke="var(--s1)"/>
<text x="80" y="49" fill="var(--ink)" font-size="9" text-anchor="middle">randomize: balanced</text>
<line x1="140" y1="45" x2="180" y2="30" stroke="var(--muted)"/>
<line x1="140" y1="45" x2="180" y2="95" stroke="var(--muted)"/>
<rect x="180" y="18" width="130" height="30" fill="var(--panel)" stroke="var(--s2)"/>
<text x="245" y="37" fill="var(--ink)" font-size="9" text-anchor="middle">per-protocol: slice</text>
<text x="245" y="60" fill="var(--s2)" font-size="8" text-anchor="middle">on adherence -&gt; unbalanced</text>
<rect x="180" y="82" width="130" height="30" fill="var(--panel)" stroke="var(--s1)"/>
<text x="245" y="101" fill="var(--ink)" font-size="9" text-anchor="middle">ITT: keep whole arms</text>
<text x="245" y="124" fill="var(--s1)" font-size="8" text-anchor="middle">still balanced</text>
</svg>
^ Randomization balances the arms; slicing on post-randomization adherence unbalances them, while intention-to-treat keeps the whole assigned arms balanced.

**Adherence is post-randomization and self-selected, so conditioning on it forfeits randomization's balance; intention-to-treat analyzes by assignment, trading efficacy for an unconfounded, conservative estimate of effectiveness.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/itt-inter-01. The fixture gives each arm-by-adherence cell its mean outcome and size.

```json filename=modules/ai-for-science-and-data/code/itt-inter-01/itt.json:3-7 COMPLETE
  "cells": [
    {"arm": "treatment", "adherent": true,  "outcome": 80, "n": 50},
    {"arm": "treatment", "adherent": false, "outcome": 50, "n": 50},
    {"arm": "control",   "adherent": true,  "outcome": 70, "n": 50},
    {"arm": "control",   "adherent": false, "outcome": 50, "n": 50}
```

The intention-to-treat view is the whole-arm mean, weighting cells by size.

```python filename=modules/ai-for-science-and-data/code/itt-inter-01/itt.py:36-41 COMPLETE
def arm_mean(cells, arm):
    """Mean outcome over a whole arm, weighting the cells by size -- the intention-to-treat view."""
    rows = [c for c in cells if c["arm"] == arm]
    total = sum(c["outcome"] * c["n"] for c in rows)
    n = sum(c["n"] for c in rows)
    return total / n
```

The within-arm adherer gap is how much better adherers did than non-adherers in one arm.

```python filename=modules/ai-for-science-and-data/code/itt-inter-01/itt.py:44-46 COMPLETE
def adherer_gap(cells, arm):
    """Within one arm: how much better adherers did than non-adherers."""
    return cell(cells, arm, True)["outcome"] - cell(cells, arm, False)["outcome"]
```

Before running it, predict: the treatment arm shows a big adherer gap, but so does the control (placebo) arm, where no drug is involved. Run `--gaps`:

```text filename=itt.py --gaps
GAPS — within each arm, adherers minus non-adherers
--------------------------------------------------------
  arm         adherent   non-adherent   gap
  treatment   80         50             30
  control     70         50             20
--------------------------------------------------------
  the control (placebo) gap is drug-free -- pure adherence selection
```

The prediction holds. In the treatment arm, adherers beat non-adherers by 30. But in the control arm — placebo — adherers beat non-adherers by 20, with a pill that does nothing. That 20 is pure adherence selection: the adhering type is simply healthier, and it shows up identically whether the pill is real or sugar.

<svg role="img" aria-label="Adherer vs non-adherer outcomes in each arm: treatment 80 vs 50 (gap 30); control placebo 70 vs 50 (gap 20), showing an adherence gap exists even with no drug" viewBox="0 0 440 160">
<line x1="40" y1="130" x2="410" y2="130" stroke="var(--line)"/>
<text x="120" y="150" fill="var(--muted)" font-size="10" text-anchor="middle">treatment</text>
<rect x="70" y="50" width="45" height="80" fill="var(--s1)"/>
<text x="92" y="44" fill="var(--ink)" font-size="9" text-anchor="middle">adh 80</text>
<rect x="125" y="80" width="45" height="50" fill="var(--panel)" stroke="var(--line)"/>
<text x="147" y="74" fill="var(--ink)" font-size="9" text-anchor="middle">non 50</text>
<text x="120" y="120" fill="var(--s1)" font-size="8" text-anchor="middle">gap 30</text>
<text x="320" y="150" fill="var(--muted)" font-size="10" text-anchor="middle">control (placebo)</text>
<rect x="270" y="60" width="45" height="70" fill="var(--s2)"/>
<text x="292" y="54" fill="var(--ink)" font-size="9" text-anchor="middle">adh 70</text>
<rect x="325" y="80" width="45" height="50" fill="var(--panel)" stroke="var(--line)"/>
<text x="347" y="74" fill="var(--ink)" font-size="9" text-anchor="middle">non 50</text>
<text x="320" y="120" fill="var(--s2)" font-size="8" text-anchor="middle">gap 20 (no drug!)</text>
</svg>
^ A 20-point adherer gap appears in the placebo arm where no drug acts — the signature of adherence-as-health-marker.

Now the three effect estimates. Predict: per-protocol reads the treatment gap (30) as the drug; ITT compares the full arms. Run `--effect`:

```text filename=itt.py --effect
EFFECT — three estimates of the treatment effect
----------------------------------------------------------
  naive per-protocol (treatment adherer gap) = 30
    of which adherence selection (placebo gap) = 20
    of which drug (per-protocol - placebo gap) = 10
  intention-to-treat (arm 65 vs arm 60)      = 5
----------------------------------------------------------
  the per-protocol gap is inflated by the placebo adherence gap; ITT is by assignment
```

The prediction holds. The naive per-protocol estimate is 30, but the placebo arm proves 20 of that is adherence selection, leaving only 10 attributable to the drug among takers. Intention-to-treat compares the full arms (65 vs 60) and reports 5 — the effect of being assigned the drug, non-adherers included. Per-protocol overstates by six-fold; ITT is unconfounded and conservative.

<svg role="img" aria-label="A stacked bar for the per-protocol estimate of 30 split into 20 adherence-selection bias and 10 drug, next to the intention-to-treat estimate of 5" viewBox="0 0 440 150">
<line x1="40" y1="125" x2="410" y2="125" stroke="var(--line)"/>
<rect x="90" y="95" width="70" height="30" fill="var(--s1)"/>
<text x="125" y="115" fill="var(--ink)" font-size="9" text-anchor="middle">drug 10</text>
<rect x="90" y="35" width="70" height="60" fill="var(--s2)"/>
<text x="125" y="69" fill="var(--ink)" font-size="9" text-anchor="middle">bias 20</text>
<text x="125" y="140" fill="var(--muted)" font-size="9" text-anchor="middle">per-protocol 30</text>
<rect x="290" y="110" width="70" height="15" fill="var(--s1)"/>
<text x="325" y="103" fill="var(--ink)" font-size="9" text-anchor="middle">ITT 5</text>
<text x="325" y="140" fill="var(--muted)" font-size="9" text-anchor="middle">intention-to-treat</text>
</svg>
^ Per-protocol stacks 20 points of adherence bias on 10 of drug; intention-to-treat, by assignment, reports the unconfounded 5.

## Build

The self-test plants the failure and names each claim as a boolean flag. It first computes the three estimates from the cells.

```python filename=modules/ai-for-science-and-data/code/itt-inter-01/itt.py:83-85 COMPLETE
    per_protocol = adherer_gap(cells, "treatment")
    placebo_gap = adherer_gap(cells, "control")
    itt = arm_mean(cells, "treatment") - arm_mean(cells, "control")
```

Then it checks that adherers beat non-adherers on placebo (the bias exists), that the per-protocol gap exceeds the drug-only effect, that ITT is smaller than per-protocol yet still positive, and that the per-protocol inflation equals the placebo gap.

```python filename=modules/ai-for-science-and-data/code/itt-inter-01/itt.py:87-98 COMPLETE
    adherence_confounded = placebo_gap > 0
    print("  adherers beat non-adherers on placebo (adherence predicts outcome) = %s (%d)" % (adherence_confounded, placebo_gap))

    per_protocol_inflated = per_protocol > (per_protocol - placebo_gap)
    print("  the naive per-protocol gap exceeds the drug-only effect = %s (%d > %d)"
          % (per_protocol_inflated, per_protocol, per_protocol - placebo_gap))

    itt_smaller_than_per_protocol = itt < per_protocol
    print("  intention-to-treat is smaller than the per-protocol gap = %s (%d < %d)" % (itt_smaller_than_per_protocol, itt, per_protocol))

    itt_positive = itt > 0
    print("  intention-to-treat still finds a real effect = %s (%d)" % (itt_positive, itt))
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the placebo gap ever vanishes or ITT ever exceeds per-protocol:

```text filename=itt.py --check
SELF-TEST — adherers beat non-adherers even on placebo; a per-protocol gap inflates the effect, ITT is by assignment
------------------------------------------------------------------------------------------------------------------------
  adherers beat non-adherers on placebo (adherence predicts outcome) = True (20)
  the naive per-protocol gap exceeds the drug-only effect = True (30 > 10)
  intention-to-treat is smaller than the per-protocol gap = True (5 < 30)
  intention-to-treat still finds a real effect = True (5)
  the per-protocol inflation equals the placebo adherence gap = True (20)
```

**The self-test ties the per-protocol inflation to the placebo gap exactly — proving the excess is adherence selection provable from the drug-free arm, not an artifact of the numbers.**

## Definition of done

You can explain why randomization makes a trial causal and why splitting on adherence forfeits that guarantee.
You can state that adherence is a post-randomization, self-selected variable and give the placebo-arm evidence that it marks health, not drug effect.
You can define intention-to-treat, explain why it counts non-adherers under their assignment, and why that keeps the arms balanced.
You can distinguish effectiveness (what ITT estimates) from efficacy (effect on perfect-takers) and say why ITT is conservative, never inflating.
You can name what per-protocol confounds and what the correct tool for efficacy is (instrumental variables), rather than a naive adherer comparison.

## Boss fight

Consider differential dropout, a sharper version of the same trap. Suppose the drug has a side effect that makes the sickest patients quit, so the treatment arm's dropouts are its frailest members while the control arm loses a random slice. A per-protocol analysis that excludes dropouts now removes the frailest from treatment but not from control, making the drug look better for a reason that is entirely selection. Intention-to-treat keeps the dropouts in their assigned arms, so this cannot happen — but it means the analyst must have follow-up outcomes even for people who stopped the drug, which is why trials work so hard to measure everyone to the end. The discipline is not just an analysis choice; it is a data-collection obligation.

Now suppose you genuinely need efficacy — the effect on those who actually take the drug, for a mechanistic question. The wrong move is to fall back to comparing adherers; the right move is an instrumental-variable analysis that uses random assignment as an instrument for adherence (the CACE, complier-average causal effect). It recovers the effect on the type of patient who would adhere, using only the variation that randomization created, so it stays unconfounded. The lesson generalizes: when ITT's effectiveness is not the question, the answer is a method that still leans on the randomization, never one that conditions on the self-selected adherence directly.

**Per-protocol also breaks under differential dropout, which is why ITT obliges you to follow even quitters to the end; and when efficacy is genuinely the question, the unconfounded tool is an instrumental-variable (complier-average) analysis that uses assignment as the instrument, never a direct adherer comparison.**

## External resources

The CONSORT guidelines for reporting randomized trials mandate intention-to-treat analysis and the accounting of all randomized patients, dropouts included.
The Coronary Drug Project (1980) is the classic demonstration that adherent placebo patients had substantially lower mortality than non-adherent ones — the empirical proof that adherence marks health.
Hernán and Robins, "Causal Inference: What If," covers per-protocol effects, the healthy-adherer bias, and the instrumental-variable methods for estimating efficacy without conditioning on adherence.
