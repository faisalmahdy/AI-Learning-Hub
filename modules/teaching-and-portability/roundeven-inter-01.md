---
id: roundeven-inter-01
title: Round half to even, not half up — the default rounding rule is not the schoolbook one, and it keeps sums unbiased
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: Rounding a value exactly halfway between two integers — a tie like 2.5 — has no correct answer, only a convention. The convention almost everyone learned is round-half-up: on a tie, go away from zero (2.5 → 3), implemented as "add 0.5 and truncate." The convention almost every computing platform actually uses is round-half-to-even (banker's rounding): a tie goes to whichever neighbor is even (2.5 → 2, 3.5 → 4). Python's round(), the IEEE-754 default, and most spreadsheet and database engines round half to even, so the rule in your head and the rule in your code disagree on every tie. The reason for the default is bias: round-half-up pushes every tie the same direction, so summing a rounded column drifts the total upward, while round-half-to-even sends ties up and down in balance so the rounded sum stays centered on the true sum. On the six ties 0.5–5.5 (true sum 18.0), half-even gives [0,2,2,4,4,6] summing to exactly 18, while half-up gives [1,2,3,4,5,6] summing to 21 — inflated by 0.5 per tie. A separate trap: most decimals are not exact in binary, so 2.675 is stored as 2.67499999…, below the tie, and round(2.675, 2) is 2.67, not the 2.68 you expect.
eli5: When a number lands exactly in the middle — like 2.5, right between 2 and 3 — you have to pick a way to break the tie. In school you learned "always round the half up," so 2.5 becomes 3. But most computers use a different rule: send the half to the nearest EVEN number, so 2.5 becomes 2 and 3.5 becomes 4. Why? If you always round halves up and then add a whole column of them, the total comes out a little too big, because every tie pushed the same way. Sending them to even makes half go up and half go down, so the errors cancel and the total stays honest. And a sneaky bonus problem: some decimals can't be stored exactly, so a number that looks like a perfect half (like 2.675) is really a hair less, and the computer rounds it down when you expected up.
---

## Why this module

Rounding feels too simple to have a bug, so almost no one checks which rule their language uses — and the rule is not the one they were taught. On every value that lands on a boundary, code that assumes "round half up" quietly disagrees with the platform, and the disagreement shows up as totals that do not reconcile.

Rounding a value that sits exactly halfway between two integers — a tie, like 2.5 — has no correct answer; it has a convention. The convention almost everyone learned in school is round-half-up: on a tie, go away from zero (2.5 → 3), which you implement as "add 0.5 and truncate." The convention almost every computing platform actually uses is different: round-half-to-even, also called banker's rounding, where a tie goes to whichever neighbor is even (2.5 → 2, 3.5 → 4). Python's built-in round(), the IEEE-754 floating-point default, and most spreadsheet and database engines round half to even. So the rule in your head and the rule in your code disagree on every tie, and code that assumes half-up is wrong exactly when a value lands on the boundary.

The reason the default is half-to-even is not perversity, it is bias. Round-half-up pushes every tie in the same direction, so if you round a column of numbers and add them, the ties all nudge the total upward and the rounded sum drifts above the true sum — a systematic error that grows with the number of ties. Round-half-to-even sends ties up and down in balance, so over a symmetric set of ties the over- and under-shoots cancel and the rounded sum stays centered on the truth. That is why finance and statistics default to it. And a separate trap hides underneath: most decimals are not stored exactly in binary, so a number that *looks* like a tie may not be one — 2.675 is stored as 2.67499999…, below the tie, so it rounds down. This module rounds six ties both ways and springs the repr trap.

**A tie has no correct rounding, only a convention, and the platform default is round-half-to-even (not the schoolbook round-half-up) precisely because sending ties to even keeps a rounded sum unbiased — so assuming half-up disagrees with your tools on every boundary value, and binary representation can mean the boundary value was never a tie at all.**

## Concepts

**Round-half-to-even** rounds to the nearest integer and breaks a tie toward the even neighbor. It is exactly what Python's `round()` does, and what IEEE-754 arithmetic does by default.

```python filename=modules/teaching-and-portability/code/roundeven-inter-01/roundeven.py:47-49 COMPLETE
def round_half_even(x):
    """Round to the nearest integer, ties to the even neighbor -- Python's built-in round() and the IEEE-754 default."""
    return round(x)
```

**Round-half-up** is the schoolbook rule: add 0.5 and truncate, which sends every tie away from zero. It is what most people expect and what most hand-written rounding does — and it disagrees with the default on every tie.

```python filename=modules/teaching-and-portability/code/roundeven-inter-01/roundeven.py:52-54 COMPLETE
def round_half_up(x):
    """Round to the nearest integer, ties away from zero -- the schoolbook rule: add 0.5 and truncate."""
    return math.floor(x + 0.5)
```

<svg role="img" aria-label="Number lines showing the tie 2.5 rounding to 2 under half-to-even and to 3 under half-up, and 3.5 rounding to 4 under both" viewBox="0 0 300 118" width="300" height="118">
  <text x="6" y="12" fill="var(--muted)" font-size="8">a tie goes to the even neighbor (round-half-to-even)</text>
  <g transform="translate(20,34)">
  <line x1="0" y1="0" x2="120" y2="0" stroke="var(--line)"/>
  <text x="-2" y="14" fill="var(--muted)" font-size="7">2</text><text x="58" y="14" fill="var(--muted)" font-size="7">2.5</text><text x="116" y="14" fill="var(--muted)" font-size="7">3</text>
  <circle cx="60" cy="0" r="3" fill="var(--ink)"/>
  <line x1="60" y1="-4" x2="4" y2="-4" stroke="var(--s1)"/><text x="8" y="-8" fill="var(--s1)" font-size="7">even → 2</text>
  <line x1="60" y1="4" x2="116" y2="4" stroke="var(--s2)"/><text x="70" y="18" fill="var(--s2)" font-size="7">up → 3</text>
  </g>
  <g transform="translate(160,34)">
  <line x1="0" y1="0" x2="120" y2="0" stroke="var(--line)"/>
  <text x="-2" y="14" fill="var(--muted)" font-size="7">3</text><text x="58" y="14" fill="var(--muted)" font-size="7">3.5</text><text x="116" y="14" fill="var(--muted)" font-size="7">4</text>
  <circle cx="60" cy="0" r="3" fill="var(--ink)"/>
  <line x1="60" y1="-4" x2="116" y2="-4" stroke="var(--s1)"/><text x="70" y="-8" fill="var(--s1)" font-size="7">even → 4</text>
  </g>
  <text x="20" y="86" fill="var(--muted)" font-size="8">2.5 → 2 sends the tie down, 3.5 → 4 sends it up —</text>
  <text x="20" y="100" fill="var(--muted)" font-size="8">so over a run of ties the up- and down-rounds balance out</text>
</svg>
^ Round-half-to-even sends 2.5 down to the even 2 and 3.5 up to the even 4, so consecutive ties alternate direction; round-half-up would send both away from zero (2.5 → 3, 3.5 → 4), always the same way.

**Half-even breaks ties toward the even neighbor and half-up breaks them away from zero, so the two rules give different answers on every tie — and because half-up always pushes the same direction, it is the biased one.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/roundeven-inter-01/roundeven.py

The fixture is six exact ties and one repr-trap value.

```json filename=modules/teaching-and-portability/code/roundeven-inter-01/roundeven.json:3-4 COMPLETE
  "ties": [0.5, 1.5, 2.5, 3.5, 4.5, 5.5],
  "repr_trap": {"value": 2.675, "places": 2, "naive_expected": 2.68}
```

Run `--ties` to round all six both ways and sum them.

```text filename=--ties
TIES — round-half-to-even vs round-half-up on exact halves
--------------------------------------------------------
  tie    half-even   half-up
  0.5    0           1
  1.5    2           2
  2.5    2           3
  3.5    4           4
  4.5    4           5
  5.5    6           6
--------------------------------------------------------
  true sum       = 18.0
  half-even sum  = 18   (matches the true sum -- unbiased)
  half-up sum    = 21   (inflated by 3 = 0.5 x 6 ties -- biased up)
```

Read the two columns. Under half-even, 0.5 → 0, 1.5 → 2, 2.5 → 2, 3.5 → 4 — each tie lands on the even neighbor, so they alternate down, up, down, up. Under half-up every tie goes up: 0.5 → 1, 2.5 → 3, 4.5 → 5. Now the sums, which is where it bites: the true total of the six ties is 18.0, the half-even rounded total is exactly 18, and the half-up total is 21. That gap of 3 is not noise — it is precisely 0.5 for each of the six ties, all pushed the same way. This is the entire argument for the default in one line: if these were six line items on an invoice, or six per-unit prices, or six sub-totals in a report, rounding them half-up and adding would over-count by a predictable, accumulating amount, while half-even's ups and downs cancel and the rounded total stays honest. The bias is not random error that averages out with more data; it is a constant lean that grows with the count of ties.

<svg role="img" aria-label="Two rounded sums against the true sum of 18: half-even lands on 18, half-up lands on 21, over by 3" viewBox="0 0 300 112" width="300" height="112">
  <text x="6" y="12" fill="var(--muted)" font-size="8">half-even sum stays at the true 18; half-up drifts to 21</text>
  <line x1="40" y1="92" x2="290" y2="92" stroke="var(--line)"/>
  <line x1="40" y1="34" x2="290" y2="34" stroke="var(--ink)" stroke-dasharray="3 2"/>
  <text x="292" y="37" fill="var(--muted)" font-size="7" text-anchor="start"></text>
  <text x="36" y="30" fill="var(--muted)" font-size="7" text-anchor="end">true 18</text>
  <g transform="translate(70,0)">
  <rect x="0" y="34" width="44" height="58" fill="var(--s1)"/><text x="2" y="104" fill="var(--muted)" font-size="7">half-even</text><text x="12" y="30" fill="var(--muted)" font-size="7">18</text>
  </g>
  <g transform="translate(190,0)">
  <rect x="0" y="24" width="44" height="68" fill="var(--s2)"/><text x="6" y="104" fill="var(--muted)" font-size="7">half-up</text><text x="12" y="20" fill="var(--muted)" font-size="7">21</text>
  </g>
  <line x1="234" y1="24" x2="234" y2="34" stroke="var(--ink)"/><text x="238" y="30" fill="var(--muted)" font-size="7">+3</text>
</svg>
^ The half-even rounded sum sits exactly on the true total of 18, while the half-up rounded sum overshoots to 21 — the +3 being 0.5 of accumulated upward bias for each of the six ties.

## Build

The second hazard does not need a rounding rule to be wrong — it is that the value handed to the rule was never the tie it looked like. Run `--repr`.

```text filename=--repr
REPR — a decimal that looks like a tie but is not one in binary
------------------------------------------------------------
  value as written      = 2.675
  value actually stored = 2.67499999999999982236
  you expect round(2.675, 2) = 2.68 (round the .5 up)
  Python gives round(2.675, 2) = 2.67
------------------------------------------------------------
  the stored double is below 2.675, so it was never a tie -- it rounds down.
```

You write `2.675`, a clean two-and-a-half-thousandths, and expect two-place rounding to push the trailing 5 up to 2.68. But 2.675 cannot be represented exactly in binary floating point; the nearest double is 2.67499999999999982…, a hair *below* 2.675. So when `round(2.675, 2)` looks at the value, it does not see a tie at all — it sees a number just under the halfway point, and rounds it down to 2.67. No rounding rule, half-even or half-up, would give 2.68 here, because the tie the decimal implied never existed in the stored number. This is why the repr trap is worse than the half-even surprise: the half-even rule is at least predictable once you know it, but the repr trap makes rounding depend on the invisible binary value behind a decimal literal, and it moves with the specific number. The self-test asserts the surprising result directly.

```python filename=modules/teaching-and-portability/code/roundeven-inter-01/roundeven.py:114-115 COMPLETE
    repr_trap_rounds_down = round(v, places) != expected
    print("  round(%s, %d) is not the expected %s (binary repr trap) = %s (got %s)" % (v, places, expected, repr_trap_rounds_down, round(v, places)))
```

<svg role="img" aria-label="A zoom on the number line near 2.675 showing the stored double sitting just below the 2.675 tie point, so it rounds down to 2.67 instead of up to 2.68" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the stored double for 2.675 sits just below the tie</text>
  <line x1="30" y1="52" x2="290" y2="52" stroke="var(--line)"/>
  <text x="26" y="68" fill="var(--muted)" font-size="7" text-anchor="end">2.67</text><text x="280" y="68" fill="var(--muted)" font-size="7">2.68</text>
  <line x1="160" y1="40" x2="160" y2="64" stroke="var(--muted)" stroke-dasharray="2 2"/><text x="140" y="34" fill="var(--muted)" font-size="7">2.675 tie</text>
  <circle cx="154" cy="52" r="3" fill="var(--s2)"/><text x="96" y="86" fill="var(--s2)" font-size="7">stored 2.67499…982</text>
  <line x1="154" y1="52" x2="40" y2="52" stroke="var(--s1)"/><text x="60" y="48" fill="var(--s1)" font-size="7">rounds down → 2.67</text>
</svg>
^ Because the nearest double to 2.675 lies just left of the 2.675 tie point, rounding sees a value below the halfway mark and goes down to 2.67 — the decimal looked like a tie, but the number actually stored was not one.

## Definition of done

The self-test pins both rules on the ties, the unbiased versus biased sums, and the repr trap.

```python filename=modules/teaching-and-portability/code/roundeven-inter-01/roundeven.py:99-108 COMPLETE
    ties_go_even = even_rounded == [0, 2, 2, 4, 4, 6]
    print("  round-half-to-even sends each tie to its even neighbor = %s (%s)" % (ties_go_even, even_rounded))

    up_rounded = [round_half_up(x) for x in ties]
    ties_go_up = up_rounded == [1, 2, 3, 4, 5, 6]
    print("  round-half-up sends every tie away from zero = %s (%s)" % (ties_go_up, up_rounded))

    ts = true_sum(ties)
    half_even_preserves_sum = sum(even_rounded) == ts
    print("  the half-even rounded sum equals the true sum = %s (%d == %.1f)" % (half_even_preserves_sum, sum(even_rounded), ts))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — half-even sends ties to even and preserves the sum; half-up biases the sum upward; the repr trap rounds 2.675 down
----------------------------------------------------------------------------------------------------------------------------
  round-half-to-even sends each tie to its even neighbor = True ([0, 2, 2, 4, 4, 6])
  round-half-up sends every tie away from zero = True ([1, 2, 3, 4, 5, 6])
  the half-even rounded sum equals the true sum = True (18 == 18.0)
  the half-up rounded sum is inflated by 0.5 per tie = True (21 == 18.0 + 0.5x6)
  round(2.675, 2) is not the expected 2.68 (binary repr trap) = True (got 2.67)
```

**Done means the convention and its consequences are proven on real values: round-half-to-even sends the six ties to [0,2,2,4,4,6] and round-half-up to [1,2,3,4,5,6], the half-even sum equals the true 18 while the half-up sum is 21 (inflated by 0.5 per tie), and round(2.675, 2) is 2.67 — so the default rule is unbiased, the schoolbook rule is not, and a decimal that looks like a tie need not be one.**

## Boss fight

Predict where this actually costs you, because the rounding rule and the binary-repr trap combine into failures that "just round it" never anticipates.

The first trap is cross-platform and cross-language disagreement, which turns rounding into a portability bug. Not every environment rounds half to even: many languages' default rounding, older spreadsheet functions, and hand-written `int(x + 0.5)` use half-up, while Python, IEEE-754 hardware, and most databases use half-even — so the *same* dataset rounded in two systems can produce totals that differ by a few cents, and a reconciliation job that expects them to match will flag phantom discrepancies. The fix when the exact rule matters is to stop using binary floating point for it at all: use a decimal type (Python's `decimal.Decimal`) that represents 2.675 exactly and lets you *name* the rounding mode explicitly — `ROUND_HALF_UP`, `ROUND_HALF_EVEN`, `ROUND_DOWN` — so the behavior is a stated policy rather than an inherited default that varies by platform. Money, tax, and anything audited belongs in decimal with an explicit mode, never in a float with whatever `round()` happens to do.

The second trap is that rounding is not associative or composable, so *when* and *how many times* you round changes the answer. Rounding each item and then summing gives a different total than summing exactly and rounding once at the end (the classic "penny off" in invoices), and rounding an already-rounded number — round to 2 places, then someone rounds that to 1 — can double-round a value across a boundary and land two steps from the truth. The discipline is to carry full precision through every intermediate step and round exactly once, at the moment of presentation, with a stated mode; every earlier round is a lossy commitment you cannot take back. And because the repr trap means a decimal literal may already be slightly off before you round it, the only way to make rounding behavior fully predictable is to keep the value exact (as a decimal or as scaled integers — cents, not dollars) from the point of entry, so the number the rounding rule sees is the number you actually wrote.

**The rounding rule is a policy, not a fact: platforms disagree (half-even vs half-up), floats cannot even represent many decimals exactly, and rounding is not composable — so for anything that must reconcile or be audited, use an exact type (decimal or scaled integers) with an explicitly named rounding mode, carry full precision through intermediates, and round once at presentation rather than trusting the language default.**

## External resources

Python's documentation for the built-in round() and the decimal module — round()'s round-half-to-even behavior for floats, the note that binary floats make some decimals inexact, and decimal.Decimal with its explicit ROUND_HALF_UP / ROUND_HALF_EVEN / ROUND_DOWN modes.

The IEEE-754 standard's rounding modes and any "What Every Computer Scientist Should Know About Floating-Point Arithmetic" reference — why round-to-nearest-even is the default and how binary representation makes a decimal like 2.675 non-exact.

The companion integer-division and locale-number modules in this topic — together they cover how a value's numeric result depends on conventions you did not choose: which way division rounds, how a locale formats a number, and which way a tie rounds.
