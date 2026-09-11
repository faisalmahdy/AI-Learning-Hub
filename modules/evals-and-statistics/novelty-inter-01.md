---
id: novelty-inter-01
title: Estimate the steady state, not the early average — a new feature's launch metrics are inflated by novelty that wears off
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: You ship a new feature, run an experiment, and the lift is big — and reading that number as the feature's value is tempting and wrong, because a brand-new feature enjoys a boost with nothing to do with its lasting worth: novelty. Users click it because it is new, explore it out of curiosity, and engage at a rate they will not sustain, so the early metrics are inflated and the inflation decays over the following days toward the feature's true steady-state effect. The trap has a second layer: averaging does not fix it. Seeing high early days, the instinct is to average over the whole experiment to smooth it out, but any average over a decaying curve is pulled up by the early novelty — the mean of the first three days and even the mean of all eight days both sit well above the plateau the lift is decaying toward, so averaging a spike with a steady state gives a number that is neither: higher than the truth, lower than the peak, wrong for forecasting the long run. The decay is not noise to average away; it is signal about which part of the curve is real. The honest estimate of the long-run effect is the steady state — the level the lift settles to after novelty wears off — got by running the experiment long enough for the curve to flatten and reading the plateau (or modeling the decay and extrapolating to the asymptote), not from a window that includes the spike. The counterpart is primacy (a feature can under-perform at first while users learn it, then rise), and the rule is the same: what matters is where the curve settles, not where it starts. On a fixture where daily lift starts at 10 and decays to a steady state of 3, the first-3-days average is 7.33 and even the full 8-day average is 4.75 — both far above the true long-run lift of 3.
eli5: Imagine you open a new ice-cream shop and on the first few days there are huge lines — everyone wants to try the new place. If you measured "how busy are we?" during that first week and used it to predict how much ice cream to make forever, you'd make way too much, because those lines are just people being curious about something new. After a couple of weeks the crowd settles down to the regulars who actually love it, and that steady number is your real business. And you can't fix it by averaging the busy opening week with a normal week — that still comes out too high. You have to wait for the excitement to fade and look at where things settle. For a new app feature, "novelty" is that opening-week crowd, and the honest number is where usage lands once the newness wears off.
---

## Why this module

A launch experiment measures two things at once and reports them as one: the feature's real effect, and the transient burst of attention any new thing gets. The burst is novelty, and it is not a measurement error — it is a genuine change in behavior that genuinely fades. Understanding it matters because the most consequential decisions (ship it, forecast its impact, size the roadmap around it) are made right after launch, exactly when the novelty inflation is largest, so a naive reading systematically overstates what a portfolio of features will deliver and the forecasts come in high across the board.

The mechanism is a decaying curve. On day one the metric is dominated by curiosity; each following day the curiosity component shrinks as users who were going to try it have tried it, until only the durable behavior remains — the steady state. The whole experiment window is a mixture of the fading transient and the durable effect, weighted toward the transient at the start.

The subtle part is that you cannot average your way out of it, because averaging a decay keeps the transient in the number. This module measures a launch curve three ways — a short early window, the full window, and the steady-state tail — and shows which one tells the truth.

**Estimate a new feature's long-run effect from the steady state its metric decays (or rises) to after novelty wears off — reading the flat tail of a long-enough experiment — rather than from an early window or an average over the launch period, because novelty inflates the early metrics and any average over the decaying curve is pulled above the true steady-state effect.**

## Concepts

The fixture is the daily lift of a feature over an 8-day experiment: it starts at 10 (pure novelty) and decays to a steady state of 3 by day 5. The short-window analysis would average the first 3 days.

```json filename=modules/evals-and-statistics/code/novelty-inter-01/novelty.json:3-4 COMPLETE
  "daily_lift": [10, 7, 5, 4, 3, 3, 3, 3],
  "short_window_days": 3
```

The steady state is the plateau the lift decays to — the flat tail. That is the honest long-run estimate.

```python filename=modules/evals-and-statistics/code/novelty-inter-01/novelty.py:33-38 COMPLETE
def steady_state(daily_lift):
    """The plateau the lift decays to: the value of the flat tail."""
    last = daily_lift[-1]
    # the steady state is the run of equal values at the end
    plateau = [v for v in reversed(daily_lift) if v == last]
    return statistics.mean(plateau)
```

The two averaging approaches — a short early window and the full window — are the tempting-but-wrong summaries, and a decay check confirms the curve is a fading novelty spike.

```python filename=modules/evals-and-statistics/code/novelty-inter-01/novelty.py:41-51 COMPLETE
def short_window_mean(daily_lift, days):
    return statistics.mean(daily_lift[:days])


def full_window_mean(daily_lift):
    return statistics.mean(daily_lift)


def decays(daily_lift):
    """Whether the lift is non-increasing (novelty fading)."""
    return all(daily_lift[i] >= daily_lift[i + 1] for i in range(len(daily_lift) - 1))
```

<svg role="img" aria-label="A decay curve of daily lift from 10 down to a plateau at 3, with the short-window average at 7.33 and full-window average at 4.75 both above the plateau" viewBox="0 0 320 130">
  <line x1="30" y1="20" x2="30" y2="110" stroke="var(--line)" stroke-width="1"/>
  <line x1="30" y1="110" x2="300" y2="110" stroke="var(--line)" stroke-width="1"/>
  <polyline points="45,25 78,52 111,70 144,79 177,88 210,88 243,88 276,88" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <circle cx="45" cy="25" r="3" fill="var(--s2)"/><circle cx="177" cy="88" r="3" fill="var(--s1)"/><circle cx="276" cy="88" r="3" fill="var(--s1)"/>
  <line x1="30" y1="88" x2="300" y2="88" stroke="var(--s1)" stroke-width="1" stroke-dasharray="3 3"/>
  <text x="240" y="85" font-size="7.5" fill="var(--s1)">steady state 3</text>
  <line x1="30" y1="52" x2="300" y2="52" stroke="var(--muted)" stroke-width="1" stroke-dasharray="2 3"/>
  <text x="230" y="49" font-size="7.5" fill="var(--muted)">short-window avg 7.33</text>
  <line x1="30" y1="70" x2="300" y2="70" stroke="var(--muted)" stroke-width="1" stroke-dasharray="2 3"/>
  <text x="235" y="67" font-size="7.5" fill="var(--muted)">full avg 4.75</text>
  <text x="40" y="124" font-size="7.5" fill="var(--muted)">day 1 (novelty) → day 8 (settled)</text>
</svg>
^ The lift decays from 10 to a plateau at 3. Both averages (7.33 short-window, 4.75 full-window) sit above the plateau, because averaging over the decay keeps the novelty in the number. Only the flat tail — the steady state — is the true long-run lift.

**A launch curve is a fading transient plus a durable effect, and any average over the window inherits the transient — only the settled tail isolates the durable part.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the experiment-analysis step of a feature launch, reduced to an 8-day curve so every average is checkable by hand.

Run `--curve` to see the daily lift.

```text filename=novelty.py --curve
  day     1  2  3  4  5  6  7  8
  lift   10  7  5  4  3  3  3  3
  starts at 10 (novelty), decays to steady state 3
```

Day 1 shows a lift of 10, and it falls each day — 7, 5, 4 — until it flattens at 3 from day 5 onward. The shape is the signature of novelty: a spike at launch decaying to a durable level. The last four days are identical at 3, which is the feature's real, sustained effect once curiosity is spent.

Now `--estimate` summarizes it three ways.

```text filename=novelty.py --estimate
  short-window mean (first 3 days) = 7.33  (overstates by 4.33)
  full-window mean  (all 8 days)   = 4.75  (overstates by 1.75)
  steady-state (flat tail)         = 3.00  (the true long-run lift)
```

The short-window mean is 7.33 — more than double the truth, because it averages the three highest-novelty days. The full-window mean is 4.75 — better, but still overstates by 1.75, because it still includes the decaying spike in days 1 through 4. Only the steady state, 3, is the honest long-run lift. Note the lesson in the two averages: extending the window from 3 days to 8 helped (7.33 to 4.75) but did not fix it, because averaging can never remove a transient it includes — you have to isolate the plateau, not blend it with the spike.

**The short-window average overstates the lift by 4.33 and even the full-window average by 1.75, while the steady-state tail gives the true 3 — averaging shrinks the error but cannot remove it, because the novelty is inside every window.**

## Build

The self-test asserts the shape and both failures: the early lift is above the steady state, the curve decays, and both the short-window and full-window averages overstate the long-run lift.

```python filename=modules/evals-and-statistics/code/novelty-inter-01/novelty.py:86-96 COMPLETE
    early_lift_high = dl[0] > ss
    print("  the early lift is well above the steady state (novelty) = %s (%d vs %.0f)" % (early_lift_high, dl[0], ss))

    lift_decays = decays(dl)
    print("  the lift decays over time (novelty fading) = %s" % lift_decays)

    short_window_overstates = swm > ss
    print("  the short-window mean overstates the long-run lift = %s (%.2f > %.0f)" % (short_window_overstates, swm, ss))

    full_window_also_overstates = fwm > ss
    print("  even the full-window average overstates it = %s (%.2f > %.0f)" % (full_window_also_overstates, fwm, ss))
```

<svg role="img" aria-label="Three estimate bars: short-window 7.33, full-window 4.75, steady-state 3, with the first two marked as overstating" viewBox="0 0 320 110">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">estimated long-run lift (truth = 3)</text>
  <line x1="70" y1="24" x2="70" y2="100" stroke="var(--s1)" stroke-width="1" stroke-dasharray="3 3"/><text x="46" y="22" font-size="7" fill="var(--s1)">truth 3</text>
  <text x="10" y="40" font-size="8" fill="var(--s2)">short win</text>
  <rect x="70" y="30" width="176" height="14" fill="var(--s2)"/><text x="250" y="41" font-size="7.5" fill="var(--ink)">7.33</text>
  <text x="10" y="64" font-size="8" fill="var(--s2)">full win</text>
  <rect x="70" y="54" width="105" height="14" fill="var(--s2)" opacity="0.6"/><text x="180" y="65" font-size="7.5" fill="var(--ink)">4.75</text>
  <text x="10" y="88" font-size="8" fill="var(--s1)">steady</text>
  <rect x="70" y="78" width="0.5" height="14" fill="var(--s1)"/><text x="76" y="89" font-size="7.5" fill="var(--ink)">3.00</text>
</svg>
^ Both averages overshoot the truth line at 3; the short window most, the full window less, the steady state exactly. The bars shrink toward truth as the window lengthens but only the steady-state estimate lands on it.

Running the check confirms every clause, including that the lift reaches a flat plateau and the steady state is below both averages.

```text filename=novelty.py --check
  the early lift is well above the steady state (novelty) = True (10 vs 3)
  the lift decays over time (novelty fading) = True
  the short-window mean overstates the long-run lift = True (7.33 > 3)
  even the full-window average overstates it = True (4.75 > 3)
  the lift reaches a flat steady-state plateau = True (tail all 3)
  the steady state is below both averages (the true, lower value) = True (3 < 7.33, 4.75)
```

**The check ties both averages' overstatement to the novelty inside their windows and pins the steady state as the true, lower value — so the honest estimate is the plateau, not any average over the decay.**

## Definition of done

Two properties close it. The lift must reach a flat steady-state plateau (there is a durable effect to estimate, distinct from the transient), and that steady state must be below both averages — the true long-run value is the lower one the averages inflate past. Together they say: the number to report is the plateau, and any window-average is biased high.

```python filename=modules/evals-and-statistics/code/novelty-inter-01/novelty.py:98-102 COMPLETE
    steady_state_is_plateau = len({v for v in dl[sw + 1:]}) == 1
    print("  the lift reaches a flat steady-state plateau = %s (tail all %.0f)" % (steady_state_is_plateau, ss))

    steady_below_windowed = ss < swm and ss < fwm
    print("  the steady state is below both averages (the true, lower value) = %s (%.0f < %.2f, %.2f)" % (steady_below_windowed, ss, swm, fwm))
```

Three clarifications keep the method honest. First, the direction is not always down: the counterpart of novelty is the primacy or learning effect, where a feature under-performs at first because users have to learn it and then rises to a higher steady state — the fix is identical (estimate the plateau, not the launch window), just with the bias pointing the other way, so the general rule is "read where the curve settles," not "assume launch overstates." Second, you need the experiment to run long enough for the curve to actually flatten, and how long depends on the usage cycle — a daily-use feature settles in days, a monthly workflow may take months; reading a "plateau" before it has truly formed re-introduces the bias, so plateau-detection must be honest about whether the tail is flat or still decaying. Third, when you cannot run long enough, the principled move is to fit a decay model to the observed curve and extrapolate to the asymptote, reporting that with its uncertainty, rather than trusting an early average — and to separately track new-user vs existing-user cohorts, since novelty lives mostly in the existing users trying something new while new users have no "before" to be curious relative to. The invariant across all of it: the launch window measures curiosity plus value, and only the settled behavior measures value.

<svg role="img" aria-label="Two curves: novelty starts high and decays to a plateau; primacy starts low and rises to a plateau; both settle at the same steady state read from the tail" viewBox="0 0 320 120">
  <line x1="30" y1="15" x2="30" y2="100" stroke="var(--line)" stroke-width="1"/>
  <line x1="30" y1="100" x2="300" y2="100" stroke="var(--line)" stroke-width="1"/>
  <line x1="30" y1="60" x2="300" y2="60" stroke="var(--ink)" stroke-width="1" stroke-dasharray="3 3"/>
  <text x="235" y="57" font-size="7.5" fill="var(--ink)">steady state (read here)</text>
  <polyline points="45,22 90,40 135,54 180,60 240,60 290,60" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <text x="90" y="30" font-size="7.5" fill="var(--s2)">novelty: high → settles</text>
  <polyline points="45,95 90,80 135,66 180,60 240,60 290,60" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <text x="120" y="92" font-size="7.5" fill="var(--s1)">primacy: low → settles</text>
</svg>
^ Novelty overshoots and decays; primacy undershoots and rises. Both mislead the launch window in opposite directions, and both are read correctly the same way — from the plateau they settle to, not from where they start.

**Done means the lift settles to a plateau that lies below both window-averages — the durable effect isolated as the steady state, distinct from a novelty (or primacy) transient the averages absorb, and read from a genuinely flat tail or a fitted asymptote.**

## Boss fight

A product team launches features rapidly, and each launch experiment shows a strong lift over its first week, which they use to forecast annual impact. At year end, the summed forecast predicted a huge gain in the north-star metric, but the actual metric barely moved. They suspect their metric is broken or their experiments are underpowered. What is the more likely explanation, and what should they change?

The more likely explanation is the novelty effect compounding across every launch. Each feature's first-week lift is inflated by curiosity — users try the new thing at a rate they do not sustain — so the first-week number overstates the durable effect, and summing many first-week numbers into an annual forecast stacks that overstatement across the whole portfolio, producing a forecast far above what the features actually deliver once novelty fades. The north-star metric barely moving is exactly what you would see if each feature's real steady-state lift is a fraction of its launch-week lift; the metric is not broken and the experiments are not underpowered — they measured curiosity plus value and reported it as value. What to change: estimate each feature's long-run effect from the steady state its metric settles to after novelty wears off, not from the launch window. Concretely, run experiments long enough for the daily lift to flatten and read the plateau (how long depends on the feature's usage cycle); where that is impractical, fit a decay curve to the observed lift and extrapolate to the asymptote, forecasting from that (with its uncertainty) rather than the first-week average. Separate new-user and existing-user cohorts, since novelty lives mostly in existing users trying something new. And forecast the annual impact by summing steady-state estimates, not launch-window estimates. Watch for the opposite bias too — a feature with a learning curve may under-perform at launch and rise — so the rule is to forecast from where each curve settles, which will bring the summed forecast into line with the north-star metric.

## External resources

Kohavi, Tang, and Xu, *Trustworthy Online Controlled Experiments*, on novelty and primacy effects — the industry treatment of why launch-window metrics overstate (or understate) long-run effects and the guidance to run experiments to a stable plateau and analyze by cohort.

Microsoft's and Booking.com's experimentation writeups on novelty effects and long-term holdouts — practical methods (long-running holdback experiments, decay-curve extrapolation, new-vs-existing-user analysis) for estimating the durable effect of a feature rather than its launch spike.
