---
id: collation-inter-01
title: Sort by codepoint for a canonical output, not locale collation — the same words sort into a different order, and a different hash, on another machine
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: Sorting looks like one of the most deterministic operations there is, and within a single machine it is — but the comparison it uses is not universal. A codepoint sort orders characters by their numeric code point, fixed everywhere: 'z' (122) before 'é' (233), every uppercase letter before every lowercase one. A locale collation orders text the way a reader of that locale expects instead: it folds accents so 'é' sorts near 'e', folds or interleaves case, and applies language-specific rules that Swedish, German, and French disagree on. So the collation order is a function of the machine's locale setting and the version of the collation data installed, and two systems can sort the identical list into two different orders. For text about to be shown to a person, the collation order is right; the trap is using it where the output must be reproducible. A very common pattern is to sort a collection before hashing, serializing, or diffing it, precisely to get a canonical form independent of insertion order — and if that sort uses locale collation, the canonical form is no longer canonical: the same data hashes to different values on different machines, content-addressed dedup treats identical data as distinct, and a diff shows changes that are only reorderings. The fix is to sort by codepoint whenever the result must be reproducible, since a codepoint sort is a pure function of the data with no hidden locale input. On a fixture of three words, the codepoint sort orders 'éclair' after 'zebra' (é's code is above z's) while a locale collation folds the accent and orders it after 'apple', and the two orders serialize to different strings with different hashes.
eli5: Alphabetizing seems like it should give one right answer, but it doesn't — different countries alphabetize differently, especially for letters with accent marks. On one computer "éclair" might file next to "eclair", on another it might go all the way at the end after "z", because the computer's language settings decide the rules. That's fine when you're just showing a list to a person. But if you sort a list and then take a "fingerprint" of it (a hash) to check two computers have the same data, the two computers will sort it differently, get different fingerprints, and wrongly think the data doesn't match. The fix is to sort by the letters' fixed numeric codes, which is the same everywhere, whenever the sorted result needs to be identical across machines.
---

## Why this module

There is a hidden assumption inside "sort the list to make the output canonical": that sorting is a fixed function of the data. It is, if the comparison is fixed — but string comparison is one of the places a locale sneaks in. The instinct behind sorting-for-canonicalization is exactly right (remove dependence on insertion order so the same set always produces the same bytes), and it is defeated when the sort itself introduces a new dependence, on the machine's locale, that is even harder to spot than insertion order.

Codepoint order and collation order are genuinely different orderings, not two spellings of one. Codepoint order compares the raw code points, so accented and uppercase letters land wherever their numbers put them — often far from where a human would file them. Collation order encodes human expectations: accents fold toward their base letter, case is folded or interleaved, and the rules are language-specific, so "the alphabetical order" is not one thing across locales. Both are legitimate; they answer different questions. The error is answering the reproducibility question with the display answer.

This module sorts the same words by codepoint and by a locale-style collation, then hashes each result, showing the "canonical" form depend on the collation.

**A locale collation folds accents and case by language-specific rules that vary across machines, so sorting a canonical form with it makes the same data order and hash differently by locale — reproducible output must sort by codepoint, a fixed function of the data.**

## Concepts

The fixture is three words, one accented, plus a small accent map that folds accented letters to their base — a stand-in for a locale collation.

```json filename=modules/teaching-and-portability/code/collation-inter-01/collation.json:3-4 COMPLETE
  "words": ["zebra", "éclair", "apple"],
  "accent_map": {"é": "e", "è": "e", "ê": "e", "á": "a", "à": "a", "ñ": "n"}
```

Two sorts. The codepoint sort is plain `sorted`, ordering by numeric code point — fixed on every machine. The collation sort orders by an accent-folded, case-folded key, modeling how a locale collation treats 'é' like 'e'. Both feed a serialize-and-hash to produce a canonical form.

```python filename=modules/teaching-and-portability/code/collation-inter-01/collation.py:33-50 COMPLETE
def codepoint_sort(words):
    """Order by numeric code point -- fixed on every machine."""
    return sorted(words)


def collation_sort(words, accent_map):
    """Order by an accent-folded, case-folded key -- a stand-in for a locale collation."""
    def key(s):
        return "".join(accent_map.get(c, c).lower() for c in s)
    return sorted(words, key=key)


def serialize(words):
    return "|".join(words)


def digest(words):
    return hashlib.sha256(serialize(words).encode("utf-8")).hexdigest()[:8]
```

The codepoint sort reads nothing but the strings; the collation sort reads the fold rules, which on a real machine come from the locale. That extra input is what makes the collation order vary and the codepoint order not.

<svg role="img" aria-label="The word éclair placed differently by two sorts: codepoint puts it after zebra because é's code 233 exceeds z's 122, collation folds é to e and puts it after apple" viewBox="0 0 320 120">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">where does 'éclair' sort?</text>
  <text x="14" y="36" font-size="8" fill="var(--s1)">codepoint</text>
  <g font-size="7.5" fill="var(--panel)">
  <rect x="80" y="26" width="44" height="14" fill="var(--s1)"/><text x="86" y="36">apple</text>
  <rect x="126" y="26" width="44" height="14" fill="var(--s1)"/><text x="132" y="36">zebra</text>
  <rect x="172" y="26" width="50" height="14" fill="var(--ink)"/><text x="178" y="36">éclair</text>
  </g>
  <text x="226" y="36" font-size="7" fill="var(--ink)">é (233) &gt; z (122)</text>
  <text x="14" y="64" font-size="8" fill="var(--s2)">collation</text>
  <g font-size="7.5" fill="var(--panel)">
  <rect x="80" y="54" width="44" height="14" fill="var(--s2)"/><text x="86" y="64">apple</text>
  <rect x="126" y="54" width="50" height="14" fill="var(--ink)"/><text x="132" y="64">éclair</text>
  <rect x="178" y="54" width="44" height="14" fill="var(--s2)"/><text x="184" y="64">zebra</text>
  </g>
  <text x="226" y="64" font-size="7" fill="var(--ink)">é folds to e</text>
  <text x="14" y="96" font-size="7.5" fill="var(--muted)">same three words, two orders — the accented word is placed by different rules</text>
</svg>
^ Codepoint order places 'éclair' last because é's code point (233) is above z's (122); collation order folds é to e and places 'éclair' second, near 'apple'. The same three words produce two different orderings depending on which comparison rule is used.

**The codepoint sort depends only on the strings; the collation sort depends on the fold rules the locale supplies — so the codepoint order is the same everywhere and the collation order is not.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the canonicalization step of a content-hashing pipeline, reduced to three words so every order is checkable by hand.

Run `--sort` to see the two orders.

```text filename=collation.py --sort
  codepoint : ['apple', 'zebra', 'éclair']
  collation : ['apple', 'éclair', 'zebra']
```

Codepoint order is apple, zebra, éclair — 'éclair' last, because its first letter's code point (233) exceeds every ASCII letter's. Collation order is apple, éclair, zebra — 'éclair' folded to sort as if it began with 'e', landing between apple and zebra where a French or English reader would file it. Neither is wrong; they are different orderings of the same three words, one by raw code point and one by human alphabetization.

Now `--hash` canonicalizes and fingerprints each order.

```python filename=modules/teaching-and-portability/code/collation-inter-01/collation.py:67-67 COMPLETE
    cp, col = codepoint_sort(words), collation_sort(words, amap)
```

The two fingerprints do not match.

```text filename=collation.py --hash
  codepoint : apple|zebra|éclair            0a8e8b11
  collation : apple|éclair|zebra            0876c9c6
```

Serializing each order gives a different string — 'apple|zebra|éclair' versus 'apple|éclair|zebra' — and therefore a different hash, 0a8e8b11 versus 0876c9c6. If this hash is the canonical fingerprint of the data (a content address, a cache key, a change-detection digest), then two machines that sort with different collations will compute different fingerprints for identical data. The machine that sorts by codepoint gets 0a8e8b11 every time regardless of locale; the machine that sorts by its locale collation gets whatever its locale dictates. Content that is byte-for-byte identical is judged different, and the bug appears only when the pipeline runs somewhere with a different locale than where it was written and tested.

<svg role="img" aria-label="Two canonical forms of the same data: codepoint order hashes to 0a8e8b11, collation order to 0876c9c6, so identical data gets two fingerprints" viewBox="0 0 320 110">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">'canonical' fingerprint of the same three words</text>
  <text x="10" y="40" font-size="8" fill="var(--s1)">codepoint</text>
  <rect x="90" y="30" width="130" height="16" fill="var(--s1)"/><text x="98" y="42" font-size="7.5" fill="var(--panel)">apple|zebra|éclair</text>
  <text x="226" y="42" font-size="8" fill="var(--s1)">0a8e8b11</text>
  <text x="10" y="70" font-size="8" fill="var(--s2)">collation</text>
  <rect x="90" y="60" width="130" height="16" fill="var(--s2)"/><text x="98" y="72" font-size="7.5" fill="var(--panel)">apple|éclair|zebra</text>
  <text x="226" y="72" font-size="8" fill="var(--s2)">0876c9c6</text>
  <text x="10" y="98" font-size="7.5" fill="var(--muted)">identical data, two fingerprints — the 'canonical' form depends on the locale</text>
</svg>
^ The same three words canonicalize to two different strings and two different hashes depending on the sort. A codepoint sort always yields 0a8e8b11; a locale collation yields whatever the locale dictates, so identical data gets machine-dependent fingerprints.

**The codepoint order hashes to 0a8e8b11 and the collation order to 0876c9c6 for identical data — so a canonical form built on locale collation is not canonical; it varies by machine, breaking hashing, dedup, and diffing.**

## Build

The self-test establishes the divergence: the two orders differ, and they hash to different canonical forms.

```python filename=modules/teaching-and-portability/code/collation-inter-01/collation.py:82-91 COMPLETE
    orders_differ = cp != col
    print("  the codepoint and collation orders differ = %s" % orders_differ)
    print("    codepoint: %s" % cp)
    print("    collation: %s" % col)

    hashes_differ = digest(cp) != digest(col)
    print("  the two orders hash to different canonical forms = %s (%s != %s)" % (hashes_differ, digest(cp), digest(col)))

    codepoint_is_pure = codepoint_sort(words) == codepoint_sort(list(reversed(words)))
    print("  the codepoint sort is the same regardless of input order = %s" % codepoint_is_pure)
```

Then the reassurance that the fix is stable: the fixture really contains an accented word the orders place differently, and the codepoint hash is the same regardless of input order — a true canonical form.

```python filename=modules/teaching-and-portability/code/collation-inter-01/collation.py:93-96 COMPLETE
    accent_moves = words != codepoint_sort(words) and any(c in amap for w in words for c in w)
    print("  the fixture contains an accented word that the two orders place differently = %s" % accent_moves)

    codepoint_hash_stable = digest(codepoint_sort(words)) == digest(codepoint_sort(list(reversed(words))))
    print("  the codepoint hash is stable across input orders = %s (%s)" % (codepoint_hash_stable, digest(cp)))
```

Running the check confirms every clause.

```text filename=collation.py --check
  the codepoint and collation orders differ = True
    codepoint: ['apple', 'zebra', 'éclair']
    collation: ['apple', 'éclair', 'zebra']
  the two orders hash to different canonical forms = True (0a8e8b11 != 0876c9c6)
  the codepoint sort is the same regardless of input order = True
  the fixture contains an accented word that the two orders place differently = True
  the codepoint hash is stable across input orders = True (0a8e8b11)
```

**The check shows the two sorts producing different orders and hashes, and the codepoint sort producing a stable hash regardless of input order — the property a canonical form needs, which locale collation lacks.**

## Definition of done

Done means the collation order is shown to differ from the codepoint order and to hash differently, while the codepoint sort is a stable, input-order-independent canonical form. The stability clause is the specification of "canonical": a hash used as a fingerprint must depend only on the data's content, and the codepoint sort delivers that where locale collation does not, because collation smuggles the machine's locale into a value that is supposed to depend on the data alone.

Two clarifications carry this to real code. First, the split is by purpose, the same split as the other locale gotchas: use codepoint (byte) ordering for anything machine-facing — hashing, deduplication, diffing, sort-merge joins, canonical serialization, database keys that must match across systems — and reserve locale collation for the last mile before a human sees the list. In practice this means sorting with the default codepoint comparison for canonical forms and only applying a locale-aware collator (or a database `COLLATE` clause) at display time. A frequent production version of this bug is a database index or `ORDER BY` whose collation differs between environments, or between a database's collation and an application's in-memory sort, so "sorted" results disagree and merge or comparison logic breaks. Second, codepoint order is not "the alphabetical order a user wants" — it puts all uppercase before lowercase and accented letters after ASCII — so it is the wrong choice for display, and the point is not that codepoint order is better but that it is fixed. When you truly need human-correct ordering that is also reproducible, pin the collation explicitly (a specific Unicode collation table and version, e.g. ICU with a named locale and version), so it is a declared input rather than the ambient machine setting.

<svg role="img" aria-label="Split by purpose: codepoint order for machine-facing canonical forms (hash, dedup, diff, keys); locale collation only for display; pin the collation if you need reproducible human order" viewBox="0 0 320 120">
  <rect x="14" y="22" width="150" height="42" fill="none" stroke="var(--s1)"/>
  <text x="22" y="37" font-size="7.5" fill="var(--s1)">canonical / machine-facing</text>
  <text x="22" y="49" font-size="7" fill="var(--ink)">hash, dedup, diff, keys</text>
  <text x="22" y="59" font-size="7" fill="var(--ink)">→ codepoint (fixed)</text>
  <rect x="176" y="22" width="130" height="42" fill="none" stroke="var(--s2)"/>
  <text x="184" y="37" font-size="7.5" fill="var(--s2)">display to a human</text>
  <text x="184" y="49" font-size="7" fill="var(--ink)">→ locale collation,</text>
  <text x="184" y="59" font-size="7" fill="var(--ink)">at the last step</text>
  <text x="14" y="84" font-size="7.5" fill="var(--muted)">watch DB ORDER BY / index collation differing across environments</text>
  <text x="14" y="104" font-size="7.5" fill="var(--ink)">need reproducible human order? pin the collation table and version explicitly</text>
</svg>
^ Sort by codepoint for canonical, machine-facing outputs and reserve locale collation for the last display step; a common real bug is a database's ORDER BY or index collation differing across environments. When reproducible human ordering is genuinely needed, pin the collation table and version so it is a declared input, not the ambient locale.

**Done means the collation order differs and re-hashes while the codepoint sort is a stable canonical form — so reproducible output sorts by codepoint, locale collation is reserved for display, and any human ordering that must reproduce has its collation table and version pinned.**

## Boss fight

A content-addressed cache keys entries by hashing a sorted list of tags. It works in development and in CI, but after deploying to a new region the cache hit rate collapses: entries written by the new region's servers are never found by the others, even for identical tag sets. The code sorts the tags and hashes the result, and nothing in it changed. What happened, and how do you fix it?

The new region's servers are sorting the tags with a different locale collation, so identical tag sets are canonicalized into different orders, hashed to different keys, and never match entries written elsewhere. The sort looks deterministic and the code did not change, but the comparison it uses reads the machine's locale, and the new region's servers have a different locale (or a different version of the collation data) than the original ones — so tags containing accented characters, or mixed case, or any letters the two collations order differently, sort into a different sequence there. Because the cache key is the hash of the sorted list, a different order means a different key for the same data, which is exactly the collapsed hit rate: identical tag sets produce region-dependent keys. The fix is to make the canonicalizing sort locale-independent: sort the tags by codepoint (the default byte/codepoint comparison, with no locale collator applied) before hashing, so the canonical order — and therefore the key — is a pure function of the tags and identical on every machine in every region. Reserve locale-aware collation for places where a human reads the tags, never in the key computation. To prevent the class of bug, audit anywhere a sort feeds a hash, a dedup, a diff, or a cross-system comparison and confirm it uses codepoint order, not the ambient locale; and if any canonical form legitimately needs human ordering, pin the exact collation (a named Unicode collation table and version) so it is a declared, portable input rather than whatever each region's machine happens to be set to. Also flag the same hazard for database indexes and ORDER BY, where a collation mismatch between environments produces the same silent disagreement.

## External resources

The Unicode Collation Algorithm and its implementations (ICU collation, database `COLLATE` clauses, and the distinction between codepoint/binary ordering and locale-tailored collation) — why alphabetical order is language-specific and versioned, and how to pin a collation when reproducible human ordering is required.

Guidance on canonicalization and content addressing (canonical serialization forms, and the practice of using binary/codepoint ordering for hashing, dedup, and cross-system comparison) — the portability discipline of keeping the ambient locale out of any sort whose result must be identical across machines.
