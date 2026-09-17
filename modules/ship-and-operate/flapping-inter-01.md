---
id: flapping-inter-01
title: Alert with hysteresis, not a single threshold — a metric hovering at the line pages on every wobble
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: An alert compares a metric to a threshold and fires when the metric crosses it, which is fine for a metric that moves decisively and fails for a noisy metric that sits near the level that matters — such a metric crosses the threshold many times in quick succession. A single-threshold alert reads each up-crossing as a fresh incident: it fires, the value dips below and it clears, the value rises and it fires again, so one sustained-ish condition generates a page per wobble, and the real cost is not the pages but the fatigue — an alert that fires several times an hour gets muted, and a muted alert misses the outage it was for. Hysteresis splits the one threshold into two: fire only when the metric exceeds a HIGH threshold, clear only when it drops below a LOWER one, and between them is a dead band, so oscillations that stay inside it do not toggle the alert; it fires once when the metric genuinely climbs past the high mark and holds until it truly recovers past the low mark. A "for duration" rule (require the breach to persist several samples before firing) is the other common fix; both stop a single crossing from meaning anything. On the fixture the samples oscillate around a threshold of 80: a single threshold fires 4 times as the metric bobs across it, while hysteresis with a high of 84 and a low of 76 fires once, and the samples between 76 and 84 (82, 78, 79, 77, 81) fall in the dead band and are ignored. The rule: an alert on a noisy metric must be insensitive to a single crossing, and a two-threshold band (or a hold-for-duration) is what provides that insensitivity.
eli5: Imagine a thermostat alarm set to beep when the room hits 80 degrees. If the room is sitting right around 80, it drifts up to 81 (beep), down to 79 (stop), up to 82 (beep), down to 78 (stop) — beeping over and over even though the temperature is basically steady, until you rip the batteries out. The fix is to give it two numbers: only start beeping at 84, and only stop at 76. Now the little wobbles between 76 and 84 don't set it off — it beeps once when the room really gets hot and quiets down once it really cools. Two numbers with a gap between them is what stops the constant beeping while still catching the real change.
---

## Why this module

On-call alerting has a failure mode that is not a missed alert or a false alert but a true alert firing too many times. When a system runs right at a limit — CPU near a cap, latency near an SLO, a queue near full — the metric does not sit still on one side of the threshold; it jitters across it. A naive alert turns that jitter into a stream of pages.

The damage is indirect and severe. A person paged five times in an hour for the same condition stops reading the alert, adds a mute, or tunes it out — and then the alert that actually needed action arrives into a channel everyone has learned to ignore. Flapping does not just annoy; it destroys the alert's credibility, which is the only thing that makes it useful.

**An alert on a noisy metric must not react to a single crossing, or a metric sitting at the threshold will page on every wobble and get muted.**

## Concepts

A single-threshold alert has one number and two states: below is clear, above is firing. The transition from clear to firing is a page. That design assumes the metric crosses the threshold rarely and decisively — true for a metric that jumps from healthy to broken, false for one that lives near the line.

A metric near its threshold is the common case, not an edge case: systems are often provisioned to run close to a limit, so the interesting metric hovers right where the alert is set. Noise then carries it back and forth across the threshold, and each up-crossing is a fresh page. The condition has not changed — the system is steadily near the limit — but the alert reports a new incident every time the value ticks up.

Hysteresis fixes this by making the fire and clear thresholds different numbers, with the fire threshold higher. Now there are three regions: above the high threshold (fire), below the low threshold (clear), and a dead band between them where the alert simply keeps its current state. A metric oscillating within the dead band never toggles the alert. It fires once, when the value climbs past the high mark, and does not clear until the value drops all the way past the low mark — so a sustained near-limit condition is one page, not many.

The same insensitivity can come from time instead of a band: a "for duration" rule requires the metric to stay above the threshold for several consecutive samples before firing, so a momentary crossing does not count. Both approaches encode the same principle — a single sample crossing the line is not an event — and real systems often use both together.

The cost is a small loss of responsiveness. Hysteresis delays the clear until the metric drops well below the threshold, and "for duration" delays the fire until the breach persists. That delay is the price of not flapping, and it is almost always worth paying, because a slightly late alert that people trust beats an instant alert they have muted.

**A single crossing is noise; hysteresis (a fire/clear band) and a for-duration hold both make the alert respond to a sustained condition instead, trading a little latency for credibility.**

<svg role="img" aria-label="A vertical scale with three regions: above the high threshold is fire, below the low threshold is clear, and the dead band between them holds the current state. A single threshold sits in the middle of the band where oscillations cross it." viewBox="0 0 320 160">
<rect x="0" y="0" width="320" height="160" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">hysteresis: fire high, clear low, hold between</text>
<rect x="120" y="30" width="160" height="30" fill="var(--s1)" opacity="0.4"></rect>
<text x="126" y="49" fill="var(--s1)" font-size="10">above 84: FIRE</text>
<rect x="120" y="62" width="160" height="34" fill="var(--grid)"></rect>
<text x="126" y="83" fill="var(--muted)" font-size="10">76..84: dead band (hold)</text>
<rect x="120" y="98" width="160" height="30" fill="var(--s2)" opacity="0.4"></rect>
<text x="126" y="117" fill="var(--s2)" font-size="10">below 76: CLEAR</text>
<line x1="120" y1="79" x2="280" y2="79" stroke="var(--ink)" stroke-dasharray="3 3"></line>
<text x="40" y="82" fill="var(--ink)" font-size="9">single at 80</text>
<text x="40" y="140" fill="var(--muted)" font-size="9">oscillations cross the single line but stay in the band</text>
</svg>
^ The single threshold sits inside the dead band, so the wobbles that keep crossing it never leave the band — hysteresis holds its state while the naive alert toggles.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/ship-and-operate/code/flapping-inter-01/flapping.py

The fixture is a metric oscillating around a threshold of 80.

```json filename=modules/ship-and-operate/code/flapping-inter-01/flapping.json:3-6 COMPLETE
  "samples": [70, 82, 78, 85, 79, 88, 77, 90, 81, 95],
  "threshold": 80,
  "high": 84,
  "low": 76
```

The single-threshold alert fires on every clear-to-fire crossing.

```python filename=modules/ship-and-operate/code/flapping-inter-01/flapping.py:30-38 COMPLETE
def single_threshold_fires(samples, threshold):
    """Count fire events for a single-threshold alert: each clear-to-fire crossing is one page."""
    firing, fires = False, 0
    for s in samples:
        if not firing and s > threshold:
            firing, fires = True, fires + 1
        elif firing and s <= threshold:
            firing = False
    return fires
```

```text filename=flapping.py --single
SINGLE — one threshold at 80
----------------------------------------------------------------
  trace: ['70', '82 FIRE', '78 clear', '85 FIRE', '79 clear', '88 FIRE', '77 clear', '90 FIRE', '81', '95']
  fire events: 4
----------------------------------------------------------------
  the metric bobs across the threshold, so the alert pages again and again
```

The trace shows the flapping directly: FIRE at 82, clear at 78, FIRE at 85, clear at 79, and so on — four pages as the metric bobs across 80, even though the situation (a metric steadily near 80) never really changed. Four pages, one condition.

<svg role="img" aria-label="A line of samples oscillating across a threshold at 80. Each time the line rises above 80 a fire marker appears; each time it dips below, a clear marker. Four fire markers." viewBox="0 0 320 150">
<rect x="0" y="0" width="320" height="150" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">metric bobbing across the single threshold (80)</text>
<line x1="30" y1="80" x2="300" y2="80" stroke="var(--grid)" stroke-dasharray="4 3"></line>
<text x="300" y="83" fill="var(--muted)" font-size="8">80</text>
<polyline points="40,105 70,72 100,88 130,64 160,84 190,55 220,90 250,50 280,74 300,45" fill="none" stroke="var(--s1)"></polyline>
<circle cx="70" cy="72" r="3" fill="var(--s1)"></circle>
<circle cx="130" cy="64" r="3" fill="var(--s1)"></circle>
<circle cx="190" cy="55" r="3" fill="var(--s1)"></circle>
<circle cx="250" cy="50" r="3" fill="var(--s1)"></circle>
<text x="120" y="130" fill="var(--s1)" font-size="9">4 fire events for one steady-near-80 condition</text>
</svg>
^ Each peak above the line is a page and each dip below clears it, so a metric that is simply sitting near 80 generates four separate incidents.

## Build

Hysteresis uses a high fire threshold and a low clear threshold, ignoring the band between.

```python filename=modules/ship-and-operate/code/flapping-inter-01/flapping.py:41-49 COMPLETE
def hysteresis_fires(samples, high, low):
    """Count fire events for a hysteresis alert: fire above high, clear below low, ignore the band between."""
    firing, fires = False, 0
    for s in samples:
        if not firing and s > high:
            firing, fires = True, fires + 1
        elif firing and s < low:
            firing = False
    return fires
```

```python filename=modules/ship-and-operate/code/flapping-inter-01/flapping.py:52-54 COMPLETE
def in_band(samples, high, low):
    """The samples that sit in the dead band -- they toggle a single threshold but not hysteresis."""
    return [s for s in samples if low <= s <= high]
```

```text filename=flapping.py --hysteresis
HYSTERESIS — fire above 84, clear below 76 (dead band 76..84)
----------------------------------------------------------------
  fire events: 1
  in-band samples (ignored): [82, 78, 79, 77, 81]
----------------------------------------------------------------
  oscillations inside the band do not toggle the alert, so it fires once and holds
```

Five of the ten samples — 82, 78, 79, 77, 81 — fall in the 76-to-84 dead band, and those are exactly the ones whose crossings of 80 caused the flapping. Hysteresis ignores them: it fires once when the metric first exceeds 84 and holds through the rest, one page for the whole episode.

<svg role="img" aria-label="A comparison of fire counts. The single-threshold alert fires 4 times; the hysteresis alert fires 1 time for the same samples." viewBox="0 0 320 150">
<rect x="0" y="0" width="320" height="150" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">pages for one near-limit episode</text>
<line x1="40" y1="120" x2="300" y2="120" stroke="var(--line)"></line>
<rect x="70" y="40" width="50" height="80" fill="var(--s1)"></rect>
<text x="76" y="34" fill="var(--s1)" font-size="10">single: 4</text>
<rect x="200" y="100" width="50" height="20" fill="var(--s2)"></rect>
<text x="200" y="94" fill="var(--s2)" font-size="10">hysteresis: 1</text>
</svg>
^ The same data pages on-call four times through a single threshold and once through the hysteresis band — the difference is entirely the dead-band samples the naive alert reacted to.

The self-test contrasts the two counts and names the in-band samples that drive the flapping.

```python filename=modules/ship-and-operate/code/flapping-inter-01/flapping.py:99-105 COMPLETE
    single = single_threshold_fires(s, t)
    single_flaps = single >= 3
    print("  single-threshold alert flaps (fires many times) = %s (%d fires)" % (single_flaps, single))

    hyst = hysteresis_fires(s, hi, lo)
    hysteresis_stable = hyst == 1
    print("  hysteresis alert fires once for the same data = %s (%d fire)" % (hysteresis_stable, hyst))
```

```text filename=flapping.py --check
SELF-TEST — the single-threshold alert flaps while hysteresis fires once for the same data, and the in-band samples are what toggle the naive alert
----------------------------------------------------------------------------------------------------------------
  single-threshold alert flaps (fires many times) = True (4 fires)
  hysteresis alert fires once for the same data = True (1 fire)
  hysteresis fires fewer times than the single threshold = True (1 < 4)
  several samples fall in the dead band that toggles the naive alert = True ([82, 78, 79, 77, 81])
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  single_flaps=True  hysteresis_stable=True  hysteresis_fewer=True  band_causes_flap=True
```

**band_causes_flap names the root cause: the flapping is entirely the samples in the dead band, so the fix is precisely to make the alert not react to that band.**

## Definition of done

You can explain why a single-threshold alert flaps on a metric that hovers near the threshold, and why the real cost is alert fatigue rather than the pages themselves.

You can define hysteresis with a fire and a clear threshold and a dead band, and show why oscillations inside the band do not toggle the alert.

You can name the alternative fix, a for-duration hold, and say what both approaches have in common — insensitivity to a single crossing.

You can state the cost of both — a small delay in firing or clearing — and why that latency is worth paying for an alert people will still trust.

## Boss fight

Your CPU alert at 80% pages the on-call engineer a dozen times one night while the service sits steadily around 80%, and the next morning a real incident's page is missed because the engineer had silenced the alert.

First: explain, in terms of this module, exactly what happened overnight and why silencing was the predictable human response. What was the metric doing, and why did a correct-looking threshold produce a dozen incidents from one condition?

Then: set the two hysteresis thresholds. What constraints decide the fire threshold (relative to the real danger level) and the clear threshold (relative to the fire threshold and the metric's noise amplitude), and what goes wrong if the gap between them is smaller than the noise?

Finally: hysteresis alone still fires late on the clear side — the alert stays active while the metric sits between the low and high thresholds recovering. Explain when you would add a for-duration rule on top, and give one condition where a for-duration hold is the better primary tool than hysteresis (hint: a metric that spikes cleanly but briefly, rather than one that hovers).

## External resources

Prometheus alerting rules expose the "for" clause exactly for this — an alert fires only after its condition holds for a specified duration — and its documentation frames it as the standard defense against flapping on a noisy metric.

Control-theory and monitoring references on hysteresis (the same mechanism a thermostat uses) explain the fire/clear band formally, and why the band must exceed the signal's noise amplitude to stop oscillation.
