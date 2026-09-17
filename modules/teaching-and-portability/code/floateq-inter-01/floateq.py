"""Never compare floats with == -- 0.1 + 0.2 is not 0.3, because decimals do not fit exactly in binary; compare with a tolerance.

A floating-point number is stored in binary, and most decimal fractions have no exact binary representation, the same way
1/3 has no exact decimal representation. 0.1 is stored as the nearest binary value, which is not exactly one tenth; so is
0.2, and so is 0.3. When you add the stored 0.1 to the stored 0.2 you get the binary sum of two already-rounded values,
and it lands on 0.30000000000000004 -- close to 0.3 but not the same stored value as the literal 0.3. So `0.1 + 0.2 == 0.3`
is False, not because the math is wrong but because == asks whether two binary values are bit-for-bit identical, and these
two are not. Any code that tests a computed float for equality against an expected float -- a loop that stops when an
accumulator `== target`, a test that asserts `result == 0.3`, a check that a balance is `== 0` -- is a latent bug that
fires whenever the computation routes through inexact values.

The errors compound. Add 0.1 to itself ten times and you do not get 1.0; you get 0.9999999999999999, because each
addition carries the tiny representation error and they accumulate. So `sum([0.1] * 10) == 1.0` is also False, and a loop
`while total != 1.0` over 0.1 steps can run forever.

The fix is to never test floats for exact equality. Compare with a tolerance: the result is 'equal' if the two values are
within a small epsilon of each other. The standard library's math.isclose does this correctly, using both a relative and
an absolute tolerance so it works across magnitudes. With it, 0.1 + 0.2 is close to 0.3 and the accumulated sum is close
to 1.0, as intended. (When you need exact decimal arithmetic -- money, especially -- use a decimal type or integer cents
instead of floats at all; but for ordinary float results, tolerance comparison is the rule.)

Not every sum is inexact: values that ARE exact in binary compare equal. 0.5 and 0.25 are 1/2 and 1/4, exact sums of
powers of two, so 0.5 + 0.25 == 0.75 is True. That is the trap's disguise -- equality sometimes works, on the dyadic
values people reach for in examples, which is exactly why the bug survives testing and surfaces on real data.

  --equality    0.1 + 0.2 vs 0.3: == is False, the stored value is 0.30000000000000004, math.isclose is True
  --accumulate  0.1 added 10 times vs 1.0: == is False (0.9999999999999999), isclose is True; and 0.5 + 0.25 == 0.75 IS True
  --check       == fails on inexact sums but isclose passes; dyadic (power-of-two) sums are exact under ==

The operands are the fixture; every sum, stored value, and comparison is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "floateq.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def approx_equal(x, y, tol=1e-9):
    """The correct float comparison: within a tolerance, not bit-for-bit -- wraps math.isclose."""
    return math.isclose(x, y, rel_tol=tol, abs_tol=tol)


def accumulate(value, times):
    """Add `value` to a running total `times` times -- the tiny per-add error compounds."""
    total = 0.0
    for _ in range(times):
        total += value
    return total


# ----------------------------------------------------------------- printing

def equality_view(data):
    a, b, exp = data["a"], data["b"], data["expected"]
    s = a + b
    print("EQUALITY — %s + %s vs %s" % (a, b, exp))
    print("-" * 56)
    print("  %s + %s          = %r" % (a, b, s))
    print("  (%s + %s) == %s   = %s   <- False: the stored values differ" % (a, b, exp, s == exp))
    print("  math.isclose(...)      = %s   <- True: within tolerance" % math.isclose(s, exp))
    print("-" * 56)
    print("  the exact-decimal answer is %s, but the binary sum is %r." % (exp, s))


def accumulate_view(data):
    v, n, target = data["accumulate_value"], data["accumulate_times"], data["accumulate_target"]
    s = accumulate(v, n)
    da, db, dexp = data["dyadic_a"], data["dyadic_b"], data["dyadic_expected"]
    ds = da + db
    print("ACCUMULATE — errors compound, but power-of-two values stay exact")
    print("-" * 60)
    print("  %s added %d times = %r" % (v, n, s))
    print("  (...) == %s        = %s   (isclose = %s)" % (target, s == target, math.isclose(s, target)))
    print("  %s + %s == %s      = %s   <- exact: dyadic values fit binary" % (da, db, dexp, ds == dexp))
    print("-" * 60)
    print("  == is unreliable for computed floats but happens to work on dyadic values -- the trap's disguise.")


def check(data):
    print("SELF-TEST — == fails on inexact sums but isclose passes; dyadic (power-of-two) sums are exact under ==")
    print("-" * 112)
    a, b, exp = data["a"], data["b"], data["expected"]
    s = a + b

    naive_equal_false = (s == exp) is False
    print("  (%s + %s) == %s is False = %s (%r)" % (a, b, exp, naive_equal_false, s))

    stored_value_off = repr(s) != repr(exp)
    print("  the stored sum differs from the literal %s = %s (%r)" % (exp, stored_value_off, s))

    isclose_true = approx_equal(s, exp)
    print("  math.isclose treats them as equal = %s" % isclose_true)

    v, n, target = data["accumulate_value"], data["accumulate_times"], data["accumulate_target"]
    acc = accumulate(v, n)
    accumulate_off = acc != target and approx_equal(acc, target)
    print("  %s x %d != %s under == but isclose = %s (%r)" % (v, n, target, accumulate_off, acc))

    da, db, dexp = data["dyadic_a"], data["dyadic_b"], data["dyadic_expected"]
    dyadic_exact = (da + db) == dexp
    print("  power-of-two sum %s + %s == %s is exact = %s" % (da, db, dexp, dyadic_exact))

    ok = naive_equal_false and stored_value_off and isclose_true and accumulate_off and dyadic_exact
    print("-" * 112)
    print("SELF-TEST %s  naive_equal_false=%s  stored_value_off=%s  isclose_true=%s  accumulate_off=%s  dyadic_exact=%s"
          % ("PASS" if ok else "FAIL", naive_equal_false, stored_value_off, isclose_true, accumulate_off, dyadic_exact))
    return ok


def main():
    p = argparse.ArgumentParser(description="Floating-point equality: most decimals have no exact binary representation, so 0.1 + 0.2 is 0.30000000000000004 and == against 0.3 is False, and accumulated float errors compound; compare computed floats with a tolerance (math.isclose) instead of ==, and use decimals or integers when you need exact arithmetic.")
    p.add_argument("--equality", action="store_true")
    p.add_argument("--accumulate", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("a=%s b=%s expected=%s  file=%s  (the operands are a fixture; the bug is binary representation)"
          % (data["a"], data["b"], data["expected"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.equality:
        equality_view(data)
    elif args.accumulate:
        accumulate_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
