"""Deep-copy a nested structure -- a slice or .copy() duplicates only the top level, so the copy's inner objects are still the original's.

You have a nested structure -- a list of lists, a dict of lists, an object holding other objects -- and you want an independent copy so you can modify one without touching the other. You reach for the obvious tools: a slice (list[:]), list(x), x.copy(), dict(d). They all make a copy, and for a flat structure that copy is fully independent. For a NESTED structure they make a SHALLOW copy, which duplicates only the outermost container: the new container is a distinct object, but its elements are not copies -- they are the very same inner objects the original holds. So copy[0] IS original[0], the same list in memory, referenced from two places.

The bug this creates is a spooky-action-at-a-distance: you mutate the copy's inner element, and the original changes too, because there is only one inner element and both containers point at it. You appended to copy[0], but copy[0] and original[0] are the same list, so original[0] grew as well. The code looks correct -- you made a copy and modified the copy -- and the original mutating anyway is baffling until you know that the copy was only skin-deep. It is especially treacherous because the shallow copy IS independent at the top level: you can append a whole new element to the copy and the original is unaffected, so it passes a naive test and fails only when you reach into the nesting, which is what real code does.

The fix is a DEEP copy: copy.deepcopy recursively duplicates every level, so the copy's inner objects are new objects too, and mutating them cannot reach the original. The cost is that deep copying is more work (it walks the entire structure and allocates a duplicate of everything), so you use a shallow copy when you know the structure is flat or you intend to share the inner objects, and a deep copy when you need true independence of a nested structure. The rule of thumb: if you will mutate anything below the top level, shallow is not enough.

The rule: to independently copy a nested structure, use a deep copy (copy.deepcopy) rather than a slice, list(), or .copy(), because those make a shallow copy that duplicates only the top level and shares the inner objects -- so mutating an inner element through the copy also mutates the original.

On this fixture the matrix is [[1, 2], [3, 4]]. A shallow copy shares the row lists (copy[0] is original[0]), so appending 9 to the shallow copy's first row makes the original's first row [1, 2, 9] too; a deep copy's rows are independent, so the same append leaves the original untouched. This computes both.

  --identity   whether the shallow and deep copies share the original's inner objects
  --mutate     the effect on the original of appending to an inner list of the shallow copy vs the deep copy
  --check      the shallow copy shares inner objects and leaks mutations to the original; the deep copy is fully independent

matrix is the fixture; the copies, inner-object identities, and mutation effects are computed. Stdlib only.
"""
import argparse
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "deepcopy.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def fresh_matrix(data):
    """A fresh independent copy of the fixture matrix to experiment on."""
    return [list(row) for row in data["matrix"]]


def shallow_copy(m):
    """A slice / list() / .copy() -- duplicates the top level only."""
    return list(m)


def deep_copy(m):
    """copy.deepcopy -- duplicates every level recursively."""
    return copy.deepcopy(m)


def append_to_inner_and_return_original(m, cp, value):
    """Append value to the copy's first inner list; return the original's first inner list."""
    cp[0].append(value)
    return m[0]


# ----------------------------------------------------------------- printing

def identity_view(data):
    m = fresh_matrix(data)
    s = shallow_copy(m)
    d = deep_copy(m)
    print("IDENTITY — do the copies share the original's inner objects?")
    print("-" * 60)
    print("  outer list is a new object:  shallow %s   deep %s" % (s is not m, d is not m))
    print("  inner row IS the original's: shallow %s   deep %s" % (s[0] is m[0], d[0] is m[0]))
    print("-" * 60)
    print("  a shallow copy duplicates the outer list but shares the inner rows")


def mutate_view(data):
    print("MUTATE — append 9 to the copy's first row; what happens to the original?")
    print("-" * 66)
    m = fresh_matrix(data)
    s = shallow_copy(m)
    print("  shallow: original[0] after copy[0].append(9) = %s" % append_to_inner_and_return_original(m, s, 9))
    m = fresh_matrix(data)
    d = deep_copy(m)
    print("  deep:    original[0] after copy[0].append(9) = %s" % append_to_inner_and_return_original(m, d, 9))
    print("-" * 66)
    print("  the shallow copy's mutation leaked into the original; the deep copy's did not")


def check(data):
    print("SELF-TEST — the shallow copy shares inner objects and leaks mutations to the original; the deep copy is fully independent")
    print("-" * 122)

    m = fresh_matrix(data)
    s = shallow_copy(m)
    d = deep_copy(m)

    shallow_outer_independent = s is not m
    print("  the shallow copy's OUTER list is a distinct object = %s" % shallow_outer_independent)

    shallow_shares_inner = s[0] is m[0]
    print("  the shallow copy shares the original's inner rows = %s (copy[0] is original[0])" % shallow_shares_inner)

    deep_inner_independent = d[0] is not m[0]
    print("  the deep copy's inner rows are new objects = %s" % deep_inner_independent)

    m1 = fresh_matrix(data)
    s1 = shallow_copy(m1)
    orig_after_shallow = append_to_inner_and_return_original(m1, s1, 9)
    shallow_leaks = orig_after_shallow == [1, 2, 9]
    print("  mutating the shallow copy's inner list changed the original = %s (%s)" % (shallow_leaks, orig_after_shallow))

    m2 = fresh_matrix(data)
    d2 = deep_copy(m2)
    orig_after_deep = append_to_inner_and_return_original(m2, d2, 9)
    deep_isolated = orig_after_deep == [1, 2]
    print("  mutating the deep copy's inner list left the original unchanged = %s (%s)" % (deep_isolated, orig_after_deep))

    shallow_top_level_safe = True  # appending a NEW row to the shallow copy does not affect the original
    m3 = fresh_matrix(data)
    s3 = shallow_copy(m3)
    s3.append([5, 6])
    shallow_top_level_safe = len(m3) == 2
    print("  appending a whole new row to the shallow copy is safe (top-level is independent) = %s" % shallow_top_level_safe)

    ok = (shallow_outer_independent and shallow_shares_inner and deep_inner_independent and shallow_leaks
          and deep_isolated and shallow_top_level_safe)
    print("-" * 122)
    print("SELF-TEST %s  shallow_outer_independent=%s  shallow_shares_inner=%s  deep_inner_independent=%s  shallow_leaks=%s  deep_isolated=%s  shallow_top_level_safe=%s"
          % ("PASS" if ok else "FAIL", shallow_outer_independent, shallow_shares_inner, deep_inner_independent, shallow_leaks, deep_isolated, shallow_top_level_safe))
    return ok


def main():
    p = argparse.ArgumentParser(description="Deep vs shallow copy: to independently copy a nested structure, use a deep copy (copy.deepcopy) rather than a slice, list(), or .copy(), because those make a shallow copy that duplicates only the top level and shares the inner objects -- so mutating an inner element through the copy also mutates the original.")
    p.add_argument("--identity", action="store_true")
    p.add_argument("--mutate", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("matrix=%s  file=%s  (the nested matrix is a fixture)" % (data["matrix"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.identity:
        identity_view(data)
    elif args.mutate:
        mutate_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
