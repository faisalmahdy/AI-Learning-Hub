---
id: normalize-inter-01
title: Normalize Unicode (NFC) before you compare or hash — or the same visible text in two encodings is silently unequal
topic: teaching-and-portability
level: intermediate
status: ready
time: 16 min
summary: The character e-with-an-acute-accent can be written two ways in Unicode — precomposed as a single code point (U+00E9), or decomposed as a plain e (U+0065) followed by a combining acute accent (U+0301) that stacks onto it. Both render as the identical glyph, but to the computer they are different strings: different lengths, different bytes, different hashes. So the same visible word is not equal to itself across the two encodings, and a comparison that should match silently fails — a lookup misses, a dedup keeps both copies, a cache never hits, a signature verifies as different. This bites when text is typed on two keyboards, pasted from two apps, or moved between operating systems (macOS stores filenames decomposed, most Linux precomposed). The fix is one call before any comparison, hash, or key: Unicode normalization to a canonical form (NFC), which rewrites any two canonically equivalent strings to be byte-for-byte identical. On a fixture, the precomposed string is 4 code points and the decomposed one is 5, unequal with different hashes though both display as the same accented "café" — and after NFC both are 4 code points, equal, with one shared hash.
eli5: The little accent mark over a letter can be stored two ways: as part of the letter, or as a separate mark placed on top of a plain letter. On screen both look exactly the same — a letter with an accent. But the computer sees "one thing" versus "two things stacked," and decides they're different words, so searching for one won't find the other. It's like writing "café" with a pre-printed é versus typing "e" and then stamping an accent on it: identical to your eyes, different to a strict machine. Squash both into one standard form first, and they match.
---

## Why this module

Two strings can be the same text to every human who reads them and different objects to every machine that compares them, because Unicode lets the same character be built more than one way — and equality, hashing, and lookup all run on the build, not the appearance.

Unicode has to represent accented and composite characters, and it offers two routes. The precomposed route assigns a single code point to the whole accented character: é is U+00E9, one unit. The decomposed route builds it from parts: a base letter e (U+0065) followed by a combining mark, the acute accent U+0301, which the renderer stacks onto the e. Both routes produce the identical glyph on screen — there is no font, no zoom level, no rendering that reveals which one you have. But underneath, one is a string of length 1 for that character and the other is length 2, with different bytes and therefore a different hash. So "café" spelled with a precomposed é and "café" spelled with a decomposed é are, to `==`, two different strings, and every operation built on `==` — dictionary lookup, set membership, deduplication, cache keys, content hashes, signature verification — treats them as unrelated.

**The same visible character can be encoded as one code point or as a base plus combining marks, so two strings that render identically can be unequal with different lengths and hashes — and every comparison, key, and hash runs on the encoding, not the glyph.**

This is not a rare edge case; it is a routine cross-system collision. Different keyboards and input methods emit different forms, copy-paste carries whatever form the source used, and — most notoriously — operating systems disagree: macOS's filesystem stores names in decomposed form while most Linux filesystems store them precomposed, so a file created on one and looked up by name on the other silently is-not-found. The fix is a single normalization step before any comparison, hash, or key: convert the string to a canonical form, NFC (Normalization Form C), which composes characters back to their precomposed spelling so that any two canonically equivalent strings become byte-for-byte identical. Normalize both sides and "café" equals "café" again. This module shows the two forms diverging and NFC collapsing them.

## Concepts

**A code point sequence** is what a string actually is. The precomposed form has one code point for the accented character; the decomposed form has two (base + combining mark). Same glyph, different sequence.

```python filename=modules/teaching-and-portability/code/normalize-inter-01/normalize.py:44-48 COMPLETE
def build(data):
    """Reconstruct the two strings from their code points, so the file is unambiguous about which is which."""
    pre = "".join(chr(c) for c in data["precomposed_codepoints"])
    dec = "".join(chr(c) for c in data["decomposed_codepoints"])
    return pre, dec
```

**Canonical equivalence** means two sequences represent the same abstract text even though their code points differ. Equality and hashing do not know about canonical equivalence — they compare code points.

**Normalization (NFC)** rewrites a string into one canonical composed form, so any two canonically equivalent strings become identical code point sequences.

```python filename=modules/teaching-and-portability/code/normalize-inter-01/normalize.py:61-63 COMPLETE
def nfc(s):
    """Normalization Form C: rewrite the string into its canonical composed form."""
    return unicodedata.normalize("NFC", s)
```

<svg role="img" aria-label="Precomposed café is four code points ending in U+00E9; decomposed café is five code points ending in e plus U+0301; NFC collapses both to the four-code-point form" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">both render 'café' — but as different code points</text>
  <g font-size="7">
  <rect x="10" y="22" width="26" height="16" fill="var(--s1)"/><text x="18" y="33" fill="var(--panel)">c</text><rect x="38" y="22" width="26" height="16" fill="var(--s1)"/><text x="46" y="33" fill="var(--panel)">a</text><rect x="66" y="22" width="26" height="16" fill="var(--s1)"/><text x="74" y="33" fill="var(--panel)">f</text><rect x="94" y="22" width="40" height="16" fill="var(--s2)"/><text x="100" y="33" fill="var(--panel)">U+00E9</text>
  <text x="140" y="33" fill="var(--muted)">precomposed: 4</text>
  <rect x="10" y="46" width="26" height="16" fill="var(--s1)"/><text x="18" y="57" fill="var(--panel)">c</text><rect x="38" y="46" width="26" height="16" fill="var(--s1)"/><text x="46" y="57" fill="var(--panel)">a</text><rect x="66" y="46" width="26" height="16" fill="var(--s1)"/><text x="74" y="57" fill="var(--panel)">f</text><rect x="94" y="46" width="26" height="16" fill="var(--s1)"/><text x="102" y="57" fill="var(--panel)">e</text><rect x="122" y="46" width="40" height="16" fill="var(--s2)"/><text x="128" y="57" fill="var(--panel)">U+0301</text>
  <text x="168" y="57" fill="var(--muted)">decomposed: 5</text>
  </g>
  <line x1="10" y1="72" x2="290" y2="72" stroke="var(--grid)"/>
  <text x="10" y="88" fill="var(--muted)" font-size="7">NFC(both) →</text>
  <g font-size="7"><rect x="70" y="80" width="20" height="14" fill="var(--s1)"/><rect x="92" y="80" width="20" height="14" fill="var(--s1)"/><rect x="114" y="80" width="20" height="14" fill="var(--s1)"/><rect x="136" y="80" width="34" height="14" fill="var(--s2)"/><text x="140" y="90" fill="var(--panel)">U+00E9</text></g>
  <text x="180" y="90" fill="var(--muted)" font-size="7">one canonical form, 4 code points</text>
</svg>
^ Precomposed "café" ends in a single U+00E9 (4 code points); decomposed "café" ends in e + U+0301 (5 code points); NFC rewrites both to the 4-code-point composed form so they match.

**Put text into one canonical form (NFC) before you compare, hash, deduplicate, or key it — because "looks the same" is not "is the same" in Unicode, and every equality-based operation runs on the code points, not the glyph.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/normalize-inter-01/normalize.py

The fixture gives the two forms as code point lists so the file itself is unambiguous about which encoding is which.

```json filename=modules/teaching-and-portability/code/normalize-inter-01/normalize.json:3-5 COMPLETE
  "precomposed_codepoints": [99, 97, 102, 233],
  "decomposed_codepoints": [99, 97, 102, 101, 769],
  "label": "cafe + acute accent"
```

Run `--compare` to inspect the two strings.

```text filename=--compare
COMPARE — two encodings of the same visible text
------------------------------------------------------------------
  precomposed:  ['U+0063', 'U+0061', 'U+0066', 'U+00E9']  len 4  hash 850f7dc43910
  decomposed:   ['U+0063', 'U+0061', 'U+0066', 'U+0065', 'U+0301']  len 5  hash 81ef060bcd98
  equal as strings?  False
```

The two strings share their first three code points — c, a, f — and then diverge. The precomposed form ends in a single U+00E9, the accented e as one unit, for a total length of 4. The decomposed form ends in U+0065 (plain e) followed by U+0301 (the combining acute accent), for a length of 5. They render as the same four-letter word, but they are different lengths, different code point sequences, and consequently different hashes — 850f7dc43910 versus 81ef060bcd98. The `equal as strings?` check is False. A program that received "café" from two sources and compared them would conclude they are different words, and it would be right about the bytes and useless to the user, who typed the same thing twice. Nothing in the rendered text warned of the divergence; it lives entirely below the glyph.

<svg role="img" aria-label="Both strings display café, but one is 4 code points hashing to 850f and the other 5 code points hashing to 81ef, so they compare unequal" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">identical on screen, different underneath</text>
  <rect x="20" y="22" width="80" height="24" fill="none" stroke="var(--line)"/><text x="44" y="38" fill="var(--ink)" font-size="10">café</text>
  <rect x="200" y="22" width="80" height="24" fill="none" stroke="var(--line)"/><text x="224" y="38" fill="var(--ink)" font-size="10">café</text>
  <text x="20" y="60" fill="var(--muted)" font-size="7">4 code points · hash 850f…</text>
  <text x="200" y="60" fill="var(--muted)" font-size="7">5 code points · hash 81ef…</text>
  <text x="130" y="40" fill="var(--s2)" font-size="9">≠</text>
  <text x="6" y="82" fill="var(--muted)" font-size="8">the glyphs match; the code points, lengths, and hashes do not — so == says unequal</text>
</svg>
^ The two "café"s are visually identical but one is 4 code points hashing to 850f… and the other 5 code points hashing to 81ef…, so string equality returns False.

## Build

The consequence is a silent lookup miss. Run `--normalize`, which also keys a dictionary on one form and looks up the other.

```text filename=--normalize
NORMALIZE — NFC collapses both to one canonical form
------------------------------------------------------------------
  NFC(precomposed): ['U+0063', 'U+0061', 'U+0066', 'U+00E9']  len 4  hash 850f7dc43910
  NFC(decomposed):  ['U+0063', 'U+0061', 'U+0066', 'U+00E9']  len 4  hash 850f7dc43910
  equal after NFC?  True

  lookup decomposed in a dict keyed on precomposed:      MISS
  lookup after normalizing both to NFC:                  row-42
```

After NFC, both strings are the same four code points ending in U+00E9, equal, with the same hash — the decomposed form was composed back to the precomposed spelling. The dictionary demonstration is the real-world sting: a dict keyed on the precomposed "café" and queried with the decomposed "café" returns MISS, because the key hashed one way and the query the other. That is a cache that never hits, a user record that cannot be found, a deduplication that stores the same name twice. Normalize both the keys and the query to NFC and the lookup returns row-42 — the match that was always semantically correct and only ever byte-wrong. The fix is not clever; it is a single `unicodedata.normalize("NFC", s)` applied consistently at every boundary where text becomes a key, a hash, or a comparison. The discipline mirrors the other portability rules exactly: choose one canonical representation and impose it before the operation that depends on sameness, because the alternative is an equality that depends on invisible encoding history.

<svg role="img" aria-label="A dict keyed on the precomposed café misses when queried with the decomposed café, but hits row-42 after both are normalized to NFC" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">dict keyed on precomposed 'café' → 'row-42'</text>
  <rect x="10" y="24" width="120" height="18" fill="none" stroke="var(--s2)"/><text x="16" y="37" fill="var(--ink)" font-size="7">query: decomposed café</text>
  <line x1="130" y1="33" x2="168" y2="33" stroke="var(--s2)"/><polygon points="168,30 174,33 168,36" fill="var(--s2)"/>
  <rect x="176" y="24" width="60" height="18" fill="var(--s2)" opacity="0.3"/><text x="192" y="37" fill="var(--s2)" font-size="8">MISS ✗</text>
  <rect x="10" y="58" width="120" height="18" fill="none" stroke="var(--s1)"/><text x="16" y="71" fill="var(--ink)" font-size="7">query: NFC(café)</text>
  <line x1="130" y1="67" x2="168" y2="67" stroke="var(--s1)"/><polygon points="168,64 174,67 168,70" fill="var(--s1)"/>
  <rect x="176" y="58" width="60" height="18" fill="var(--s1)"/><text x="188" y="71" fill="var(--panel)" font-size="8">row-42 ✓</text>
  <text x="6" y="92" fill="var(--muted)" font-size="8">normalizing key and query to NFC turns a silent miss into the correct hit</text>
</svg>
^ Keyed on the precomposed form, the dict misses the decomposed query; normalizing both to NFC recovers the correct row-42, the match that was semantically right all along.

## Definition of done

The self-test pins both halves: the raw forms are unequal with different length and hash, and NFC makes them equal with the same hash, and is idempotent.

```python filename=modules/teaching-and-portability/code/normalize-inter-01/normalize.py:100-113 COMPLETE
    look_same_differ = pre != dec
    print("  the two forms are unequal though they render the same = %s" % look_same_differ)

    different_length = len(pre) != len(dec)
    print("  they have different code-point lengths = %s (%d vs %d)" % (different_length, len(pre), len(dec)))

    different_hash = digest(pre) != digest(dec)
    print("  they hash differently = %s (%s vs %s)" % (different_hash, digest(pre), digest(dec)))

    nfc_equal = nfc(pre) == nfc(dec)
    print("  NFC makes them equal = %s" % nfc_equal)

    nfc_same_hash = digest(nfc(pre)) == digest(nfc(dec))
    print("  NFC makes their hashes equal = %s (%s)" % (nfc_same_hash, digest(nfc(pre))))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the raw forms are unequal with different hash and length; NFC makes them equal, same hash, same length
--------------------------------------------------------------------------------------------------------------------
  the two forms are unequal though they render the same = True
  they have different code-point lengths = True (4 vs 5)
  they hash differently = True (850f7dc43910 vs 81ef060bcd98)
  NFC makes them equal = True
  NFC makes their hashes equal = True (850f7dc43910)
  NFC is idempotent (normalizing twice changes nothing) = True
```

**Done means the encoding divergence and its fix are proven: the precomposed (4 code points) and decomposed (5 code points) forms of the same visible "café" are unequal with different hashes (850f… vs 81ef…), while NFC rewrites both to the same 4-code-point form, equal, with one shared hash — and NFC is idempotent, so it is safe to apply everywhere.**

## Boss fight

Predict the two ways normalization is still not enough. It is tempting to think one `NFC` call makes all "same-looking" strings equal.

The first trap is that there are four normalization forms and they are not interchangeable, so both sides of a comparison must use the *same* one and the right one for the job. NFC and NFD are the canonical forms (composed and decomposed) — they preserve the text exactly and only reshuffle equivalent encodings — and either works for equality as long as both sides match, though NFC is the usual choice because it is more compact and matches most web and OS conventions. But NFKC and NFKD are *compatibility* forms, and they are lossy: they fold characters that are merely similar, turning the ligature ﬁ into "fi", full-width "Ａ" into "A", and the superscript ² into "2". That is exactly what you want for a search index or a username uniqueness check (so "①" and "1" collide) and exactly what you must not do to text you will display or round-trip, because it destroys distinctions the author made. Choosing the form is a real decision: canonical (NFC/NFD) to compare without changing meaning, compatibility (NFKC/NFKD) to fold look-alikes on purpose, and never mixing forms across a comparison.

```python filename=modules/teaching-and-portability/code/normalize-inter-01/normalize.py:56-58 COMPLETE
def codepoints(s):
    """The string's code points as U+XXXX names -- what the computer actually stores."""
    return ["U+%04X" % ord(ch) for ch in s]
```

The second trap is that normalization equates canonically-equivalent text but not visually-confusable text, and the gap between them is a security hole. Normalization will never make the Latin "a" (U+0061) equal to the Cyrillic "а" (U+0430) — they are different characters that happen to share a glyph in most fonts, not two encodings of one character — so a normalized comparison still treats "paypal" (Latin) and "pаypаl" (with Cyrillic а) as different, which is correct for text but is the mechanism behind homograph phishing domains and spoofed identifiers. Defending against that is a separate problem (confusable/skeleton detection, restricting to a single script), not normalization. And even within one script, normalization does not handle case, whitespace, or other folding — comparing user input usually needs case-folding and trimming *in addition to* NFC, applied in a fixed order. So the honest rule is layered: normalize to a canonical form for byte-level sameness, then apply whatever additional folding the use case demands (case, compatibility, confusables), consistently on every string that will be compared. NFC is the necessary first step, not the whole of "are these the same text?"

**Normalize text to a canonical Unicode form (NFC) before comparing, hashing, deduplicating, or keying, because the same visible character can be encoded as different code-point sequences that are unequal with different hashes — but use the same form on both sides, pick canonical (NFC/NFD) to compare without changing meaning versus compatibility (NFKC/NFKD) to fold look-alikes on purpose, and remember normalization equates canonically-equivalent text only: confusable characters from different scripts, case, and whitespace are separate folds you must apply on top, or a security-sensitive comparison is still wrong.**

## External resources

The Unicode Standard Annex #15 "Unicode Normalization Forms" — the definitive description of NFC, NFD, NFKC, and NFKD, canonical versus compatibility equivalence, and the idempotence and stability guarantees.

Your language's normalization API and any reference on Unicode security (UTS #39, "Unicode Security Mechanisms") — the practical call (`unicodedata.normalize` in Python) and the confusable/skeleton detection that normalization does not provide.

The companion "specify encoding='utf-8' when you read and write" and "normalize line endings before you hash" modules — all three are cases where text that looks identical differs in its byte or code-point representation, so any comparison, hash, or key over it must first impose one canonical form.
