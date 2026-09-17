---
id: numlocale-inter-01
title: Format numbers locale-independently for interchange — or a comma-decimal locale writes data another machine misreads
topic: teaching-and-portability
level: intermediate
status: ready
time: 16 min
summary: Locales disagree on how to write a number. The United States writes 1,234.5 — period decimal, comma thousands — while much of Europe writes the same value as 1.234,5 — comma decimal, period thousands. Both are correct locally and both are ambiguous globally: the string "1.234" is a little over one in the US convention and one thousand two hundred thirty-four in the German one. So a program that formats or parses numbers using whatever locale the machine is set to produces data another machine, set to a different locale, cannot read — and the dangerous part is that it often does not fail. It silently reads the number as a different value: the European "1.234,5" parsed by a US-locale reader becomes 1.234, off by a factor of a thousand, with no error. The fix is to stop using the display locale for data: any number stored, transmitted, compared, or parsed must use a single fixed, locale-independent format — a period decimal, no thousands separators (1234.5), parsed the same way everywhere. On a fixture, the value 1234.5 formats as "1,234.5" (US) and "1.234,5" (DE), each parses correctly under its own locale but cross-parses to the wrong 1.2345, and only the fixed format round-trips to 1234.5 exactly.
eli5: Two countries write the same amount of money differently: one puts a dot before the cents and commas between the thousands, the other swaps them. So "1.234" means "one and a bit" to one country and "one thousand two hundred thirty-four" to the other. If a program writes numbers the way its country does and another country's program reads them its own way, the amount silently changes — sometimes by a thousand times — and nothing complains. The safe rule: when a number is being saved or sent for a machine to read, always write it one plain, agreed way (a dot for the decimal, nothing between the thousands), no matter what country the machine thinks it's in.
---

## Why this module

A number written for a human carries the writer's locale conventions, and those conventions are not universal — so a number formatted for display and then read back by a program becomes a different number whenever the reader's locale differs from the writer's, silently.

Every locale has its own way of writing numbers, and the two most common conventions are mirror images. The US style uses a period for the decimal point and a comma to group thousands: 1,234.5. Much of Europe uses a comma for the decimal and a period for grouping: 1.234,5. Each is unambiguous to a reader who knows the locale, but between locales the same characters mean different things — "1.234" is one-point-two-three-four under one convention and one-thousand-two-hundred-thirty-four under the other. When a program formats a number using the machine's configured locale and writes it to a file, a CSV field, a config, or an API response, it has embedded that ambiguity into data. A second program, on a machine set to a different locale, reads the string with *its* conventions and gets a different number. The reader does not know the writer's locale, and the string does not carry it, so there is nothing to reconcile.

**A number formatted in the display locale carries that locale's decimal and thousands conventions, which differ across machines — so data written by one locale is read as a different value by another, and because both strings are valid numbers, no error is raised.**

The failure is silent, which is what makes it dangerous. If the cross-locale string were malformed the reader would throw, but "1.234,5" and "1,234.5" are both parseable, so the reader happily returns the wrong value — often off by three orders of magnitude when a thousands separator is read as a decimal. A price becomes a thousand times too small, a measurement a thousand times too large, and the pipeline runs clean. The fix is to separate two jobs that look the same but are not: formatting a number *for a human to read* (use their locale) and serializing a number *for a machine to read back* (use one fixed format everywhere). For any number that is stored, transmitted, compared, or parsed, use a locale-independent format — a period decimal, no thousands separator, 1234.5 — and parse it with a locale-independent parser. This module formats a value under two locales and a fixed format and shows only the fixed one survive the round trip.

## Concepts

**Locale formatting** writes a number with a locale's decimal and thousands separators. The same value produces different text under different locales.

```python filename=modules/teaching-and-portability/code/numlocale-inter-01/numlocale.py:42-52 COMPLETE
def fmt(value, decimal, thousands):
    """Write `value` with the given decimal and thousands separators."""
    whole, frac = ("%.1f" % value).split(".")
    if thousands:
        groups = []
        while len(whole) > 3:
            groups.insert(0, whole[-3:])
            whole = whole[:-3]
        groups.insert(0, whole)
        whole = thousands.join(groups)
    return whole + decimal + frac
```

**Locale parsing** reads a number string under a locale's separators. Applied to a string written in a *different* locale, it returns a wrong value without error.

```python filename=modules/teaching-and-portability/code/numlocale-inter-01/numlocale.py:55-60 COMPLETE
def parse(s, decimal, thousands):
    """Read a number string under the given separators: drop thousands, normalize the decimal to a period, to float."""
    if thousands:
        s = s.replace(thousands, "")
    s = s.replace(decimal, ".")
    return float(s)
```

**The fixed interchange format** is one locale-independent convention — period decimal, no thousands separator — used for all data a machine reads back, parsed the same way everywhere.

<svg role="img" aria-label="The string 1.234 is interpreted as one-point-two-three-four under US rules but one-thousand-two-hundred-thirty-four under DE rules" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the same characters, two meanings</text>
  <rect x="110" y="20" width="80" height="20" fill="none" stroke="var(--ink)"/><text x="128" y="34" fill="var(--ink)" font-size="10">1.234</text>
  <line x1="150" y1="40" x2="80" y2="62" stroke="var(--s1)"/><line x1="150" y1="40" x2="220" y2="62" stroke="var(--s2)"/>
  <text x="30" y="76" fill="var(--s1)" font-size="8">US: 1.234 (≈ one)</text>
  <text x="180" y="76" fill="var(--s2)" font-size="8">DE: 1234 (one thousand)</text>
  <text x="6" y="92" fill="var(--muted)" font-size="8">a period is a decimal to one locale and a thousands separator to the other</text>
</svg>
^ The string "1.234" is barely over one under US rules (period = decimal) and one thousand two hundred thirty-four under DE rules (period = thousands), so the same text is two different numbers depending on the reader's locale.

**Use the display locale to show a number to a human and a single fixed, locale-independent format (period decimal, no thousands separator) for any number a machine will read back — because a number serialized in the display locale changes value across locales, without error.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/numlocale-inter-01/numlocale.py

The fixture is one value and the separators used by the US locale, the DE locale, and a fixed interchange format.

```json filename=modules/teaching-and-portability/code/numlocale-inter-01/numlocale.json:3-8 COMPLETE
  "value": 1234.5,
  "locales": {
    "US": {"decimal": ".", "thousands": ","},
    "DE": {"decimal": ",", "thousands": "."}
  },
  "fixed": {"decimal": ".", "thousands": ""}
```

Run `--format` to write the same value three ways.

```text filename=--format
FORMAT — the same number written three ways
--------------------------------------------------
  US       locale:  1,234.5
  DE       locale:  1.234,5
  fixed (interchange): 1234.5
```

One value, 1234.5, three strings. The US locale writes "1,234.5", the DE locale writes "1.234,5", and the fixed format writes "1234.5". The US and DE strings are the crux: they use the exact same two characters — a period and a comma — in opposite roles. Where US puts the comma (thousands) DE puts the period, and where US puts the period (decimal) DE puts the comma. A reader handed "1.234,5" with no locale label cannot tell whether the period is a decimal or a thousands mark; it has to assume, and its assumption is its own locale. The fixed format sidesteps the ambiguity by removing the thousands separator entirely and fixing the decimal to a period, so there is only one character with meaning and only one way to read it. That is the string you commit to a file or send over the wire; the locale strings are for a human's eyes only.

<svg role="img" aria-label="The value 1234.5 formatted as 1,234.5 in US, 1.234,5 in DE, and 1234.5 in the fixed format" viewBox="0 0 300 92" width="300" height="92">
  <text x="6" y="12" fill="var(--muted)" font-size="8">value 1234.5 → three strings</text>
  <rect x="10" y="20" width="60" height="20" fill="none" stroke="var(--ink)"/><text x="22" y="34" fill="var(--ink)" font-size="9">1234.5</text>
  <line x1="70" y1="30" x2="110" y2="30" stroke="var(--line)"/>
  <text x="120" y="26" fill="var(--s1)" font-size="8">US:  1,234.5</text>
  <text x="120" y="42" fill="var(--s2)" font-size="8">DE:  1.234,5</text>
  <text x="120" y="58" fill="var(--ink)" font-size="8">fixed: 1234.5  ← for machines</text>
  <text x="6" y="80" fill="var(--muted)" font-size="8">US and DE swap the roles of '.' and ',' — the fixed format uses only a period decimal</text>
</svg>
^ The same value 1234.5 becomes "1,234.5" (US), "1.234,5" (DE), and "1234.5" (fixed) — the two locale forms swap the roles of period and comma, while the fixed form is unambiguous.

## Build

The ambiguity turns into a wrong number at parse time. Run `--roundtrip`.

```text filename=--roundtrip
ROUNDTRIP — parse each string by its own rules vs the other locale's rules
------------------------------------------------------------------
  US string 1,234.5   parsed as US = 1234.5    parsed as DE = 1.2345
  DE string 1.234,5   parsed as DE = 1234.5    parsed as US = 1.2345
  fixed  1234.5       parsed fixed = 1234.5
------------------------------------------------------------------
  cross-locale parsing silently returns the wrong number; the fixed format round-trips.
```

Read the diagonal: each locale's string, parsed by its own rules, returns the correct 1234.5 — within a single locale everything is consistent. The off-diagonal is the disaster. The US string "1,234.5" parsed with DE rules becomes 1.2345, because DE treats the comma as a decimal and the period as thousands. The DE string "1.234,5" parsed with US rules also becomes 1.2345, for the mirror reason. Both cross-parses land on 1.2345 — a value off from the true 1234.5 by almost exactly a factor of a thousand — and neither raised an error, because 1.2345 is a perfectly valid float. That is the signature of this bug: not a crash, but a number quietly a thousand times wrong, propagating through every calculation downstream. The fixed format, parsed with fixed rules, returns 1234.5, and it would return 1234.5 on any machine in any locale, because its parser does not consult the locale at all. The lesson is the general portability rule in numeric form: a value that crosses a boundary must be serialized in one canonical representation, and numbers written in the display locale are not that.

<svg role="img" aria-label="The US string cross-parsed as DE gives 1.2345, a thousandfold error; the fixed string parses to 1234.5 correctly everywhere" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">parse a locale string with the wrong locale's rules</text>
  <rect x="10" y="20" width="70" height="18" fill="none" stroke="var(--s1)"/><text x="16" y="33" fill="var(--ink)" font-size="8">US "1,234.5"</text>
  <line x1="80" y1="29" x2="120" y2="29" stroke="var(--s2)"/><polygon points="120,26 126,29 120,32" fill="var(--s2)"/><text x="84" y="24" fill="var(--s2)" font-size="6">as DE</text>
  <rect x="128" y="20" width="70" height="18" fill="var(--s2)" opacity="0.3"/><text x="134" y="33" fill="var(--s2)" font-size="8">1.2345 ✗</text>
  <text x="204" y="33" fill="var(--muted)" font-size="7">×1000 off</text>
  <rect x="10" y="56" width="70" height="18" fill="none" stroke="var(--ink)"/><text x="20" y="69" fill="var(--ink)" font-size="8">fixed "1234.5"</text>
  <line x1="80" y1="65" x2="120" y2="65" stroke="var(--s1)"/><polygon points="120,62 126,65 120,68" fill="var(--s1)"/><text x="84" y="60" fill="var(--muted)" font-size="6">any</text>
  <rect x="128" y="56" width="70" height="18" fill="var(--s1)"/><text x="140" y="69" fill="var(--panel)" font-size="8">1234.5 ✓</text>
  <text x="6" y="92" fill="var(--muted)" font-size="8">cross-locale parsing is silently wrong; the fixed format is right in every locale</text>
</svg>
^ Cross-parsing the US string with DE rules yields 1.2345 — a thousandfold error with no exception — while the fixed "1234.5" parses to 1234.5 under any locale's reader that uses fixed rules.

## Definition of done

The self-test pins the failure and the fix: the locale strings differ, each parses correctly under its own locale but cross-parses to the wrong value, and the fixed format round-trips.

```python filename=modules/teaching-and-portability/code/numlocale-inter-01/numlocale.py:98-106 COMPLETE
    strings_differ = us_s != de_s
    print("  the US and DE strings differ for the same value = %s (%r vs %r)" % (strings_differ, us_s, de_s))

    same_locale_ok = parse(us_s, us["decimal"], us["thousands"]) == v and parse(de_s, de["decimal"], de["thousands"]) == v
    print("  each string parsed by its OWN locale gives the right value = %s" % same_locale_ok)

    cross_parse_wrong = parse(us_s, de["decimal"], de["thousands"]) != v and parse(de_s, us["decimal"], us["thousands"]) != v
    print("  parsing across locales gives the WRONG value = %s (US-as-DE %s, DE-as-US %s)"
          % (cross_parse_wrong, parse(us_s, de["decimal"], de["thousands"]), parse(de_s, us["decimal"], us["thousands"])))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the locale strings differ and cross-parse to wrong values; the fixed format round-trips everywhere
----------------------------------------------------------------------------------------------------------------
  the US and DE strings differ for the same value = True ('1,234.5' vs '1.234,5')
  each string parsed by its OWN locale gives the right value = True
  parsing across locales gives the WRONG value = True (US-as-DE 1.2345, DE-as-US 1.2345)
  the fixed format round-trips to the exact value = True ('1234.5' -> 1234.5)
  the fixed format is a period decimal with no thousands separator = True ('1234.5')
```

**Done means the locale hazard and its fix are both proven: the same value 1234.5 formats as "1,234.5" (US) and "1.234,5" (DE), each parses correctly under its own locale but cross-parses to 1.2345 — a thousandfold error with no exception — while the fixed format "1234.5" (period decimal, no thousands separator) round-trips to 1234.5 under a locale-independent parser everywhere.**

## Boss fight

Predict the two places the locale hazard hides beyond the decimal point. It is tempting to think "always use a period decimal" is the whole rule.

The first trap is that the locale governs far more than the decimal separator, and other locale-sensitive conversions bite the same way. Date formats (day/month/year order), currency symbols and their placement, the digits themselves (some locales use non-ASCII digit glyphs), list separators (the CSV "comma-separated" file uses a semicolon in comma-decimal locales, precisely so the decimal comma is not confused with the field comma), sort order (covered by locale collation), and even uppercasing (the Turkish dotless-i) all change with the locale. So "format numbers locale-independently" is one instance of a general rule: any value serialized for a machine must use a fixed, documented representation, and any function whose behavior depends on the ambient locale — number formatting, date formatting, case conversion, sorting, string comparison — must be pinned to a fixed convention (often the "C" or "invariant" locale) when its output crosses a boundary. The bug is not the decimal point specifically; it is trusting the ambient locale for data.

```python filename=modules/teaching-and-portability/code/numlocale-inter-01/numlocale.py:108-113 COMPLETE
    fx = fmt(v, fixed["decimal"], fixed["thousands"])
    fixed_roundtrips = parse(fx, fixed["decimal"], fixed["thousands"]) == v
    print("  the fixed format round-trips to the exact value = %s (%r -> %s)" % (fixed_roundtrips, fx, parse(fx, fixed["decimal"], fixed["thousands"])))

    fixed_is_clean = fixed["decimal"] == "." and fixed["thousands"] == "" and "," not in fx
    print("  the fixed format is a period decimal with no thousands separator = %s (%r)" % (fixed_is_clean, fx))
```

The second trap is that even the fixed format has a floating-point round-trip subtlety, and using a display-oriented format loses precision. Formatting a float for humans typically rounds to a fixed number of decimals ("%.2f"), which is fine for display but destroys precision if it is what you serialize — 0.1 + 0.2 rounded to two places is 0.30, and a value like 1/3 becomes 0.33, unrecoverable. For machine interchange you want the *shortest string that round-trips exactly back to the same float*, which is what a language's `repr` (Python) or round-trip formatter provides, not a fixed-decimal display format. And the receiving parser must be the locale-independent one — in Python, `float()` and `repr()` always use a period and never consult the locale, which is exactly why they are the right tools and `locale.atof` / `"%n"`-style formatting are exactly wrong for data. So the full rule has two parts: use a fixed, locale-independent *convention* (period decimal, no grouping) so different machines agree on what the characters mean, and use a *round-trip-precise* serialization (repr, not rounded display) so no precision is lost — display formatting fails on both counts, which is why it must stay at the human-facing edge and never in the data path.

**Serialize any number a machine will read back in a fixed, locale-independent format — period decimal, no thousands separator, parsed with a locale-independent parser — because the display locale's decimal and thousands conventions differ across machines and make a value silently wrong (often ×1000) with no error; and remember this is one case of a general rule (dates, case, sorting, list separators are locale-sensitive too, so pin them to a fixed convention at any boundary) and that the interchange format must also be round-trip-precise (a language's repr/round-trip formatter, not a rounded display format), so display formatting stays at the human edge and never in the data path.**

## External resources

Your language's locale and number-formatting documentation (for example Python's `locale` module versus `repr`/`float`, and .NET's `CultureInfo.InvariantCulture`) — which functions consult the ambient locale, which are locale-independent, and how to force the invariant/"C" locale for interchange.

Any reference on data serialization formats and internationalization (i18n/l10n) — the distinction between formatting for display and serializing for interchange, and the locale-sensitive operations (dates, collation, case, list separators) that share this hazard.

The companion "specify encoding='utf-8' when you read and write" and "seed the random generator" modules — all three are cases where a program silently inherits an ambient, per-environment setting (text encoding, RNG seed, number locale) that must be pinned explicitly for output to be reproducible and portable across machines.
