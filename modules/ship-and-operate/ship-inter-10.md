---
id: ship-inter-10
title: Track the p99, not the mean — the average latency hides the tail regression that hits 1 in 20 users
topic: ship-and-operate
level: intermediate
status: ready
time: 22 min
summary: The mean latency drowns the slow tail in the many fast requests, so a regression that pushes the slowest 5% from 200ms to 900ms barely moves it. The mean creeps 57.5 → 92.5, staying under a 150ms alert, while the p99 jumps 200 → 900 and smashes the 500ms SLO. Percentiles see the tail; the mean cannot.
eli5: If nineteen friends get their food in five minutes and one waits an hour, the average wait still looks short — the one long wait gets buried. But that one person had a terrible time. To catch it you have to look at the slowest person, not the average person.
---

## Why this module

The single most misleading number on an operations dashboard is "average latency," and it is misleading in exactly the situation where you most need the truth.

Here is why. Your latency distribution is lopsided: most requests are fast, a few are slow, and there is no symmetric spread around a typical value the way there is for, say, human height. The mean of a lopsided distribution is dominated by the bulk — the 95% of requests that are fast — so it tells you about the common case and says almost nothing about the tail. But the tail is what your users feel. The person whose request took 900 milliseconds does not care that the average was 92; they care that their page hung. And tail slowness is rarely uniform bad luck; it is a specific slow path — a cold cache, a lock, a retry, a garbage-collection pause — that hits a predictable slice of traffic every time.

So when that slow path gets slower, the mean barely notices. Push the slowest 5% of requests from 200ms out to 900ms and the mean moves by the slow fraction times the change — a few percent of a few hundred milliseconds — while the tail itself, the thing you measure with a percentile, moves by the whole change. A mean-based alert, tuned to fire on a threshold the mean rarely approaches, sleeps straight through a regression that is degrading one in twenty requests to nearly a second.

This is why SLOs are written on percentiles. "p99 under 500ms" is a promise about the worst 1% of requests, and it is enforceable because the p99 is a direct readout of the tail. The mean bounds nothing: you can hit any mean you like with an arbitrarily bad tail, as long as enough requests are fast.

<svg role="img" aria-label="Twenty request dots: nineteen fast at 50ms and one slow at 900ms, the one the mean averages away" viewBox="0 0 460 120" width="460" height="120">
  <rect x="0" y="0" width="460" height="120" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="24" font-family="var(--mono)" font-size="11" fill="var(--muted)">1 in 20 requests (the slow 5%)</text>
  <g stroke="var(--line)">
    <circle cx="40" cy="60" r="9" fill="var(--acc-soft)"/><circle cx="70" cy="60" r="9" fill="var(--acc-soft)"/><circle cx="100" cy="60" r="9" fill="var(--acc-soft)"/><circle cx="130" cy="60" r="9" fill="var(--acc-soft)"/><circle cx="160" cy="60" r="9" fill="var(--acc-soft)"/>
    <circle cx="190" cy="60" r="9" fill="var(--acc-soft)"/><circle cx="220" cy="60" r="9" fill="var(--acc-soft)"/><circle cx="250" cy="60" r="9" fill="var(--acc-soft)"/><circle cx="280" cy="60" r="9" fill="var(--acc-soft)"/><circle cx="310" cy="60" r="9" fill="var(--s2)"/>
    <circle cx="40" cy="90" r="9" fill="var(--acc-soft)"/><circle cx="70" cy="90" r="9" fill="var(--acc-soft)"/><circle cx="100" cy="90" r="9" fill="var(--acc-soft)"/><circle cx="130" cy="90" r="9" fill="var(--acc-soft)"/><circle cx="160" cy="90" r="9" fill="var(--acc-soft)"/>
    <circle cx="190" cy="90" r="9" fill="var(--acc-soft)"/><circle cx="220" cy="90" r="9" fill="var(--acc-soft)"/><circle cx="250" cy="90" r="9" fill="var(--acc-soft)"/><circle cx="280" cy="90" r="9" fill="var(--acc-soft)"/><circle cx="310" cy="90" r="9" fill="var(--acc-soft)"/>
  </g>
  <text x="330" y="64" font-family="var(--mono)" font-size="10" fill="var(--s2)">← 900ms</text>
  <text x="330" y="94" font-family="var(--mono)" font-size="10" fill="var(--muted)">others 50ms</text>
</svg>
^ Nineteen fast requests and one slow one: the mean smears that one across all twenty, but the person who got it waited nearly a second.

We will measure the same endpoint before and after a tail regression. The mean stays quiet under its alert both times. The p99 goes from comfortably within the SLO to nearly double it. Same 95% of fast requests, one moved tail, two monitors — one blind, one that catches it.

**The mean is an average over everyone, so it hides the tail; the p99 is a readout of the tail, which is exactly the part your users feel and your SLO promises.**

## Concepts

A percentile is a rank statistic. The p99 latency is the value that 99% of requests come in at or under — equivalently, the threshold the slowest 1% exceed. Sort your requests by latency and the p99 is near the top of the list; the p50, the median, is the middle. Reading a percentile is reading a specific position in the sorted sample, which is why it tracks the tail directly: the p99 is *made of* tail requests, where the mean is made of all requests.

The mean and the median part ways precisely when the distribution is skewed. For a symmetric distribution they coincide, and either would do. For latency — fast bulk, slow tail — the mean is pulled toward the tail relative to the median, but only a little, because the tail is a small fraction. That "only a little" is the trap: the mean moves in the right direction when the tail worsens, just not enough to cross an alert threshold. The median may not move at all, because the middle of the sample is still a fast request. Only the high percentiles move enough to matter, because only they live where the change happened.

Which percentile you watch is a judgment about how much of your traffic you are willing to disappoint. p50 is the typical user and is nearly useless for catching tail problems. p90 catches broad slowness but misses a regression confined to a few percent. p99 catches a one-in-a-hundred slow path; p99.9 catches one-in-a-thousand, which for a high-traffic service is still thousands of requests an hour. The higher you go, the smaller the slice you protect and the noisier the estimate becomes — you need a large sample to estimate p99.9 stably. The standard compromise is to watch several — p50 for the typical experience, p99 for the tail your SLO covers — and never to watch the mean alone.

The computation here is the nearest-rank percentile: sort, take the value at rank ceil(p/100 × n). It is the simplest honest definition and it is exact for a given sample. Production systems approximate it — you cannot sort a billion latencies per minute — with sketches like t-digest or HDR histograms, but the meaning is identical: the value at a position in the sorted order.

**A percentile reads a position in the sorted sample, so a high percentile is built entirely from tail requests; that is why it moves when the tail moves and the mean does not.**

## Worked example

The fixture is two latency samples for one endpoint — a baseline and a regression — plus the two thresholds that decide whether anyone gets paged.

```json filename=modules/ship-and-operate/code/ship-inter-10/latencies.json:3-5 COMPLETE
  "slo_p99_ms": 500,
  "mean_alert_ms": 150,
  "samples": {
```

The SLO allows a p99 up to 500ms. A naive monitor pages when the mean exceeds 150ms. Both samples are a hundred requests, 95 of them fast; only the slow tail differs.

```text filename=modules/ship-and-operate/code/ship-inter-10/latency.py --samples
SAMPLES — two 100-request latency samples for the same endpoint (ms)
----------------------------------------------------------
  baseline   95 fast (50ms) + 5 slow (200ms)
  regressed  95 fast (50ms) + 5 slow (900ms)
----------------------------------------------------------
  95% of requests are identical across the two; only the slow 5% changed.
```

Ninety-five of every hundred requests are identical between the two samples — 50ms flat. The only change is the slow five: 200ms became 900ms. That is a real, targeted regression — a slow path got 4.5× worse — affecting exactly one in twenty requests. The mean is the average over all hundred.

```python filename=modules/ship-and-operate/code/ship-inter-10/latency.py:40-41 COMPLETE
def mean(xs):
    return round(sum(xs) / len(xs), 2)
```

The percentile is the value at a rank in the sorted sample.

```python filename=modules/ship-and-operate/code/ship-inter-10/latency.py:44-48 COMPLETE
def percentile(xs, p):
    """Nearest-rank percentile: the smallest value that at least p% of the sample come in under."""
    s = sorted(xs)
    rank = math.ceil(p / 100 * len(s))
    return s[rank - 1]
```

The stats view lays the mean beside the percentiles and flags each against its threshold.

```python filename=modules/ship-and-operate/code/ship-inter-10/latency.py:65-83 COMPLETE
def stats_view(data):
    slo, alert = data["slo_p99_ms"], data["mean_alert_ms"]
    print("STATS — mean vs percentiles; SLO p99<%d, mean alert>%d" % (slo, alert))
    print("-" * 62)
    print("  sample      mean    p50   p90    p99    mean alert   SLO p99")
    for name, xs in data["samples"].items():
        m = mean(xs)
        p99 = percentile(xs, 99)
        mflag = "FIRES" if m > alert else "quiet"
        sflag = "BREACH" if p99 > slo else "ok"
        print("  %-10s %5.1f  %4d  %4d  %5d    %-9s    %s"
              % (name, m, percentile(xs, 50), percentile(xs, 90), p99, mflag, sflag))
    print("-" * 62)
    print("  the mean alert never fires; the p99 breaches the SLO after the regression.")
```

Predict before running. The mean: baseline 57.5, regressed rises by 5% of the 700ms jump, so 92.5 — both under 150. The p99: baseline 200, regressed 900. Now run it.

```text filename=modules/ship-and-operate/code/ship-inter-10/latency.py --stats
STATS — mean vs percentiles; SLO p99<500, mean alert>150
--------------------------------------------------------------
  sample      mean    p50   p90    p99    mean alert   SLO p99
  baseline    57.5    50    50    200    quiet        ok
  regressed   92.5    50    50    900    quiet        BREACH
--------------------------------------------------------------
  the mean alert never fires; the p99 breaches the SLO after the regression.
```

Read across the two rows. The mean went 57.5 → 92.5 — it moved, but stayed "quiet," never approaching the 150ms alert. The p50 and p90 did not move at all: 50ms both times, because the middle and even the 90th percentile of the sample are still fast requests. Only the p99 tells the truth: 200 → 900, from "ok" to "BREACH." A team watching the mean sees a healthy 92ms and goes home; a team watching the p99 gets paged because one in a hundred requests now takes nearly a second and the SLO is broken.

<svg role="img" aria-label="A latency distribution: a tall bar of fast requests at 50ms and a short tail at 900ms; the mean sits just past the fast bulk while the p99 sits out in the tail" viewBox="0 0 460 180" width="460" height="180">
  <rect x="0" y="0" width="460" height="180" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">regressed sample: where each statistic lands</text>
  <line x1="40" y1="140" x2="440" y2="140" stroke="var(--line)"/>
  <rect x="50" y="40" width="40" height="100" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="46" y="155" font-family="var(--mono)" font-size="9" fill="var(--muted)">50ms</text><text x="52" y="36" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">95 reqs</text>
  <rect x="400" y="128" width="20" height="12" fill="var(--s2)" stroke="var(--line)"/><text x="388" y="155" font-family="var(--mono)" font-size="9" fill="var(--muted)">900ms</text><text x="384" y="122" font-family="var(--mono)" font-size="9" fill="var(--ink)">5 reqs</text>
  <line x1="108" y1="30" x2="108" y2="140" stroke="var(--ink)" stroke-dasharray="4 3"/><text x="112" y="60" font-family="var(--mono)" font-size="9" fill="var(--ink)">mean 92</text>
  <line x1="70" y1="30" x2="70" y2="140" stroke="var(--acc-ink)" stroke-dasharray="2 2"/><text x="60" y="112" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">p50 50</text>
  <line x1="410" y1="30" x2="410" y2="140" stroke="var(--s2)"/><text x="360" y="48" font-family="var(--mono)" font-size="9" fill="var(--s2)">p99 900</text>
  <text x="150" y="90" font-family="var(--mono)" font-size="10" fill="var(--muted)">the mean sits near the bulk;</text>
  <text x="150" y="106" font-family="var(--mono)" font-size="10" fill="var(--muted)">only the p99 reaches the tail</text>
</svg>
^ The mean and median sit in the fast bulk where 95% of requests live; the p99 is the only statistic that reaches the slow tail the regression actually moved.

<svg role="img" aria-label="Baseline vs regressed as two pairs of bars: means 57.5 and 92.5 both under the mean alert, p99s 200 and 900 with the regressed one past the SLO line" viewBox="0 0 460 190" width="460" height="190">
  <rect x="0" y="0" width="460" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">mean (left) never crosses its alert; p99 (right) breaches the SLO</text>
  <line x1="40" y1="150" x2="220" y2="150" stroke="var(--line)"/>
  <line x1="40" y1="120" x2="220" y2="120" stroke="var(--ink)" stroke-dasharray="4 3"/><text x="150" y="116" font-family="var(--mono)" font-size="9" fill="var(--ink)">alert 150</text>
  <rect x="70" y="139" width="30" height="11" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="66" y="164" font-family="var(--mono)" font-size="9" fill="var(--muted)">base 57</text>
  <rect x="140" y="132" width="30" height="18" fill="var(--s2)" stroke="var(--line)"/><text x="132" y="164" font-family="var(--mono)" font-size="9" fill="var(--muted)">regr 92</text>
  <line x1="250" y1="150" x2="440" y2="150" stroke="var(--line)"/>
  <line x1="250" y1="90" x2="440" y2="90" stroke="var(--ink)" stroke-dasharray="4 3"/><text x="360" y="86" font-family="var(--mono)" font-size="9" fill="var(--ink)">SLO 500</text>
  <rect x="280" y="126" width="30" height="24" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="276" y="164" font-family="var(--mono)" font-size="9" fill="var(--muted)">base 200</text>
  <rect x="350" y="42" width="30" height="108" fill="var(--s2)" stroke="var(--line)"/><text x="346" y="164" font-family="var(--mono)" font-size="9" fill="var(--muted)">regr 900</text>
</svg>
^ Both means stay under the alert line, so a mean monitor is silent through the regression; only the p99 crosses its SLO line, and only after the tail moved.

## Build

Reproduce the table. Pure standard library, deterministic samples, so 57.5, 92.5, 200, and 900 come out exactly.

Run `--samples` for the shape, `--stats` for the table, `--check` for the gate. The self-test pins the whole story: the mean stays under its alert, the p99 crosses from within-SLO to breaching, the median never moves, and the tail moves far more than the mean.

```python filename=modules/ship-and-operate/code/ship-inter-10/latency.py:87-94 COMPLETE
    m_base, m_regr = mean(base), mean(regr)
    mean_under_alert = m_regr <= alert  # the regressed mean is still below the alert threshold
    print("  the mean stays under its alert after the regression = %s (%.1f -> %.1f, alert %d)"
          % (mean_under_alert, m_base, m_regr, alert))

    p99_base, p99_regr = percentile(base, 99), percentile(regr, 99)
    p99_breaches = p99_base <= slo < p99_regr
    print("  the p99 goes from within-SLO to breaching = %s (%d -> %d, SLO %d)"
          % (p99_breaches, p99_base, p99_regr, slo))
```

The `p99_breaches` predicate is a crossing check, not a level check: `p99_base <= slo < p99_regr`. It demands the baseline p99 was within the SLO and the regressed p99 is not — that the regression is what pushed it over, not that it was always broken. A monitor that was already breaching before the regression would not demonstrate the point; this predicate insists the tail crossed the line, which is what a real regression looks like. Here is the full gate.

```text filename=modules/ship-and-operate/code/ship-inter-10/latency.py --check
SELF-TEST — the mean stays under its alert while the p99 breaches the SLO (averaging hid the tail)
--------------------------------------------------------------------------------------------
  the mean stays under its alert after the regression = True (57.5 -> 92.5, alert 150)
  the p99 goes from within-SLO to breaching = True (200 -> 900, SLO 500)
  even the median is unchanged -- only the tail moved = True (p50 50)
  the p99 moved far more than the mean = True (p99 +700 vs mean +35.0)
--------------------------------------------------------------------------------------------
SELF-TEST PASS  mean_under_alert=True  p99_breaches=True  p50_unchanged=True  tail_moves_more=True
```

Four True flags. Mean_under_alert: the mean monitor never fires. P99_breaches: the p99 crossed the SLO. P50_unchanged: the median did not move, proving the regression was purely in the tail. Tail_moves_more: the p99 moved 700ms against the mean's 35 — twenty times as much. Together they are the case for percentiles: the signal was entirely in a statistic the mean averages away.

**The p99 crossing is checked as a transition, not a level — the regression had to push the tail over the line, which is what distinguishes a regression from a system that was always broken.**

## Definition of done

You are done when you reproduce the table and can explain why the mean stayed quiet.

Concretely: `--stats` shows mean 57.5 → 92.5 (both quiet) and p99 200 → 900 (ok → BREACH); `--check` prints PASS with four True flags. You can define the p99 as the value 99% of requests come in under and explain why it tracks the tail while the mean does not — the mean averages the tail into the bulk, the p99 is the tail. You can say why the median did not move (the middle of the sample is still fast) and why SLOs are written on percentiles rather than means (a percentile bounds the worst experience; a mean bounds nothing). And you can name the right monitors to run: p50 and p99, never the mean alone.

The habit to carry: when someone reports a latency number, ask "which percentile?" and treat a bare "average latency" as a number that has already hidden the thing you need to see. Alert on p99, chart p50 and p99 together, and never let the mean be your tail alarm.

## Boss fight

The instructive failure is the migration that "had no performance impact" according to the dashboard and generated a wave of support tickets anyway.

A team ships a change that adds a slow path — a cache miss on a cold key, a fallback query — that fires on 2% of requests and adds 800ms. Their dashboard shows mean latency, which rises from 60ms to 76ms: a 16ms bump, well within noise, so the change is declared clean and rolled out fully. But 2% of every user's requests now take most of a second, and on a page that makes twenty requests, nearly every page load hits the slow path at least once. Tickets pour in about "the app feeling sluggish," and no one connects them to the migration because the latency graph is flat. The p99 would have jumped from 200ms to 800ms on day one. The mean buried the entire regression in the 98% that were unaffected.

Your turn, two moves. First, find the mean's blind spot precisely. Keeping the fast bulk at 50ms, how slow does the 5% tail have to get before the mean crosses its 150ms alert? Solve it: mean = 0.95×50 + 0.05×tail, set to 150, and you get a tail of about 2050ms — so the tail must reach two seconds before the mean monitor even notices, by which point the SLO has been broken for a very long time. Second, make the regression subtler and watch which monitor still catches it. Change the slow fraction from 5% to 1% and the slow value to 900ms, and predict: the mean barely moves at all (it rises by 1% of 850, under 9ms), the p90 and even p95 stay at 50ms, but the p99 still lands at 900 and breaches. The rarer the slow path, the more only the high percentiles can see it — which is the argument for watching p99 and p99.9, not stopping at the mean or the median.

## External resources

Gil Tene's talk "How NOT to Measure Latency" is the canonical treatment of why means and low percentiles lie about latency, and it introduces "coordinated omission," a second way tail measurements get silently wrong.

Google's SRE book chapters on SLOs and monitoring make the same case in production terms: define objectives on percentiles, alert on the percentile that matches the user experience, and never let an average stand in for the tail.

For the computation at scale, read up on t-digest (Ted Dunning) and HDR Histogram (Gil Tene) — the sketches that estimate high percentiles from a stream without sorting every value, which is how real systems compute the p99 this module computes by sorting.
