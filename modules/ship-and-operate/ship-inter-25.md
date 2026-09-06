---
id: ship-inter-25
title: Measure elapsed time with a monotonic clock, not the wall clock — or a clock correction makes a duration go backward
topic: ship-and-operate
level: intermediate
status: ready
time: 16 min
summary: To time anything — a request against a deadline, a backoff interval, a latency metric — you subtract a start reading from a now reading. That is a valid duration only if the clock advanced steadily in between, and the wall clock does not promise that: NTP periodically disciplines it to real-world time, and when it has drifted forward the correction steps it backward, sometimes by seconds. A start-to-now subtraction that straddles such a step measures the true elapsed minus the correction, which can be far too small or even negative, so a deadline check built on it silently stops firing. The monotonic clock exists for this: it only ever moves forward at a steady rate and is never adjusted, so the difference of two readings is always a real, non-negative elapsed time. On a fixture where an NTP correction steps the wall clock back 1.5 s at true time 1.0 s, the wall-clock elapsed drops to −0.5 s and never reaches the 2.0 s deadline even at 2.5 s of real time, while the monotonic elapsed equals the true elapsed exactly and crosses the deadline right at 2.0 s.
eli5: To measure how long something takes, you check the clock at the start and again at the end and subtract. That works with a stopwatch, which only counts up. It does not work with a wall clock that someone occasionally nudges to the "correct" time — if they nudge it backward while you're timing, your end reading can be earlier than your start reading, and your stopwatch says the task took negative seconds. Computers have both kinds of clock. Use the wall clock to know what time it is; use the stopwatch (the monotonic clock) to measure how long something took.
---

## Why this module

An elapsed time is a subtraction of two clock readings, and that subtraction is only a duration if the clock never went backward between them — which the wall clock, disciplined by NTP, does not guarantee.

Every timeout, retry interval, and latency measurement is the same operation: read the clock at the start, read it again now, subtract. The result is a trustworthy duration only under one assumption — that the clock ticked forward at a steady rate the whole time. The wall clock breaks that assumption routinely. It exists to track calendar time, so it is continuously corrected to match an authoritative source, and when the local clock has run fast, the correction pulls it *backward*. Straddle one of those steps with your start and now readings and the subtraction returns the true elapsed time minus the size of the correction. A one-second correction can turn a genuine 0.8-second duration into −0.2 seconds. A duration cannot be negative, but the arithmetic does not know that, and neither does the deadline check reading its output.

**A duration is start-to-now on whatever clock you read, so measuring it on the wall clock — which NTP can step backward — can yield an elapsed time that is too small or negative, and a timeout built on it silently stops firing.**

The monotonic clock is the fix, and it is a different clock, not a flag. It only ever advances, at a steady rate, and nothing — not NTP, not a manual date change, not a leap second — ever sets it backward or forward. Its absolute value is meaningless: it counts from an arbitrary origin like "seconds since the machine booted," not from any date, which is exactly why it is safe, because there is no outside truth anyone would adjust it to. The division of labor is clean: the wall clock answers "what time is it?" for logs and timestamps; the monotonic clock answers "how much time has passed?" for every duration. This module times a request against a deadline through an NTP step and shows the wall-clock measurement go backward while the monotonic one stays true.

## Concepts

**A wall clock** reports calendar time and is continuously disciplined by NTP toward an authoritative source. A correction can step it backward, so consecutive readings are not guaranteed to increase.

**A monotonic clock** reports seconds from an arbitrary origin and is never adjusted. Consecutive readings never decrease, so the difference of two readings is always a real, non-negative elapsed time.

**Measured elapsed** is always the same subtraction — now minus start — but its meaning depends entirely on which clock the readings came from.

```python filename=modules/ship-and-operate/code/ship-inter-25/monotonic.py:41-44 COMPLETE
def elapsed(samples, clock):
    """Measured elapsed time per sample: this clock's reading now minus its reading at the start."""
    start = samples[0][clock]
    return [s[clock] - start for s in samples]
```

**A deadline check** asks whether the measured elapsed has reached the timeout. If the measured elapsed can go backward or stall, the check can fail to fire even after the real deadline has passed.

```python filename=modules/ship-and-operate/code/ship-inter-25/monotonic.py:47-52 COMPLETE
def first_cross(samples, series, deadline):
    """The true time at which `series` first reaches the deadline, or None if it never does."""
    for s, e in zip(samples, series):
        if e >= deadline:
            return s["true"]
    return None
```

<svg role="img" aria-label="The wall clock rises then steps backward at an NTP correction, while the monotonic clock rises steadily without any step" viewBox="0 0 300 108" width="300" height="108">
  <line x1="30" y1="90" x2="290" y2="90" stroke="var(--grid)"/><line x1="30" y1="14" x2="30" y2="90" stroke="var(--grid)"/>
  <text x="4" y="20" fill="var(--muted)" font-size="7">reading</text><text x="250" y="100" fill="var(--muted)" font-size="7">true time →</text>
  <path d="M30 70 L70 60 L110 78 L150 68 L190 58 L230 48" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
  <text x="112" y="90" fill="var(--s2)" font-size="7">NTP step ↓</text>
  <line x1="110" y1="60" x2="110" y2="78" stroke="var(--s2)" stroke-dasharray="2 2"/>
  <text x="200" y="66" fill="var(--s2)" font-size="7">wall (jumps back)</text>
  <path d="M30 74 L70 66 L110 58 L150 50 L190 42 L230 34" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="176" y="34" fill="var(--s1)" font-size="7">monotonic (steady)</text>
  <text x="30" y="106" fill="var(--muted)" font-size="8">the wall clock steps backward at the correction; the monotonic clock only ever rises</text>
</svg>
^ The wall-clock reading climbs, then drops at the NTP correction and climbs again; the monotonic reading rises steadily throughout, so only its differences are valid durations.

**Read the wall clock for what time it is and the monotonic clock for how long something took — because only the monotonic clock guarantees that now minus start is a real elapsed time.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/ship-inter-25/monotonic.py

The fixture times a request against a 2.0 s deadline; at true time 1.0 s an NTP correction steps the wall clock back 1.5 s.

```json filename=modules/ship-and-operate/code/ship-inter-25/monotonic.json:3-11 COMPLETE
  "deadline": 2.0,
  "samples": [
    {"true": 0.0, "wall": 100.0, "mono": 500.0},
    {"true": 0.5, "wall": 100.5, "mono": 500.5},
    {"true": 1.0, "wall": 99.5,  "mono": 501.0},
    {"true": 1.5, "wall": 100.0, "mono": 501.5},
    {"true": 2.0, "wall": 100.5, "mono": 502.0},
    {"true": 2.5, "wall": 101.0, "mono": 502.5}
  ]
```

Run `--measure` to see the elapsed time each clock reports against the truth.

```text filename=--measure
MEASURE — elapsed time each clock reports (NTP steps the wall clock back 1.5s at true=1.0s)
------------------------------------------------------------------
  true elapsed   wall-clock elapsed   monotonic elapsed
    0.0            0.00                0.00
    0.5            0.50                0.50
    1.0           -0.50                1.00  <- went backward
    1.5            0.00                1.50
    2.0            0.50                2.00
    2.5            1.00                2.50
------------------------------------------------------------------
  the wall-clock elapsed drops below zero and never catches up; the monotonic tracks true exactly.
```

For the first second both clocks agree with the truth. Then the correction lands, and the wall-clock elapsed reads −0.50 s at true time 1.0 s — the request has been running for a full second, and its own clock says it started half a second in the future. From there the wall measurement climbs again but stays 1.5 s behind reality forever, so at 2.5 s of real elapsed time it reports 1.00 s. The monotonic column, meanwhile, is the true column: 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, never off by anything, because nothing stepped it. The −0.50 is the tell that should be impossible — no real duration is negative — and it is the exact fingerprint of a backward clock step landing inside a measurement.

<svg role="img" aria-label="Monotonic elapsed rises along the true-elapsed diagonal, while wall-clock elapsed dips negative at true 1.0 and stays well below, never reaching 2.0" viewBox="0 0 300 108" width="300" height="108">
  <line x1="30" y1="70" x2="290" y2="70" stroke="var(--grid)"/><text x="4" y="30" fill="var(--muted)" font-size="7">elapsed</text>
  <line x1="30" y1="20" x2="290" y2="20" stroke="var(--ink)" stroke-dasharray="2 2"/><text x="232" y="18" fill="var(--muted)" font-size="7">deadline 2.0</text>
  <path d="M30 62 L82 54 L134 46 L186 38 L238 20 L290 12" fill="none" stroke="var(--s1)" stroke-width="1.5"/><text x="196" y="34" fill="var(--s1)" font-size="7">monotonic = true</text>
  <circle cx="238" cy="20" r="2.5" fill="var(--s1)"/><text x="222" y="32" fill="var(--s1)" font-size="7">crosses</text>
  <path d="M30 62 L82 54 L134 78 L186 70 L238 62 L290 54" fill="none" stroke="var(--s2)" stroke-width="1.5"/><text x="120" y="90" fill="var(--s2)" font-size="7">wall — dips below 0, never reaches 2.0</text>
  <text x="30" y="104" fill="var(--muted)" font-size="8">only the monotonic line reaches the deadline; the wall line stays stranded below it</text>
</svg>
^ The monotonic elapsed follows the true-elapsed diagonal and crosses the 2.0 s deadline on time; the wall-clock elapsed dips below zero at the step and never climbs back to the deadline.

## Build

What the broken measurement does to the timeout is the whole cost. Run `--timeout`.

```text filename=--timeout
TIMEOUT — when each clock's measured elapsed crosses the 2.0s deadline
--------------------------------------------------------------
  wall clock:       fires at true NEVER (measured elapsed stalls below the deadline)
  monotonic clock:  fires at true 2.0s
--------------------------------------------------------------
  the request blows through its deadline unnoticed on the wall clock; the monotonic catches it on time.
```

The monotonic clock fires the timeout at true 2.0 s, exactly when the deadline is reached. The wall clock never fires it — its measured elapsed peaks at 1.00 s within this window and would keep trailing real time by the 1.5 s correction indefinitely, so the request runs past its deadline with the guard that was supposed to stop it permanently asleep. This is the failure that makes the bug dangerous rather than merely wrong: a timeout that reports a slightly-off duration is a nuisance, but a timeout that *never fires* removes a safety limit entirely. A hung request holds its connection and its slot forever; a retry loop that waits "until 2 s elapse" spins without end; a lock with a monotonic-less lease is never reclaimed. And it is intermittent by nature — it only manifests when a clock correction happens to land inside a live measurement — so it survives every test run where the clock behaved and detonates in production during a routine NTP adjustment. The fix costs one word: read the monotonic clock, not the wall clock, for the duration.

<svg role="img" aria-label="The monotonic clock reaches the deadline and fires; the wall clock's measured elapsed stays below the deadline and never fires" viewBox="0 0 300 92" width="300" height="92">
  <line x1="90" y1="16" x2="90" y2="78" stroke="var(--grid)"/>
  <line x1="250" y1="12" x2="250" y2="82" stroke="var(--ink)" stroke-dasharray="2 2"/><text x="228" y="10" fill="var(--muted)" font-size="7">deadline 2.0</text>
  <text x="6" y="32" fill="var(--muted)" font-size="8">monotonic</text>
  <rect x="90" y="24" width="160" height="12" fill="var(--s1)"/><text x="254" y="34" fill="var(--s1)" font-size="7">fires ✓</text>
  <text x="6" y="58" fill="var(--muted)" font-size="8">wall clock</text>
  <rect x="90" y="50" width="64" height="12" fill="var(--s2)"/><text x="158" y="60" fill="var(--muted)" font-size="7">stalls — never fires ✗</text>
  <text x="6" y="88" fill="var(--muted)" font-size="8">the wall-clock measurement never reaches the line, so the safety timeout is disabled</text>
</svg>
^ Measured on the monotonic clock the elapsed reaches the deadline and the timeout fires; measured on the wall clock it stalls short and the timeout never fires — a disabled safety limit.

## Definition of done

The self-test pins both clocks: the monotonic elapsed equals the true elapsed and never decreases, while the wall-clock elapsed goes backward and never reaches the deadline.

```python filename=modules/ship-and-operate/code/ship-inter-25/monotonic.py:95-108 COMPLETE
    mono_matches_true = all(abs(m - t) < 1e-9 for m, t in zip(mono, true))
    print("  monotonic elapsed equals the true elapsed at every sample = %s" % mono_matches_true)

    mono_never_backward = not goes_backward(mono)
    print("  monotonic elapsed never decreases = %s" % mono_never_backward)

    wall_goes_backward = goes_backward(wall)
    print("  wall-clock elapsed decreases (goes backward in time) = %s (min %.2f)" % (wall_goes_backward, min(wall)))

    mono_fires = first_cross(samples, mono, deadline) is not None
    print("  the monotonic clock crosses the deadline = %s (at true %.1fs)" % (mono_fires, first_cross(samples, mono, deadline)))

    wall_misses = first_cross(samples, wall, deadline) is None
    print("  the wall clock never crosses the deadline despite real time passing it = %s (max elapsed %.2f < %.1f)"
          % (wall_misses, max(wall), deadline))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the monotonic elapsed matches true and never decreases; the wall elapsed goes backward and misses the deadline
--------------------------------------------------------------------------------------------------------------------------
  monotonic elapsed equals the true elapsed at every sample = True
  monotonic elapsed never decreases = True
  wall-clock elapsed decreases (goes backward in time) = True (min -0.50)
  the monotonic clock crosses the deadline = True (at true 2.0s)
  the wall clock never crosses the deadline despite real time passing it = True (max elapsed 1.00 < 2.0)
```

**Done means the clock choice is proven to decide the outcome: the monotonic elapsed matches the true elapsed at every sample and never decreases, so its deadline check fires on time at true 2.0 s — while the wall-clock elapsed drops to −0.50 s at the NTP step and peaks at 1.00 s, so its deadline check never fires though real time passed 2.0 s.**

## Boss fight

Predict the two places this bites beyond a single timeout — the durable state that inherits the bug, and the clock that is monotonic but still not what you want. It is tempting to think "use monotonic for timeouts" is the whole rule.

The first trap is that a monotonic clock's readings are meaningless across process restarts and across machines, so anything durable or distributed cannot store them. The monotonic origin is arbitrary — often boot time — so a monotonic timestamp written to disk, sent over the network, or compared against another host's monotonic reading is nonsense: reboot the machine and the origin resets, so a saved "deadline at monotonic 502.0" now refers to a different moment or a time already passed. Durable deadlines and cross-host ordering need a shared reference, which means the wall clock (or a logical clock) with all its correction hazards, handled explicitly. The clean rule is narrower than "always use monotonic": use monotonic for a duration measured within one process's lifetime, and use a wall or logical clock — knowing it can jump — for anything that must survive a restart or cross a machine boundary.

```python filename=modules/ship-and-operate/code/ship-inter-25/monotonic.py:55-57 COMPLETE
def goes_backward(series):
    """True if the series ever decreases -- an impossible property for a real elapsed time."""
    return any(series[i + 1] < series[i] for i in range(len(series) - 1))
```

The second trap is that "monotonic" guarantees non-decreasing, not steady or comparable in rate. A monotonic clock can still be *slewed* — NTP often corrects small drift not by stepping but by temporarily speeding up or slowing the clock's rate, so a monotonic second may be slightly longer or shorter than a real second while never going backward. For a timeout that is fine; for a high-precision latency benchmark it is a systematic error. Different platforms also expose several monotonic sources with different resolutions and costs, and some (like a raw hardware counter) are per-core and can appear to go backward if a thread migrates between cores without the OS correcting for it. The lesson is to use the language's blessed monotonic call — the one the runtime guarantees is process-wide and non-decreasing — rather than a raw counter, and to remember that even it measures elapsed time only as accurately as the oscillator behind it. Monotonic solves the "went backward" catastrophe cleanly; it does not turn the clock into a metrology-grade instrument.

**Measure every in-process duration — timeouts, intervals, latencies — with the runtime's monotonic clock, because the wall clock can be stepped backward by NTP and make a measured elapsed negative and a timeout never fire; but a monotonic reading is meaningless across restarts and across machines (its origin is arbitrary), so durable and distributed deadlines still need a wall or logical clock handled with its jump hazards in mind, and even a monotonic clock is only non-decreasing, not perfectly steady.**

## External resources

Your language runtime's clock documentation — for example Python's `time.monotonic` versus `time.time`, or the equivalent `CLOCK_MONOTONIC` versus `CLOCK_REALTIME` in POSIX — which state exactly which clock is adjustable, which is monotonic, and what each guarantees.

Writing on NTP clock discipline (stepping versus slewing) and on the hazards of leap seconds and manual clock changes — the mechanisms that move the wall clock and the reasons a duration must not be built on it.

The companion "propagate the remaining deadline to each hop" and "store timestamps in UTC" modules — deadline propagation is where a duration crosses process and machine boundaries (so it needs the durable-clock handling this boss fight describes), and UTC timestamps are the wall-clock side of the same clock-hygiene discipline.
