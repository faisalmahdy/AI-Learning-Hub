---
id: intdiv-inter-01
title: Integer division rounds two different ways across languages — so a ported remainder flips sign and a hash bucket goes negative
topic: teaching-and-portability
level: intermediate
status: ready
time: 16 min
summary: Every language agrees on dividing positives, but disagrees the instant a negative appears, because there are two ways to round the quotient to an integer. Python and Ruby floor toward negative infinity, so the remainder takes the divisor's sign and is never negative for a positive divisor; C, Java, Go, JavaScript, and Rust truncate toward zero, so the remainder takes the dividend's sign and can be negative. Same operands, same operators, different answers — so a formula correct in one language is wrong when ported, and the bug hides until a negative value flows through. It bites hardest at value % n, the workhorse of hashing and indexing: programmers rely on it to land in [0, n), which holds in Python for any value but gives a negative index in a truncating language, reading out of bounds or selecting the wrong bucket. The portable fix in any language is ((value % n) + n) % n. On a fixture, −7 divided by 3 is (−3, 2) floored and (−2, −1) truncated, and a negative hash gives a negative bucket under truncation that the portable form corrects back into [0, num_buckets).
eli5: Ask "how many whole 3s are in −7, and what's left over?" Python answers "−3 with 2 left over" (it rounds down); C answers "−2 with −1 left over" (it rounds toward zero). Both are self-consistent, but they don't agree, so a little math formula you copy from one language to the other can quietly give a different answer once a negative number shows up. The usual place this breaks is picking a slot with "leftover after dividing" — in some languages the leftover can be negative, which points at a slot that doesn't exist. Wrapping it as ((x mod n) + n) mod n always lands on a real slot.
---

## Why this module

Integer division has to turn a fractional quotient into a whole number, and there is more than one defensible way to round it — so the language you run on, not the arithmetic you wrote, decides the sign of a remainder, and a formula that assumed one convention breaks silently on the other.

For non-negative numbers there is no ambiguity: 7 divided by 3 is 2 with remainder 1 everywhere. The disagreement begins with a negative operand, because −7 divided by 3 is −2.33, and rounding that to an integer quotient can go two ways. Python and Ruby floor it toward negative infinity to −3, which forces the remainder to +2 so that quotient × divisor + remainder still equals −7; the remainder takes the sign of the divisor and is never negative for a positive divisor. C, Java, Go, JavaScript, and Rust truncate toward zero to −2, which forces the remainder to −1; the remainder takes the sign of the dividend. Both obey the fundamental identity, both are internally consistent, and they give different answers. Nothing in the source code `a % b` tells you which you will get — the runtime does.

**Integer division rounds toward negative infinity in some languages and toward zero in others, so for a negative operand the quotient and the sign of the remainder differ by language — a `%` that is correct where you wrote it can be wrong where you port it, with no error to warn you.**

The blast radius is `value % n`, the operation behind hash buckets, ring buffers, array wrap-around, and clock arithmetic. Programmers lean on one guarantee: that `value % n` lands in `[0, n)`, a valid index. That guarantee holds in Python for any value, positive or negative — but in a truncating language a negative value yields a negative remainder, so `hash % num_buckets` returns a negative index that reads out of bounds or selects the wrong bucket. The bug is invisible until the first negative value arrives, which for a hash function that can return negatives is a matter of when, not if. The portable defense, correct in every language, is `((value % n) + n) % n`: a no-op where the remainder is already non-negative, and a lift back into range where it is not. This module computes both conventions and shows the negative bucket appear and get corrected.

## Concepts

**Floored division** (Python, Ruby) rounds the quotient toward negative infinity. The remainder then takes the sign of the divisor, so `a % n` for a positive `n` is always in `[0, n)`.

```python filename=modules/teaching-and-portability/code/intdiv-inter-01/intdiv.py:42-44 COMPLETE
def floor_divmod(a, b):
    """Python/Ruby semantics: quotient floored toward -inf, remainder takes the divisor's sign (native // and %)."""
    return a // b, a % b
```

**Truncated division** (C, Java, Go, JavaScript, Rust) rounds the quotient toward zero. The remainder then takes the sign of the dividend, so it can be negative — which is what breaks a bucket index.

```python filename=modules/teaching-and-portability/code/intdiv-inter-01/intdiv.py:47-52 COMPLETE
def trunc_divmod(a, b):
    """C/Java/Go/JS/Rust semantics: quotient truncated toward zero, remainder takes the dividend's sign."""
    q = abs(a) // abs(b)
    if (a < 0) != (b < 0):
        q = -q
    return q, a - q * b
```

**Both obey the identity** dividend = quotient × divisor + remainder. That is why the two rounding choices force different remainders: once you fix how the quotient rounds, the remainder is determined, and the two quotients differ for negatives.

<svg role="img" aria-label="On a number line, -7/3 = -2.33 rounds to -3 under floored division and to -2 under truncated division, giving remainders +2 and -1" viewBox="0 0 300 92" width="300" height="92">
  <line x1="20" y1="50" x2="290" y2="50" stroke="var(--grid)"/>
  <g font-size="7" fill="var(--muted)"><text x="40" y="64">-3</text><text x="120" y="64">-2</text><text x="200" y="64">-1</text><text x="278" y="64">0</text></g>
  <line x1="44" y1="46" x2="44" y2="54" stroke="var(--line)"/><line x1="124" y1="46" x2="124" y2="54" stroke="var(--line)"/><line x1="204" y1="46" x2="204" y2="54" stroke="var(--line)"/><line x1="282" y1="46" x2="282" y2="54" stroke="var(--line)"/>
  <circle cx="97" cy="50" r="3" fill="var(--ink)"/><text x="78" y="40" fill="var(--ink)" font-size="7">-7/3 = -2.33</text>
  <line x1="97" y1="50" x2="44" y2="50" stroke="var(--s1)" stroke-width="1.5"/><text x="30" y="28" fill="var(--s1)" font-size="7">floor → -3, r=+2</text>
  <line x1="97" y1="50" x2="124" y2="50" stroke="var(--s2)" stroke-width="1.5"/><text x="150" y="40" fill="var(--s2)" font-size="7">trunc → -2, r=-1</text>
  <text x="20" y="82" fill="var(--muted)" font-size="8">floor rounds down (away from zero here); trunc rounds toward zero — different quotient, different remainder</text>
</svg>
^ For −7/3 = −2.33, floored division rounds down to −3 (remainder +2) while truncated division rounds toward zero to −2 (remainder −1) — the same operands giving different results by rounding rule.

**Positives divide the same everywhere, but a negative operand splits the quotient and flips the remainder's sign between floored and truncated languages — so never assume `%` is non-negative or that a division formula ports unchanged.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/intdiv-inter-01/intdiv.py

The fixture is four (dividend, divisor) pairs spanning the sign combinations, plus hashes to bucket.

```json filename=modules/teaching-and-portability/code/intdiv-inter-01/intdiv.json:3-5 COMPLETE
  "pairs": [[7, 3], [-7, 3], [8, -3], [-8, -3]],
  "hashes": [12345, -9876, -1, 7],
  "num_buckets": 8
```

Run `--divmod` to divide each pair both ways.

```text filename=--divmod
DIVMOD — floored (Python/Ruby) vs truncated (C/Java/Go/JS/Rust) integer division
--------------------------------------------------------------------------
  a    b     floored q,r      truncated q,r    differ?
  7    3     2, 1             2, 1             False
  -7   3     -3, 2            -2, -1           True
  8    -3    -3, -1           -2, 2            True
  -8   -3    2, -2            2, -2            False
```

The first row, 7 ÷ 3, agrees: (2, 1) both ways, because rounding −2.33 versus rounding a positive never diverges. The last row, −8 ÷ −3, also agrees at (2, −2) — two negatives make a positive quotient, and both conventions round it the same. The two middle rows are where the languages part. For −7 ÷ 3 the floored answer is (−3, 2) and the truncated is (−2, −1): different quotient, and a remainder that flips from +2 to −1. For 8 ÷ −3 it is (−3, −1) versus (−2, 2). The pattern is exactly the rule: floored remainders follow the divisor's sign, truncated remainders follow the dividend's. A programmer who tested `a % b` only on the agreeing rows — all positives — would ship code that is correct in their tests and wrong the first time a negative flows through on a runtime with the other convention.

<svg role="img" aria-label="A 2x2 grid of dividend and divisor signs: same-sign-as-positives and both-negative agree, the two mixed-sign cases differ between floored and truncated" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">do floored and truncated agree? by operand signs</text>
  <text x="30" y="28" fill="var(--muted)" font-size="7">b &gt; 0        b &lt; 0</text>
  <text x="4" y="48" fill="var(--muted)" font-size="7">a ≥ 0</text>
  <rect x="40" y="38" width="90" height="20" fill="var(--s1)"/><text x="60" y="52" fill="var(--panel)" font-size="8">agree</text>
  <rect x="140" y="38" width="90" height="20" fill="var(--s2)"/><text x="158" y="52" fill="var(--panel)" font-size="8">DIFFER</text>
  <text x="4" y="76" fill="var(--muted)" font-size="7">a &lt; 0</text>
  <rect x="40" y="66" width="90" height="20" fill="var(--s2)"/><text x="58" y="80" fill="var(--panel)" font-size="8">DIFFER</text>
  <rect x="140" y="66" width="90" height="20" fill="var(--s1)"/><text x="160" y="80" fill="var(--panel)" font-size="8">agree</text>
  <text x="6" y="97" fill="var(--muted)" font-size="8">the two cases with exactly one negative operand are where the conventions split</text>
</svg>
^ The two conventions agree when both operands are non-negative and when both are negative, and differ in exactly the two mixed-sign cases — so a positives-only test never sees the divergence.

## Build

The divergence turns into a real out-of-bounds bug at the bucket index. Run `--bucket`, which maps each hash into 8 buckets three ways.

```text filename=--bucket
BUCKET — hash % 8 under each rule, and the portable form
----------------------------------------------------------------------
  hash      floored %   truncated %   portable ((h%n)+n)%n   in [0,8)?
  12345     1          1            1                     True
  -9876     4          -4           4                     True
  -1        7          -1           7                     True
  7         7          7            7                     True
```

For the positive hashes, all three columns agree and land in `[0, 8)`. For the negative hashes the truncated column breaks: `-9876 % 8` is −4 and `-1 % 8` is −1 under truncation — negative indices that would read before the start of an 8-element bucket array. The floored column gives 4 and 7, valid buckets, which is why the same `hash % num_buckets` line is safe in Python and a latent crash in C or Java. The portable column applies `((h % n) + n) % n` and lands in `[0, 8)` for every hash, matching the floored result exactly: it adds `n` to lift a negative remainder back into range, then takes `% n` again to leave already-valid values untouched.

```python filename=modules/teaching-and-portability/code/intdiv-inter-01/intdiv.py:55-57 COMPLETE
def portable_bucket(h, n):
    """A non-negative bucket in [0, n) under ANY language's %: lift a possibly-negative remainder back into range."""
    return ((trunc_divmod(h, n)[1]) + n) % n
```

The reason this one line works in every language is that it never relies on `%` being non-negative. Whatever sign the first `% n` produces — non-negative under flooring, possibly negative under truncation — adding `n` makes the value fall in `(0, 2n)` for a negative remainder or `[n, 2n)`-ish for a non-negative one, and the final `% n` maps that back to `[0, n)` regardless of convention (because after adding `n` the value is non-negative, where both conventions agree). It is the portable idiom for any wrap-around: bucket assignment, circular buffers, modular clock math, negative array indexing. Write the bare `%` and you are betting the code never moves to a truncating language and never meets a negative — two bets that eventually lose.

<svg role="img" aria-label="A negative hash points to a negative index outside the 8-bucket ring under truncation; the portable formula wraps it back to a valid bucket inside [0,8)" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">bucket index for hash −1 into 8 buckets</text>
  <g font-size="7" fill="var(--muted)"><text x="60" y="46">0</text><text x="90" y="46">1</text><text x="230" y="46">7</text></g>
  <rect x="56" y="50" width="200" height="16" fill="none" stroke="var(--line)"/>
  <g><line x1="86" y1="50" x2="86" y2="66" stroke="var(--grid)"/><line x1="116" y1="50" x2="116" y2="66" stroke="var(--grid)"/><line x1="146" y1="50" x2="146" y2="66" stroke="var(--grid)"/><line x1="176" y1="50" x2="176" y2="66" stroke="var(--grid)"/><line x1="206" y1="50" x2="206" y2="66" stroke="var(--grid)"/><line x1="236" y1="50" x2="236" y2="66" stroke="var(--grid)"/></g>
  <circle cx="42" cy="58" r="3" fill="var(--s2)"/><text x="20" y="40" fill="var(--s2)" font-size="7">trunc −1: out of bounds ✗</text>
  <circle cx="242" cy="58" r="3" fill="var(--s1)"/><text x="210" y="82" fill="var(--s1)" font-size="7">portable → 7 ✓</text>
  <path d="M42 62 Q140 92 240 64" fill="none" stroke="var(--s1)" stroke-dasharray="3 2"/>
  <text x="6" y="94" fill="var(--muted)" font-size="8">((h % n) + n) % n wraps the negative index back into the valid bucket range</text>
</svg>
^ Under truncation hash −1 maps to index −1, before the start of the 8-bucket array; the portable `((h % n) + n) % n` wraps it to bucket 7, inside `[0, 8)`.

## Definition of done

The self-test pins every claim: the two roundings agree on non-negatives and differ on negatives, both satisfy the division identity, a truncated `%` can go negative, and the portable form is always a valid bucket.

```python filename=modules/teaching-and-portability/code/intdiv-inter-01/intdiv.py:94-107 COMPLETE
    agree_on_nonneg = all(floor_divmod(a, b) == trunc_divmod(a, b) for a, b in pairs if a >= 0 and b > 0)
    print("  floored and truncated agree when operands are non-negative = %s" % agree_on_nonneg)

    differ_on_neg = any(floor_divmod(a, b) != trunc_divmod(a, b) for a, b in pairs if a < 0 or b < 0)
    print("  they differ once a negative operand appears = %s" % differ_on_neg)

    identity_both = all(fq * b + fr == a and tq * b + tr == a
                        for a, b in pairs
                        for (fq, fr), (tq, tr) in [(floor_divmod(a, b), trunc_divmod(a, b))])
    print("  both satisfy dividend = quotient*divisor + remainder = %s" % identity_both)

    trunc_can_go_negative = any(trunc_divmod(h, n)[1] < 0 for h in hashes)
    print("  a truncated hash %% n can be negative (out-of-bounds bucket) = %s (%s)"
          % (trunc_can_go_negative, [trunc_divmod(h, n)[1] for h in hashes]))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the two roundings agree on non-negatives but differ on negatives; the portable form is always in [0, n)
--------------------------------------------------------------------------------------------------------------------
  floored and truncated agree when operands are non-negative = True
  they differ once a negative operand appears = True
  both satisfy dividend = quotient*divisor + remainder = True
  a truncated hash % n can be negative (out-of-bounds bucket) = True ([1, -4, -1, 7])
  the portable ((h%n)+n)%n is always a valid bucket in [0,8) = True ([1, 4, 7, 7])
  the portable form equals Python's floored % for every hash = True
```

**Done means the divergence and its fix are proven: floored and truncated division agree on non-negative operands but differ once a negative appears (−7/3 is −3,2 versus −2,−1), both satisfy the division identity, a truncated `hash % 8` returns negative indices (−4, −1) that are out-of-bounds buckets, and the portable `((h % n) + n) % n` returns a valid bucket in [0,8) for every hash, matching Python's floored `%`.**

## Boss fight

Predict the two ways the "just make it positive" instinct goes wrong. It is tempting to fix a negative remainder with `abs(value) % n`.

The first trap is that `abs(value) % n` gives a value in range but the WRONG value — it is not the same bucket as `((value % n) + n) % n`. For hash −1 into 8 buckets, `abs(-1) % 8` is 1, but the correct wrapped bucket is 7; `abs` folds negative inputs onto their positive twins, so `−1` and `+1` collide into the same bucket while `−1` and `−9` (which should collide, both ≡ 7 mod 8) do not. That silently doubles the collision rate for the mapping and corrupts any scheme where the sign carries meaning. `abs` also changes the value's residue class entirely, so it is not modular arithmetic at all — it just happens to be non-negative. The only correct non-negative modulo is the add-and-remod form; `abs` is a different function that looks similar and passes a "no negative index" check while getting the actual bucket wrong.

The second trap is that the same two-conventions problem lives in every operation that has to round, not just `%`, and in every language boundary, not just source ports. Rounding a float to int (round-half-to-even versus round-half-up), rounding a division in SQL versus in the application, integer overflow wrapping versus saturating, and right-shifting a negative integer (arithmetic versus logical shift) are all places where two runtimes give two answers for the same input. Data that crosses a boundary — a value computed in Postgres and re-derived in Python, a hash written by a C service and looked up by a Java one — must agree on the convention or the two sides compute different buckets for the same key and silently miss each other. The general rule is the portability rule: when an operation has an implementation-defined rounding or sign behavior, pin it explicitly (use a floor-division or a defined-modulo function, state the rounding mode) rather than trusting that "integer division" means the same thing on both sides of the boundary.

**Integer division rounds toward negative infinity (Python, Ruby) or toward zero (C, Java, Go, JS, Rust), so a negative operand flips the remainder's sign and a bare `hash % n` yields a negative, out-of-bounds bucket in a truncating language — force a valid bucket with `((value % n) + n) % n` (never `abs`, which computes the wrong residue class), and treat every rounding- or sign-defined operation that crosses a language boundary as something to pin explicitly, because "integer division" is not one operation but two.**

## External resources

Any language reference on the `%` / `mod` operator and integer division rounding — for example Python's floor-division semantics versus the C99 / Java / Go specification of truncation toward zero — which state the sign of the remainder precisely.

Donald Knuth's discussion of floored versus truncated division (and the case for floored/Euclidean modulo) and any cross-language "modulo of negative numbers" reference — the design rationale and the table of which languages choose which.

The companion "normalize line endings before you hash" and "specify encoding when you read and write" modules — all three are portability bugs where an operation you assume is universal (hashing, text decoding, integer modulo) has a platform- or language-dependent behavior that only shows up across a boundary.
