---
id: concurrent-inter-01
title: Compare against a concurrent control, not a before/after — a metric's time trend gets credited to the treatment
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: Real metrics move on their own — traffic swings between weekday and weekend, seasons turn, a campaign lands, the user mix drifts — and none of that is your change, yet all of it shows up in the numbers over time. So the question a good experiment answers, did my change move the metric, can only be answered if the comparison holds time constant. A before/after design does not: it measures the old variant in one period, ships the new variant, and measures it in a later period, so the difference it reports is the treatment effect plus everything the metric drifted between the two periods, and the two are inseparable — a metric that was rising anyway makes a neutral change look like a win, and one that was falling makes a real win look like a loss. A concurrent design fixes this by running both variants at the same time on a random split of the same traffic, so both arms live through the identical period — the same day, the same campaign, the same user mix — and whatever the metric was going to do over time happens to both equally and cancels out of their difference, leaving the treatment effect alone. The control is not the past; it is the other half of today. On a fixture where the metric drifts up by 5 between periods while the treatment's true effect is 2, a before/after comparison reports 7 (effect plus trend) while a concurrent comparison reports 2.
eli5: Imagine you want to know if a new fertilizer makes your tomatoes grow taller. The wrong way: measure your plants in April, add fertilizer, then measure again in July and say "look, they grew a foot, the fertilizer works!" — but tomatoes grow a lot from April to July anyway, fertilizer or not, so you can't tell how much was the fertilizer and how much was just summer. The right way: on the same day, give fertilizer to half your plants and nothing to the other half, then compare the two halves. Both halves get the same summer weather, so whatever extra the fertilized half grew is the fertilizer's doing. The trick is to compare two groups living through the same time, not the same group at two different times, because time changes things all by itself.
---

## Why this module

An experiment exists to isolate one cause: your change. Everything else has to be held equal between the thing that got the change and the thing that did not, or you cannot attribute the difference. Most confounds are things you can imagine controlling — the user segment, the device, the traffic source. Time is the one that is easy to forget you have failed to control, because it does not feel like a variable; it just passes.

But time is a powerful confound, because almost every metric you care about is non-stationary. Conversion rates rise before a holiday and fall after. Engagement is different on a Monday than a Saturday. A metric measured in one week and compared to another week differs for a dozen reasons that have nothing to do with any change you made. If your two variants live in two different time windows, every one of those reasons is baked into your result.

A before/after comparison does exactly that — it puts the old variant in the past and the new one in the present, so the calendar is different for the two arms. The reported difference is the treatment effect tangled together with the trend, and nothing in those two numbers can separate them. This module computes the same treatment two ways, before/after and concurrent, against a metric that is drifting, and shows the trend contaminating one design and canceling in the other.

**Time is a confound because metrics are non-stationary, so a before/after comparison — old variant in one period, new in another — reports the treatment effect plus the period's trend, with no way to tell them apart.**

## Concepts

The mechanism of the fix is cancellation. If both variants are measured over the identical time window, then whatever the metric was going to do over that window — rise, fall, spike on the weekend — happens to both arms in the same amount. When you take the difference between the arms, that common movement subtracts out, and what remains is the part that differed between them, which is the treatment. The trend does not have to be estimated or modeled; it cancels for free, as long as both arms share the time.

This is why the control has to be concurrent, not historical. A historical baseline shares no time with the treatment, so nothing cancels; a concurrent control shares all of it, so everything common cancels. The randomized split is what makes the two arms otherwise comparable, and the shared clock is what makes the comparison immune to the trend. Both properties matter: random assignment removes population differences, concurrency removes time differences.

It is worth being precise about how the before/after number decomposes, because it explains every symptom. The before/after difference equals the true effect plus the trend over the gap between periods. When the trend is positive, before/after overstates a positive effect and can turn a null result into an apparent win. When the trend is negative, it understates, and can hide a real win or invent a loss. The size of the error is the size of the trend, which you do not know and cannot recover from the two numbers — which is exactly why the design, not a later correction, has to be right.

<svg role="img" aria-label="A rising metric line over time: before/after samples the old variant early and the new variant late, so the gap spans the slope; concurrent samples both variants at the same late time, so they sit at the same height apart only by the effect" viewBox="0 0 440 160">
<line x1="40" y1="130" x2="410" y2="130" stroke="var(--line)"/>
<line x1="40" y1="20" x2="40" y2="130" stroke="var(--line)"/>
<text x="225" y="150" fill="var(--muted)" font-size="9" text-anchor="middle">time</text>
<line x1="50" y1="115" x2="400" y2="45" stroke="var(--grid)"/>
<text x="360" y="40" fill="var(--muted)" font-size="8">metric trend</text>
<circle cx="90" cy="107" r="4" fill="var(--s2)"/>
<text x="90" y="122" fill="var(--muted)" font-size="8" text-anchor="middle">old, early</text>
<circle cx="360" cy="53" r="4" fill="var(--s2)"/>
<text x="360" y="68" fill="var(--muted)" font-size="8" text-anchor="middle">new, late</text>
<line x1="90" y1="107" x2="360" y2="53" stroke="var(--s2)" stroke-dasharray="3 3"/>
<text x="200" y="72" fill="var(--s2)" font-size="8">before/after: spans the slope</text>
<circle cx="360" cy="63" r="4" fill="var(--s1)"/>
<text x="392" y="60" fill="var(--s1)" font-size="8">both late</text>
</svg>
^ Before/after reads the two arms at different points on the rising line, so its gap includes the slope; concurrent reads both at the same time, so only the effect separates them.

**A concurrent control shares the whole time window with the treatment, so the trend cancels in their difference; a before/after difference is the effect plus an unknown trend, biased up or down by whichever way the metric was already moving.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/concurrent-inter-01. The fixture is a metric with a baseline, a time trend between periods, and the treatment's true effect.

```json filename=modules/evals-and-statistics/code/concurrent-inter-01/concurrent.json:3-5 COMPLETE
  "base": 10,
  "time_trend": 5,
  "true_effect": 2
```

The metric model adds the period's trend and the effect only for the new variant.

```python filename=modules/evals-and-statistics/code/concurrent-inter-01/concurrent.py:32-34 COMPLETE
def metric(base, trend, effect, period, is_new):
    """The metric for a variant in a period: baseline + the period's trend + the effect if it's the new variant."""
    return base + (trend if period == 2 else 0) + (effect if is_new else 0)
```

The before/after design compares the old variant in period 1 against the new variant in period 2 — across two time periods.

```python filename=modules/evals-and-statistics/code/concurrent-inter-01/concurrent.py:37-41 COMPLETE
def before_after(base, trend, effect):
    """Old variant measured in period 1, new variant in period 2 -- across two time periods."""
    old_p1 = metric(base, trend, effect, 1, is_new=False)
    new_p2 = metric(base, trend, effect, 2, is_new=True)
    return new_p2 - old_p1
```

The concurrent design compares both variants in the same period, on a random split.

```python filename=modules/evals-and-statistics/code/concurrent-inter-01/concurrent.py:44-48 COMPLETE
def concurrent(base, trend, effect):
    """Both variants measured in the same period (2), on a random split -- same time for both."""
    old_p2 = metric(base, trend, effect, 2, is_new=False)
    new_p2 = metric(base, trend, effect, 2, is_new=True)
    return new_p2 - old_p2
```

Before running it, predict: the before/after difference should be the effect plus the trend, 7; the concurrent difference should be the effect alone, 2. Run `--values`:

```text filename=concurrent.py --values
VALUES — metric per variant per period (base=10, trend=5, effect=2)
----------------------------------------------------------
  period   old variant   new variant
  1        10            12
  2        15            17
----------------------------------------------------------
  before/after diff = 7   concurrent diff = 2   (true effect = 2)
```

The prediction holds. Before/after takes the old variant's 10 in period 1 and the new variant's 17 in period 2, reporting 7 — but 5 of that is the trend that lifted everything from period 1 to period 2. Concurrent takes both variants in period 2, 15 and 17, and reports 2, the true effect. The trend that inflated before/after is present in both period-2 numbers, so it cancels.

<svg role="img" aria-label="A two-by-two grid of metric values: old and new variant across period 1 and period 2; the before/after comparison spans the diagonal across periods while the concurrent comparison is within period 2" viewBox="0 0 440 160">
<text x="150" y="24" fill="var(--muted)" font-size="10" text-anchor="middle">old</text>
<text x="250" y="24" fill="var(--muted)" font-size="10" text-anchor="middle">new</text>
<text x="70" y="58" fill="var(--muted)" font-size="10" text-anchor="middle">period 1</text>
<text x="70" y="108" fill="var(--muted)" font-size="10" text-anchor="middle">period 2</text>
<rect x="120" y="40" width="60" height="30" fill="var(--panel)" stroke="var(--line)"/>
<text x="150" y="60" fill="var(--ink)" font-size="11" text-anchor="middle">10</text>
<rect x="220" y="40" width="60" height="30" fill="var(--panel)" stroke="var(--line)"/>
<text x="250" y="60" fill="var(--ink)" font-size="11" text-anchor="middle">12</text>
<rect x="120" y="90" width="60" height="30" fill="var(--panel)" stroke="var(--line)"/>
<text x="150" y="110" fill="var(--ink)" font-size="11" text-anchor="middle">15</text>
<rect x="220" y="90" width="60" height="30" fill="var(--panel)" stroke="var(--line)"/>
<text x="250" y="110" fill="var(--ink)" font-size="11" text-anchor="middle">17</text>
<line x1="150" y1="70" x2="250" y2="90" stroke="var(--s2)"/>
<text x="200" y="140" fill="var(--s2)" font-size="9" text-anchor="middle">before/after: 10 -&gt; 17 = 7 (crosses periods)</text>
<line x1="180" y1="105" x2="220" y2="105" stroke="var(--s1)"/>
<text x="360" y="110" fill="var(--s1)" font-size="9" text-anchor="middle">concurrent: 17-15 = 2</text>
</svg>
^ Before/after reads across the diagonal into a different period and picks up the trend; concurrent reads within period 2, so the shared trend cancels.

Now decompose the before/after number. Run `--attribute`:

```text filename=concurrent.py --attribute
ATTRIBUTE — what the before/after difference is made of
--------------------------------------------------
  before/after difference        = 7
    of which true effect         = 2
    of which time trend (bias)   = 5
  concurrent difference          = 2  (trend cancels)
--------------------------------------------------
  the trend is credited to the treatment only in the before/after design
```

The before/after 7 is exactly the true effect (2) plus the time trend (5). Every unit of trend is misattributed to the treatment. The concurrent design reports the 2 with the trend removed — not estimated and subtracted, but cancelled by construction.

<svg role="img" aria-label="A stacked bar for the before/after difference of 7 split into 2 of true effect and 5 of time-trend bias, next to a concurrent bar of 2 that is all true effect" viewBox="0 0 440 150">
<line x1="40" y1="120" x2="410" y2="120" stroke="var(--line)"/>
<rect x="90" y="90" width="70" height="30" fill="var(--s1)"/>
<text x="125" y="110" fill="var(--ink)" font-size="10" text-anchor="middle">effect 2</text>
<rect x="90" y="30" width="70" height="60" fill="var(--s2)"/>
<text x="125" y="64" fill="var(--ink)" font-size="10" text-anchor="middle">trend 5</text>
<text x="125" y="136" fill="var(--muted)" font-size="9" text-anchor="middle">before/after = 7</text>
<rect x="280" y="90" width="70" height="30" fill="var(--s1)"/>
<text x="315" y="110" fill="var(--ink)" font-size="10" text-anchor="middle">effect 2</text>
<text x="315" y="136" fill="var(--muted)" font-size="9" text-anchor="middle">concurrent = 2</text>
</svg>
^ Before/after stacks the trend on top of the effect; the concurrent design keeps only the effect, because the trend cancelled.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that the metric drifts, that the before/after difference does not equal the true effect but does equal effect plus trend, that the concurrent difference equals the true effect, and that concurrent is closer to the truth.

```python filename=modules/evals-and-statistics/code/concurrent-inter-01/concurrent.py:85-95 COMPLETE
    trend_exists = metric(b, t, e, 2, False) != metric(b, t, e, 1, False)
    print("  the metric drifts over time on its own (trend != 0) = %s (%d)" % (trend_exists, t))

    before_after_overstates = ba != e
    print("  before/after difference does not equal the true effect = %s (%d vs %d)" % (before_after_overstates, ba, e))

    before_after_is_effect_plus_trend = ba == e + t
    print("  before/after difference = true effect + time trend = %s (%d = %d + %d)" % (before_after_is_effect_plus_trend, ba, e, t))

    concurrent_correct = co == e
    print("  concurrent difference equals the true effect = %s (%d)" % (concurrent_correct, co))
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the concurrent design ever stops recovering the true effect or the trend ever stops contaminating before/after:

```text filename=concurrent.py --check
SELF-TEST — before/after confounds the effect with the time trend; a concurrent split cancels it
--------------------------------------------------------------------------------------------------------
  the metric drifts over time on its own (trend != 0) = True (5)
  before/after difference does not equal the true effect = True (7 vs 2)
  before/after difference = true effect + time trend = True (7 = 2 + 5)
  concurrent difference equals the true effect = True (2)
  concurrent is closer to the truth than before/after = True
```

**The self-test pins the exact decomposition — before/after equals effect plus trend, concurrent equals effect — which proves the contamination is the trend specifically, not generic noise.**

## Definition of done

You can explain why time is a confound: metrics are non-stationary, so two different periods differ for reasons unrelated to the treatment.
You can state why a concurrent control cancels the trend — both arms share the time window, so common movement subtracts out of their difference.
You can decompose a before/after difference into the true effect plus the period's trend, and say which way each sign of trend biases it.
You can explain why this must be fixed by design rather than by a later correction — the trend is unknown and unrecoverable from the two numbers.
You can distinguish the two things a randomized concurrent A/B controls: random assignment removes population differences, concurrency removes time differences.

## Boss fight

Consider the design that tries to have it both ways: a before/after comparison with a concurrent control running alongside — measure old and new in period 2, but also compare each to period 1. This is the difference-in-differences design, and it can be valid, but only under an assumption the pure concurrent design does not need: that both arms would have followed the same trend absent the treatment. If the trend differs between the arms — the new variant's users were on a steeper trajectory anyway — difference-in-differences is biased again. The lesson deepens: concurrency plus randomization removes the trend without assuming anything about it, which is why it is the gold standard; every design that reaches back in time buys convenience with an assumption that can fail.

Now the sneaky version of the same bug within a single A/B test: ramping. Suppose you start the new variant at 1% of traffic and increase it to 50% over a week, while the metric has a weekday cycle. Early in the week the new variant is mostly weekend traffic; later it is mostly weekday. The two arms are concurrent in name but not in composition over time, and the trend leaks back in through the changing mix. Concurrency has to mean the arms see the same time distribution, not merely that both are live at some point during the window — otherwise you have rebuilt the before/after confound inside a supposedly concurrent test.

**Difference-in-differences reuses the past but must assume both arms share a trend, an assumption concurrency avoids entirely; and a ramped rollout breaks concurrency by giving the arms different time mixes, smuggling the before/after confound back into a live test.**

## External resources

Kohavi, Tang, and Xu's "Trustworthy Online Controlled Experiments" makes the case for concurrent randomized controls over before/after comparisons and catalogs the trends that break the latter.
The econometrics literature on difference-in-differences documents the parallel-trends assumption that a partly-historical design must make and a concurrent one does not.
The topic's own modules on sample ratio mismatch and on peeking cover other ways an experiment's validity is decided by its design rather than its analysis.
