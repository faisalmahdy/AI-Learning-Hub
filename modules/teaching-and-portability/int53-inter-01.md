---
id: int53-inter-01
title: Carry a large integer ID as a string — past 2^53 it loses precision through any 64-bit float
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: A double has a 52-bit mantissa plus one implicit leading bit, so it represents every integer exactly up to 2^53 = 9007199254740992 and no further; above that the representable values step by 2, then 4, then 8, so most integers in the range are not representable and snap to the nearest one that is. This bites because so many pipes are secretly doubles: JavaScript has one number type and it is a double, so JSON.parse turns a big integer ID into a double; spreadsheets store numbers as doubles; a float column does too. Send a 64-bit ID — a snowflake/Twitter ID, a Discord ID, a bigint primary key — through any of them and it comes back changed, and nothing raises, because the number is a valid number, just the wrong one, so a lookup by it hits the wrong row or none. On the fixture, 42 and 9007199254740991 (2^53 − 1, JavaScript's Number.MAX_SAFE_INTEGER) survive the round trip, 2^53 itself is still exact, but 9007199254740993 (2^53 + 1) comes back as 9007199254740992, and two 19-digit snowflake IDs that differ by one — 1387496749436723201 and 1387496749436723202 — both come back as 1387496749436723200, so they collide and become indistinguishable. The fix is never to let a large integer ID travel as a JSON or JavaScript number: carry it as a string, whose digits are just text and survive any parser, or decode with a parser that produces a big integer or a decimal. The rule: an integer ID is not a quantity to compute on, it is an identity to preserve, and the moment it exceeds 2^53 a double silently stops preserving it.
eli5: Computers can hold whole numbers perfectly only up to a certain size — about nine quadrillion. Below that, every number has its own exact slot. Above it, the slots start skipping: only every second number has a slot, then every fourth, and any number in between gets bumped to the nearest slot. That is fine for measurements, where a hair of rounding does not matter, but an ID is not a measurement — it is a name. If your account number gets bumped to the nearest slot, it is now someone else's account number, or nobody's. And because whole runs of numbers share one slot, two different people's IDs can land on the same slot and become the same name. The safe move is to treat a big ID as text — a string of digits — because text never gets bumped; it is only numbers that do.
---

## Why this module

An integer ID feels like the safest thing in a system. It is just a number; numbers are exact; what could go wrong. And for a long time nothing does, because early IDs are small and every small integer has an exact home in every numeric type you pass it through.

Then the ID counter climbs past nine quadrillion — or you adopt snowflake IDs, which start there — and a boundary is crossed that no type declares and no error announces. Above it, the numeric type you have been trusting can no longer hold every integer, so it holds the nearest one it can. Your ID comes back as a neighbor. The system keeps running, looking up the wrong rows.

**An integer ID is an identity to preserve, not a quantity to compute on, and a 64-bit float silently stops preserving it above 2^53.**

## Concepts

A 64-bit IEEE-754 float — a double — spends its bits on a sign, an exponent, and a 52-bit mantissa. With the mantissa's implicit leading bit that is 53 bits of significand, which means it can name every integer from 0 up to 2^53 exactly: 2^53 distinct integers, each with its own bit pattern. At 2^53 = 9007199254740992 it runs out. Past that, the exponent has to grow, and a larger exponent means the representable values are spaced two apart, then four, then eight — the same 53 bits of precision, sliding up a scale where the gaps between representable numbers are now bigger than one.

So an integer above 2^53 that is not one of the representable values has nowhere exact to land, and the double stores the nearest representable neighbor. This is not a bug in any one library; it is the definition of the type.

The reason it reaches your IDs is that doubles hide inside formats you would not suspect. JavaScript's only number type is the double, so JSON.parse decodes every JSON number — including a bigint ID — as a double. Spreadsheets hold numbers as doubles. A float or REAL database column does too. Any of these in the path between where an ID is written and where it is read will quietly round it.

Two consequences, both silent. A single ID round-trips to a wrong-but-valid number, so a lookup misses or hits the wrong record. And because a whole run of consecutive integers collapses onto one representable value, two different IDs can round to the same number and become indistinguishable — a collision that no uniqueness constraint upstream anticipated.

**Below 2^53 every integer has an exact double and IDs survive; above it, integers snap to representable neighbors, so IDs change and distinct IDs can merge.**

<svg role="img" aria-label="The 64 bits of a double: 1 sign bit, 11 exponent bits, and 52 mantissa bits. With the implicit leading bit the significand is 53 bits, which names every integer up to 2 to the 53." viewBox="0 0 480 130">
<rect x="0" y="0" width="480" height="130" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">a 64-bit double: where the 2^53 ceiling comes from</text>
<rect x="40" y="40" width="24" height="26" fill="var(--muted)"></rect>
<text x="42" y="58" fill="var(--panel)" font-size="9">sgn</text>
<rect x="66" y="40" width="90" height="26" fill="var(--s1)"></rect>
<text x="82" y="58" fill="var(--panel)" font-size="9">exponent (11)</text>
<rect x="158" y="40" width="280" height="26" fill="var(--s2)"></rect>
<text x="240" y="58" fill="var(--panel)" font-size="9">mantissa (52 bits)</text>
<text x="158" y="88" fill="var(--s2)" font-size="10">52 stored + 1 implicit = 53-bit significand</text>
<text x="158" y="108" fill="var(--ink)" font-size="10">&#8594; every integer exact up to 2^53, then gaps</text>
</svg>
^ The 52 stored mantissa bits plus one implicit leading bit give 53 bits of significand, exactly enough to name every integer below 2^53 and no more.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/teaching-and-portability/code/int53-inter-01/int53.py

The fixture is a spread of IDs from tiny to 19 digits. In Python, `float` is the 64-bit double, so passing an integer through it reproduces exactly what a double-based JSON parser does.

```json filename=modules/teaching-and-portability/code/int53-inter-01/int53.json:3-10 COMPLETE
  "max_safe_int": 9007199254740991,
  "ids": [
    {"label": "small",             "value": 42},
    {"label": "max_safe (2^53-1)", "value": 9007199254740991},
    {"label": "2^53",              "value": 9007199254740992},
    {"label": "2^53+1",            "value": 9007199254740993},
    {"label": "snowflake_a",       "value": 1387496749436723201},
    {"label": "snowflake_b",       "value": 1387496749436723202}
  ]
```

The round trip is one line: through a float and back to int.

```python filename=modules/teaching-and-portability/code/int53-inter-01/int53.py:31-33 COMPLETE
def through_double(n):
    """Pass an integer through a 64-bit float and back -- exactly what a double-based JSON parser does."""
    return int(float(n))
```

Corruption is just failing to survive that, and the safe range is |n| ≤ 2^53.

```python filename=modules/teaching-and-portability/code/int53-inter-01/int53.py:36-43 COMPLETE
def is_corrupted(n):
    """True if the value does not survive the double round trip."""
    return through_double(n) != n


def in_safe_range(n):
    """True if the integer is small enough to be exactly representable as a double (|n| <= 2^53)."""
    return abs(n) <= TWO_53
```

Run it and the boundary is exact.

```text filename=int53.py --roundtrip
ROUNDTRIP — each ID through a 64-bit float and back (max safe = 9007199254740991)
------------------------------------------------------------------------
  small              42                   safe=True  ok
  max_safe (2^53-1)  9007199254740991     safe=True  ok
  2^53               9007199254740992     safe=True  ok
  2^53+1             9007199254740993     safe=False CORRUPTED -> 9007199254740992
  snowflake_a        1387496749436723201  safe=False CORRUPTED -> 1387496749436723200
  snowflake_b        1387496749436723202  safe=False CORRUPTED -> 1387496749436723200
------------------------------------------------------------------------
  every ID above 2^53 comes back as a different number -- a valid, wrong ID
```

42 and 2^53 − 1 survive, and 2^53 itself is still exact — it is the last exact one. But 2^53 + 1 comes back as 2^53, one less than it went in, because 2^53 + 1 is not representable and the nearest neighbor is 2^53. Both snowflake IDs come back as 1387496749436723200 — neither of them the value that went in.

<svg role="img" aria-label="A number line. Below 2^53 the representable integers are drawn as a dense solid strip labeled every integer exact. At 2^53 the strip becomes separated ticks spaced apart, labeled gaps of 2, then 4, with an arrow showing 2^53+1 snapping left to 2^53." viewBox="0 0 480 140">
<rect x="0" y="0" width="480" height="140" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">representable integers thin out above 2^53</text>
<rect x="40" y="60" width="200" height="14" fill="var(--s2)"></rect>
<text x="44" y="52" fill="var(--s2)" font-size="9">every integer exact</text>
<line x1="240" y1="55" x2="240" y2="82" stroke="var(--ink)"></line>
<text x="214" y="98" fill="var(--ink)" font-size="9">2^53</text>
<line x1="280" y1="60" x2="280" y2="74" stroke="var(--s1)"></line>
<line x1="320" y1="60" x2="320" y2="74" stroke="var(--s1)"></line>
<line x1="360" y1="60" x2="360" y2="74" stroke="var(--s1)"></line>
<line x1="400" y1="60" x2="400" y2="74" stroke="var(--s1)"></line>
<text x="286" y="52" fill="var(--s1)" font-size="9">gaps of 2, then 4, then 8</text>
<text x="255" y="120" fill="var(--muted)" font-size="9">2^53+1 has no slot &#8594; snaps back to 2^53</text>
<line x1="258" y1="110" x2="242" y2="80" stroke="var(--muted)"></line>
</svg>
^ Up to 2^53 the integers form a solid line; past it only every second, then fourth, integer is representable, so 2^53 + 1 falls into the gap and snaps back onto 2^53.

## Build

The collision is the worse failure: two different IDs become one.

```python filename=modules/teaching-and-portability/code/int53-inter-01/int53.py:46-48 COMPLETE
def collide(a, b):
    """True if two distinct integers map to the same double -- indistinguishable after the round trip."""
    return a != b and float(a) == float(b)
```

```text filename=int53.py --collide
COLLIDE — two distinct snowflake IDs that differ by 1
------------------------------------------------------------------------
  snowflake_a = 1387496749436723201
  snowflake_b = 1387496749436723202
  as doubles: 1387496749436723200 and 1387496749436723200
  collide as numbers? True   (distinct as strings? True)
------------------------------------------------------------------------
  through a double they are the same ID; as strings they stay two IDs
```

Two IDs that differ by one both round to 1387496749436723200 — at that magnitude the representable doubles are spaced 256 apart, so 256 consecutive IDs share one value. As numbers they collide; as strings they stay distinct, which is the fix in one line: transport the ID as text and the digits cannot round.

<svg role="img" aria-label="Two paths for a large ID. As a JSON number it passes through a double and two distinct IDs merge into one value. As a JSON string the two IDs stay separate and exact." viewBox="0 0 480 150">
<rect x="0" y="0" width="480" height="150" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">same two IDs, two transports</text>
<text x="12" y="46" fill="var(--s1)" font-size="11">as a number</text>
<text x="20" y="66" fill="var(--muted)" font-size="9">...201</text>
<text x="20" y="82" fill="var(--muted)" font-size="9">...202</text>
<line x1="60" y1="63" x2="150" y2="72" stroke="var(--s1)"></line>
<line x1="60" y1="79" x2="150" y2="72" stroke="var(--s1)"></line>
<text x="156" y="76" fill="var(--s1)" font-size="9">...200 (merged)</text>
<text x="12" y="112" fill="var(--s2)" font-size="11">as a string</text>
<text x="20" y="132" fill="var(--muted)" font-size="9">"...201"</text>
<line x1="70" y1="128" x2="150" y2="128" stroke="var(--s2)"></line>
<text x="156" y="132" fill="var(--s2)" font-size="9">"...201" and "...202" stay distinct</text>
</svg>
^ As numbers the two IDs merge into one value through the double; as strings they arrive exactly as sent, distinct — text has no representable-value ceiling.

The self-test pins the boundary and both failure modes.

```python filename=modules/teaching-and-portability/code/int53-inter-01/int53.py:86-93 COMPLETE
    unsafe_corrupts = is_corrupted(ids["2^53+1"])
    print("  the ID just past 2^53 is corrupted = %s (%d -> %d)" % (unsafe_corrupts, ids["2^53+1"], through_double(ids["2^53+1"])))

    boundary_exact = not is_corrupted(ids["2^53"])
    print("  2^53 itself is still exact (the last exact one) = %s" % boundary_exact)

    ids_collide = collide(ids["snowflake_a"], ids["snowflake_b"])
    print("  two distinct snowflake IDs collide as doubles = %s (both -> %d)" % (ids_collide, through_double(ids["snowflake_a"])))
```

```text filename=int53.py --check
SELF-TEST — IDs within the safe range survive, an ID above it is corrupted, two distinct IDs collide, and the string form preserves them all
----------------------------------------------------------------------------------------------------------------
  every ID within the safe range survives the double round trip = True
  the ID just past 2^53 is corrupted = True (9007199254740993 -> 9007199254740992)
  2^53 itself is still exact (the last exact one) = True
  two distinct snowflake IDs collide as doubles = True (both -> 1387496749436723200)
  carrying IDs as strings preserves every value and keeps them distinct = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  safe_ids_survive=True  unsafe_corrupts=True  boundary_exact=True  ids_collide=True  string_preserves=True
```

**string_preserves is the whole fix: the digits of an ID are an identity, and text carries an identity where a number carries a quantity that rounds.**

## Definition of done

You can state the exact boundary and why it is there: 2^53, because a double has 53 bits of significand and can name that many consecutive integers before the gaps exceed one.

You can name the everyday pipes that are secretly doubles — a JavaScript number, JSON.parse, a spreadsheet cell, a float column — and explain why the corruption is silent (a valid number, just the wrong one).

You can describe both failure modes: a single ID rounding to a wrong value, and two IDs colliding onto one because runs of integers share a representable value.

You can give the fix and why it works: transport large integer IDs as strings (or parse to a big integer/decimal), because text has no representable-value ceiling and preserves the exact digits.

## Boss fight

Your service issues 64-bit snowflake IDs and stores them in a bigint column, and everything is fine until you add a JavaScript web client that fetches records as JSON. Users start reporting that "sometimes I open a record and it's the wrong one," always for recently created records.

First: explain the full path the ID takes from the database to the browser and back, and name the exact step where it loses precision. Why is it always recent records — what do their IDs have in common?

Then: you have three candidate fixes — serialize the ID as a JSON string, keep it a number but subtract a fixed offset to bring it under 2^53, or round all IDs to multiples of 1000 at creation. For each, say whether it actually preserves identity and what it breaks. Which one is the real fix and why are the other two traps?

Finally: the string fix means the client compares IDs as strings, and someone proposes sorting records by ID to get newest-first, still comparing as strings. Given snowflake IDs are time-ordered integers, when does string comparison of the ID agree with numeric order and when does it silently disagree — and what does that tell you about treating a stringified ID as anything other than an opaque key?

## External resources

The ECMAScript specification defines Number as a 64-bit double and exposes the boundary directly as Number.MAX_SAFE_INTEGER (2^53 − 1) and Number.isSafeInteger — the language admitting in its own API that integers past this point are not safe.

Twitter's and Discord's developer documentation both warn that snowflake IDs must be treated as strings in JavaScript for exactly this reason, and their JSON payloads deliver the IDs as strings — a production example of the fix this module builds.
