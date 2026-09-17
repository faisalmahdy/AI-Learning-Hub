---
id: versioncmp-inter-01
title: Compare versions component-by-component as integers — "1.10" sorts before "1.9" as a string because the character "1" is less than "9"
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: A dotted version like 1.10.0 looks sortable as text, and for a while it is — while every component is a single digit, string order and version order happen to agree, and that coincidence is the trap. A version is not a word and not a decimal number; it is a sequence of integer components, and the correct comparison reads those components left to right and compares each as an integer. String comparison does something different: it compares raw characters one position at a time, so lining up "1.10" and "1.9", they share "1" and ".", and then one has "1" (the first digit of the component "10") while the other has "9" — the character "1" is less than "9", so the comparison declares "1.10" < "1.9" and stops, having never read "10" as the number ten. That is why the bug hides then bites: up through 1.9 every component is one digit and the naive string sort looks correct, but the first time a component reaches double digits — the 1.10 release — string order diverges and 1.10 is sorted as if it were older than 1.9, which lands on mature software that has shipped ten releases, where an update check or a "latest version" pick silently regresses. The fix is to parse before comparing: split on the dots, turn each component into an integer, and compare the resulting tuples, which order (1, 10) > (1, 9) correctly and put a shorter version before its extension. On a fixture the string sort puts 1.10 first (as the oldest) while the integer-tuple sort orders 1.2, 1.9, 1.9.1, 1.10 correctly.
eli5: Imagine putting house numbers in order, but you sort them like words instead of numbers. As words, "10" comes before "9", because you compare the first character and "1" is smaller than "9" — so you'd file house 10 before house 9, which is backwards. It works fine as long as all the numbers are single digits, so you might not notice for a long time; the mistake only shows up once a number hits double digits. Version numbers have the same trap: 1.10 is a later release than 1.9, but sorted like text, "1.10" lands before "1.9" because the computer compares "1" against "9" character by character and never realizes "10" means ten. The fix is to read each part as an actual number before comparing, so ten is correctly bigger than nine.
---

## Why this module

Versions are ordered data — the whole point of a version number is to say which release is newer — so any code that picks the latest version, checks whether an installed version is at least some minimum, or sorts a changelog depends on comparing them correctly. And comparison is exactly where the representation of a version as a string leads you astray, because the string looks like it already carries the order.

For single-digit components it does, which is what makes the mistake so durable. 1.0, 1.1, up through 1.9 sort identically as strings and as versions, so a string comparison passes every test anyone writes early in a project's life. The code ships, works for years, and accrues trust — all while carrying a latent bug that no single-digit release can trigger.

The trigger is the tenth release in some position: 1.10, or 2.0.10, or a jump to 1.11. The moment a component has two digits, character comparison and numeric comparison part ways, and they part ways silently — no error, just a wrong order, with the newest release sorted as if it were among the oldest. This module sorts a set of versions as strings and as integer tuples and shows the orders diverging exactly at the double-digit component.

**A version is a sequence of integer components, but as a string it is compared character by character; that agrees with version order only while every component is one digit, and diverges silently the moment a component reaches double digits.**

## Concepts

The root cause is that string comparison is lexicographic and per-character: it walks the two strings together and decides at the first position where they differ, comparing those two characters by their code points. It has no notion that a run of digits forms a number; "10" and "9" are compared at their first characters, "1" against "9", and since "1" < "9" the string "10..." loses immediately, no matter what follows. Numeric magnitude is simply not part of what a string comparison sees.

Version comparison needs the opposite: read each dot-separated component as an integer and compare integers, left to right. Ten is greater than nine as integers, so (1, 10) > (1, 9), which is the order releases actually shipped. The dots are separators between components, not decimal points — 1.10 is "one, then ten", not "one and one tenth" — which is another reason treating the whole thing as a number is also wrong; only the component-wise integer comparison is right.

Representing each version as a tuple of integers gets the rest for free, because tuple comparison already does the right thing. Comparing (1, 10) with (1, 9) compares 1 with 1, then 10 with 9, and stops — exactly the left-to-right component rule. And a shorter version orders before its extension: (1, 9) < (1, 9, 1), so 1.9 precedes 1.9.1, which matches how a patch release relates to its base. The single decision — parse to integer tuples before comparing — resolves the ordering, the double-digit case, and the differing-length case together.

<svg role="img" aria-label="Comparing 1.10 and 1.9: character comparison stops at 1 versus 9 and picks 1.9 as larger; integer comparison reads 10 versus 9 and picks 1.10 as larger" viewBox="0 0 440 130">
<text x="220" y="18" fill="var(--muted)" font-size="9" text-anchor="middle">comparing 1.10 and 1.9</text>
<text x="110" y="42" fill="var(--s2)" font-size="9" text-anchor="middle">character comparison</text>
<text x="110" y="62" fill="var(--ink)" font-size="10" text-anchor="middle">'1' vs '9'  ->  '1' &lt; '9'</text>
<text x="110" y="80" fill="var(--s2)" font-size="9" text-anchor="middle">so 1.10 &lt; 1.9 (wrong)</text>
<line x1="220" y1="30" x2="220" y2="100" stroke="var(--line)"/>
<text x="330" y="42" fill="var(--s1)" font-size="9" text-anchor="middle">integer comparison</text>
<text x="330" y="62" fill="var(--ink)" font-size="10" text-anchor="middle">10 vs 9  ->  10 &gt; 9</text>
<text x="330" y="80" fill="var(--s1)" font-size="9" text-anchor="middle">so 1.10 &gt; 1.9 (right)</text>
</svg>
^ At the deciding component, character comparison weighs "1" against "9" and integer comparison weighs 10 against 9 — opposite verdicts from the same version.

**String comparison is per-character and blind to numeric magnitude; version order is component-wise integer comparison, which a tuple of integers implements exactly, handling double digits and differing lengths in one rule: parse before you compare.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/versioncmp-inter-01. The fixture is a list of version strings including a double-digit component.

```json filename=modules/teaching-and-portability/code/versioncmp-inter-01/versioncmp.json:3-3 COMPLETE
  "versions": ["1.9", "1.10", "1.2", "1.9.1"]
```

Parsing splits on the dots and makes each component an integer — the correct comparison key.

```python filename=modules/teaching-and-portability/code/versioncmp-inter-01/versioncmp.py:34-36 COMPLETE
def parse(version):
    """Split on dots and turn each component into an integer -- the correct comparison key."""
    return tuple(int(part) for part in version.split("."))
```

The naive sort compares the raw strings lexicographically.

```python filename=modules/teaching-and-portability/code/versioncmp-inter-01/versioncmp.py:39-41 COMPLETE
def string_sorted(versions):
    """Sort by the raw string -- lexicographic, per-character."""
    return sorted(versions)
```

The correct sort compares the parsed integer tuples.

```python filename=modules/teaching-and-portability/code/versioncmp-inter-01/versioncmp.py:44-46 COMPLETE
def version_sorted(versions):
    """Sort by the integer-component tuple -- the correct version order."""
    return sorted(versions, key=parse)
```

First, the parsed forms. Run `--parse`:

```text filename=versioncmp.py --parse
PARSE — each version string as its integer-component tuple
--------------------------------------------
  1.9      -> (1, 9)
  1.10     -> (1, 10)
  1.2      -> (1, 2)
  1.9.1    -> (1, 9, 1)
--------------------------------------------
  the tuple is what carries the correct ordering
```

Each version becomes a tuple of integers: 1.10 becomes (1, 10), where the second component is the number ten, not the characters "1" and "0". This is the representation in which comparison is correct, and where 1.9.1 is visibly an extension of 1.9.

<svg role="img" aria-label="The version 1.10 shown two ways: as the character sequence 1 dot 1 0 compared per character, versus as the integer tuple (1, 10) where the second component is the number ten" viewBox="0 0 440 120">
<text x="110" y="24" fill="var(--ink)" font-size="10" text-anchor="middle">as string</text>
<rect x="50" y="35" width="24" height="24" fill="var(--panel)" stroke="var(--line)"/><text x="62" y="52" fill="var(--ink)" font-size="11" text-anchor="middle">1</text>
<rect x="74" y="35" width="24" height="24" fill="var(--panel)" stroke="var(--line)"/><text x="86" y="52" fill="var(--muted)" font-size="11" text-anchor="middle">.</text>
<rect x="98" y="35" width="24" height="24" fill="var(--s2)" stroke="var(--line)"/><text x="110" y="52" fill="var(--ink)" font-size="11" text-anchor="middle">1</text>
<rect x="122" y="35" width="24" height="24" fill="var(--panel)" stroke="var(--line)"/><text x="134" y="52" fill="var(--ink)" font-size="11" text-anchor="middle">0</text>
<text x="110" y="78" fill="var(--s2)" font-size="8" text-anchor="middle">compared at this '1'</text>
<text x="330" y="24" fill="var(--ink)" font-size="10" text-anchor="middle">as integer tuple</text>
<rect x="280" y="35" width="40" height="24" fill="var(--panel)" stroke="var(--line)"/><text x="300" y="52" fill="var(--ink)" font-size="11" text-anchor="middle">1</text>
<rect x="330" y="35" width="50" height="24" fill="var(--s1)" stroke="var(--line)"/><text x="355" y="52" fill="var(--ink)" font-size="11" text-anchor="middle">10</text>
<text x="330" y="78" fill="var(--s1)" font-size="8" text-anchor="middle">the number ten</text>
</svg>
^ As a string, "10" is two characters compared one at a time; as a tuple, it is the integer ten — the difference that decides the ordering.

Now the two sorts. Predict: the string sort puts 1.10 first (wrong), the version sort puts it last. Run `--sort`:

```text filename=versioncmp.py --sort
SORT — string order vs integer-component order
------------------------------------------------------
  string-sorted : ['1.10', '1.2', '1.9', '1.9.1']
  version-sorted: ['1.2', '1.9', '1.9.1', '1.10']
------------------------------------------------------
  the string sort puts 1.10 near the front, as if it were the oldest
```

The prediction holds. The string sort ranks 1.10 first — the newest release treated as the oldest — because "1.10" < "1.2" < "1.9" as text. The version sort orders them 1.2, 1.9, 1.9.1, 1.10, with 1.10 correctly last and 1.9.1 correctly between 1.9 and 1.10. The only difference is whether the components were compared as integers or as characters.

<svg role="img" aria-label="Two ordered lists: string sort 1.10, 1.2, 1.9, 1.9.1 with 1.10 wrongly first; version sort 1.2, 1.9, 1.9.1, 1.10 with 1.10 correctly last" viewBox="0 0 440 140">
<text x="110" y="20" fill="var(--s2)" font-size="9" text-anchor="middle">string sort (wrong)</text>
<text x="110" y="42" fill="var(--s2)" font-size="9" text-anchor="middle">1.10  &lt;  1.2  &lt;  1.9  &lt;  1.9.1</text>
<text x="110" y="60" fill="var(--muted)" font-size="8" text-anchor="middle">newest release ranked oldest</text>
<text x="330" y="90" fill="var(--s1)" font-size="9" text-anchor="middle">version sort (right)</text>
<text x="330" y="112" fill="var(--s1)" font-size="9" text-anchor="middle">1.2  &lt;  1.9  &lt;  1.9.1  &lt;  1.10</text>
<text x="330" y="130" fill="var(--muted)" font-size="8" text-anchor="middle">1.10 correctly last</text>
</svg>
^ The string sort strands 1.10 at the front as the apparent oldest; the integer-tuple sort places it last, where the newest release belongs.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that "1.10" < "1.9" as strings but 1.10 > 1.9 as tuples, that the two sort orders disagree, that only the version sort puts 1.10 last, and that tuple comparison also orders 1.9.1 after 1.9.

```python filename=modules/teaching-and-portability/code/versioncmp-inter-01/versioncmp.py:76-90 COMPLETE
    string_says_110_less_than_19 = "1.10" < "1.9"
    print("  as strings, '1.10' < '1.9' = %s (character '1' < '9')" % string_says_110_less_than_19)

    version_says_110_greater = parse("1.10") > parse("1.9")
    print("  as integer tuples, 1.10 > 1.9 = %s (%s > %s)" % (version_says_110_greater, parse("1.10"), parse("1.9")))

    ss = string_sorted(versions)
    vs = version_sorted(versions)
    orders_differ = ss != vs
    print("  the two sort orders disagree = %s" % orders_differ)

    string_puts_newest_wrong = ss[-1] != "1.10" and vs[-1] == "1.10"
    print("  the string sort fails to put 1.10 last (newest); the version sort does = %s" % string_puts_newest_wrong)

    tuple_handles_length = parse("1.9.1") > parse("1.9")
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if string and version order ever stop diverging on this fixture:

```text filename=versioncmp.py --check
SELF-TEST — string comparison misorders double-digit components; tuple-of-int comparison orders correctly
----------------------------------------------------------------------------------------------------------------
  as strings, '1.10' < '1.9' = True (character '1' < '9')
  as integer tuples, 1.10 > 1.9 = True ((1, 10) > (1, 9))
  the two sort orders disagree = True
  the string sort fails to put 1.10 last (newest); the version sort does = True
  tuple comparison orders 1.9.1 after 1.9 = True
```

**The self-test pins the exact character-level cause ("1" < "9") next to the correct integer result — proving the misordering is lexicographic comparison, not a typo or a bad fixture.**

## Definition of done

You can explain why string comparison is per-character and blind to numeric magnitude, and why that makes "1.10" < "1.9".
You can explain why the bug is invisible through single-digit releases and appears at the first double-digit component.
You can state the fix — parse each version into a tuple of integers and compare tuples — and why tuple comparison gives the component-wise rule for free.
You can explain why the dots are separators, not a decimal point, so treating the version as a single number is also wrong.
You can predict how the two methods order a shorter version against its extension (1.9 vs 1.9.1).

## Boss fight

Real version strings are messier than clean integers, and each mess breaks the naive parse. Pre-release tags — 1.10.0-rc1, 2.0.0-beta — contain non-numeric components that int() cannot parse, and by the semantic-versioning rule a pre-release actually orders before its release (1.10.0-rc1 < 1.10.0), which a plain integer tuple gets backwards or crashes on. Zero-padded components (1.09) and differing lengths compared against tags add more edge cases. The lesson sharpens: the integer-tuple parse is the correct core, but production version comparison follows a specification (SemVer) with defined rules for pre-release and build metadata, so the right move for real software is a library that implements that spec, not a hand-rolled split — while still never, ever, comparing the raw strings.

Now consider where this bug most often escapes notice: sorting for display versus selecting the maximum. A changelog sorted as strings looks slightly off and a human might catch it, but "pick the latest version to install" or "is the installed version at least the required minimum" makes a silent, consequential decision — installing 1.9 over 1.10 because 1.10 sorted lower, or rejecting a satisfactory version as too old. The same character-comparison bug is cosmetic in one place and a functional regression in another, which is why version comparison should go through one correct, tested routine used everywhere, rather than an ad-hoc string compare written inline at each call site.

**Real versions carry pre-release and build tags that plain integer tuples mis-order or crash on, so production comparison should follow the SemVer spec via a library — never raw string compare; and because the same bug is merely cosmetic when sorting for display but a functional regression when selecting the latest or checking a minimum, version comparison belongs in one correct shared routine.**

## External resources

The Semantic Versioning (SemVer) specification defines precedence rules for numeric components, pre-release identifiers, and build metadata — the correct ordering that a raw string compare violates.
Language ecosystems ship version-comparison utilities (Python's packaging.version, Node's semver, and similar) that implement the spec so you never hand-roll it.
The topic's own module on pinning dependency versions covers the adjacent reproducibility concern of which version you get, complementing this one on how versions are ordered.
