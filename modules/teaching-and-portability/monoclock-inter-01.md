---
id: monoclock-inter-01
title: Measure elapsed time with a monotonic clock, not the wall clock — the wall clock can jump backward and make a duration negative
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: The reflex for timing a task is start = time.time(); work; elapsed = time.time() - start. It reads correctly and passes every test, because on a quiet machine the wall clock ticks smoothly forward. But the wall clock — the calendar clock — is periodically re-synced to an outside reference: an NTP daemon steps it, an operator sets it, DST rewinds it in autumn. Any of these can move it backward, and real time never does. When a backward step lands inside the interval you are timing, the second reading is smaller than it should be, so the measured duration undercounts the real elapsed time or goes negative outright. On the fixture here a task runs for a true 7.0 seconds while an NTP correction steps the wall clock back 10 seconds partway through: the wall-clock measurement comes out to -3.0 seconds, a negative duration for a task that plainly took time, while the true elapsed is 7.0. A negative or shrunken duration is not cosmetic — it poisons rate limiters, timeouts, retry backoff, and profilers downstream. The monotonic clock (time.monotonic, perf_counter) exists for exactly this: it answers "how much time has passed," counts from an arbitrary meaningless origin, and is guaranteed never to go backward, so the difference of two of its readings is always the true interval regardless of what the calendar clock did. The rule: time intervals with a monotonic clock; use the wall clock only to answer "what time is it" — timestamps and calendar arithmetic, never durations.
eli5: A wall clock on the wall tells you what time it is, but every so often someone notices it's a little fast and turns the hands back to fix it. If you were using that clock to time how long you baked cookies — noting the time when they went in and when they came out — and someone turned the hands back by ten minutes while the cookies were in the oven, your subtraction would say the cookies baked for negative three minutes. That's obviously wrong; the cookies really baked seven minutes. The fix is to use a stopwatch instead of the wall clock: a stopwatch only ever counts up and nobody resets it to fix the time of day, so the number it gives you is the real elapsed time. Computers have both — a wall clock for "what time is it" and a stopwatch for "how long did this take" — and you have to pick the stopwatch for durations.
---

## Why this module

Timing something is one of the first things you write, and the obvious code is right there in the standard library: note the time, do the work, subtract. It looks unimpeachable and it passes review, because when you run it the number is sensible every time. On your laptop, in CI, in the demo — the wall clock moves forward and the subtraction gives the elapsed seconds.

The bug only shows up when the wall clock does the one thing you never watched it do: move backward. It is a calendar clock, and calendar clocks get corrected. An NTP daemon decides the machine has drifted and steps the time. Someone sets the clock. Daylight-saving ends and the hour from 2am repeats. Each of these can push the reading earlier than a moment ago, and if it happens between your two measurements, your duration is wrong — sometimes shrunken, sometimes negative.

This module builds a task whose wall clock is stepped back ten seconds mid-run and measures its duration two ways. The monotonic clock reports the true seven seconds; the wall clock reports minus three. Then it shows why the monotonic clock cannot have this bug, and where each clock actually belongs.

**A wall clock answers "what time is it," and that question has a different answer after a correction than before — which is exactly the property you do not want in a stopwatch.**

## Concepts

A machine has two clocks, and they are not interchangeable. The wall clock, `time.time()`, tracks calendar time: it is the one that knows it is Tuesday, and it is kept honest by being re-synced to the outside world. The monotonic clock, `time.monotonic()`, tracks a raw count of elapsed time from an arbitrary origin nobody chose; it does not know what day it is and it is never re-synced.

The defining guarantee of the monotonic clock is in its name: successive readings never decrease. It only ever moves forward, so the difference between a later reading and an earlier one is always the real time that passed between them. Its absolute value is meaningless — it might read eight hundred thousand "seconds" since some boot-time origin — but differences are exactly what timing needs, and differences are what it gets right.

The wall clock offers no such guarantee. Its whole job is to match an external reference, so when it has drifted it is corrected, and a correction can be a step in either direction. A forward step makes an interval look too long; a backward step makes it look too short, or negative. Real elapsed time only ever increases, but the wall clock's reading of it does not, and that mismatch is the entire bug.

The figure lays the two clocks side by side across the same four events, with a backward correction landing at the third. The monotonic line climbs the whole way; the wall line climbs, then drops below where it was.

<svg role="img" aria-label="Two clock readings plotted across four events; the monotonic clock rises steadily at every event, while the wall clock rises for the first two events then drops sharply below its previous value at the third event before rising again" viewBox="0 0 640 300">
<line x1="60" y1="250" x2="600" y2="250" stroke="var(--line)" stroke-width="1"/>
<line x1="60" y1="30" x2="60" y2="250" stroke="var(--line)" stroke-width="1"/>
<text x="330" y="285" fill="var(--muted)" font-size="11" text-anchor="middle">event 0 &#8594; 1 &#8594; 2 &#8594; 3 (time really moves forward)</text>
<polyline points="110,210 250,170 390,130 530,90" fill="none" stroke="var(--ink)" stroke-width="2"/>
<circle cx="110" cy="210" r="4" fill="var(--ink)"/>
<circle cx="250" cy="170" r="4" fill="var(--ink)"/>
<circle cx="390" cy="130" r="4" fill="var(--ink)"/>
<circle cx="530" cy="90" r="4" fill="var(--ink)"/>
<text x="470" y="78" fill="var(--ink)" font-size="11">monotonic: only climbs</text>
<polyline points="110,200 250,160 390,235 530,215" fill="none" stroke="var(--s2)" stroke-width="2" stroke-dasharray="5 3"/>
<circle cx="110" cy="200" r="4" fill="var(--s2)"/>
<circle cx="250" cy="160" r="4" fill="var(--s2)"/>
<circle cx="390" cy="235" r="4" fill="var(--s2)"/>
<circle cx="530" cy="215" r="4" fill="var(--s2)"/>
<text x="400" y="255" fill="var(--s2)" font-size="11">wall: stepped back at event 2</text>
</svg>
^ Across the same four events the monotonic clock never decreases, while the wall clock drops below its previous reading when the correction lands.

**The monotonic clock is not a more accurate wall clock; it is a different instrument that answers "how much time passed" and refuses to answer "what time is it."**

## Worked example

The fixture is one task, with the real seconds between readings and the corrections applied to the wall clock kept separate.

```json filename=modules/teaching-and-portability/code/monoclock-inter-01/monoclock.json:3-6 COMPLETE
  "true_intervals": [2.0, 3.0, 2.0],
  "wall_jumps": [0.0, 0.0, -10.0, 0.0],
  "wall_start": 1700000000.0,
  "mono_start": 812345.0
```

Real time only moves forward, so `true_intervals` are all positive: the task takes 2, then 3, then 2 seconds — seven in total. The `wall_jumps` are corrections applied to the calendar clock at each event; the `-10.0` is an NTP step backward that lands at the third reading. The monotonic clock adds only the real intervals.

```python filename=modules/teaching-and-portability/code/monoclock-inter-01/monoclock.py:30-37 COMPLETE
def monotonic_readings(data):
    """The monotonic clock at each event: origin plus the real time elapsed so far. Never steps back."""
    out, t = [], data["mono_start"]
    out.append(t)
    for dt in data["true_intervals"]:
        t += dt                                  # only ever adds real elapsed time
        out.append(t)
    return out
```

The wall clock adds the same real intervals but also folds in each correction as it happens.

```python filename=modules/teaching-and-portability/code/monoclock-inter-01/monoclock.py:40-47 COMPLETE
def wall_readings(data):
    """The wall clock at each event: real time elapsed plus every correction applied so far. Can step back."""
    out, t = [], data["wall_start"] + data["wall_jumps"][0]
    out.append(t)
    for i, dt in enumerate(data["true_intervals"]):
        t += dt + data["wall_jumps"][i + 1]      # real time, then whatever correction hit the calendar clock
        out.append(t)
    return out
```

Printing both readings at each event shows the divergence directly: the wall clock reads earlier at event 2 than it did at event 1.

```text filename=monoclock.py --readings
READINGS — the two clocks at each event (the correction lands at event 2)
------------------------------------------------------------
  event      monotonic          wall
    0          812345.0      1700000000.0
    1          812347.0      1700000002.0
    2          812350.0      1699999995.0  <- wall stepped BACKWARD
    3          812352.0      1699999997.0
------------------------------------------------------------
  the monotonic reading only climbs; the wall clock reads earlier after the correction
```

A duration is the last reading minus the first — the shape of every `start; work; now - start` timer.

```python filename=modules/teaching-and-portability/code/monoclock-inter-01/monoclock.py:50-52 COMPLETE
def measure(readings):
    """A duration is measured as the last reading minus the first -- the idiom start; ...; now - start."""
    return readings[-1] - readings[0]
```

Apply that subtraction to each clock and the two answers split apart. The monotonic clock gives the true seven seconds; the wall clock gives minus three.

```text filename=monoclock.py --measure
MEASURE — the task duration, timed from each clock (now - start)
------------------------------------------------------------
  true elapsed (sum of real intervals) = 7.0 s
  monotonic: 812352.0 - 812345.0 = 7.0 s
  wall:      1699999997.0 - 1700000000.0 = -3.0 s
------------------------------------------------------------
  the monotonic measurement is the true 7.0 s; the wall measurement is -3.0 s -- a negative duration
```

Seven seconds of real work, measured as negative three, because the ten-second correction inside the interval is subtracted straight out of the answer. The figure shows the two measurements as arrows from the same start: the monotonic one runs forward to seven, the wall one runs backward past zero.

<svg role="img" aria-label="Two arrows starting from a common zero point; the monotonic arrow points right to a value of 7.0 seconds, and the wall arrow points left to a value of minus 3.0 seconds, crossing to the negative side of zero" viewBox="0 0 640 220">
<line x1="40" y1="120" x2="600" y2="120" stroke="var(--line)" stroke-width="1"/>
<line x1="220" y1="70" x2="220" y2="170" stroke="var(--grid)" stroke-width="1" stroke-dasharray="3 3"/>
<text x="220" y="186" fill="var(--muted)" font-size="11" text-anchor="middle">start (0 s)</text>
<line x1="220" y1="95" x2="520" y2="95" stroke="var(--ink)" stroke-width="2.5"/>
<polygon points="520,95 510,90 510,100" fill="var(--ink)"/>
<text x="530" y="99" fill="var(--ink)" font-size="12">monotonic +7.0 s</text>
<line x1="220" y1="145" x2="100" y2="145" stroke="var(--s2)" stroke-width="2.5"/>
<polygon points="100,145 110,140 110,150" fill="var(--s2)"/>
<text x="96" y="164" fill="var(--s2)" font-size="12" text-anchor="end">wall -3.0 s</text>
</svg>
^ Measured from the same start, the monotonic clock runs the true seven seconds forward while the wall clock's answer crosses to the wrong side of zero.

**The wall clock did not lose track of the time of day — after the correction it is more accurate about that than before — it just cannot be subtracted to get a duration, because the correction lives inside the subtraction.**

## Build

The monotonic clock's immunity is not luck; it is the never-decreases guarantee, and the self-test asserts exactly that alongside the wall clock's failure.

```python filename=modules/teaching-and-portability/code/monoclock-inter-01/monoclock.py:92-105 COMPLETE
    monotonic_never_decreases = all(mono[i] >= mono[i - 1] for i in range(1, len(mono)))
    print("  the monotonic clock never steps backward = %s" % monotonic_never_decreases)

    monotonic_is_true_elapsed = abs(measure(mono) - true_elapsed) < 1e-9
    print("  the monotonic measurement equals the true elapsed = %s (%.1f == %.1f)" % (monotonic_is_true_elapsed, measure(mono), true_elapsed))

    wall_steps_backward = any(wall[i] < wall[i - 1] for i in range(1, len(wall)))
    print("  the wall clock steps backward at the correction = %s" % wall_steps_backward)

    wall_is_wrong = abs(measure(wall) - true_elapsed) > 1e-9
    print("  the wall measurement is NOT the true elapsed = %s (%.1f != %.1f)" % (wall_is_wrong, measure(wall), true_elapsed))

    wall_goes_negative = measure(wall) < 0
    print("  the wall measurement is a negative duration = %s (%.1f s)" % (wall_goes_negative, measure(wall)))
```

The first two flags certify the monotonic clock: it never steps back, and its measurement equals the true elapsed. The last three certify the failure: the wall clock does step back, its measurement is wrong, and here it is outright negative.

```text filename=monoclock.py --check
SELF-TEST — the monotonic reading never decreases and gives the true elapsed; the wall clock decreases and gives a wrong, negative duration
----------------------------------------------------------------------------------------------------------------
  the monotonic clock never steps backward = True
  the monotonic measurement equals the true elapsed = True (7.0 == 7.0)
  the wall clock steps backward at the correction = True
  the wall measurement is NOT the true elapsed = True (-3.0 != 7.0)
  the wall measurement is a negative duration = True (-3.0 s)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  monotonic_never_decreases=True  monotonic_is_true_elapsed=True  wall_steps_backward=True  wall_is_wrong=True  wall_goes_negative=True
```

**The monotonic measurement matched the truth not because the fixture was kind but because the guarantee it relies on — never decreasing — is unconditional.**

## Definition of done

You are done when every duration in your code — every timeout, every rate-limit window, every retry backoff, every "how long did this take" — is measured from a monotonic clock, and the wall clock is reserved for timestamps and calendar arithmetic.

The division is clean once you ask what question you are answering. "How much time has passed" is a monotonic question: the answer must not change when the calendar is corrected, so use `time.monotonic()` (or `perf_counter()` for the finest resolution). "What time is it," "when did this event happen," "how many days until the deadline" are wall-clock questions: the answer is a point on the calendar, and you want it re-synced to the outside world, so use `time.time()` (stored in UTC — a separate portability rule).

<svg role="img" aria-label="A decision diagram: the question how much time has passed points to a box labeled monotonic clock for durations, and the question what time is it or when did it happen points to a box labeled wall clock for timestamps" viewBox="0 0 640 240">
<text x="320" y="30" fill="var(--muted)" font-size="12" text-anchor="middle">which clock?</text>
<text x="170" y="70" fill="var(--ink)" font-size="12" text-anchor="middle">"how much time passed?"</text>
<line x1="170" y1="80" x2="170" y2="120" stroke="var(--line)" stroke-width="1"/>
<polygon points="170,120 165,110 175,110" fill="var(--line)"/>
<rect x="70" y="122" width="200" height="60" fill="var(--panel)" stroke="var(--ink)" stroke-width="1.5" rx="6"/>
<text x="170" y="148" fill="var(--ink)" font-size="12" text-anchor="middle">monotonic clock</text>
<text x="170" y="166" fill="var(--muted)" font-size="11" text-anchor="middle">durations, timeouts, backoff</text>
<text x="470" y="70" fill="var(--ink)" font-size="12" text-anchor="middle">"what time is it / when?"</text>
<line x1="470" y1="80" x2="470" y2="120" stroke="var(--line)" stroke-width="1"/>
<polygon points="470,120 465,110 475,110" fill="var(--line)"/>
<rect x="370" y="122" width="200" height="60" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="6"/>
<text x="470" y="148" fill="var(--ink)" font-size="12" text-anchor="middle">wall clock</text>
<text x="470" y="166" fill="var(--muted)" font-size="11" text-anchor="middle">timestamps, calendar (in UTC)</text>
</svg>
^ Route every question to the clock that answers it: durations to the monotonic clock, points in time to the wall clock.

**If subtracting two readings is supposed to give you a length of time, those readings must come from the clock that cannot be reset underneath you.**

## Boss fight

Your turn: change the correction so it is larger and lands earlier. Set `wall_jumps` to `[0.0, -20.0, 0.0, 0.0]` — a twenty-second backward step at the very first interval — and rerun `--measure`. The true elapsed is still 7.0, the monotonic measurement is still 7.0, and the wall measurement drops further, to -15.0. No size of correction touches the monotonic answer, because the monotonic clock never saw the correction at all.

Then try a forward step: `[0.0, 0.0, 30.0, 0.0]`. Now the wall clock does not go backward, so `wall_goes_negative` flips to False and the self-test fails — but `wall_is_wrong` is still True, because the wall measurement is now 37.0 for a 7.0-second task. The negative duration was only the most obvious symptom; a forward correction corrupts the measurement just as thoroughly, it just does not announce itself with a minus sign. That is the real reason to distrust the wall clock for durations: even when the answer looks plausible, it is not the elapsed time.

**A negative duration is a gift, because it is impossible and you notice it; the dangerous case is the wall-clock correction that leaves a plausible-but-wrong number you never question.**

## External resources

The Python docs for the `time` module state the contract directly: `time.monotonic()` "cannot go backward" and is the correct clock for measuring intervals, while `time.perf_counter()` gives the highest available resolution for the same purpose.

PEP 418, "Add monotonic time, performance counter, and process time functions," is the design rationale — it catalogs exactly the wall-clock hazards (NTP steps, manual sets, leap seconds, DST) that motivated adding a guaranteed-monotonic clock to the standard library.

The NTP project's documentation on "slewing versus stepping" explains when a correction is applied gradually versus as a discrete backward jump, which is the mechanism behind the step this module models.
