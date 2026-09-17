"""Compare values with ==, never with `is` -- identity accidentally agrees with equality for small integers and silently disagrees for large ones.

Python has two comparison operators that are easy to confuse because they so often agree: `==` asks whether two things have the same VALUE, and `is` asks whether they are the same OBJECT in memory. For comparing values -- is this number the one I expect, is this the sentinel -- you always want `==`. Reaching for `is` instead is a common slip, and it is dangerous precisely because it usually works: for the small integers, short strings, and None that show up in quick tests, `is` returns the same answer `==` would, so the bug passes every test written with small examples and waits for production data to expose it.

The reason `is` seems to work is an optimization, not a guarantee. CPython pre-creates a single cached object for every small integer -- the range -5 to 256 -- and hands out that same object every time such a value is produced. So two separately-computed small integers of the same value are literally the same object, and `is` returns True, coincidentally matching `==`. Step outside that cached range and the coincidence ends: each large integer is a freshly allocated object, so two separately-computed large integers of the same value are DIFFERENT objects, and `is` returns False even though their values are equal. Same code, same logic, and the answer flips based purely on whether the number happened to fall inside an interpreter cache.

That cache range is an implementation detail. It is -5 to 256 in current CPython, but the boundary has changed across versions, other interpreters cache differently, and constant-folding can intern literals unpredictably. So code that uses `is` to compare values is not just occasionally wrong -- it is wrong in a way that depends on the interpreter, the version, and the exact values, which is the definition of a portability bug. The fix is a single character of discipline: use `==` for value equality, and reserve `is` for the identity checks it is meant for -- comparing against None, or checking whether two references are deliberately the same object.

The rule: compare values with `==`, never with `is`, because `is` tests object identity and only coincidentally matches value equality for cached small integers (and interned literals) -- outside that implementation-defined cache, two equal values are distinct objects and `is` returns False, so `is`-for-equality passes tests on small numbers and fails on large ones.

On this fixture two equal small integers (256, inside the cache) and two equal large integers (257, just outside it) are compared both ways. `==` is True for both pairs; `is` is True for 256 and False for 257 -- the identical comparison, right answer on the small value, wrong on the large. This computes both.

  --pairs    each pair's value, whether `is` (identity) holds, and whether `==` (equality) holds
  --diverge  the pair where `is` and `==` disagree, and why the cache boundary causes it
  --check    `==` is correct for both pairs while `is` flips at the cache boundary -- identity is not a value test

pairs are the fixture; every value, identity result, and equality result is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "isequal.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def build(parts):
    """Build an integer by summing parts at runtime, forcing a separately-computed object (not one interned literal)."""
    total = 0
    for p in parts:
        total += p
    return total


def identity_holds(a, b):
    """Whether a and b are the SAME object (`is`)."""
    return a is b


def equality_holds(a, b):
    """Whether a and b have the same VALUE (`==`)."""
    return a == b


# ----------------------------------------------------------------- printing

def pairs_view(data):
    print("PAIRS — value, identity (`is`), and equality (`==`) for each pair")
    print("-" * 66)
    print("  label                          value   a is b   a == b")
    for pr in data["pairs"]:
        a, b = build(pr["a_parts"]), build(pr["b_parts"])
        print("  %-29s  %-6d  %-7s  %s" % (pr["label"], a, identity_holds(a, b), equality_holds(a, b)))
    print("-" * 66)
    print("  `==` compares value; `is` compares object identity -- they are not the same test")


def diverge_view(data):
    print("DIVERGE — the pair where `is` and `==` disagree")
    print("-" * 60)
    for pr in data["pairs"]:
        a, b = build(pr["a_parts"]), build(pr["b_parts"])
        if identity_holds(a, b) != equality_holds(a, b):
            print("  %s: value %d" % (pr["label"], a))
            print("    a is b  = %s (different objects -- %d is outside the small-int cache)" % (identity_holds(a, b), a))
            print("    a == b  = %s (equal values)" % equality_holds(a, b))
            print("    -> `is` says NOT equal, `==` says equal; `==` is the correct value test")
            return
    print("  (no divergence found)")


def check(data):
    print("SELF-TEST — `==` is correct for both pairs while `is` flips at the cache boundary -- identity is not a value test")
    print("-" * 120)
    small = data["pairs"][0]
    large = data["pairs"][1]
    sa, sb = build(small["a_parts"]), build(small["b_parts"])
    la, lb = build(large["a_parts"]), build(large["b_parts"])

    both_pairs_value_equal = equality_holds(sa, sb) and equality_holds(la, lb)
    print("  both pairs are value-equal (`==` True) = %s (%d==%d, %d==%d)" % (both_pairs_value_equal, sa, sb, la, lb))

    small_in_cache = sa <= 256
    is_agrees_small = identity_holds(sa, sb)
    print("  for the small value (%d, cached) `is` accidentally agrees = %s" % (sa, is_agrees_small and small_in_cache))

    large_out_of_cache = la > 256
    is_fails_large = not identity_holds(la, lb)
    print("  for the large value (%d, uncached) `is` returns False though `==` is True = %s" % (la, is_fails_large and large_out_of_cache))

    is_disagrees_with_eq = identity_holds(la, lb) != equality_holds(la, lb)
    print("  `is` and `==` disagree on the large pair = %s (is=%s, ==%s)" % (is_disagrees_with_eq, identity_holds(la, lb), equality_holds(la, lb)))

    eq_never_wrong = equality_holds(sa, sb) and equality_holds(la, lb)
    print("  `==` gives the correct answer on every pair = %s" % eq_never_wrong)

    is_unreliable = identity_holds(sa, sb) != identity_holds(la, lb)
    print("  `is` gives different answers for the same value-equality question = %s (small %s, large %s)"
          % (is_unreliable, identity_holds(sa, sb), identity_holds(la, lb)))

    ok = (both_pairs_value_equal and (is_agrees_small and small_in_cache) and (is_fails_large and large_out_of_cache)
          and is_disagrees_with_eq and eq_never_wrong and is_unreliable)
    print("-" * 120)
    print("SELF-TEST %s  both_pairs_value_equal=%s  is_agrees_small=%s  is_fails_large=%s  is_disagrees_with_eq=%s  eq_never_wrong=%s  is_unreliable=%s"
          % ("PASS" if ok else "FAIL", both_pairs_value_equal, is_agrees_small and small_in_cache, is_fails_large and large_out_of_cache, is_disagrees_with_eq, eq_never_wrong, is_unreliable))
    return ok


def main():
    p = argparse.ArgumentParser(description="Identity vs equality: compare values with `==`, never with `is`, because `is` tests object identity and only coincidentally matches value equality for cached small integers (and interned literals) -- outside that implementation-defined cache, two equal values are distinct objects and `is` returns False, so `is`-for-equality passes tests on small numbers and fails on large ones.")
    p.add_argument("--pairs", action="store_true")
    p.add_argument("--diverge", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("pairs=%d  file=%s  (the integer pairs, built from parts at runtime, are a fixture)"
          % (len(data["pairs"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.pairs:
        pairs_view(data)
    elif args.diverge:
        diverge_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
