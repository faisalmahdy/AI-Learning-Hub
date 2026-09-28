---
id: totalorder-inter-01
title: Sort by a consistent total order — a "within tolerance" comparator is non-transitive, so the same values sort into different orders depending on the input
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: A sort takes a comparison and arranges elements so it holds between every pair, and that produces a unique answer only if the comparison is a total order — consistent and, crucially, transitive. A common, reasonable-looking comparator breaks transitivity: "treat two values as equal if they are within a tolerance, otherwise order them by value," cmp(a,b) = 0 when abs(a−b) ≤ eps else sign(a−b). The "equal" relation it defines chains but does not span. With eps = 10 the comparator calls 0 and 6 equal and 6 and 12 equal, yet 0 and 12 are 12 apart and it calls them unequal — equality that is not transitive is not equality, and a sort built on it has no consistent target. Without a consistent target the order the sort lands on depends on the input arrangement: on the fixture the multiset {0, 6, 12, 18, 24} arranged ascending sorts to [0, 6, 12, 18, 24] and the same multiset arranged descending sorts to [24, 18, 12, 6, 0] — opposite orders, both "sorted" in the only sense the comparator can check, that every adjacent pair is within tolerance. The result is non-reproducible, which for a golden-file test, a cache key, or a cross-language port is a silent bug (and Java's TimSort is strict enough to throw "Comparison method violates its general contract" rather than return a garbage order). The fix is a comparator that is a genuine total order — compare exact values, breaking ties by an exact key — which sorts the same multiset to the same sequence from any arrangement. The rule: a sort comparator must define a transitive, consistent total order, or its output is arrangement-dependent and not reproducible.
eli5: Imagine ranking people by height, but you decide "if two people are within a few centimeters, call them the same height." That sounds fine until you line up a row where each person is just a little taller than the one before: everyone is "the same height" as their neighbor, but the person at one end is clearly much taller than the person at the other end. Now "sort them by height" has no single right answer — you could put them shortest-to-tallest or tallest-to-shortest and every neighbor still looks "the same," so which way they end up just depends on how they happened to be standing when you started. The fix is to compare exact heights so there's one true order, and everyone lands the same way every time.
---

## Why this module

Custom sort comparators are everywhere — sort files by a version-aware rule, sort records by a computed score, sort points by nearness. It is easy to write one that looks sensible and passes your tests, and easy for it to hide a defect that only shows up as a result that changes for no reason, or a crash on another platform.

The defect is a comparator that is not a total order. A sort assumes its comparison behaves like a real ordering: transitive, so that if a comes before b and b before c then a comes before c, and consistent, giving the same answer every time. When the comparator violates that, the sort has no well-defined answer to find, so what it returns depends on incidental things — the input order, the sort algorithm, the language.

This module builds the most common offender: "equal if within a tolerance." It sorts one arrangement of five values to ascending order and the reverse arrangement to descending order — the same numbers, opposite results, each of which the comparator itself calls correctly sorted. Then it shows the broken transitivity that causes it and the exact-value comparator that fixes it.

**A sort is only as well-defined as its comparator's ordering, and a comparator that is not transitive gives the sort a question with more than one right answer — so which answer you get is not reproducible.**

## Concepts

A total order is a comparison with three properties that together pin down a unique sorted sequence: it is total (any two elements are comparable), antisymmetric (they cannot each come strictly before the other), and transitive (order chains — a before b and b before c forces a before c). Transitivity is the one that quietly fails, and it is the one that makes "sorted" mean something: it is what lets a local rule about adjacent pairs add up to a global order of the whole list.

The tolerance comparator has a non-transitive notion of equality. It calls two values equal when they are within eps, and that relation chains without spanning: each value can be within eps of the next while the two ends are far apart. With eps = 10 and the values 0, 6, 12, the comparator says 0 equals 6 and 6 equals 12, but 0 and 12 differ by 12 and it orders them. Three elements, and the comparator holds two incompatible opinions: 0 and 12 are equal-by-chain and unequal-by-comparison.

The figure shows the chain. Each dot is within tolerance of its neighbor, so the comparator draws an equality link between them, but the span from the first dot to the last is far wider than the tolerance, so no single "these are all equal" or "these are all ordered" is true.

<svg role="img" aria-label="Five dots at 0, 6, 12, 18, 24 on a line. Arcs link each dot to its neighbor labeled within-tolerance-equal because each gap is 6, under the tolerance of 10. A wide bracket spans from 0 to 24 labeled 24 apart, not equal, showing the equality chains locally but fails across the span" viewBox="0 0 640 200">
<line x1="60" y1="120" x2="580" y2="120" stroke="var(--line)" stroke-width="1"/>
<circle cx="80" cy="120" r="6" fill="var(--ink)"/>
<text x="80" y="140" fill="var(--muted)" font-size="11" text-anchor="middle">0</text>
<circle cx="200" cy="120" r="6" fill="var(--ink)"/>
<text x="200" y="140" fill="var(--muted)" font-size="11" text-anchor="middle">6</text>
<circle cx="320" cy="120" r="6" fill="var(--ink)"/>
<text x="320" y="140" fill="var(--muted)" font-size="11" text-anchor="middle">12</text>
<circle cx="440" cy="120" r="6" fill="var(--ink)"/>
<text x="440" y="140" fill="var(--muted)" font-size="11" text-anchor="middle">18</text>
<circle cx="560" cy="120" r="6" fill="var(--ink)"/>
<text x="560" y="140" fill="var(--muted)" font-size="11" text-anchor="middle">24</text>
<path d="M 80 114 q 60 -26 120 0" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
<path d="M 200 114 q 60 -26 120 0" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
<path d="M 320 114 q 60 -26 120 0" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
<path d="M 440 114 q 60 -26 120 0" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
<text x="320" y="80" fill="var(--s1)" font-size="10" text-anchor="middle">each gap 6 ≤ 10: "equal"</text>
<path d="M 80 165 L 560 165" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
<text x="320" y="185" fill="var(--s2)" font-size="10" text-anchor="middle">span 24 &gt; 10: not equal</text>
</svg>
^ The tolerance comparator links each dot to its neighbor as equal, but the span across the whole chain is far wider than the tolerance — so "equal" is not transitive.

**Transitivity is what turns pairwise comparisons into a global order, so a comparator that lacks it does not describe an order at all, only a set of local opinions that need not agree.**

## Worked example

The fixture is one multiset of five values in two arrangements — ascending and descending — plus the tolerance.

```json filename=modules/teaching-and-portability/code/totalorder-inter-01/totalorder.json:3-5 COMPLETE
  "eps": 10,
  "arrangement_a": [0, 6, 12, 18, 24],
  "arrangement_b": [24, 18, 12, 6, 0]
```

The buggy comparator is equal-within-tolerance, else ordered by value.

```python filename=modules/teaching-and-portability/code/totalorder-inter-01/totalorder.py:31-33 COMPLETE
def tolerance_cmp(a, b, eps):
    """BUG: equal within a tolerance, else ordered by value -- 'equal' is not transitive, so this is not a total order."""
    return 0 if abs(a - b) <= eps else (-1 if a < b else 1)
```

Sorting with it depends on the input arrangement.

```python filename=modules/teaching-and-portability/code/totalorder-inter-01/totalorder.py:36-38 COMPLETE
def sort_tolerance(seq, eps):
    """Sort with the tolerance comparator -- the result depends on the input arrangement."""
    return sorted(seq, key=cmp_to_key(lambda a, b: tolerance_cmp(a, b, eps)))
```

The only thing the comparator can actually verify about a result is that adjacent pairs are in order.

```python filename=modules/teaching-and-portability/code/totalorder-inter-01/totalorder.py:46-48 COMPLETE
def locally_ordered(seq, eps):
    """Whether every adjacent pair is non-decreasing under the tolerance comparator -- all the comparator can check."""
    return all(tolerance_cmp(seq[i], seq[i + 1], eps) <= 0 for i in range(len(seq) - 1))
```

Running the tolerance sort on both arrangements produces opposite orders — each of which passes the local check.

```text filename=totalorder.py --tolerance
TOLERANCE — sort with the within-tolerance comparator (eps=10)
----------------------------------------------------------------
  arrangement A [0, 6, 12, 18, 24] -> [0, 6, 12, 18, 24]   (adjacent pairs within tol: True)
  arrangement B [24, 18, 12, 6, 0] -> [24, 18, 12, 6, 0]   (adjacent pairs within tol: True)
  same multiset, two arrangements, same output? False
----------------------------------------------------------------
  both are 'sorted' by the comparator, yet they are reverses -- the answer depends on input order
```

The same five numbers come out ascending from one arrangement and descending from the other, and the comparator is content with both, because every adjacent pair is within tolerance in each. There is no fact of the matter about which is "sorted." Swap in the exact-value comparator and the ambiguity is gone.

```text filename=totalorder.py --total
TOTAL — sort with the exact-value comparator (a genuine total order)
----------------------------------------------------------------
  arrangement A [0, 6, 12, 18, 24] -> [0, 6, 12, 18, 24]
  arrangement B [24, 18, 12, 6, 0] -> [0, 6, 12, 18, 24]
  same multiset, two arrangements, same output? True
----------------------------------------------------------------
  one consistent target, so both arrangements land on the identical sequence
```

Both arrangements now land on [0, 6, 12, 18, 24]. The figure puts the two comparators side by side on the two inputs.

<svg role="img" aria-label="Two panels. The tolerance panel shows arrangement A sorting to ascending 0..24 and arrangement B sorting to descending 24..0, marked different. The total panel shows both arrangements sorting to the same ascending 0..24, marked same" viewBox="0 0 640 210">
<text x="160" y="26" fill="var(--ink)" font-size="12" text-anchor="middle">tolerance comparator</text>
<text x="160" y="58" fill="var(--muted)" font-size="10" text-anchor="middle">A [0,6,12,18,24] → 0,6,12,18,24</text>
<text x="160" y="82" fill="var(--muted)" font-size="10" text-anchor="middle">B [24,18,12,6,0] → 24,18,12,6,0</text>
<rect x="60" y="98" width="200" height="30" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="5"/>
<text x="160" y="118" fill="var(--s2)" font-size="11" text-anchor="middle">different outputs (not reproducible)</text>
<text x="480" y="26" fill="var(--ink)" font-size="12" text-anchor="middle">total-order comparator</text>
<text x="480" y="58" fill="var(--muted)" font-size="10" text-anchor="middle">A [0,6,12,18,24] → 0,6,12,18,24</text>
<text x="480" y="82" fill="var(--muted)" font-size="10" text-anchor="middle">B [24,18,12,6,0] → 0,6,12,18,24</text>
<rect x="380" y="98" width="200" height="30" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="5"/>
<text x="480" y="118" fill="var(--s1)" font-size="11" text-anchor="middle">identical output (reproducible)</text>
</svg>
^ The tolerance comparator returns opposite orders for the two arrangements; the total-order comparator returns the one true order for both.

**The tolerance comparator did not sort the data wrong — it sorted it to two different right answers, which is worse, because "right" was never well-defined and the one you observe is an accident of input order.**

## Build

The self-test pins the cause and the effect: the equality is non-transitive, the tolerance sort's output depends on input order, yet both outputs pass the comparator's own local check, while the total order is reproducible.

```python filename=modules/teaching-and-portability/code/totalorder-inter-01/totalorder.py:92-102 COMPLETE
    tolerance_order_depends_on_input = ta != tb
    print("  the tolerance sort gives different results for the two arrangements = %s (%s vs %s)" % (tolerance_order_depends_on_input, ta, tb))

    both_locally_ordered = locally_ordered(ta, eps) and locally_ordered(tb, eps)
    print("  yet both outputs pass the comparator's own local order check = %s" % both_locally_ordered)

    total_reproducible = sort_total(a) == sort_total(b)
    print("  the total-order sort gives the same result for both arrangements = %s (%s)" % (total_reproducible, sort_total(a)))

    total_is_true_order = sort_total(a) == sorted(set(a))
    print("  and that result is the one true ascending order = %s" % total_is_true_order)
```

Running the check confirms all five flags.

```text filename=totalorder.py --check
SELF-TEST — the tolerance comparator is non-transitive and its sort depends on input order, while the total order is reproducible
----------------------------------------------------------------------------------------------------------------
  'equal within tol' is not transitive = True (0~6, 6~12, but 0 vs 12 differ)
  the tolerance sort gives different results for the two arrangements = True ([0, 6, 12, 18, 24] vs [24, 18, 12, 6, 0])
  yet both outputs pass the comparator's own local order check = True
  the total-order sort gives the same result for both arrangements = True ([0, 6, 12, 18, 24])
  and that result is the one true ascending order = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  equal_non_transitive=True  tolerance_order_depends_on_input=True  both_locally_ordered=True  total_reproducible=True  total_is_true_order=True
```

**"Both outputs pass the local check" is the diagnosis: the comparator can only see adjacent pairs, and a non-transitive comparator lets a globally-wrong order look locally-perfect, which is exactly why the bug is invisible to the comparator that caused it.**

## Definition of done

You are done when every sort comparator you write defines a genuine total order — total, consistent, and transitive — so the sorted result is unique and reproducible regardless of input arrangement, algorithm, or platform.

The reliable way to get there is to sort by a key rather than a hand-rolled comparison: map each element to a value (a number, a string, or a tuple of exact fields) and let the language order those, because the built-in order on numbers and tuples is already a total order. When you do need "close values should group," do the grouping as an explicit, deterministic step — round or bucket each value to a canonical representative first, then sort the buckets — so the grouping is transitive by construction (equal buckets are truly equal) instead of a non-transitive tolerance. And when a comparator ties, break the tie with an exact secondary key rather than leaving it to the sort's stability, so the order does not depend on the input arrangement or on whether this language's sort happens to be stable.

<svg role="img" aria-label="A decision. If you need close values grouped, bucket each value to a canonical representative first, then sort, which is transitive. Otherwise sort by an exact key or tuple. Both lead to a unique reproducible order" viewBox="0 0 640 200">
<text x="320" y="28" fill="var(--muted)" font-size="12" text-anchor="middle">need "close values grouped"?</text>
<text x="165" y="66" fill="var(--ink)" font-size="11" text-anchor="middle">yes</text>
<rect x="55" y="78" width="230" height="52" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="170" y="100" fill="var(--ink)" font-size="10" text-anchor="middle">bucket to a canonical value first,</text>
<text x="170" y="116" fill="var(--muted)" font-size="10" text-anchor="middle">then sort — equal buckets truly equal</text>
<text x="475" y="66" fill="var(--ink)" font-size="11" text-anchor="middle">no</text>
<rect x="360" y="78" width="230" height="52" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="475" y="100" fill="var(--ink)" font-size="10" text-anchor="middle">sort by an exact key or tuple</text>
<text x="475" y="116" fill="var(--muted)" font-size="10" text-anchor="middle">(break ties with an exact field)</text>
<line x1="170" y1="130" x2="320" y2="165" stroke="var(--line)" stroke-width="1"/>
<line x1="475" y1="130" x2="320" y2="165" stroke="var(--line)" stroke-width="1"/>
<rect x="220" y="165" width="200" height="28" fill="var(--panel)" stroke="var(--ink)" stroke-width="1.5" rx="6"/>
<text x="320" y="184" fill="var(--ink)" font-size="10" text-anchor="middle">unique, reproducible order</text>
</svg>
^ Both branches produce a transitive total order — grouping happens before the sort, never inside a non-transitive comparison.

**"Close values are equal" is a clustering operation, not an ordering one, and doing it inside the comparator smuggles a non-transitive relation into a place that requires a total order — so bucket first, then sort.**

## Boss fight

Your turn: shrink the tolerance until the bug disappears, and notice it does not disappear gradually. Set `eps` to 4 and rerun `--tolerance`. Now no two of the values 0, 6, 12, 18, 24 are within tolerance of each other (the smallest gap is 6), so the comparator never returns 0, it always orders by value, and it is a total order again — both arrangements sort to ascending. The comparator is broken only when the tolerance is large enough to make some pair "equal" while a wider pair is not; below that, the same code is correct. This is what makes tolerance comparators so treacherous: whether the bug fires depends on the data's spacing relative to eps, so it can pass every test on well-separated data and fail silently the day the data clusters.

Then take the failure to another runtime. Python's `sorted` with `cmp_to_key` will return one of the inconsistent orders without complaint, so the bug shows up as a wrong-but-quiet result. Java's `Collections.sort` and `Arrays.sort` run TimSort with a contract check that detects the inconsistency mid-sort and throws `IllegalArgumentException: Comparison method violates its general contract`. Same comparator, same defect, but one platform hands you a silent non-reproducible result and the other a loud crash — and the crash is the friendlier outcome, because at least it tells you the comparator was never an order. A comparator that only sometimes crashes, on some inputs, on some platforms, is the signature of a broken total order.

**The tolerance comparator is correct on well-separated data and broken on clustered data, so it survives the tests you write and fails on the inputs you did not imagine — which is why the fix is structural (bucket, then sort) rather than picking a "safe" tolerance.**

## External resources

The Java documentation for `Comparator` and `Comparable` states the contract explicitly — the comparison must be transitive and consistent — and `Arrays.sort` / `Collections.sort` throw when TimSort detects a violation, which is the loud version of this bug.

The C++ standard's requirement that `std::sort`'s comparator be a "strict weak ordering" is the same contract under another name; violating it is undefined behavior, and the cppreference notes on it explain why.

Python's `functools.cmp_to_key` documentation and the general move from `cmp` to `key` functions reflect the same lesson — prefer sorting by a key that is already totally ordered over hand-writing a comparison that might not be.
