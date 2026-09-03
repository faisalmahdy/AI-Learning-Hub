---
id: data-inter-13
title: Significance is not size — with enough data a trivial difference gets a tiny p-value that means nothing
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 21 min
summary: A p-value asks whether a difference is real; it says nothing about whether the difference is big enough to matter. Because the test statistic grows with the square root of n, a fixed effect gets an ever-smaller p-value as data piles up. A 1-point difference on a scale with standard deviation 10 (Cohen's d = 0.1, trivial) goes from p=0.823 at n=10 to p=1.5e-12 at n=10000 — same negligible effect, p-value measuring the sample size, not the importance.
eli5: A magnifying glass lets you see something is really there, but it does not make the thing bigger. With a huge amount of data you can prove a tiny difference is real — but real and important are different things. Always ask how big the difference is, not just whether it's real.
---

## Why this module

A p-value tells you a difference is probably real; it never tells you the difference is big enough to care about, and at large sample sizes people forget that.

The p-value answers one narrow question: if there were truly no difference between the groups, how surprising would data this extreme be? A small p-value means "you'd rarely see a gap this big by chance alone," which licenses you to believe the gap is real. That is all it says. It does not say the gap is large, important, or worth acting on. Those are questions about the size of the effect, and the p-value is silent on them.

The two questions come apart completely as the sample grows, and the reason is mechanical. The test statistic for comparing two groups is the observed difference divided by its standard error, and the standard error shrinks like one over the square root of n. So for a fixed real difference, the statistic grows like the square root of n, and the p-value falls toward zero — not because the effect got bigger, but because more data made your estimate precise enough to resolve an effect that was always there and always tiny. Pour in enough data and any nonzero difference, however microscopic, becomes "statistically significant." The p-value at large n is measuring your sample size as much as the world.

The fix is to report the effect size alongside the p-value. Cohen's d — the difference expressed in standard-deviation units — measures how big the gap is, and crucially it does not change with n, because it is a property of the populations, not the sample. A d of 0.1 is trivially small whether you measured ten points or a million; only its p-value moves. A claim needs both numbers: the effect size says whether it matters, and the p-value (with a confidence interval) says whether you have enough data to believe it is real. Reporting significance without size is how a nothing-difference gets dressed up as a discovery.

On the fixture two groups differ by 1 point on a scale with a standard deviation of 10 — a Cohen's d of 0.1, trivially small. As n grows from 10 to 10000, the effect size stays exactly 0.1 while the two-sided p-value falls from 0.823 (nowhere near significant) to 1.5e-12 (wildly significant). Same negligible effect; the p-value is tracking the sample size, not the importance.

**A p-value asks whether a difference is real, not whether it is big; the test statistic grows with the square root of n, so a fixed trivial effect earns an ever-tinier p-value as data accumulates — report the effect size, which is a population fact and does not move with n.**

## Concepts

Two different quantities get conflated under the word "significant," and separating them is the whole lesson. Statistical significance is about evidence: do you have enough data to rule out chance? Practical significance is about magnitude: is the effect large enough to matter? A result can be any combination of the two — real and large (the ideal), real and trivial (the large-n trap this module is about), not-yet-established and large (worth collecting more data), or not-established and trivial. The p-value speaks only to the first axis. Reading it as if it spoke to the second is the error.

<svg role="img" aria-label="A two-by-two grid of real versus trivial effect against established versus not-established significance, marking the large-n trap cell" viewBox="0 0 470 190" width="470" height="190">
  <rect x="0" y="0" width="470" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">significance (evidence) vs effect size (magnitude)</text>
  <text x="120" y="46" font-family="var(--mono)" font-size="9" fill="var(--ink)">effect trivial</text>
  <text x="300" y="46" font-family="var(--mono)" font-size="9" fill="var(--ink)">effect large</text>
  <text x="12" y="90" font-family="var(--mono)" font-size="8" fill="var(--ink)">not sig.</text>
  <text x="12" y="150" font-family="var(--mono)" font-size="8" fill="var(--ink)">significant</text>
  <rect x="110" y="60" width="160" height="50" fill="var(--panel)" stroke="var(--line)"/>
  <text x="120" y="82" font-family="var(--mono)" font-size="8" fill="var(--muted)">nothing, unproven</text>
  <text x="120" y="98" font-family="var(--mono)" font-size="8" fill="var(--muted)">(correctly ignored)</text>
  <rect x="280" y="60" width="160" height="50" fill="var(--panel)" stroke="var(--line)"/>
  <text x="290" y="82" font-family="var(--mono)" font-size="8" fill="var(--muted)">real but need</text>
  <text x="290" y="98" font-family="var(--mono)" font-size="8" fill="var(--muted)">more data</text>
  <rect x="110" y="118" width="160" height="50" fill="var(--s2)"/>
  <text x="120" y="140" font-family="var(--mono)" font-size="8" fill="var(--ink)">LARGE-n TRAP:</text>
  <text x="120" y="156" font-family="var(--mono)" font-size="8" fill="var(--ink)">real but trivial</text>
  <rect x="280" y="118" width="160" height="50" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="290" y="140" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">real and big</text>
  <text x="290" y="156" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">(the ideal)</text>
</svg>
^ The p-value tells you only which row you are in; the effect size tells you the column. The large-n trap is the bottom-left cell — significant and trivial — which a p-value alone cannot distinguish from the bottom-right ideal.

The mechanics are worth seeing explicitly. The two-sample statistic is the difference in means divided by the standard error of that difference, and with equal group sizes the standard error is proportional to the standard deviation over the square root of n. Hold the difference and the standard deviation fixed, and the statistic is proportional to the square root of n: quadruple the sample and the statistic doubles, so the p-value drops. Nothing about the effect changed — the same 1-point gap on the same 10-unit scale — but the estimate tightened, and a tight estimate around a tiny nonzero value is exactly what produces a tiny p-value. The p-value is a statement about precision, and precision is bought with sample size.

Cohen's d is the antidote because it is dimensionless and n-free. It divides the raw difference by the standard deviation, giving the gap in units of the population's spread: d = 0.1 means the two group means sit a tenth of a standard deviation apart, which is a large overlap and a small effect by any convention (0.2 is the usual threshold for "small," 0.5 for "medium," 0.8 for "large"). Because both the difference and the standard deviation are population quantities, d does not change when you collect more data — you just estimate the same d more precisely. That invariance is exactly why it, not the p-value, answers "does this matter?"

The practical upshot is that a claim should always carry an effect size and, ideally, a confidence interval — the range of effect sizes the data is consistent with. A confidence interval does both jobs at once: it excludes zero when the result is significant, and its width and location tell you whether the plausible effects are large enough to care about. A significant result whose entire confidence interval sits within the trivial range is a precisely estimated nothing. In large-n settings — web-scale A/B tests, big observational datasets, anything in "AI for science" where n is enormous — this is the default failure, because at those sample sizes essentially everything is significant.

**Statistical significance (is it real?) and practical significance (is it big?) are different axes; the p-value measures the first and buys it with sample size, while Cohen's d measures the second and is invariant to n — so report the effect size and a confidence interval, not significance alone.**

## Worked example

The fixture is two group means, a standard deviation, and a set of sample sizes to test the same difference at.

```json filename=modules/ai-for-science-and-data/code/data-inter-13/groups.json:3-6 COMPLETE
  "mean1": 100,
  "mean2": 101,
  "sd": 10,
  "sample_sizes": [10, 100, 1000, 10000]
```

A 1-point difference on a scale whose standard deviation is 10. The effect size is that difference divided by the standard deviation — and it uses no sample size at all.

```python filename=modules/ai-for-science-and-data/code/data-inter-13/significance.py:44-52 COMPLETE
def cohens_d(mean1, mean2, sd):
    """Effect size: the difference in standard-deviation units -- independent of sample size."""
    return abs(mean1 - mean2) / sd


def t_statistic(mean1, mean2, sd, n):
    """Two-sample statistic with equal n and sd -- grows with sqrt(n) for a fixed difference."""
    se = sd * math.sqrt(2.0 / n)
    return abs(mean1 - mean2) / se
```

Cohen's d is 1/10 = 0.1 for every n. The statistic divides that same 1-point difference by a standard error that shrinks as n grows, so it climbs with the square root of n. The p-value comes from the statistic through the normal error function — pure standard library.

```python filename=modules/ai-for-science-and-data/code/data-inter-13/significance.py:55-58 COMPLETE
def two_sided_p(z):
    """Two-sided p-value under a normal approximation, via the error function (stdlib)."""
    phi = 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0)))
    return 2.0 * (1.0 - phi)
```

Predict: d is flat at 0.1, while the p-value starts far above 0.05 at n=10 and marches down past significance to the trillionths by n=10000. Run it.

```text filename=modules/ai-for-science-and-data/code/data-inter-13/significance.py --table
TABLE — a 1-point difference (sd 10) at growing sample sizes
----------------------------------------------------------
  n        effect size d   t-stat    p-value      significant?
  10             0.100     0.224   0.823       no
  100            0.100     0.707   0.48        no
  1000           0.100     2.236   0.0253      yes
  10000          0.100     7.071   1.54e-12    yes
----------------------------------------------------------
  the effect size never moves; only the p-value does.
```

The effect size is 0.100 on every row — the difference did not change, because it cannot: it is a fact about the two populations. The p-value, though, falls from 0.823 at n=10 (a difference this small in ten points is utterly unsurprising by chance) through 0.0253 at n=1000 (now "significant") to 1.54e-12 at n=10000 (a number you would report as overwhelming evidence). The exact same trivial 0.1-standard-deviation gap is "not significant" with a small sample and "highly significant" with a large one. If you read only the last row's p-value, you would announce a strong finding; the effect-size column tells you the finding is that the groups are essentially identical.

<svg role="img" aria-label="As n grows, the p-value drops below the significance line and keeps falling while the effect size stays flat at 0.1" viewBox="0 0 470 190" width="470" height="190">
  <rect x="0" y="0" width="470" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">p-value (falls) vs effect size (flat) across n = 10..10000</text>
  <line x1="45" y1="160" x2="450" y2="160" stroke="var(--line)"/>
  <line x1="45" y1="40" x2="45" y2="160" stroke="var(--line)"/>
  <line x1="45" y1="120" x2="450" y2="120" stroke="var(--acc-line)" stroke-dasharray="3 3"/>
  <text x="360" y="116" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">p = 0.05</text>
  <polyline points="80,52 190,80 300,128 410,156" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <g fill="var(--s2)"><circle cx="80" cy="52" r="3"/><circle cx="190" cy="80" r="3"/><circle cx="300" cy="128" r="3"/><circle cx="410" cy="156" r="3"/></g>
  <text x="150" y="48" font-family="var(--mono)" font-size="8" fill="var(--s2)">p-value collapses with n</text>
  <line x1="80" y1="138" x2="410" y2="138" stroke="var(--s1)" stroke-width="2"/>
  <g fill="var(--s1)"><circle cx="80" cy="138" r="3"/><circle cx="190" cy="138" r="3"/><circle cx="300" cy="138" r="3"/><circle cx="410" cy="138" r="3"/></g>
  <text x="150" y="152" font-family="var(--mono)" font-size="8" fill="var(--s1)">effect size d = 0.1, flat</text>
  <text x="70" y="176" font-family="var(--mono)" font-size="8" fill="var(--muted)">n=10</text>
  <text x="385" y="176" font-family="var(--mono)" font-size="8" fill="var(--muted)">n=10000</text>
</svg>
^ The p-value crosses the 0.05 line and keeps plunging as n grows, while the effect size holds flat at 0.1 — significance is bought with sample size; importance is not.

## Build

Reproduce the table. Pure standard library, deterministic, so the p-values from 0.823 down to 1.54e-12 and the flat 0.1 effect size come out exactly.

Run `--table` for the full grid, `--effect` for the two sequences side by side, `--check` for the gate. The effect view puts the invariance and the collapse next to each other.

```text filename=modules/ai-for-science-and-data/code/data-inter-13/significance.py --effect
EFFECT — Cohen's d is a population fact; the p-value is a sample-size fact
----------------------------------------------------------
  sample sizes:   [10, 100, 1000, 10000]
  effect size d:  [0.1, 0.1, 0.1, 0.1]   (constant)
  p-value:        ['0.82', '0.48', '0.025', '1.5e-12']   (collapses)
----------------------------------------------------------
  d=0.10 is 'small' by convention (<0.2); it is trivial at every n.
```

Each row of the table is assembled by one helper that computes the invariant effect size and the n-dependent statistic and p-value together.

```python filename=modules/ai-for-science-and-data/code/data-inter-13/significance.py:61-64 COMPLETE
def row(data, n):
    d = cohens_d(data["mean1"], data["mean2"], data["sd"])
    t = t_statistic(data["mean1"], data["mean2"], data["sd"], n)
    return {"n": n, "d": d, "t": t, "p": two_sided_p(t)}
```

The `d` line takes no `n`; the `t` line takes `n` — that single asymmetry is the whole phenomenon, one number fixed and one growing with the sample.

<svg role="img" aria-label="Bar chart of the t-statistic rising with sqrt of n from 0.22 to 7.07, crossing the significance threshold, while the effect size bars stay equal" viewBox="0 0 470 180" width="470" height="180">
  <rect x="0" y="0" width="470" height="180" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">t-statistic grows with sqrt(n); crosses ~1.96 for p&lt;0.05</text>
  <line x1="45" y1="150" x2="450" y2="150" stroke="var(--line)"/>
  <line x1="45" y1="128" x2="450" y2="128" stroke="var(--acc-line)" stroke-dasharray="3 3"/>
  <text x="360" y="124" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">t ≈ 1.96</text>
  <g fill="var(--s2)"><rect x="70" y="147" width="50" height="3"/><rect x="170" y="141" width="50" height="9"/><rect x="270" y="122" width="50" height="28"/><rect x="370" y="62" width="50" height="88"/></g>
  <text x="78" y="166" font-family="var(--mono)" font-size="8" fill="var(--muted)">10: 0.22</text>
  <text x="176" y="166" font-family="var(--mono)" font-size="8" fill="var(--muted)">100: 0.71</text>
  <text x="270" y="166" font-family="var(--mono)" font-size="8" fill="var(--muted)">1000: 2.24</text>
  <text x="366" y="166" font-family="var(--mono)" font-size="8" fill="var(--muted)">10000: 7.07</text>
</svg>
^ The statistic climbs with the square root of n — 0.22, 0.71, 2.24, 7.07 — crossing the ~1.96 significance line between n=100 and n=1000, all from the same fixed 0.1 effect.

The self-test pins the whole story: the p-value falls monotonically with n, Cohen's d is identical at every sample size, that d is trivially small, and the same difference flips from not-significant at the smallest n to highly significant at the largest.

```python filename=modules/ai-for-science-and-data/code/data-inter-13/significance.py:102-105 COMPLETE
    p_shrinks_with_n = all(ps[i] > ps[i + 1] for i in range(len(ps) - 1))
    print("  the p-value falls monotonically as n grows = %s (%s)" % (p_shrinks_with_n, ["%.2g" % x for x in ps]))

    effect_constant = max(ds) - min(ds) < 1e-12
    print("  Cohen's d is identical at every sample size = %s (%.3f)" % (effect_constant, ds[0]))
```

```text filename=modules/ai-for-science-and-data/code/data-inter-13/significance.py --check
SELF-TEST — the p-value shrinks with n while the effect size stays fixed and trivial
--------------------------------------------------------------------------------------------
  the p-value falls monotonically as n grows = True (['0.82', '0.48', '0.025', '1.5e-12'])
  Cohen's d is identical at every sample size = True (0.100)
  the effect size is trivially small (d < 0.2) = True (0.100)
  at the smallest n the difference is not significant = True (p=0.823)
  at the largest n the same nothing is 'highly significant' = True (p=1.54e-12)
--------------------------------------------------------------------------------------------
SELF-TEST PASS  p_shrinks_with_n=True  effect_constant=True  effect_trivial=True  small_n_not_significant=True  large_n_significant=True
```

Five True flags. P_shrinks_with_n: the p-value falls at every step as data accumulates. Effect_constant and effect_trivial: Cohen's d is 0.100 at every n and below the 0.2 "small" threshold — the effect never changes and never mattered. Small_n_not_significant and large_n_significant: the identical difference is p=0.823 at n=10 and p=1.5e-12 at n=10000, so significance is entirely a function of sample size here. The two constant-effect flags are the ones that expose the trap: the thing the p-value is dramatizing did not move.

**The effect-size flags are the tell — d is 0.100 and trivial at every sample size, so the p-value's march from 0.823 to 1.5e-12 is measuring how much data you have, not how big the difference is.**

## Definition of done

You are done when you reproduce the p-value collapse and can explain why the effect size does not follow it.

Concretely: `--table` shows d flat at 0.100 while the p-value falls from 0.823 to 1.54e-12 across n; `--effect` shows the constant-versus-collapsing sequences; `--check` prints PASS with five True flags. You can distinguish statistical significance (is the effect real?) from practical significance (is it big?) and explain that the test statistic scales with the square root of n so the p-value tracks sample size. You can explain why Cohen's d is invariant to n — it divides by the standard deviation, a population quantity — and why a confidence interval on the effect size answers both questions at once.

The habit to carry: never report a p-value without an effect size, and prefer a confidence interval on the effect. When someone announces a "highly significant" result from a huge dataset, ask for the effect size before believing it matters; at large n, significance is nearly free and importance is the only thing that discriminates. A precisely estimated nothing is still nothing.

## Boss fight

The instructive failure is a product change that ships on a p-value and moves no real metric.

A team runs an A/B test with millions of users and finds the new checkout flow improves conversion with p < 0.0001 — "highly significant," so they ship it. Months later the revenue line has not budged. The effect size was a 0.05% absolute lift, well within the noise of everything else that changes month to month; with millions of users even that microscopic difference was resolved to a tiny p-value, and the team read the p-value as importance. Every future engineering quarter is now spent shipping changes that are "significant" and worthless. The fix is to set a minimum effect size worth caring about before running the test, power the test to detect that size, and report the observed effect size with a confidence interval — shipping only when the plausible effects are large enough to matter, not merely nonzero.

Your turn, two moves. First, find the n at which this trivial effect crosses significance. Add sample sizes between 100 and 1000 and locate where p first drops below 0.05; confirm it is around n=768 (where the square-root-of-n growth pushes the statistic past the critical value of about 1.96), and note that this crossing point is a fact about sample size, not about the effect, which was 0.1 the whole time. Second, flip the experiment: make the effect real (raise mean2 to 108 for d=0.8, a large effect) and shrink n to 10, and confirm you get a large effect size with a p-value that may still miss significance — the opposite failure, a real and important effect the study was too small to establish, which is why non-significant is not the same as no effect.

## External resources

The American Statistical Association's 2016 statement on p-values is the authoritative short treatment — it explicitly warns that a p-value does not measure effect size or importance, and that "statistical significance is not equivalent to scientific, human, or economic significance."

Jacob Cohen's "Statistical Power Analysis for the Behavioral Sciences" is the origin of Cohen's d and the small/medium/large conventions, and his essay "The Earth Is Round (p < .05)" is the classic polemic against reading significance as importance.

Any modern methods guide on estimation over testing (the "new statistics," e.g. Cumming) argues for reporting effect sizes and confidence intervals in place of bare p-values, which is the constructive version of this module's warning.
