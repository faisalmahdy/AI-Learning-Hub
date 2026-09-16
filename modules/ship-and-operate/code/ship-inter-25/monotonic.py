"""Measure elapsed time with a monotonic clock, not the wall clock -- or a clock correction makes a duration go backward.

To time anything -- a request against a deadline, a retry backoff, a latency metric -- you subtract a start reading from
a now reading and call the difference the elapsed time. That is only a valid duration if the clock advanced steadily in
between. The wall clock does not promise that. It is periodically disciplined to real-world time by NTP, and when it has
drifted forward the correction steps it BACKWARD -- sometimes by seconds. A start-to-now subtraction that straddles such
a step measures the true elapsed time minus the correction, which can be far too small, or even negative. A "how long
has this run?" computed from the wall clock can come back as -0.5 seconds, and a deadline check built on it silently
stops firing: the measured elapsed stalls below the timeout while real time marches past it.

The monotonic clock exists for exactly this. It only ever moves forward, at a steady rate, and is never set or stepped,
so the difference of two monotonic readings is always a real, non-negative elapsed time. Its absolute value is
meaningless -- it counts from an arbitrary origin, not from any calendar date -- which is precisely why it is safe:
nothing ever adjusts it to match the outside world. Use the wall clock to answer "what time is it?" for logs and
timestamps; use the monotonic clock to answer "how much time has passed?" for every timeout, interval, and duration.

On this fixture a request is timed against a 2.0-second deadline while, at true time 1.0s, an NTP correction steps the
wall clock back by 1.5 seconds. Measured off the wall clock the elapsed time goes to -0.5s at that moment and never
reaches 2.0s even at 2.5s of real time -- so the timeout never fires. Measured off the monotonic clock the elapsed time
equals the true elapsed exactly, never decreases, and crosses the deadline right at 2.0s. This computes both.

  --measure   the elapsed time each clock reports at every sample, against the true elapsed -- the wall clock goes backward
  --timeout   when each clock's measured elapsed crosses the 2.0s deadline -- the wall clock never does
  --check     the monotonic elapsed matches true and never decreases; the wall elapsed goes backward and misses the deadline

The samples and deadline are the fixture; every elapsed time is computed by subtraction. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "monotonic.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def elapsed(samples, clock):
    """Measured elapsed time per sample: this clock's reading now minus its reading at the start."""
    start = samples[0][clock]
    return [s[clock] - start for s in samples]


def first_cross(samples, series, deadline):
    """The true time at which `series` first reaches the deadline, or None if it never does."""
    for s, e in zip(samples, series):
        if e >= deadline:
            return s["true"]
    return None


def goes_backward(series):
    """True if the series ever decreases -- an impossible property for a real elapsed time."""
    return any(series[i + 1] < series[i] for i in range(len(series) - 1))


# ----------------------------------------------------------------- printing

def measure_view(data):
    samples = data["samples"]
    wall, mono = elapsed(samples, "wall"), elapsed(samples, "mono")
    true = [s["true"] for s in samples]
    print("MEASURE — elapsed time each clock reports (NTP steps the wall clock back 1.5s at true=1.0s)")
    print("-" * 66)
    print("  true elapsed   wall-clock elapsed   monotonic elapsed")
    for t, w, m in zip(true, wall, mono):
        flag = "  <- went backward" if w < 0 else ""
        print("  %5.1f          %6.2f               %5.2f%s" % (t, w, m, flag))
    print("-" * 66)
    print("  the wall-clock elapsed drops below zero and never catches up; the monotonic tracks true exactly.")


def timeout_view(data):
    samples, deadline = data["samples"], data["deadline"]
    wall, mono = elapsed(samples, "wall"), elapsed(samples, "mono")
    cw, cm = first_cross(samples, wall, deadline), first_cross(samples, mono, deadline)
    print("TIMEOUT — when each clock's measured elapsed crosses the %.1fs deadline" % deadline)
    print("-" * 62)
    print("  wall clock:       fires at true %s" % ("%.1fs" % cw if cw is not None else "NEVER (measured elapsed stalls below the deadline)"))
    print("  monotonic clock:  fires at true %s" % ("%.1fs" % cm if cm is not None else "never"))
    print("-" * 62)
    print("  the request blows through its deadline unnoticed on the wall clock; the monotonic catches it on time.")


def check(data):
    print("SELF-TEST — the monotonic elapsed matches true and never decreases; the wall elapsed goes backward and misses the deadline")
    print("-" * 122)
    samples, deadline = data["samples"], data["deadline"]
    wall, mono = elapsed(samples, "wall"), elapsed(samples, "mono")
    true = [s["true"] for s in samples]

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

    ok = mono_matches_true and mono_never_backward and wall_goes_backward and mono_fires and wall_misses
    print("-" * 122)
    print("SELF-TEST %s  mono_matches_true=%s  mono_never_backward=%s  wall_goes_backward=%s  mono_fires=%s  wall_misses=%s"
          % ("PASS" if ok else "FAIL", mono_matches_true, mono_never_backward, wall_goes_backward, mono_fires, wall_misses))
    return ok


def main():
    p = argparse.ArgumentParser(description="Measure durations with a monotonic clock, not the wall clock, because an NTP correction can step the wall clock backward and make a measured elapsed time negative.")
    p.add_argument("--measure", action="store_true")
    p.add_argument("--timeout", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("deadline=%.1fs  samples=%d  file=%s  (the readings are a fixture; NTP steps the wall clock back at true=1.0s)"
          % (data["deadline"], len(data["samples"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.measure:
        measure_view(data)
    elif args.timeout:
        timeout_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
