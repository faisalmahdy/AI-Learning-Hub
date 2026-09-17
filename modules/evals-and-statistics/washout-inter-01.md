---
id: washout-inter-01
title: A crossover test needs a washout — the first treatment's carryover biases the second period's measurement
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: Comparing two treatments across separate groups wastes power, because units differ from each other far more than the treatments differ and that between-unit variance drowns the signal. A crossover design fixes this by making each unit its own control — give it treatment A in period 1 and treatment B in period 2, compare period 2 to period 1 within the unit, and the unit's baseline subtracts out, so units with wildly different baselines all contribute the same clean within-unit difference. The danger the sequence introduces is carryover: if treatment A leaves a residual — a learned habit, a lingering effect, a warmed cache — then when B is measured in period 2, some of what is measured is A's leftover, not B, so the within-unit difference is the true effect plus the carryover, and it is biased. The baseline still cancels, so the estimate is precise (every unit agrees) and precisely wrong. On the fixture the true effect of B over A is 10 − 4 = 6 and carryover is half the previous treatment's effect: without a washout every unit's within-unit estimate is 8 — the true 6 plus the carryover of A into B's period, 0.5 × 4 = 2 — identical across units of baselines 100, 130, 90. A washout period is the fix: leave enough time (or reset enough state) that the first treatment's residual has decayed to zero before the second is measured, so period 2 measures B alone, the carryover term vanishes, and every unit's estimate is the true 6. The rule: a crossover buys precision by reusing each unit, and the price is that the design must guarantee each measurement is uncontaminated by the last — which is what the washout enforces.
eli5: Suppose you want to know which of two energy drinks makes you run faster, and instead of using two different people (who run at very different speeds anyway) you test the same person twice — once on drink A, once on drink B — and compare their two times. Smart: it cancels out how fast that person naturally is. But if you give drink A and then, five minutes later, drink B, the caffeine from A is still in them when you measure B, so B's time is really "B plus leftover A" and looks better than it is. The fix is to wait long enough between the two drinks that the first one has fully worn off before you test the second. Then each drink is measured clean, and the comparison is fair.
---

## Why this module

Within-subject designs — crossover, repeated measures — are the most powerful comparison you can run when they apply, because they eliminate the single biggest source of noise: the differences between units. The same person, server, or model measured under both conditions is a far tighter comparison than two different ones.

That power comes with a specific liability that between-subjects designs never have. When one unit experiences both treatments in sequence, the treatments are no longer isolated — the first can leave something behind that contaminates the measurement of the second. The design that cancels between-unit noise so beautifully introduces a within-unit bias, and the washout period is what keeps that bias out.

**A crossover buys precision by measuring each unit twice, and the cost is that each measurement must be clean of the last — which the washout enforces.**

## Concepts

Start with why the crossover is worth it. In a between-subjects comparison you split units into two groups, give one A and one B, and compare group means. But units vary — baselines of 100, 130, 90 — and that spread is usually much larger than the treatment effect you are chasing, so the effect is buried in baseline noise.

A crossover measures every unit under both treatments and compares within the unit. Because you subtract the unit's own period-1 value from its period-2 value, the baseline appears in both and cancels exactly. Every unit, whatever its baseline, contributes the same within-unit difference — the noise from unit-to-unit variation is simply gone. That is the whole appeal.

Carryover is the failure the sequence creates. The design assumes period 2 measures treatment B on a unit in the same state it was before treatment A. That assumption breaks whenever A leaves a residual: a drug still in the bloodstream, a skill the user learned, a cache A warmed that B now benefits from. When B is measured, part of the measurement is A's leftover, so the within-unit difference is the true B-minus-A effect plus the carryover.

Note the specific character of this bias. Because the baseline still cancels, every unit reports the same contaminated estimate — the design looks impeccably consistent, and the consistency is exactly what makes the bias easy to trust. Precise and wrong is more dangerous than noisy and wrong.

The washout removes it. Insert a gap between the two treatments long enough that the first's residual decays to nothing — or, where the residual is state rather than time, reset that state. Then period 2 measures B on a clean unit, the carryover term is zero, and the within-unit difference is the true effect. Counterbalancing the order (half the units B-then-A) helps average out a symmetric carryover but does not remove a treatment-specific one; only the washout guarantees each measurement is uncontaminated.

**Carryover biases every unit's estimate by the same amount, so the crossover stays precise while becoming wrong — and the washout is what makes each period's measurement clean.**

<svg role="img" aria-label="Two designs. Between-subjects: three units with baselines 100, 130, 90 spread widely, so the small effect is buried in baseline noise. Crossover: each unit measured twice, and the within-unit difference is the same clean value because the baseline cancels." viewBox="0 0 440 160">
<rect x="0" y="0" width="440" height="160" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">why crossover: the baseline cancels within a unit</text>
<text x="20" y="48" fill="var(--muted)" font-size="10">between-subjects</text>
<circle cx="150" cy="44" r="4" fill="var(--s1)"></circle>
<circle cx="240" cy="44" r="4" fill="var(--s1)"></circle>
<circle cx="110" cy="44" r="4" fill="var(--s1)"></circle>
<text x="270" y="48" fill="var(--s1)" font-size="9">baselines spread wide &#8594; effect buried</text>
<text x="20" y="96" fill="var(--muted)" font-size="10">crossover</text>
<text x="110" y="96" fill="var(--s2)" font-size="10">diff 6</text>
<text x="180" y="96" fill="var(--s2)" font-size="10">diff 6</text>
<text x="250" y="96" fill="var(--s2)" font-size="10">diff 6</text>
<text x="110" y="120" fill="var(--s2)" font-size="9">every within-unit difference is the same &#8594; effect clear</text>
</svg>
^ Between-subjects, the baselines' spread hides the effect; within a unit, the baseline subtracts out and every unit reports the same difference — precision the washout must keep unbiased.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/evals-and-statistics/code/washout-inter-01/washout.py

The fixture has three units of very different baselines, treatment effects 4 and 10, and carryover of half the previous effect.

```json filename=modules/evals-and-statistics/code/washout-inter-01/washout.json:4-7 COMPLETE
  "effect_a": 4,
  "effect_b": 10,
  "carryover_fraction": 0.5,
  "unit_baselines": [100, 130, 90]
```

Period 1 measures A on a fresh unit; period 2 measures B plus the carryover of A.

```python filename=modules/evals-and-statistics/code/washout-inter-01/washout.py:35-37 COMPLETE
def period1(baseline, d):
    """Period 1 measures treatment A on a fresh unit: baseline plus A's effect, no carryover."""
    return baseline + d["effect_a"]
```

```python filename=modules/evals-and-statistics/code/washout-inter-01/washout.py:40-42 COMPLETE
def period2(baseline, d, carryover_fraction):
    """Period 2 measures treatment B, plus a fraction of A's effect carried over from period 1."""
    return baseline + d["effect_b"] + carryover_fraction * d["effect_a"]
```

Run it with the carryover in place and every unit agrees on the wrong answer.

```text filename=washout.py --nowashout
NO-WASHOUT — within-unit estimate of B minus A per unit (true effect = 6)
----------------------------------------------------------------
  baseline 100:  period1(A)=104  period2(B)=112  ->  estimate 8
  baseline 130:  period1(A)=134  period2(B)=142  ->  estimate 8
  baseline  90:  period1(A)=94  period2(B)=102  ->  estimate 8
----------------------------------------------------------------
  every unit agrees (baseline cancels), but each estimate is high by the carryover
```

Baselines of 100, 130, and 90 all vanish in the subtraction — that is the crossover working — and all three units report 8. But the true effect is 6; the extra 2 is the carryover of A (0.5 × 4) leaking into B's period. Three units in perfect agreement, all wrong by the same amount.

<svg role="img" aria-label="One unit's two periods. Period 1 is a bar for treatment A. Period 2 is a taller bar for treatment B with a small extra segment on top marked carryover from A. The within-unit difference measures B plus the carryover, not B alone." viewBox="0 0 440 170">
<rect x="0" y="0" width="440" height="170" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">one unit: carryover inflates period 2's measurement</text>
<line x1="60" y1="140" x2="400" y2="140" stroke="var(--line)"></line>
<rect x="90" y="100" width="60" height="40" fill="var(--s2)"></rect>
<text x="92" y="156" fill="var(--muted)" font-size="9">period 1: A</text>
<rect x="250" y="60" width="60" height="64" fill="var(--s2)"></rect>
<text x="252" y="156" fill="var(--muted)" font-size="9">period 2: B</text>
<rect x="250" y="46" width="60" height="14" fill="var(--s1)"></rect>
<text x="314" y="55" fill="var(--s1)" font-size="9">+ carryover of A</text>
<line x1="150" y1="100" x2="250" y2="100" stroke="var(--grid)" stroke-dasharray="3 3"></line>
<text x="120" y="128" fill="var(--ink)" font-size="9">estimate = period2 &#8722; period1 = 8 (true 6)</text>
</svg>
^ Period 2 measures B plus the residual of A; the within-unit difference therefore overshoots the true effect by exactly that residual.

## Build

The washout sets the carryover to zero — period 2 measures B on a clean unit.

```python filename=modules/evals-and-statistics/code/washout-inter-01/washout.py:45-47 COMPLETE
def within_estimate(baseline, d, carryover_fraction):
    """The crossover estimate of B minus A for one unit: its period-2 minus its period-1 measurement."""
    return period2(baseline, d, carryover_fraction) - period1(baseline, d)
```

```text filename=washout.py --washout
WASHOUT — within-unit estimate of B minus A per unit (true effect = 6)
----------------------------------------------------------------
  baseline 100:  period1(A)=104  period2(B)=110  ->  estimate 6
  baseline 130:  period1(A)=134  period2(B)=140  ->  estimate 6
  baseline  90:  period1(A)=94  period2(B)=100  ->  estimate 6
----------------------------------------------------------------
  A's residual has decayed, so each unit's estimate is the true effect
```

With the residual gone, period 2 is baseline + 10, period 1 is baseline + 4, and every unit's difference is the true 6. The crossover's baseline-cancellation is untouched — the design was always precise — and now it is also unbiased.

<svg role="img" aria-label="Three estimates of the effect against the true value of 6. The no-washout estimate is 8, the washout estimate is 6 sitting on the true line. A note says the gap of 2 is the carryover." viewBox="0 0 440 150">
<rect x="0" y="0" width="440" height="150" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">within-unit estimate of B &#8722; A (true = 6)</text>
<line x1="60" y1="120" x2="400" y2="120" stroke="var(--line)"></line>
<line x1="60" y1="62" x2="400" y2="62" stroke="var(--grid)" stroke-dasharray="3 3"></line>
<text x="404" y="65" fill="var(--muted)" font-size="9">6</text>
<rect x="110" y="43" width="60" height="77" fill="var(--s1)"></rect>
<text x="112" y="37" fill="var(--s1)" font-size="10">no washout 8</text>
<rect x="260" y="62" width="60" height="58" fill="var(--s2)"></rect>
<text x="264" y="56" fill="var(--s2)" font-size="10">washout 6</text>
<text x="110" y="140" fill="var(--muted)" font-size="9">the gap of 2 is the carryover (0.5 &#215; 4)</text>
</svg>
^ The washout estimate sits on the true effect; the no-washout estimate stands two above it, and that two is the carryover the washout removed.

The self-test shows the design cancels baseline either way, but only the washout is unbiased.

```python filename=modules/evals-and-statistics/code/washout-inter-01/washout.py:85-92 COMPLETE
    nowashout_biased = nw[0] != truth
    print("  no-washout estimate is biased (not the true effect) = %s (%g vs %d)" % (nowashout_biased, nw[0], truth))

    washout_recovers = wo[0] == truth
    print("  washout estimate recovers the true effect = %s (%g == %d)" % (washout_recovers, wo[0], truth))

    bias_is_carryover = abs((nw[0] - truth) - cf * d["effect_a"]) < 1e-9
    print("  the bias equals the carryover (fraction times A's effect) = %s (%g == %g)" % (bias_is_carryover, nw[0] - truth, cf * d["effect_a"]))
```

```text filename=washout.py --check
SELF-TEST — the design cancels baseline under both, but no-washout is biased by exactly the carryover while washout recovers the true effect
----------------------------------------------------------------------------------------------------------------
  every unit gives the same within-unit estimate (baseline cancels) = True (no-washout [8.0, 8.0, 8.0], washout [6.0, 6.0, 6.0])
  no-washout estimate is biased (not the true effect) = True (8 vs 6)
  washout estimate recovers the true effect = True (6 == 6)
  the bias equals the carryover (fraction times A's effect) = True (2 == 2)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  baseline_cancels=True  nowashout_biased=True  washout_recovers=True  bias_is_carryover=True
```

**baseline_cancels being True for both is the trap: the crossover's clean, unanimous agreement across units is present with or without the bias, so consistency across units is not evidence the estimate is right.**

## Definition of done

You can explain why a crossover design is more powerful than between-subjects — it cancels the between-unit baseline variance that otherwise swamps the effect.

You can define carryover and give a concrete residual for a given domain (a drug's half-life, a learned habit, a warmed cache), and explain why it biases the second period's measurement.

You can say why the carryover bias is especially deceptive: it is the same for every unit, so the estimate is precise and consistent even while it is wrong.

You can name the fix and its two forms — a time washout for a decaying residual, a state reset for a stateful one — and why counterbalancing order helps with symmetric carryover but does not replace a washout.

## Boss fight

You A/B test two recommendation algorithms by showing each user algorithm A for a week, then algorithm B the next week, and comparing per-user engagement. B wins by a comfortable margin and every user cohort agrees, so you ship B.

First: name the carryover mechanism that a week of algorithm A could leave behind that would inflate B's week, and explain why the fact that "every cohort agrees" is not the reassurance it feels like.

Then: you cannot pause the product for a washout week. Give two ways to get an unbiased estimate anyway — one based on the order you assign treatments, one based on which week you compare — and state exactly what each assumes about the carryover for it to work.

Finally: suppose the carryover is not symmetric — A leaves a strong habit but B leaves almost none. Explain why counterbalancing the order (half B-then-A) reduces but does not remove the bias in that case, and what that tells you about when a crossover is simply the wrong design and you should pay for the between-subjects test instead.

## External resources

Any design-of-experiments text's chapter on crossover trials (common in clinical pharmacology) formalizes carryover and the washout period, and derives why counterbalancing handles a symmetric carryover but not a treatment-specific one.

Guidance on within-subject online experiments (for example writing on switchback tests, where a system is toggled between treatments over time) is the software analogue: it treats carryover between periods explicitly and uses randomized switch timing as the industrial substitute for a clean washout.
