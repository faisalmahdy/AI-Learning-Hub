---
id: practsig-inter-01
title: Judge the effect size against a threshold, not the p-value — a big enough sample makes a trivial effect "significant"
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: A p-value below 0.05 is treated as the finish line — the result is "significant", so ship it — but statistical significance answers only one narrow question (is the effect distinguishable from zero?) and answers even that in a way that depends on sample size. The standard error of an estimate shrinks as the sample grows, and the test statistic is the effect divided by that standard error, so for any real effect, however tiny, a large enough sample drives the statistic past the significance threshold. Significance is thus partly a statement about how much data you collected, not only how big the effect is; collect enough and a 0.1% lift no user would notice becomes statistically significant. The question significance does not answer is the one that decides an action: is the effect big enough to matter? That is practical significance, measured against a domain threshold — the smallest effect worth the cost of shipping and maintaining it. A result can be statistically significant (its interval excludes zero) and practically negligible (its whole interval sits below the threshold) at once; those answer different questions, and reading significance as importance conflates them, shipping a stream of real-but-meaningless changes each with a p-value to defend it. The fix is to report and decide on the effect size and its confidence interval against a pre-set threshold: an interval excluding zero but lying entirely below the threshold is a real effect too small to act on. On a fixture with a 0.2 percentage-point true effect and a 1pp practical threshold, at n=1000 it is not significant (z=0.089, CI [-4.18pp, 4.58pp]) while at n=1,000,000 the identical 0.2pp effect is significant (z=2.83, p=0.005, CI [0.06pp, 0.34pp]) — excluding zero yet entirely below the 1pp threshold.
eli5: Imagine you have a scale and you want to know if a new cookie recipe makes cookies heavier. If you weigh just a few cookies, the scale is jittery and you can't tell a real difference from random wobble. If you weigh a million cookies, the average becomes rock-steady, and now you can detect that the new cookies are heavier by — a hundredth of a gram. It's a real difference, and with enough cookies you can prove it's real. But a hundredth of a gram is nothing; no one would ever notice or care. So "we proved it's heavier" is true and useless at the same time. The thing to ask is not just "is it heavier?" but "is it heavier by enough to matter?" — and for that you look at how big the difference actually is, not just whether you managed to detect it.
---

## Why this module

Statistical significance has a gravitational pull on decisions: p < 0.05 reads as "true, act on it," and p ≥ 0.05 as "nothing there." Both readings are wrong often enough to matter, and the reason is that significance measures something narrower than people think. It measures whether an effect is distinguishable from zero given your data — and "given your data" is doing enormous work, because the same effect can be indistinguishable from zero in a small sample and unmistakable in a large one. At the sample sizes modern experiments reach (millions of users, billions of events), that pull ships a steady stream of changes that are real and pointless, each defended by a significant p-value.

The mechanism is mechanical. The test statistic is the effect divided by its standard error, and the standard error shrinks as the sample grows — roughly with the square root of n. So for any effect that is not exactly zero, you can make the test statistic as large as you like by collecting more data. Significance is therefore partly a report on your sample size. A 0.1% lift that no user would ever feel is genuinely there, and with ten million users behind it, it clears every significance bar you set.

What significance never tells you is whether the effect is big enough to act on. That is a separate judgment against a threshold you set from the domain. This module measures one fixed tiny effect at two sample sizes and shows significance flipping while the effect — and its irrelevance — stays put.

**Judge a result by its effect size and confidence interval against a pre-set practical threshold, not by statistical significance alone, because the test statistic grows with sample size for any nonzero effect — so a large enough sample makes a trivially small effect statistically significant while it remains far below the size worth acting on.**

## Concepts

The fixture fixes one true effect and varies only the sample size. The treatment lifts conversion by 0.2 percentage points over a 50% baseline; the team's practical threshold — the smallest lift worth shipping — is 1 percentage point. The effect is measured at n=1,000 and n=1,000,000 per arm.

```json filename=modules/evals-and-statistics/code/practsig-inter-01/practsig.json:3-6 COMPLETE
  "baseline_rate": 0.50,
  "effect": 0.002,
  "practical_threshold": 0.01,
  "sample_sizes": [1000, 1000000]
```

The standard error of the difference between two proportions shrinks with n, and the z-statistic is the effect divided by it — so z grows with n for a fixed effect.

```python filename=modules/evals-and-statistics/code/practsig-inter-01/practsig.py:53-63 COMPLETE
def standard_error(p, n):
    """SE of the difference between two proportions, each arm rate p and size n."""
    return math.sqrt(2 * p * (1 - p) / n)


def z_stat(effect, se):
    return effect / se


def p_value(z):
    """Two-sided p-value from a z-statistic (normal approximation)."""
    return math.erfc(abs(z) / math.sqrt(2))
```

The confidence interval carries both answers at once: whether it excludes zero (statistical significance) and where it sits relative to the practical threshold (practical significance).

```python filename=modules/evals-and-statistics/code/practsig-inter-01/practsig.py:66-73 COMPLETE
def conf_interval(effect, se):
    """95% confidence interval for the effect."""
    return effect - 1.96 * se, effect + 1.96 * se


def significant(z):
    return abs(z) >= 1.96
```

<svg role="img" aria-label="A number line with zero and a practical threshold marked; the small-n interval is very wide spanning zero, the large-n interval is narrow, excluding zero but sitting entirely left of the threshold" viewBox="0 0 320 130">
  <line x1="20" y1="70" x2="300" y2="70" stroke="var(--line)" stroke-width="1"/>
  <line x1="70" y1="20" x2="70" y2="120" stroke="var(--ink)" stroke-width="1" stroke-dasharray="3 3"/>
  <text x="60" y="16" font-size="8" fill="var(--ink)">0</text>
  <line x1="250" y1="20" x2="250" y2="120" stroke="var(--s2)" stroke-width="1.3" stroke-dasharray="4 3"/>
  <text x="220" y="16" font-size="8" fill="var(--s2)">threshold 1pp</text>
  <line x1="24" y1="48" x2="180" y2="48" stroke="var(--muted)" stroke-width="3"/>
  <circle cx="80" cy="48" r="3" fill="var(--muted)"/>
  <text x="24" y="42" font-size="8" fill="var(--muted)">n=1000 CI (spans 0 — not significant)</text>
  <line x1="74" y1="92" x2="92" y2="92" stroke="var(--s1)" stroke-width="4"/>
  <circle cx="83" cy="92" r="3" fill="var(--s1)"/>
  <text x="96" y="96" font-size="8" fill="var(--s1)">n=1e6 CI (excludes 0, below threshold)</text>
</svg>
^ The small-n interval is wide and straddles zero — not significant. The large-n interval is narrow, sits to the right of zero (significant) but entirely left of the 1pp threshold: a real effect, provably nonzero, provably too small to matter.

<svg role="img" aria-label="A curve of standard error falling as sample size grows, with the z-statistic rising past the significance line, for a fixed effect" viewBox="0 0 320 130">
  <line x1="35" y1="20" x2="35" y2="105" stroke="var(--line)" stroke-width="1"/>
  <line x1="35" y1="105" x2="300" y2="105" stroke="var(--line)" stroke-width="1"/>
  <text x="4" y="30" font-size="8" fill="var(--muted)">SE</text>
  <text x="150" y="122" font-size="8.5" fill="var(--muted)">sample size n →</text>
  <path d="M 50 30 Q 110 95 300 100" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <text x="120" y="55" font-size="8.5" fill="var(--s2)">SE shrinks ~ 1/√n</text>
  <path d="M 50 100 Q 130 90 300 35" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <text x="180" y="60" font-size="8.5" fill="var(--s1)">z = effect / SE grows</text>
  <line x1="35" y1="50" x2="300" y2="50" stroke="var(--ink)" stroke-width="1" stroke-dasharray="3 3"/>
  <text x="250" y="47" font-size="7.5" fill="var(--ink)">z=1.96</text>
</svg>
^ For a fixed effect, the standard error falls with the square root of n, so the z-statistic (effect ÷ SE) climbs and eventually crosses the significance line — no matter how small the effect. Significance is guaranteed at enough n; importance is not.

**The confidence interval answers both questions the p-value cannot separate — does it exclude zero, and does it clear the threshold — so deciding on the interval keeps significance and importance distinct.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the result-interpretation step of an experiment analysis, reduced to one effect at two sample sizes so every statistic is checkable by hand.

Run `--measure` to see the same 0.2pp effect evaluated at both sizes.

```text filename=practsig.py --measure
  n           SE          z       p-value    95% CI                significant?
  1000        0.02236     0.089   0.92873    [-4.183pp, 4.583pp]   False
  1000000     0.00071     2.828   0.00468    [0.061pp, 0.339pp]   True
```

At n=1,000 the standard error is 0.022, so the z-statistic is 0.089 and the p-value is 0.93 — nowhere near significant, and the confidence interval [-4.18pp, 4.58pp] is enormous, easily spanning zero. At n=1,000,000 the standard error has shrunk to 0.0007, the z-statistic is 2.83, and the p-value is 0.005 — comfortably significant, with a tight interval [0.06pp, 0.34pp]. The only thing that changed between the two rows is n; the effect is 0.2pp in both.

Now `--compare` states what did and did not change.

```text filename=practsig.py --compare
  n=1000     effect 0.200pp (not significant), CI [-4.183pp, 4.583pp], below threshold -- not worth shipping
  n=1000000  effect 0.200pp (SIGNIFICANT), CI [0.061pp, 0.339pp], below threshold -- not worth shipping
```

Significance flipped from False to True; the effect size and its practical verdict did not. At both sample sizes the effect is 0.2pp, and at both it is below the 1pp threshold — not worth shipping. The large-n result is the trap in its purest form: statistically significant (the interval excludes zero, p=0.005) and practically negligible (the entire interval, up to its 0.34pp upper end, is below the 1pp threshold). Reading the p-value alone, you ship it; reading the interval against the threshold, you correctly pass.

**The same 0.2pp effect is "not significant" at n=1000 and "significant" at n=1,000,000, but it is below the 1pp threshold at both — significance tracked the sample size, importance tracked the effect, and only the second should drive the decision.**

## Build

The self-test asserts the whole structure: the true effect is below the threshold, it is not significant at small n but significant at large n, and — the crux — at large n the interval excludes zero yet lies entirely below the threshold.

```python filename=modules/evals-and-statistics/code/practsig-inter-01/practsig.py:96-110 COMPLETE
    effect_below_threshold = eff < thr
    print("  the true effect is below the practical threshold = %s (%s < %s)" % (effect_below_threshold, pp(eff), pp(thr)))

    small_n_not_significant = not significant(z_s)
    print("  at n=%d the effect is NOT significant = %s (z=%.3f, p=%.4f)" % (small_n, small_n_not_significant, z_s, p_value(z_s)))

    large_n_significant = significant(z_l)
    print("  at n=%d the identical effect IS significant = %s (z=%.3f, p=%.5f)" % (large_n, large_n_significant, z_l, p_value(z_l)))

    effect_unchanged = True  # effect is a fixture constant, identical at both n
    print("  the effect size is identical at both sample sizes = %s (%s)" % (effect_unchanged, pp(eff)))

    ci_excludes_zero = lo_l > 0
    print("  at large n the CI excludes zero (statistically significant) = %s ([%s, %s])" % (ci_excludes_zero, pp(lo_l), pp(hi_l)))
```

<svg role="img" aria-label="Two bars for z-statistic: at n=1000 z is 0.089 far below the 1.96 significance line, at n=1,000,000 z is 2.83 above it, with a note that the effect size is identical" viewBox="0 0 320 130">
  <line x1="30" y1="105" x2="300" y2="105" stroke="var(--line)" stroke-width="1"/>
  <line x1="30" y1="45" x2="300" y2="45" stroke="var(--s2)" stroke-width="1.2" stroke-dasharray="4 3"/>
  <text x="250" y="41" font-size="8" fill="var(--s2)">z = 1.96</text>
  <rect x="70" y="102" width="40" height="3" fill="var(--muted)"/>
  <text x="60" y="118" font-size="8" fill="var(--muted)">n=1000</text>
  <text x="66" y="98" font-size="7.5" fill="var(--muted)">z=0.09</text>
  <rect x="200" y="20" width="40" height="85" fill="var(--s1)"/>
  <text x="188" y="118" font-size="8" fill="var(--muted)">n=1e6</text>
  <text x="204" y="16" font-size="7.5" fill="var(--muted)">z=2.83</text>
  <text x="30" y="16" font-size="8.5" fill="var(--ink)">z grows with n — same 0.2pp effect both bars</text>
</svg>
^ The z-statistic is tiny at n=1000 and clears the 1.96 line at n=1,000,000, purely because the standard error shrank — the effect feeding both bars is the identical 0.2pp. Significance is riding sample size.

Running the check confirms every clause, including that the standard error shrinking is the whole cause.

```text filename=practsig.py --check
  the true effect is below the practical threshold = True (0.200pp < 1.000pp)
  at n=1000 the effect is NOT significant = True (z=0.089, p=0.9287)
  at n=1000000 the identical effect IS significant = True (z=2.828, p=0.00468)
  the effect size is identical at both sample sizes = True (0.200pp)
  at large n the CI excludes zero (statistically significant) = True ([0.061pp, 0.339pp])
  at large n the whole CI lies below the practical threshold = True (0.339pp < 1.000pp)
  the standard error shrinks as n grows (the whole cause) = True (0.00071 < 0.02236)
```

**The check pins significance to sample size and importance to effect size — the large-n interval excludes zero and sits wholly below the threshold, the exact signature of a real effect not worth acting on.**

## Definition of done

Two properties close it. At large n the interval must exclude zero (so the effect is genuinely significant, not a fluke) and lie entirely below the practical threshold (so it is genuinely too small to matter) — those two together are the whole lesson. And the effect size must be identical across sample sizes, so the flip in significance is provably driven by n, not by any change in the effect.

```python filename=modules/evals-and-statistics/code/practsig-inter-01/practsig.py:112-117 COMPLETE
    ci_below_threshold = hi_l < thr
    print("  at large n the whole CI lies below the practical threshold = %s (%s < %s)" % (ci_below_threshold, pp(hi_l), pp(thr)))

    se_shrinks_with_n = se_l < se_s
    print("  the standard error shrinks as n grows (the whole cause) = %s (%.5f < %.5f)" % (se_shrinks_with_n, se_l, se_s))
```

The threshold is a judgment, and stating it plainly keeps the tool honest. Practical significance is not something the statistics hand you — it comes from the domain: the smallest lift that justifies the engineering, the risk, and the added complexity of shipping. Set it before the experiment, not after, or it becomes a post-hoc excuse to accept or reject whatever you wanted. And the interval-versus-threshold reading covers the other cases too: an interval straddling the threshold means the test cannot yet tell whether the effect is big enough — a call for more data, not a decision; an interval entirely above the threshold is both significant and worth shipping; the wide small-n interval here (spanning from −4pp to +4.6pp) is genuinely inconclusive, which is different from "no effect." The one reading to retire is the p-value as a ship/no-ship switch, because at scale it stops carrying the information the decision needs.

**Done means the large-n interval excludes zero and lies below the threshold while the effect is identical across n — significance driven by sample size, importance by effect size, and the decision made on the interval against a pre-set threshold.**

## Boss fight

A product team runs experiments on 20 million users and reports that their last quarter shipped twelve statistically significant wins, every one with p < 0.01. But the top-line metric those wins were supposed to move is flat for the quarter. Leadership asks you to explain the contradiction. What is the most likely cause, and what one change to how results are evaluated would fix it?

The most likely cause is that "statistically significant" at 20 million users is a very low bar — the standard error is so small that almost any nonzero effect clears p < 0.01 — so the twelve wins are probably real but tiny, each a fraction of a percent, individually too small to move the top-line metric and collectively swamped by noise and offsetting changes. Significance confirmed the effects were distinguishable from zero; it never confirmed they were large enough to matter, and at that sample size those are very different claims. The one change is to evaluate and gate every result on effect size and its confidence interval against a pre-registered practical threshold — the minimum lift worth shipping — rather than on the p-value. Ship only when the interval clears the threshold, not merely when it excludes zero; report the effect size and interval in every result so a "significant" 0.1% win is visibly recognized as negligible; and when an interval straddles the threshold, treat it as "need more data or a bigger idea," not a win. Twelve significant-but-sub-threshold wins summing to a flat top line is exactly what conflating significance with importance produces at scale, and moving the decision rule to effect-size-versus-threshold is what stops it.

## External resources

The American Statistical Association's 2016 statement on p-values, and Sullivan and Feinn's "Using Effect Size — or Why the P Value Is Not Enough" (Journal of Graduate Medical Education) — authoritative statements that significance depends on sample size and that effect size and its interval, not the p-value, should drive interpretation.

Kohavi, Tang, and Xu, *Trustworthy Online Controlled Experiments*, the chapters on practical vs statistical significance and choosing a minimum detectable effect — the industry treatment of setting a practical threshold before an experiment and deciding on the confidence interval relative to it, at exactly the large sample sizes where this trap bites.
