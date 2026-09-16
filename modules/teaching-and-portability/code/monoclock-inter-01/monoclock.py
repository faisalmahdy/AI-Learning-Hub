"""Measure an elapsed interval with a monotonic clock, not the wall clock -- the wall clock can be stepped backward mid-measurement, so a duration timed from it comes out too small or even negative, while a monotonic clock only ever moves forward.

There are two clocks, and they answer two different questions. The wall clock (time.time) answers 'what time is it': it tracks calendar time and is periodically re-synced to an outside reference. An NTP daemon nudges or steps it, an operator sets it, DST rewinds it in the autumn. The monotonic clock (time.monotonic, perf_counter) answers 'how much time has passed': it counts from an arbitrary origin and is guaranteed never to go backward.

Timing a task is a 'how much time has passed' question, so it belongs to the monotonic clock. The classic bug uses the wall clock instead -- start = time.time(); ...; elapsed = time.time() - start -- because it is the clock everyone reaches for. That works until the wall clock is corrected during the interval. Real time only ever moves forward, but the wall clock's reading does not: a backward step subtracts from the second reading, so the difference undercounts the real elapsed time, and a step larger than the elapsed-so-far makes the measured duration negative.

A negative or shrunken duration is not a harmless cosmetic error. It feeds rate limiters (which now think no time passed and throttle), timeouts (which fire early or never), retry backoff (which computes a nonsensical wait), and profilers (which report impossible speeds). The monotonic clock has none of this exposure: its readings never decrease, so the difference of two of them is always the true elapsed interval, no matter what the calendar clock did in between.

On this fixture a task runs for a true 7.0 seconds, and an NTP correction steps the wall clock back 10 seconds partway through. Measured on the monotonic clock the duration is the true 7.0; measured on the wall clock it is -3.0 -- a negative duration for a task that plainly took time. This computes both.

  --readings   the two clocks' readings at each event: monotonic climbs, the wall clock drops at the correction
  --measure    the task duration measured each way: the monotonic true 7.0 versus the wall clock's -3.0
  --check      the monotonic reading never decreases and gives the true elapsed; the wall clock decreases and gives a wrong, negative duration

true_intervals and wall_jumps are the fixture; the readings and the two measured durations are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "monoclock.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def monotonic_readings(data):
    """The monotonic clock at each event: origin plus the real time elapsed so far. Never steps back."""
    out, t = [], data["mono_start"]
    out.append(t)
    for dt in data["true_intervals"]:
        t += dt                                  # only ever adds real elapsed time
        out.append(t)
    return out


def wall_readings(data):
    """The wall clock at each event: real time elapsed plus every correction applied so far. Can step back."""
    out, t = [], data["wall_start"] + data["wall_jumps"][0]
    out.append(t)
    for i, dt in enumerate(data["true_intervals"]):
        t += dt + data["wall_jumps"][i + 1]      # real time, then whatever correction hit the calendar clock
        out.append(t)
    return out


def measure(readings):
    """A duration is measured as the last reading minus the first -- the idiom start; ...; now - start."""
    return readings[-1] - readings[0]


# ----------------------------------------------------------------- printing

def readings_view(data):
    mono = monotonic_readings(data)
    wall = wall_readings(data)
    print("READINGS — the two clocks at each event (the correction lands at event 2)")
    print("-" * 60)
    print("  event      monotonic          wall")
    for i in range(len(mono)):
        step = ""
        if i > 0 and wall[i] < wall[i - 1]:
            step = "  <- wall stepped BACKWARD"
        print("    %d      %12.1f    %14.1f%s" % (i, mono[i], wall[i], step))
    print("-" * 60)
    print("  the monotonic reading only climbs; the wall clock reads earlier after the correction")


def measure_view(data):
    mono = monotonic_readings(data)
    wall = wall_readings(data)
    true_elapsed = sum(data["true_intervals"])
    print("MEASURE — the task duration, timed from each clock (now - start)")
    print("-" * 60)
    print("  true elapsed (sum of real intervals) = %.1f s" % true_elapsed)
    print("  monotonic: %.1f - %.1f = %.1f s" % (mono[-1], mono[0], measure(mono)))
    print("  wall:      %.1f - %.1f = %.1f s" % (wall[-1], wall[0], measure(wall)))
    print("-" * 60)
    print("  the monotonic measurement is the true %.1f s; the wall measurement is %.1f s -- a negative duration" % (true_elapsed, measure(wall)))


def check(data):
    print("SELF-TEST — the monotonic reading never decreases and gives the true elapsed; the wall clock decreases and gives a wrong, negative duration")
    print("-" * 112)
    mono = monotonic_readings(data)
    wall = wall_readings(data)
    true_elapsed = sum(data["true_intervals"])

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

    ok = (monotonic_never_decreases and monotonic_is_true_elapsed and wall_steps_backward
          and wall_is_wrong and wall_goes_negative)
    print("-" * 112)
    print("SELF-TEST %s  monotonic_never_decreases=%s  monotonic_is_true_elapsed=%s  wall_steps_backward=%s  wall_is_wrong=%s  wall_goes_negative=%s"
          % ("PASS" if ok else "FAIL", monotonic_never_decreases, monotonic_is_true_elapsed, wall_steps_backward,
             wall_is_wrong, wall_goes_negative))
    return ok


def main():
    p = argparse.ArgumentParser(description="Monotonic vs wall clock: measure an elapsed interval with a monotonic clock (time.monotonic), never the wall clock (time.time), because the wall clock is re-synced and can step backward mid-measurement, making a timed duration too small or negative, while the monotonic clock only ever moves forward.")
    p.add_argument("--readings", action="store_true")
    p.add_argument("--measure", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("true_intervals=%s  wall_jumps=%s  file=%s  (these are a fixture)"
          % (data["true_intervals"], data["wall_jumps"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.readings:
        readings_view(data)
    elif args.measure:
        measure_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
