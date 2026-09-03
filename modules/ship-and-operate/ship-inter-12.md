---
id: ship-inter-12
title: Alert on the error-budget burn rate, not the raw error rate — a slow burn under the threshold blows the whole SLO
topic: ship-and-operate
level: intermediate
status: ready
time: 22 min
summary: An SLO is an error budget, and the question is how fast you spend it, not the instantaneous rate. A raw-threshold alert catches a loud fast burn but misses a quiet slow burn that sits under the threshold yet exhausts the month's budget. On a 99.9% SLO, a 5% fast burn (2h) eats 14% of budget and fires; a 0.3% slow burn consumes 300% and never trips a 1% alert. Burn-rate alerting catches both.
eli5: A monthly allowance for mistakes gets spent as errors happen. If you only sound the alarm when errors spike really high, you'll miss the quiet leak that spends the whole allowance over the month without ever spiking. Instead, watch how fast the allowance is draining — a fast drain and a slow-but-steady drain both set off the alarm.
---

## Why this module

An SLO is not a line the error rate must stay under moment to moment — it is a budget spent over a window, and monitoring it as a line misses the way it is most often blown.

Say your SLO is 99.9% success over 30 days. That is an error budget: 0.1% of requests are allowed to fail across the whole month, and every error spends a little of it. What you care about is whether you are spending that budget faster than it refills — the burn rate. The instinctive way to monitor it is a threshold alert: page when the error rate exceeds some fixed level, say 1%. That catches a loud, fast incident that spikes well above the line. But it is blind to the incident that sits just under the line and runs for a long time. A steady 0.3% error rate never crosses a 1% threshold, so no alert ever fires — and yet 0.3% is three times the 0.1% you budgeted, so over the month it spends 300% of your budget and blows the SLO completely, silently.

The two failure shapes are different and a raw threshold only sees one. A fast burn is a spike: high rate, short duration, obvious, and it trips any reasonable threshold. A slow burn is a leak: modest rate, long duration, invisible to a threshold set high enough not to page on every blip — and it is the one that quietly exhausts your budget while every dashboard looks fine. Set the threshold low to catch the leak and you page constantly on noise; set it high to avoid noise and you miss the leak. There is no single raw threshold that catches both.

Burn-rate alerting solves it by measuring the thing you actually care about: how fast the budget is draining, relative to sustainable. Burn rate is the error rate divided by the budgeted rate — a burn rate of 1 spends the budget exactly over the window, 50 spends it fifty times too fast, 3 spends it three times too fast. A fast burn has an enormous burn rate and fires immediately on a short window; a slow burn has a modest burn rate but, checked over a long window, still exceeds sustainable and fires. Both are caught, because both are spending too fast.

We will run a fast burn and a slow burn against a 99.9% SLO. The fast burn eats 14% of the month's budget in 2 hours and trips the raw 1% alert. The slow burn consumes 300% of the budget over the month and never trips it — but its burn rate of 3 trips the burn-rate alert. Same SLO; only the alerting philosophy differs.

**An SLO is a budget spent over a window, so a slow burn under the raw threshold can exhaust it unseen; burn-rate alerting watches how fast the budget drains and catches both the spike and the leak.**

## Concepts

Start with the budget. An SLO of 99.9% over a window permits an error budget of 1 − 0.999 = 0.1% of the requests in that window to fail. That budget is a fixed quantity for the window; errors draw it down. The sustainable error rate — the rate that spends the budget exactly evenly over the window — is just the budget rate itself, 0.1%. Run at exactly 0.1% errors for the whole window and you finish having spent 100% of the budget: right at the SLO. Run hotter and you overspend; run cooler and you have budget to spare.

Burn rate is the ratio of your actual error rate to that sustainable rate. It is the natural unit because it is dimensionless and directly interpretable: burn rate 1 is on-pace, burn rate 2 spends the budget in half the window, burn rate 50 spends it in one-fiftieth of the window. The budget a scenario consumes is its burn rate times the fraction of the window it runs for. A burn rate of 50 for 1/360 of the window (2 hours of 720) consumes 50/360 ≈ 14% of the budget; a burn rate of 3 for the whole window consumes 3 × 1 = 300%. This factoring — consumption equals rate times duration — is why both dimensions matter and why a raw threshold, which sees only rate, is incomplete.

<svg role="img" aria-label="Two burn shapes above the raw threshold line: a fast burn is a tall narrow spike that pokes above the line, a slow burn is a low wide band that stays under it" viewBox="0 0 460 170" width="460" height="170">
  <rect x="0" y="0" width="460" height="170" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">error rate over time (area = budget spent)</text>
  <line x1="40" y1="140" x2="440" y2="140" stroke="var(--line)"/>
  <line x1="40" y1="70" x2="440" y2="70" stroke="var(--s2)" stroke-dasharray="4 3"/><text x="330" y="66" font-family="var(--mono)" font-size="9" fill="var(--s2)">raw threshold</text>
  <rect x="70" y="34" width="24" height="106" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="60" y="30" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">fast spike</text>
  <text x="60" y="156" font-family="var(--mono)" font-size="8" fill="var(--muted)">short, pokes above → seen</text>
  <rect x="200" y="118" width="220" height="22" fill="var(--acc-soft)" stroke="var(--line)"/><text x="240" y="133" font-family="var(--mono)" font-size="8" fill="var(--ink)">slow leak — long, stays under → unseen</text>
</svg>
^ The fast spike rises above the raw threshold and is seen; the slow leak stays below it for a long time, spending just as much budget while never tripping the alarm.

The raw threshold's blind spot is precisely the low-rate, long-duration corner. Any threshold you pick partitions error rates into "pages" and "silent," and everything below the line is silent regardless of how long it runs. A rate that is above sustainable (burn rate > 1) but below the threshold burns the budget steadily and silently, and given enough window it exhausts it. The only way a raw threshold could catch every budget-exhausting scenario is to sit at the sustainable rate itself — but that is so low that normal noise crosses it constantly, so you would page every few minutes. The threshold is caught between missing slow burns and crying wolf, and it cannot escape.

Burn-rate alerting escapes by using multiple windows. The standard practice is to alert on a high burn rate over a short window (catch fast burns fast — a burn rate of 14.4 over an hour means you would exhaust a month's budget in about two days, page now) and a lower burn rate over a long window (catch slow burns eventually — a burn rate of 3 over six hours means a steady leak, page before it drains the month). The short window gives fast detection of spikes; the long window gives eventual detection of leaks without paging on brief noise. This module uses a single burn-rate threshold for clarity, but the multi-window structure is the production form, and its whole purpose is to cover both corners a single raw threshold cannot.

**The budget consumed is burn rate times duration, so a raw threshold that sees only rate misses the low-rate, long-duration leak; burn-rate alerting on short and long windows covers both the spike and the leak.**

## Worked example

The fixture is an SLO, the raw alert threshold, and two error scenarios.

```json filename=modules/ship-and-operate/code/ship-inter-12/slo.json:7-18 COMPLETE
  "slo": 0.999,
  "window_hours": 720,
  "raw_alert_rate": 0.01,
  "scenarios": {
    "fast_burn": {
      "error_rate": 0.05,
      "hours": 2
    },
    "slow_burn": {
      "error_rate": 0.003,
      "hours": 720
    }
  }
```

A 99.9% SLO over 720 hours (30 days), a raw alert at 1% error rate. The fast burn is 5% errors for 2 hours; the slow burn is 0.3% errors for the whole month. The error budget is one minus the SLO.

```python filename=modules/ship-and-operate/code/ship-inter-12/burn.py:42-44 COMPLETE
def error_budget(slo):
    """The fraction of requests the SLO permits to fail."""
    return round(1 - slo, 6)
```

Burn rate is the error rate over that budget; budget consumed is burn rate scaled by the fraction of the window the scenario ran.

```python filename=modules/ship-and-operate/code/ship-inter-12/burn.py:47-49 COMPLETE
def burn_rate(error_rate, slo):
    """How many times faster than sustainable the budget is being spent."""
    return round(error_rate / error_budget(slo), 4)
```

```python filename=modules/ship-and-operate/code/ship-inter-12/burn.py:52-55 COMPLETE
def budget_consumed(scenario, data):
    """Fraction of the whole-window budget this scenario spends (>1 means the SLO is blown)."""
    frac_of_window = scenario["hours"] / data["window_hours"]
    return round(scenario["error_rate"] * frac_of_window / error_budget(data["slo"]), 4)
```

Predict: the fast burn's rate is 5%, budget 0.1%, so burn rate 50; over 2/720 of the window that is 50 × (2/720) ≈ 14% of budget, and 5% > 1% so the raw alert fires. The slow burn's rate is 0.3%, burn rate 3; over the whole window that is 3 × 1 = 300% of budget, but 0.3% < 1% so the raw alert stays silent. Run it.

```text filename=modules/ship-and-operate/code/ship-inter-12/burn.py --burn
BURN — burn rate, budget consumed, and which alert fires
--------------------------------------------------------------------
  scenario     burn rate   budget used   raw alert   burn alert
  fast_burn      50.0           14%   FIRES       FIRES
  slow_burn       3.0          300%   silent      FIRES
--------------------------------------------------------------------
  the slow burn blows the budget (300%) yet the raw alert stays silent; burn-rate catches it.
```

The fast burn fires both alerts — its 5% rate clears the 1% raw threshold and its burn rate of 50 clears the burn-rate threshold. But look at the slow burn: it consumes 300% of the budget — blowing the SLO three times over — and the raw alert never fires, because 0.3% is below the 1% line. A team on raw-threshold alerting would sail through the entire month watching a green dashboard while the SLO was being obliterated by a leak too small to trip the alarm. The burn-rate alert catches it, because a burn rate of 3 is three times sustainable regardless of how modest 0.3% looks.

<svg role="img" aria-label="Budget consumed by each scenario: fast burn 14 percent, slow burn 300 percent, past the 100 percent SLO-blown line" viewBox="0 0 460 160" width="460" height="160">
  <rect x="0" y="0" width="460" height="160" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">month's error budget consumed</text>
  <line x1="60" y1="130" x2="440" y2="130" stroke="var(--line)"/>
  <line x1="60" y1="70" x2="440" y2="70" stroke="var(--acc-ink)" stroke-dasharray="4 3"/><text x="330" y="66" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">100% = SLO blown</text>
  <rect x="100" y="122" width="90" height="8" fill="var(--acc-line)" stroke="var(--line)"/><text x="112" y="116" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">14%</text><text x="98" y="146" font-family="var(--mono)" font-size="9" fill="var(--muted)">fast (2h)</text>
  <rect x="280" y="40" width="90" height="90" fill="var(--s2)" stroke="var(--line)"/><text x="300" y="34" font-family="var(--mono)" font-size="10" fill="var(--s2)">300%</text><text x="278" y="146" font-family="var(--mono)" font-size="9" fill="var(--muted)">slow (month)</text>
</svg>
^ The fast burn takes a 14% bite in 2 hours; the slow burn towers past the 100% line — it blows the SLO three times over — yet its rate never trips the raw alarm.

The raw alert misses the slow burn because a threshold sees only rate, not the budget being drained.

```text filename=modules/ship-and-operate/code/ship-inter-12/burn.py --budget
BUDGET — SLO 99.9% over 720 hours
----------------------------------------------------
  error budget: 0.100% of requests may fail
  raw alert fires at instantaneous error rate > 1.0%
  burn-rate alert fires at burn rate > 2.0
----------------------------------------------------
  fast_burn  5.0% errors for 2 h
  slow_burn  0.3% errors for 720 h
```

<svg role="img" aria-label="Alert coverage: raw threshold catches the fast burn but misses the slow burn; burn-rate catches both" viewBox="0 0 460 150" width="460" height="150">
  <rect x="0" y="0" width="460" height="150" fill="var(--panel)" stroke="var(--line)"/>
  <text x="180" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">fast burn</text>
  <text x="330" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">slow burn</text>
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="55" fill="var(--ink)">raw threshold</text>
    <rect x="170" y="40" width="90" height="22" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="188" y="55" fill="var(--acc-ink)">FIRES ✓</text>
    <rect x="320" y="40" width="90" height="22" fill="var(--s2)" stroke="var(--line)"/><text x="332" y="55" fill="var(--ink)">MISSED ✗</text>
    <text x="20" y="100" fill="var(--acc-ink)">burn rate</text>
    <rect x="170" y="85" width="90" height="22" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="188" y="100" fill="var(--acc-ink)">FIRES ✓</text>
    <rect x="320" y="85" width="90" height="22" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="338" y="100" fill="var(--acc-ink)">FIRES ✓</text>
  </g>
  <text x="20" y="134" font-family="var(--mono)" font-size="9" fill="var(--muted)">the raw threshold has a hole exactly where the silent, budget-blowing leak lives</text>
</svg>
^ The raw threshold covers only the fast burn; burn-rate alerting covers both, closing the gap where the slow, SLO-blowing leak hides.

## Build

Reproduce the burn rates and budget figures. Pure arithmetic, so 50, 3, 14%, and 300% come out exactly.

Run `--budget` for the setup, `--burn` for the table, `--check` for the gate. The self-test pins the whole point: the slow burn blows the budget, the raw threshold misses it, burn-rate catches both, and the fast burn eats a large chunk quickly.

```python filename=modules/ship-and-operate/code/ship-inter-12/burn.py:92-96 COMPLETE
    slow_blows_budget = budget_consumed(slow, data) > 1.0
    print("  the slow burn exhausts the whole budget = %s (%.0f%% consumed)" % (slow_blows_budget, budget_consumed(slow, data) * 100))

    raw_misses_slow = slow["error_rate"] <= data["raw_alert_rate"]
    print("  the raw threshold never fires on the slow burn = %s (%.1f%% <= %.1f%%)"
          % (raw_misses_slow, slow["error_rate"] * 100, data["raw_alert_rate"] * 100))
```

The pairing of `slow_blows_budget` and `raw_misses_slow` is the entire argument, and it is why both must be checked together. Either alone is unremarkable — a scenario can blow the budget loudly, or stay under a threshold harmlessly. The danger is the conjunction: a scenario that blows the budget *while* staying under the alert, so the SLO is destroyed and nobody is paged. The self-test insists on both at once, which is the exact silent-failure the module exists to prevent. Here is the full gate.

```text filename=modules/ship-and-operate/code/ship-inter-12/burn.py --check
SELF-TEST — the slow burn blows the SLO under the raw threshold; burn-rate alerting catches both
--------------------------------------------------------------------------------------------
  the slow burn exhausts the whole budget = True (300% consumed)
  the raw threshold never fires on the slow burn = True (0.3% <= 1.0%)
  burn-rate alerting fires on both burns = True (slow 3, fast 50)
  the fast burn eats a large chunk of budget quickly = True (14% in 2 h)
--------------------------------------------------------------------------------------------
SELF-TEST PASS  slow_blows_budget=True  raw_misses_slow=True  burn_catches_both=True  fast_burns_fast=True
```

Four True flags. Slow_blows_budget: the slow burn consumes over 100% of the budget. Raw_misses_slow: the raw threshold never fires on it. Burn_catches_both: burn-rate alerting fires on both scenarios. Fast_burns_fast: the fast burn eats 14% of the month's budget in 2 hours. The first two together are the silent failure; the third is the fix; the fourth is the reminder that fast burns are expensive per minute and deserve their own fast-window alert.

**The slow-blows-budget and raw-misses-slow flags are checked together because the danger is their conjunction — an SLO destroyed while every alert stays silent.**

## Definition of done

You are done when you reproduce the burn rates and can explain the raw threshold's blind spot.

Concretely: `--burn` shows the fast burn at burn rate 50 (14% of budget, raw fires) and the slow burn at burn rate 3 (300% of budget, raw silent, burn-rate fires); `--check` prints PASS with four True flags. You can define an error budget as (1 − SLO) over the window and burn rate as error rate over the budgeted rate. You can explain why a raw threshold cannot catch both fast and slow burns — set it low and it cries wolf, set it high and it misses leaks — and why burn-rate alerting on short and long windows can. And you can compute budget consumed as burn rate times duration and see why the low-rate, long-duration corner is the dangerous one.

The habit to carry: define SLOs as budgets and alert on burn rate over multiple windows, not on a single raw error-rate threshold. When an SLO is missed at month's end but no alert ever fired, look for a slow burn — a modest error rate that ran long enough to drain the budget under the radar.

## Boss fight

The instructive failure is a clean-dashboard month that ends with a blown SLO and a surprised team.

A service has a 99.9% SLO and a page-on-1%-errors alert. The alert never fires all month — the error rate hovers around 0.4%, well under 1%, so the dashboard is green and on-call is quiet. At the monthly SLO review, the service has delivered 99.6% — it missed its SLO badly, consuming four times its error budget — and no one saw it coming, because 0.4% never looked alarming and never tripped the alarm. The 0.4% was a slow burn: a burn rate of 4, draining the budget steadily for 30 days. A burn-rate alert on a multi-hour window would have paged in the first day. The bug was not a bad threshold value; it was alerting on rate at all instead of on budget consumption.

Your turn, two moves. First, find the raw threshold that would catch this slow burn — and see why you would not want it. To catch a 0.4% slow burn you would need the raw threshold at or below 0.4%, but normal traffic noise routinely spikes above 0.4% for a few seconds, so that threshold would page many times a day on nothing. Confirm the trap: the threshold low enough to catch the leak is low enough to cry wolf, which is exactly why raw thresholds cannot win. Second, size the multi-window burn-rate alerts. The Google SRE recommendation for a 30-day SLO is roughly: page if burn rate exceeds 14.4 over 1 hour (a fast burn that would exhaust the budget in ~2 days) or exceeds 3 over 6 hours (a slow burn draining it over the month). Check the fixture against these: the fast burn's 50 clears the 1-hour/14.4 rule and pages in an hour; the slow burn's 3 clears the 6-hour/3 rule and pages within six hours. Both caught, neither on noise — the two windows cover the two corners a single raw line cannot.

## External resources

The Google SRE workbook chapter "Alerting on SLOs" is the canonical treatment; it derives multi-window, multi-burn-rate alerting and gives the exact 14.4-over-1-hour and 3-over-6-hour thresholds this module points to.

The original Site Reliability Engineering book's chapters on service-level objectives and error budgets establish the budget framing — an SLO as an amount of allowed failure spent over a window — that makes burn rate the natural quantity to alert on.

For the implementation, Prometheus and Grafana SLO tooling (and hosted equivalents) document recording rules for burn rate over several windows; reading one shows how the single-threshold artifact here becomes the production multi-window alert.
