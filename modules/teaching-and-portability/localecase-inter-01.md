---
id: localecase-inter-01
title: Fold case with a locale-independent rule for comparison — the Turkish dotless-I makes the same check accept or reject a string differently by locale
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: Turning a letter from upper to lower case looks universal and is not — the mapping depends on the locale, and the famous divergence is the letter I. In most locales uppercase 'I' lowercases to dotted 'i', but the Turkish and Azeri alphabets have two I letters, a dotless pair ('I'/'ı') and a dotted pair ('İ'/'i'), so there 'I' lowercases to dotless 'ı' and it is 'İ' that lowercases to 'i'. The same lower() call on the same string returns 'i' on one machine and 'ı' on another, purely from the process's locale. That wrecks case-insensitive comparison, which is usually done by lowercasing both sides and testing equality. A blocklist that forbids the username 'admin' and lowercases new names to compare will, on an English-locale machine, turn 'ADMIN' into 'admin', match, and block it — correct; on a Turkish-locale machine it turns 'ADMIN' into 'admın' (dotless), which does not equal 'admin', so the check misses and the forbidden name is allowed. Same code, same input, a different security decision made by the server's locale, which the developer never considered. The fix is to fold case with a fixed locale-independent rule — an invariant case fold using the Unicode default mapping where 'I' always maps to 'i', or an explicit invariant-culture API — so the comparison returns the same answer on every machine. On a fixture where the blocklist forbids 'admin', the invariant fold lowercases all three inputs to 'admin' and blocks them, while the Turkish fold turns any input with an uppercase I into 'admın' and lets 2 of 3 bypass.
eli5: You'd think making a letter lowercase is the same everywhere, but it isn't. In Turkish there are two kinds of the letter I — one with a dot and one without — so the capital "I" becomes a dotless "ı" there instead of the dotted "i" you'd expect. Now imagine a bouncer with a list of banned names who checks by making everything lowercase first. In most places "ADMIN" becomes "admin" and gets caught. But on a Turkish computer "ADMIN" becomes "admın" with a dotless i, which doesn't match "admin" — so the banned name walks right in. The same code lets someone through on one computer and stops them on another, just because of the language setting. The fix is to always lowercase the same fixed way, no matter what language the computer is set to.
---

## Why this module

Case-insensitive comparison feels like one of the safest operations there is: lowercase both strings, check if they are equal. It hides a portability landmine, because lowercasing is not a fixed function. The Unicode standard defines case mapping, but the operating-system locale can override parts of it, and the letter I is where the override bites. Most of the world maps uppercase 'I' to dotted 'i'. Turkish and Azeri, which genuinely have two distinct I letters, map uppercase 'I' to the dotless 'ı' and reserve dotted 'i' for the uppercase 'İ'.

The result is that `lower()` is a different function depending on where the process runs, and any code that lowercases to compare inherits that difference. The developer writes and tests in one locale, sees the comparison work, and ships. The same binary on a server configured for a Turkish locale computes a different lowercase for any string containing an I, and the comparison quietly changes its answer. Nothing errors; the two machines simply disagree about whether two strings are "the same ignoring case."

When that comparison is a security check — a blocklist, an allowlist, a duplicate-username guard — the disagreement becomes a vulnerability. This module builds the canonical case: a blocklist that forbids 'admin', and shows the same check blocking or bypassing the forbidden name depending on the locale's case fold.

**Case conversion is locale-dependent — the Turkish dotless-I is the classic example — so a case-insensitive check built on the OS locale's lower/upper accepts or rejects the same string differently by machine; comparison must fold case with a fixed, locale-independent rule.**

## Concepts

The fixture is a forbidden name and three spellings of it to test against a case-insensitive blocklist.

```json filename=modules/teaching-and-portability/code/localecase-inter-01/localecase.json:3-4 COMPLETE
  "forbidden": "admin",
  "inputs": ["admin", "ADMIN", "aDmIn"]
```

Two case folds model the two locales, applied character by character. The invariant fold maps every 'A'–'Z' to 'a'–'z', so 'I' always becomes 'i'. The Turkish fold is identical except that 'I' becomes the dotless 'ı' and the dotted 'İ' becomes 'i' — the two-I alphabet.

```python filename=modules/teaching-and-portability/code/localecase-inter-01/localecase.py:32-49 COMPLETE
def invariant_lower(s):
    """Locale-independent fold: uppercase A-Z map to a-z, so 'I' -> 'i' always."""
    return "".join(chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in s)


def turkish_lower(s):
    """Turkish locale fold: 'I' -> dotless 'ı', dotted 'İ' -> 'i'."""
    out = []
    for c in s:
        if c == "I":
            out.append("ı")
        elif c == "İ":
            out.append("i")
        elif "A" <= c <= "Z":
            out.append(chr(ord(c) + 32))
        else:
            out.append(c)
    return "".join(out)
```

A blocklist check lowercases the input with whichever fold and compares it to the forbidden name. The choice of fold — and only that choice — is what the two machines differ on.

```python filename=modules/teaching-and-portability/code/localecase-inter-01/localecase.py:52-53 COMPLETE
def blocked(value, forbidden, fold):
    return fold(value) == forbidden
```

The fold is passed in, so the same comparison logic yields different verdicts depending on which fold a machine's locale supplies.

<svg role="img" aria-label="The word ADMIN lowercased two ways: invariant gives admin which matches the blocklist, Turkish gives admin with a dotless i which does not match, so it bypasses" viewBox="0 0 320 120">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">lowercasing 'ADMIN' to compare against forbidden 'admin'</text>
  <text x="10" y="42" font-size="8" fill="var(--s1)">invariant</text>
  <rect x="70" y="32" width="70" height="16" fill="var(--s1)"/><text x="80" y="44" font-size="8" fill="var(--panel)">admin</text>
  <text x="150" y="44" font-size="8" fill="var(--ink)">= admin → BLOCKED</text>
  <text x="10" y="72" font-size="8" fill="var(--s2)">turkish</text>
  <rect x="70" y="62" width="70" height="16" fill="var(--s2)"/><text x="80" y="74" font-size="8" fill="var(--panel)">admın</text>
  <text x="150" y="74" font-size="8" fill="var(--ink)">≠ admin → BYPASS</text>
  <text x="10" y="104" font-size="7.5" fill="var(--muted)">the dotless 'ı' from uppercase 'I' is why the two folds disagree</text>
</svg>
^ The identical input 'ADMIN' folds to 'admin' under the invariant rule (matches the blocklist, blocked) and to 'admın' with a dotless i under the Turkish rule (does not match, bypasses). The single character that diverges — uppercase I — is the whole bug.

**The two folds differ only on the letter I, but a case-insensitive check is exactly a case fold plus an equality test — so that one character flips the check's decision.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the username-blocklist check of a signup flow, reduced to three inputs so every fold is checkable by hand.

Run `--fold` to see each input lowercased both ways.

```text filename=localecase.py --fold
  input     invariant   turkish
  admin     admin       admin
  ADMIN     admin       admın
  aDmIn     admin       admın
```

The all-lowercase 'admin' folds to 'admin' under both — no uppercase I, no divergence. But 'ADMIN' and 'aDmIn' each contain an uppercase I, and there the folds split: invariant gives 'admin', Turkish gives 'admın' with a dotless i. The strings look identical on screen except for the dot, and that dot is the difference between matching the blocklist and not.

Now `--block` runs the actual check, folding each input both ways and comparing to the forbidden name.

```python filename=modules/teaching-and-portability/code/localecase-inter-01/localecase.py:74-78 COMPLETE
    for s in inputs:
        inv = blocked(s, forbidden, invariant_lower)
        tr = blocked(s, forbidden, turkish_lower)
        note = "   <- BYPASS in Turkish" if inv and not tr else ""
        print("  %-8s  %-17s  %s%s" % (s, inv, tr, note))
```

The two boolean columns are where the locales part ways.

```text filename=localecase.py --block
  input     invariant blocks?   turkish blocks?
  admin     True               True
  ADMIN     True               False   <- BYPASS in Turkish
  aDmIn     True               False   <- BYPASS in Turkish
```

Under the invariant fold the blocklist catches all three spellings — every case variant of the forbidden name is blocked, which is the whole point of a case-insensitive check. Under the Turkish fold it catches only the already-lowercase 'admin'; the two spellings with an uppercase I fold to 'admın' and slip through. The exact same code, given the exact same forbidden name and inputs, blocks three names on one machine and one name on another. An attacker who registers 'ADMIN' is rejected in testing and admitted in production, if production happens to run a Turkish locale.

<svg role="img" aria-label="A bar chart: invariant fold blocks 3 of 3 forbidden spellings, Turkish fold blocks only 1 of 3, leaving 2 bypasses" viewBox="0 0 320 110">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">forbidden spellings blocked (of 3)</text>
  <text x="10" y="42" font-size="8.5" fill="var(--s1)">invariant</text>
  <rect x="80" y="32" width="180" height="16" fill="var(--s1)"/><text x="160" y="44" font-size="8" fill="var(--panel)">3 of 3</text>
  <text x="10" y="72" font-size="8.5" fill="var(--s2)">turkish</text>
  <rect x="80" y="62" width="60" height="16" fill="var(--s2)"/><text x="102" y="74" font-size="8" fill="var(--panel)">1 of 3</text>
  <text x="146" y="74" font-size="8" fill="var(--ink)">2 bypass (any uppercase I)</text>
  <text x="10" y="98" font-size="7.5" fill="var(--muted)">same code, same inputs — the locale decides the security outcome</text>
</svg>
^ The invariant fold blocks all three spellings; the Turkish fold blocks one and lets the two containing an uppercase I bypass. The gap is not a difference in the code or the data — only in the locale's case mapping.

**The invariant fold blocks 3 of 3 forbidden spellings, the Turkish fold 1 of 3 — the same blocklist makes opposite security decisions on the two locales, and any input with an uppercase I is the bypass.**

## Build

The self-test asserts the divergence and its consequence: the two folds differ on some input, the invariant fold blocks every spelling, and the Turkish fold blocks fewer — letting a forbidden name bypass.

```python filename=modules/teaching-and-portability/code/localecase-inter-01/localecase.py:91-101 COMPLETE
    folds_differ = any(invariant_lower(s) != turkish_lower(s) for s in inputs)
    print("  the two locales fold some input differently = %s" % folds_differ)

    invariant_blocks_all = len(inv_blocked) == len(inputs)
    print("  the invariant fold blocks every spelling of the forbidden name = %s (%d/%d)" % (invariant_blocks_all, len(inv_blocked), len(inputs)))

    turkish_misses_some = len(tr_blocked) < len(inputs)
    print("  the Turkish fold blocks fewer than all = %s (%d/%d)" % (turkish_misses_some, len(tr_blocked), len(inputs)))

    bypass_exists = len(bypass) > 0
    print("  a forbidden name bypasses under the Turkish fold = %s (%s)" % (bypass_exists, bypass))
```

Running the check confirms every clause, including that the same code makes a different block decision by locale.

```text filename=localecase.py --check
  the two locales fold some input differently = True
  the invariant fold blocks every spelling of the forbidden name = True (3/3)
  the Turkish fold blocks fewer than all = True (1/3)
  a forbidden name bypasses under the Turkish fold = True (['ADMIN', 'aDmIn'])
  the same code makes a different block decision by locale = True
```

**The check pins the vulnerability to the locale's case fold: the invariant fold blocks every spelling everywhere, the Turkish fold lets uppercase-I names through, and the only thing that changed was the locale.**

## Definition of done

Done means the same blocklist is shown to block or bypass the same forbidden name depending on the locale's case fold, and the invariant fold blocks it consistently. The clause that the two folds differ is the root cause made explicit — the bug is not in the comparison logic, which is fine, but in the assumption that lowercasing is a single fixed function when it is a locale-parameterized one.

Two clarifications carry this to real code. First, the concrete fix in most languages is a case fold that is documented as locale-independent: in .NET, `ToLowerInvariant()` or, better, `string.Equals(a, b, StringComparison.OrdinalIgnoreCase)`; in Java, `toLowerCase(Locale.ROOT)` or `equalsIgnoreCase`; in Python, `str.casefold()` (which uses the Unicode default mapping and is not locale-sensitive, unlike the C library's locale-aware routines) — the rule is to pick the API that pins the mapping rather than the one that reads the ambient locale. For a security check, an ordinal (byte/codepoint) case-insensitive comparison is safest, because it does no locale lookup at all. Second, the deeper principle is the same one behind seeding a random generator, pinning a dependency, and fixing an encoding: an implicit environment setting must never be allowed to silently change what your code computes. Case folding for comparison is data processing, and data processing has to be deterministic across machines; the display of text to a human can and should respect the locale, but the moment you fold case to make a decision, the locale must be out of the loop.

<svg role="img" aria-label="A split: fold case by the ambient locale for displaying text to a human, but fold case by a fixed invariant rule when comparing to make a decision" viewBox="0 0 320 120">
  <rect x="16" y="24" width="130" height="36" fill="none" stroke="var(--s1)"/>
  <text x="26" y="40" font-size="7.5" fill="var(--s1)">comparing / deciding</text>
  <text x="26" y="53" font-size="7.5" fill="var(--ink)">→ invariant fold</text>
  <rect x="170" y="24" width="134" height="36" fill="none" stroke="var(--s2)"/>
  <text x="180" y="40" font-size="7.5" fill="var(--s2)">displaying to a human</text>
  <text x="180" y="53" font-size="7.5" fill="var(--ink)">→ locale fold is fine</text>
  <text x="16" y="84" font-size="7.5" fill="var(--muted)">the locale may shape what a person sees, never what a comparison decides</text>
  <text x="16" y="102" font-size="7.5" fill="var(--ink)">same principle as seeding RNG and pinning versions: no implicit env in the result</text>
</svg>
^ Locale-aware casing is correct for presenting text to a person, but a comparison that drives a decision must fold case by a fixed invariant rule, so the ambient locale never changes the outcome — the same discipline as seeding randomness or pinning a dependency.

**Done means the locale-sensitive fold is shown to change the blocklist's decision while the invariant fold blocks consistently — comparison folds case by a fixed rule (casefold, invariant culture, or ordinal), keeping the ambient locale out of every decision.**

## Boss fight

A web app lets users pick a display name but forbids reserved names like "admin" and "root", checked case-insensitively by lowercasing the requested name and comparing. It passes all tests. After the service is deployed to a new regional data center, support reports users who somehow registered names like "ADMIN". The code did not change. What happened, and how do you fix it and prevent the class of bug?

The new data center's servers run a Turkish (or Azeri) locale, and the reserved-name check lowercases using the locale-sensitive routine, so uppercase 'I' folds to the dotless 'ı' instead of 'i'. "ADMIN" becomes "admın", which does not equal the reserved "admin", and the check lets it through — while on the original locale it folded to "admin" and was correctly blocked. The code is identical; only the ambient locale changed, and with it the meaning of `lower()`. The immediate fix is to fold case for this comparison with a locale-independent rule: use an ordinal case-insensitive comparison, or lowercase/casefold with the invariant mapping (`ToLowerInvariant`/`Locale.ROOT`/`str.casefold`) rather than the locale-aware one, so 'ADMIN' folds to 'admin' on every machine and the reserved name is blocked everywhere. To prevent the class of bug, treat every case fold that drives a decision — not just this one — as needing an explicit, locale-independent mapping, and audit the codebase for locale-sensitive `toLowerCase`/`toUpperCase` used in comparisons, deduplication, routing, or lookups. More broadly, forbid implicit-locale behavior in data processing the same way you forbid unseeded randomness and unpinned dependencies: pin the locale (or bypass it) wherever the result must be identical across machines, and reserve locale-aware casing for text shown to humans. Adding a test that runs the reserved-name check under a Turkish locale would have caught it before deployment, and is the kind of cross-locale test worth having for any case-insensitive security check.

## External resources

The many writeups of the "Turkish-I problem" (Microsoft's guidance on culture-insensitive string operations with `ToLowerInvariant`/`StringComparison.Ordinal`, and the Java `Locale.ROOT` case-conversion guidance) — the canonical treatment of why case conversion is locale-dependent and which APIs pin the mapping.

The Unicode case-folding specification and the distinction between case mapping and case folding (`str.casefold` in Python, the CaseFolding.txt data) — the fixed, locale-independent mapping designed specifically for caseless comparison, and why it, not the locale's lower/upper, belongs in a comparison.
