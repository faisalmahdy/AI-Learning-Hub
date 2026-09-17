---
id: bom-inter-01
title: Strip the UTF-8 BOM when reading — an invisible byte corrupts the first field and a lookup by its name silently fails
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: Some programs — Excel exporting a CSV, Notepad, many Windows editors — write a UTF-8 file with a byte-order mark at the very front: the three bytes EF BB BF, which decode to U+FEFF. For UTF-8 the BOM is pointless (UTF-8 has no byte order) but editors add it as a Unicode signature. It becomes a bug the moment another program reads the file with a plain "utf-8" decoder, because that decoder faithfully includes the BOM in the string. The BOM lands on the very first character, so the first field — a CSV's first column header, a JSON's leading whitespace, the first config line — comes back with an invisible U+FEFF glued to its front. This is pernicious because the BOM is invisible when printed: a header that is actually "﻿name" displays as "name", looks like "name" in a debugger, and compares unequal to "name". So a program that reads the columns and looks up the row by data["name"] gets a KeyError for a column that is right there on screen, and because the BOM only ever hits the first field, most of the data is fine and only the first column is mysteriously unreachable — which looks like a logic bug, not an encoding one. The fix is to decode with "utf-8-sig" instead of "utf-8" when reading files that might carry a BOM: the -sig codec strips a leading BOM (and reads BOM-less files identically). On a fixture where a CSV "name,age,city / Alice,30,NYC" is saved with a BOM, plain utf-8 makes the first header "﻿name" so a lookup for "name" fails, while utf-8-sig strips the BOM, the first header is "name", and the lookup returns "Alice".
eli5: Imagine someone hands you a form where, in invisible ink, they've written a tiny mark right before the word "Name" in the first blank. You can't see the mark, so the label looks exactly like "Name" — but when your filing machine searches for the blank labeled precisely "Name," it can't find it, because the real label is "✦Name" with that hidden mark. Every other blank on the form is fine; only the first one has the invisible mark, so only the first one goes missing, and you're left staring at a form whose first field is clearly "Name" wondering why the machine says it isn't there. The fix is to use a reader that knows about the invisible-ink trick and wipes that mark off the front before filing.
---

## Why this module

An encoding bug that you can see is annoying; one you cannot see is maddening, and the UTF-8 BOM is the second kind. It is a real character sitting at the start of the file, but it renders as nothing — no glyph, no width — so every tool that shows you the string shows you a string that looks correct. The mismatch only appears when the computer compares the string to what you typed, and by then you are looking at a column plainly labeled "name", a lookup for "name" that returns nothing, and no visible difference between the two. The bug is one byte you were never shown, on exactly one field.

Editors like Excel and Notepad write a UTF-8 file with a byte-order mark at the front — bytes EF BB BF, decoding to U+FEFF — as a Unicode signature. Read that file with a plain "utf-8" decoder and the BOM survives into the string, glued to the very first character, so the first field comes back with an invisible U+FEFF on its front. Because the BOM is invisible when printed, a header that is actually "﻿name" displays as "name" and compares unequal to "name", so a lookup by the clean key fails for a column that is right there on screen.

And it only ever affects the first field, so most of the data is fine and only the first column is mysteriously unreachable — which makes it look like a logic bug rather than an encoding one. The fix is to decode with "utf-8-sig", which strips a leading BOM and reads BOM-less files identically. This module reads the same bytes both ways.

**Read text that may have been saved by a BOM-adding editor (Excel, Windows tools) with "utf-8-sig", not plain "utf-8", because a UTF-8 BOM decodes to an invisible U+FEFF glued to the first field, so a lookup by that field's clean name silently fails even though the field looks correct — and write with plain "utf-8" so you do not add a BOM yourself.**

## Concepts

**The saved file carries the BOM, and the decoder decides whether it survives:** plain utf-8 keeps it on the first field, utf-8-sig strips it.

```python filename=modules/teaching-and-portability/code/bom-inter-01/bom.py:51-66 COMPLETE
def saved_file_bytes(data):
    """The bytes a BOM-adding editor would write for this CSV: content encoded with utf-8-sig (which prepends the BOM)."""
    content = ",".join(data["columns"]) + "\n" + ",".join(data["row"])
    return content.encode("utf-8-sig")


def headers_plain(raw):
    """Decode with plain utf-8 (the BOM survives) and split the first line into headers."""
    text = raw.decode("utf-8")
    return text.splitlines()[0].split(",")


def headers_sig(raw):
    """Decode with utf-8-sig (the BOM is stripped) and split the first line into headers."""
    text = raw.decode("utf-8-sig")
    return text.splitlines()[0].split(",")
```

**We build a header→value row and look up by column name** — the operation the BOM silently breaks.

```python filename=modules/teaching-and-portability/code/bom-inter-01/bom.py:69-70 COMPLETE
def row_dict(headers, row):
    return dict(zip(headers, row))
```

<svg role="img" aria-label="The file's leading bytes EF BB BF form the BOM, then the bytes for 'name'; a plain utf-8 decode keeps a U+FEFF character before 'name', while utf-8-sig discards the BOM bytes and yields just 'name'" viewBox="0 0 300 110" width="300" height="110">
  <text x="6" y="12" fill="var(--muted)" font-size="8">EF BB BF is the BOM; the decoder decides if it survives</text>
  <g font-size="7">
    <rect x="14" y="22" width="28" height="16" fill="var(--s2)"/><text x="18" y="34" fill="var(--panel)">EF</text>
    <rect x="44" y="22" width="28" height="16" fill="var(--s2)"/><text x="48" y="34" fill="var(--panel)">BB</text>
    <rect x="74" y="22" width="28" height="16" fill="var(--s2)"/><text x="78" y="34" fill="var(--panel)">BF</text>
    <rect x="104" y="22" width="28" height="16" fill="none" stroke="var(--line)"/><text x="108" y="34" fill="var(--ink)">6E</text>
    <rect x="134" y="22" width="28" height="16" fill="none" stroke="var(--line)"/><text x="138" y="34" fill="var(--ink)">61</text>
    <rect x="164" y="22" width="28" height="16" fill="none" stroke="var(--line)"/><text x="168" y="34" fill="var(--ink)">6D</text>
    <rect x="194" y="22" width="28" height="16" fill="none" stroke="var(--line)"/><text x="198" y="34" fill="var(--ink)">65</text>
  </g>
  <text x="14" y="48" fill="var(--s2)" font-size="6">↑ BOM</text><text x="104" y="48" fill="var(--muted)" font-size="6">↑ 'n a m e'</text>
  <text x="14" y="72" fill="var(--s2)" font-size="7">plain utf-8 → '﻿name'  (BOM kept, invisible)</text>
  <text x="14" y="92" fill="var(--s1)" font-size="7">utf-8-sig → 'name'  (BOM stripped)</text>
</svg>
^ The file's first three bytes (EF BB BF) are the BOM, followed by the bytes for "name"; a plain utf-8 decode keeps the BOM as an invisible U+FEFF in front of "name", while utf-8-sig discards those three bytes and yields the clean "name".

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/bom-inter-01/bom.py

The fixture is the CSV's logical content and the column a program will look up by name.

```json filename=modules/teaching-and-portability/code/bom-inter-01/bom.json:3-5 COMPLETE
  "columns": ["name", "age", "city"],
  "row": ["Alice", "30", "NYC"],
  "lookup_key": "name"
```

Run `--bytes`.

```text filename=--bytes
BYTES — the saved file starts with the UTF-8 BOM (EF BB BF)
------------------------------------------------------------
  first 6 bytes: EF BB BF 6E 61 6D
  plain utf-8   first header = '﻿name'
  utf-8-sig     first header = 'name'
```

<svg role="img" aria-label="Two strings shown as they display versus as they compare: both display as 'name', but one has a hidden leading mark, so an equality test between them is false" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">both display as 'name' — but they are not equal</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">plain utf-8</text>
  <rect x="90" y="24" width="70" height="16" fill="none" stroke="var(--s2)"/><text x="112" y="35" fill="var(--ink)" font-size="8">name</text>
  <text x="168" y="35" fill="var(--s2)" font-size="6">(hidden ✦ in front)</text>
  <text x="10" y="60" fill="var(--muted)" font-size="7">utf-8-sig</text>
  <rect x="90" y="50" width="70" height="16" fill="none" stroke="var(--s1)"/><text x="112" y="61" fill="var(--ink)" font-size="8">name</text>
  <text x="168" y="61" fill="var(--s1)" font-size="6">(clean)</text>
  <text x="90" y="84" fill="var(--s2)" font-size="8">'name' == 'name'  →  False</text>
  <text x="10" y="96" fill="var(--muted)" font-size="6">the display agrees, the bytes disagree — the whole trap in one line</text>
</svg>
^ Both decodings print as "name", but the plain-utf8 one carries a hidden leading mark, so an equality test between the two returns False — the display agrees while the bytes disagree, which is exactly why the bug is invisible until you compare or inspect the raw bytes.

Read the bytes and the two decodings. The file begins with EF BB BF — the UTF-8 BOM — followed by 6E 61 6D ("nam..."), so the actual header text starts three bytes in. When the file is decoded with plain utf-8, the BOM becomes U+FEFF and stays attached, so the first header is the four-code-point string `'﻿name'`. When decoded with utf-8-sig, the codec recognizes and removes the leading BOM, so the first header is the clean `'name'`. The crucial thing is what the terminal shows: Python's `repr` here reveals the `﻿` because we asked for repr, but in a normal print, a log line, or a CSV viewer, `'﻿name'` and `'name'` are visually identical — the BOM has zero width. So without repr you would see two lines both reading "name" and have no way to tell that one of them carries an extra, invisible character that will make it unequal to every "name" you compare it against.

## Build

The consequence surfaces the moment you use that header as a key.

```text filename=--lookup
LOOKUP — parse the CSV and look up the row by 'name'
--------------------------------------------------------------
  plain utf-8  headers = ['﻿name', 'age', 'city']
    row['name'] = '<KeyError: not found>'
  utf-8-sig    headers = ['name', 'age', 'city']
    row['name'] = 'Alice'
```

Look at the two header lists. Under plain utf-8, the headers are `['﻿name', 'age', 'city']` — the first is corrupted, the other two are clean, because the BOM only touches the very first character of the file. So `row['name']` fails: there is no key `'name'` in the dictionary, only `'﻿name'`, and they are different strings. Under utf-8-sig, the headers are `['name', 'age', 'city']` and `row['name']` returns `'Alice'`. This is the exact shape of the real-world bug: a CSV exported from Excel is loaded, every column reads correctly in a preview, and then `df['name']` (or `row['name']`, or `record['name']`) raises a KeyError for the first column only, while `df['age']` works fine. Developers lose hours because the failing column is visibly present and visibly named "name" — the difference is a byte they were never shown, and only inspecting the raw bytes or the string's `repr` (or noticing that only the *first* column fails) reveals it. The one-line fix, decoding with utf-8-sig, makes the whole class of bug disappear.

```python filename=modules/teaching-and-portability/code/bom-inter-01/bom.py:111-118 COMPLETE
    bom_present = raw[:3] == b"\xef\xbb\xbf"
    print("  the saved file begins with the UTF-8 BOM = %s (%s)" % (bom_present, " ".join("%02X" % b for b in raw[:3])))

    plain_corrupts_first = hp[0] == BOM + key and hp[0] != key
    print("  plain utf-8 glues the BOM to the first header = %s (%r != %r)" % (plain_corrupts_first, hp[0], key))

    plain_lookup_fails = key not in plain
    print("  the lookup by the clean key fails under plain utf-8 = %s" % plain_lookup_fails)
```

## Definition of done

The self-test pins the BOM bytes, the corrupted first header, the failed lookup, the working utf-8-sig lookup, and that only the first field is affected.

```python filename=modules/teaching-and-portability/code/bom-inter-01/bom.py:120-124 COMPLETE
    sig_lookup_works = sig.get(key) == data["row"][0]
    print("  utf-8-sig strips the BOM and the lookup returns the value = %s (%r)" % (sig_lookup_works, sig.get(key)))

    only_first_affected = hp[1:] == hs[1:]
    print("  only the first field is affected; the rest are identical = %s (%s == %s)" % (only_first_affected, hp[1:], hs[1:]))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the BOM corrupts only the first field under plain utf-8 and the lookup fails; utf-8-sig strips it and it works
----------------------------------------------------------------------------------------------------------------------------
  the saved file begins with the UTF-8 BOM = True (EF BB BF)
  plain utf-8 glues the BOM to the first header = True ('﻿name' != 'name')
  the lookup by the clean key fails under plain utf-8 = True
  utf-8-sig strips the BOM and the lookup returns the value = True ('Alice')
  only the first field is affected; the rest are identical = True (['age', 'city'] == ['age', 'city'])
```

<svg role="img" aria-label="Header lists compared: plain utf-8 has a corrupted first entry and clean rest, utf-8-sig has all clean; only the first field differs" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">only the first field differs; the rest are identical</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">plain utf-8</text>
  <rect x="80" y="24" width="70" height="14" fill="var(--s2)"/><text x="84" y="34" fill="var(--panel)" font-size="6">✦name (broken)</text>
  <rect x="152" y="24" width="40" height="14" fill="none" stroke="var(--s1)"/><text x="158" y="34" fill="var(--muted)" font-size="6">age</text>
  <rect x="194" y="24" width="40" height="14" fill="none" stroke="var(--s1)"/><text x="200" y="34" fill="var(--muted)" font-size="6">city</text>
  <text x="10" y="60" fill="var(--muted)" font-size="7">utf-8-sig</text>
  <rect x="80" y="50" width="70" height="14" fill="var(--s1)"/><text x="98" y="60" fill="var(--panel)" font-size="6">name</text>
  <rect x="152" y="50" width="40" height="14" fill="none" stroke="var(--s1)"/><text x="158" y="60" fill="var(--muted)" font-size="6">age</text>
  <rect x="194" y="50" width="40" height="14" fill="none" stroke="var(--s1)"/><text x="200" y="60" fill="var(--muted)" font-size="6">city</text>
  <text x="10" y="84" fill="var(--muted)" font-size="6">'age' and 'city' match exactly — only the first column is unreachable</text>
</svg>
^ The two header lists differ only in the first entry — plain utf-8 carries the BOM-corrupted "✦name" while utf-8-sig has a clean "name", and "age" and "city" are byte-identical either way — which is why the bug masquerades as a logic error affecting exactly one column.

**Done means the invisible corruption is proven on real bytes: a CSV saved with a BOM (EF BB BF) decodes under plain utf-8 to a first header "﻿name" that fails a lookup for "name" while "age" and "city" are unaffected, and decodes under utf-8-sig to a clean "name" that returns "Alice" — so files that may carry a BOM must be read with utf-8-sig, and written with plain utf-8.**

## Boss fight

Predict two ways the BOM problem is broader and trickier than "read with utf-8-sig," because the mark shows up in more places and the fix has a matching write-side rule.

The first trap is that the BOM is not only a CSV-header problem — it corrupts the *start* of any file, so it breaks parsers that are strict about the first byte, and stripping it on read is necessary but you must also not re-add it on write. A BOM at the start of a JSON file makes many strict JSON parsers fail outright (the spec does not permit a leading U+FEFF, so `json.loads` on a BOM-prefixed string raises), a BOM before `<?xml` or a shebang `#!` line breaks XML parsers and shell scripts, and a BOM in a source file can produce baffling syntax errors on line 1. So "decode with utf-8-sig" generalizes to "tolerate a possible leading BOM wherever you accept text from unknown tools," and the mirror rule is the write side: when your program *writes* a file, use plain `utf-8`, never `utf-8-sig`, because adding a BOM inflicts this exact trap on whoever reads your output next — and a round-trip that reads with utf-8-sig but writes with utf-8-sig quietly keeps the BOM alive forever. The discipline is asymmetric on purpose: be liberal in what you accept (strip a BOM if present), strict in what you emit (never add one).

The second trap is that U+FEFF is a real, meaningful character in the middle of text, so you cannot just blindly delete every U+FEFF you find — only the leading one is a BOM. U+FEFF has a second identity as the ZERO WIDTH NO-BREAK SPACE, and while its use as a mid-string joiner is deprecated, it (and its invisible cousins — zero-width space U+200B, zero-width joiner U+200D, the various directional marks) can legitimately or maliciously appear inside strings, so a global `text.replace('﻿', '')` is too aggressive and a naive `strip()` may miss it because it is not whitespace by default. The correct handling is position-specific: strip a BOM only at the very start (which utf-8-sig does exactly, on decode), and treat any interior zero-width character as data to be handled by explicit normalization if your application needs it. This connects to the broader lesson that invisible and look-alike characters are a portability and even security hazard — homoglyph attacks, zero-width characters smuggled into identifiers or secrets, Unicode normalization mismatches — all of which share the property that the bytes disagree while the display agrees. The BOM is the most common member of that family, and the habit it should instill is: when a string comparison fails but the two strings look identical, inspect the bytes.

**The BOM corrupts the start of any file, not just CSV headers — it breaks strict JSON/XML parsers and shebangs — so tolerate a leading BOM wherever you accept text (utf-8-sig on read), and enforce the mirror rule on write: emit plain utf-8 and never add a BOM, or you inflict the trap on the next reader and a utf-8-sig round-trip keeps it alive forever. And strip the BOM only at the start: U+FEFF is a real zero-width character mid-string, one of a family of invisible and look-alike characters (zero-width spaces, homoglyphs) that make bytes disagree while displays agree — so when a comparison fails on strings that look identical, inspect the bytes.**

## External resources

The Unicode standard's notes on U+FEFF and the byte-order mark, and Python's codecs documentation for "utf-8" vs "utf-8-sig" — why UTF-8 needs no BOM, why editors add one, and exactly what the -sig codec strips on read and adds on write.

Discussions of BOM issues in CSV and JSON handling (Excel CSV exports, `json.loads` failing on a BOM, spreadsheet-to-program pipelines) — the concrete first-column KeyError and parser-failure symptoms and their fixes.

The companion encoding, line-ending, and Unicode-normalization modules in this topic — the BOM is one more case where a byte you cannot see changes how text compares across tools, and the fix pattern (be explicit and liberal on read, strict on write) is the same one those modules apply to encoding, newlines, and normalization.
