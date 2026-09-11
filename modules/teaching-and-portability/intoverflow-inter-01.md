---
id: intoverflow-inter-01
title: Mask fixed-width integer arithmetic to the width — Python's ints never overflow, so a ported 32-bit hash won't match
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: Many algorithms — hashes, checksums, PRNGs, CRCs — are specified in terms of fixed-width integers that wrap around on overflow. A 32-bit unsigned integer holds 0 through 2**32−1, and when a computation exceeds that the high bits are discarded, so the result is the true value modulo 2**32. In C, Java, and JavaScript this wraparound is automatic and invisible, so a reference implementation relies on it without ever mentioning it. Port that to Python and there is a trap: Python integers are arbitrary-precision, so they never overflow, never wrap, they just grow. A faithful-looking translation — hash = hash * 33 + byte with no wrap — computes a completely different number, because after a few bytes the true value has raced past 2**32 and Python keeps every digit while the reference kept only the low 32 bits. The two agree for the first few bytes and then diverge silently — no error, no warning — so a file hashed in C won't match the same file hashed in the ported Python, quietly breaking any cross-language dedup, cache key, or integrity check. The fix is to mask each step with & 0xFFFFFFFF, which reproduces the hardware wraparound; and because addition and multiplication commute with taking a remainder, masking every step equals taking the full arbitrary-precision value modulo 2**32 once. On a fixture hashing "portable" with DJB2 (seed 5381, multiplier 33), the unmasked Python hash grows to a 53-bit integer (7572805995910718) while the masked hash stays 32-bit (1263982142) and equals the unmasked value mod 2**32 — the value a C/Java/JS implementation returns.
eli5: Imagine a car odometer with only 6 digit-wheels. Drive far enough and it "rolls over" — after 999999 it clicks back to 000000, because there's no room for a 7th digit. A lot of number recipes (like the code that turns a word into a fingerprint number) are built assuming the odometer rolls over like that. Python's numbers, though, are like an odometer with unlimited wheels — it never rolls over, it just keeps adding digits. So if you copy the recipe into Python without telling it "only keep 6 wheels," you get a giant number instead of the rolled-over one, and it won't match the fingerprint any other program computed. The fix is to chop the number back down to 6 digits after every step, which is the same as rolling it over.
---

## Why this module

A whole class of algorithms — hashes, checksums, random-number generators — are written for a machine integer that quietly rolls over when it gets too big, and they lean on that rollover so hard that they never bother to write it down. It is just how C and Java and JavaScript integers behave. That silence is the trap: when you port the algorithm to Python, the one operation the reference depended on and never mentioned is exactly the one Python does not do, and nothing in the translated code looks wrong. It runs, it produces a number, and the number is silently incompatible with every other implementation of the same algorithm.

A 32-bit unsigned integer holds values 0 through 2**32−1, and when a computation exceeds that, the high bits are simply discarded: the result is the true value modulo 2**32. In C, Java, and JavaScript this wraparound is automatic and invisible, so an algorithm's reference implementation relies on it without ever mentioning it. The DJB2 string hash is exactly this: start at 5381, and for each byte compute hash = hash × 33 + byte, on a 32-bit unsigned integer, so every step silently wraps.

Port that to Python, whose integers are arbitrary-precision — they never overflow, never wrap, they just grow. A direct, faithful-looking translation computes a completely different number, because after a few bytes the true value has raced past 2**32 and Python keeps every digit while the reference kept only the low 32 bits. The two agree for the first few bytes and then diverge without any error, warning, or exception — the worst kind of failure: silent and cross-language. This module hashes the same string both ways.

**When you port an algorithm that assumes fixed-width integer overflow to a language with arbitrary-precision integers like Python, you must mask every operation to the width (& (2**width − 1)), because Python's ints never wrap on their own — and because arithmetic mod 2**width distributes over + and ×, masking each step is identical to taking the full-precision result modulo 2**width once.**

## Concepts

**The bug is a faithful-looking port that omits the wrap:** in Python this integer just keeps growing, past 32 bits and on forever.

```python filename=modules/teaching-and-portability/code/intoverflow-inter-01/intoverflow.py:53-58 COMPLETE
def djb2_unmasked(data, seed, mult):
    """Faithful-looking Python port with NO wrap -- the integer grows without bound (the bug)."""
    h = seed
    for byte in data:
        h = h * mult + byte
    return h
```

**The fix masks each step to the width**, discarding everything above the low 32 bits to reproduce the hardware wraparound.

```python filename=modules/teaching-and-portability/code/intoverflow-inter-01/intoverflow.py:61-66 COMPLETE
def djb2_masked(data, seed, mult, mask):
    """Portable version: mask each step to the width, reproducing fixed-width wraparound."""
    h = seed
    for byte in data:
        h = (h * mult + byte) & mask
    return h
```

<svg role="img" aria-label="A 32-bit-wide box holding the low bits of a number; the arithmetic produces a wider value whose high bits spill past the box edge and are discarded, leaving only the low 32 bits" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">fixed width keeps only the low 32 bits — the rest is discarded</text>
  <rect x="120" y="30" width="150" height="22" fill="none" stroke="var(--ink)"/>
  <text x="160" y="45" fill="var(--ink)" font-size="8">low 32 bits (kept)</text>
  <rect x="40" y="30" width="80" height="22" fill="none" stroke="var(--muted)" stroke-dasharray="2 2"/>
  <text x="52" y="45" fill="var(--muted)" font-size="7">high bits</text>
  <line x1="120" y1="26" x2="120" y2="56" stroke="var(--s2)"/><text x="96" y="66" fill="var(--s2)" font-size="6">width edge</text>
  <text x="46" y="78" fill="var(--s2)" font-size="7">✂ discarded on wrap</text>
  <text x="40" y="96" fill="var(--muted)" font-size="7">Python keeps the high bits (grows); the mask '& 0xFFFFFFFF' cuts them off</text>
</svg>
^ A fixed-width integer is a box that holds only the low 32 bits; arithmetic that overflows spills high bits past the box edge, where the hardware discards them — Python instead keeps those high bits and grows, so masking with & 0xFFFFFFFF is what restores the box.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/intoverflow-inter-01/intoverflow.py

The fixture is the string and DJB2's parameters.

```json filename=modules/teaching-and-portability/code/intoverflow-inter-01/intoverflow.json:3-7 COMPLETE
  "text": "portable",
  "seed": 5381,
  "multiplier": 33,
  "width_bits": 32
```

Run `--hash`.

```text filename=--hash
HASH — DJB2 of 'portable' (seed 5381, multiplier 33, 32-bit)
--------------------------------------------------------------------
  unmasked (Python, no wrap) = 7572805995910718
    ... that is 53 bits wide -- far above the 32-bit range 0..4294967295
  masked   (portable 32-bit) = 1263982142
    ... within 0..4294967295, the value a C/Java/JS implementation returns
--------------------------------------------------------------------
  same algorithm, different answers: the missing '& 0xFFFFFFFF' is the whole bug.
```

The two hashes of the same eight-character string are not close — they are different numbers of different magnitudes. The unmasked Python port returns 7572805995910718, a 53-bit integer, because it faithfully multiplied and added without ever discarding a high bit. The masked version returns 1263982142, which fits in 32 bits and is exactly the number a C, Java, or JavaScript implementation of DJB2 produces for "portable." If you hashed your files in a C tool and then wrote a Python script to check them, the unmasked port would report that every single file had changed, because not one of its hashes would match — and the code would look correct, because the multiply-add is the algorithm. The bug is not in what the code does; it is in the one thing it fails to do at the end of every step.

## Build

The divergence is not immediate — it begins the instant the running value first crosses 2**32.

```text filename=--trace
TRACE — byte by byte, where the unmasked value escapes the 32-bit range
--------------------------------------------------------------------------
  byte        unmasked h                masked h      over 2**32?
  'p'   177685                    177685        no
  'o'   5863716                   5863716       no
  'r'   193502742                 193502742     no
  't'   6385590602                2090623306    yes
  'a'   210724489963              271092459     yes
  'b'   6953908168877             356116653     yes
  'l'   229478969573049           3161915065    yes
  'e'   7572805995910718          1263982142    yes
```

Read the two columns down the string. For the first three bytes — 'p', 'o', 'r' — the running hash is still under 2**32, so masking changes nothing and the columns are identical. At the fourth byte, 't', the value reaches 6385590602, which is larger than 4294967295, and here the columns split: the masked column drops to 2090623306, which is 6385590602 − 2**32, exactly the wraparound; the unmasked column keeps the full value. From that byte on they never agree again, and the gap widens every step as the unmasked value compounds unbounded. This is why a short test string can mask the bug entirely: hash three or four characters and the two implementations may still match, so a too-small test passes and the incompatibility only shows up in production on real, longer inputs. The overflow is not an edge case you can hope to avoid; it is the normal operating condition of the algorithm, deliberately built in.

<svg role="img" aria-label="Two paths by byte position: the unmasked hash climbs steeply and unbounded past the 32-bit ceiling after the fourth byte, while the masked hash bounces below the ceiling, wrapping each time it would exceed it" viewBox="0 0 300 118" width="300" height="118">
  <text x="6" y="12" fill="var(--muted)" font-size="8">after byte 4 the paths split: unbounded growth vs wrap-in-range</text>
  <line x1="30" y1="40" x2="280" y2="40" stroke="var(--s2)" stroke-dasharray="3 2"/><text x="200" y="36" fill="var(--s2)" font-size="6">2**32 ceiling</text>
  <line x1="30" y1="100" x2="30" y2="24" stroke="var(--grid)"/>
  <line x1="30" y1="100" x2="280" y2="100" stroke="var(--grid)"/>
  <polyline points="45,98 75,96 105,92 135,80 165,60 195,44 225,32 255,22" fill="none" stroke="var(--s2)"/>
  <text x="222" y="20" fill="var(--s2)" font-size="6">unmasked →∞</text>
  <polyline points="45,98 75,96 105,92 135,66 165,88 195,80 225,52 255,72" fill="none" stroke="var(--s1)"/>
  <text x="200" y="92" fill="var(--s1)" font-size="6">masked (wraps, stays below)</text>
  <text x="40" y="112" fill="var(--muted)" font-size="6">p    o    r    t    a    b    l    e</text>
</svg>
^ Both paths track together through byte 3, then at byte 4 ('t') the unmasked hash breaks through the 2**32 ceiling and climbs without bound while the masked hash wraps back below it on every overflow — the same algorithm producing an unbounded number in Python and a bounded 32-bit one anywhere the wrap is honored.

```python filename=modules/teaching-and-portability/code/intoverflow-inter-01/intoverflow.py:115-122 COMPLETE
    unmasked_overflows = unmasked > mask
    print("  unmasked hash exceeds the %d-bit range = %s (%d bits wide)" % (bits, unmasked_overflows, unmasked.bit_length()))

    masked_fits = 0 <= masked <= mask
    print("  masked hash fits in %d bits = %s (%d)" % (bits, masked_fits, masked))

    they_differ = masked != unmasked
    print("  the two implementations give different values = %s (%d vs %d)" % (they_differ, masked, unmasked))
```

## Definition of done

The self-test pins the overflow, the fit, the divergence, and the identity that makes masking correct: masking each step equals one final modulo.

```python filename=modules/teaching-and-portability/code/intoverflow-inter-01/intoverflow.py:124-128 COMPLETE
    masking_equals_mod = masked == unmasked % modulus
    print("  masking each step == taking the full value mod 2**%d = %s (%d)" % (bits, masking_equals_mod, unmasked % modulus))

    reference = unmasked % modulus
    masked_matches_reference = masked == reference
    print("  masked hash matches the C/Java/JS reference value = %s (%d)" % (masked_matches_reference, reference))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the unmasked hash overflows and differs from the reference; the masked hash fits and equals value mod 2**width
----------------------------------------------------------------------------------------------------------------------------
  unmasked hash exceeds the 32-bit range = True (53 bits wide)
  masked hash fits in 32 bits = True (1263982142)
  the two implementations give different values = True (1263982142 vs 7572805995910718)
  masking each step == taking the full value mod 2**32 = True (1263982142)
  masked hash matches the C/Java/JS reference value = True (1263982142)
```

<svg role="img" aria-label="An equation showing the masked step-by-step hash equals the full unmasked value taken modulo 2 to the 32, both equal to 1263982142" viewBox="0 0 300 92" width="300" height="92">
  <text x="6" y="12" fill="var(--muted)" font-size="8">masking every step = one final modulo (both give the reference)</text>
  <rect x="14" y="30" width="86" height="30" fill="none" stroke="var(--s1)"/>
  <text x="24" y="42" fill="var(--s1)" font-size="6">mask each step</text>
  <text x="30" y="54" fill="var(--ink)" font-size="8">1263982142</text>
  <text x="108" y="50" fill="var(--muted)" font-size="10">=</text>
  <rect x="124" y="30" width="160" height="30" fill="none" stroke="var(--s2)"/>
  <text x="134" y="42" fill="var(--s2)" font-size="6">7572805995910718 mod 2^32</text>
  <text x="170" y="54" fill="var(--ink)" font-size="8">1263982142</text>
  <text x="14" y="80" fill="var(--muted)" font-size="6">because + and × commute with remainder — that is why the mask is exact</text>
</svg>
^ Masking the running hash at every step yields the identical value to computing the full arbitrary-precision hash and taking it modulo 2**32 once — both are 1263982142 — because addition and multiplication commute with taking a remainder, which is exactly why the per-step mask reproduces fixed-width wraparound.

**Done means the porting bug and its fix are proven on real values: the unmasked Python hash of "portable" is a 53-bit 7572805995910718 that no 32-bit implementation returns, while the masked hash 1263982142 fits in 32 bits and equals both the unmasked value mod 2**32 and the C/Java/JS reference — so a ported fixed-width algorithm must mask every step to the width, and that mask is provably the same as one final modulo.**

## Boss fight

Predict two ways this masking is done wrong even by people who know they need it, because the width, the sign, and where you put the mask all have to be right.

The first trap is signedness — masking gives you the right bits but not necessarily the right *interpretation* of them. A 32-bit value can be read as unsigned (0 to 2**32−1) or signed two's-complement (−2**31 to 2**31−1), and the same bit pattern is a different number under each. Java's `int` is signed and its `>>>` versus `>>` and its hash functions assume that; C's `unsigned` is not; JavaScript's bitwise operators coerce to signed 32-bit so `x | 0` can hand you a negative number where you expected a large positive one. So masking with & 0xFFFFFFFF makes your Python value unsigned, and if the reference you must match is producing a signed 32-bit result, you have the right low bits but the wrong sign convention, and the numbers still won't match. Porting fixed-width arithmetic means matching the width *and* the signedness of the reference, converting to two's-complement when the reference is signed (subtract 2**width if the top bit is set) — the mask is only half the contract. This is the same portability discipline as the integer-division module's sign-of-remainder problem: the low-level operator's convention, not just its arithmetic, has to be reproduced.

The second trap is masking too late, or not everywhere, so that Python's unbounded integers cause a different failure than a wrong final value. If you compute the whole thing unmasked and mask only at the end, you get the right answer for pure +/×/− (by the mod identity), but the intermediate values can grow to thousands of bits on a long input, which is slow and memory-heavy — Python will happily hash a gigabyte file into a million-bit integer before you reduce it, when masking each step keeps it at 32 bits throughout. Worse, the "mask once at the end" shortcut is *only* valid for operations that commute with modulo: addition, subtraction, multiplication. The moment the algorithm includes a right-shift, a division, or a comparison that depends on the value being truncated (many hashes and all CRCs mix in shifts and xors on the truncated register), the intermediate value must be masked *before* that operation or the shift sees phantom high bits and the result is wrong — mod does not commute with `>>`. So the safe rule is to mask after every step that could overflow, not once at the end: it is both faster and the only version that stays correct when the algorithm is more than plus and times.

**Match the reference's signedness, not just its width — & 0xFFFFFFFF gives unsigned low bits, so when the reference returns a signed 32-bit result you must convert to two's-complement or the sign still won't match; and mask after every overflowing step rather than once at the end, because the "mod once" shortcut holds only for +, −, and × (which commute with modulo) and breaks the instant a shift, divide, or truncation-dependent comparison enters, where an unmasked high bit changes the result.**

## External resources

Documentation on Python's arbitrary-precision integers and bitwise masking, and on fixed-width integer types in C, Java, and JavaScript (and NumPy's fixed-width dtypes, which *do* overflow) — why a ported hash or PRNG needs an explicit & (2**width − 1) and how two's-complement signedness interacts with it.

The DJB2 and FNV hash references and any CRC specification — canonical fixed-width algorithms whose reference implementations assume silent wraparound, useful for seeing exactly where the mask belongs and where shifts force per-step masking.

The companion integer-division and float-equality modules in this topic — all three are the same lesson that a language's default numeric behavior is part of an algorithm's contract, so a faithful-looking port that ignores overflow, remainder sign, or binary rounding silently computes a different, non-reproducible answer.
