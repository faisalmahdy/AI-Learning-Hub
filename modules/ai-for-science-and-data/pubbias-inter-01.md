---
id: pubbias-inter-01
title: Average all the studies, not just the published ones — publication bias manufactures an effect from pure noise
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: A meta-analysis pools the studies on a question to estimate the true effect, and it can only pool the studies it can see. That is the trap, because which studies become visible is not random: journals, reviewers, and authors prefer a positive, statistically significant result to a null one. A study that finds "no effect" is harder to publish and sits in the researcher's file drawer — the file-drawer problem — and among significant results, the ones pointing in the hoped-for positive direction get published and cited far more than significant results pointing the other way (positive-outcome bias). So the published literature is a biased sample of all studies actually run, skewed toward large, positive, significant effects, and a meta-analysis of it estimates from the skewed sample and gets it wrong. The failure is starkest when the true effect is zero: a treatment that does nothing still produces noisy estimates scattered around zero — some positive, some negative, most small, a few large by chance — and publishing only the significant, positive ones leaves a visible literature made entirely of the upper tail. A meta-analyst pooling those published studies computes a confident positive effect, with a tight confidence interval, for a treatment that does nothing. On a fixture of eight studies of a no-effect treatment whose effects average to exactly 0, only the significant positive studies (effects 2 and 4) are published, and their mean is 3 — so the visible literature reports an effect of 3 where the truth is 0, with six of eight studies hidden in the file drawer.
eli5: Imagine a hundred people each flip a coin ten times and only the ones who got a lot of heads bother to tell you about it — everyone who got a normal mix stays quiet, and everyone who got a lot of tails is too embarrassed to mention it. If you only listen to the people who spoke up, you'd conclude the coin is rigged toward heads, even though the coin is perfectly fair and the full group averaged out to normal. Science has the same problem: studies that find an exciting result get shouted about and published, while the "we found nothing" studies quietly go in a drawer — so if you only read the published ones, you can be convinced a treatment works when it does nothing at all.
---

## Why this module

A meta-analysis is only as honest as the set of studies it can see, and that set has been filtered before it ever reaches the analyst — by what got published. The filter is not neutral: a striking, significant, positive finding sails through review and into citation, while a null result is quietly shelved. So the literature is not a fair sample of the experiments people ran; it is the survivors of a selection process that specifically favors the results most likely to be exciting and least likely to be true when the truth is boring. Pooling that filtered set does not average out the noise — it averages the tail that the filter let through.

Which studies become visible is not random: journals, reviewers, and authors prefer a positive, significant result to a null one. A study that finds "no effect" is harder to publish and sits in the file drawer, and among significant results, the ones pointing in the hoped-for direction get published and cited far more than those pointing the other way. The published literature is a biased upper-tail sample of all studies run, and a meta-analysis of it gets the effect wrong.

This is starkest when the true effect is zero. A treatment that does nothing still produces noisy estimates scattered around zero; publish only the significant, positive ones and the visible literature is entirely the upper tail — a run of studies all showing a sizeable positive effect, none of the negatives or nulls that would cancel them. This module pools all the studies and then only the published ones.

**Estimate an effect from all the studies run, not only the published ones, because publication favors significant and positive results, so the visible literature is a biased upper-tail sample — and pooling only it manufactures a confident effect even when the true effect is zero and the full set of studies averages to nothing.**

## Concepts

**Two filters decide visibility:** a result is significant if its magnitude clears the threshold, and it is published only if it is significant *and* positive (the file drawer plus positive-outcome bias).

```python filename=modules/ai-for-science-and-data/code/pubbias-inter-01/pubbias.py:52-58 COMPLETE
def is_significant(effect, threshold):
    return abs(effect) >= threshold


def is_published(effect, threshold):
    """Published if significant AND positive (file-drawer + positive-outcome bias)."""
    return is_significant(effect, threshold) and effect > 0
```

**The estimate is a mean, computed over whichever set of studies you can see** — all of them, or only the published subset.

```python filename=modules/ai-for-science-and-data/code/pubbias-inter-01/pubbias.py:61-66 COMPLETE
def mean(xs):
    return sum(xs) / len(xs)


def published(effects, threshold):
    return [e for e in effects if is_published(e, threshold)]
```

<svg role="img" aria-label="Eight study effects on a number line centered at zero; a filter keeps only the two positive significant ones (2 and 4), discarding the negatives and the small nulls" viewBox="0 0 300 116" width="300" height="116">
  <text x="6" y="12" fill="var(--muted)" font-size="8">eight studies scattered around 0; the filter keeps only the upper tail</text>
  <line x1="20" y1="50" x2="285" y2="50" stroke="var(--grid)"/>
  <line x1="150" y1="42" x2="150" y2="58" stroke="var(--ink)"/><text x="142" y="70" fill="var(--muted)" font-size="6">0</text>
  <line x1="110" y1="44" x2="110" y2="56" stroke="var(--s2)" stroke-dasharray="1 2"/><line x1="190" y1="44" x2="190" y2="56" stroke="var(--s2)" stroke-dasharray="1 2"/><text x="176" y="40" fill="var(--s2)" font-size="6">±2 sig</text>
  <circle cx="70" cy="50" r="3" fill="var(--muted)"/><text x="64" y="42" fill="var(--muted)" font-size="6">-4</text>
  <circle cx="110" cy="50" r="3" fill="var(--muted)"/><circle cx="130" cy="50" r="3" fill="var(--muted)"/><circle cx="132" cy="50" r="3" fill="var(--muted)"/>
  <circle cx="170" cy="50" r="3" fill="var(--muted)"/><circle cx="168" cy="50" r="3" fill="var(--muted)"/>
  <circle cx="190" cy="50" r="3" fill="var(--s1)"/><text x="186" y="42" fill="var(--s1)" font-size="6">2</text>
  <circle cx="230" cy="50" r="3" fill="var(--s1)"/><text x="226" y="42" fill="var(--s1)" font-size="6">4</text>
  <rect x="184" y="80" width="66" height="20" fill="none" stroke="var(--s1)"/><text x="190" y="93" fill="var(--s1)" font-size="6">published: 2, 4</text>
  <text x="20" y="96" fill="var(--muted)" font-size="6">discarded: -4, -2, -1, -1, 1, 1 (negatives and nulls)</text>
</svg>
^ The eight effects sit symmetrically around zero, but the publication filter keeps only the two that are both significant and positive (2 and 4) and discards the negative-significant and all the small null results — so the visible set is the upper tail, not the center.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/pubbias-inter-01/pubbias.py

The fixture is eight study effects for a treatment with no real effect, and the significance threshold.

```json filename=modules/ai-for-science-and-data/code/pubbias-inter-01/pubbias.json:3-4 COMPLETE
  "effects": [-4, -2, -1, -1, 1, 1, 2, 4],
  "threshold": 2
```

Run `--studies`.

```text filename=--studies
STUDIES — effect, significance (|effect| >= 2), and publication under the bias
------------------------------------------------------------
  effect   significant?   published?
  -4       yes            file drawer
  -2       yes            file drawer
  -1       no             file drawer
  -1       no             file drawer
  1        no             file drawer
  1        no             file drawer
  2        yes            PUBLISHED
  4        yes            PUBLISHED
------------------------------------------------------------
  published: [2, 4]   (the rest are hidden)
```

Read the publication column down. The four small studies (−1, −1, 1, 1) are not significant, so they go in the file drawer — this is the classic file-drawer problem, null results never seeing daylight. But look at the two *significant negative* studies, −4 and −2: they cleared the significance bar, yet they are also filed away, because they point the wrong way. This is positive-outcome bias, and it is what makes the distortion so severe: it is not merely that nulls are hidden, it is that the negatives are hidden too, so the visible literature loses everything that would pull the estimate back toward zero. Only the two positive significant studies, 2 and 4, are published. Six of the eight studies — every negative and every null — are invisible to anyone reading the literature, and the two that remain are the largest positive results in the whole set.

## Build

Now pool each set and see what a meta-analysis would report.

```text filename=--bias
BIAS — the mean over all studies vs the mean over only the published ones
--------------------------------------------------------------
  all 8 studies:        [-4, -2, -1, -1, 1, 1, 2, 4]   mean = 0.0   <- the truth (no effect)
  published 2 studies:   [2, 4]              mean = 3.0   <- the phantom
--------------------------------------------------------------
  6 of 8 studies are in the file drawer; the meta-analysis sees only the upper tail.
```

<svg role="img" aria-label="A funnel plot: effect on the horizontal axis centered at zero, precision on the vertical; the full symmetric funnel of studies versus the published set which is missing its entire bottom-left corner, making it asymmetric" viewBox="0 0 300 116" width="300" height="116">
  <text x="6" y="12" fill="var(--muted)" font-size="8">funnel plot: publication eats the bottom-left (small, negative)</text>
  <line x1="150" y1="24" x2="150" y2="92" stroke="var(--grid)" stroke-dasharray="1 3"/><text x="140" y="102" fill="var(--muted)" font-size="6">effect 0</text>
  <line x1="60" y1="92" x2="150" y2="26" stroke="var(--grid)"/><line x1="240" y1="92" x2="150" y2="26" stroke="var(--grid)"/>
  <text x="16" y="30" fill="var(--muted)" font-size="6">precise</text><text x="16" y="90" fill="var(--muted)" font-size="6">noisy</text>
  <circle cx="150" cy="34" r="2.5" fill="var(--muted)"/><circle cx="135" cy="50" r="2.5" fill="var(--muted)"/><circle cx="168" cy="50" r="2.5" fill="var(--s1)"/>
  <circle cx="110" cy="74" r="2.5" fill="var(--muted)"/><circle cx="130" cy="74" r="2.5" fill="var(--muted)"/>
  <circle cx="190" cy="74" r="2.5" fill="var(--s1)"/><circle cx="215" cy="86" r="2.5" fill="var(--s1)"/>
  <path d="M60 68 L112 68 L150 30 L60 30 Z" fill="var(--s2)" opacity="0.25"/>
  <text x="62" y="60" fill="var(--s2)" font-size="6">missing:</text><text x="62" y="70" fill="var(--s2)" font-size="6">small &amp; negative</text>
</svg>
^ In a funnel plot each study is placed by its effect (horizontal) and precision (vertical); an unbiased set forms a symmetric funnel, but publication bias removes the shaded bottom-left corner — the small, imprecise studies with negative or null effects — leaving a visibly lopsided funnel that is the diagnostic fingerprint of the missing file-drawer studies.

The two means could not disagree more completely. Pooled over all eight studies — the studies that were actually run — the mean effect is exactly 0.0, which is the truth: the treatment does nothing, and the noisy positive and negative results cancel. Pooled over only the two published studies, the mean effect is 3.0 — a large, confident, positive effect for a treatment with no effect at all. Nothing about the analysis is wrong; the meta-analyst computed the mean of the studies correctly. The error was upstream, in the sample: the published set is not a sample of the treatment's effect, it is a sample of the treatment's effect *conditioned on being large and positive*, which is guaranteed to look like an effect whether or not one exists. This is why the file drawer is not a minor caveat but the whole story — the six hidden studies are precisely the evidence that would reveal the phantom, and their absence is what lets a mean over the visible two masquerade as a finding. A tight confidence interval around 3.0 would make it worse, lending false precision to an artifact.

```python filename=modules/ai-for-science-and-data/code/pubbias-inter-01/pubbias.py:102-109 COMPLETE
    true_effect_zero = mean(effects) == 0
    print("  all studies average to zero (the true effect) = %s (mean %.1f)" % (true_effect_zero, mean(effects)))

    published_shows_effect = mean(pub) > 0
    print("  the published studies show a positive effect = %s (mean %.1f)" % (published_shows_effect, mean(pub)))

    publication_inflates = mean(pub) > mean(effects)
    print("  publication bias inflates the estimate = %s (%.1f vs %.1f)" % (publication_inflates, mean(pub), mean(effects)))
```

## Definition of done

The self-test pins the zero truth, the positive phantom, the file-drawer majority, and that every null is hidden.

```python filename=modules/ai-for-science-and-data/code/pubbias-inter-01/pubbias.py:111-116 COMPLETE
    most_in_drawer = (len(effects) - len(pub)) > len(pub)
    print("  most studies are hidden in the file drawer = %s (%d hidden, %d published)"
          % (most_in_drawer, len(effects) - len(pub), len(pub)))

    nulls_all_hidden = all(not is_published(e, thr) for e in effects if not is_significant(e, thr))
    print("  every non-significant study is unpublished = %s" % nulls_all_hidden)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — all studies average to zero; the published subset averages to a positive phantom effect
----------------------------------------------------------------------------------------------------
  all studies average to zero (the true effect) = True (mean 0.0)
  the published studies show a positive effect = True (mean 3.0)
  publication bias inflates the estimate = True (3.0 vs 0.0)
  most studies are hidden in the file drawer = True (6 hidden, 2 published)
  every non-significant study is unpublished = True
```

<svg role="img" aria-label="Two means: all eight studies average to 0, the two published studies average to 3; a stack shows 6 studies in the file drawer and 2 published" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">true effect 0 (all 8) vs published effect 3 (only 2 visible)</text>
  <line x1="70" y1="24" x2="70" y2="70" stroke="var(--grid)"/><text x="52" y="80" fill="var(--muted)" font-size="6">0</text>
  <circle cx="70" cy="40" r="4" fill="var(--ink)"/><text x="80" y="43" fill="var(--muted)" font-size="7">all 8 studies → mean 0 (truth)</text>
  <circle cx="190" cy="40" r="4" fill="var(--s2)"/><text x="200" y="43" fill="var(--muted)" font-size="7">published 2 → mean 3 (phantom)</text>
  <line x1="190" y1="24" x2="190" y2="70" stroke="var(--grid)" stroke-dasharray="1 3"/><text x="182" y="80" fill="var(--muted)" font-size="6">3</text>
  <text x="10" y="98" fill="var(--s2)" font-size="6">file drawer: 6 hidden</text><text x="150" y="98" fill="var(--s1)" font-size="6">published: 2</text>
  <rect x="90" y="90" width="54" height="8" fill="var(--muted)"/><rect x="204" y="90" width="18" height="8" fill="var(--s1)"/>
</svg>
^ Pooled over all eight studies the effect is 0 (the truth); pooled over the two published studies it is 3 (the phantom), and the bar shows why — six of the eight studies, the ones that would drag the estimate back to zero, are hidden in the file drawer.

**Done means the manufactured effect is proven on real numbers: eight studies of a no-effect treatment average to exactly 0 (the truth), but publication keeps only the two significant-positive studies (2 and 4), whose mean is 3 — a confident phantom effect — with six of eight studies (every negative and every null) hidden in the file drawer, so an effect must be estimated from all studies run, not the published subset.**

## Boss fight

Predict two things about publication bias that make it harder to escape than "just include the unpublished studies," because the missing data is missing precisely because it is inconvenient.

The first trap is that you usually cannot simply include the file-drawer studies, because you do not have them — that is what "unpublished" means — so the practical fight is detection and prevention, not retrieval. Detection leans on the shape the bias leaves in the visible data: a funnel plot graphs each study's effect against its precision, and without bias it should be a symmetric funnel (small, imprecise studies scatter widely around the true effect, large precise ones cluster near it); publication bias eats the bottom-left corner (small studies with small or negative effects never get published), producing a visibly asymmetric funnel, and tests like Egger's regression quantify that asymmetry. Correction methods like trim-and-fill try to estimate and impute the missing studies to re-symmetrize the funnel, but they are patches on a fundamentally missing-data problem and can mislead. The real fix is upstream and structural: pre-registration and registered reports, where a study's methods and analysis are reviewed and accepted *before* the results are known, so the study is published regardless of outcome — which converts the file drawer into a registry you can actually pool. Clinical-trial registries exist for exactly this reason. The lesson is that publication bias is not an analysis bug you can clean up after the fact so much as an incentive problem you have to prevent at the source, because the evidence you most need is the evidence the system was designed not to produce.

The second trap is that publication bias compounds with the other tail-selection effects and is not limited to formal meta-analysis. It is a sibling of the multiple-comparisons and winner's-curse problems: run enough studies (or enough analyses within one study — p-hacking, the garden of forking paths) and some will cross significance by chance, and if only those are reported, the reported effect is inflated even from a single lab. It interacts with small-study effects (small studies are noisier, so their published survivors are the most extreme). And it reaches far beyond journals: a company reporting only its successful A/B tests, a blog citing only the papers that agree with it, a model card showing only the benchmarks it wins, an anecdote-driven belief formed from the vivid successes you heard about and the failures you never did — all are the file drawer in another costume. The defense is the same everywhere: ask not "what does the visible evidence show?" but "what would have to be true of the *invisible* evidence for this to hold?", seek the denominator (how many studies/tests/attempts were run, not just how many succeeded), and distrust a clean positive result whose null and negative counterparts are conspicuously absent. A finding is only as trustworthy as the completeness of the sample that produced it.

**You usually cannot retrieve the file-drawer studies, so fight publication bias by detection and prevention, not retrieval: read funnel-plot asymmetry and Egger's test as symptoms, treat trim-and-fill as a patch on missing data, and rely on pre-registration and registries that publish regardless of outcome to prevent the drawer at the source. And recognize the same tail-selection everywhere — it compounds with multiple comparisons, p-hacking, and small-study effects, and appears wherever only the successes are reported (A/B tests, benchmarks, anecdotes) — so always seek the denominator and ask what the invisible, unreported results would have to be, because a finding is only as trustworthy as the completeness of the sample behind it.**

## External resources

The meta-analysis and research-methods literature on publication bias (Rosenthal's file-drawer problem, funnel plots and Egger's test, trim-and-fill, and the registered-reports / pre-registration movement) — how the bias is detected, partially corrected, and structurally prevented.

Writing on the replication crisis and p-hacking (Ioannidis's "Why Most Published Research Findings Are False," the garden of forking paths) — how publication bias combines with multiple comparisons and selective reporting to inflate the published effect size.

The companion multiple-comparisons, winner's-curse, and survivorship-bias modules in this topic — publication bias is tail selection on which studies are visible, a close relative of selecting the best of many noisy estimates and of averaging over survivors, and all share the fix of seeking the full denominator rather than the reported numerator.
