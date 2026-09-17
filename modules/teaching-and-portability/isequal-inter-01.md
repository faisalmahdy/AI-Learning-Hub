---
id: isequal-inter-01
title: Compare values with ==, never with `is` — identity agrees with equality for small integers and silently breaks for large ones
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: Python has two comparison operators that are easy to confuse because they so often agree: == asks whether two things have the same value, and `is` asks whether they are the same object in memory. For comparing values you always want ==, and reaching for `is` is dangerous precisely because it usually works — for the small integers, short strings, and None in quick tests, `is` returns the same answer == would, so the bug passes every test written with small examples and waits for production data. The reason `is` seems to work is an optimization: CPython pre-creates a single cached object for every small integer (the range −5 to 256) and hands out that same object every time such a value is produced, so two separately-computed small integers of the same value are literally the same object and `is` returns True, coincidentally matching ==. Step outside the cached range and the coincidence ends: each large integer is a freshly allocated object, so two separately-computed large integers of the same value are different objects and `is` returns False even though the values are equal. That cache range is an implementation detail — −5 to 256 in current CPython, but the boundary has changed across versions and other interpreters cache differently — so code using `is` for value equality is wrong in a way that depends on the interpreter, the version, and the exact values, the definition of a portability bug. The fix is one character of discipline: use == for value equality and reserve `is` for identity checks like comparing against None. On a fixture with two equal small integers (256, cached) and two equal large integers (257, just outside the cache), == is True for both while `is` is True for 256 and False for 257 — the identical comparison, right on the small value, wrong on the large.
eli5: Imagine two ways to ask if two coins are "the same." One way asks "are these worth the same amount?" — that's ==. The other asks "is this literally the exact same physical coin?" — that's `is`. Usually you care about the value. Now, a shop keeps one special penny that it lends out whenever anyone needs a penny, so if two people both grab "a penny" they're holding the very same coin — and "is it the same coin?" accidentally says yes, matching "is it worth the same?". But for a hundred-dollar bill the shop hands out a fresh one each time, so two people holding equal hundreds have different bills — "same physical bill?" says no, even though they're worth exactly the same. If you'd been asking "same physical object?" to check value, it worked for pennies and quietly failed for hundreds. Just ask about the value.
---

## Why this module

`is` and `==` are one character apart and mean genuinely different things, and the gap between them is a classic source of bugs that survive testing and surface in production. The trap is not that `is` is obscure — it is that it *works*, on exactly the inputs you use while writing and testing code. Small numbers, `None`, short interned strings: for all of these `is` gives the same answer as `==`, so a value comparison written with `is` looks correct, passes its tests, and gets shipped. Then a real user's data carries a larger number, and the comparison that "worked" starts returning the wrong answer with no code change at all.

The two operators ask different questions. `==` asks whether two objects have the same value, delegating to the type's equality definition. `is` asks whether two references point to the very same object in memory — identity, not value. These coincide only when equal values happen to be the same object, and whether that happens is up to the interpreter. CPython makes it happen for small integers by caching them: it builds one object for each value from −5 to 256 and reuses it everywhere, so equal small integers are identical objects and `is` accidentally behaves like `==`.

Outside that cache, equal values are separate objects and `is` diverges from `==`. This module compares an equal pair inside the cache and an equal pair just outside it, both ways, and shows the identical `is` comparison giving the right answer on one and the wrong answer on the other.

**Compare values with `==`, never with `is`, because `is` tests object identity and only coincidentally matches value equality for cached small integers (and interned literals) — outside that implementation-defined cache, two equal values are distinct objects and `is` returns False, so `is`-for-equality passes tests on small numbers and fails on large ones.**

## Concepts

The fixture is two pairs of equal-valued integers. The first pair sums to 256 — inside CPython's small-integer cache (−5 to 256). The second sums to 257 — just outside it. Each value is built from parts so it is computed at runtime, not written as a single literal (which the compiler might intern into one shared object, hiding the effect).

```json filename=modules/teaching-and-portability/code/isequal-inter-01/isequal.json:3-6 COMPLETE
  "pairs": [
    {"label": "small (in the -5..256 cache)", "a_parts": [250, 6], "b_parts": [200, 56]},
    {"label": "large (outside the cache)", "a_parts": [250, 7], "b_parts": [200, 57]}
  ]
```

Building by summing parts forces a separately-computed object. Then the two comparisons are one line each — `is` for identity, `==` for value.

```python filename=modules/teaching-and-portability/code/isequal-inter-01/isequal.py:32-47 COMPLETE
def build(parts):
    """Build an integer by summing parts at runtime, forcing a separately-computed object (not one interned literal)."""
    total = 0
    for p in parts:
        total += p
    return total


def identity_holds(a, b):
    """Whether a and b are the SAME object (`is`)."""
    return a is b


def equality_holds(a, b):
    """Whether a and b have the same VALUE (`==`)."""
    return a == b
```

For the small pair, both `a_parts` and `b_parts` sum to 256, and because 256 is cached, both computations return the one shared 256 object — so `a is b` is True. For the large pair, both sum to 257, which is not cached, so each computation allocates a fresh 257 object — and `a is b` is False, even though `a == b` is True.

<svg role="img" aria-label="Two 256 references both pointing to a single cached object, versus two 257 references each pointing to its own separate object" viewBox="0 0 320 130">
  <text x="10" y="18" font-size="9" fill="var(--muted)">256 (cached): both refs → one object</text>
  <text x="20" y="42" font-size="9" fill="var(--s1)">a</text>
  <text x="20" y="62" font-size="9" fill="var(--s1)">b</text>
  <rect x="110" y="38" width="60" height="22" fill="var(--s1)"/><text x="128" y="53" font-size="9" fill="var(--panel)">256</text>
  <line x1="30" y1="40" x2="108" y2="46" stroke="var(--s1)" stroke-width="1"/>
  <line x1="30" y1="58" x2="108" y2="52" stroke="var(--s1)" stroke-width="1"/>
  <text x="180" y="53" font-size="8.5" fill="var(--muted)">a is b → True</text>
  <text x="10" y="90" font-size="9" fill="var(--muted)">257 (uncached): each ref → its own object</text>
  <text x="20" y="110" font-size="9" fill="var(--s2)">c</text>
  <text x="20" y="126" font-size="9" fill="var(--s2)">d</text>
  <rect x="110" y="98" width="60" height="16" fill="var(--s2)"/><text x="128" y="110" font-size="8" fill="var(--panel)">257</text>
  <rect x="110" y="118" width="60" height="14" fill="var(--s2)"/><text x="128" y="129" font-size="8" fill="var(--panel)">257</text>
  <line x1="30" y1="107" x2="108" y2="106" stroke="var(--s2)" stroke-width="1"/>
  <line x1="30" y1="123" x2="108" y2="125" stroke="var(--s2)" stroke-width="1"/>
  <text x="180" y="115" font-size="8.5" fill="var(--muted)">c is d → False</text>
</svg>
^ For 256 the cache makes both references point at one object, so `is` is True. For 257 each value is its own object, so `is` is False — while `==` is True for both because the values are equal either way.

**`is` and `==` are different questions — same object versus same value — and they coincide only when the interpreter happens to share objects, which for integers it does inside a fixed cache and not outside it.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — a value-comparison check reduced to two integer pairs so every identity and equality result is checkable by hand.

Run `--pairs` to see both comparisons for each pair.

```text filename=isequal.py --pairs
  label                          value   a is b   a == b
  small (in the -5..256 cache)   256     True     True
  large (outside the cache)      257     False    True
```

For 256, `is` and `==` both return True — they agree, which is exactly the trap: a value comparison written as `a is b` looks correct here and passes any test that uses small numbers. For 257, the same `a is b` returns False while `a == b` returns True. The comparison did not change; only the value did, and it crossed the cache boundary. Code that used `is` to check equality just silently gave the wrong answer for a number one larger than the one it was tested with.

The `--diverge` view scans the pairs and prints the one where the two operators split — the case where identity and equality give different answers.

```python filename=modules/teaching-and-portability/code/isequal-inter-01/isequal.py:66-73 COMPLETE
    for pr in data["pairs"]:
        a, b = build(pr["a_parts"]), build(pr["b_parts"])
        if identity_holds(a, b) != equality_holds(a, b):
            print("  %s: value %d" % (pr["label"], a))
            print("    a is b  = %s (different objects -- %d is outside the small-int cache)" % (identity_holds(a, b), a))
            print("    a == b  = %s (equal values)" % equality_holds(a, b))
            print("    -> `is` says NOT equal, `==` says equal; `==` is the correct value test")
            return
```

Running it isolates the failing pair.

```text filename=isequal.py --diverge
  large (outside the cache): value 257
    a is b  = False (different objects -- 257 is outside the small-int cache)
    a == b  = True (equal values)
    -> `is` says NOT equal, `==` says equal; `==` is the correct value test
```

The 257 pair is where identity and equality part ways: `is` reports the two objects are not the same (true — they are separate allocations) and `==` reports the values are equal (also true). Both operators answered their own question correctly; the bug is asking `is` a question you meant for `==`. The correct value test is `==`, and it is right here as it was right for 256.

**The identical `is` comparison returns True for 256 and False for 257 — nothing about the code changed, only whether the value fell inside an interpreter cache, which is why `is`-for-equality is a bug that hides until the data grows.**

## Build

The self-test asserts the whole pattern: both pairs are value-equal, `is` accidentally agrees inside the cache, `is` returns False outside it though `==` is True, and the two operators disagree on the large pair.

```python filename=modules/teaching-and-portability/code/isequal-inter-01/isequal.py:85-100 COMPLETE
    both_pairs_value_equal = equality_holds(sa, sb) and equality_holds(la, lb)
    print("  both pairs are value-equal (`==` True) = %s (%d==%d, %d==%d)" % (both_pairs_value_equal, sa, sb, la, lb))

    small_in_cache = sa <= 256
    is_agrees_small = identity_holds(sa, sb)
    print("  for the small value (%d, cached) `is` accidentally agrees = %s" % (sa, is_agrees_small and small_in_cache))

    large_out_of_cache = la > 256
    is_fails_large = not identity_holds(la, lb)
    print("  for the large value (%d, uncached) `is` returns False though `==` is True = %s" % (la, is_fails_large and large_out_of_cache))

    is_disagrees_with_eq = identity_holds(la, lb) != equality_holds(la, lb)
    print("  `is` and `==` disagree on the large pair = %s (is=%s, ==%s)" % (is_disagrees_with_eq, identity_holds(la, lb), equality_holds(la, lb)))

    eq_never_wrong = equality_holds(sa, sb) and equality_holds(la, lb)
    print("  `==` gives the correct answer on every pair = %s" % eq_never_wrong)
```

<svg role="img" aria-label="A table: rows small 256 and large 257, columns is and equals; is is True then False, equals is True then True, with equals marked correct for both" viewBox="0 0 320 110">
  <text x="120" y="20" font-size="9" fill="var(--muted)">a is b</text>
  <text x="200" y="20" font-size="9" fill="var(--muted)">a == b</text>
  <text x="10" y="46" font-size="9" fill="var(--ink)">256 (cached)</text>
  <rect x="115" y="34" width="55" height="18" fill="var(--s1)"/><text x="130" y="47" font-size="8" fill="var(--panel)">True</text>
  <rect x="195" y="34" width="55" height="18" fill="var(--s1)"/><text x="210" y="47" font-size="8" fill="var(--panel)">True</text>
  <text x="10" y="76" font-size="9" fill="var(--ink)">257 (uncached)</text>
  <rect x="115" y="64" width="55" height="18" fill="var(--s2)"/><text x="126" y="77" font-size="8" fill="var(--panel)">False</text>
  <rect x="195" y="64" width="55" height="18" fill="var(--s1)"/><text x="210" y="77" font-size="8" fill="var(--panel)">True</text>
  <text x="120" y="98" font-size="8" fill="var(--s2)">flips with the cache</text>
  <text x="196" y="98" font-size="8" fill="var(--s1)">correct for both</text>
</svg>
^ The `==` column is True in both rows — always correct. The `is` column flips from True to False across the cache boundary, giving the wrong equality answer for 257.

Running the check confirms every clause, including that `is` gives different answers for the same value-equality question.

```text filename=isequal.py --check
  both pairs are value-equal (`==` True) = True (256==256, 257==257)
  for the small value (256, cached) `is` accidentally agrees = True
  for the large value (257, uncached) `is` returns False though `==` is True = True
  `is` and `==` disagree on the large pair = True (is=False, ==True)
  `==` gives the correct answer on every pair = True
  `is` gives different answers for the same value-equality question = True (small True, large False)
```

**The check pins `==` as correct on every pair and `is` as flipping at the cache boundary — so the operator, not the value, is the bug, and `==` is the fix.**

## Definition of done

Two properties close it. `==` must give the correct answer on every pair — it is the reliable value test — and `is` must give *different* answers for the same value-equality question depending only on whether the value is cached, which is what makes it unreliable. The second is the portability point: an operator whose answer to "are these equal?" depends on an interpreter cache cannot be trusted for equality.

```python filename=modules/teaching-and-portability/code/isequal-inter-01/isequal.py:102-107 COMPLETE
    is_unreliable = identity_holds(sa, sb) != identity_holds(la, lb)
    print("  `is` gives different answers for the same value-equality question = %s (small %s, large %s)"
          % (is_unreliable, identity_holds(sa, sb), identity_holds(la, lb)))

    ok = (both_pairs_value_equal and (is_agrees_small and small_in_cache) and (is_fails_large and large_out_of_cache)
          and is_disagrees_with_eq and eq_never_wrong and is_unreliable)
```

Two clarifications keep the tool from being mis-stated. First, `is` is not broken and not useless — it is the right operator for identity checks, and there is exactly one value comparison where it is idiomatic and correct: `x is None`. `None` is a true singleton (there is only ever one None object), so identity and equality always coincide for it, and `is None` is preferred because it is unambiguous and cannot be fooled by a class overriding `__eq__`. The rule is not "never use `is`," it is "never use `is` for value equality of things that are not singletons." Second, the specific cache range (−5 to 256) and the interning of literals are CPython implementation details you should never rely on in either direction — do not use `is` and count on caching to make it work, and do not assume two equal small integers are always distinct objects either; write `==` and the question of caching never arises. The same trap applies to strings (short or interned strings may satisfy `is`, longer or computed ones will not), which is why `==` is the universal answer for value comparison.

<svg role="img" aria-label="A number line marking the cached range from minus 5 to 256 where is-equals-equals holds, and the region beyond 256 where is breaks for value comparison" viewBox="0 0 320 100">
  <line x1="20" y1="55" x2="300" y2="55" stroke="var(--line)" stroke-width="1"/>
  <rect x="40" y="48" width="180" height="14" fill="var(--s1)" opacity="0.5"/>
  <text x="60" y="40" font-size="8.5" fill="var(--s1)">-5 .. 256 cached: `is` matches `==`</text>
  <line x1="220" y1="45" x2="220" y2="65" stroke="var(--ink)" stroke-width="1.3"/>
  <text x="206" y="78" font-size="8" fill="var(--ink)">256</text>
  <rect x="220" y="48" width="80" height="14" fill="var(--s2)" opacity="0.6"/>
  <text x="224" y="40" font-size="8.5" fill="var(--s2)">beyond: `is` breaks</text>
  <text x="20" y="95" font-size="8" fill="var(--muted)">the boundary is an implementation detail — `==` is correct on both sides</text>
</svg>
^ Inside the cache `is` coincidentally matches `==`; past 256 it breaks for value comparison. The boundary is interpreter- and version-specific, so `==` — correct on both sides — is the only reliable value test.

**Done means `==` is correct on every pair while `is` flips with the cache — so value comparisons use `==`, `is` is reserved for identity (and `is None`), and no equality answer ever depends on an interpreter's caching.**

## Boss fight

A colleague reports a bug: their function that checks whether a computed order quantity equals a configured limit works in unit tests but occasionally lets orders through that should have been blocked. The check is `if quantity is limit:`. Both `quantity` and `limit` are integers read or computed at runtime. Why does it pass tests but fail in production, and what is the one-character fix — and why is the same bug latent even for the cases where it currently "works"?

The check uses `is`, which tests object identity, not value. In the unit tests the quantities and limits are small — the kind of round numbers people put in test fixtures — and small integers (−5 to 256 in CPython) are cached, so two equal small integers are the same object and `quantity is limit` accidentally returns True, matching what `==` would say; the tests pass. In production the real quantities and limits are larger, outside the cache, so two equal large integers are distinct objects and `quantity is limit` returns False even when the values are equal — the check fails to fire and the order slips through. The one-character fix is `if quantity == limit:`, which compares value and is correct regardless of size. And the reason the bug is latent even in the passing cases is that their correctness depends entirely on the small-integer cache, an implementation detail: the same code on a different Python version, another interpreter, or with the boundary values could stop caching those integers and the "working" tests would start failing too. The code was never correct — it was coincidentally right on cached values — so the fix is not "handle the large case," it is to use `==` everywhere value equality is meant, leaving `is` only for genuine identity checks like `is None`.

## External resources

The CPython documentation and source notes on small-integer caching (the `NSMALLPOSINTS`/`NSMALLNEGINTS` range) and string interning — the implementation details behind why `is` sometimes matches `==`, stated as optimizations you must not depend on.

The Python language reference on the `is`/`is not` and `==`/`!=` operators, and PEP 8's guidance to compare singletons like None with `is` — the authoritative statement of what each operator means and the one place `is` is the correct choice for a comparison that looks like equality.
