---
id: block-inter-01
title: Block the randomization on a strong covariate — simple randomization does not guarantee balance in a small sample, and a chance imbalance confounds the estimate
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: An A/B estimate is the treated mean minus the control mean, and it equals the true effect only when the two arms are balanced on everything that affects the outcome. Randomization is what usually buys that balance — but "usually" is doing a lot of work. Randomization makes the arms balanced in expectation and near-certain to balance in a large sample; in a small sample, any single random split can, by luck, put more of a strong covariate in one arm, and then that arm's outcome is higher for a reason that has nothing to do with the treatment. On the fixture four units have baseline 100 and four have baseline 0 (the baseline determines most of the outcome), the true treatment effect is 5, and a simple split that happened to give treatment three high-baseline units and control three low-baseline ones has arm baselines of 75 versus 25 — an imbalance of 50 — so it estimates the effect at 55, the true 5 plus that 50. Nothing about the randomization was done wrong; it drew an unlucky split, which small samples do at a rate you cannot ignore. Blocking removes the luck by design: stratify the units into blocks by the covariate (high-baseline and low-baseline) and randomize to treatment and control within each block, so each arm is guaranteed the same covariate composition — 50 versus 50 here — and the confounder cannot be unevenly split. The blocked split recovers the true effect of 5. The rule: when a covariate strongly predicts the outcome and the sample is small, block the randomization on it rather than trusting a single random split to balance it.
eli5: Imagine testing whether a new fertilizer helps plants, using eight plants — four already big and healthy, four small and weak. If you split them into two groups by flipping a coin, you might by bad luck put three of the big plants in the fertilizer group and three of the small ones in the no-fertilizer group. Then the fertilizer group grows more, but mostly because it started with the big plants, not because of the fertilizer — you can't tell the two apart. The fix is to deliberately put two big and two small plants in each group before you start, so both groups begin equally healthy and any difference at the end is really the fertilizer. Splitting fairly by hand beats hoping a coin flip happens to split fairly, especially with only a few plants.
---

## Why this module

Randomization is sold as the thing that makes an experiment trustworthy: assign at random and the arms are comparable, so the difference in outcomes is the treatment. That is true on average and true in the limit, and it is why randomized experiments are the gold standard. But it hides a caveat that bites hardest exactly when you have the fewest units to spare.

The caveat is that randomization guarantees balance in expectation, not in any single experiment. Over infinitely many re-randomizations the arms match on every covariate; in the one split you actually ran, a strong predictor of the outcome can land lopsided by pure luck. In a large sample the law of large numbers makes that luck negligible. In a small sample — a few dozen units, a handful of clusters, an eval with tens of items — an unlucky split is common, and an unlucky split of a strong covariate is a confounder you built by accident.

This module makes that concrete with eight units whose baseline drives the outcome. A simple split happens to stack the treatment arm with high-baseline units, and the estimate comes out at 55 against a true effect of 5 — the 50-point covariate gap masquerading as treatment. Then it blocks the randomization on the baseline, forces each arm to the same composition, and recovers the 5. The lesson is that in a small sample you should not leave balance on a known strong covariate to chance.

**Randomization balances the arms in expectation, but the experiment you ran is one draw, and in a small sample one draw can imbalance a strong covariate badly enough to swamp the effect — so a known strong predictor should be balanced by design, not by luck.**

## Concepts

Start from what "balanced arms" buys. The estimate is the treated mean minus the control mean. Decompose each unit's outcome into the part explained by its covariate and the part from the treatment; then the treated-minus-control difference is the true treatment effect plus the difference in the covariate's contribution between the arms. If the arms have the same covariate composition, that second term is zero and the estimate is clean. If they do not, the estimate carries the covariate gap.

Randomization's job is to make that gap zero — and it does, on average. Across all possible random assignments, the expected covariate mean is the same in both arms, so the expected bias is zero. But you do not run all possible assignments; you run one. The covariate mean in your treated arm is a random draw, and its spread around the true mean shrinks with sample size. In a large sample the draw is tightly concentrated and any imbalance is tiny; in a small sample the draw is wide, and a sizable imbalance on a strong covariate happens often enough to matter.

That is the whole failure. With eight units split four and four, there are many equally-likely assignments, and a good fraction of them put three or four of the high-baseline units in one arm. Each such split is a perfectly valid randomization that nonetheless hands you a confounded estimate — the covariate is unevenly divided, so the arm difference is the effect plus a gap that has nothing to do with the treatment.

Blocking removes the draw's variance on the covariate you block. Sort the units into strata by the covariate — high-baseline and low-baseline — and randomize within each stratum separately, assigning half of each to treatment. Now the treated arm has exactly the same number of high- and low-baseline units as the control arm, no matter how the within-stratum coin lands, so the covariate mean is identical in both arms by construction. You have spent the randomness only on the part that does not affect the outcome, and forced balance on the part that does.

<svg role="img" aria-label="Eight units, four high-baseline and four low-baseline. Under the simple split, the treatment arm gets three high and one low while the control arm gets one high and three low — visibly skewed. The arm baseline means are 75 and 25." viewBox="0 0 640 210">
<text x="160" y="26" fill="var(--ink)" font-size="12" text-anchor="middle">treatment arm</text>
<rect x="60" y="40" width="40" height="40" fill="var(--s2)" opacity="0.6" stroke="var(--line)"/>
<rect x="105" y="40" width="40" height="40" fill="var(--s2)" opacity="0.6" stroke="var(--line)"/>
<rect x="150" y="40" width="40" height="40" fill="var(--s2)" opacity="0.6" stroke="var(--line)"/>
<rect x="195" y="40" width="40" height="40" fill="var(--panel)" stroke="var(--line)"/>
<text x="150" y="98" fill="var(--muted)" font-size="10" text-anchor="middle">3 high + 1 low</text>
<text x="150" y="114" fill="var(--s2)" font-size="11" text-anchor="middle">mean baseline 75</text>
<text x="480" y="26" fill="var(--ink)" font-size="12" text-anchor="middle">control arm</text>
<rect x="380" y="40" width="40" height="40" fill="var(--s2)" opacity="0.6" stroke="var(--line)"/>
<rect x="425" y="40" width="40" height="40" fill="var(--panel)" stroke="var(--line)"/>
<rect x="470" y="40" width="40" height="40" fill="var(--panel)" stroke="var(--line)"/>
<rect x="515" y="40" width="40" height="40" fill="var(--panel)" stroke="var(--line)"/>
<text x="467" y="98" fill="var(--muted)" font-size="10" text-anchor="middle">1 high + 3 low</text>
<text x="467" y="114" fill="var(--s2)" font-size="11" text-anchor="middle">mean baseline 25</text>
<text x="320" y="160" fill="var(--ink)" font-size="11" text-anchor="middle">the arms differ on the covariate by 50 before any treatment</text>
<text x="320" y="180" fill="var(--muted)" font-size="10" text-anchor="middle">(shaded = high baseline, empty = low baseline)</text>
</svg>
^ A valid random split can still stack the high-baseline units into one arm, so the arms differ on the covariate by 50 before the treatment does anything.

**Randomization spends its balancing power across all possible splits, but you only get one split, and in a small sample that one split can leave a strong covariate lopsided — blocking forces the balance instead of averaging toward it.**

## Worked example

The fixture is eight units, four with baseline 100 and four with baseline 0, a true effect of 5, and the two assignments.

```json filename=modules/evals-and-statistics/code/block-inter-01/block.json:3-9 COMPLETE
  "true_effect": 5.0,
  "units": [
    {"id": "u1", "baseline": 100}, {"id": "u2", "baseline": 100}, {"id": "u3", "baseline": 100}, {"id": "u4", "baseline": 100},
    {"id": "u5", "baseline": 0}, {"id": "u6", "baseline": 0}, {"id": "u7", "baseline": 0}, {"id": "u8", "baseline": 0}
  ],
  "simple_treatment": ["u1", "u2", "u3", "u5"],
  "blocked_treatment": ["u1", "u2", "u5", "u6"]
```

The arm split and the covariate balance of an arm are simple.

```python filename=modules/evals-and-statistics/code/block-inter-01/block.py:30-34 COMPLETE
def arms(data, treatment_ids):
    """Split the units into the treated arm (ids in treatment_ids) and the control arm (the rest)."""
    treated = [u for u in data["units"] if u["id"] in treatment_ids]
    control = [u for u in data["units"] if u["id"] not in treatment_ids]
    return treated, control
```

```python filename=modules/evals-and-statistics/code/block-inter-01/block.py:37-39 COMPLETE
def mean_baseline(units):
    """The average covariate value of an arm -- the thing that must match between arms for a clean estimate."""
    return sum(u["baseline"] for u in units) / len(units)
```

The estimate is the treated-minus-control outcome, where the outcome is the baseline plus the effect when treated.

```python filename=modules/evals-and-statistics/code/block-inter-01/block.py:42-48 COMPLETE
def estimate(data, treatment_ids):
    """Treated-mean minus control-mean of the outcome (baseline + true_effect when treated)."""
    treated, control = arms(data, treatment_ids)
    eff = data["true_effect"]
    treated_mean = sum(u["baseline"] + eff for u in treated) / len(treated)
    control_mean = sum(u["baseline"] for u in control) / len(control)
    return treated_mean - control_mean
```

The unlucky simple split imbalances the covariate and inflates the estimate.

```text filename=block.py --simple
SIMPLE — one random split that happened to imbalance the covariate
------------------------------------------------------------
  treatment ids: ['u1', 'u2', 'u3', 'u5']
  mean baseline: treated 75.0 vs control 25.0   (imbalance 50.0)
  estimated effect = 55.0   (true 5.0)
------------------------------------------------------------
  the treated arm is higher-baseline, so its outcome is up for a non-treatment reason
```

The treated arm averages baseline 75 against the control's 25 — a 50-point head start — so the estimate is 55, the true 5 plus that 50. The blocked split balances the arms.

```text filename=block.py --blocked
BLOCKED — randomize within high- and low-baseline strata
------------------------------------------------------------
  treatment ids: ['u1', 'u2', 'u5', 'u6']
  mean baseline: treated 50.0 vs control 50.0   (imbalance 0.0)
  estimated effect = 5.0   (true 5.0)
------------------------------------------------------------
  each arm has the same baseline mix, so the difference is the treatment alone
```

Two high and two low in each arm gives both a baseline mean of 50, so the covariate contributes equally to both and cancels, leaving exactly the treatment effect of 5. The figure lines the two designs up.

<svg role="img" aria-label="A comparison of the two designs. Under simple, treated baseline is 75, control 25, and the estimate is 55 against a true 5. Under blocked, treated and control baseline are both 50 and the estimate is 5." viewBox="0 0 640 210">
<text x="160" y="26" fill="var(--ink)" font-size="12" text-anchor="middle">simple split</text>
<text x="160" y="54" fill="var(--muted)" font-size="11" text-anchor="middle">treated baseline 75</text>
<text x="160" y="74" fill="var(--muted)" font-size="11" text-anchor="middle">control baseline 25</text>
<rect x="60" y="88" width="200" height="34" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="5"/>
<text x="160" y="110" fill="var(--s2)" font-size="12" text-anchor="middle">estimate 55 (true 5)</text>
<text x="160" y="150" fill="var(--muted)" font-size="10" text-anchor="middle">50 of the 55 is covariate imbalance</text>
<text x="480" y="26" fill="var(--ink)" font-size="12" text-anchor="middle">blocked split</text>
<text x="480" y="54" fill="var(--muted)" font-size="11" text-anchor="middle">treated baseline 50</text>
<text x="480" y="74" fill="var(--muted)" font-size="11" text-anchor="middle">control baseline 50</text>
<rect x="380" y="88" width="200" height="34" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="5"/>
<text x="480" y="110" fill="var(--s1)" font-size="12" text-anchor="middle">estimate 5 (true 5)</text>
<text x="480" y="150" fill="var(--muted)" font-size="10" text-anchor="middle">covariate cancels; only the effect remains</text>
</svg>
^ The same units and the same true effect give 55 under the unlucky simple split and 5 under blocking — the whole difference is whether the covariate was balanced.

**The estimate of 55 is not a measurement error but a correct estimate of the wrong quantity — the effect plus the covariate gap — and blocking changes what is being estimated by removing the gap.**

## Build

The self-test pins the mechanism: the simple split imbalances the covariate, its estimate is biased by exactly that imbalance, and the blocked split balances the covariate and recovers the truth.

```python filename=modules/evals-and-statistics/code/block-inter-01/block.py:83-92 COMPLETE
    s_gap = mean_baseline(s_treated) - mean_baseline(s_control)
    simple_imbalances = abs(s_gap) > 1e-9
    print("  the simple split imbalances the covariate = %s (treated %.1f vs control %.1f)" % (simple_imbalances, mean_baseline(s_treated), mean_baseline(s_control)))

    s_est = estimate(data, data["simple_treatment"])
    simple_biased = abs(s_est - eff) > 1e-9
    print("  the simple estimate is biased = %s (%.1f vs true %.1f)" % (simple_biased, s_est, eff))

    bias_equals_imbalance = abs((s_est - eff) - s_gap) < 1e-9
    print("  the bias equals the covariate imbalance = %s (%.1f == %.1f)" % (bias_equals_imbalance, s_est - eff, s_gap))
```

The remaining flags confirm the blocked split balances the covariate and recovers the true effect. All five pass.

```text filename=block.py --check
SELF-TEST — the simple split imbalances the covariate and biases the estimate by exactly that imbalance, while the blocked split balances it and recovers the true effect
----------------------------------------------------------------------------------------------------------------
  the simple split imbalances the covariate = True (treated 75.0 vs control 25.0)
  the simple estimate is biased = True (55.0 vs true 5.0)
  the bias equals the covariate imbalance = True (50.0 == 50.0)
  the blocked split balances the covariate = True (treated 50.0 vs control 50.0)
  the blocked estimate recovers the true effect = True (5.0)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  simple_imbalances=True  simple_biased=True  bias_equals_imbalance=True  blocked_balances=True  blocked_correct=True
```

**"The bias equals the covariate imbalance" is the whole story in one flag: the estimate is off by 50 because the covariate is off by 50, so balancing the covariate is not a refinement but the fix.**

## Definition of done

You are done when a covariate that strongly predicts the outcome is balanced across arms by design — blocked or stratified randomization — whenever the sample is small enough that a single random split could imbalance it, rather than trusting one draw to come out even.

The design is straightforward: identify the covariates most predictive of the outcome (a pre-experiment baseline of the metric is usually the strongest), sort units into strata on them, and randomize within each stratum so every arm gets the same composition. This buys two things at once — no chance imbalance on the blocked covariate, and lower variance, because the between-stratum variation is removed from the comparison. When there are too many covariates to stratify on jointly, the common alternatives are the same idea in another form: pairwise or rerandomization matching before assignment, or covariate adjustment (regression, or CUPED) after, which corrects for whatever imbalance the randomization left. Two cautions keep it honest. Block on covariates chosen before seeing outcomes, not after — blocking is a design decision, and choosing strata to make a result come out is just p-hacking. And blocking helps only for covariates you measured and predicted; it does nothing for an unmeasured confounder, which is why large-sample randomization (where all covariates, measured or not, balance in probability) remains the ideal and blocking is what you reach for when the sample is too small to rely on that alone.

<svg role="img" aria-label="Blocking: eight units sorted into a high-baseline stratum and a low-baseline stratum, and within each stratum half are randomized to treatment and half to control, so both arms end up with two high and two low." viewBox="0 0 640 200">
<rect x="40" y="40" width="240" height="50" fill="var(--panel)" stroke="var(--line)" stroke-width="1" rx="6"/>
<text x="160" y="60" fill="var(--ink)" font-size="10" text-anchor="middle">high-baseline stratum (4 units)</text>
<text x="160" y="78" fill="var(--muted)" font-size="9" text-anchor="middle">randomize 2 → treat, 2 → control</text>
<rect x="40" y="110" width="240" height="50" fill="var(--panel)" stroke="var(--line)" stroke-width="1" rx="6"/>
<text x="160" y="130" fill="var(--ink)" font-size="10" text-anchor="middle">low-baseline stratum (4 units)</text>
<text x="160" y="148" fill="var(--muted)" font-size="9" text-anchor="middle">randomize 2 → treat, 2 → control</text>
<line x1="280" y1="65" x2="360" y2="80" stroke="var(--s1)" stroke-width="1"/>
<line x1="280" y1="135" x2="360" y2="120" stroke="var(--s1)" stroke-width="1"/>
<rect x="360" y="75" width="240" height="50" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="480" y="95" fill="var(--ink)" font-size="10" text-anchor="middle">each arm: 2 high + 2 low</text>
<text x="480" y="113" fill="var(--muted)" font-size="9" text-anchor="middle">covariate balanced by construction</text>
</svg>
^ Sort into strata by the covariate and randomize within each, so both arms inherit the same high/low composition no matter how the within-stratum coins fall.

**Blocking spends the randomness only on the part of the assignment that does not affect the outcome and pins the rest, so a strong known covariate is balanced by construction instead of being left to a small-sample coin flip.**

## Boss fight

Your turn: shrink the covariate's effect and watch the bias shrink with it, then grow it and watch the bias dominate. In the fixture the baseline is the whole outcome, so a 50-point imbalance is a 50-point bias. Change the outcome model so the baseline contributes only a fraction — imagine the outcome is baseline times 0.1 plus the treatment — and the same imbalanced split now biases the estimate by only 5, comparable to the effect. The lesson is that blocking pays off in proportion to how strongly the blocked covariate predicts the outcome: block the strong predictors, because balancing a covariate that barely moves the outcome buys almost nothing, while balancing the dominant one is the difference between a clean estimate and a confounded one.

Then confront blocking's boundary, the thing it cannot do. Add an unmeasured covariate — a second baseline you did not record — and let it also drive the outcome and land imbalanced in the simple split. Blocking on the measured baseline does nothing for it, so the blocked estimate is still biased by the unmeasured imbalance. This is the honest limit: blocking only balances what you measured and chose to block, whereas large-sample randomization balances everything, measured or not, in probability, because the law of large numbers acts on every covariate at once. So blocking is not a replacement for randomization or for sample size; it is what you add when the sample is too small for randomization alone to reliably balance the covariates you already know matter. The full defense is randomize (to balance the unknowns in probability), block the strong known covariates (to balance them for sure in a small sample), and adjust for residual imbalance afterward.

**Blocking balances only the covariates you measured and chose, so it cuts the small-sample luck on your known strong predictors but leaves the unmeasured ones to randomization — which is why blocking augments randomization for the knowns rather than replacing it for the unknowns.**

## External resources

Any design-of-experiments text (for example Montgomery's "Design and Analysis of Experiments") derives randomized block designs and shows the variance reduction and bias protection blocking provides over completely randomized designs.

The clinical-trials literature on stratified and permuted-block randomization explains how trials balance strong prognostic factors across arms in small studies, and why they still randomize within strata rather than assigning deterministically.

Writing on rerandomization and covariate balance in experiments (Morgan and Rubin's work on rerandomization) formalizes when to reject an unlucky random split and re-draw, a close cousin of blocking for the same small-sample balance problem.
