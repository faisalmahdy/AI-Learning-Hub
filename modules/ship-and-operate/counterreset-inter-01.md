---
id: counterreset-inter-01
title: Compute a rate from a counter with reset-aware deltas — a restart drops it to zero and a plain subtraction goes negative
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: A cumulative counter — requests_total, bytes_sent, errors_total — only ever increases while a process runs, and a monitoring system samples it every scrape interval and reports the per-interval increase as current minus previous. That is exactly right until the process restarts: the counter is re-created at zero, so the next scrape reads a small value where the previous read a large one, and current minus previous is a large negative number — an impossible rate for a counter that only climbs. On a dashboard it shows as a sharp downward spike or a nonsensical negative throughput, and worse, any total summed from those deltas is short by roughly the pre-restart value, because the negative delta cancels real traffic. On the fixture the counter reads 10, 25, 40, then drops to 5 (a restart), then 18, 33; the plain deltas are 15, 15, −35, 13, 15 with a window total of 23, while the reset-aware deltas replace the −35 with 5 (the rise from zero after the reset) for 15, 15, 5, 13, 15 and a total of 63 — which matches the true in-window increase of (40 − 10) before the reset plus (33 − 0) after it. The fix is to recognize the reset: a reading smaller than the one before it means the counter restarted, so the increase since the last scrape is the new reading itself, not new minus old, which is exactly what a monitoring system's rate() and increase() do internally. The rule: a counter's value is not its rate, and turning value into rate must treat a drop as a restart, not as negative traffic.
eli5: Imagine a turnstile that counts everyone who walks through, and you check it each hour and write down how many more people passed by subtracting the last number from the new one. That works great — until someone reboots the turnstile and its count starts over at zero. Now the new number is smaller than your last one, and subtracting gives a negative answer, as if people walked through backwards. They didn't; the counter just restarted. The fix is to notice when the number is smaller than before and realize it reset, so the people who passed since your last check are just the new count itself, counted up from zero. Otherwise your negative hour cancels out real visitors and your daily total comes out way too low.
---

## Why this module

Every dashboard rate — requests per second, error rate, throughput — is computed from a counter that only goes up, by taking the difference between successive readings. It is one of the most basic operations in monitoring, and it has a failure mode built into the thing being measured: the counter's monotonicity is a property of the process, and processes restart.

A restart is not a rare edge case. Deploys restart processes, crashes restart processes, autoscaling and evictions restart processes. So the moment when the counter drops back to zero is a routine event, and a naive rate calculation turns every one of them into a spike of impossible data and a hole in every total that spans it.

**A counter's value is monotonic only within one process lifetime, so turning it into a rate must treat a drop as a restart rather than as negative change.**

## Concepts

A cumulative counter starts at zero when the process starts and increases forever after — it never decreases while that process lives. A scraper reads it every interval and reports the increase since the last read as current minus previous, which is correct precisely because the counter cannot go down within a lifetime.

The restart breaks the "within a lifetime" premise. The new process starts a fresh counter at zero, so the first scrape after the restart reads a small value while the previous scrape held a large one. Now current minus previous is negative — not a rate at all, but the arithmetic of subtracting the whole pre-restart total from the small post-restart value. A counter cannot produce a negative rate, so the negative delta is a signal that the premise was violated, not a measurement.

Two harms follow. First, the instantaneous rate is nonsense: a dashboard renders a deep downward spike, or a negative throughput that no query should ever show. Second, and quieter, any total accumulated by summing the deltas is wrong: the one big negative delta cancels a chunk of real traffic, so a "requests in this window" figure comes out far too low, and nobody notices because the number is merely plausible.

The fix is to detect the reset from the data. A reading smaller than the previous one can only mean the counter restarted. In that case the increase since the last scrape is not new minus old — it is simply the new reading, the amount counted up from zero since the restart. So the rule is: if current is at least previous, the delta is current minus previous; if current is smaller, the delta is current. That is the exact logic inside a monitoring system's rate() and increase() functions, and it is why you use them instead of raw subtraction.

**When a reading drops, the counter reset, and the increase is the new reading counted from zero — not the negative of new minus old.**

<svg role="img" aria-label="A decision. If the current reading is at least the previous, the delta is current minus previous, the normal case. If the current reading is smaller, the counter reset and the delta is the current reading itself." viewBox="0 0 460 150">
<rect x="0" y="0" width="460" height="150" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">the reset-aware rule for one scrape</text>
<text x="30" y="52" fill="var(--ink)" font-size="11">is current &#8805; previous?</text>
<line x1="200" y1="48" x2="270" y2="34" stroke="var(--line)"></line>
<line x1="200" y1="54" x2="270" y2="96" stroke="var(--line)"></line>
<text x="278" y="38" fill="var(--s2)" font-size="10">yes &#8594; delta = current &#8722; previous</text>
<text x="278" y="60" fill="var(--muted)" font-size="9">(normal increase)</text>
<text x="278" y="100" fill="var(--s1)" font-size="10">no &#8594; reset: delta = current</text>
<text x="278" y="122" fill="var(--muted)" font-size="9">(rise from zero since restart)</text>
</svg>
^ One branch handles the normal rise and one the restart; the plain method is only ever the top branch, which is why the drop turns into a negative number.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/ship-and-operate/code/counterreset-inter-01/counterreset.py

The fixture is six scrapes with one restart in the middle.

```json filename=modules/ship-and-operate/code/counterreset-inter-01/counterreset.json:3 COMPLETE
  "readings": [10, 25, 40, 5, 18, 33]
```

The naive rate is the plain difference between consecutive readings.

```python filename=modules/ship-and-operate/code/counterreset-inter-01/counterreset.py:30-32 COMPLETE
def plain_deltas(readings):
    """Per-scrape increase as current minus previous -- correct until the counter resets."""
    return [cur - prev for prev, cur in zip(readings, readings[1:])]
```

```text filename=counterreset.py --plain
PLAIN — per-scrape delta as current minus previous
----------------------------------------------------------------
  scrape 0->1:   10 ->  25   delta +15
  scrape 1->2:   25 ->  40   delta +15
  scrape 2->3:   40 ->   5   delta -35   <- reset (reading dropped)
  scrape 3->4:    5 ->  18   delta +13
  scrape 4->5:   18 ->  33   delta +15
```

The delta at the restart is −35: the counter dropped from 40 to 5, and the subtraction reports it as 35 fewer requests, which is impossible for a counter. Summing the deltas gives 23, but real traffic in this window was far more — the −35 cancelled the 30 that accumulated before the restart.

<svg role="img" aria-label="A sawtooth of the counter value across six scrapes: it rises 10, 25, 40, then drops sharply to 5, then rises 18, 33. The drop is marked as a process restart." viewBox="0 0 460 160">
<rect x="0" y="0" width="460" height="160" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">counter value over scrapes (drops to zero on restart)</text>
<line x1="40" y1="130" x2="430" y2="130" stroke="var(--line)"></line>
<line x1="40" y1="40" x2="40" y2="130" stroke="var(--line)"></line>
<polyline points="60,118 130,93 200,68 270,122 340,101 410,84" fill="none" stroke="var(--s2)"></polyline>
<circle cx="60" cy="118" r="3" fill="var(--s2)"></circle>
<circle cx="130" cy="93" r="3" fill="var(--s2)"></circle>
<circle cx="200" cy="68" r="3" fill="var(--s2)"></circle>
<circle cx="270" cy="122" r="3" fill="var(--s1)"></circle>
<circle cx="340" cy="101" r="3" fill="var(--s2)"></circle>
<circle cx="410" cy="84" r="3" fill="var(--s2)"></circle>
<line x1="200" y1="68" x2="270" y2="122" stroke="var(--s1)" stroke-dasharray="3 3"></line>
<text x="212" y="112" fill="var(--s1)" font-size="9">restart: 40 &#8594; 5</text>
<text x="60" y="145" fill="var(--muted)" font-size="9">10</text>
<text x="192" y="60" fill="var(--muted)" font-size="9">40</text>
<text x="262" y="140" fill="var(--muted)" font-size="9">5</text>
</svg>
^ The counter climbs, drops to near zero at the restart, and climbs again — a plain difference reads that drop as a large negative rate, which no counter can actually produce.

## Build

Reset-aware differencing treats the drop as a restart.

```python filename=modules/ship-and-operate/code/counterreset-inter-01/counterreset.py:35-40 COMPLETE
def reset_aware_deltas(readings):
    """Per-scrape increase, but a reading smaller than the last means a reset, so the increase is the new reading."""
    out = []
    for prev, cur in zip(readings, readings[1:]):
        out.append(cur - prev if cur >= prev else cur)
    return out
```

The true in-window increase sums each rise and counts a drop as a rise from zero.

```python filename=modules/ship-and-operate/code/counterreset-inter-01/counterreset.py:43-48 COMPLETE
def true_increase(readings):
    """The real in-window increase: sum each rising run, and count a drop as a rise from zero."""
    total = 0
    for prev, cur in zip(readings, readings[1:]):
        total += (cur - prev) if cur >= prev else cur
    return total
```

```text filename=counterreset.py --reset
RESET-AWARE — a drop means a restart, so the delta is the new reading
----------------------------------------------------------------
  scrape 0->1:   10 ->  25   delta +15
  scrape 1->2:   25 ->  40   delta +15
  scrape 2->3:   40 ->   5   delta +5   <- reset (reading dropped)
  scrape 3->4:    5 ->  18   delta +13
  scrape 4->5:   18 ->  33   delta +15
```

The −35 becomes +5 — the traffic counted from zero since the restart — every delta is non-negative, and the total is 63, matching the real in-window increase of (40 − 10) before the reset plus (33 − 0) after it.

<svg role="img" aria-label="Three totals for the window: plain sum 23, reset-aware sum 63, and the true increase 63. The plain bar is much shorter than the other two, which are equal." viewBox="0 0 440 160">
<rect x="0" y="0" width="440" height="160" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">window total: requests counted (true = 63)</text>
<line x1="50" y1="130" x2="420" y2="130" stroke="var(--line)"></line>
<line x1="50" y1="45" x2="420" y2="45" stroke="var(--grid)" stroke-dasharray="3 3"></line>
<text x="424" y="48" fill="var(--muted)" font-size="9">63</text>
<rect x="90" y="99" width="50" height="31" fill="var(--s1)"></rect>
<text x="92" y="94" fill="var(--s1)" font-size="10">plain 23</text>
<rect x="200" y="45" width="50" height="85" fill="var(--s2)"></rect>
<text x="196" y="40" fill="var(--s2)" font-size="10">reset 63</text>
<rect x="310" y="45" width="50" height="85" fill="var(--s2)"></rect>
<text x="308" y="40" fill="var(--muted)" font-size="10">true 63</text>
</svg>
^ The plain total is far short of the truth because the negative delta cancelled real traffic; the reset-aware total lands exactly on the true in-window increase.

The self-test pins both harms of the plain method and both fixes of the reset-aware one.

```python filename=modules/ship-and-operate/code/counterreset-inter-01/counterreset.py:87-91 COMPLETE
    plain_goes_negative = any(d < 0 for d in plain)
    print("  plain deltas include a negative (impossible for a counter) = %s (%s)" % (plain_goes_negative, plain))

    reset_all_nonneg = all(d >= 0 for d in reset)
    print("  reset-aware deltas are all non-negative = %s (%s)" % (reset_all_nonneg, reset))
```

```text filename=counterreset.py --check
SELF-TEST — the plain deltas include a negative value and a low total, while the reset-aware deltas are all non-negative and total the true in-window increase
----------------------------------------------------------------------------------------------------------------
  plain deltas include a negative (impossible for a counter) = True ([15, 15, -35, 13, 15])
  reset-aware deltas are all non-negative = True ([15, 15, 5, 13, 15])
  a reset was detected (a reading dropped) = True
  reset-aware total equals the true in-window increase = True (63 == 63)
  plain total undercounts the true increase = True (23 < 63)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  plain_goes_negative=True  reset_all_nonneg=True  reset_detected=True  reset_total_correct=True  plain_total_undercounts=True
```

**plain_total_undercounts is the quiet harm: the negative spike is visible on a graph, but the undercount in a summed total is just a plausible-looking wrong number nobody questions.**

## Definition of done

You can explain why a cumulative counter's monotonicity holds only within one process lifetime, and why a restart is a routine event that breaks it.

You can state the reset-aware rule — delta is current minus previous unless current is smaller, in which case delta is current — and why the new reading is the right increase after a reset.

You can name both harms of the naive method: the visible negative spike in the instantaneous rate, and the silent undercount in any total summed across the reset.

You can say why you use a monitoring system's rate()/increase() rather than raw subtraction, because that reset handling is exactly what those functions provide.

## Boss fight

Your "requests served today" dashboard number is computed by summing per-minute deltas of a requests_total counter, and on days with a deploy the number comes out suspiciously low — always low, never high. Nobody trusts it anymore.

First: explain precisely why the daily total is always low and never high on deploy days. What is the sign of the error each deploy introduces, and why can it never overcount?

Then: your fix detects a drop and uses the new reading as the delta. But this only estimates the traffic during the reset interval — the counter could have climbed higher than 40 and then reset, so the true increase in that interval might exceed what you recorded. Explain why the reset-aware value is a lower bound, why that is the best you can do from scrapes alone, and what you would need to measure it exactly.

Finally: a teammate proposes avoiding the whole problem by switching requests_total to a gauge that your app sets to the per-minute count directly. Explain what you gain and what you lose — specifically, what happens to a minute's data if a scrape is missed, for a counter versus for that gauge, and why cumulative counters are the standard despite the reset problem.

## External resources

Prometheus's documentation for rate() and increase() states explicitly that they "automatically adjust for counter resets," and its guidance on counter versus gauge metric types is the canonical framing of why counters are cumulative and how resets are handled.

The OpenMetrics specification formalizes the counter type and the meaning of a reset, and reading it clarifies why a decrease in a counter is defined to mean "the counter was reset," not "the value went down."
