---
id: sumorder-inter-01
title: Fix the summation order (or use an exact sum) — or the same numbers total differently and no one reproduces you
topic: teaching-and-portability
level: intermediate
status: ready
time: 17 min
summary: Floating-point addition is not associative. A 64-bit float carries about sixteen significant digits, so adding a small number to a huge one rounds the small one away — 1e16 + 1.0 is exactly 1e16, the 1.0 lost. That makes the order of additions change the answer: add 1.0 to 1e16 first and it vanishes, then subtracting 1e16 leaves 0.0; cancel the two big values first and they make 0.0, then adding 1.0 leaves 1.0. Same three numbers, two orders, two totals — and only one is the true sum of 1.0. This is a reproducibility trap: you document a total, a reader reruns and gets different last digits (or, as here, a wildly different answer) because their loop, their optimized math library, or their BLAS summed in another order. The fix is to remove the order dependence — a fixed specified order, or an order-independent exact sum like math.fsum, which returns 1.0 either way.
eli5: If you pour a teaspoon of water into a full swimming pool and then scoop out exactly a pool's worth, the teaspoon is gone — the pool was too big to notice it. But if you cancel the pool against itself first, the teaspoon is still sitting there. Adding numbers on a computer works the same way: a tiny number next to a giant one can vanish, so the order you add things in changes the total. To get an answer everyone agrees on, add them in a fixed way, or use a method built to never lose the teaspoon.
---

## Why this module

A total you print to full precision looks like a fact, but if it came from adding floats in a particular order, a reader who adds them in another order gets a different number — and neither of you did anything wrong.

Floating-point numbers have finite precision: a 64-bit float holds about sixteen significant digits. When you add a small number to a much larger one, the small one's digits fall past the sixteenth and are rounded off entirely — `1e16 + 1.0` evaluates to exactly `1e16`, as if the `1.0` were never there. This makes addition non-associative: the grouping changes the result. Summing `1.0, 1e16, -1e16` left to right adds the `1.0` into `1e16` (losing it), then subtracts `1e16` to reach `0.0`. Summing the same three right to left cancels the two big values into `0.0` first, then adds the `1.0` to reach `1.0`. Same numbers, same operations, different association, different answer — and only one is the true sum.

**Floating-point addition is not associative, so the same values summed in different orders can give different totals — and a documented total that depends on order is not reproducible.**

This is a portability and reproducibility problem, not a numerical footnote. You run an analysis, it prints a total, you write that total into a report to full precision. A reader reruns the code and gets different trailing digits — or a completely different answer — because their loop summed in another order, or their optimized math library reordered the additions across SIMD lanes or threads, or they linked a different BLAS. Everyone's arithmetic is "correct"; they merely associated it differently. The fix is to remove the order dependence: sum in a fixed, specified order, or use an order-independent exact summation like `math.fsum` or Kahan compensation. This module sums the same values two ways, watches them disagree, and shows the exact sum agree with itself.

## Concepts

**Finite precision** means a float keeps only about sixteen significant digits, so a small addend next to a large accumulator is rounded away — `1e16 + 1.0 == 1e16`.

**Non-associativity** is the consequence: `(a + b) + c` need not equal `a + (b + c)`, so the order in which you add a list changes its total.

**Order dependence** makes a naive sum non-reproducible. Left-to-right, right-to-left, or a library's reordered/parallel sum can each give a different last few digits — or, with cancellation, a different answer entirely.

**An exact or order-independent sum** removes the dependence. `math.fsum` tracks the partial sums exactly and returns the correctly rounded total regardless of order; Kahan summation compensates for the lost low-order bits. Either gives every reader the same number.

**This is a documented-output problem.** Like seeding an RNG or pinning a dependency version, specifying the summation (a fixed order or an exact method) is what lets a stranger reproduce the total you printed.

```python filename=modules/teaching-and-portability/code/sumorder-inter-01/sumorder.py:42-48 COMPLETE
def running_sum(values):
    """Add left to right, returning the running total after each step."""
    total, steps = 0.0, []
    for x in values:
        total = total + x
        steps.append(total)
    return steps
```

**A floating-point total is only reproducible if its summation order is fixed or its method is order-independent, because non-associativity lets the same values add up to different numbers.**

<svg role="img" aria-label="A float holds about 16 digits; adding 1.0 to 1e16 needs 17 digits, so the 1 falls off the end and is lost" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">~16 significant digits fit in a 64-bit float</text>
  <rect x="30" y="24" width="200" height="18" fill="none" stroke="var(--grid)" stroke-width="1"/>
  <text x="34" y="37" fill="var(--ink)" font-size="9" font-family="monospace">10000000000000000</text>
  <text x="236" y="37" fill="var(--s2)" font-size="9" font-family="monospace">.1</text>
  <line x1="232" y1="20" x2="232" y2="46" stroke="var(--s2)" stroke-width="1"/>
  <text x="236" y="56" fill="var(--s2)" font-size="7">the 1 is past digit 16</text>
  <text x="30" y="76" fill="var(--muted)" font-size="8">1e16 + 1.0 would need 17 digits, so the 1 is rounded away → result is exactly 1e16</text>
  <text x="30" y="92" fill="var(--muted)" font-size="8">the small addend vanishes next to the large accumulator</text>
</svg>
^ Representing 1e16 already uses all sixteen digits, so the extra 1.0 would land in a seventeenth place that does not exist — it is rounded off and the sum is exactly 1e16, the 1.0 gone.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/sumorder-inter-01/sumorder.py

The fixture is three values whose exact sum is 1.0, spanning enormous magnitudes.

```json filename=modules/teaching-and-portability/code/sumorder-inter-01/sumorder.json:1-5 COMPLETE
{
  "_meta": "Three floating-point values whose exact sum is 1.0. They span huge magnitudes: a large positive, its large negative, and a small 1.0. Floating-point addition is NOT associative: a 64-bit float has ~16 significant digits, so adding 1.0 to 1e16 rounds the 1.0 completely away (1e16 + 1.0 == 1e16), but adding the two big values first cancels them to 0.0 and then the 1.0 survives. So the SAME three numbers summed in different orders give different totals. A documented result that prints one order's total is not reproducible by a reader who sums in another order — or whose optimized/parallel library reorders the additions. true_sum is the mathematically exact total.",
  "values": [1.0, 1e16, -1e16],
  "true_sum": 1.0
}
```

Two naive orders and one exact method; the exact one is order-independent by construction.

```python filename=modules/teaching-and-portability/code/sumorder-inter-01/sumorder.py:51-61 COMPLETE
def left_to_right(values):
    return running_sum(values)[-1] if values else 0.0


def right_to_left(values):
    return running_sum(list(reversed(values)))[-1] if values else 0.0


def exact(values):
    """math.fsum tracks partial sums exactly, so the result does not depend on order."""
    return math.fsum(values)
```

Run `--orders` to watch the running total each way.

```text filename=--orders
ORDERS — the running total, left-to-right vs right-to-left
------------------------------------------------------------
  left to right:  ['1', '1e+16', '0']  ->  0
  right to left:  ['-1e+16', '0', '1']  ->  1
------------------------------------------------------------
  adding 1.0 to 1e16 loses it; cancelling the big values first keeps it.
```

Follow the left-to-right steps: start at 1, add 1e16 to get 1e16 — the 1 is gone, rounded off the end — then add -1e16 to get 0. The true 1.0 was destroyed at step two and can never come back. Right to left: start at -1e16, add 1e16 to get exactly 0, then add 1.0 to get 1.0. The two big values cancelled cleanly before the small one was ever exposed to them, so it survived. The entire difference between the two answers is whether the 1.0 met the 1e16 before or after the cancellation.

<svg role="img" aria-label="Left to right the running total goes 1, 1e16, 0 losing the one; right to left it goes -1e16, 0, 1 keeping the one" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">running total after each addition</text>
  <text x="8" y="34" fill="var(--s2)" font-size="8">left→right</text>
  <rect x="70" y="26" width="30" height="14" fill="var(--s2)"/><text x="76" y="37" fill="var(--panel)" font-size="7">1</text>
  <text x="104" y="37" fill="var(--muted)" font-size="9">→</text><rect x="116" y="26" width="45" height="14" fill="var(--s2)"/><text x="120" y="37" fill="var(--panel)" font-size="7">1e16</text>
  <text x="165" y="37" fill="var(--muted)" font-size="9">→</text><rect x="177" y="26" width="30" height="14" fill="var(--grid)"/><text x="185" y="37" fill="var(--muted)" font-size="7">0</text>
  <text x="212" y="37" fill="var(--s2)" font-size="7">1 lost</text>
  <text x="8" y="72" fill="var(--s1)" font-size="8">right→left</text>
  <rect x="70" y="64" width="45" height="14" fill="var(--s1)"/><text x="74" y="75" fill="var(--panel)" font-size="7">-1e16</text>
  <text x="119" y="75" fill="var(--muted)" font-size="9">→</text><rect x="131" y="64" width="30" height="14" fill="var(--grid)"/><text x="139" y="75" fill="var(--muted)" font-size="7">0</text>
  <text x="165" y="75" fill="var(--muted)" font-size="9">→</text><rect x="177" y="64" width="30" height="14" fill="var(--s1)"/><text x="185" y="75" fill="var(--panel)" font-size="7">1</text>
  <text x="212" y="75" fill="var(--s1)" font-size="7">1 kept</text>
  <text x="30" y="98" fill="var(--muted)" font-size="8">whether the 1 meets the 1e16 before or after cancellation decides the answer</text>
</svg>
^ Left to right the 1 is absorbed into 1e16 at step two and the total ends at 0; right to left the big values cancel first, so the 1 survives to the end.

## Build

Which do you trust, and how do you make it reproducible? Run `--fix`.

```text filename=--fix
FIX — naive orders vs an order-independent exact sum
------------------------------------------------------------
  left to right:   0   (naive, order-dependent)
  right to left:   1   (naive, order-dependent)
  math.fsum:       1   (exact, order-independent)
  true sum:        1
```

The two naive sums give 0 and 1 — you cannot tell from either which is right without knowing the exact answer, and a reader has no way to know which order you used. `math.fsum` gives 1 regardless of order, matching the true sum, because it keeps the partial sums exactly and rounds only at the end. That order-independence is the property you need for a reproducible total: it does not matter whether the reader's loop, library, or hardware reorders the additions, because the answer does not depend on order at all. When you cannot use an exact sum, the fallback is to specify the order explicitly — sort the values, or document "summed in file order" — so at least everyone sums the same way.

<svg role="img" aria-label="Left to right gives 0, right to left gives 1, math.fsum gives 1 matching the true sum" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">computed total (true sum = 1)</text>
  <line x1="90" y1="20" x2="90" y2="84" stroke="var(--grid)" stroke-width="1"/>
  <line x1="230" y1="20" x2="230" y2="84" stroke="var(--s1)" stroke-width="1" stroke-dasharray="3 3"/><text x="212" y="18" fill="var(--muted)" font-size="7">true 1</text>
  <text x="8" y="34" fill="var(--muted)" font-size="8">L→R</text><rect x="90" y="26" width="2" height="12" fill="var(--s2)"/><text x="96" y="36" fill="var(--muted)" font-size="8">0 (value lost)</text>
  <text x="8" y="52" fill="var(--muted)" font-size="8">R→L</text><rect x="90" y="44" width="140" height="12" fill="var(--s2)"/><text x="234" y="54" fill="var(--muted)" font-size="8">1</text>
  <text x="8" y="70" fill="var(--muted)" font-size="8">fsum</text><rect x="90" y="62" width="140" height="12" fill="var(--s1)"/><text x="234" y="72" fill="var(--muted)" font-size="8">1 (order-free)</text>
  <text x="90" y="96" fill="var(--muted)" font-size="8">only fsum reaches the true-sum line no matter how the additions are ordered</text>
</svg>
^ The two naive orders land at 0 and 1; only fsum reaches the dashed true-sum line and does so independent of order, which is what makes it reproducible.

## Definition of done

The self-test pins it: the two orders disagree, the naive sum loses the value, the disagreement is the whole value, and fsum is exact and order-independent.

```python filename=modules/teaching-and-portability/code/sumorder-inter-01/sumorder.py:93-106 COMPLETE
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
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the two orders disagree; naive summation loses the value; fsum is exact and order-independent
------------------------------------------------------------------------------------------------------------
  the same values sum differently in different orders = True (0 vs 1)
  the left-to-right sum is not the true total = True (0 != 1)
  the disagreement is the entire small value = True (|0 - 1| = 1)
  math.fsum returns the exact true sum = True (1)
  math.fsum is the same in either order = True (1)
------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  not_associative=True  naive_loses_value=True  error_is_whole_value=True  fsum_exact=True  fsum_order_independent=True
```

**Done means the non-reproducibility is proven: the identical three values sum to 0 left-to-right and 1 right-to-left — a disagreement equal to the entire true value — while math.fsum returns the exact 1 in either order, the property a documented total needs.**

## Boss fight

The fixture used an extreme cancellation to make the error the whole value. Predict what non-associativity does in ordinary sums with no dramatic cancellation, and whether math.fsum is always the answer. It is tempting to think this only bites contrived inputs.

Even without dramatic cancellation, non-associativity perturbs the last few digits of any long floating-point sum, and that is enough to break bit-exact reproducibility. Sum a million ordinary numbers left-to-right versus in a different order and the totals typically differ in the final digits, because rounding error accumulates order-dependently. That rarely changes a headline number, but it means a documented result printed to full precision will not match on a rerun that sums differently — and modern numerical libraries sum differently all the time: BLAS and NumPy reorder additions for cache and SIMD, parallel reductions combine partial sums in a non-deterministic order, GPUs reorder across thousands of threads. Bit-exact reproducibility across machines is genuinely hard, which is why reproducible-build and deterministic-ML efforts pin thread counts and reduction orders, not just seeds.

Whether to reach for `math.fsum` depends on what you need. It gives the correctly rounded exact sum and is the right default for a scalar total you want reproducible and accurate, but it is slower than a plain loop and does not vectorize, so it is wrong for a hot inner loop over huge arrays. There the practical answers are: fix and document the order (sort, or "sum in index order"), use a compensated sum (Kahan) that is fast and order-robust, use a higher-precision accumulator, or accept that only the first several digits are reproducible and round your reported result to those. The general lesson is the same as seeding and version-pinning: a number is only reproducible if you have controlled everything it silently depends on, and floating-point sums silently depend on order.

```python filename=modules/teaching-and-portability/code/sumorder-inter-01/sumorder.py:59-61 COMPLETE
def exact(values):
    """math.fsum tracks partial sums exactly, so the result does not depend on order."""
    return math.fsum(values)
```

**Floating-point addition is not associative, so a naive sum's total depends on order and is not reproducible — fix it with an order-independent exact sum (math.fsum), a compensated sum, or a specified fixed order, and remember that libraries, threads, and GPUs reorder additions freely, so a documented total needs its summation controlled just as a random result needs its seed.**

## External resources

Goldberg's "What Every Computer Scientist Should Know About Floating-Point Arithmetic" — the canonical reference on rounding, non-associativity, and cancellation, with the guarantees that do and do not hold.

The Python `math.fsum` documentation and the Kahan summation algorithm — the exact and compensated summation methods that remove the order dependence a plain loop has.

The companion "seed the random generator" and "pin the dependency version" modules — the same reproducibility discipline in two other guises: a documented output is only reproducible once every hidden dependency, including summation order, is controlled.
