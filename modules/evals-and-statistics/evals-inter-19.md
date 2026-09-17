---
id: evals-inter-19
title: Bootstrap a confidence interval — a single eval score hides how much it would move on other cases
topic: evals-and-statistics
level: intermediate
status: ready
time: 19 min
summary: An eval gives you one number — the model passed 6 of 8 cases, so the score is 0.75 — and reported alone it pretends to be exact. But you evaluated 8 particular cases; a different 8 would give a different score, and 8 cases pin down almost nothing. The point estimate carries no sense of that wobble, so a 0.75 from 8 cases and a 0.75 from 8000 look identical on a dashboard while meaning wildly different things. The bootstrap measures the wobble with no formula: resample the cases with replacement to a same-size set, score it, repeat thousands of times, and take the 2.5th and 97.5th percentiles of the resampled scores as a 95% interval. It works for any metric, not just proportions. On 8 cases at 0.75, the bootstrap interval is about [0.375, 1.0] — enormous; the point clears a 0.6 bar but the interval reaches down to 0.375, so you cannot conclude the model is above it.
eli5: If you taste three spoonfuls of soup and two are salty, you would not swear the whole pot is exactly two-thirds salty — three spoons is too few to be sure. The bootstrap is like re-tasting the same three spoons in every combination to see how much your guess could jump around. When the guess jumps a lot, you know your few spoons cannot pin down the pot, and you say so instead of pretending.
---

## Why this module

A single eval score is an estimate from a handful of cases, and reporting it without an interval hides the one thing a decision needs: how much it would change on a different sample.

You ran the eval on some fixed set of cases and got 0.75. That number is the pass rate *on those cases*, but what you actually want to know is the pass rate in general — and the cases you happened to pick are a small, noisy sample of everything the model might face. With only 8 cases, swapping even one changes the score by 0.125, so the true rate could be far from 0.75 in either direction. The point estimate says nothing about this. It looks the same whether it came from 8 cases or 8000, which is exactly the information a decision-maker must not lose.

**A point estimate from a small eval is one draw from a wide distribution, and printing it alone erases the width that tells you whether to trust it.**

The bootstrap recovers that width with no distributional assumptions and no closed-form formula. Resample the cases with replacement into a new same-size eval, score it, and repeat thousands of times; the spread of those scores is how much the metric would wobble, and its percentiles are a confidence interval. This module bootstraps a small eval and shows the interval swallow a decision the point estimate looked ready to make.

## Concepts

The **point estimate** is the metric on your actual cases — here the mean of the pass/fail scores, 0.75.

A **bootstrap replica** is a new eval set of the same size drawn from your cases *with replacement*, so some cases appear twice and others not at all. Scoring many replicas simulates "what if I'd drawn a different sample of cases," using only the data you have.

The **bootstrap interval** is the 2.5th and 97.5th percentiles of the replicas' scores — a 95% confidence interval. Its great virtue is generality: it works for a mean, an F1, a win rate, a latency percentile, anything, because it resamples the metric itself rather than assuming a formula.

Because resampling is random, the interval is **seeded** for reproducibility — the same seed gives the same interval every run, so a documented result is checkable. This is the seed-the-RNG discipline applied to a statistic.

The interval's width is driven by sample size. Eight cases give a very wide interval because each case carries so much weight; thousands of cases give a tight one. So the bootstrap does not just add error bars — it tells you, honestly, when your eval is too small to conclude anything.

**The bootstrap turns "what if the cases were different" into a computation you can run on the cases you have, and its width is the sample size speaking.**

The loop is the same three moves repeated: draw a resample, score it, collect the score — and the collected pile's percentiles are the interval.

<svg role="img" aria-label="The bootstrap loop: from the cases, draw a resample, score it, add to a pile of scores, repeat; the pile's 2.5 and 97.5 percentiles are the interval" viewBox="0 0 300 100" width="300" height="100">
  <rect x="15" y="35" width="45" height="22" fill="none" stroke="var(--line)" stroke-width="1"/><text x="22" y="49" fill="var(--muted)" font-size="8">8 cases</text>
  <line x1="60" y1="46" x2="85" y2="46" stroke="var(--s2)" stroke-width="1"/>
  <rect x="85" y="35" width="50" height="22" fill="none" stroke="var(--s2)" stroke-width="1"/><text x="90" y="49" fill="var(--muted)" font-size="7">resample</text>
  <line x1="135" y1="46" x2="160" y2="46" stroke="var(--s2)" stroke-width="1"/>
  <rect x="160" y="35" width="40" height="22" fill="none" stroke="var(--s2)" stroke-width="1"/><text x="167" y="49" fill="var(--muted)" font-size="8">score</text>
  <line x1="200" y1="46" x2="225" y2="46" stroke="var(--s2)" stroke-width="1"/>
  <rect x="225" y="35" width="55" height="22" fill="var(--s2)" opacity="0.4"/><text x="230" y="49" fill="var(--ink)" font-size="7">pile of 2000</text>
  <path d="M252,57 Q252,80 120,80 Q92,80 92,59" fill="none" stroke="var(--s2)" stroke-width="1" stroke-dasharray="3 2"/>
  <text x="120" y="94" fill="var(--muted)" font-size="7">repeat; then take the 2.5% and 97.5% percentiles of the pile</text>
</svg>
^ Draw, score, collect, repeat — the interval is just the percentile spread of the pile of resampled scores.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/evals-inter-19/bootstrap.py

The fixture is eight per-case scores, a seed, a resample count, and a decision threshold.

```json filename=modules/evals-and-statistics/code/evals-inter-19/scores.json:1-6 COMPLETE
{
  "_meta": "Per-case pass/fail from an eval run: 1 is a pass, 0 a fail, so the point estimate of the pass rate is the mean. seed fixes the bootstrap's random resampling so the interval is reproducible. resamples is how many bootstrap replicas to draw. threshold is a bar we want to decide the model clears (e.g. 'is it above 60%?'). The question: how much would the pass rate wobble on a different sample of cases, and can we conclude it clears the bar?",
  "scores": [1, 1, 1, 0, 1, 1, 0, 1],
  "seed": 0,
  "resamples": 2000,
  "threshold": 0.6
}
```

A replica draws n cases with replacement; the interval sorts the replicas' means and reads the 2.5% and 97.5% percentiles, all from a seeded RNG.

```python filename=modules/evals-and-statistics/code/evals-inter-19/bootstrap.py:45-57 COMPLETE
def resample(scores, rng):
    """One bootstrap replica: draw len(scores) cases with replacement."""
    n = len(scores)
    return [scores[rng.randrange(n)] for _ in range(n)]


def bootstrap_interval(scores, seed, b):
    """The 95% percentile interval of the resampled means, using a seeded RNG for reproducibility."""
    rng = random.Random(seed)
    means = sorted(mean(resample(scores, rng)) for _ in range(b))
    lo = means[int(0.025 * b)]
    hi = means[int(0.975 * b) - 1]
    return lo, hi
```

The resample view prints a few replicas and their scores before reporting the interval over all of them.

```python filename=modules/evals-and-statistics/code/evals-inter-19/bootstrap.py:62-72 COMPLETE
def resample_view(data):
    scores, seed, b = data["scores"], data["seed"], data["resamples"]
    rng = random.Random(seed)
    print("RESAMPLE — a few bootstrap replicas of %s (point %.3f)" % (scores, mean(scores)))
    print("-" * 62)
    for i in range(5):
        r = resample(scores, rng)
        print("  replica %d: %s  score %.3f" % (i + 1, r, mean(r)))
    lo, hi = bootstrap_interval(scores, seed, b)
    print("-" * 62)
    print("  across %d replicas the 95%% interval is [%.3f, %.3f]." % (b, lo, hi))
```

Run `--resample` to see the method in action.

```text filename=--resample
RESAMPLE — a few bootstrap replicas of [1, 1, 1, 0, 1, 1, 0, 1] (point 0.750)
--------------------------------------------------------------
  replica 1: [0, 0, 1, 1, 1, 0, 1, 1]  score 0.625
  replica 2: [1, 0, 1, 1, 1, 1, 1, 1]  score 0.875
  replica 3: [1, 1, 1, 1, 1, 1, 1, 0]  score 0.875
  replica 4: [1, 0, 1, 1, 1, 1, 1, 1]  score 0.875
  replica 5: [0, 1, 1, 1, 0, 1, 1, 0]  score 0.625
--------------------------------------------------------------
  across 2000 replicas the 95% interval is [0.375, 1.000].
```

Each replica is a different draw from the same 8 cases — some pull the two failures twice, some miss them, and their scores range from 0.625 to 0.875 in just these five. Across 2000 replicas the scores spread from 0.375 to 1.0. That spread is the estimate of how much your 0.75 would jump on a different sample of cases.

<svg role="img" aria-label="Bootstrap replicas' scores spread from 0.375 to 1.0 around the point estimate 0.75" viewBox="0 0 300 110" width="300" height="110">
  <line x1="20" y1="70" x2="285" y2="70" stroke="var(--grid)" stroke-width="1"/>
  <text x="15" y="85" fill="var(--muted)" font-size="7">0</text>
  <text x="270" y="85" fill="var(--muted)" font-size="7">1.0</text>
  <path d="M110,70 Q150,20 210,45 Q240,58 285,68" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
  <text x="150" y="18" fill="var(--s2)" font-size="7">spread of 2000 replica scores</text>
  <line x1="219" y1="30" x2="219" y2="70" stroke="var(--ink)" stroke-width="1.5" stroke-dasharray="3 2"/>
  <text x="205" y="28" fill="var(--ink)" font-size="7">point 0.75</text>
  <line x1="119" y1="70" x2="119" y2="82" stroke="var(--s1)" stroke-width="1.5"/><text x="105" y="98" fill="var(--s1)" font-size="7">0.375</text>
  <line x1="285" y1="70" x2="285" y2="82" stroke="var(--s1)" stroke-width="1.5"/><text x="262" y="98" fill="var(--s1)" font-size="7">1.0</text>
</svg>
^ The resampled scores form a broad hump from 0.375 to 1.0 around the point at 0.75 — that hump is the sampling uncertainty the single number 0.75 concealed.

## Build

Turn it into a decision with `--interval`.

```text filename=--interval
INTERVAL — point estimate, 95% bootstrap interval, and the 0.60 decision
--------------------------------------------------------------
  cases:            8
  point estimate:   0.750
  95% interval:     [0.375, 1.000]   width 0.625
  above 0.60?  point says yes, but the interval reaches down to 0.375
--------------------------------------------------------------
  the point clears the bar; the interval cannot rule out being below it.
```

The point estimate 0.75 sits above the 0.6 bar, so on the point alone you would ship. But the 95% interval runs from 0.375 to 1.0 — its lower bound is well below 0.6, so the eval is fully consistent with a true pass rate under the bar. You have not shown the model clears 0.6; you have shown 8 cases cannot tell. The honest report is "0.75, 95% CI [0.375, 1.0] — inconclusive against 0.6," and the fix is more cases, which narrows the interval.

<svg role="img" aria-label="The 0.6 threshold sits inside the bootstrap interval [0.375, 1.0], so the point 0.75 above it is not conclusive" viewBox="0 0 300 100" width="300" height="100">
  <line x1="20" y1="55" x2="285" y2="55" stroke="var(--grid)" stroke-width="1"/>
  <rect x="119" y="50" width="166" height="10" fill="var(--s2)" opacity="0.5"/>
  <text x="150" y="46" fill="var(--s2)" font-size="7">95% interval [0.375, 1.0]</text>
  <circle cx="219" cy="55" r="4" fill="var(--ink)"/><text x="205" y="74" fill="var(--ink)" font-size="7">point 0.75</text>
  <line x1="179" y1="38" x2="179" y2="72" stroke="var(--s1)" stroke-width="1.5" stroke-dasharray="3 2"/>
  <text x="165" y="88" fill="var(--s1)" font-size="7">bar 0.6</text>
  <text x="30" y="92" fill="var(--muted)" font-size="8">the bar falls inside the interval → not proven above it</text>
</svg>
^ The 0.6 bar lands inside the interval, so even though the point sits to its right, the eval cannot rule out a true rate on the wrong side of the bar.

## Definition of done

The self-test pins the method and the consequence: the point is the mean, the interval contains it, the interval is wide, the point clears the threshold while the lower bound does not, and the seeded interval reproduces exactly.

```python filename=modules/evals-and-statistics/code/evals-inter-19/bootstrap.py:96-108 COMPLETE
    point_is_mean = point == mean(scores)
    print("  the point estimate is the mean score = %s (%.3f)" % (point_is_mean, point))

    interval_contains_point = lo <= point <= hi
    print("  the interval contains the point estimate = %s ([%.3f, %.3f])" % (interval_contains_point, lo, hi))

    interval_is_wide = (hi - lo) > 0.3
    print("  the interval is wide (small eval) = %s (width %.3f)" % (interval_is_wide, hi - lo))

    lower_below_threshold = lo < thr < point
    print("  the point clears %.2f but the lower bound does not = %s (%.3f < %.2f < %.3f)" % (thr, lower_below_threshold, lo, thr, point))

    reproducible = bootstrap_interval(scores, seed, b) == (lo, hi)
    print("  the seeded interval reproduces exactly = %s" % reproducible)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the point hides the spread; the bootstrap interval is wide and reproducible under the seed
--------------------------------------------------------------------------------------------------------
  the point estimate is the mean score = True (0.750)
  the interval contains the point estimate = True ([0.375, 1.000])
  the interval is wide (small eval) = True (width 0.625)
  the point clears 0.60 but the lower bound does not = True (0.375 < 0.60 < 0.750)
  the seeded interval reproduces exactly = True
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  point_is_mean=True  interval_contains_point=True  interval_is_wide=True  lower_below_threshold=True  reproducible=True
```

**Done means the uncertainty is a number, not a caveat: the point 0.75 comes with a bootstrap interval [0.375, 1.0] that straddles the 0.6 bar, so "above 0.6" is provably unproven on 8 cases.**

## Boss fight

The bootstrap gave a wide interval here. Predict whether running more resamples — say 200,000 instead of 2000 — would narrow it. It is tempting to think more resamples means more precision.

They will not narrow it, and confusing the two knobs is the classic bootstrap mistake. More resamples make the interval *smoother and more stable* — the percentiles stop jittering between runs — but they do not add information about the pass rate, because every replica is still drawn from the same 8 cases. The width is set by the number of real cases, not the number of resamples. To shrink the interval you need more *cases*, which is real new data; more *resamples* only render the same uncertainty more precisely. A common error is to crank resamples and report a suspiciously tight interval that is really just a well-measured picture of a small sample.

The mirror-image mistake is forgetting the seed. An unseeded bootstrap gives a slightly different interval every run, so a documented "[0.375, 1.0]" becomes uncheckable — a colleague reruns it and gets [0.375, 0.875], and no one can tell whether the model changed or the RNG did. Seeding makes the interval a reproducible function of the data, which is the whole point of reporting it. The bootstrap is random; a documented bootstrap must be seeded.

```python filename=modules/evals-and-statistics/code/evals-inter-19/bootstrap.py:51-57 COMPLETE
def bootstrap_interval(scores, seed, b):
    """The 95% percentile interval of the resampled means, using a seeded RNG for reproducibility."""
    rng = random.Random(seed)
    means = sorted(mean(resample(scores, rng)) for _ in range(b))
    lo = means[int(0.025 * b)]
    hi = means[int(0.975 * b) - 1]
    return lo, hi
```

**Bootstrap a seeded interval and report it, not the bare point: its width is the number of real cases speaking, so widen it with more cases and stabilize it with more resamples — never confuse the two.**

## External resources

Efron and Tibshirani, "An Introduction to the Bootstrap" — the foundational treatment of resampling for confidence intervals, including the percentile method used here and its variants.

The scikit-learn and SciPy `bootstrap` utilities — production implementations with the resample count, confidence level, and interval method as parameters, for any metric.

The companion modules on seeding the RNG and the Wilson interval — the bootstrap needs the seed for reproducibility, and Wilson is the closed-form alternative when the metric is a simple proportion.
