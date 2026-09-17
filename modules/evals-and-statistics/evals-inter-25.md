---
id: evals-inter-25
title: The LLM judge is a noisy instrument — a model gap inside its grading noise is not real, so re-grade to shrink it
topic: evals-and-statistics
level: intermediate
status: ready
time: 17 min
summary: An LLM judge does not return the same verdict every time — grade one answer twice and it can pass once and fail once, because the judge samples a token stream like the model under test. That makes every eval score a measurement with its own error, not a fact read off a ruler. If model A scores 0.70 and model B 0.78, the 0.08 gap looks like a win, but if grading each answer once carries enough judge-to-judge variance that a single model's score wobbles by 0.10, the gap sits inside the instrument's noise and could vanish or reverse on a re-grade. There are two independent noise sources: sampling different items (the usual confidence interval) and re-running the same judge on the same items — and averaging more items does nothing for grader noise; only averaging more gradings does, shrinking the grader-induced standard error like 1/√R. On a fixture where two models truly differ by 0.08 on 40 items and the judge injects a per-grade variance of 0.20, a single grading gives a difference noise band of ±0.20 that buries the gap, and averaging 7 gradings per item is needed to clear it.
eli5: Imagine a judge scoring a diving contest, but this judge is a little random — score the same dive twice and you might get a 7 or an 8. If two divers finish a tenth of a point apart, you can't tell who was really better, because the judge's own wobble is bigger than that gap. Averaging more different dives doesn't fix it — the judge is still wobbly on each one. What fixes it is having the judge score each dive several times and averaging, so the wobble shrinks. Only then can a small true difference show through.
---

## Why this module

An eval score is a measurement, and the LLM judge that produced it is a stochastic instrument, so part of every score is the judge's own reading error — and a difference smaller than that error is not a result, no matter how many items you tested.

We are used to one source of eval noise: the sample of items. Test on thirty questions instead of thirty thousand and the score would move if you drew a different thirty, which is what a confidence interval captures. But an LLM judge adds a second, independent source that the item interval does not see. The judge samples tokens to reach its verdict, so grading the same answer twice can pass it once and fail it once; the score of a fixed answer on a fixed item is itself a random variable. Report model A at 0.70 and model B at 0.78 and the 0.08 gap looks decisive — until you notice that re-grading the very same answers, no new items, would move each model's score on its own. If that grader-only wobble is 0.10 per model, the 0.08 gap is smaller than the noise the instrument injects, and the "win" is a coin that happened to land B-up this grading.

**An LLM judge grades stochastically, so every eval score carries grader measurement error on top of item-sampling error — and a model difference inside the grader's noise band can vanish or reverse on a re-grade, however many items you used.**

The two noise sources need two different fixes, and confusing them wastes effort. Item-sampling noise shrinks by adding items; grader noise does not — a million items graded once each still inherits the judge's per-item wobble. Grader noise shrinks only by grading each item more times and averaging, which cuts the grader-induced standard error like 1/√R: four gradings halve it, nine cut it to a third. So when a gap is drowned in grader noise, the remedy is not a bigger test set but more gradings per item, or a less random judge (a lower temperature), until the difference clears the judge's own error band. This module computes the grader noise band and the gradings needed to beat it.

## Concepts

**Grader variance** is the per-grade wobble the judge adds: the average of p(1−p) over items, where p is the judge's pass probability on an item. It is 0 for a perfectly consistent judge and up to 0.25 for a judge that is a coin flip on every item.

**The grader-induced standard error** of a model's score is that variance spread over the items and the gradings: sqrt(grader_var / (items × gradings)). More items help, but so do more gradings — and only gradings touch the grader's contribution specifically.

```python filename=modules/evals-and-statistics/code/evals-inter-25/judgenoise.py:42-44 COMPLETE
def grader_sem(grader_var, n_items, replicates):
    """Grader-induced standard error of one model's mean score: sqrt(per-grade var / (items * gradings))."""
    return math.sqrt(grader_var / (n_items * replicates))
```

**The difference's standard error** combines the two models' grader errors, because each was graded independently. The gap between the models must be judged against this, not against zero.

```python filename=modules/evals-and-statistics/code/evals-inter-25/judgenoise.py:47-51 COMPLETE
def diff_sem(a, b, n_items, replicates):
    """Standard error of the A-B score difference from grader noise (the two models graded independently)."""
    va = grader_sem(a["grader_var"], n_items, replicates) ** 2
    vb = grader_sem(b["grader_var"], n_items, replicates) ** 2
    return math.sqrt(va + vb)
```

<svg role="img" aria-label="Two independent noise sources: item sampling shrinks with more items, grader noise shrinks with more gradings; averaging items does not reduce grader noise" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">two noise sources in one eval score</text>
  <rect x="14" y="24" width="128" height="30" fill="none" stroke="var(--s1)"/><text x="20" y="38" fill="var(--ink)" font-size="8">item-sampling noise</text>
  <text x="20" y="49" fill="var(--muted)" font-size="7">↓ add more items</text>
  <rect x="158" y="24" width="128" height="30" fill="none" stroke="var(--s2)"/><text x="164" y="38" fill="var(--ink)" font-size="8">grader noise</text>
  <text x="164" y="49" fill="var(--muted)" font-size="7">↓ add more gradings</text>
  <text x="14" y="74" fill="var(--muted)" font-size="7">more items → ✗ no effect on grader noise</text>
  <line x1="150" y1="70" x2="180" y2="70" stroke="var(--s2)" stroke-dasharray="2 2"/><text x="184" y="73" fill="var(--muted)" font-size="7">stays</text>
  <text x="14" y="90" fill="var(--muted)" font-size="7">more gradings → grader SEM shrinks like 1/√R</text>
  <text x="6" y="101" fill="var(--muted)" font-size="8">the fix must match the source: gradings for grader noise, items for sampling noise</text>
</svg>
^ Item-sampling noise and grader noise are independent; adding items shrinks only the first, so a gap buried in grader noise needs more gradings per item, not a bigger test set.

**Every eval score carries grader measurement error, so compare a model gap against the grader's noise band, not against zero — and remember only more gradings per item (not more items) shrink that band.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/evals-inter-25/judgenoise.py

The fixture is two models that truly differ by 0.08, graded on 40 items by a judge with a per-grade variance of 0.20.

```json filename=modules/evals-and-statistics/code/evals-inter-25/judgenoise.json:3-6 COMPLETE
  "n_items": 40,
  "model_a": {"true_score": 0.70, "grader_var": 0.20},
  "model_b": {"true_score": 0.78, "grader_var": 0.20},
  "replicates": 1
```

Run `--noise` to weigh the gap against the judge's grading noise.

```text filename=--noise
NOISE — the model gap against the judge's own grading noise (1 gradings per item)
------------------------------------------------------------------
  model A score            = 0.700   grader SEM = 0.071
  model B score            = 0.780   grader SEM = 0.071
  observed gap  B - A      = 0.080
  grader noise band (2sig) = 0.200   -> gap is INSIDE the band
------------------------------------------------------------------
  the gap is smaller than the noise the judge injects, so a re-grade could erase or reverse it.
```

Each model's score carries a grader-induced standard error of 0.071 — from a single grading of 40 items with a judge that wobbles by 0.20 per grade. The difference between the two independent scores therefore has a two-sigma noise band of 0.200, and the observed gap is 0.080. The gap is inside the band, by a wide margin: the judge's own inconsistency is more than twice the size of the difference it is being asked to detect. Report "B beats A, 0.78 to 0.70" and you are reporting the outcome of one noisy grading, which another grading of the identical answers could flip. Nothing about the models is in question here — they really do differ by 0.08 — but this measurement cannot see it, because the instrument reading it is noisier than the signal. The item count is not the problem; 40 items is fine. The judge is the problem.

<svg role="img" aria-label="The observed gap of 0.08 sits well inside the grader noise band of plus or minus 0.20, so it cannot be distinguished from zero" viewBox="0 0 300 92" width="300" height="92">
  <text x="6" y="12" fill="var(--muted)" font-size="8">B − A against the grader noise band (2σ) at one grading</text>
  <line x1="20" y1="52" x2="290" y2="52" stroke="var(--grid)"/>
  <line x1="155" y1="40" x2="155" y2="64" stroke="var(--ink)"/><text x="140" y="76" fill="var(--muted)" font-size="7">0 (no diff)</text>
  <rect x="55" y="44" width="200" height="16" fill="var(--s2)" opacity="0.35"/><text x="60" y="34" fill="var(--muted)" font-size="7">grader noise band ±0.20</text>
  <circle cx="187" cy="52" r="3.5" fill="var(--s1)"/><text x="176" y="46" fill="var(--s1)" font-size="7">gap 0.08</text>
  <text x="6" y="90" fill="var(--muted)" font-size="8">the gap falls inside the band around zero — indistinguishable from noise on one grading</text>
</svg>
^ The 0.08 gap lands well within the ±0.20 grader noise band around zero, so a single grading cannot separate B from A — the difference is smaller than the judge's own wobble.

## Build

The way out is more gradings, and the payoff follows the square-root law. Run `--average`.

```text filename=--average
AVERAGE — the difference's noise band shrinks like 1/sqrt(gradings)
----------------------------------------------------------
  gap to resolve = 0.080
   1 gradings/item -> noise band 0.200   gap buried
   4 gradings/item -> noise band 0.100   gap buried
   9 gradings/item -> noise band 0.067   gap clears it
  16 gradings/item -> noise band 0.050   gap clears it
  need 7 gradings per item for the gap to clear the two-sigma grader band.
```

At one grading the band is 0.200 and the gap is buried. Quadruple to four gradings and the band halves to 0.100 — still wider than 0.080, so the gap is buried yet. Nine gradings brings the band to 0.067, finally under the gap, and the minimum that clears the two-sigma band is 7 gradings per item. The band fell by exactly the square root of the gradings — four gradings for half, nine for a third — because averaging R independent grades of an item cuts that item's grader variance by R and the standard error by √R. The lesson is quantitative: a gap drowned by a factor of 2.5 in grader noise is not hopeless, it is about seven gradings away, and no amount of adding items would have gotten there. The other lever is the judge itself — grading at temperature 0, or with a more consistent rubric, lowers the per-grade variance directly, so fewer gradings are needed. Choose whichever is cheaper, but budget for the grader's variance explicitly rather than pretending the score is exact.

<svg role="img" aria-label="The grader noise band falls from 0.20 at one grading toward 0.05 at sixteen, crossing below the 0.08 gap at seven gradings" viewBox="0 0 300 104" width="300" height="104">
  <line x1="30" y1="86" x2="290" y2="86" stroke="var(--grid)"/><line x1="30" y1="14" x2="30" y2="86" stroke="var(--grid)"/>
  <text x="4" y="20" fill="var(--muted)" font-size="7">band</text><text x="250" y="100" fill="var(--muted)" font-size="7">gradings →</text>
  <line x1="30" y1="52" x2="290" y2="52" stroke="var(--s1)" stroke-dasharray="3 2"/><text x="232" y="50" fill="var(--s1)" font-size="7">gap 0.08</text>
  <path d="M40 20 L70 44 L110 58 L150 64 L190 68 L230 71 L270 73" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
  <circle cx="40" cy="20" r="2.5" fill="var(--s2)"/><text x="44" y="20" fill="var(--muted)" font-size="7">0.20 @1</text>
  <line x1="130" y1="16" x2="130" y2="86" stroke="var(--ink)" stroke-dasharray="2 2"/><text x="118" y="98" fill="var(--ink)" font-size="7">R=7</text>
  <text x="30" y="103" fill="var(--muted)" font-size="8">the band crosses below the gap at 7 gradings — the square-root law, not more items</text>
</svg>
^ The grader noise band shrinks as 1/√R, crossing below the 0.08 gap at 7 gradings per item — the point where the true difference finally clears the judge's own error.

## Definition of done

The self-test pins the mechanism: the two models truly differ, the gap is inside the grader band at one grading, the SEM obeys the 1/√R law, enough gradings clear the band, and a perfectly consistent judge adds no noise at all.

```python filename=modules/evals-and-statistics/code/evals-inter-25/judgenoise.py:104-116 COMPLETE
    gap_positive = gap > 0
    print("  the two models truly differ = %s (gap %.3f)" % (gap_positive, gap))

    buried_at_one = gap < noise_band(a, b, n, 1)
    print("  at 1 grading the gap is inside the grader noise band = %s (%.3f < %.3f)" % (buried_at_one, gap, noise_band(a, b, n, 1)))

    sem1, sem4 = diff_sem(a, b, n, 1), diff_sem(a, b, n, 4)
    sqrt_law = abs(sem1 / sem4 - 2.0) < 1e-9
    print("  quadrupling the gradings halves the SEM (1/sqrt(R)) = %s (%.4f -> %.4f)" % (sqrt_law, sem1, sem4))

    need = min_replicates(a, b, n, gap)
    resolves = gap >= noise_band(a, b, n, need)
    print("  averaging %d gradings per item clears the band = %s (band %.3f <= gap %.3f)" % (need, resolves, noise_band(a, b, n, need), gap))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the gap is inside the grader noise at one grading; the SEM shrinks like 1/sqrt(R); enough gradings clear it
----------------------------------------------------------------------------------------------------------------------
  the two models truly differ = True (gap 0.080)
  at 1 grading the gap is inside the grader noise band = True (0.080 < 0.200)
  quadrupling the gradings halves the SEM (1/sqrt(R)) = True (0.1000 -> 0.0500)
  averaging 7 gradings per item clears the band = True (band 0.076 <= gap 0.080)
  a perfectly consistent judge (grader_var 0) adds no noise and resolves at R=1 = True
```

**Done means the grader's contribution is proven and located: a real 0.08 gap on 40 items is buried inside the judge's two-sigma noise band of 0.20 at one grading, the difference standard error shrinks exactly like 1/√R (0.10 → 0.05 from quadrupling), 7 gradings per item are needed to clear the band, and a perfectly consistent judge (grader_var 0) adds no noise and resolves the gap at a single grading — so the noise was the judge, not the models or the item count.**

## Boss fight

Predict the two ways this accounting still misleads — the noise it silently ignores, and the bias that no amount of re-grading removes. It is tempting to think "average enough gradings and the score is trustworthy."

The first trap is that grader noise is only one of the two variance components, and beating it does not beat the other. This module holds the item set fixed and studies only the judge, so its "noise band" is the grader-induced error alone; the item-sampling error — would the gap survive a different 40 items — is a separate term that more gradings do nothing for. A gap that clears the grader band on these items can still be an artifact of which items you happened to choose, so the honest interval combines both variances: grader noise (shrink with gradings) and item noise (shrink with items). Report only one and you will over-trust the result exactly when the other dominates. The two are multiplicative in effort, not interchangeable — you need both enough items and enough gradings — and the cheaper one to fix depends on which term is larger, which you only learn by estimating both.

```python filename=modules/evals-and-statistics/code/evals-inter-25/judgenoise.py:59-64 COMPLETE
def min_replicates(a, b, n_items, gap, sigmas=2.0, cap=200):
    """The fewest gradings per item that make the gap clear the noise band."""
    for r in range(1, cap + 1):
        if gap >= noise_band(a, b, n_items, r, sigmas):
            return r
    return None
```

The second trap is that averaging gradings shrinks variance but not bias, and an LLM judge has plenty of bias. Re-grading reduces the random wobble around the judge's expected verdict; it does nothing about the fact that the expected verdict may be systematically wrong — the judge may favor longer answers, prefer its own model family, reward confident phrasing, or be swayed by answer order. Grade such a judge a thousand times and you get a very precise measurement of a biased quantity: a tight confidence interval around the wrong number. So the two problems are orthogonal and both must be handled — variance by more gradings (this module), bias by blinding the judge to provenance, controlling for length, randomizing order, and validating the judge against human labels. A confident, low-variance eval built on a biased judge is more dangerous than a noisy one, because its tight interval invites the trust its bias does not deserve. Precision is not accuracy; re-grading buys the first and not the second.

**An LLM judge is a stochastic instrument, so compare a model gap against the grader's noise band (2σ of the difference's grader-induced SEM) and shrink that band with more gradings per item, not more items, since it falls like 1/√R — but grader noise is only one variance component (item-sampling noise, fixed by more items, is the other, and the honest interval combines both), and averaging reduces variance not bias, so a judge that is systematically biased must also be blinded and validated, because more gradings only make a biased score more precisely wrong.**

## External resources

Any measurement-theory or generalizability-theory reference on separating measurement error from sampling error and on variance components — the framework behind treating a rater as a source of variance distinct from the items.

Writing on LLM-as-judge reliability, judge temperature, and self-consistency / majority-vote grading — the practical techniques for estimating and reducing grader variance by re-grading, and for measuring inter-run agreement.

The companion "the judge agrees 80% of the time" (chance-corrected agreement) and "bootstrap a confidence interval" modules — the first quantifies how good the judge is against gold labels (its bias and reliability), and the second captures the item-sampling half of the total eval variance this module deliberately holds fixed.
