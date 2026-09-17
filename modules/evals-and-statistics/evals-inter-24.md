---
id: evals-inter-24
title: Weight the eval by the production mix — or an eval set that over-samples easy cases reports a score you won't see
topic: evals-and-statistics
level: intermediate
status: ready
time: 17 min
summary: An eval's headline number is an average of per-category accuracies weighted by how many of each category the eval set contains — so the number depends on the eval set's mix, not just the model. If the eval set over-represents easy categories (cheaper to collect, or just not matched to production), the average leans on the high accuracies and comes out too high; the model hasn't changed, the eval merely asked more of the questions it is good at. The fix is to weight the same per-category accuracies by the production distribution, which answers the question you actually care about — the accuracy on the traffic the model will really face. On a fixture where the model is 95% accurate on easy inputs and 50% on hard ones, an eval set of 90 easy and 10 hard reports 0.905, while the true 50/50 production mix gives 0.725 — the eval overstates real-world accuracy by 0.18, entirely because it over-sampled the easy category.
eli5: If you test a student mostly on the easy chapters, they'll score high — but that score isn't what they'll get on the real exam that covers everything evenly. The student didn't get smarter; you just asked them more of what they knew. To predict the real exam, weight each chapter the way the real exam does, not the way your practice test happened to. An eval set that over-samples easy cases is that lopsided practice test.
---

## Why this module

An eval score is not a property of the model alone — it is the model's accuracy averaged over whatever mix of cases the eval set happens to contain, so a set that leans toward easy cases reports a number the model will never reproduce in production.

The headline accuracy an eval reports is a weighted average: the model's accuracy on each category of input, weighted by how many of that category the eval set holds. That weighting is the hidden variable. The model's per-category accuracies are fixed properties of the model, but the average of them depends entirely on the mix, and the mix is a property of the eval set, not the model. If the eval set was built by collecting whatever cases were cheap — and easy cases are usually cheaper and more plentiful — it over-represents the categories the model is good at, and the weighted average leans on those high accuracies. The result is a score inflated by exactly the gap between the eval's mix and the real one. The model performs identically; the eval merely gave it a disproportionate share of the questions it answers well, and a team can ship on a 90% eval and watch production land far lower.

**An eval's score is the per-category accuracy averaged over the eval set's mix, so a set that over-samples easy categories reports a number biased above real-world performance — the bias is in the mix, not the model.**

The fix is to average the same per-category accuracies by the *production* distribution instead of the eval set's counts. That production-weighted number answers the question you actually care about: what accuracy the model will deliver on the traffic it will really face. It uses the identical per-category numbers, just combined by the correct weights. When the eval set matches production the two agree and nothing changes; when it does not, the production-weighted number is the honest one and the gap between them measures how unrepresentative your eval set is. This module computes both and shows the eval overstate real-world accuracy, then attributes the entire gap to the mix.

## Concepts

**Per-category accuracy** is the model's accuracy within one category of input. These are fixed properties of the model and are identical across every way of weighting them.

**The weighted average** combines per-category accuracies by some set of weights. The weights, not the accuracies, determine whether the headline number is honest.

```python filename=modules/evals-and-statistics/code/evals-inter-24/stratify.py:41-44 COMPLETE
def weighted(accuracy, weights):
    """Accuracy averaged over categories weighted by `weights` (counts or a distribution)."""
    total = sum(weights.values())
    return sum(accuracy[c] * weights[c] for c in accuracy) / total
```

**The eval aggregate** weights by the eval set's category counts. If those counts over-sample easy cases, the aggregate is inflated.

**The production estimate** weights the same accuracies by the production distribution — the mix the model will actually face — and is the number that predicts real-world performance.

```python filename=modules/evals-and-statistics/code/evals-inter-24/stratify.py:47-54 COMPLETE
def eval_aggregate(data):
    """The eval's headline number: accuracy weighted by the eval set's category counts."""
    return weighted(data["accuracy"], data["eval_counts"])


def production_estimate(data):
    """The honest number: accuracy weighted by the production category distribution."""
    return weighted(data["accuracy"], data["production"])
```

**The gap is a measure of the eval set, not the model.** When the eval mix and production mix differ, the difference between the two averages quantifies how unrepresentative the eval set is.

**An eval score only predicts production when its category mix matches production's, so weight per-category accuracy by the real-world distribution — the eval set's own counts are the wrong weights whenever they were not deliberately matched to production.**

<svg role="img" aria-label="One set of per-category accuracies feeds two weightings: the eval's easy-heavy mix produces a high aggregate, the production mix produces a lower honest estimate" viewBox="0 0 300 120" width="300" height="120">
  <rect x="8" y="44" width="70" height="34" fill="none" stroke="var(--line)" stroke-width="1"/>
  <text x="12" y="40" fill="var(--muted)" font-size="8">accuracies</text>
  <text x="14" y="60" fill="var(--ink)" font-size="8">easy 0.95</text>
  <text x="14" y="72" fill="var(--ink)" font-size="8">hard 0.50</text>
  <line x1="78" y1="55" x2="150" y2="28" stroke="var(--s2)" stroke-width="1"/>
  <line x1="78" y1="67" x2="150" y2="92" stroke="var(--s1)" stroke-width="1"/>
  <text x="100" y="34" fill="var(--s2)" font-size="7">× eval 90/10</text>
  <text x="100" y="104" fill="var(--s1)" font-size="7">× prod 50/50</text>
  <rect x="152" y="18" width="90" height="18" fill="var(--s2)"/><text x="156" y="30" fill="var(--panel)" font-size="8">aggregate 0.905</text>
  <rect x="152" y="84" width="90" height="18" fill="var(--s1)"/><text x="156" y="96" fill="var(--panel)" font-size="8">estimate 0.725</text>
  <text x="8" y="116" fill="var(--muted)" font-size="8">same accuracies, two weight vectors → two different headline numbers</text>
</svg>
^ The identical per-category accuracies branch through two weightings — the eval's easy-heavy counts give 0.905, the production mix gives 0.725 — so the headline number is a choice of weights, not a fact about the model.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/evals-inter-24/stratify.py

The fixture is a model with per-category accuracy, an eval set that over-samples easy, and a 50/50 production mix.

```json filename=modules/evals-and-statistics/code/evals-inter-24/stratify.json:1-5 COMPLETE
{
  "_meta": "A model with a different accuracy on each category of input, plus two ways to weight those categories. accuracy is the model's per-category accuracy (the same numbers in every scenario -- the model does not change). eval_counts is how many of each category are in the EVAL SET; here it over-samples the easy category (90 easy, 10 hard). production is the mix the model will actually face in the real world (50/50 here). The eval's headline number is the accuracy averaged over the eval set's mix; but the number that matters is the accuracy averaged over the PRODUCTION mix. When the eval mix differs from production, the eval aggregate is a biased estimate of real-world performance -- and reweighting the same per-category accuracies by the production mix recovers the honest estimate. The gap comes entirely from the mix, not the model.",
  "accuracy": {"easy": 0.95, "hard": 0.50},
  "eval_counts": {"easy": 90, "hard": 10},
  "production": {"easy": 0.5, "hard": 0.5}
}
```

Run `--score` to compute both averages.

```text filename=--score
SCORE — eval-set aggregate vs production-weighted accuracy
------------------------------------------------------------
  per-category accuracy:  {'easy': 0.95, 'hard': 0.5}
  eval set mix:           {'easy': 90, 'hard': 10}  -> aggregate 0.905
  production mix:         {'easy': 0.5, 'hard': 0.5} -> estimate  0.725
  eval overstates by:     0.180
```

The model is 95% accurate on easy inputs and 50% on hard ones — those are fixed. The eval set is 90 easy and 10 hard, so its aggregate leans almost entirely on the 0.95 and comes out to 0.905: an impressive-looking 90.5%. But production is a 50/50 mix, and averaging the same two accuracies at 50/50 gives 0.725 — a 72.5% the model will actually deliver. The eval overstates real-world accuracy by 18 points. Nothing about the model differs between the two numbers; the eval simply asked 90% easy questions when reality asks 50%, and the average moved by exactly the amount that mismatch implies. Ship on the 0.905 and the 0.725 is the surprise waiting in production.

<svg role="img" aria-label="The eval-set aggregate is 0.905 while the production-weighted estimate is 0.725, a gap of 0.18 from the mix" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">reported accuracy (same model, two mixes)</text>
  <line x1="60" y1="20" x2="60" y2="78" stroke="var(--grid)" stroke-width="1"/>
  <line x1="60" y1="78" x2="285" y2="78" stroke="var(--grid)" stroke-width="1"/>
  <rect x="60" y="26" width="203" height="16" fill="var(--s2)"/><text x="64" y="38" fill="var(--panel)" font-size="8">eval (90/10 easy): 0.905</text>
  <rect x="60" y="50" width="163" height="16" fill="var(--s1)"/><text x="64" y="62" fill="var(--panel)" font-size="8">production (50/50): 0.725</text>
  <text x="228" y="62" fill="var(--muted)" font-size="7">← reality</text>
  <text x="60" y="94" fill="var(--muted)" font-size="8">the 0.18 gap is the eval's easy-heavy mix, not any change in the model</text>
</svg>
^ The eval bar reads 0.905 and the production bar 0.725, an 18-point gap produced entirely by the eval set's easy-heavy mix.

## Build

Where does the 0.18 come from? Run `--attribute`.

```text filename=--attribute
ATTRIBUTE — the gap is the mix, not the model (same accuracies, different weights)
------------------------------------------------------------------
  category   accuracy   eval weight   prod weight
  easy       0.95       0.90          0.50
  hard       0.50       0.10          0.50
  gap = sum(accuracy * (eval_weight - prod_weight)) = 0.180
------------------------------------------------------------------
  the accuracies are identical; only the weights differ, and that difference is the whole gap.
```

The accuracies column is the same for both averages — 0.95 and 0.50 — so the model contributes nothing to the difference. The only thing that changed is the weights: the eval put 0.90 on easy where production puts 0.50, and 0.10 on hard where production puts 0.50. Multiply each accuracy by how much its weight shifted and sum, and you get exactly the 0.18 gap: `0.95 × (0.90 − 0.50) + 0.50 × (0.10 − 0.50) = 0.38 − 0.20 = 0.18`. The eval over-weighted the category where the model scores 0.95 and under-weighted the one where it scores 0.50, and the reported score rose by precisely that reweighting. This is why "our eval says 90%" is not a claim about the model until you know the eval's mix — the number is half model, half sampling decision, and reweighting to production separates the two.

<svg role="img" aria-label="The easy category is weighted 0.90 in the eval but 0.50 in production; hard is 0.10 versus 0.50; the weight shift on the high-accuracy category drives the gap" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">category weights: eval (dark) vs production (light)</text>
  <text x="8" y="40" fill="var(--muted)" font-size="8">easy (.95)</text>
  <rect x="70" y="26" width="150" height="12" fill="var(--s2)"/><text x="224" y="36" fill="var(--muted)" font-size="7">eval 0.90</text>
  <rect x="70" y="40" width="83" height="12" fill="var(--s1)"/><text x="157" y="50" fill="var(--muted)" font-size="7">prod 0.50</text>
  <text x="8" y="82" fill="var(--muted)" font-size="8">hard (.50)</text>
  <rect x="70" y="66" width="17" height="12" fill="var(--s2)"/><text x="91" y="76" fill="var(--muted)" font-size="7">eval 0.10</text>
  <rect x="70" y="80" width="83" height="12" fill="var(--s1)"/><text x="157" y="90" fill="var(--muted)" font-size="7">prod 0.50</text>
  <text x="70" y="104" fill="var(--muted)" font-size="8">the eval over-weights the 0.95 category and under-weights the 0.50 one → +0.18</text>
</svg>
^ The eval over-weights the easy (0.95) category and under-weights the hard (0.50) one relative to production, and that reweighting of the fixed accuracies is exactly the 0.18 inflation.

## Definition of done

The self-test pins it: the eval aggregate is higher than the production estimate by a large amount, the mixes differ, the gap equals the accuracy-times-weight-difference sum, and reweighting recovers the honest number.

```python filename=modules/evals-and-statistics/code/evals-inter-24/stratify.py:90-103 COMPLETE
    eval_inflated = eval_aggregate(data) > production_estimate(data)
    print("  the eval aggregate is higher than the production estimate = %s (%.3f > %.3f)" % (eval_inflated, eval_aggregate(data), production_estimate(data)))

    gap_is_large = eval_aggregate(data) - production_estimate(data) > 0.1
    print("  the overstatement is large, not rounding = %s (%.3f)" % (gap_is_large, eval_aggregate(data) - production_estimate(data)))

    mix_differs = {c: ev[c] / ev_total for c in ev} != prod
    print("  the eval mix differs from production = %s" % mix_differs)

    gap_from_mix = abs((eval_aggregate(data) - production_estimate(data)) - sum(acc[c] * (ev[c] / ev_total - prod[c]) for c in acc)) < 1e-9
    print("  the gap equals sum(accuracy * weight difference) -- the mix, not the model = %s" % gap_from_mix)

    reweight_recovers = abs(weighted(acc, prod) - production_estimate(data)) < 1e-9
    print("  reweighting the same accuracies by the production mix recovers the honest number = %s (%.3f)" % (reweight_recovers, weighted(acc, prod)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the eval over-samples easy and inflates the score; reweighting to production recovers the honest one
--------------------------------------------------------------------------------------------------------------------
  the eval aggregate is higher than the production estimate = True (0.905 > 0.725)
  the overstatement is large, not rounding = True (0.180)
  the eval mix differs from production = True
  the gap equals sum(accuracy * weight difference) -- the mix, not the model = True
  reweighting the same accuracies by the production mix recovers the honest number = True (0.725)
```

**Done means the mix bias is proven and located: the eval reports 0.905 and production is 0.725, an 18-point gap that equals exactly sum(accuracy × weight-shift) — so the inflation is the eval set's easy-heavy mix, and reweighting the identical accuracies by the production distribution recovers the honest 0.725.**

## Boss fight

Reweighting fixed the aggregate, but predict what it cannot fix, and the subtler bias hiding inside a single category. It is tempting to think matching the category mix makes the eval representative.

Reweighting corrects the *proportions* of categories you measured, but it cannot invent accuracy for a category the eval barely sampled. If production is 50% hard but the eval had only 10 hard examples, the hard-category accuracy of 0.50 is estimated from 10 items — a wide confidence interval — so even after reweighting, the production estimate inherits that imprecision. Reweighting shifts the point estimate to the right mix; it does not add the data you would need to measure each category precisely. So the two fixes are separate: match the mix to remove the bias, and sample each category enough to shrink its variance. A stratified eval does both by design — deliberately including enough of every category to estimate its accuracy well, then combining by production weights — which is why "stratify your eval set" is the standard advice, not merely "match the proportions."

The deeper trap is that categories are only as fine as you defined them, and bias hides inside a category you treated as uniform. If "hard" secretly contains a sub-population the model fails completely and another it handles, and production draws mostly from the failing sub-population, then even a perfectly production-weighted "hard" accuracy is wrong, because it averaged over a within-category mix that also does not match production. This is the same bias one level down, and it recurses: representativeness is required not just across your chosen categories but within them, all the way to the level of variation that actually affects accuracy. In practice you cannot stratify infinitely, so the discipline is to identify the axes of variation that move accuracy most — difficulty, language, input length, source, demographic slice — stratify on those, and treat the eval score as an estimate whose representativeness is bounded by the coarsest mismatch you left uncorrected. An eval number is a claim about a distribution; it is only as trustworthy as the match between that distribution and the one you will actually serve.

```python filename=modules/evals-and-statistics/code/evals-inter-24/stratify.py:71-81 COMPLETE
def attribute_view(data):
    acc, ev, prod = data["accuracy"], data["eval_counts"], data["production"]
    ev_total = sum(ev.values())
    print("ATTRIBUTE — the gap is the mix, not the model (same accuracies, different weights)")
    print("-" * 66)
    print("  category   accuracy   eval weight   prod weight")
    for c in acc:
        print("  %-8s   %.2f       %.2f          %.2f" % (c, acc[c], ev[c] / ev_total, prod[c]))
    print("  gap = sum(accuracy * (eval_weight - prod_weight)) = %.3f" % sum(acc[c] * (ev[c] / ev_total - prod[c]) for c in acc))
    print("-" * 66)
    print("  the accuracies are identical; only the weights differ, and that difference is the whole gap.")
```

**An eval score is per-category accuracy averaged over the eval set's mix, so it predicts production only when that mix matches — weight the same per-category accuracies by the production distribution to remove the bias, but also sample each category enough to estimate it precisely (stratify, don't just reweight), and remember the correction recurses: representativeness is required within categories too, bounded by the coarsest mismatch you leave uncorrected.**

## External resources

Any survey-sampling or machine-learning-evaluation reference on stratified sampling and post-stratification / reweighting — the formal methods for building a representative test set and for correcting a mismatched one by weighting to the target distribution.

Writing on dataset shift and evaluation under distribution mismatch (covariate shift, importance weighting) — the general framing of "your eval distribution is not your deployment distribution" and how reweighting estimates deployment performance.

The companion "macro-average an imbalanced eval" and "average over the right population" modules — macro-averaging is the equal-weight special case of choosing weights, and averaging over the right population is the same reweighting principle applied wherever a mix is silently assumed.
