"""Round half to EVEN, not half up -- the default rounding rule is not the schoolbook one, and it keeps sums unbiased.

Rounding a value that sits exactly halfway between two integers -- a tie, like 2.5 -- has no correct answer; it has a
convention. The convention almost everyone learned in school is round-half-UP: on a tie, go away from zero (2.5 -> 3),
which you implement as 'add 0.5 and truncate'. The convention almost every computing platform actually USES is different:
round-half-to-EVEN, also called banker's rounding, where a tie goes to whichever neighbor is even (2.5 -> 2, 3.5 -> 4).
Python's built-in round(), the IEEE-754 floating-point default, and most spreadsheet and database engines round half to
even. So the rule in your head and the rule in your code disagree on every tie, and code that assumes half-up will be
wrong exactly when a value lands on the boundary.

The reason the default is half-to-even is not perversity, it is bias. Round-half-up pushes EVERY tie in the same
direction (away from zero), so if you round a column of numbers and add them, the ties all nudge the total upward and
the rounded sum drifts above the true sum -- a systematic error that grows with the number of ties. Round-half-to-even
sends ties up and down in balance (to whichever side is even), so over a symmetric set of ties the over- and
under-shoots cancel and the rounded sum stays centered on the true sum. That is why finance and statistics default to
it: it is the tie-break that does not accumulate bias.

A separate trap hides underneath all of this: most decimals are not stored exactly in binary, so a number that LOOKS
like a tie may not be one. 2.675 appears to be a tie for 2-place rounding, but the nearest double to 2.675 is
2.67499999999999982..., which is below 2.675, so it rounds DOWN to 2.67 -- not the 2.68 a half-up (or even a half-even)
rule on the exact decimal would give. The rounding rule never saw a tie, because the value it received was not one.

On this fixture the six ties 0.5..5.5 sum to 18.0. Round-half-to-even gives [0, 2, 2, 4, 4, 6], summing to 18 -- exactly
the true total. Round-half-up gives [1, 2, 3, 4, 5, 6], summing to 21 -- inflated by 3, which is 0.5 for each of the six
ties. And round(2.675, 2) is 2.67. This computes all of it.

  --ties   each tie under round-half-to-even vs round-half-up, and the two rounded sums against the true sum (18 vs 21)
  --repr   round(2.675, 2) = 2.67, with the actual stored value that shows 2.675 was never a tie in binary
  --check  half-even sends ties to even and preserves the sum; half-up biases the sum upward; the repr trap rounds 2.675 down

The ties and the trap value are the fixture; every rounded value and sum is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "roundeven.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def round_half_even(x):
    """Round to the nearest integer, ties to the even neighbor -- Python's built-in round() and the IEEE-754 default."""
    return round(x)


def round_half_up(x):
    """Round to the nearest integer, ties away from zero -- the schoolbook rule: add 0.5 and truncate."""
    return math.floor(x + 0.5)


def true_sum(values):
    return sum(values)


# ----------------------------------------------------------------- printing

def ties_view(data):
    ties = data["ties"]
    print("TIES — round-half-to-even vs round-half-up on exact halves")
    print("-" * 56)
    print("  tie    half-even   half-up")
    for x in ties:
        print("  %-5s  %-9d   %d" % (x, round_half_even(x), round_half_up(x)))
    print("-" * 56)
    even_sum = sum(round_half_even(x) for x in ties)
    up_sum = sum(round_half_up(x) for x in ties)
    ts = true_sum(ties)
    print("  true sum       = %.1f" % ts)
    print("  half-even sum  = %d   (matches the true sum -- unbiased)" % even_sum)
    print("  half-up sum    = %d   (inflated by %d = 0.5 x %d ties -- biased up)" % (up_sum, up_sum - int(ts), len(ties)))


def repr_view(data):
    v = data["repr_trap"]["value"]
    places = data["repr_trap"]["places"]
    expected = data["repr_trap"]["naive_expected"]
    print("REPR — a decimal that looks like a tie but is not one in binary")
    print("-" * 60)
    print("  value as written      = %s" % v)
    print("  value actually stored = %.20f" % v)
    print("  you expect round(%s, %d) = %s (round the .5 up)" % (v, places, expected))
    print("  Python gives round(%s, %d) = %s" % (v, places, round(v, places)))
    print("-" * 60)
    print("  the stored double is below %s, so it was never a tie -- it rounds down." % v)


def check(data):
    print("SELF-TEST — half-even sends ties to even and preserves the sum; half-up biases the sum upward; the repr trap rounds 2.675 down")
    print("-" * 124)
    ties = data["ties"]

    even_rounded = [round_half_even(x) for x in ties]
    ties_go_even = even_rounded == [0, 2, 2, 4, 4, 6]
    print("  round-half-to-even sends each tie to its even neighbor = %s (%s)" % (ties_go_even, even_rounded))

    up_rounded = [round_half_up(x) for x in ties]
    ties_go_up = up_rounded == [1, 2, 3, 4, 5, 6]
    print("  round-half-up sends every tie away from zero = %s (%s)" % (ties_go_up, up_rounded))

    ts = true_sum(ties)
    half_even_preserves_sum = sum(even_rounded) == ts
    print("  the half-even rounded sum equals the true sum = %s (%d == %.1f)" % (half_even_preserves_sum, sum(even_rounded), ts))

    half_up_biased = sum(up_rounded) == ts + 0.5 * len(ties)
    print("  the half-up rounded sum is inflated by 0.5 per tie = %s (%d == %.1f + 0.5x%d)" % (half_up_biased, sum(up_rounded), ts, len(ties)))

    v, places, expected = data["repr_trap"]["value"], data["repr_trap"]["places"], data["repr_trap"]["naive_expected"]
    repr_trap_rounds_down = round(v, places) != expected
    print("  round(%s, %d) is not the expected %s (binary repr trap) = %s (got %s)" % (v, places, expected, repr_trap_rounds_down, round(v, places)))

    ok = ties_go_even and ties_go_up and half_even_preserves_sum and half_up_biased and repr_trap_rounds_down
    print("-" * 124)
    print("SELF-TEST %s  ties_go_even=%s  ties_go_up=%s  half_even_preserves_sum=%s  half_up_biased=%s  repr_trap_rounds_down=%s"
          % ("PASS" if ok else "FAIL", ties_go_even, ties_go_up, half_even_preserves_sum, half_up_biased, repr_trap_rounds_down))
    return ok


def main():
    p = argparse.ArgumentParser(description="Round half to even: the default rounding rule in Python, IEEE-754, and most engines rounds ties to the nearest even integer (banker's rounding), not away from zero as the schoolbook half-up rule does, so half-up biases sums of ties upward; and binary float representation means a decimal that looks like a tie may not be one, so round(2.675, 2) is 2.67.")
    p.add_argument("--ties", action="store_true")
    p.add_argument("--repr", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("ties=%s  repr_trap=%s  file=%s  (the ties and trap value are a fixture)"
          % (data["ties"], data["repr_trap"]["value"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.ties:
        ties_view(data)
    elif getattr(args, "repr"):
        repr_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
