---
id: harness-adv-01
title: Is the agent quietly getting worse? A control chart for the weekly eval
topic: agent-harness
level: advanced
status: ready
eli5: Run the same test every week and write down the score. Instead of panicking on every little dip, draw the band the score normally wobbles in — then you only sound the alarm when a week falls out of the band, and one common mistake makes the alarm go permanently silent.
time: 10-14h
summary: A scheduled eval appends one dated pass rate per week; the naive "it dropped since last week" alarm fires on ordinary noise while missing the point, and recomputing the band over all history silently swallows a real regression. Freeze a 3-sigma baseline band from the stable weeks (sigma = sqrt(p(1-p)/n)) and a genuine 19-point model-swap regression (0.80 down to a 0.61 average) is caught the first week it appears, wk07 at 0.62 below an LCL of 0.630, with zero false alarms on the baseline.
---

## Why this module

Every module in this topic so far ran once. The loop ran, the seams held, the governed server refused a write, the ratchet kept one skill — each a single verdict at a single moment. Production is not a moment. The model behind your agent gets swapped, a provider silently changes a default, a prompt you edited three weeks ago rots — and the way you find out is that the agent is quietly worse than it was, with no error, no traceback, no crash. Nothing tells you. That is what a scheduled eval is for, and the labs already have the manual version: `docs/LIVE_VALIDATION.md` is a runbook a human follows to run the suite against the live model and eyeball the result. `CURRICULUM.md`'s Track 2.5 names the gap in one line: turn the runbook into "a scheduled real-model eval that trends over time," whose artifact is "a dashboard/ledger with at least three dated runs."

The runbook's weak point is the eyeball. A human looking at twelve weekly numbers will either panic at every dip or, worse, get numb and stop looking. This module replaces the eyeball with a rule that has a century of industrial use behind it: a control chart. You freeze a band from the weeks when nothing was wrong, and you alarm only when a later week falls out of that band. The band is three standard errors of a proportion, and the standard error is `sqrt(p*(1-p)/n)` — the exact "state the spread" discipline the evals track is built on, pointed at a time series instead of a leaderboard.

This is the topic's `advanced` module, so it composes rather than introduces. You need the paired-difference and interval instincts from evals-inter-01 and the keep/reject framing from harness-inter-03; here the same statistics run forward through time. What it omits: no live model, no scheduler daemon, no alerting integration — the twelve weeks are a committed fixture and the "schedule" is a loop over rows, so the whole thing runs offline in under a second. Stdlib Python 3, `$0.00`, one long sitting. The hard part is a single instinct that has to be unlearned: the belief that a drop is a signal. In a noisy time series, most drops are nothing, and the one rule that feels most obviously correct — "alarm if it dropped since last week" — is the one that ruins the alarm.

By the end, one command reads twelve weeks and names the exact week a real regression began. Skipping ahead:

```
# modules/agent-harness/code/harness-adv-01/ — COMPLETE, run from that directory
$ python3 livecheck.py --alarm

THE ALARM — frozen band, two rules (point < LCL, or 5 weeks below center)
  center 0.800   LCL 0.630
------------------------------------------------------------------------
  ALARM at wk07 (2026-07-13): rate 0.62  --  point < LCL
  caught the model swap the first week it showed, with zero baseline alarms.
```

run: 2026-08-22 · runs are a fixture; p-chart is deterministic · n=50 tasks/week, 12 weeks · `python3 livecheck.py --alarm`

Twelve weeks of the same 50-task suite against the production model. For six weeks the pass rate wobbles around 0.80; on week seven a model swap drops it to the low 0.60s and holds. The alarm fires on week seven — the first week the regression shows — and never once during the six baseline weeks, even though those weeks bounced between 0.76 and 0.84. This module is about the band that makes that possible, the two ways of building it that fail, and why the failure of the second one is the dangerous kind: it is silent.

## Concepts

Named here so you can find them again; each is built, and two are broken, below.

- **Scheduled eval** — the same task suite run against the live model on a cadence, appending one dated row per run.
- **The ledger** — the dated rows: date, task count, pass count. The only input.
- **p-chart** — a control chart for a pass/fail proportion; the band and the rules.
- **Standard error of a proportion** — `sqrt(p*(1-p)/n)`, how much a pass rate wobbles by chance at this n.
- **Frozen baseline band** — center and 3-sigma limits computed once, from the stable weeks, and never moved. #3.
- **Point rule / shift rule** — the two alarms: one week below the lower limit, or a run of weeks below center.
- **The delta detector** — alarm if this week dropped since last week. The false-alarm storm.
- **Baseline contamination** — recomputing the band over all history so the regression widens its own band and hides. The planted bug.

## Worked example

Source: faisalmahdy/agent — `docs/LIVE_VALIDATION.md`, the manual runbook this module automates, and the skills-matrix note that "nothing trends the live eval over time." And faisalmahdy/AI-Learning-Hub — `code/evals-inter-01/`, whose spread-and-interval discipline this reuses, now along a time axis.

Script and fixture: `modules/agent-harness/code/harness-adv-01/` — `livecheck.py`, and `ledger.json`, twelve weekly runs of a 50-task suite. Every command runs from there. The one dial is the ledger: swap in your own dated runs and every number below recomputes.

### Install the frame: the eval is a smoke detector, and it has two ways to fail

In my opinion the right way to think about a scheduled eval is as a smoke detector, not a thermometer. A thermometer reports a number and leaves the judgment to you; a smoke detector makes the judgment — quiet, or screaming — and the whole game is calibrating what makes it scream.

A smoke detector has exactly two failure modes, and a scheduled eval inherits both. One: it goes off every time you make toast, so within a week you have taken the battery out — that is the detector tuned to ordinary variation, and it is worse than no detector because it trains you to ignore it. Two: someone taped over it after the toast incident, so when the kitchen actually catches fire it stays silent — that is the detector that has been desensitized until it cannot fire. This module builds one detector and then shows you both failures, in order: the toast-triggered one (the delta detector), then the taped-over one (baseline contamination). The correct detector is the narrow path between them: deaf to toast, awake to fire.

The number the detector listens to is the weekly pass rate, and the reason it wobbles is not that the model changed — it is that 50 tasks is a sample. Run the same fixed model on 50 tasks this week and 50 next week and the pass rate will differ, by chance, even with nothing wrong. How much? That is the standard error of a proportion, and it is the whole foundation of the band.

```
# livecheck.py:46-58 — COMPLETE (freeze the band from the stable weeks)
def limits(runs):
    """Freeze the baseline: center and 3-sigma band from the first BASE weeks.

    sigma of a proportion over n tasks is sqrt(p*(1-p)/n) -- the binomial
    standard error. The band is center +/- SIGMA*sigma. Frozen: computed once,
    from the clean period, and never moved by later weeks."""
    base = runs[:BASE]
    passed = sum(r["passed"] for r in base)
    n = sum(r["n"] for r in base)
    center = passed / n
    per_run_n = n / len(base)                      # avg tasks per run
    se = sqrt(center * (1 - center) / per_run_n)
    return center, center - SIGMA * se, center + SIGMA * se, se
```

run: 2026-08-22 · deterministic · BASE=6 weeks, SIGMA=3, n=50 · this is the band behind every view

Three numbers come out: a center, a lower control limit, an upper one. The center is the baseline pass rate. The limits are three standard errors either side of it — the range a healthy week is allowed to wander in. Everything else in the file is a reading of one week's rate against these three frozen numbers.

### Look at the data: twelve weeks against the band

Here is the whole ledger, each week's rate drawn against the frozen band. Weeks 1-6 are the baseline the band was built from; weeks 7-12 are after a model swap.

```
# $ python3 livecheck.py --trend
#   baseline = first 6 weeks   center 0.800   LCL 0.630   UCL 0.970   (3 sigma, se 0.0566)
#   wk01 2026-06-01  base  40/50 = 0.80  ###################---------
#   wk02 2026-06-08  base  42/50 = 0.84  #####################-------
#   wk03 2026-06-15  base  38/50 = 0.76  #################-----------
#   wk04 2026-06-22  base  41/50 = 0.82  ####################--------
#   wk05 2026-06-29  base  39/50 = 0.78  ##################----------
#   wk06 2026-07-06  base  40/50 = 0.80  ###################---------
#   wk07 2026-07-13     31/50 = 0.62  ##########------------------  <-- below LCL
#   wk08 2026-07-20     30/50 = 0.60  #########-------------------  <-- below LCL
#   wk09 2026-07-27     32/50 = 0.64  ###########-----------------
#   wk10 2026-08-03     29/50 = 0.58  ########--------------------  <-- below LCL
#   wk11 2026-08-10     31/50 = 0.62  ##########------------------  <-- below LCL
#   wk12 2026-08-17     30/50 = 0.60  #########-------------------  <-- below LCL
```

run: 2026-08-22 · fixture; deterministic · n=50/week, 12 weeks · `python3 livecheck.py --trend`

Look at the baseline weeks first. They range from 0.76 to 0.84 — an eight-point spread — and every one of them is healthy. That spread is the toast: ordinary variation that a naive eye reads as "getting worse, then better, then worse." The band says all six are the same week. Now the regression: weeks 7-12 sit between 0.58 and 0.64, and five of the six are below the lower limit of 0.630. The eye that panicked at the 0.84-to-0.76 dip in the baseline has no calibration left for the 0.80-to-0.62 fall that actually matters.

<svg viewBox="0 0 700 260" role="img" aria-label="A control chart of twelve weekly pass rates. A shaded band runs from the lower control limit 0.63 to the upper 0.97 with a center line at 0.80. Weeks 1 through 6 fall inside the band around 0.80. Weeks 7 through 12 drop to between 0.58 and 0.64, five of them below the lower limit, marked as the regression.">
  <g font-family="var(--mono)" font-size="9">
    <rect x="56" y="40" width="588" height="86" fill="var(--acc-soft)"></rect>
    <line x1="56" y1="83" x2="644" y2="83" stroke="var(--line)" stroke-width="1.2" stroke-dasharray="4 3"></line>
    <line x1="56" y1="40" x2="644" y2="40" stroke="var(--s2)" stroke-width="1.2"></line>
    <line x1="56" y1="126" x2="644" y2="126" stroke="var(--s2)" stroke-width="1.4"></line>
    <text x="648" y="43" fill="var(--muted)">UCL 0.97</text>
    <text x="648" y="86" fill="var(--muted)">center 0.80</text>
    <text x="648" y="129" fill="var(--s2)">LCL 0.63</text>
    <g fill="var(--muted)" text-anchor="end"><text x="50" y="43">0.97</text><text x="50" y="171">0.58</text></g>
    <line x1="56" y1="30" x2="56" y2="210" stroke="var(--grid)" stroke-width="1"></line>
    <line x1="56" y1="210" x2="644" y2="210" stroke="var(--grid)" stroke-width="1"></line>
    <g>
      <circle cx="80" cy="83" r="4" fill="var(--s1)"></circle>
      <circle cx="128" cy="55" r="4" fill="var(--s1)"></circle>
      <circle cx="176" cy="98" r="4" fill="var(--s1)"></circle>
      <circle cx="224" cy="69" r="4" fill="var(--s1)"></circle>
      <circle cx="272" cy="112" r="4" fill="var(--s1)"></circle>
      <circle cx="320" cy="83" r="4" fill="var(--s1)"></circle>
      <circle cx="368" cy="169" r="4.5" fill="var(--s2)"></circle>
      <circle cx="416" cy="184" r="4.5" fill="var(--s2)"></circle>
      <circle cx="464" cy="155" r="4.5" fill="var(--ink)"></circle>
      <circle cx="512" cy="198" r="4.5" fill="var(--s2)"></circle>
      <circle cx="560" cy="169" r="4.5" fill="var(--s2)"></circle>
      <circle cx="608" cy="184" r="4.5" fill="var(--s2)"></circle>
    </g>
    <polyline points="80,83 128,55 176,98 224,69 272,112 320,83 368,169 416,184 464,155 512,198 560,169 608,184" fill="none" stroke="var(--muted)" stroke-width="1"></polyline>
    <g fill="var(--muted)" text-anchor="middle"><text x="80" y="224">w1</text><text x="320" y="224">w6</text><text x="368" y="224">w7</text><text x="608" y="224">w12</text></g>
    <rect x="356" y="234" width="264" height="18" rx="5" fill="var(--panel)" stroke="var(--s2)"></rect>
    <text x="488" y="246" text-anchor="middle" fill="var(--s2)">model swap: 5 of 6 weeks below LCL</text>
    <text x="80" y="246" fill="var(--muted)">baseline: all 6 inside the band</text>
  </g>
</svg>
^ The weekly pass rate against the frozen band. The baseline (weeks 1-6, light dots) wanders eight points and stays inside; the swap (weeks 7-12, dark dots) drops out the bottom, five of six below the lower limit.

How to read this: the diagnostic is a dot's position against the shaded band, never against the dot before it. A dot inside the band is "the same as baseline" no matter which way it moved; a dot below the band is a regression no matter how small the step that put it there. The failure signature of a real regression is a cluster of dots that leaves the band and stays out.

### Strategy #1 — alarm if it dropped since last week. The toast detector.

The most obvious detector compares each week to the one before and alarms on any drop. It is one line and it feels airtight — a regression is a drop, so catch every drop.

```
# livecheck.py:81-88 — COMPLETE (the trap: alarm on any week-over-week drop)
def alarm_naive(runs):
    """The trap: alarm on any week whose rate dropped since the week before.
    Returns the list of alarming week indices."""
    hits = []
    for i in range(1, len(runs)):
        if runs[i]["rate"] < runs[i - 1]["rate"]:
            hits.append(i)
    return hits
```

Run it across the twelve weeks and watch it cry wolf:

```
# $ python3 livecheck.py --naive
#   ALARM at wk03 2026-06-15: 0.84 -> 0.76  (baseline)
#   ALARM at wk05 2026-06-29: 0.82 -> 0.78  (baseline)
#   ALARM at wk07 2026-07-13: 0.80 -> 0.62  (regression)
#   ALARM at wk08 2026-07-20: 0.62 -> 0.60  (regression)
#   ALARM at wk10 2026-08-03: 0.64 -> 0.58  (regression)
#   ALARM at wk12 2026-08-17: 0.62 -> 0.60  (regression)
#   6 alarms total, 2 of them in the stable baseline.
```

run: 2026-08-22 · fixture · n=50/week · `python3 livecheck.py --naive`

Six alarms, and two of them fired in weeks where nothing was wrong — the ordinary 0.84-to-0.76 and 0.82-to-0.78 wobble. Here is the surprise, though: the point is not that it also fired correctly four times in the regression. The point is what it did to the alarms *inside* the regression. Look at week 9: the rate went 0.60 to 0.64, an improvement, so the naive detector went quiet — during the regression. And week 11 the same, 0.58 to 0.62, quiet. The detector that alarms on drops falls silent exactly when a broken agent has a slightly-less-broken week, telling the on-call "recovering" in the middle of a sustained failure. It is not merely noisy; it reads the wrong axis. A regression is not a step down, it is a level that is too low, and week-over-week deltas cannot see a level.

<svg viewBox="0 0 700 150" role="img" aria-label="Two rows of twelve weekly markers. The top row, the delta detector, marks alarms at weeks 3, 5, 7, 8, 10, 12 — scattered across both eras, with weeks 9 and 11 silent inside the regression. The bottom row, the truth, marks weeks 7 through 12 as the regression, contiguous.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="34" fill="var(--muted)">delta detector fires:</text>
    <text x="20" y="104" fill="var(--muted)">the actual regression:</text>
    <g>
      <text x="196" y="16" fill="var(--muted)" font-size="8">baseline (nothing wrong)</text>
      <text x="470" y="16" fill="var(--muted)" font-size="8">after the model swap</text>
      <line x1="340" y1="22" x2="340" y2="128" stroke="var(--grid)" stroke-width="1" stroke-dasharray="3 3"></line>
    </g>
    <g>
      <rect x="180" y="26" width="20" height="14" rx="3" fill="var(--s2)"></rect>
      <rect x="276" y="26" width="20" height="14" rx="3" fill="var(--s2)"></rect>
      <rect x="348" y="26" width="20" height="14" rx="3" fill="var(--ink)"></rect>
      <rect x="396" y="26" width="20" height="14" rx="3" fill="var(--ink)"></rect>
      <rect x="492" y="26" width="20" height="14" rx="3" fill="var(--ink)"></rect>
      <rect x="588" y="26" width="20" height="14" rx="3" fill="var(--ink)"></rect>
      <text x="454" y="56" font-size="8" fill="var(--s2)" text-anchor="middle">wk9 &amp; wk11 silent — "recovering" mid-failure</text>
    </g>
    <g>
      <rect x="348" y="96" width="20" height="14" rx="3" fill="var(--s2)"></rect>
      <rect x="396" y="96" width="20" height="14" rx="3" fill="var(--s2)"></rect>
      <rect x="444" y="96" width="20" height="14" rx="3" fill="var(--s2)"></rect>
      <rect x="492" y="96" width="20" height="14" rx="3" fill="var(--s2)"></rect>
      <rect x="540" y="96" width="20" height="14" rx="3" fill="var(--s2)"></rect>
      <rect x="588" y="96" width="20" height="14" rx="3" fill="var(--s2)"></rect>
    </g>
    <g fill="var(--muted)" text-anchor="middle" font-size="8"><text x="190" y="126">w3</text><text x="358" y="126">w7</text><text x="598" y="126">w12</text></g>
  </g>
</svg>
^ The delta detector's alarms (top) against the truth (bottom). It fires twice in the clean baseline and goes quiet on the two "up" weeks inside the regression — it tracks steps, and a regression is a level.

### Strategy #2 — a proper control chart, recomputed every week. This is the bug.

So drop the deltas and build the real thing: a control chart. Center, limits, alarm when a week falls below the lower limit. That is correct — and there is a single, natural, catastrophic mistake in how you maintain it. Every week a new row arrives, so every week you recompute the band over all the data you have. It feels like the responsible choice: use all the data, keep the baseline current. It is the bug.

```
# livecheck.py:91-104 — COMPLETE (the planted bug: recompute the band over all history)
def alarm_contaminated(runs):
    """THE BUG: recompute the band over ALL weeks seen so far, every week, so the
    regression is folded into its own baseline. Returns the first alarm or None."""
    for i in range(BASE, len(runs)):
        seen = runs[: i + 1]                       # <- includes the regressed weeks
        passed = sum(r["passed"] for r in seen)
        n = sum(r["n"] for r in seen)
        center = passed / n
        per_run_n = n / len(seen)
        se = sqrt(center * (1 - center) / per_run_n)
        lcl = center - SIGMA * se
        if runs[i]["rate"] < lcl:
            return i, lcl
    return None, None
```

Stop here and predict. This is a real control chart with correct 3-sigma limits. It runs every week. Does it catch the regression? Write down yes or no before the output.

```
# $ python3 livecheck.py --bug
#   no alarm, ever: the regressed weeks were folded into the baseline,
#   the band widened and drooped to cover them, and the chart went quiet
#   exactly when it should have screamed. The baseline must stay frozen.
```

run: 2026-08-22 · fixture · n=50/week · `python3 livecheck.py --bug`

Never. Not once in six weeks of a nineteen-point regression. Here is the mechanism, and it is worth slowing down for because it is the whole module. When week 7 comes in at 0.62 and you recompute over weeks 1-7, that 0.62 pulls the center down and, because the pass rate moved toward 0.5, the standard error *up* — the band both sinks and widens. Each further regressed week pulls it down again. By week 12 the recomputed lower limit has sunk from the frozen 0.630 to 0.512, and every regressed week — the lowest of which was 0.58 — sits comfortably above it, inside the band, "healthy." The regression defined its own normal. This is the taped-over smoke detector, except no one taped it: it desensitized itself, one honest-looking recompute at a time.

<svg viewBox="0 0 700 210" role="img" aria-label="Two lower-limit lines under the regression weeks. The frozen LCL sits at 0.63, above five of the six regressed weeks, so they breach it. The contaminated LCL sinks from 0.63 toward 0.512 as regressed weeks are folded in, ending below every regressed week, so none breach it.">
  <g font-family="var(--mono)" font-size="9">
    <text x="40" y="24" fill="var(--muted)">the six regressed weeks (0.58-0.64) against two lower limits</text>
    <g fill="var(--muted)" text-anchor="end"><text x="60" y="60">0.66</text><text x="60" y="180">0.50</text></g>
    <line x1="66" y1="40" x2="66" y2="184" stroke="var(--grid)" stroke-width="1"></line>
    <g>
      <circle cx="120" cy="84" r="4" fill="var(--ink)"></circle>
      <circle cx="200" cy="100" r="4" fill="var(--ink)"></circle>
      <circle cx="280" cy="68" r="4" fill="var(--ink)"></circle>
      <circle cx="360" cy="116" r="4" fill="var(--ink)"></circle>
      <circle cx="440" cy="84" r="4" fill="var(--ink)"></circle>
      <circle cx="520" cy="100" r="4" fill="var(--ink)"></circle>
    </g>
    <line x1="90" y1="76" x2="560" y2="76" stroke="var(--s2)" stroke-width="1.8"></line>
    <text x="566" y="79" fill="var(--s2)">frozen LCL 0.63</text>
    <text x="566" y="91" fill="var(--muted)" font-size="8">5 of 6 breach it</text>
    <polyline points="90,76 200,120 320,140 440,150 520,156 560,158" fill="none" stroke="var(--s1)" stroke-width="1.8" stroke-dasharray="5 3"></polyline>
    <text x="566" y="158" fill="var(--s1)">contaminated LCL</text>
    <text x="566" y="170" fill="var(--muted)" font-size="8">sinks to 0.512 — none breach</text>
    <g fill="var(--muted)" text-anchor="middle" font-size="8"><text x="120" y="200">w7</text><text x="520" y="200">w12</text></g>
  </g>
</svg>
^ Same six regressed weeks, two lower limits. The frozen limit holds at 0.63 and the weeks fall through it; the contaminated limit slides down to meet them and nothing ever breaches.

**A control chart that recomputes its baseline every week cannot detect a slow regression, because the regression becomes the baseline. The band must be frozen from a period you have certified as good.**

### Strategy #3 — freeze the band, alarm on two rules

The fix is one word: freeze. Certify the first six weeks as a good baseline, compute the band from them once, and never let a later week move it. Then read every new week against those fixed numbers with two rules — a point below the lower limit, or a sustained run of weeks below the center even if no single one breaches.

```
# livecheck.py:63-78 — COMPLETE (the frozen band, two rules)
def alarm_measured(runs):
    """Two rules on the FROZEN band: a point below the lower limit, or SHIFT
    weeks in a row below center. Returns the first alarming week or None."""
    center, lcl, ucl, _ = limits(runs)
    below_streak = 0
    for i, r in enumerate(runs):
        if r["rate"] < center:
            below_streak += 1
        else:
            below_streak = 0
        point = r["rate"] < lcl
        shift = below_streak >= SHIFT
        if point or shift:
            why = "point < LCL" if point else "%d wk run below center" % SHIFT
            return i, why
    return None, None
```

The point rule catches a sudden fall; the shift rule catches a slide too gentle to breach the limit in any single week — a run of weeks all on the low side of center, which the standard control-chart literature treats as its own signal precisely because a small sustained shift hides between the limits. Run it:

```
# $ python3 livecheck.py --alarm
#   center 0.800   LCL 0.630
#   ALARM at wk07 (2026-07-13): rate 0.62  --  point < LCL
#   caught the model swap the first week it showed, with zero baseline alarms.
```

run: 2026-08-22 · fixture · n=50/week · `python3 livecheck.py --alarm`

Week seven, the first week the regression appears, by the point rule — 0.62 is below the frozen 0.630. Zero alarms in the baseline, where the delta detector fired twice. The shift rule never even had to trigger here because the point rule caught it first, but it is the backstop: had the swap been gentler — say a drop to 0.66, above the limit — the six-in-a-row below center would have raised it by week eleven. Two rules, one deaf to toast, both awake to fire.

### The running tally

| detector | baseline (wks 1-6) | regression (wks 7-12) |
|---|---|---|
| delta: alarm on any drop | 2 false alarms | fires, but goes quiet on "up" weeks |
| control chart, recomputed each week (the bug) | silent | silent — never fires |
| frozen band + two rules | silent | ALARM wk07, first week |

The twelve weekly numbers never changed; only the detector reading them did. The delta detector is too sensitive and reads the wrong axis; the recomputed chart is a correct chart sabotaged by a live baseline; only the frozen band, calibrated on a certified-good period and never moved, is deaf to the baseline's wobble and awake to the swap. And the honest limit: this is a p-chart, which assumes each week's 50 tasks are roughly independent draws of comparable difficulty. If your suite is dominated by one flaky task or the difficulty drifts week to week, the band is miscalibrated and you will get exactly the false alarms this whole module is trying to kill.

**Do not ask whether this week dropped. Ask whether this week is inside the band you drew before anything went wrong.**

### The schedule that makes it live

The chart is nothing without the cron. A scheduled eval is a loop: on a cadence, run the suite against the live model, append one dated row, read the new row against the frozen band, alarm or stay quiet. The fixture stands in for the run, but the shape is exactly this.

<svg viewBox="0 0 700 150" role="img" aria-label="A weekly loop: a cron timer triggers a run of the suite against the live model, which appends a dated row to the ledger, which is read against the frozen band. A breach alarms the on-call; no breach stays quiet and loops back to wait for the next week. The frozen band is drawn once from the certified baseline and feeds the read step without being updated by it.">
  <g font-family="var(--mono)" font-size="10">
    <rect x="24" y="54" width="86" height="34" rx="6" fill="var(--panel)" stroke="var(--line)"></rect>
    <text x="67" y="75" text-anchor="middle" fill="var(--ink)">cron: wk+1</text>
    <rect x="140" y="54" width="102" height="34" rx="6" fill="var(--panel)" stroke="var(--line)"></rect>
    <text x="191" y="70" text-anchor="middle" fill="var(--ink)">run suite</text>
    <text x="191" y="82" text-anchor="middle" fill="var(--muted)">vs live model</text>
    <rect x="272" y="54" width="96" height="34" rx="6" fill="var(--panel)" stroke="var(--line)"></rect>
    <text x="320" y="70" text-anchor="middle" fill="var(--ink)">append row</text>
    <text x="320" y="82" text-anchor="middle" fill="var(--muted)">to ledger</text>
    <rect x="398" y="50" width="96" height="42" rx="6" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="446" y="67" text-anchor="middle" fill="var(--acc-ink)">read vs</text>
    <text x="446" y="81" text-anchor="middle" fill="var(--acc-ink)">frozen band</text>
    <line x1="110" y1="71" x2="138" y2="71" stroke="var(--muted)" stroke-width="1.4"></line>
    <line x1="242" y1="71" x2="270" y2="71" stroke="var(--muted)" stroke-width="1.4"></line>
    <line x1="368" y1="71" x2="396" y2="71" stroke="var(--muted)" stroke-width="1.4"></line>
    <rect x="548" y="30" width="112" height="28" rx="6" fill="var(--panel)" stroke="var(--s2)"></rect>
    <text x="604" y="48" text-anchor="middle" fill="var(--s2)">breach → alarm</text>
    <rect x="548" y="86" width="112" height="28" rx="6" fill="var(--panel)" stroke="var(--s1)"></rect>
    <text x="604" y="104" text-anchor="middle" fill="var(--s1)">quiet → wait</text>
    <line x1="494" y1="62" x2="546" y2="46" stroke="var(--s2)" stroke-width="1.4"></line>
    <line x1="494" y1="80" x2="546" y2="98" stroke="var(--s1)" stroke-width="1.4"></line>
    <path d="M 604 114 L 604 130 L 67 130 L 67 90" fill="none" stroke="var(--grid)" stroke-width="1.2" stroke-dasharray="3 3"></path>
    <rect x="398" y="112" width="96" height="24" rx="5" fill="var(--panel)" stroke="var(--grid)"></rect>
    <text x="446" y="128" text-anchor="middle" font-size="8.5" fill="var(--muted)">frozen once, never updated</text>
    <path d="M 446 112 L 446 94" fill="none" stroke="var(--grid)" stroke-width="1.2" stroke-dasharray="2 2"></path>
  </g>
</svg>
^ The scheduled loop. Each week runs, appends, and reads against the frozen band; only a breach breaks the quiet. The band is drawn once from the certified baseline and feeds the read without being touched by it — the freeze is the one arrow that does not close.

### Prove the whole thing in one run

One command checks the claims that hold this together: the band matches the closed-form standard error, the frozen detector catches the swap on its first week, and the contaminated detector stays silent.

```
# $ python3 livecheck.py --check
#   baseline center = 0.800, se = 0.0566, hand-computed se = 0.0566, agree = True
#   frozen LCL = 0.630  (regression weeks sit at ~0.60-0.64)
#   correct detector alarms at wk07 (point < LCL) = first regressed week is True
#   contaminated detector: no alarm (its LCL sinks below the regressed weeks)
#   by wk12 the contaminated LCL = 0.512 vs the frozen LCL = 0.630
#   SELF-TEST PASS  closed_form=True  caught_early=True  bug_silent=True  deterministic=True
```

run: 2026-08-22 · deterministic · n=50/week, 12 weeks · `python3 livecheck.py --check`

The standard error the code computes, 0.0566, is `sqrt(0.80*0.20/50)` to the digit; the frozen detector alarms at week 7; the contaminated one never does and its limit is shown sunk to 0.512, below the deepest regressed week. The self-test asserts all four and is the only thing you should trust over the prose.

### Bridge to the standard names

Nobody in industry calls it a smoke detector. This is **statistical process control**, invented by Shewhart at Bell Labs in the 1920s; the specific chart for a pass/fail proportion is a **p-chart**, its band the **control limits**, the run-below-center rule one of the **Western Electric rules** for detecting a shift the limits alone miss. The freeze has a name too: the certified baseline is **Phase I** and the ongoing monitoring is **Phase II**, and mixing them — estimating limits from the data you are monitoring — is the classic Phase I/Phase II error, which is exactly the contamination bug. In eval-specific language this is **regression testing over time** or **continuous evaluation**; the false-alarm axis is the **alerting precision** an on-call rotation lives and dies by. "Smoke detector" is just the operational feel of it: calibrated to ordinary variation, and never, ever taped over.

### What we did not settle

The twelve weeks are a fixture, so this measures the chart honestly and the world only as authored. The real complications we skipped, each of which can break a live chart: the p-chart assumes the 50 tasks are independent and of stable difficulty, which a suite with one dominant flaky task violates — you would move to a chart on the per-task residual or stratify; a real regression is often gradual, not a step, and choosing the shift-run length trades detection speed against false alarms exactly as a longer or shorter smoke-detector delay does; the upper limit matters too, because a suspicious *jump* in pass rate is often a broken grader, not a better agent; and re-certifying the baseline after a legitimate improvement (you shipped a real fix, the level really is higher now) is a deliberate, logged act — the one time you are allowed to move the band, and it must never happen automatically, because "the level looks higher now" is indistinguishable from the contamination bug until a human certifies which one it is.

## Build

The pipeline in one paragraph: run the same eval suite against the live model on a schedule; append one dated row per run to a ledger; certify a stable stretch as the baseline and freeze its 3-sigma band once; then read every new week against those fixed limits with two rules — a point below the lower limit, or a sustained run below center — and alarm on either, never on a week-over-week drop and never against a band you recomputed.

We opened on the alarm naming the exact week. The payoff again:

```
# modules/agent-harness/code/harness-adv-01/ — COMPLETE, run from that directory
$ python3 livecheck.py --alarm
  center 0.800   LCL 0.630
  ALARM at wk07 (2026-07-13): rate 0.62  --  point < LCL
```

Now point it at your own runs. The one dial is `ledger.json`: replace the twelve rows with your own dated `{date, n, passed}` records, one per scheduled run, and every number recomputes. Three tuning knobs sit at the top of the file, and the "what we did not settle" trade-offs live in them:

```
# livecheck.py:31-33 — COMPLETE (the three knobs)
BASE = 6          # weeks used to freeze the baseline band (the stable period)
SIGMA = 3.0       # control-limit width, in standard errors
SHIFT = 5         # consecutive weeks below center that count as a sustained shift
```

Set `BASE` to the number of leading weeks you can certify as genuinely stable — too few and the band is noisy, too many and you risk folding a slow regression into it. Leave `SIGMA` at 3 unless your on-call can absorb more pages for faster detection. Then wire the loop: a real scheduler (cron, a CI cron job, a workflow timer) runs the suite weekly, appends the row, and runs `livecheck.py --alarm`; a breach pages you.

Your number to beat is not a pass rate — it is your alarm's **false-alarm rate on a known-good stretch of history**. Replay a period where you know nothing regressed and count how often each detector fires: the delta detector will light up on ordinary wobble, the frozen band should be silent. Then inject a known regression — drop a handful of recent weeks by fifteen points — and confirm the frozen band catches it while a recomputed band swallows it. Bring back both numbers: false alarms on the good stretch, and the week your band caught the injected drop. Good luck.

### FAQ

**Why three sigma and not two?** Three sigma is the Shewhart default because it trades away sensitivity to buy a very low false-alarm rate — roughly one false point-alarm in 370 in-control runs. On a weekly cadence that is a false page every seven years, which is the point: an alarm you can trust. Two sigma catches smaller shifts faster and pages you far more often; use it only with an on-call that can absorb the noise.

**My pass rate is near 1.0 and the lower limit goes above a rate I actually hit — is that wrong?** Near the ceiling the symmetric normal band misbehaves; `sqrt(p(1-p)/n)` shrinks and the band gets tight and can clip. That is the p-chart's known weak spot at extreme proportions. Move to more tasks per run, or a chart on the log-odds, or an exact binomial limit.

**Should the baseline ever change?** Yes, once, deliberately, and logged: when you ship a real improvement and re-certify a new stable period as the baseline. That is the single legitimate un-freeze, and it is a human decision precisely because "the level is higher now" and "the grader broke and inflates everything now" produce the same upward shift.

**Why did the shift rule not fire in the demo?** Because the point rule caught the swap first, on week 7. The shift rule is the backstop for a gentler regression that never breaches the limit in one week; the module keeps it in for exactly that case and the "what we did not settle" section names the tuning it needs.

### Errata

Version one, dated 2026-08-22. The regression is authored as a clean step from ~0.80 to ~0.61 so the point rule fires on week 7 and the contamination is stark; a real regression is usually gradual, which is what the shift rule and the "what we did not settle" section exist to handle, and the point rule alone would catch such a case later or not at all. The p-chart's independence and stable-difficulty assumptions are stated but not stress-tested here; a suite with one dominant flaky task would need the stratification named above.

## Definition of done

- [ ] `ledger.json` of your own scheduled runs: dated `{date, n, passed}`, one row per run, at least three
- [ ] A frozen band: center and 3-sigma limits from a certified-stable baseline period, computed once
- [ ] The standard error is `sqrt(p*(1-p)/n)`, verified against a hand computation in `--check`
- [ ] Two alarm rules on the frozen band: a point below the lower limit, and a run of weeks below center
- [ ] The delta detector and the recomputed-band bug kept for contrast, so both failure modes are visible
- [ ] `python3 livecheck.py --check` printing SELF-TEST PASS: closed form, early catch, bug silent, deterministic
- [ ] The whole thing wired to a real schedule, appending a row and reading the band every run
- [ ] A measured false-alarm rate on a known-good stretch of history, and the week your band caught an injected drop
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. A weekly eval dropped from 0.84 to 0.76, then later held at 0.62 for six weeks. Say which of those is a regression and which is noise, and the one thing you compare each week against to tell them apart.
2. Give the standard error of a pass rate of 0.80 over 50 tasks, and turn it into a 3-sigma lower control limit. Then say why the regressed weeks at ~0.60 breach it.
3. State the contamination bug in one sentence. Explain, in terms of the center and the standard error, why recomputing the band each week makes it sink *and* widen, and what that does to the alarm.
4. The delta detector fired on two baseline weeks and went silent on two regression weeks. Explain both — why a false alarm in the baseline, and why silence during a real regression.
5. Give the two alarm rules on the frozen band and what each is for. Then say which one fired in your own run, on which week, and how many times the frozen band alarmed during the baseline.

## External resources

- Montgomery, *Introduction to Statistical Quality Control* — https://www.wiley.com/en-us/Introduction+to+Statistical+Quality+Control%2C+8th+Edition-p-9781119399308 — my summary: the standard text for control charts, the p-chart, and the Western Electric run rules this module borrows; read chapters 5-7 for the Phase I / Phase II split that names the contamination bug, and note it never once mentions evals — the machinery is a century older than the application.
- NIST/SEMATECH, *e-Handbook of Statistical Methods*, control charts — https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc3.htm — my summary: a free, worked treatment of Shewhart charts and control limits; the fastest way to check the closed form behind `limits()` and to see the p-chart's behavior near extreme proportions the FAQ warns about.
- This hub, *evals-inter-01* — modules/evals-and-statistics/evals-inter-01.md — my summary: the spread-and-interval discipline this module runs forward through time; if `sqrt(p(1-p)/n)` or "state the spread" feels unmotivated, that module builds the instinct from a single comparison before this one stretches it across twelve weeks.
