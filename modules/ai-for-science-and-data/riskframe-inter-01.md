---
id: riskframe-inter-01
title: Report the absolute risk reduction, not just the relative one — "50% lower risk" means something different at every baseline
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: A treatment's benefit gets reported two ways that can sound wildly different for the exact same effect. The relative risk reduction is the fraction of baseline risk the treatment removes — 2% down to 1% removes half the risk, so it is a 50% relative reduction, the dramatic number headlines reach for. The absolute risk reduction is the actual drop in the event rate — 2% to 1% is a drop of 1 percentage point. The relative figure hides the baseline, and the baseline decides whether "half the risk" is a big deal or a rounding error. Put the same 50% relative reduction on two baselines: on a rare outcome (2% to 1%) the absolute reduction is 1 point and you must treat 100 people to prevent one event (NNT 100); on a common outcome (40% to 20%) the same 50% relative reduction is a 20-point absolute drop and you need to treat only 5 (NNT 5). Identical relative reduction, one marginal and one transformative, and the relative number alone cannot tell them apart. The number needed to treat, the reciprocal of the absolute reduction, is the honest single number. On a fixture of two treatments each cutting risk by a relative 50%, the rare-outcome treatment has ARR 1 point and NNT 100, the common-outcome treatment ARR 20 points and NNT 5 — a 20-fold difference in real benefit behind the same headline.
eli5: Imagine two coupons that both say "50% off!" One is 50% off a $2 candy bar — you save a dollar. The other is 50% off a $40 shirt — you save twenty dollars. The "50% off" sounds the same, but what you actually save depends entirely on the starting price. Medicine works the same way: "cuts your risk in half" saves a lot of people when the risk was big to start with, and almost nobody when the risk was tiny. So you should always ask not "by what percent?" but "how many people actually avoid the bad thing?" — and the honest answer is a plain count, like "you'd have to treat 100 people for 1 to benefit."
---

## Why this module

"Cuts your risk by 50%" is the number that sells a treatment, and it is often technically true while telling you almost nothing about whether the treatment is worth taking. The relative reduction deliberately drops the one fact that decides the answer — how big the risk was to begin with — so the same impressive-sounding percentage can hide a life-changing benefit or a benefit so small that nearly everyone who takes the treatment gets nothing from it. The trap is that the relative number is not a lie; it is a framing, and the framing systematically makes small effects look large.

A treatment's benefit gets reported two ways. The *relative* risk reduction is the fraction of the baseline risk that the treatment removes: if 2% of untreated people have the event and 1% of treated people do, the treatment removed half of the risk, so the relative risk reduction is 50%. The *absolute* risk reduction is the actual drop in the event rate: from 2% to 1% is a drop of 1 percentage point. The relative figure hides the baseline, and the baseline is what decides whether "half the risk" is a big deal or a rounding error.

Watch the same 50% relative reduction sit on two baselines. On a rare outcome — 2% down to 1% — the absolute reduction is 1 percentage point, so you would have to treat 100 people to prevent a single event, because 99 of every 100 treated were never going to have it anyway. On a common outcome — 40% down to 20% — the same 50% relative reduction is a 20-point absolute drop, and you only need to treat 5 people to prevent one event. The number needed to treat (NNT), the reciprocal of the absolute reduction, is the honest single number. This module computes both from real counts.

**A relative risk reduction is meaningless without the baseline it applies to, so always report the absolute risk reduction (the change in percentage points) and ideally the number needed to treat alongside it — the same "50% lower" can be an NNT of 5 or an NNT of 100, and only the absolute framing tells you which.**

## Concepts

**Three numbers from the same two counts:** the relative reduction divides by the baseline risk (so it hides the baseline), the absolute reduction divides by the population (so it keeps it), and the NNT inverts the absolute reduction into a plain headcount.

```python filename=modules/ai-for-science-and-data/code/riskframe-inter-01/riskframe.py:47-59 COMPLETE
def relative_reduction(control_events, treated_events):
    """Fraction of the baseline risk removed = (control - treated) / control."""
    return (control_events - treated_events) / control_events


def absolute_reduction(control_events, treated_events, per):
    """Drop in the event rate, in the same units as the risks (a proportion) = (control - treated) / per."""
    return (control_events - treated_events) / per


def number_needed_to_treat(control_events, treated_events, per):
    """How many must be treated to prevent one event = 1 / absolute_reduction = per / (control - treated)."""
    return per / (control_events - treated_events)
```

**We compute all three per scenario from integer event counts**, so every printed number is exact rather than a float artifact.

```python filename=modules/ai-for-science-and-data/code/riskframe-inter-01/riskframe.py:62-71 COMPLETE
def metrics(s):
    c, t, per = s["control_events"], s["treated_events"], s["per"]
    return {
        "control_risk": c / per,
        "treated_risk": t / per,
        "rrr": relative_reduction(c, t),
        "arr": absolute_reduction(c, t, per),
        "nnt": number_needed_to_treat(c, t, per),
        "prevented": c - t,
    }
```

<svg role="img" aria-label="Two treatments with the same 50 percent relative reduction: bars show the relative reduction is identical while the absolute reduction is 1 point for the rare outcome and 20 points for the common outcome" viewBox="0 0 300 130" width="300" height="130">
  <text x="6" y="12" fill="var(--muted)" font-size="8">same relative 50% — absolute reduction 1pt vs 20pt</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">RRR rare</text>
  <rect x="80" y="26" width="100" height="10" fill="var(--s1)"/><text x="184" y="34" fill="var(--muted)" font-size="7">50%</text>
  <text x="10" y="50" fill="var(--muted)" font-size="7">RRR common</text>
  <rect x="80" y="42" width="100" height="10" fill="var(--s1)"/><text x="184" y="50" fill="var(--muted)" font-size="7">50% (identical)</text>
  <line x1="14" y1="62" x2="286" y2="62" stroke="var(--grid)"/>
  <text x="10" y="84" fill="var(--muted)" font-size="7">ARR rare</text>
  <rect x="80" y="76" width="5" height="10" fill="var(--s2)"/><text x="90" y="84" fill="var(--muted)" font-size="7">1 pt → NNT 100</text>
  <text x="10" y="104" fill="var(--muted)" font-size="7">ARR common</text>
  <rect x="80" y="96" width="100" height="10" fill="var(--s2)"/><text x="184" y="104" fill="var(--muted)" font-size="7">20 pt → NNT 5</text>
  <text x="10" y="122" fill="var(--muted)" font-size="6">the relative bar can't tell the two treatments apart; the absolute bar can</text>
</svg>
^ The relative-reduction bars are identical (both 50%), but the absolute-reduction bars differ 20-fold — 1 point for the rare outcome versus 20 points for the common one — which is exactly the information the relative figure discards.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/riskframe-inter-01/riskframe.py

The fixture is two treatments as integer counts per 10,000 people: a rare outcome (200 → 100 events) and a common one (4000 → 2000).

```json filename=modules/ai-for-science-and-data/code/riskframe-inter-01/riskframe.json:3-6 COMPLETE
  "scenarios": [
    {"name": "rare outcome (2% baseline)", "per": 10000, "control_events": 200, "treated_events": 100},
    {"name": "common outcome (40% baseline)", "per": 10000, "control_events": 4000, "treated_events": 2000}
  ]
```

Run `--risk`.

```text filename=--risk
RISK — two treatments, each a 50% RELATIVE reduction, on different baselines
----------------------------------------------------------------------------------
  treatment                       baseline  treated   RRR     ARR      NNT
  rare outcome (2% baseline)      2%        1%        50%     1 pt     100
  common outcome (40% baseline)   40%       20%       50%     20 pt    5
----------------------------------------------------------------------------------
  same RRR (50%), but ARR and NNT differ 20-fold -- the relative number hid the baseline.
```

Read across the two rows. The RRR column is identical — both treatments remove exactly half of the baseline risk, so both would earn the headline "cuts risk by 50%." Now read the ARR and NNT columns, which the relative figure suppressed. The rare-outcome treatment drops the event rate by 1 percentage point (2% to 1%), so its number needed to treat is 100: you must treat a hundred people for one to avoid the event. The common-outcome treatment drops the rate by 20 points (40% to 20%), so its NNT is 5. Same relative reduction; a 20-fold difference in how many people you must treat to help one. If all you were told was "50% reduction," you could not distinguish a treatment where 99 of 100 recipients get no benefit from one where 1 in 5 does — and that distinction is usually the whole decision.

## Build

The relative figure hides the baseline; spelling the treatment out as counts of real people restores it.

```text filename=--headline
HEADLINE — what '50% lower risk' means per 10000 people treated
--------------------------------------------------------------------------
  rare outcome (2% baseline):
    without treatment: 200 of 10000 have the event
    with treatment:    100 of 10000 have the event
    events prevented:  100  (so 9900 treated people got no benefit; NNT 100)
  common outcome (40% baseline):
    without treatment: 4000 of 10000 have the event
    with treatment:    2000 of 10000 have the event
    events prevented:  2000  (so 8000 treated people got no benefit; NNT 5)
```

Counting people is what makes the difference concrete. For the rare outcome, treating 10,000 people prevents 100 events — real, but it means 9,900 of the 10,000 took the treatment for nothing (they were never going to have the event, or they had it anyway). For the common outcome, the same 10,000 treated prevents 2,000 events. The relative reduction erased this entirely: divided by its own baseline, each treatment "removes half the risk," and the arithmetic is honest — half of 2% is 1%, half of 40% is 20%. What the relative framing cannot express is that half of a small thing is small. This is why the absolute reduction and the NNT are the numbers that belong in the abstract and the patient conversation: they are denominated in events prevented and people treated, the units the decision is actually made in, while the relative reduction is denominated in a baseline it then throws away.

<svg role="img" aria-label="Two bars each representing 10000 treated people: for the rare outcome a thin slice of 100 events is prevented; for the common outcome a large slice of 2000 events is prevented" viewBox="0 0 300 116" width="300" height="116">
  <text x="6" y="12" fill="var(--muted)" font-size="8">events prevented per 10000 treated — the same '50% reduction'</text>
  <text x="10" y="40" fill="var(--muted)" font-size="7">rare 2%→1%</text>
  <rect x="80" y="28" width="200" height="16" fill="none" stroke="var(--line)"/>
  <rect x="80" y="28" width="2" height="16" fill="var(--s2)"/><text x="86" y="40" fill="var(--muted)" font-size="6">100 prevented (9900 got no benefit)</text>
  <text x="10" y="76" fill="var(--muted)" font-size="7">common 40%→20%</text>
  <rect x="80" y="64" width="200" height="16" fill="none" stroke="var(--line)"/>
  <rect x="80" y="64" width="40" height="16" fill="var(--s1)"/><text x="124" y="76" fill="var(--muted)" font-size="6">2000 prevented</text>
  <text x="10" y="102" fill="var(--muted)" font-size="6">same headline; the prevented slice is 100 vs 2000 out of the same 10000</text>
</svg>
^ Out of an identical 10,000 people treated, the rare-outcome treatment prevents a sliver of 100 events while the common-outcome one prevents 2,000 — the "50% reduction" is the same, but the slice of people actually helped is what the absolute framing shows and the relative framing hides.

```python filename=modules/ai-for-science-and-data/code/riskframe-inter-01/riskframe.py:110-116 COMPLETE
    same_rrr = abs(mr["rrr"] - mc["rrr"]) < 1e-9
    print("  both treatments have the same relative reduction = %s (%.0f%% vs %.0f%%)"
          % (same_rrr, mr["rrr"] * 100, mc["rrr"] * 100))

    arr_differs = abs(mr["arr"] - mc["arr"]) > 0.1
    print("  the absolute reductions differ = %s (%.0f pt vs %.0f pt)"
          % (arr_differs, mr["arr"] * 100, mc["arr"] * 100))
```

## Definition of done

The self-test pins the identical relative reduction against the diverging absolute reduction and NNT.

```python filename=modules/ai-for-science-and-data/code/riskframe-inter-01/riskframe.py:118-124 COMPLETE
    rare_nnt_100 = abs(mr["nnt"] - 100) < 1e-9
    print("  rare-outcome NNT = %s (%g)" % (rare_nnt_100, mr["nnt"]))

    common_nnt_5 = abs(mc["nnt"] - 5) < 1e-9
    print("  common-outcome NNT = %s (%g)" % (common_nnt_5, mc["nnt"]))

    relative_alone_ambiguous = same_rrr and mr["nnt"] != mc["nnt"]
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the relative reduction is identical while the absolute reduction and NNT differ 20-fold
----------------------------------------------------------------------------------------------------
  both treatments have the same relative reduction = True (50% vs 50%)
  the absolute reductions differ = True (1 pt vs 20 pt)
  rare-outcome NNT = True (100)
  common-outcome NNT = True (5)
  identical RRR maps to different NNT -> relative framing is ambiguous = True (NNT 100 vs 5)
```

<svg role="img" aria-label="Number needed to treat: 100 people for the rare outcome versus 5 for the common outcome, both behind the same 50 percent relative reduction" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">number needed to treat behind the same '50% reduction'</text>
  <text x="10" y="38" fill="var(--muted)" font-size="7">rare (NNT 100)</text>
  <rect x="90" y="28" width="200" height="14" fill="var(--s2)"/><text x="94" y="39" fill="var(--panel)" font-size="7">treat 100 to prevent 1</text>
  <text x="10" y="68" fill="var(--muted)" font-size="7">common (NNT 5)</text>
  <rect x="90" y="58" width="10" height="14" fill="var(--s1)"/><text x="104" y="69" fill="var(--muted)" font-size="7">treat 5 to prevent 1</text>
  <text x="10" y="90" fill="var(--muted)" font-size="6">identical relative reduction, 20x difference in people treated per benefit</text>
</svg>
^ Behind the identical "50% reduction," the rare-outcome treatment needs 100 people treated per event prevented and the common-outcome one needs 5 — the NNT is the single number that separates them, and the relative figure cannot.

**Done means the framing effect is proven on real counts: both treatments show an identical 50% relative reduction, while the absolute reduction is 1 point (NNT 100) for the rare outcome and 20 points (NNT 5) for the common one — a 20-fold difference in benefit hidden by the same headline, so a relative reduction must always be reported with the absolute reduction and the number needed to treat.**

## Boss fight

Predict two ways this framing can still mislead even once you are reporting absolute numbers, because the choice of number and the choice of denominator both carry hidden judgments.

The first trap is that the same asymmetry runs the other way for harms, and reporting styles are often chosen — consciously or not — to make a case. A drug company describing a benefit reaches for the relative reduction ("cuts risk 50%") because it sounds largest; a report downplaying a side effect reaches for the absolute increase ("only 0.1 percentage points more") because *that* sounds smallest. The honest practice is to report benefits and harms in the *same* framing so they can be weighed against each other — an NNT of 100 to prevent one event alongside a number-needed-to-harm of, say, 50 for one serious side effect tells you the treatment harms twice as often as it helps, a comparison that "50% less risk, rare side effects" completely obscures. So the rule is not simply "use absolute numbers"; it is "use one consistent framing for everything being compared," because mixing relative-for-benefit with absolute-for-harm is the oldest trick in the deck.

The second trap is that the baseline risk is not one number — it varies across people — so a single NNT can hide who the treatment actually helps. The 2% baseline in the fixture is an average; the real population is a mix of high-risk people (maybe 10% baseline) and low-risk people (maybe 0.5%), and a treatment with a constant *relative* reduction gives the high-risk group a large absolute benefit (NNT ~20) and the low-risk group almost none (NNT ~400). Reporting one pooled NNT of 100 tells the high-risk patient the treatment is weaker than it is for them, and the low-risk patient that it is stronger. This is why absolute risk should be computed on the *relevant* baseline — the patient's own risk stratum, not the trial's average — and why the same treatment can be clearly worth it for one person and clearly not for another with the identical relative effect. Absolute framing fixes the "half of what?" problem only if the "what" is the baseline that actually applies, which turns the reporting question back into the base-rate question: whose risk, exactly, are we halving?

**Report benefits and harms in the same framing or you can rig the comparison (relative-for-benefit against absolute-for-harm is the classic distortion — pair the NNT with the number-needed-to-harm), and remember a single NNT rests on a single baseline: because absolute benefit scales with baseline risk, the same relative reduction helps a high-risk person far more than a low-risk one, so the absolute number is only honest when computed on the baseline that actually applies to the person deciding.**

## External resources

Gerd Gigerenzer's "Reckoning with Risk" and the risk-communication literature — why relative risk reductions systematically overstate benefit, and why absolute risk reduction and natural frequencies (counts of people) are the honest way to report medical evidence.

Documentation and primers on number needed to treat (NNT) and number needed to harm — how the reciprocal of the absolute risk reduction turns a rate change into a headcount, and why it must be computed on the relevant baseline risk.

The companion base-rate and significance-vs-size modules in this topic — the "half of what?" question is the base-rate question in another guise, and a relative reduction that is statistically real can still be practically negligible when its absolute size is tiny.
