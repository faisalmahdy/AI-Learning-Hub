"""Fix the summation order (or use an exact sum), or the same numbers total differently and no one reproduces you.

Floating-point addition is not associative. A 64-bit float carries about sixteen significant digits, so when you
add a small number to a huge one, the small number falls off the end and is rounded away: 1e16 + 1.0 is exactly
1e16, the 1.0 simply lost. That means the order you add things in changes the answer. Add 1.0 to 1e16 first and
the 1.0 vanishes, then subtracting 1e16 leaves 0.0. Cancel the two big values first and they make 0.0, then
adding 1.0 leaves 1.0. Same three numbers, two orders, two different totals -- and only one of them is the true
sum of 1.0.

This is a reproducibility trap, not just a numerical curiosity. You run your analysis, it prints a total, you
document that total to full precision. A reader reruns it and gets a different last few digits -- or a wildly
different answer, as here -- because their loop summed in another order, or their optimized math library
reordered the additions across SIMD lanes or threads, or they used a different BLAS. Your documented output is
not reproducible, and the culprit is invisible: everyone's arithmetic is 'correct', they just associated it
differently. The fix is to remove the order dependence: sum with a fixed, specified order, or use an
order-independent exact summation (math.fsum, or Kahan compensation) so every reader gets the same total.

On this fixture three values totalling exactly 1.0 are summed two ways. Left to right gives 0.0 -- the 1.0 is
absorbed into 1e16 and lost. Right to left gives 1.0 -- the big values cancel first. math.fsum gives 1.0 in
either order. This computes all of them.

  --orders     the running total left-to-right vs right-to-left, step by step, and each final answer
  --fix        naive orders vs math.fsum (exact) vs the true sum, and which are order-independent
  --check      the two orders disagree; naive summation loses the value; fsum is exact and order-independent

The values are the fixture; every total is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "sumorder.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def running_sum(values):
    """Add left to right, returning the running total after each step."""
    total, steps = 0.0, []
    for x in values:
        total = total + x
        steps.append(total)
    return steps


def left_to_right(values):
    return running_sum(values)[-1] if values else 0.0


def right_to_left(values):
    return running_sum(list(reversed(values)))[-1] if values else 0.0


def exact(values):
    """math.fsum tracks partial sums exactly, so the result does not depend on order."""
    return math.fsum(values)


# ----------------------------------------------------------------- printing

def orders_view(data):
    v = data["values"]
    print("ORDERS — the running total, left-to-right vs right-to-left")
    print("-" * 60)
    print("  left to right:  %s  ->  %g" % ([("%g" % s) for s in running_sum(v)], left_to_right(v)))
    print("  right to left:  %s  ->  %g" % ([("%g" % s) for s in running_sum(list(reversed(v)))], right_to_left(v)))
    print("-" * 60)
    print("  adding 1.0 to 1e16 loses it; cancelling the big values first keeps it.")


def fix_view(data):
    v = data["values"]
    print("FIX — naive orders vs an order-independent exact sum")
    print("-" * 60)
    print("  left to right:   %g   (naive, order-dependent)" % left_to_right(v))
    print("  right to left:   %g   (naive, order-dependent)" % right_to_left(v))
    print("  math.fsum:       %g   (exact, order-independent)" % exact(v))
    print("  true sum:        %g" % data["true_sum"])
    print("-" * 60)
    print("  only fsum gives the true sum regardless of order; every reader gets the same answer.")


def check(data):
    print("SELF-TEST — the two orders disagree; naive summation loses the value; fsum is exact and order-independent")
    print("-" * 108)
    v, true_sum = data["values"], data["true_sum"]

    not_associative = left_to_right(v) != right_to_left(v)
    print("  the same values sum differently in different orders = %s (%g vs %g)" % (not_associative, left_to_right(v), right_to_left(v)))

    naive_loses_value = left_to_right(v) != true_sum
    print("  the left-to-right sum is not the true total = %s (%g != %g)" % (naive_loses_value, left_to_right(v), true_sum))

    error_is_whole_value = abs(left_to_right(v) - right_to_left(v)) == abs(true_sum)
    print("  the disagreement is the entire small value = %s (|%g - %g| = %g)" % (error_is_whole_value, left_to_right(v), right_to_left(v), abs(true_sum)))

    fsum_exact = exact(v) == true_sum
    print("  math.fsum returns the exact true sum = %s (%g)" % (fsum_exact, exact(v)))

    fsum_order_independent = exact(v) == exact(list(reversed(v)))
    print("  math.fsum is the same in either order = %s (%g)" % (fsum_order_independent, exact(list(reversed(v)))))

    ok = not_associative and naive_loses_value and error_is_whole_value and fsum_exact and fsum_order_independent
    print("-" * 108)
    print("SELF-TEST %s  not_associative=%s  naive_loses_value=%s  error_is_whole_value=%s  fsum_exact=%s  fsum_order_independent=%s"
          % ("PASS" if ok else "FAIL", not_associative, naive_loses_value, error_is_whole_value, fsum_exact, fsum_order_independent))
    return ok


def main():
    p = argparse.ArgumentParser(description="Floating-point addition is not associative; fix the order or use an exact sum so a documented total is reproducible.")
    p.add_argument("--orders", action="store_true")
    p.add_argument("--fix", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("values=%s  true_sum=%g  file=%s  (the values are a fixture)"
          % (data["values"], data["true_sum"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.orders:
        orders_view(data)
    elif args.fix:
        fix_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
