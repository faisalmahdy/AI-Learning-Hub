"""Average rates with the harmonic mean, or the arithmetic mean overstates the true average speed.

"Average speed" tempts the arithmetic mean: drive 60 mph then 20 mph, average is (60+20)/2 = 40 mph. That is
wrong, and the reason is that speed is a RATE -- distance per time -- and the true average is total distance
over total TIME, not the average of the numbers. You spend far more time on the slow segment than the fast one
(covering the same distance at 20 mph takes three times as long as at 60), so the slow speed dominates the
trip, and the honest average is pulled toward it. The arithmetic mean weights each speed equally; the trip
weights each speed by how long you spend at it, which is the opposite of what you want when the DISTANCES are
equal.

When the segments cover equal distances, the correct average of the speeds is the HARMONIC mean:
n / (sum of 1/speed). It equals total-distance-over-total-time exactly, and it is always <= the arithmetic
mean, with equality only when all the speeds are the same. The rule generalizes: the right mean depends on
what is held constant. Equal distances -> harmonic mean of speeds; equal times -> arithmetic mean of speeds.
Averaging rates without asking "constant over what?" silently uses the arithmetic mean and gets a number that
corresponds to no real trip.

On this fixture two equal 60-mile legs are driven at 60 and 20 mph. The arithmetic mean says 40 mph. The true
average -- 120 miles over 4 hours -- is 30 mph, which is exactly the harmonic mean. This computes both.

  --trip       the time and the two candidate averages for the trip, vs the true speed
  --means      the arithmetic vs harmonic mean, and why harmonic is never larger
  --check      the arithmetic mean overstates; the harmonic mean equals total distance over total time

The distances and speeds are the fixture; every mean is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "trip.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def arithmetic_mean(xs):
    return sum(xs) / len(xs)


def harmonic_mean(xs):
    """n divided by the sum of reciprocals -- the correct average of equal-distance rates."""
    return len(xs) / sum(1.0 / x for x in xs)


def true_average_speed(distances, speeds):
    """Total distance over total time -- the definition of average speed."""
    total_time = sum(d / s for d, s in zip(distances, speeds))
    return sum(distances) / total_time


# ----------------------------------------------------------------- printing

def trip_view(data):
    d, s = data["distances"], data["speeds"]
    times = [dist / spd for dist, spd in zip(d, s)]
    print("TRIP — %d segments, distances %s mi, speeds %s mph" % (len(d), d, s))
    print("-" * 62)
    for i in range(len(d)):
        print("  leg %d: %d mi at %d mph -> %.2f h" % (i + 1, d[i], s[i], times[i]))
    print("  total: %d mi in %.2f h" % (sum(d), sum(times)))
    print("-" * 62)
    print("  arithmetic mean %.1f mph vs true average %.1f mph" % (arithmetic_mean(s), true_average_speed(d, s)))


def means_view(data):
    d, s = data["distances"], data["speeds"]
    print("MEANS — arithmetic vs harmonic mean of the speeds")
    print("-" * 62)
    print("  arithmetic: (%s)/%d = %.1f mph" % ("+".join(str(x) for x in s), len(s), arithmetic_mean(s)))
    print("  harmonic:   %d/(%s) = %.1f mph" % (len(s), "+".join("1/%d" % x for x in s), harmonic_mean(s)))
    print("  true speed: %d mi / %.2f h = %.1f mph" % (sum(d), sum(dd / ss for dd, ss in zip(d, s)), true_average_speed(d, s)))
    print("-" * 62)
    print("  the harmonic mean matches the true speed; the arithmetic mean sits above both.")


def check(data):
    print("SELF-TEST — the arithmetic mean overstates; the harmonic mean equals total distance over total time")
    print("-" * 100)
    d, s = data["distances"], data["speeds"]
    am, hm, true = arithmetic_mean(s), harmonic_mean(s), true_average_speed(d, s)

    equal_distances = len(set(d)) == 1
    print("  the segments are equal distance (so harmonic applies) = %s (%s)" % (equal_distances, d))

    harmonic_equals_true = abs(hm - true) < 1e-9
    print("  the harmonic mean equals total-distance-over-total-time = %s (%.1f = %.1f)" % (harmonic_equals_true, hm, true))

    arithmetic_overstates = am > true
    print("  the arithmetic mean is above the true average = %s (%.1f > %.1f)" % (arithmetic_overstates, am, true))

    harmonic_le_arithmetic = hm <= am
    print("  the harmonic mean is never larger than the arithmetic = %s (%.1f <= %.1f)" % (harmonic_le_arithmetic, hm, am))

    slow_leg_dominates_time = (d[1] / s[1]) > (d[0] / s[0]) if s[1] < s[0] else (d[0] / s[0]) > (d[1] / s[1])
    print("  more time is spent on the slower leg = %s" % slow_leg_dominates_time)

    ok = equal_distances and harmonic_equals_true and arithmetic_overstates and harmonic_le_arithmetic and slow_leg_dominates_time
    print("-" * 100)
    print("SELF-TEST %s  equal_distances=%s  harmonic_equals_true=%s  arithmetic_overstates=%s  harmonic_le_arithmetic=%s  slow_leg_dominates_time=%s"
          % ("PASS" if ok else "FAIL", equal_distances, harmonic_equals_true, arithmetic_overstates, harmonic_le_arithmetic, slow_leg_dominates_time))
    return ok


def main():
    p = argparse.ArgumentParser(description="Average equal-distance rates with the harmonic mean, not the arithmetic mean.")
    p.add_argument("--trip", action="store_true")
    p.add_argument("--means", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("segments=%d  distances=%s  speeds=%s  file=%s  (the trip is a fixture)"
          % (len(data["distances"]), data["distances"], data["speeds"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.trip:
        trip_view(data)
    elif args.means:
        means_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
