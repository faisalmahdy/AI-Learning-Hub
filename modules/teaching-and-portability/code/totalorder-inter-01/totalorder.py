"""Sort by a consistent total order, or the result is not even well-defined -- a 'within tolerance' comparator is non-transitive, so the same values sort into different orders depending on how they were arranged going in.

A sort takes a comparison and arranges elements so it holds between every pair. That only produces a unique answer if the comparison is a total order: consistent and, crucially, transitive -- if a is not-after b and b is not-after c, then a must be not-after c. When that holds, there is exactly one sorted arrangement, and every sort algorithm on every machine finds it.

A common, reasonable-looking comparator breaks transitivity. 'Treat two values as equal if they are within a tolerance, otherwise order them by value' -- cmp(a,b) = 0 when abs(a-b) <= eps, else sign(a-b) -- defines an 'equal' relation that is not transitive. With eps=10, the comparator calls 0 and 6 equal and 6 and 12 equal, but 0 and 12 are 12 apart, so it calls them unequal. Equality that chains along a sequence but fails across its span is not equality, and a sort built on it has no consistent target.

Without a consistent target, the order the sort lands on depends on the input arrangement. The same multiset, arranged ascending, sorts to ascending; arranged descending, it sorts to descending -- and both are 'sorted' in the only sense the comparator can check, that every adjacent pair is within tolerance. The result is non-reproducible: run it on data that arrived in a different order and you get a different answer, which for a golden-file test, a cache key, or a cross-language port is a silent bug. (Java's TimSort is strict enough to detect the inconsistency and throw 'Comparison method violates its general contract' rather than return a garbage order.)

The fix is a comparator that is a genuine total order -- compare the exact values, breaking ties by an exact key -- so the same multiset sorts to the same sequence no matter how it was arranged. On this fixture the tolerance comparator sorts one arrangement to ascending and its reverse to descending; the total-order comparator sorts both to the one true order. This computes both.

  --tolerance  the within-tolerance comparator: the two arrangements sort to opposite orders, both locally 'ordered'
  --total      the exact-value comparator: both arrangements sort to the same, truly ordered sequence
  --check      the tolerance comparator is non-transitive and its sort depends on input order, while the total order is reproducible

eps and the two arrangements are the fixture; each comparator's output on each arrangement is computed. Stdlib only.
"""
import argparse
import json
import sys
from functools import cmp_to_key
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "totalorder.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def tolerance_cmp(a, b, eps):
    """BUG: equal within a tolerance, else ordered by value -- 'equal' is not transitive, so this is not a total order."""
    return 0 if abs(a - b) <= eps else (-1 if a < b else 1)


def sort_tolerance(seq, eps):
    """Sort with the tolerance comparator -- the result depends on the input arrangement."""
    return sorted(seq, key=cmp_to_key(lambda a, b: tolerance_cmp(a, b, eps)))


def sort_total(seq):
    """Sort with a genuine total order (exact value), reproducible from any input arrangement."""
    return sorted(seq)


def locally_ordered(seq, eps):
    """Whether every adjacent pair is non-decreasing under the tolerance comparator -- all the comparator can check."""
    return all(tolerance_cmp(seq[i], seq[i + 1], eps) <= 0 for i in range(len(seq) - 1))


# ----------------------------------------------------------------- printing

def tolerance_view(data):
    eps, a, b = data["eps"], data["arrangement_a"], data["arrangement_b"]
    ra, rb = sort_tolerance(a, eps), sort_tolerance(b, eps)
    print("TOLERANCE — sort with the within-tolerance comparator (eps=%d)" % eps)
    print("-" * 64)
    print("  arrangement A %s -> %s   (adjacent pairs within tol: %s)" % (a, ra, locally_ordered(ra, eps)))
    print("  arrangement B %s -> %s   (adjacent pairs within tol: %s)" % (b, rb, locally_ordered(rb, eps)))
    print("  same multiset, two arrangements, same output? %s" % (ra == rb))
    print("-" * 64)
    print("  both are 'sorted' by the comparator, yet they are reverses -- the answer depends on input order")


def total_view(data):
    a, b = data["arrangement_a"], data["arrangement_b"]
    ra, rb = sort_total(a), sort_total(b)
    print("TOTAL — sort with the exact-value comparator (a genuine total order)")
    print("-" * 64)
    print("  arrangement A %s -> %s" % (a, ra))
    print("  arrangement B %s -> %s" % (b, rb))
    print("  same multiset, two arrangements, same output? %s" % (ra == rb))
    print("-" * 64)
    print("  one consistent target, so both arrangements land on the identical sequence")


def check(data):
    print("SELF-TEST — the tolerance comparator is non-transitive and its sort depends on input order, while the total order is reproducible")
    print("-" * 112)
    eps, a, b = data["eps"], data["arrangement_a"], data["arrangement_b"]
    lo = min(a)
    mid = sorted(a)[len(a) // 2]
    hi = max(a)

    equal_non_transitive = (tolerance_cmp(lo, sorted(a)[1], eps) == 0
                            and tolerance_cmp(sorted(a)[1], sorted(a)[2], eps) == 0
                            and tolerance_cmp(lo, sorted(a)[2], eps) != 0)
    print("  'equal within tol' is not transitive = %s (%d~%d, %d~%d, but %d vs %d differ)"
          % (equal_non_transitive, lo, sorted(a)[1], sorted(a)[1], sorted(a)[2], lo, sorted(a)[2]))

    ta, tb = sort_tolerance(a, eps), sort_tolerance(b, eps)
    tolerance_order_depends_on_input = ta != tb
    print("  the tolerance sort gives different results for the two arrangements = %s (%s vs %s)" % (tolerance_order_depends_on_input, ta, tb))

    both_locally_ordered = locally_ordered(ta, eps) and locally_ordered(tb, eps)
    print("  yet both outputs pass the comparator's own local order check = %s" % both_locally_ordered)

    total_reproducible = sort_total(a) == sort_total(b)
    print("  the total-order sort gives the same result for both arrangements = %s (%s)" % (total_reproducible, sort_total(a)))

    total_is_true_order = sort_total(a) == sorted(set(a))
    print("  and that result is the one true ascending order = %s" % total_is_true_order)

    ok = (equal_non_transitive and tolerance_order_depends_on_input and both_locally_ordered
          and total_reproducible and total_is_true_order)
    print("-" * 112)
    print("SELF-TEST %s  equal_non_transitive=%s  tolerance_order_depends_on_input=%s  both_locally_ordered=%s  total_reproducible=%s  total_is_true_order=%s"
          % ("PASS" if ok else "FAIL", equal_non_transitive, tolerance_order_depends_on_input, both_locally_ordered,
             total_reproducible, total_is_true_order))
    return ok


def main():
    p = argparse.ArgumentParser(description="Total order: sort by a consistent, transitive comparison, not a 'within tolerance' rule, because a non-transitive comparator gives the sort no consistent target -- the same multiset sorts to different orders depending on its input arrangement, so the result is non-reproducible (and strict runtimes like Java's TimSort throw on it).")
    p.add_argument("--tolerance", action="store_true")
    p.add_argument("--total", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("eps=%d  arrangement_a=%s  arrangement_b=%s  file=%s  (these are a fixture)"
          % (data["eps"], data["arrangement_a"], data["arrangement_b"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.tolerance:
        tolerance_view(data)
    elif args.total:
        total_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
