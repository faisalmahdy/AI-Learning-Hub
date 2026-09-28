---
id: floateq-inter-01
title: Never compare floats with == — 0.1 + 0.2 is not 0.3, because decimals don't fit exactly in binary
topic: teaching-and-portability
level: intermediate
status: ready
time: 14 min
summary: A floating-point number is stored in binary, and most decimal fractions have no exact binary representation — 0.1, 0.2, and 0.3 are each stored as the nearest binary value, slightly off. So adding the stored 0.1 to the stored 0.2 lands on 0.30000000000000004, close to 0.3 but not the same stored value as the literal 0.3, and `0.1 + 0.2 == 0.3` is False — not because the math is wrong but because == asks whether two binary values are bit-for-bit identical. Any code that tests a computed float for exact equality — a loop that stops when an accumulator `== target`, an assertion that `result == 0.3`, a check that a balance is `== 0` — is a latent bug that fires whenever the computation routes through inexact values, and the errors compound: adding 0.1 ten times gives 0.9999999999999999, not 1.0. The fix is to compare with a tolerance — the values are "equal" if within a small epsilon — for which the standard library's math.isclose uses both relative and absolute tolerances so it works across magnitudes; for exact decimal arithmetic like money, use a decimal type or integer cents instead of floats. The trap's disguise is that dyadic values (sums of powers of two) are exact, so 0.5 + 0.25 == 0.75 is True — equality sometimes works, which is exactly why the bug survives testing and surfaces on real data.
eli5: Computers store numbers in base two, and just as you can't write one-third exactly as a decimal (0.3333…), the computer can't write one-tenth exactly in base two. So 0.1 is stored as something a hair off, and when you add a few of these slightly-off numbers the tiny errors add up: 0.1 + 0.2 comes out as 0.30000000000000004, which is NOT the same as the stored 0.3. Asking "are these exactly equal?" then says no, even though they should be. The fix is to ask "are these close enough?" instead. And beware: it sometimes works by luck (for halves and quarters), which fools people into trusting it.
---

## Why this module

`==` on floats is the equality test everyone writes and almost no one should. It looks obviously correct, it passes on the tidy example values people test with, and then it fails on real data — a total that never hits its target, an assertion that rejects a right answer, a loop that never ends — because two numbers that are equal in decimal are different in the binary the computer actually stores.

A floating-point number is stored in binary, and most decimal fractions have no exact binary representation, the same way 1/3 has no exact decimal representation. 0.1 is stored as the nearest binary value, which is not exactly one tenth; so is 0.2, and so is 0.3. When you add the stored 0.1 to the stored 0.2 you get the binary sum of two already-rounded values, and it lands on 0.30000000000000004 — close to 0.3 but not the same stored value as the literal 0.3. So `0.1 + 0.2 == 0.3` is False, not because the math is wrong but because `==` asks whether two binary values are bit-for-bit identical, and these two are not. Any code that tests a computed float for equality against an expected float — a loop that stops when an accumulator `== target`, a test that asserts `result == 0.3`, a check that a balance is `== 0` — is a latent bug that fires whenever the computation routes through inexact values. And the errors compound: add 0.1 to itself ten times and you get 0.9999999999999999, not 1.0.

The fix is to never test floats for exact equality. Compare with a tolerance: the values are "equal" if within a small epsilon of each other, and the standard library's math.isclose does this correctly, using both a relative and an absolute tolerance so it works across magnitudes. For exact decimal arithmetic — money especially — use a decimal type or integer cents instead of floats at all. The trap's disguise is that values which *are* exact in binary compare equal: 0.5 and 0.25 are 1/2 and 1/4, so 0.5 + 0.25 == 0.75 is True. Equality sometimes works, on the dyadic values people reach for in examples, which is exactly why the bug survives testing and surfaces on real data. This module runs the comparisons.

**Most decimals have no exact binary representation, so 0.1 + 0.2 is 0.30000000000000004 and == against 0.3 is False (and accumulated float errors compound), so compare computed floats with a tolerance (math.isclose) — never == — and use decimals or integers when you need exact arithmetic.**

## Concepts

**The correct comparison** tests whether two floats are within a tolerance, not bit-for-bit identical — `math.isclose` with both a relative and an absolute tolerance so it works whether the numbers are near 1 or near a million.

```python filename=modules/teaching-and-portability/code/floateq-inter-01/floateq.py:46-48 COMPLETE
def approx_equal(x, y, tol=1e-9):
    """The correct float comparison: within a tolerance, not bit-for-bit -- wraps math.isclose."""
    return math.isclose(x, y, rel_tol=tol, abs_tol=tol)
```

**Accumulation** is where the error grows: each addition of an inexact value carries its rounding error, and repeated additions compound it, so a running total drifts away from the exact decimal answer.

```python filename=modules/teaching-and-portability/code/floateq-inter-01/floateq.py:51-56 COMPLETE
def accumulate(value, times):
    """Add `value` to a running total `times` times -- the tiny per-add error compounds."""
    total = 0.0
    for _ in range(times):
        total += value
    return total
```

<svg role="img" aria-label="A number line zoomed near 0.3 showing the literal 0.3 and the sum 0.1 plus 0.2 landing at a slightly higher point, with a tolerance band around 0.3 that includes the sum" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">0.1 + 0.2 lands just past 0.3; == misses, a tolerance catches</text>
  <line x1="20" y1="56" x2="285" y2="56" stroke="var(--line)"/>
  <rect x="120" y="48" width="60" height="16" fill="var(--s1)" opacity="0.3"/><text x="120" y="82" fill="var(--muted)" font-size="6">tolerance band</text>
  <line x1="150" y1="42" x2="150" y2="70" stroke="var(--s1)"/><text x="138" y="38" fill="var(--muted)" font-size="7">0.3 (literal)</text>
  <circle cx="168" cy="56" r="3" fill="var(--s2)"/><text x="150" y="90" fill="var(--muted)" font-size="6">0.30000000000000004</text>
  <line x1="168" y1="50" x2="168" y2="62" stroke="var(--s2)"/>
  <text x="196" y="46" fill="var(--muted)" font-size="6">== says ✗ (not identical)</text>
  <text x="196" y="72" fill="var(--muted)" font-size="6">isclose says ✓ (in band)</text>
</svg>
^ The sum 0.1 + 0.2 sits a hair to the right of the stored 0.3, so `==` (which demands the identical bits) rejects it, while a tolerance comparison accepts anything inside a small band around 0.3.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/floateq-inter-01/floateq.py

The fixture is the classic operands.

```json filename=modules/teaching-and-portability/code/floateq-inter-01/floateq.json:3-5 COMPLETE
  "a": 0.1,
  "b": 0.2,
  "expected": 0.3,
```

Run `--equality`.

```text filename=--equality
EQUALITY — 0.1 + 0.2 vs 0.3
--------------------------------------------------------
  0.1 + 0.2          = 0.30000000000000004
  (0.1 + 0.2) == 0.3   = False   <- False: the stored values differ
  math.isclose(...)      = True   <- True: within tolerance
--------------------------------------------------------
  the exact-decimal answer is 0.3, but the binary sum is 0.30000000000000004.
```

The sum prints as 0.30000000000000004 — that trailing `4` at the seventeenth digit is the accumulated rounding of storing 0.1 and 0.2 in binary and adding them. It is a tiny error, about 4 parts in 10^17, but it is enough that the stored result and the stored literal 0.3 are different bit patterns, so `==` returns False. This is the whole bug in one line: the arithmetic is as correct as binary floats allow, but exact equality asks a question binary floats cannot answer the way you expect. `math.isclose` returns True because the two values are far closer than its tolerance — it asks "are these within epsilon?" which is the question you actually meant. The lesson is not that floats are broken; it is that `==` is the wrong operator for them, and it fails silently, returning a plausible False that sends a correct computation down the wrong branch.

## Build

The error is not a one-off; it accumulates, and its absence on some values is what makes it dangerous. Run `--accumulate`.

```text filename=--accumulate
ACCUMULATE — errors compound, but power-of-two values stay exact
------------------------------------------------------------
  0.1 added 10 times = 0.9999999999999999
  (...) == 1.0        = False   (isclose = True)
  0.5 + 0.25 == 0.75      = True   <- exact: dyadic values fit binary
```

Adding 0.1 ten times gives 0.9999999999999999, not 1.0 — each addition folded in a little more representation error, and ten of them drifted the total below 1.0, so `== 1.0` is False. A loop written `while total != 1.0` incrementing by 0.1 would never stop. But look at the last line: `0.5 + 0.25 == 0.75` is True. 0.5 is 1/2 and 0.25 is 1/4, both exact powers of two, so they and their sum are represented perfectly in binary and `==` works. This is the trap's disguise and the reason it is so persistent: the dyadic fractions people naturally use in quick tests (halves, quarters, eighths) compare equal under `==`, so the naive code passes every hand-written test, and then fails in production on values like 0.1, 0.3, or any price, percentage, or measurement that is not a power of two. The tell is that whether `==` works depends on the specific values, which is exactly the property a correctness test must not have.

```python filename=modules/teaching-and-portability/code/floateq-inter-01/floateq.py:102-109 COMPLETE
    v, n, target = data["accumulate_value"], data["accumulate_times"], data["accumulate_target"]
    acc = accumulate(v, n)
    accumulate_off = acc != target and approx_equal(acc, target)
    print("  %s x %d != %s under == but isclose = %s (%r)" % (v, n, target, accumulate_off, acc))

    da, db, dexp = data["dyadic_a"], data["dyadic_b"], data["dyadic_expected"]
    dyadic_exact = (da + db) == dexp
    print("  power-of-two sum %s + %s == %s is exact = %s" % (da, db, dexp, dyadic_exact))
```

<svg role="img" aria-label="Adding 0.1 ten times drifts below 1.0 to 0.9999999999999999, while 0.5 plus 0.25 lands exactly on 0.75" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">inexact values drift; dyadic values stay exact</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">0.1 ×10</text>
  <line x1="70" y1="30" x2="250" y2="30" stroke="var(--line)"/>
  <line x1="250" y1="24" x2="250" y2="36" stroke="var(--s1)"/><text x="238" y="22" fill="var(--muted)" font-size="6">1.0</text>
  <circle cx="244" cy="30" r="3" fill="var(--s2)"/><text x="150" y="46" fill="var(--muted)" font-size="6">lands at 0.9999999999999999 (≠ 1.0)</text>
  <text x="10" y="76" fill="var(--muted)" font-size="7">0.5+0.25</text>
  <line x1="70" y1="72" x2="250" y2="72" stroke="var(--line)"/>
  <line x1="210" y1="66" x2="210" y2="78" stroke="var(--s1)"/><text x="200" y="64" fill="var(--muted)" font-size="6">0.75</text>
  <circle cx="210" cy="72" r="3" fill="var(--s1)"/><text x="150" y="88" fill="var(--muted)" font-size="6">lands exactly on 0.75 (== works)</text>
</svg>
^ Accumulating 0.1 drifts off the target to 0.9999999999999999, so `==` fails, while the dyadic 0.5 + 0.25 lands exactly on 0.75 and `==` succeeds — the same operator, reliable or not depending on whether the values happen to be powers of two.

## Definition of done

The self-test pins the failed equality, the off-by-a-hair stored value, and the tolerance fix.

```python filename=modules/teaching-and-portability/code/floateq-inter-01/floateq.py:93-100 COMPLETE
    naive_equal_false = (s == exp) is False
    print("  (%s + %s) == %s is False = %s (%r)" % (a, b, exp, naive_equal_false, s))

    stored_value_off = repr(s) != repr(exp)
    print("  the stored sum differs from the literal %s = %s (%r)" % (exp, stored_value_off, s))

    isclose_true = approx_equal(s, exp)
    print("  math.isclose treats them as equal = %s" % isclose_true)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — == fails on inexact sums but isclose passes; dyadic (power-of-two) sums are exact under ==
----------------------------------------------------------------------------------------------------------------
  (0.1 + 0.2) == 0.3 is False = True (0.30000000000000004)
  the stored sum differs from the literal 0.3 = True (0.30000000000000004)
  math.isclose treats them as equal = True
  0.1 x 10 != 1.0 under == but isclose = True (0.9999999999999999)
  power-of-two sum 0.5 + 0.25 == 0.75 is exact = True
```

**Done means the failure and the fix are proven on real values: 0.1 + 0.2 stores as 0.30000000000000004 so `== 0.3` is False while math.isclose is True, accumulating 0.1 ten times gives 0.9999999999999999 (≠ 1.0 under ==, close under isclose), and the dyadic 0.5 + 0.25 == 0.75 is exact — so computed floats must be compared with a tolerance, and the fact that == works on power-of-two values is the disguise that lets the bug ship.**

## Boss fight

Predict two ways the tolerance fix is more than "use math.isclose," because the right tolerance is not universal and sometimes floats are the wrong tool entirely.

The first trap is that a single fixed epsilon is wrong across magnitudes, which is why isclose uses *two* tolerances and why a naive `abs(a - b) < 1e-9` is a bug of its own. Floating point has constant *relative* precision, not constant absolute precision: near 1.0 the gap between representable numbers is about 10^-16, but near a billion it is about 10^-7, so an absolute tolerance of 1e-9 is far too loose near zero (calling 0 and 1e-10 unequal-but-you-wanted-equal, or worse, calling genuinely different tiny numbers equal) and far too tight near large values (rejecting numbers that are as close as floats near a billion can get). A relative tolerance (`|a-b| <= tol * max(|a|,|b|)`) fixes the large end but breaks near zero, where relative comparison against ~0 is meaningless — which is exactly why math.isclose combines a relative tolerance for the general case with an absolute tolerance as a floor for values near zero. So the discipline is to use a well-designed comparison (isclose, or numpy's allclose) rather than hand-rolling one, and to set the absolute tolerance deliberately when your values can be near zero.

<svg role="img" aria-label="The gap between representable floats grows with magnitude: tightly spaced near 1, widely spaced near a billion, so a fixed absolute epsilon is too loose in one place and too tight in another" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">float spacing grows with magnitude — a fixed epsilon can't fit both</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">near 1</text>
  <g fill="var(--s1)">
  <circle cx="60" cy="30" r="1.5"/><circle cx="70" cy="30" r="1.5"/><circle cx="80" cy="30" r="1.5"/><circle cx="90" cy="30" r="1.5"/><circle cx="100" cy="30" r="1.5"/><circle cx="110" cy="30" r="1.5"/><circle cx="120" cy="30" r="1.5"/><circle cx="130" cy="30" r="1.5"/>
  </g>
  <text x="150" y="34" fill="var(--muted)" font-size="6">gap ≈ 1e-16 (dense)</text>
  <text x="10" y="64" fill="var(--muted)" font-size="7">near 1e9</text>
  <g fill="var(--s2)">
  <circle cx="60" cy="60" r="1.5"/><circle cx="95" cy="60" r="1.5"/><circle cx="130" cy="60" r="1.5"/><circle cx="165" cy="60" r="1.5"/><circle cx="200" cy="60" r="1.5"/>
  </g>
  <text x="210" y="64" fill="var(--muted)" font-size="6">gap ≈ 1e-7 (sparse)</text>
  <text x="10" y="88" fill="var(--muted)" font-size="7">isclose uses a relative tolerance (+ an absolute floor near zero)</text>
</svg>
^ Representable floats are packed densely near 1 and sparsely near a billion, so a single absolute epsilon is far too loose at small magnitudes and too tight at large ones — which is why isclose scales its tolerance relatively, with an absolute floor for values near zero.

The second trap is that tolerance comparison is the right fix for *approximate* quantities but the wrong fix for values that must be *exact*, and confusing the two causes real damage.

The second trap is that tolerance comparison is the right fix for *approximate* quantities but the wrong fix for values that must be *exact*, and confusing the two causes real damage. Money is the canonical case: if you represent dollars as floats, 0.1 + 0.2 dollars is not 0.30 and rounding for display can be off by a cent, and no tolerance makes a financial ledger balance — the fix there is not isclose, it is to not use binary floats at all, using a decimal type (which represents 0.1 exactly) or integer cents. More broadly, floats are for measurements and computed reals where a tiny error is acceptable; exact-decimal domains (currency, some IDs, tax) need exact types, and discrete quantities (counts, indices) need integers. And even within float land, equality is not the only comparison that gets subtle: sorting or hashing floats, using a float as a dict key, or relying on `<` at the boundary all inherit the representation issues, and NaN breaks equality entirely (NaN != NaN, so `x == x` can be False). The rule generalizes: know whether your quantity is exact or approximate, pick the type accordingly (integer/decimal for exact, float for approximate), and for approximate floats compare with a purpose-built tolerance, never `==`.

**A correct float comparison needs both a relative tolerance (for large magnitudes) and an absolute floor (near zero), so use math.isclose / allclose rather than a hand-rolled epsilon — but tolerance is only right for approximate quantities; exact domains like money need a decimal type or integer units, counts need integers, and NaN's self-inequality is a further reason `==` on floats is unsafe.**

## External resources

Python's documentation for math.isclose and "Floating Point Arithmetic: Issues and Limitations," plus "What Every Computer Scientist Should Know About Floating-Point Arithmetic" — why decimals are inexact in binary, the relative/absolute tolerance design, and why == fails.

Python's decimal module documentation — exact decimal arithmetic for money and other domains where binary floats and tolerance comparison are the wrong tool.

The companion sum-order and round-half-even modules in this topic — all three stem from binary floating point contradicting decimal intuition: order-dependent sums, surprising tie-rounding, and here inexact equality, each fixed by respecting how floats actually store and combine numbers.
