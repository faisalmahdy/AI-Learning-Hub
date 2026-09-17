---
id: winnerscurse-inter-01
title: Re-measure the winning variant on a fresh holdout — the one you picked for the highest observed lift is biased upward
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: Run several variants, measure each one's lift, ship the best — the obvious way to pick a winner, and it systematically overstates how good the winner is. The reason is selection: every measured lift is the true lift plus noise, and when you take the maximum observed lift, you select not just for a high true effect but for a high noise draw; the variant that caught a lucky upward error is more likely to top the chart than an equally-good variant that got unlucky. So the winner is disproportionately a variant whose noise was positive, and its observed lift is inflated relative to its true lift — the winner's curse — meaning the number you used to justify the launch is, on average, too high. Two damaging things follow: the winner underdelivers (you shipped expecting the observed lift and get the lower true lift, so the launch looks like a regression against its own forecast even when it is a real improvement), and the winner may not even be the best variant (a genuinely superior variant that drew unlucky noise can lose to a mediocre one that drew lucky noise). The more variants compared, the stronger the effect, because the maximum of many noisy estimates is pulled further above the truth. The fix separates selection from estimation: use the experiment to select the winner, but re-measure the chosen variant on a fresh holdout that had no part in the selection, whose estimate is unbiased because the winner was not chosen for its holdout noise. On a fixture where four variants have true effects 2, 1, 3, 2 and observed 2, 5, 3, 4, selecting the highest observed picks v2 at +5 though its true effect is only 1 (inflated by 4), missing v3, the genuinely best (true +3) — and a holdout re-measure of v2 reveals the true +1.
eli5: Imagine a class takes a pop quiz and you crown "the smartest kid" as whoever scored highest on that one quiz. The top scorer is usually a genuinely good student — but they also probably got a little lucky that day (guessed a couple right, happened to study the exact topics). So their quiz score overstates how they'll do in general. If you then bet that they'll score just as high next time, you'll be disappointed: they'll drift back toward their real level. And sometimes the actual smartest kid had an off day and didn't win the quiz at all. The fix is to give the crowned winner a second, separate test — one that didn't decide the crown — to see their true level before you bet on it.
---

## Why this module

Choosing a winner from an experiment feels like reading off an answer: measure each variant, pick the top number, ship it. The catch is that the top number is not an ordinary sample of the winner's effect — it is the maximum of several noisy samples, and the maximum is a biased thing. This bias, the winner's curse, shows up everywhere you select the best of many measured options: A/B/n tests, model checkpoints picked by validation score, features ranked by measured importance, funds chosen by past return. Anywhere you take a max over noisy estimates, the winner's estimate is inflated, and if you trust it you overpromise.

The mechanism is worth making precise because it is not obvious. Each variant's observed lift is its true lift plus noise. Selecting the highest observed lift favors variants with high true effects — good — but it also favors variants with high noise, because a lucky upward error helps you win the max just as much as real quality does. The winner is therefore enriched for positive noise, and positive noise means the observed number sits above the truth. It is not that the experiment was run wrong; the arithmetic of "take the maximum" builds the bias in.

The consequence is a launch that underdelivers against its own forecast, and sometimes the wrong variant shipped entirely. This module runs the selection on four variants whose true effects are known and shows the winner's estimate inflated and the true best missed.

**Select the winning variant on the experiment but re-estimate its effect on a fresh holdout, rather than trusting the observed lift of the highest-scoring variant, because taking the maximum over noisy estimates selects for positive noise — so the winner's observed lift is biased upward and it underdelivers, and a holdout that did not drive the selection gives an unbiased estimate.**

## Concepts

The fixture is four variants, each with its true effect (what it delivers long-run) and its observed effect (this experiment's noisy estimate = true + noise). v2 has a small true effect (1) but a big lucky noise draw (+4), so its observed effect (5) tops the chart.

```json filename=modules/evals-and-statistics/code/winnerscurse-inter-01/winnerscurse.json:3-8 COMPLETE
  "variants": [
    {"id": "v1", "true_effect": 2, "observed_effect": 2},
    {"id": "v2", "true_effect": 1, "observed_effect": 5},
    {"id": "v3", "true_effect": 3, "observed_effect": 3},
    {"id": "v4", "true_effect": 2, "observed_effect": 4}
  ]
```

The naive rule selects the highest observed effect; the truly-best variant is the highest true effect — and these can differ.

```python filename=modules/evals-and-statistics/code/winnerscurse-inter-01/winnerscurse.py:32-39 COMPLETE
def selected_by_observed(variants):
    """The variant the naive rule ships: highest observed effect (ties broken by id)."""
    return max(variants, key=lambda v: (v["observed_effect"], v["id"]))


def true_best(variants):
    """The variant with the highest true effect (ties broken by id)."""
    return max(variants, key=lambda v: (v["true_effect"], v["id"]))
```

The inflation is how far the winner's observed effect exceeds its true effect, and the holdout — a fresh measurement that had no part in the selection — recovers the true effect unbiased.

```python filename=modules/evals-and-statistics/code/winnerscurse-inter-01/winnerscurse.py:42-49 COMPLETE
def inflation(variant):
    """How much the observed effect overstates the true effect."""
    return variant["observed_effect"] - variant["true_effect"]


def holdout_estimate(variant):
    """A fresh holdout, not used for selection, measures the true effect (unbiased)."""
    return variant["true_effect"]
```

<svg role="img" aria-label="Four variants with true effects marked and observed effects as bars; v2 has a small true effect but the tallest observed bar due to noise, and is selected" viewBox="0 0 320 120">
  <line x1="30" y1="100" x2="300" y2="100" stroke="var(--line)" stroke-width="1"/>
  <g font-size="7.5" fill="var(--muted)">
  <rect x="45" y="60" width="30" height="40" fill="var(--s1)"/><text x="50" y="112">v1</text><text x="52" y="56" fill="var(--ink)">o2</text>
  <rect x="105" y="0" width="30" height="100" fill="var(--s2)"/><text x="110" y="112">v2</text><text x="112" y="-2" fill="var(--ink)">o5</text>
  <rect x="165" y="40" width="30" height="60" fill="var(--s1)"/><text x="170" y="112">v3</text><text x="172" y="36" fill="var(--ink)">o3</text>
  <rect x="225" y="20" width="30" height="80" fill="var(--s1)"/><text x="230" y="112">v4</text><text x="232" y="16" fill="var(--ink)">o4</text>
  </g>
  <line x1="45" y1="60" x2="75" y2="60" stroke="var(--ink)" stroke-width="2"/>
  <line x1="105" y1="80" x2="135" y2="80" stroke="var(--ink)" stroke-width="2"/>
  <line x1="165" y1="40" x2="195" y2="40" stroke="var(--ink)" stroke-width="2"/>
  <line x1="225" y1="60" x2="255" y2="60" stroke="var(--ink)" stroke-width="2"/>
  <text x="100" y="14" font-size="7" fill="var(--s2)">selected (tallest observed)</text>
</svg>
^ Bars are observed effects; the dark tick on each is the true effect. v2's observed bar is tallest (it drew lucky noise) so it is selected, but its true tick is the lowest — while v3's true tick is highest yet its observed bar lost. Selecting the tallest bar picks the luckiest, not the best.

**Taking the maximum observed effect selects for the sum of quality and luck, so the winner is enriched for luck — its observed number sits above its true effect, by construction.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the variant-selection step of an experimentation platform, reduced to four variants so every effect is checkable by hand.

Run `--variants` to see the true and observed effects and the selection.

```text filename=winnerscurse.py --variants
  variant  true   observed   selected?
  v1       2      2
  v2       1      5          <- SHIP
  v3       3      3
  v4       2      4
  the naive rule ships the highest observed effect: v2 (+5 observed)
```

The observed column drives the decision, and its maximum is v2 at +5, so v2 ships. But look at the true column: v2's true effect is only 1 — it topped the chart on a +4 noise draw, not on merit. Meanwhile v3, whose true effect is the highest at 3, shows an observed 3 and loses the selection. The rule picked the luckiest variant, not the best one.

Now `--curse` quantifies the damage.

```text filename=winnerscurse.py --curse
  selected winner v2: observed +5, true +1 -> inflated by 4
  holdout re-measure of v2 reveals: +1 (the true effect)
  truly-best variant: v3 (true +3) -- NOT the one selected
  shipping on the observed lift forecasts +5 but delivers +1
```

The winner's observed +5 overstates its true +1 by 4 — that is the winner's curse in one number. If you launch v2 on the strength of the +5 you measured, production delivers +1, and the launch reads as a 4-point miss against its own forecast even though v2 is a genuine (if small) improvement. And you shipped the wrong variant: v3 would have delivered +3. A holdout re-measure of v2 — a fresh experiment that did not pick v2 — reports +1, the truth, because v2 was not selected for its holdout noise.

**Selecting on the observed max shipped v2 with a +5 forecast that delivers +1, and passed over the truly-best v3 — the estimate is inflated and the choice is wrong, both from taking a maximum over noise.**

## Build

The self-test asserts the mechanism: the winner is the observed max, its observed effect overstates its true effect, the bias is positive, and the winner is not the truly-best variant.

```python filename=modules/evals-and-statistics/code/winnerscurse-inter-01/winnerscurse.py:86-96 COMPLETE
    winner_is_observed_max = win["observed_effect"] == max(v["observed_effect"] for v in variants)
    print("  the naive rule ships the variant with the maximum observed effect = %s (%s, +%d)" % (winner_is_observed_max, win["id"], win["observed_effect"]))

    winner_estimate_inflated = win["observed_effect"] > win["true_effect"]
    print("  the winner's observed effect overstates its true effect = %s (+%d > +%d)" % (winner_estimate_inflated, win["observed_effect"], win["true_effect"]))

    inflation_positive = inflation(win) > 0
    print("  the selection bias is positive (winner's curse direction) = %s (inflated by %d)" % (inflation_positive, inflation(win)))

    winner_not_true_best = win["true_effect"] < best["true_effect"]
    print("  the selected winner is NOT the truly-best variant = %s (true +%d < best +%d, which is %s)" % (winner_not_true_best, win["true_effect"], best["true_effect"], best["id"]))
```

<svg role="img" aria-label="The winner v2 shown three ways: observed +5 tall bar, true +1 short bar, and holdout +1 short bar matching true; with an arrow showing the drop from selection estimate to holdout" viewBox="0 0 320 110">
  <line x1="30" y1="90" x2="300" y2="90" stroke="var(--line)" stroke-width="1"/>
  <rect x="50" y="20" width="50" height="70" fill="var(--s2)"/><text x="58" y="103" font-size="7.5" fill="var(--muted)">observed</text><text x="66" y="16" font-size="7.5" fill="var(--ink)">+5</text>
  <rect x="140" y="76" width="50" height="14" fill="var(--s1)"/><text x="150" y="103" font-size="7.5" fill="var(--muted)">true</text><text x="158" y="72" font-size="7.5" fill="var(--ink)">+1</text>
  <rect x="230" y="76" width="50" height="14" fill="var(--s1)"/><text x="232" y="103" font-size="7.5" fill="var(--muted)">holdout</text><text x="248" y="72" font-size="7.5" fill="var(--ink)">+1</text>
  <path d="M 100 30 Q 170 20 255 74" fill="none" stroke="var(--ink)" stroke-width="1" stroke-dasharray="3 2"/>
  <text x="120" y="40" font-size="7" fill="var(--muted)">inflated by 4; holdout reveals the truth</text>
</svg>
^ The winner's selection estimate (+5) towers over its true effect (+1); the holdout, which did not choose the winner, measures +1 — matching the truth. The holdout undoes the winner's curse.

Running the check confirms every clause, including that the holdout is lower than the selection estimate and unbiased.

```text filename=winnerscurse.py --check
  the naive rule ships the variant with the maximum observed effect = True (v2, +5)
  the winner's observed effect overstates its true effect = True (+5 > +1)
  the selection bias is positive (winner's curse direction) = True (inflated by 4)
  the selected winner is NOT the truly-best variant = True (true +1 < best +3, which is v3)
  the holdout re-measure is lower than the selection estimate = True (+1 < +5)
  the holdout estimate equals the true effect (unbiased) = True (+1)
```

**The check ties the inflated estimate and the wrong choice to selecting on the max, and shows the holdout recovering the unbiased truth — selection and estimation split, as they must be.**

## Definition of done

Two properties close it. The winner's observed effect must be inflated (biased upward by selection) and the holdout re-measure must be both lower than the selection estimate and equal to the true effect (unbiased). The holdout being unbiased is the whole fix: it is a measurement that had no hand in choosing the winner, so it cannot be enriched for the winner's noise.

```python filename=modules/evals-and-statistics/code/winnerscurse-inter-01/winnerscurse.py:98-102 COMPLETE
    holdout_lower_than_observed = holdout_estimate(win) < win["observed_effect"]
    print("  the holdout re-measure is lower than the selection estimate = %s (+%d < +%d)" % (holdout_lower_than_observed, holdout_estimate(win), win["observed_effect"]))

    holdout_is_unbiased = holdout_estimate(win) == win["true_effect"]
    print("  the holdout estimate equals the true effect (unbiased) = %s (+%d)" % (holdout_is_unbiased, holdout_estimate(win)))
```

Three clarifications keep this calibrated. First, the bias grows with the number of variants and shrinks with sample size: more variants means the maximum is taken over more noise draws (larger inflation), and larger samples mean less noise per estimate (smaller inflation) — so the curse is worst exactly when you A/B/n-test many variants on modest traffic. Second, the fix is not to stop selecting on the experiment — that is what experiments are for — but to stop trusting the winning experiment's number as the effect estimate; re-measure the chosen variant on fresh data (a holdout split reserved before selection, or a confirmatory follow-up experiment), and report that number as the launch forecast. This is the same discipline as never reporting training-set accuracy: the data that chose the winner cannot also fairly grade it. Third, if a full re-run is too costly, statistical shrinkage (empirical-Bayes or similar) can correct the winner's estimate toward the mean by an amount that depends on the noise, giving a de-biased estimate without a fresh experiment — but a clean holdout is the simplest and most defensible correction.

<svg role="img" aria-label="A rising curve: the winner's inflation grows as the number of variants compared increases, from small at 2 variants to large at many" viewBox="0 0 320 110">
  <line x1="35" y1="20" x2="35" y2="90" stroke="var(--line)" stroke-width="1"/>
  <line x1="35" y1="90" x2="300" y2="90" stroke="var(--line)" stroke-width="1"/>
  <text x="2" y="26" font-size="7.5" fill="var(--muted)">inflation</text>
  <text x="150" y="106" font-size="7.5" fill="var(--muted)">number of variants compared →</text>
  <path d="M 50 82 Q 130 60 290 30" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <circle cx="50" cy="82" r="3" fill="var(--s1)"/><text x="42" y="78" font-size="7" fill="var(--s1)">2 → small</text>
  <circle cx="290" cy="30" r="3" fill="var(--s2)"/><text x="230" y="28" font-size="7" fill="var(--s2)">many → large</text>
</svg>
^ The winner's curse grows with how many variants you compare, because the maximum is taken over more noise draws — and it shrinks with sample size. It bites hardest when many variants share modest traffic, exactly the common A/B/n setup, which is why the holdout re-measure matters most there.

**Done means the winner's estimate is inflated and a holdout that did not drive the selection recovers the unbiased true effect — selection on the experiment, estimation on fresh data, so the launch forecast is honest.**

## Boss fight

Your team runs an experimentation platform where PMs test 5–10 variants per experiment and ship whichever has the highest measured lift. Over a year, the sum of the shipped experiments' measured lifts predicts a huge gain in the top-line metric, but the actual top-line moved far less. Leadership suspects the metric is broken. What is the more likely explanation, and what change to the platform fixes it?

The more likely explanation is the winner's curse compounding across every experiment. Each experiment ships the variant with the highest observed lift out of 5–10, and taking the maximum over that many noisy estimates selects for positive noise, so every shipped variant's measured lift is biased upward — it overstates the true effect. Summing those inflated per-experiment lifts produces a forecast far above what the variants actually deliver, which is exactly the gap leadership sees: the metric is not broken, the per-experiment estimates are systematically too high because selection and estimation were done on the same data. The bias is worst here precisely because the platform tests many variants (larger max-over-noise) on per-experiment traffic that is often modest. The fix is to build holdout re-estimation into the platform: after an experiment selects a winner, automatically re-measure that winner on a fresh holdout — either a slice of traffic reserved and not used in the selection, or a short confirmatory follow-up — and report that holdout number as the official launch effect, not the selection number. Roll up the holdout estimates, not the selection estimates, into the top-line forecast, and the forecast will match reality. For teams that cannot afford a re-run per experiment, apply shrinkage to the winner's estimate as a cheaper de-biasing step. Either way, the platform must stop treating the number that chose the winner as the winner's effect.

## External resources

The statistical literature on the winner's curse and post-selection inference (and its economics origin in auction theory) — the formal result that the maximum of noisy estimates is upward-biased, and the empirical-Bayes shrinkage corrections for it.

Kohavi, Tang, and Xu, *Trustworthy Online Controlled Experiments*, on the winner's curse and the "reproducibility" of experiment results — the industry treatment showing shipped-variant lifts are inflated and recommending holdouts and replication to get honest launch estimates.
