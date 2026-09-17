---
id: codeunit-inter-01
title: String length is code points in one language and UTF-16 code units in another — an emoji counts as two
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: A Unicode code point is a character's number, and UTF-16 stores each code point as either one 16-bit code unit (for the Basic Multilingual Plane below U+10000) or a surrogate pair of two code units (for the astral planes at or above U+10000 — most emoji, some CJK, historic scripts). Python strings are sequences of code points, so len() counts code points, while JavaScript's .length and Java's .length() count UTF-16 code units — so the same string has a different length in each. A string of h, i, an emoji (U+1F600), and x is 4 code points and 5 UTF-16 code units, because the emoji is one code point encoded as two units; a test that expects length 4 passes in Python and fails in JavaScript on the same text, and a length limit enforced in one unit admits or rejects strings the other would not (a limit of 4 fits by code points but not by UTF-16 units). Worse than a mismatched count, indexing or slicing by UTF-16 units can land between the two halves of a surrogate pair, leaving a lone high surrogate — half a character, which is not a valid character at all: truncating this string to 3 UTF-16 units keeps h and i and then the high surrogate of the emoji, a broken fragment, while truncating to 3 code points keeps h, i, and the whole emoji. The rule: "length" and "the i-th character" are ambiguous across languages because they may mean code points or code units, and any limit or slice that must be portable — or must never split a character — has to be defined in code points (or graphemes), not in whatever unit the local string type happens to use.
eli5: Think of a word made of letter-tiles, where most letters are one tile but a few special ones (like emoji) are actually two tiles snapped together to make a single picture. If you count "how many tiles" you get a bigger number than "how many letters," and different computers count different ways — some count letters, some count tiles. That's already confusing when you compare lengths. But it gets worse if you cut the word to a certain number of tiles: you might slice right between the two tiles of a snapped-together letter, leaving half a picture that isn't any letter at all. Cutting by whole letters never does that. So if you must chop a word safely, count letters, not tiles.
---

## Why this module

"How long is this string" feels like the most unambiguous question in programming, and it is a trap, because the answer depends on the language's string type. The same text is one length in Python, another in JavaScript, and the difference is not a bug in either — it is two different, both-correct definitions of "length."

This bites in exactly the places that must agree: a character limit validated on a JavaScript client and re-checked on a Python server, a database column sized in one unit and filled from code that counted in another, a preview that truncates a message. When those disagree, valid input is rejected, stored text is cut wrong, and — worst — a character can be sliced in half into something that is not a character at all.

**"Length" and "the i-th character" mean code points in some languages and UTF-16 code units in others, so any limit or slice that must be portable cannot be left to the local definition.**

## Concepts

A code point is the number Unicode assigns to a character. Code points below U+10000 form the Basic Multilingual Plane and cover almost all everyday text. Code points at or above U+10000 — the astral planes — include most emoji, less common CJK characters, and historic scripts.

UTF-16 encodes a code point in one or two 16-bit code units. A BMP code point is one unit. An astral code point is a surrogate pair: two units, a high surrogate followed by a low surrogate, which together encode the one character. Neither surrogate is a valid character on its own; only the pair is.

Now the language split. Python 3 strings are sequences of code points, so len() and indexing are in code points — an emoji is length 1. JavaScript strings and Java strings are sequences of UTF-16 code units, so .length and .length() and charAt are in code units — an emoji is length 2. This is not a preference; it is what the string type is made of. The same text genuinely has two lengths, and both are right for their own unit.

The count mismatch alone causes real failures: a "max 100 characters" limit is 100 code points in one place and 100 code units in another, so a message full of emoji passes one check and fails the other. But the sharper failure is splitting. Indexing or slicing by UTF-16 units can stop between a high surrogate and its low surrogate, keeping half the pair. That half is a lone surrogate — not the emoji, not any character, an invalid fragment that downstream code may reject, mojibake, or crash on. Truncation by code points cannot do this, because a code point is atomic: you keep the whole character or none of it.

**A code point is atomic; a UTF-16 code unit can be half of one, so counting and slicing in code units both mismatch code-point counts and risk cutting a character in two.**

<svg role="img" aria-label="The same one-emoji string measured by two languages. Python len returns 1 (code points). JavaScript and Java length return 2 (UTF-16 code units)." viewBox="0 0 320 130">
<rect x="0" y="0" width="320" height="130" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">one emoji, two answers to "how long?"</text>
<text x="20" y="52" fill="var(--s2)" font-size="11">Python len()</text>
<text x="180" y="52" fill="var(--s2)" font-size="12">1</text>
<text x="210" y="52" fill="var(--muted)" font-size="9">(code points)</text>
<text x="20" y="90" fill="var(--s1)" font-size="11">JS / Java .length</text>
<text x="180" y="90" fill="var(--s1)" font-size="12">2</text>
<text x="210" y="90" fill="var(--muted)" font-size="9">(UTF-16 code units)</text>
<text x="20" y="116" fill="var(--ink)" font-size="9">same string, same emoji, neither language is wrong</text>
</svg>
^ The disagreement is not a bug in either language; it is two definitions of length, code points versus code units, applied to a character that is one of the first and two of the second.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/teaching-and-portability/code/codeunit-inter-01/codeunit.py

The fixture is the string h, i, the emoji U+1F600, x, given as code points.

```json filename=modules/teaching-and-portability/code/codeunit-inter-01/codeunit.json:3-6 COMPLETE
  "code_points": [104, 105, 128512, 120],
  "labels": ["h", "i", "U+1F600 emoji", "x"],
  "limit": 4,
  "truncate_units": 3
```

The two length functions differ only in how they count the astral code point.

```python filename=modules/teaching-and-portability/code/codeunit-inter-01/codeunit.py:35-37 COMPLETE
def utf16_len(cps):
    """Length in UTF-16 code units -- what JavaScript's .length and Java's .length() return."""
    return sum(2 if cp >= 0x10000 else 1 for cp in cps)
```

```python filename=modules/teaching-and-portability/code/codeunit-inter-01/codeunit.py:40-49 COMPLETE
def unit_list(cps):
    """The UTF-16 code units: an astral code point becomes a high ('H') then low ('L') surrogate."""
    units = []
    for cp in cps:
        if cp >= 0x10000:
            units.append(("H", cp))
            units.append(("L", cp))
        else:
            units.append(("C", cp))
    return units
```

```text filename=codeunit.py --measure
MEASURE — string: h i U+1F600 emoji x
----------------------------------------------------------------
  code-point length (Python len) = 4
  UTF-16 length (JS/Java .length) = 5
  limit 4: fits by code points? True   fits by UTF-16 units? False
----------------------------------------------------------------
  the same string is two different lengths; a limit judges it differently under each
```

Four code points, five UTF-16 units — the emoji is the one character that counts as two. A limit of 4 accepts the string in Python (4 ≤ 4) and rejects it in JavaScript (5 > 4), so the exact same input passes client-side validation and fails server-side, or vice versa, with no bug in either checker.

<svg role="img" aria-label="The four characters h, i, emoji, x. Each of h, i, x is one box (one code unit). The emoji is one code point drawn as two boxes labeled high surrogate and low surrogate. Total: 4 code points, 5 boxes." viewBox="0 0 320 130">
<rect x="0" y="0" width="320" height="130" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">4 code points, 5 UTF-16 units</text>
<rect x="30" y="40" width="34" height="30" fill="none" stroke="var(--line)"></rect>
<text x="42" y="60" fill="var(--ink)" font-size="12">h</text>
<rect x="70" y="40" width="34" height="30" fill="none" stroke="var(--line)"></rect>
<text x="82" y="60" fill="var(--ink)" font-size="12">i</text>
<rect x="110" y="40" width="34" height="30" fill="var(--s1)"></rect>
<rect x="144" y="40" width="34" height="30" fill="var(--s1)"></rect>
<text x="112" y="88" fill="var(--s1)" font-size="8">high sur.</text>
<text x="146" y="88" fill="var(--s1)" font-size="8">low sur.</text>
<text x="116" y="104" fill="var(--muted)" font-size="8">one emoji (U+1F600)</text>
<rect x="184" y="40" width="34" height="30" fill="none" stroke="var(--line)"></rect>
<text x="196" y="60" fill="var(--ink)" font-size="12">x</text>
</svg>
^ The emoji is a single code point but two adjacent UTF-16 boxes; counting boxes gives 5, counting characters gives 4, and the extra box is the surrogate pair.

## Build

Truncating by units can cut between the surrogate halves; truncating by code points cannot.

```python filename=modules/teaching-and-portability/code/codeunit-inter-01/codeunit.py:52-64 COMPLETE
def truncate_by_units(cps, n):
    """Keep the first n UTF-16 units and rebuild; a trailing lone high surrogate means a split character."""
    u = unit_list(cps)[:n]
    broken = len(u) > 0 and u[-1][0] == "H"
    out, i = [], 0
    while i < len(u):
        if u[i][0] == "C":
            out.append(u[i][1]); i += 1
        elif u[i][0] == "H" and i + 1 < len(u) and u[i + 1][0] == "L":
            out.append(u[i][1]); i += 2
        else:
            i += 1  # lone surrogate: dropped, the split is recorded in `broken`
    return out, broken
```

```text filename=codeunit.py --truncate
TRUNCATE — cut to 3 units vs 3 code points
----------------------------------------------------------------
  by UTF-16 units: kept code points [104, 105]  split a character? True
  by code points : kept code points [104, 105, 128512]  split a character? False
----------------------------------------------------------------
  cutting at a UTF-16 unit boundary can land inside a surrogate pair; code points cannot
```

Cutting to 3 UTF-16 units keeps h and i and then the emoji's high surrogate alone — a split character, so the recovered text is just "hi" plus a broken fragment. Cutting to 3 code points keeps h, i, and the whole emoji. Same "3", two different results, and only the unit cut is unsafe.

<svg role="img" aria-label="Truncating the string at 3 UTF-16 units. The cut falls after h, i, and the high surrogate, leaving the low surrogate behind, so the emoji is split into a lone half." viewBox="0 0 320 130">
<rect x="0" y="0" width="320" height="130" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">cut at 3 UTF-16 units splits the emoji</text>
<rect x="30" y="44" width="34" height="30" fill="none" stroke="var(--line)"></rect>
<text x="42" y="64" fill="var(--ink)" font-size="12">h</text>
<rect x="70" y="44" width="34" height="30" fill="none" stroke="var(--line)"></rect>
<text x="82" y="64" fill="var(--ink)" font-size="12">i</text>
<rect x="110" y="44" width="34" height="30" fill="var(--s1)"></rect>
<text x="112" y="90" fill="var(--s1)" font-size="8">high (kept)</text>
<rect x="144" y="44" width="34" height="30" fill="none" stroke="var(--muted)" stroke-dasharray="3 2"></rect>
<text x="146" y="90" fill="var(--muted)" font-size="8">low (cut)</text>
<line x1="144" y1="34" x2="144" y2="84" stroke="var(--ink)"></line>
<text x="150" y="30" fill="var(--ink)" font-size="9">cut here</text>
</svg>
^ The cut line falls between the emoji's two surrogates, so the kept side ends in a lone high surrogate — half a character that is no character.

The self-test states the mismatch, the limit disagreement, and the split.

```python filename=modules/teaching-and-portability/code/codeunit-inter-01/codeunit.py:109-117 COMPLETE
    lengths_differ = cpl != u16
    print("  code-point length differs from UTF-16 length = %s (%d vs %d)" % (lengths_differ, cpl, u16))

    astral = sum(1 for cp in cps if cp >= 0x10000)
    astral_adds_units = (u16 - cpl) == astral
    print("  the extra units equal the number of astral characters = %s (%d extra, %d astral)" % (astral_adds_units, u16 - cpl, astral))

    limit_disagrees = (cpl <= limit) != (u16 <= limit)
    print("  a limit of %d admits the string by one measure but not the other = %s (cp %s, u16 %s)" % (limit, limit_disagrees, cpl <= limit, u16 <= limit))
```

```text filename=codeunit.py --check
SELF-TEST — the two lengths differ because the astral character is two UTF-16 units, a unit-based limit disagrees with a code-point limit, and unit truncation splits a character while code-point truncation does not
----------------------------------------------------------------------------------------------------------------
  code-point length differs from UTF-16 length = True (4 vs 5)
  the extra units equal the number of astral characters = True (1 extra, 1 astral)
  a limit of 4 admits the string by one measure but not the other = True (cp True, u16 False)
  truncating to 3 UTF-16 units splits a character = True
  truncating to 3 code points never splits a character = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  lengths_differ=True  astral_adds_units=True  limit_disagrees=True  unit_trunc_splits=True  codepoint_trunc_safe=True
```

**limit_disagrees is the interop bug in one line: the same "max length" number, enforced in code units on one side and code points on the other, accepts and rejects the same string.**

## Definition of done

You can explain what a code point and a UTF-16 code unit are, and why an astral character (U+10000 and above) is one code point but two code units.

You can say which common languages count which — Python code points, JavaScript and Java UTF-16 code units — and why the same string has two legitimate lengths.

You can describe both failure modes: a length limit that disagrees across a code-unit and a code-point boundary, and a slice by code units that splits a surrogate pair into an invalid lone surrogate.

You can state the fix for anything that must be portable or must not split a character: define the limit or slice in code points (or graphemes for user-perceived characters), not in the local string type's unit.

## Boss fight

Your app enforces a 280-character post limit in the browser (JavaScript) and re-validates it on the server (Python). Users report that some posts full of emoji are accepted by the browser but rejected by the server as "too long," and occasionally a truncated preview shows a broken box at the end.

First: explain both symptoms in terms of this module. Why does an emoji-heavy post pass the browser's 280 check but fail the server's, and what is the broken box at the end of the truncated preview?

Then: you must make the two checks agree. Decide which unit the limit should be defined in and why, and describe what each side must change so that "280" means the same thing in the browser and on the server — including what JavaScript has to do differently, since its native .length is the wrong unit.

Finally: even a code-point limit does not match what a user thinks of as "one character," because a single perceived character (a family emoji, a flag, an accented letter) can be several code points joined together. Explain when you would need to count grapheme clusters instead of code points, and why truncating at a code-point boundary — though it never splits a surrogate pair — can still break a user-perceived character.

## External resources

The Unicode standard's sections on encoding forms and surrogate pairs define code points, code units, and the astral planes precisely, and are the authority for why an astral character is two UTF-16 units.

Language references make the split explicit: MDN documents String.prototype.length as a count of UTF-16 code units (with String.prototype codePointAt and the iterator for code points), while Python's data model documents str as a sequence of code points — reading both side by side is the fastest way to see why the same string has two lengths.
