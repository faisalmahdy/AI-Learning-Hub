---
id: evals-inter-21
title: Correct for multiple comparisons — test enough metrics and a false winner is guaranteed by luck
topic: evals-and-statistics
level: intermediate
status: ready
time: 19 min
summary: A single significance test at alpha=0.05 accepts a 5% false-positive rate — for one test. Compare two truly identical models across many metrics and declare a win if any of them is significant, and you run that 5% gamble many times and keep the luckiest outcome: the chance that at least one of ten independent null tests trips 0.05 is 1-(1-0.05)^10 = 40%, not 5%. Bonferroni spends the budget across the family — require each test to clear alpha/m instead of alpha — pulling the family-wise error back to about alpha. On two identical models compared across 10 metrics over 8000 trials, declaring a win on any uncorrected metric is a false positive 39.9% of the time (8x nominal); the Bonferroni alpha/m threshold holds it at 5.0%, matching the theoretical 4.89%.
eli5: If you flip ten coins and get to shout "rigged!" the moment any one lands on a rare streak, you will shout "rigged!" almost every time, even with fair coins — you gave yourself ten chances at a one-in-twenty event. Testing a model on ten different scores works the same way: check enough of them and one will look like a win by pure luck. The fix is to make each score clear a much higher bar, so the whole batch together still only fools you one time in twenty.
---

## Why this module

The 5% you allow a single significance test is a budget for one test, and the moment you compare on many metrics and keep whichever is significant, you spend that budget over and over until luck hands you a win.

A test at alpha=0.05 means: if the two systems are truly identical, one run in twenty says "different" anyway. That is the deal for a single comparison. But an eval rarely reports one number — it reports accuracy, latency, refusal rate, cost, and a dozen task subscores, and the temptation is to scan them and announce a win on whichever crossed significance. Now you are not running one 5% gamble, you are running ten, and reporting the luckiest. Under the null the chance that at least one of ten independent tests trips 0.05 is `1-(1-0.05)^10 = 0.40`. A false positive is no longer a 5% risk you accepted; it is the most likely outcome.

**Each significance test spends 5% of false-positive budget; run the family and keep any hit, and the family-wise error is 1-(1-alpha)^m — testing ten metrics turns a 5% risk into a 40% one.**

The fix is to spend the budget across the whole family rather than per test. Bonferroni is the simplest: to hold the family-wise error at alpha over m tests, require each individual test to clear alpha/m. Ten metrics means each must beat 0.005, not 0.05, and the chance any of them trips falls back to about 5%. You did not run fewer tests — you raised the bar each one clears so the battery together still risks only 5%. This module simulates two identical models across many metrics and measures how often each rule declares a false winner.

## Concepts

The **per-test alpha** is the false-positive rate of one comparison: 0.05 means a 1-in-20 chance of "significant" when nothing is really different.

The **family-wise error rate (FWER)** is the chance of *at least one* false positive across the whole set of tests. For m independent null tests it is `1-(1-alpha)^m`, which climbs fast: 0.40 at ten tests, 0.64 at twenty.

**Keeping any hit** is the trap. Reporting "the model is better — look, metric 7 is significant" out of a dozen metrics is not one test at 0.05; it is the maximum of a dozen, and the maximum crosses the line far more often than any single one.

**Bonferroni correction** divides the threshold: each test must clear alpha/m. The union bound guarantees the FWER stays at or below alpha, so the whole family together risks only the budget you intended one test to risk.

**Correction trades power for honesty.** A tighter per-test threshold makes it harder to detect a real difference too, so Bonferroni is conservative; when many tests are correlated, less blunt methods (Holm, Benjamini-Hochberg) recover power. But some correction is not optional — reporting the best of many uncorrected tests is how a tie becomes a headline.

**The false-positive budget is a property of the whole family of tests, not each one; declare a win on any of m metrics and you must divide the threshold by m, or the batch fools you far more than the 5% you signed up for.**

<svg role="img" aria-label="The family-wise error rate 1 minus (1 minus 0.05) to the m rises from 0.05 at one test to 0.64 at twenty tests" viewBox="0 0 300 130" width="300" height="130">
  <text x="10" y="12" fill="var(--muted)" font-size="8">FWER = 1-(1-0.05)^m as tests m grow</text>
  <line x1="30" y1="20" x2="30" y2="105" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="105" x2="285" y2="105" stroke="var(--grid)" stroke-width="1"/>
  <polyline points="42,100 72,80 102,70 162,52 282,20" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <circle cx="42" cy="100" r="2.5" fill="var(--s1)"/><text x="34" y="116" fill="var(--muted)" font-size="7">m=1</text><text x="46" y="98" fill="var(--muted)" font-size="7">0.05</text>
  <circle cx="102" cy="70" r="2.5" fill="var(--s1)"/><text x="92" y="116" fill="var(--muted)" font-size="7">5</text><text x="96" y="66" fill="var(--muted)" font-size="7">0.23</text>
  <circle cx="162" cy="52" r="2.5" fill="var(--s1)"/><text x="150" y="116" fill="var(--muted)" font-size="7">10</text><text x="156" y="48" fill="var(--muted)" font-size="7">0.40</text>
  <circle cx="282" cy="20" r="2.5" fill="var(--s1)"/><text x="270" y="116" fill="var(--muted)" font-size="7">20</text><text x="262" y="16" fill="var(--muted)" font-size="7">0.64</text>
  <text x="34" y="128" fill="var(--muted)" font-size="8">the nominal 5% holds only at m=1; by ten tests it is 40%</text>
</svg>
^ The family-wise error climbs steeply with the number of tests — 5% at one, 40% at ten, 64% at twenty — so the more metrics you scan, the more certain a false win becomes.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/evals-inter-21/multiplecomparisons.py

The fixture sets the number of metrics, the alpha, and seeds for the simulation.

```json filename=modules/evals-and-statistics/code/evals-inter-21/multiplecomparisons.json:1-8 COMPLETE
{
  "_meta": "A family-wise-error simulation for multiple comparisons. Suppose two models are TRULY identical (the null hypothesis is true) and you compare them on `metrics` different measures — accuracy, latency, refusal rate, and so on. Under the null, each test's p-value is uniform on [0,1], so each has a 5% chance of falling below alpha=0.05 by pure luck. If you declare a difference whenever ANY metric is significant, the chance of at least one false positive across `metrics` tests is 1-(1-alpha)^metrics, far above alpha. Bonferroni tightens each test's threshold to alpha/metrics, pulling the family-wise error back down to about alpha. We simulate `trials` runs (seed = base_seed + trial), each drawing `metrics` null p-values, and measure how often at least one test fires under each rule. example_seed shows one concrete trial.",
  "metrics": 10,
  "alpha": 0.05,
  "trials": 8000,
  "base_seed": 42,
  "example_seed": 15
}
```

Under the null each p-value is uniform on [0,1]; a family "wins" if any metric clears the threshold; the FWER is the fraction of trials that win, with or without the alpha/m correction.

```python filename=modules/evals-and-statistics/code/evals-inter-21/multiplecomparisons.py:41-56 COMPLETE
def null_pvalues(metrics, seed):
    """Under the null hypothesis each test's p-value is uniform on [0,1]."""
    rng = random.Random(seed)
    return [rng.random() for _ in range(metrics)]


def any_significant(pvalues, threshold):
    """A family 'wins' if at least one metric clears the threshold."""
    return any(p < threshold for p in pvalues)


def fwer(metrics, alpha, trials, base_seed, corrected):
    """Fraction of trials with at least one false positive. corrected=True uses the alpha/m Bonferroni threshold."""
    threshold = alpha / metrics if corrected else alpha
    hits = sum(any_significant(null_pvalues(metrics, base_seed + i), threshold) for i in range(trials))
    return hits / trials
```

One trial makes the trap concrete. Run `--trial`.

```text filename=--trial
TRIAL — one run's 10 null p-values (seed 15), thresholds alpha=0.050 and alpha/m=0.0050
------------------------------------------------------------------
  p-values: ['0.965', '0.012', '0.736', '0.158', '0.986', '0.017', '0.879', '0.681', '0.857', '1.000']
  significant uncorrected (p<0.050):   [0.012, 0.017]  -> FALSE POSITIVE
  significant bonferroni  (p<0.0050):  []  -> correctly no win
------------------------------------------------------------------
  the models are identical; the uncorrected 'hits' are luck the tighter threshold rejects.
```

The two models are identical, so every one of these ten p-values is noise. But two of them — 0.012 and 0.017 — fell below 0.05 by chance, and an uncorrected reader would report a significant difference on two metrics and call it a win. The Bonferroni threshold of 0.005 is below both, so it correctly finds nothing. The "significant" metrics were the luckiest two draws out of ten, exactly what you expect when you take the minimum of many uniform numbers.

<svg role="img" aria-label="Ten null p-values scattered on a 0 to 1 axis; two fall below the 0.05 line but none below the 0.005 Bonferroni line" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">10 null p-values (models identical) on a 0→1 axis</text>
  <line x1="20" y1="60" x2="285" y2="60" stroke="var(--grid)" stroke-width="1"/>
  <line x1="33" y1="30" x2="33" y2="70" stroke="var(--s1)" stroke-width="1" stroke-dasharray="3 2"/><text x="24" y="26" fill="var(--s1)" font-size="7">0.05</text>
  <line x1="21" y1="30" x2="21" y2="70" stroke="var(--s2)" stroke-width="1" stroke-dasharray="3 2"/><text x="8" y="86" fill="var(--s2)" font-size="7">0.005</text>
  <circle cx="24" cy="60" r="3" fill="var(--s1)"/><circle cx="25" cy="60" r="3" fill="var(--s1)"/>
  <circle cx="61" cy="60" r="3" fill="var(--ink)"/><circle cx="215" cy="60" r="3" fill="var(--ink)"/><circle cx="180" cy="60" r="3" fill="var(--ink)"/><circle cx="253" cy="60" r="3" fill="var(--ink)"/><circle cx="240" cy="60" r="3" fill="var(--ink)"/><circle cx="245" cy="60" r="3" fill="var(--ink)"/><circle cx="281" cy="60" r="3" fill="var(--ink)"/><circle cx="200" cy="60" r="3" fill="var(--ink)"/>
  <text x="40" y="100" fill="var(--muted)" font-size="8">two points cross 0.05 by luck; none cross the tighter 0.005 bar</text>
</svg>
^ Two of ten null p-values slip under the 0.05 line by chance — enough for an uncorrected "win" — but the Bonferroni line at 0.005 is stricter than either, so it reports no difference.

## Build

The rate view runs the same trials under both thresholds and prints each against the theoretical curve.

```python filename=modules/evals-and-statistics/code/evals-inter-21/multiplecomparisons.py:62-65 COMPLETE
    m, a, tr, bs = data["metrics"], data["alpha"], data["trials"], data["base_seed"]
    unc = fwer(m, a, tr, bs, False)
    bon = fwer(m, a, tr, bs, True)
    theory = 1 - (1 - a) ** m
```

One trial is luck; the rate over many trials is the law. Run `--rate`.

```text filename=--rate
RATE — family-wise false-positive rate over 8000 trials (10 metrics, alpha 0.05)
------------------------------------------------------------------
  nominal per-test alpha:      0.050
  uncorrected (any metric):    0.399   (theory 0.401 — 8x alpha)
  bonferroni (alpha/m=0.0050): 0.050   (back under alpha)
------------------------------------------------------------------
  testing 10 metrics and keeping any hit turns a 5% risk into a 40% one.
```

Across 8000 simulated eval runs of two identical models, the uncorrected rule declares a false winner 39.9% of the time — eight times the 5% you thought you were risking, and a near-perfect match to the theoretical `1-(1-0.05)^10 = 0.401`. The Bonferroni rule fires in 5.0% of runs, matching its theoretical 4.89%: the correction did exactly its job, holding the whole family to the budget of a single test. Note the correction changed nothing about the data or the number of tests — it only moved the threshold, and that alone collapsed the error from 40% to 5%.

<svg role="img" aria-label="Uncorrected family-wise error is 0.399, Bonferroni is 0.050, against a nominal alpha of 0.05" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">family-wise false-positive rate (nominal alpha = 0.05)</text>
  <line x1="55" y1="20" x2="55" y2="92" stroke="var(--grid)" stroke-width="1"/>
  <line x1="55" y1="92" x2="285" y2="92" stroke="var(--grid)" stroke-width="1"/>
  <line x1="66" y1="20" x2="66" y2="92" stroke="var(--line)" stroke-width="1" stroke-dasharray="3 3"/><text x="60" y="18" fill="var(--muted)" font-size="7">alpha</text>
  <rect x="55" y="28" width="212" height="20" fill="var(--s1)"/><text x="150" y="42" fill="var(--panel)" font-size="8">uncorrected: 0.399 (8x)</text>
  <rect x="55" y="58" width="12" height="20" fill="var(--s2)"/><text x="72" y="72" fill="var(--muted)" font-size="8">bonferroni: 0.050</text>
  <text x="55" y="108" fill="var(--muted)" font-size="8">the dashed line is alpha; uncorrected overshoots 8x, Bonferroni lands on it</text>
</svg>
^ The uncorrected bar runs 8x past the alpha line; the Bonferroni bar sits right on it — same tests, same data, only the threshold moved.

## Definition of done

The self-test pins the claims: the uncorrected rate blows past alpha, Bonferroni's theoretical FWER is at or under alpha, its empirical rate collapses below the uncorrected one, both match theory, and the run is reproducible.

```python filename=modules/evals-and-statistics/code/evals-inter-21/multiplecomparisons.py:99-112 COMPLETE
    uncorrected_above_alpha = unc > 3 * a
    print("  uncorrected family-wise error far exceeds alpha = %s (%.3f > %.3f)" % (uncorrected_above_alpha, unc, 3 * a))

    bonferroni_theory_controls = theory_bon <= a
    print("  Bonferroni's family-wise error (theory 1-(1-a/m)^m) is <= alpha = %s (%.4f <= %.3f)" % (bonferroni_theory_controls, theory_bon, a))

    bonferroni_far_below_uncorrected = bon < unc / 3
    print("  Bonferroni's error rate collapses below the uncorrected one = %s (%.3f < %.3f)" % (bonferroni_far_below_uncorrected, bon, unc / 3))

    matches_theory = abs(unc - theory_unc) < 0.02 and abs(bon - theory_bon) < 0.02
    print("  both rates match their theory within noise = %s (unc %.3f~%.3f, bon %.3f~%.3f)" % (matches_theory, unc, theory_unc, bon, theory_bon))

    unc_again = fwer(m, a, tr, bs, False)
    deterministic = unc == unc_again
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the uncorrected rate blows past alpha; Bonferroni holds it under alpha; threshold is alpha/m
--------------------------------------------------------------------------------------------------------
  uncorrected family-wise error far exceeds alpha = True (0.399 > 0.150)
  Bonferroni's family-wise error (theory 1-(1-a/m)^m) is <= alpha = True (0.0489 <= 0.050)
  Bonferroni's error rate collapses below the uncorrected one = True (0.050 < 0.133)
  both rates match their theory within noise = True (unc 0.399~0.401, bon 0.050~0.049)
  the seeded simulation is reproducible = True (0.3985)
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  uncorrected_above_alpha=True  bonferroni_theory_controls=True  bonferroni_far_below_uncorrected=True  matches_theory=True  deterministic=True
```

**Done means the inflation and the fix are both measured: across 8000 runs of two identical models, keeping any of 10 uncorrected metrics is a false positive 39.9% of the time (matching 1-(1-alpha)^m = 0.401), while the alpha/m threshold holds it to 5.0% (matching 0.0489).**

## Boss fight

Bonferroni fixed the false positives. Predict what it does to your ability to detect a difference that is *real*, and whether dividing by m is always the right correction. It is tempting to slap alpha/m on everything and call multiplicity solved.

Bonferroni buys its error control with statistical power: a threshold of 0.005 rejects more true differences too, so a real but modest effect on one metric can now miss significance it would have made alone. That is the correct trade when the metrics are independent, but real eval metrics are usually correlated — accuracy and F1 move together, latency and cost move together — and Bonferroni assumes the worst case of independence, so it over-corrects and throws away power you did not need to spend. Holm's step-down method controls the same family-wise error less bluntly, and Benjamini-Hochberg controls the false *discovery* rate (the expected fraction of your "wins" that are false) instead of the chance of any false win, which is usually what you actually care about when screening many metrics. The lesson is not "always divide by m"; it is "spend the budget across the family, with a method matched to how many true effects you expect and how correlated the tests are."

The deeper trap is not counting the tests at all. Every metric you glance at, every subgroup you slice, every threshold you retune is a comparison, and the multiplicity is over *all* of them, not just the ones you wrote up. Decide the metrics and the analysis before you look — pre-register them — because a correction applied only to the tests you remember running is no correction. The honest denominator is the number of chances you gave luck, and that number is almost always larger than the table in the report admits.

```python filename=modules/evals-and-statistics/code/evals-inter-21/multiplecomparisons.py:52-56 COMPLETE
def fwer(metrics, alpha, trials, base_seed, corrected):
    """Fraction of trials with at least one false positive. corrected=True uses the alpha/m Bonferroni threshold."""
    threshold = alpha / metrics if corrected else alpha
    hits = sum(any_significant(null_pvalues(metrics, base_seed + i), threshold) for i in range(trials))
    return hits / trials
```

**Declaring a win on any of m metrics inflates the false-positive rate to 1-(1-alpha)^m, so spend the budget across the whole family — Bonferroni's alpha/m is the blunt floor, Holm and Benjamini-Hochberg recover power, and the count m must include every metric, slice, and threshold you tried, not just the ones you reported.**

## External resources

Any statistics text's chapter on multiple comparisons — the Bonferroni, Holm, and Benjamini-Hochberg procedures side by side, with the family-wise-error versus false-discovery-rate distinction.

The xkcd "Significant" comic (jelly beans and acne) — the canonical one-panel illustration of testing twenty colors and reporting the one that reached p<0.05.

The companion "a null result from a small eval is not no difference" and "the winner's curse" modules — power and multiplicity are the two halves of not fooling yourself: one is about missing real effects, the other about inventing fake ones.
