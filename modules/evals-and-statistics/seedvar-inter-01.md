---
id: seedvar-inter-01
title: Report an eval score as a mean over seeds, not one run — a single noisy run can flip the winner between two models
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: A model's score on a benchmark is not a fixed number. Any evaluation that samples the model's outputs (temperature above zero, nucleus sampling, nondeterministic tool ordering) produces a different score every time you run it with a different seed, because different generations are sampled and graded. That variation is the real uncertainty of the measurement, not a bug — yet the near-universal habit is to run the benchmark once, report that single number as "the model's score," and compare two models by their single numbers. That comparison is unreliable to the degree the per-run spread is large, and for many benchmarks it is large enough to change the answer. A single run puts a model somewhere in its own distribution — a lucky high draw or an unlucky low one — so comparing two single draws compares two points that each carry that noise: if A truly averages a few points above B but each has a spread of several points, a low run of A against a high run of B reports that B won, the opposite of the truth. The fix is to run each model over several seeds and report the mean with its spread (standard deviation or standard error), judging a difference against that spread. On a fixture where A averages 72 across five seeds and B averages 66 — a 6-point gap that is 3 standard errors, solid — A's runs still dip to 68 and B's rise to 70, so a single-run comparison can report B ahead of A by 2, the opposite verdict.
eli5: Imagine judging which of two dice is "bigger" by rolling each one just once. If one die comes up 2 and the other comes up 5, you'd say the second is bigger — but that's just luck of a single roll; roll again and it could flip. The right way is to roll each die many times and compare the averages, and also notice how much the rolls bounce around. Testing an AI on a benchmark is like that: because the model rolls the dice a little each time it answers, one test run is one roll. So you run it several times, average the scores, and only trust a "this model is better" claim if the gap between the averages is bigger than the normal bounce.
---

## Why this module

Two models get a benchmark run each, one scores higher, and a leaderboard is born — and the number that decided it was a coin the size of the run-to-run noise. The habit of treating a single benchmark run as "the model's score" quietly assumes the score is deterministic, but any eval that samples generations is a random draw, and a single draw is a point somewhere in a distribution you never looked at. Comparing two single draws is comparing two coin flips and announcing which coin is heavier.

Any evaluation that samples the model's outputs produces a different score every time you run it with a different random seed, because different generations are sampled and graded. The variation is not a bug to be eliminated; it is the real uncertainty of the measurement. A single run puts a model somewhere within its own distribution — possibly a lucky high draw, possibly an unlucky low one — and comparing two single draws compares two points that each carry that noise. If A truly averages a few points above B, but each has a spread of several points, a single run of A can land low while a single run of B lands high, and the one-shot comparison reports that B beat A — the opposite of the truth.

The fix is to run each model over several seeds and report the mean with its spread (standard deviation, or a standard error / confidence interval), and to judge a difference against that spread. The mean over seeds is a far more stable estimate than any single run, and the standard error of the mean shrinks as you add seeds, so a real gap becomes distinguishable from noise. This module runs the comparison both ways.

**Report a sampled model's benchmark score as a mean over multiple seeds together with its spread, and compare models by those means against the combined standard error — never by a single run, because run-to-run variance can make one lucky or unlucky seed flip the apparent winner even when the true, seed-averaged gap is solid.**

## Concepts

**A model's score is a distribution, summarized by its mean and its run-to-run standard deviation** across seeds.

```python filename=modules/evals-and-statistics/code/seedvar-inter-01/seedvar.py:52-63 COMPLETE
def mean(xs):
    return sum(xs) / len(xs)


def sample_variance(xs):
    """Unbiased (n-1) variance of the per-seed scores."""
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def sample_std(xs):
    return math.sqrt(sample_variance(xs))
```

**A difference is judged against the standard error of the difference; a single-run comparison, by contrast, can land anywhere in a wide range** bounded by the two models' extremes.

```python filename=modules/evals-and-statistics/code/seedvar-inter-01/seedvar.py:66-73 COMPLETE
def se_of_difference(a, b):
    """Standard error of the difference in means of two independent samples."""
    return math.sqrt(sample_variance(a) / len(a) + sample_variance(b) / len(b))


def single_run_gap_range(a, b):
    """The most extreme A-minus-B a single-run comparison could report: (worst for A, best for A)."""
    return min(a) - max(b), max(a) - min(b)
```

<svg role="img" aria-label="Two overlapping distributions on a score axis: model A centered at 72 and model B centered at 66, their spreads overlapping between 68 and 70 so a low A run and a high B run cross over" viewBox="0 0 300 116" width="300" height="116">
  <text x="6" y="12" fill="var(--muted)" font-size="8">each model is a distribution of scores — and they overlap</text>
  <line x1="20" y1="86" x2="285" y2="86" stroke="var(--grid)"/>
  <path d="M40 86 Q90 40 140 86" fill="none" stroke="var(--s1)"/><text x="96" y="44" fill="var(--s1)" font-size="7">B (mean 66)</text>
  <path d="M110 86 Q160 40 210 86" fill="none" stroke="var(--s2)"/><text x="150" y="44" fill="var(--s2)" font-size="7">A (mean 72)</text>
  <rect x="110" y="60" width="30" height="26" fill="var(--grid)" opacity="0.5"/><text x="96" y="100" fill="var(--muted)" font-size="6">overlap 68–70</text>
  <line x1="90" y1="86" x2="90" y2="78" stroke="var(--s1)"/><text x="80" y="112" fill="var(--muted)" font-size="6">66</text>
  <line x1="160" y1="86" x2="160" y2="78" stroke="var(--s2)"/><text x="150" y="112" fill="var(--muted)" font-size="6">72</text>
  <text x="150" y="106" fill="var(--muted)" font-size="6">a low-A run (68) can land below a high-B run (70)</text>
</svg>
^ Model A's score distribution (mean 72) sits above B's (mean 66), but the two overlap in the 68–70 band, so an unlucky low run of A can fall below a lucky high run of B — the overlap is exactly where a single-run comparison can report the wrong winner.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/seedvar-inter-01/seedvar.py

The fixture is five per-seed scores for each of the two models.

```json filename=modules/evals-and-statistics/code/seedvar-inter-01/seedvar.json:3-4 COMPLETE
  "model_a": {"name": "A", "seed_scores": [68, 70, 72, 74, 76]},
  "model_b": {"name": "B", "seed_scores": [62, 64, 66, 68, 70]}
```

Run `--seeds`.

```text filename=--seeds
SEEDS — five runs of each model, different seed each time
------------------------------------------------------------
  model  per-seed scores        mean    run-to-run std
  A      [68, 70, 72, 74, 76]   72.0    3.16
  B      [62, 64, 66, 68, 70]   66.0    3.16
```

Read the two rows. Averaged over five seeds, A scores 72 and B scores 66 — a real 6-point gap. But look at the per-seed scores, not just the means: A's runs range from 68 to 76, and B's range from 62 to 70. The run-to-run standard deviation is 3.16 for each, which is large relative to the 6-point gap between the means. Crucially, the two ranges overlap: A can score as low as 68, and B can score as high as 70. So if you had run each model once and happened to catch A on its 68 seed and B on its 70 seed, you would have reported that B beat A — despite A being genuinely better on average. The mean over seeds is the stable, trustworthy summary; each individual number in those lists is a noisy sample, and any one of them, reported alone, is a shaky basis for a comparison.

## Build

Spell out exactly how wide the single-run comparison can swing.

```text filename=--single
SINGLE — what a one-run-each comparison can report vs the seed-mean gap
--------------------------------------------------------------------
  seed-mean gap (A - B)          = +6.0  (A really is better on average)
  single-run gap, worst for A    = -2.0  (A's low 68 vs B's high 70 -> B 'wins')
  single-run gap, best for A     = +14.0  (A's high 76 vs B's low 62)
--------------------------------------------------------------------
  one run each can report anything from -2.0 to +14.0 -- the sign itself is not safe.
```

The seed-averaged gap is a stable +6 in A's favor, but a single run of each model can report a gap anywhere from −2 (B ahead) to +14 (A far ahead), depending only on which seeds you happened to draw. The range is 16 points wide — nearly three times the true gap — and, most damningly, it straddles zero: the *sign* of a single-run comparison is not reliable, so a one-shot eval can not only mis-size the gap but name the wrong winner. This is the concrete cost of reporting one run. It is not that the single number is a little noisy; it is that the conclusion you draw from comparing two single numbers ("A is better," "B is better") can be the opposite of the truth, and you cannot tell from the run itself which case you are in. Only by running multiple seeds and looking at the spread do you learn that the comparison was inside the noise band and needed averaging.

<svg role="img" aria-label="A shared score axis from 62 to 76 with model A's five seed scores plotted as one series and model B's as another; A's lowest (68) sits at the same place as B's highest (70 just above 68), showing the overlap where a single-run comparison crosses over" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the five seeds of each model, on one score axis — they overlap</text>
  <line x1="20" y1="70" x2="285" y2="70" stroke="var(--grid)"/>
  <text x="16" y="84" fill="var(--muted)" font-size="6">62</text><text x="270" y="84" fill="var(--muted)" font-size="6">76</text>
  <g fill="var(--s2)"><circle cx="130" cy="40" r="3"/><circle cx="167" cy="40" r="3"/><circle cx="204" cy="40" r="3"/><circle cx="241" cy="40" r="3"/><circle cx="278" cy="40" r="3"/></g>
  <text x="120" y="32" fill="var(--s2)" font-size="6">A: 68 70 72 74 76</text>
  <g fill="var(--s1)"><circle cx="30" cy="56" r="3"/><circle cx="67" cy="56" r="3"/><circle cx="104" cy="56" r="3"/><circle cx="130" cy="56" r="3"/><circle cx="167" cy="56" r="3"/></g>
  <text x="26" y="98" fill="var(--s1)" font-size="6">B: 62 64 66 68 70</text>
  <rect x="126" y="34" width="45" height="28" fill="var(--grid)" opacity="0.5"/><text x="128" y="52" fill="var(--muted)" font-size="6">68–70 overlap</text>
</svg>
^ Plotting all five seeds of each model on one axis shows A (68–76) sitting above B (62–70) on average, but their ranges overlap at 68–70; a single run that draws A from the low end and B from the high end of that overlap crosses the two over, which is exactly how one run can name the wrong winner.

```python filename=modules/evals-and-statistics/code/seedvar-inter-01/seedvar.py:112-119 COMPLETE
    mean_gap_is_six = abs(gap - 6.0) < 1e-9
    print("  seed-mean gap A - B = %s (%.1f - %.1f = %.1f)" % (mean_gap_is_six, mean_a, mean_b, gap))

    single_run_can_flip = worst < 0
    print("  a single-run comparison can show B ahead of A = %s (worst-for-A gap = %+.1f)" % (single_run_can_flip, worst))

    single_run_range_wide = (best - worst) > abs(gap)
    print("  the single-run gap range (%+.1f..%+.1f) dwarfs the true gap = %s" % (worst, best, single_run_range_wide))
```

## Definition of done

The self-test pins the flip risk of a single run against the solidity of the seed-averaged gap — a 6-point difference at 3 standard errors.

```python filename=modules/evals-and-statistics/code/seedvar-inter-01/seedvar.py:121-124 COMPLETE
    mean_gap_solid = abs(gap) / se >= 2.0
    print("  the seed-mean gap is large vs its standard error = %s (t = %.1f / %.1f = %.1f)" % (mean_gap_solid, gap, se, gap / se))

    runs_vary = sample_std(a) > 0 and sample_std(b) > 0
    print("  the per-seed scores genuinely vary run to run = %s (std A=%.2f, B=%.2f)" % (runs_vary, sample_std(a), sample_std(b)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — a single run can flip the winner, while the seed-averaged gap is solid
----------------------------------------------------------------------------------------------------
  seed-mean gap A - B = True (72.0 - 66.0 = 6.0)
  a single-run comparison can show B ahead of A = True (worst-for-A gap = -2.0)
  the single-run gap range (-2.0..+14.0) dwarfs the true gap = True
  the seed-mean gap is large vs its standard error = True (t = 6.0 / 2.0 = 3.0)
  the per-seed scores genuinely vary run to run = True (std A=3.16, B=3.16)
```

<svg role="img" aria-label="Two ways to compare: single-run gaps span from minus 2 to plus 14 crossing zero, while the seed-mean gap is a tight plus 6 at three standard errors, well clear of zero" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">single run: sign not safe; seed mean: +6 at t=3, solid</text>
  <line x1="20" y1="50" x2="285" y2="50" stroke="var(--grid)"/>
  <line x1="70" y1="30" x2="70" y2="90" stroke="var(--line)" stroke-dasharray="2 2"/><text x="60" y="100" fill="var(--muted)" font-size="6">0 (tie)</text>
  <text x="10" y="40" fill="var(--s2)" font-size="7">single run</text>
  <line x1="50" y1="44" x2="260" y2="44" stroke="var(--s2)"/><circle cx="50" cy="44" r="3" fill="var(--s2)"/><circle cx="260" cy="44" r="3" fill="var(--s2)"/>
  <text x="30" y="58" fill="var(--s2)" font-size="6">-2</text><text x="256" y="34" fill="var(--s2)" font-size="6">+14</text>
  <text x="10" y="76" fill="var(--s1)" font-size="7">seed mean</text>
  <rect x="150" y="70" width="24" height="8" fill="var(--s1)"/><line x1="150" y1="74" x2="174" y2="74" stroke="var(--s1)"/><text x="178" y="77" fill="var(--s1)" font-size="6">+6 ± SE (clear of 0)</text>
</svg>
^ A single-run comparison spans −2 to +14, crossing the tie line so its winner is not safe; the seed-mean gap is a tight +6 at three standard errors, sitting well to the right of zero — averaging over seeds is what moves the comparison off the noise and clear of the tie.

**Done means the run-to-run risk is proven on real scores: the seed-mean gap is a solid +6 (t = 3.0), yet a single run of each model can report anything from B ahead by 2 to A ahead by 14 — a 16-point swing that flips the winner — so a sampled model's score must be reported as a mean over seeds with its spread and compared against the standard error, never as one run.**

## Boss fight

Predict two ways this seed-averaging is done wrong, because more runs help only if they are the right runs and you account for them correctly.

The first trap is confusing the two kinds of variance an eval has, and averaging away the wrong one. There is run-to-run (seed) variance — the same model on the same items scoring differently because generation is sampled — and there is item (case) variance — the model being genuinely better on some test cases than others. They need different treatment: seed variance is reduced by running the same benchmark multiple times and averaging (this module), while item variance is characterized by bootstrapping over the test cases or using a paired comparison on the same items. If you only run more seeds but keep a tiny, unrepresentative item set, you will report a beautifully tight mean that is precisely wrong, because you shrank the seed noise while leaving the item noise (and any item-selection bias) untouched. And the standard error must reflect the actual design: if you draw n seeds on a fixed item set, your effective sample for the seed-mean is the seeds, but your generalization to *new items* is limited by the items, not the seeds — so the honest interval accounts for both sources, and reporting only the seed standard error understates the true uncertainty about how the model does on the population of tasks.

The second trap is that seeds must be independent and the runs comparable, or the averaging is an illusion. If your "different seeds" are not actually independent — the harness caches responses, the temperature is effectively zero so all runs are identical, or a shared random state couples them — then five runs give you one run's worth of information with false confidence, and the standard error you compute (which assumes independence) is too small. Likewise, the runs must be comparable: same prompts, same grader version, same model snapshot, same decoding parameters; if anything drifts between runs (a grader update, a silent model version bump, a changed system prompt) the "seed variance" you measure is contaminated by those changes and the mean is over an apples-and-oranges mixture. And there is a cost dimension — running every eval on many seeds is expensive, so the practical discipline is to spend seeds where they matter (close comparisons near a decision boundary get more seeds; a model that is obviously far ahead or behind needs fewer) and always to report how many seeds and how much spread, so a reader can judge whether a reported gap cleared the noise or is another lucky single-ish run dressed up as a mean.

**Average away seed variance, but do not mistake it for item variance — run more seeds to stabilize the score and bootstrap or pair over cases to handle case-to-case variation, and let the reported interval reflect both, or a tight seed-mean on a tiny item set is precisely wrong. And the seeds must earn their standard error: they have to be genuinely independent (not a zero-temperature or cached run repeated) and the runs comparable (same prompts, grader, model snapshot, and decoding), or the averaging buys false confidence — so report the seed count and the spread, and spend seeds where a comparison is close enough for the noise to matter.**

## External resources

Writing on evaluation reproducibility and variance (the "reproducibility crisis" discussions for LLM benchmarks, and papers reporting mean ± std over seeds) — why single-run leaderboard numbers are unreliable and how many seeds are needed to make a gap credible.

Documentation on standard error of the mean, the two-sample t-test, and bootstrapping — the tools for turning several noisy runs into a mean with an interval, and for separating seed variance from case variance.

The companion bootstrap-confidence-interval, paired-comparison, and error-bar-overlap modules in this topic — seed variance is the sampling-noise counterpart to case variance, and the "test the difference against its combined uncertainty" rule is the same one those modules apply to test-case resampling.
