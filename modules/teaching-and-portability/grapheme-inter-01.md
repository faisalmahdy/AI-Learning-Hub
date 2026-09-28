---
id: grapheme-inter-01
title: Count and truncate by grapheme clusters, not code points — len() overcounts characters and a code-point slice splits an emoji
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: A grapheme cluster is what a person calls a character — a base letter plus the combining marks stacked on it, or an emoji assembled from several code points joined by zero-width joiners. Python's len() counts code points, not grapheme clusters, so it reports more characters than a reader sees for any string with such a cluster; JavaScript and Java count UTF-16 code units and overcount even further, splitting a single astral code point in two. None is the count a user means by "how many characters." The wrong count is annoying; wrong truncation is a bug: slicing a string to N code points to fit a column, a length limit, or a database field can cut inside a grapheme, dropping a combining accent (changing the letter) or splitting a multi-code-point emoji into a fragment. This is separate from Unicode normalization: NFC makes canonically-equivalent spellings equal and collapses some base-plus-mark sequences to one code point, but it does not reduce every grapheme to one code point — a zero-width-joined emoji, a skin-tone-modified emoji, and a base letter with no precomposed accented form all stay several code points after NFC — so length and truncation need grapheme awareness NFC does not provide. On a fixture of "Hi " plus a family emoji (man + zero-width joiner + woman + zero-width joiner + girl, five code points that render as one glyph) plus "!", len() reports 9 code points where a reader sees 5 characters; truncating to 4 characters by code points yields "Hi " plus a lone man — the family split apart — while truncating by grapheme clusters keeps the family whole, and NFC leaves the string 9 code points.
eli5: Think of a word written with some letters that are really little stacks — an accented letter is a base letter with an accent glued on top, and a family emoji is several tiny people holding hands, glued into one picture. If you count the glued-together pieces instead of the finished pictures, you get too many, because you counted the parts, not the characters a person sees. Worse, if you cut the word to make it shorter by chopping off pieces one at a time, you can chop right through the middle of a stack — knocking the accent off a letter, or slicing the family down to a single person still reaching for a hand that is gone. To count or cut safely, you have to work in whole finished characters, not in the little pieces they are built from.
---

## Why this module

Getting a string's length and cutting it to fit are the most ordinary operations there are, and they feel too simple to have a portability trap. You call len(), you slice with s[:n], and it works — on the strings you tested it with, which were almost certainly plain ASCII where one byte is one code point is one character.

Unicode breaks that chain of equalities. A character a person sees on screen — a grapheme cluster — can be built from several code points. An accented letter can be a base letter plus a separate combining accent. An emoji can be several emoji code points fused by invisible zero-width joiners into one glyph, the way a family emoji is a man, a woman, and a girl joined into a single picture. The finished character is one thing to a reader and several things to len().

So len() counts the pieces, not the characters, and reports a number no user would recognize. And slicing counts in pieces too, which is worse than a wrong number: a cut at a code-point boundary can land in the middle of a grapheme, knocking the accent off a letter or slicing a family emoji down to a lone figure. The bug hides through all of testing and appears on the first real name or emoji the code meets.

**A grapheme cluster — one character to a reader — can be several code points, but len() counts code points and slicing cuts on code-point boundaries, so len() overcounts the visible length and a slice can split a grapheme and mangle it.**

## Concepts

There are three different "lengths" of a string, and they disagree. The bytes are how many bytes the chosen encoding uses — UTF-8 gives an emoji four. The code points are the abstract Unicode scalars, what Python's len() counts. The grapheme clusters are the user-perceived characters. For plain ASCII all three are equal, which is exactly why the confusion survives so long; for anything richer they diverge, and only the grapheme count answers "how many characters does a person see."

<svg role="img" aria-label="Three stacked rows for the same string showing three counts. Bytes: many small cells. Code points (len): nine cells. Grapheme clusters: five cells. The counts get smaller as the unit gets closer to a perceived character." viewBox="0 0 440 140">
<text x="20" y="16" fill="var(--muted)" font-size="9">three ways to count the same string 'Hi (family)!'</text>
<text x="90" y="42" fill="var(--ink)" font-size="8" text-anchor="end">bytes (UTF-8)</text>
<rect x="95" y="32" width="260" height="14" fill="var(--panel)" stroke="var(--line)"/>
<text x="360" y="43" fill="var(--muted)" font-size="8">many</text>
<text x="90" y="72" fill="var(--ink)" font-size="8" text-anchor="end">code points — len()</text>
<rect x="95" y="62" width="180" height="14" fill="var(--s2)"/>
<text x="280" y="73" fill="var(--s2)" font-size="8">9</text>
<text x="90" y="102" fill="var(--ink)" font-size="8" text-anchor="end">grapheme clusters</text>
<rect x="95" y="92" width="100" height="14" fill="var(--s1)"/>
<text x="200" y="103" fill="var(--s1)" font-size="8">5 — what a reader sees</text>
</svg>
^ Bytes, code points, and grapheme clusters are three different counts of one string; len() gives the middle one, but "how many characters" means the last one.

The clusters themselves are formed by simple rules: a base code point starts a cluster, and certain following code points attach to it rather than starting new clusters — combining marks (an accent), a variation selector, an emoji skin-tone modifier, and code points joined by a zero-width joiner. The family emoji is one cluster because zero-width joiners bind the man, woman, and girl into a single grapheme; the accent on a letter is part of that letter's cluster because a combining mark attaches to what precedes it.

<svg role="img" aria-label="Five code points — man, zero-width joiner, woman, zero-width joiner, girl — bracketed together into a single grapheme cluster labeled one character. The joiners are shown binding the pieces." viewBox="0 0 440 120">
<rect x="20" y="40" width="55" height="20" fill="var(--panel)" stroke="var(--line)"/>
<text x="47" y="54" fill="var(--ink)" font-size="8" text-anchor="middle">man</text>
<rect x="79" y="40" width="40" height="20" fill="var(--muted)" opacity="0.3"/>
<text x="99" y="54" fill="var(--muted)" font-size="7" text-anchor="middle">ZWJ</text>
<rect x="123" y="40" width="55" height="20" fill="var(--panel)" stroke="var(--line)"/>
<text x="150" y="54" fill="var(--ink)" font-size="8" text-anchor="middle">woman</text>
<rect x="182" y="40" width="40" height="20" fill="var(--muted)" opacity="0.3"/>
<text x="202" y="54" fill="var(--muted)" font-size="7" text-anchor="middle">ZWJ</text>
<rect x="226" y="40" width="55" height="20" fill="var(--panel)" stroke="var(--line)"/>
<text x="253" y="54" fill="var(--ink)" font-size="8" text-anchor="middle">girl</text>
<path d="M20 68 L 281 68" fill="none" stroke="var(--s1)"/>
<text x="150" y="84" fill="var(--s1)" font-size="9" text-anchor="middle">one grapheme cluster = one character</text>
<text x="150" y="30" fill="var(--muted)" font-size="8" text-anchor="middle">5 code points</text>
</svg>
^ Zero-width joiners bind five code points into one grapheme; len() sees the five pieces, a reader sees one character.

The crucial point for portability is that normalization does not solve this. A companion module fixes string equality with Unicode NFC, which rewrites canonically-equivalent spellings to one form and does collapse some base-plus-accent pairs into a single precomposed code point. But NFC has no single code point to collapse a zero-width-joined emoji, a skin-tone-modified emoji, or a base letter that was never given a precomposed accented form — those stay multi-code-point after NFC. So even on fully normalized text, the grapheme count and safe truncation still require grapheme-cluster logic; normalization is a different fix for a different problem.

**Grapheme clusters are formed by attaching combining marks, joiners, and modifiers to a base; NFC normalization equalizes spellings and collapses some pairs but not zero-width-joined or unprecomposed graphemes, so counting and truncating still need grapheme awareness.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/grapheme-inter-01. The fixture gives the string as an explicit list of code points, so there is no ambiguity about the invisible joiners.

```json filename=modules/teaching-and-portability/code/grapheme-inter-01/grapheme.json:3 COMPLETE
  "codepoints": [72, 105, 32, 128104, 8205, 128105, 8205, 128103, 33],
```

The string is rebuilt from those code points: "Hi ", then the man (128104), a zero-width joiner (8205), the woman, a joiner, the girl, then "!".

```python filename=modules/teaching-and-portability/code/grapheme-inter-01/grapheme.py:34-35 COMPLETE
def text_of(data):
    return "".join(chr(c) for c in data["codepoints"])
```

Clustering walks the code points, attaching combining marks, variation selectors, skin-tone modifiers, and zero-width-joined code points to the current cluster instead of starting a new one.

```python filename=modules/teaching-and-portability/code/grapheme-inter-01/grapheme.py:38-59 COMPLETE
def clusters(s):
    """Group code points into grapheme clusters: a base plus following combining marks, zero-width-joined sequences, variation selectors, and skin-tone modifiers (a simplified UAX #29)."""
    out = []
    i, n = 0, len(s)
    while i < n:
        cluster = s[i]
        i += 1
        while i < n:
            ch = s[i]
            if unicodedata.combining(ch) or ch == VS16 or "\U0001F3FB" <= ch <= "\U0001F3FF":
                cluster += ch
                i += 1
            elif ch == ZWJ:
                cluster += ch
                i += 1
                if i < n:            # a zero-width joiner pulls the next code point in too
                    cluster += s[i]
                    i += 1
            else:
                break
        out.append(cluster)
    return out
```

The two truncations differ only in their unit: code points versus whole clusters.

```python filename=modules/teaching-and-portability/code/grapheme-inter-01/grapheme.py:62-69 COMPLETE
def naive_truncate(s, n):
    """Slice to n code points -- what s[:n] does, blind to graphemes."""
    return s[:n]


def grapheme_truncate(s, n):
    """Keep the first n grapheme clusters whole."""
    return "".join(clusters(s)[:n])
```

Before running it, predict: a reader sees five characters — H, i, space, the family, and the exclamation mark — but len() will count the family as its five code points and report nine. Run `--length`:

```text filename=grapheme.py --length
LENGTH — code points vs grapheme clusters
----------------------------------------------------
  string              : Hi 👨‍👩‍👧!
  len() code points   : 9
  grapheme clusters   : 5
  clusters            : ['H', 'i', ' ', '👨‍👩‍👧', '!']
----------------------------------------------------
  len() reports 9, but a reader sees 5 characters
```

The prediction holds. len() returns 9; the grapheme count is 5. The cluster list shows why: the family is a single cluster holding five code points — the three figures and the two joiners printed as `‍`. Any length check built on len() — a character limit, a progress indicator, a column width — is off by four here, and off by a different amount for every different string.

Now truncate to four characters. Run `--truncate`:

```text filename=grapheme.py --truncate
TRUNCATE — cut to 4 perceived characters
----------------------------------------------------
  by code points  s[:4]        : 'Hi 👨'  (4 clusters)
  by graphemes    first 4      : 'Hi 👨‍👩‍👧'  (4 clusters)
----------------------------------------------------
  the code-point slice splits the family emoji; the grapheme slice keeps it whole
```

Both results have four grapheme clusters, but they are not the same four. The code-point slice `s[:4]` keeps "Hi " and then the first code point of the family — a lone man — dropping the joiners and the rest, so the family emoji is silently amputated to one person. The grapheme slice keeps "Hi " and the whole family cluster intact. Cutting to "four characters" gave a mangled emoji one way and the right string the other; only the grapheme-aware cut is safe.

<svg role="img" aria-label="Two truncations to four characters. The code-point slice keeps H, i, space, and only the man from the family, with the rest of the family dropped and marked broken. The grapheme slice keeps H, i, space, and the whole family cluster intact." viewBox="0 0 440 140">
<text x="20" y="16" fill="var(--muted)" font-size="9">cut to 4 characters</text>
<text x="80" y="46" fill="var(--ink)" font-size="8" text-anchor="end">code points</text>
<rect x="88" y="36" width="22" height="16" fill="var(--panel)" stroke="var(--line)"/>
<text x="99" y="48" fill="var(--ink)" font-size="8" text-anchor="middle">H</text>
<rect x="112" y="36" width="22" height="16" fill="var(--panel)" stroke="var(--line)"/>
<text x="123" y="48" fill="var(--ink)" font-size="8" text-anchor="middle">i</text>
<rect x="136" y="36" width="22" height="16" fill="var(--panel)" stroke="var(--line)"/>
<rect x="160" y="36" width="45" height="16" fill="var(--s2)"/>
<text x="182" y="48" fill="var(--s2)" font-size="7" text-anchor="middle">man only</text>
<text x="215" y="48" fill="var(--muted)" font-size="7">family broken</text>
<text x="80" y="86" fill="var(--ink)" font-size="8" text-anchor="end">graphemes</text>
<rect x="88" y="76" width="22" height="16" fill="var(--panel)" stroke="var(--line)"/>
<text x="99" y="88" fill="var(--ink)" font-size="8" text-anchor="middle">H</text>
<rect x="112" y="76" width="22" height="16" fill="var(--panel)" stroke="var(--line)"/>
<text x="123" y="88" fill="var(--ink)" font-size="8" text-anchor="middle">i</text>
<rect x="136" y="76" width="22" height="16" fill="var(--panel)" stroke="var(--line)"/>
<rect x="160" y="76" width="90" height="16" fill="var(--s1)"/>
<text x="205" y="88" fill="var(--s1)" font-size="7" text-anchor="middle">whole family</text>
</svg>
^ Cutting to four characters: the code-point slice keeps only the man and drops the rest of the family; the grapheme slice keeps the family whole.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that len() exceeds the grapheme count, that one grapheme is several code points, that the code-point slice splits a grapheme, that grapheme truncation keeps the family whole, and that NFC normalization does not reduce the length.

```python filename=modules/teaching-and-portability/code/grapheme-inter-01/grapheme.py:105-121 COMPLETE
    codepoints_exceed_graphemes = len(s) > grapheme_len
    print("  len() (code points) exceeds the grapheme count = %s (%d > %d)" % (codepoints_exceed_graphemes, len(s), grapheme_len))

    one_grapheme_many_codepoints = max(len(c) for c in cl) > 1
    print("  one grapheme is several code points = %s (longest cluster is %d code points)" % (one_grapheme_many_codepoints, max(len(c) for c in cl)))

    naive = naive_truncate(s, 4)
    naive_truncate_breaks_grapheme = clusters(naive)[-1] != cl[3]
    print("  the code-point slice splits a grapheme = %s (its 4th char is %r, not the family)" % (naive_truncate_breaks_grapheme, clusters(naive)[-1]))

    gt = grapheme_truncate(s, 4)
    grapheme_truncate_preserves = clusters(gt)[-1] == cl[3] and gt == "".join(cl[:4])
    print("  grapheme truncation keeps the family whole = %s (%r)" % (grapheme_truncate_preserves, gt))

    nfc = unicodedata.normalize("NFC", s)
    nfc_does_not_reduce_length = len(nfc) > grapheme_len
    print("  NFC normalization does not fix the length = %s (NFC is still %d code points)" % (nfc_does_not_reduce_length, len(nfc)))
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the code-point slice ever stopped splitting the emoji or NFC ever collapsed it:

```text filename=grapheme.py --check
SELF-TEST — len() overcounts the visible length and a code-point slice splits the emoji; grapheme truncation keeps it, and NFC does not fix the length
----------------------------------------------------------------------------------------------------------------
  len() (code points) exceeds the grapheme count = True (9 > 5)
  one grapheme is several code points = True (longest cluster is 5 code points)
  the code-point slice splits a grapheme = True (its 4th char is '👨', not the family)
  grapheme truncation keeps the family whole = True ('Hi 👨‍👩‍👧')
  NFC normalization does not fix the length = True (NFC is still 9 code points)
```

**The self-test checks the NFC flag alongside the others precisely to fence this off from the normalization module — proving that even after normalization the string is still nine code points, so grapheme awareness, not NFC, is what counting and truncation require.**

## Definition of done

You can distinguish bytes, code points, and grapheme clusters, and say which one len() returns and which one a user means by "characters."
You can explain how combining marks and zero-width joiners build a single grapheme from several code points.
You can explain why slicing by code points can split a grapheme and give two concrete corruptions it causes.
You can explain why Unicode NFC normalization does not solve counting or truncation.
You can describe truncating by grapheme clusters and why it keeps each character whole.

## Boss fight

The clusterer here is a simplified version of the real algorithm. Reason about where it would be wrong. The Unicode standard's grapheme rules (UAX #29) cover cases this fixture does not: a country flag is two regional-indicator code points that pair into one grapheme, so a naive per-code-point walk splits every flag in half; some scripts (Korean Hangul, and Indic scripts like Devanagari and Tamil) form clusters from sequences of ordinary letters, not combining marks; and newer emoji use tag sequences and combinations this code does not handle. The lesson is not that the simplified version is useless — it is right for the common cases of combining accents and joined emoji — but that grapheme segmentation is a real specification, so production code should use a library that implements UAX #29 (Python's regex module, or ICU) rather than a hand-rolled walk, and should be tested against flags and Indic text, not only accents.

Now the trap that makes this a genuine data-loss bug, not just a display glitch. Truncating a UTF-8 or UTF-16 byte string by bytes rather than code points can cut in the middle of a multi-byte code point, producing invalid bytes that a strict decoder rejects — so the string does not just look wrong, it fails to load, and a naive fixed-width database column can silently corrupt the last character of every over-long value on insert. The defense is layered: store text in a field measured in characters or with generous byte headroom, truncate in the application by grapheme clusters with a library, and if you must enforce a byte budget, back off to the nearest grapheme boundary rather than cutting mid-character. The rule generalizes the module: any operation that slices text — for a UI, a column, a protocol field, a filename — must respect grapheme boundaries, because every layer below the grapheme is a place to cut a character in half.

**A hand-rolled clusterer misses flags, Hangul, and Indic clusters, so use a UAX #29 library and test beyond accents; and because slicing by bytes can produce invalid UTF-8 that fails to decode, enforce any budget by backing off to a grapheme boundary rather than cutting mid-character.**

## External resources

Unicode Standard Annex #29, "Text Segmentation," defines grapheme cluster boundaries — the specification a correct clusterer implements.
Python's third-party regex module and the ICU library provide grapheme-aware segmentation; Swift's String, which counts in grapheme clusters by default, is a good example of a language that makes the right unit the default.
The topic's own module on Unicode normalization (NFC) covers the neighboring problem — making canonically-equivalent strings compare equal — which this one is carefully distinguished from, since normalization fixes equality but not length or truncation.
