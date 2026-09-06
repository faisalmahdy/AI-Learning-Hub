---
id: newline-inter-01
title: Normalize line endings before you hash — or the same text written on two platforms has two different hashes
topic: teaching-and-portability
level: intermediate
status: ready
time: 16 min
summary: Text that looks identical can be different bytes, and the usual culprit is the invisible character at the end of each line. Unix ends a line with a single line-feed (LF, \n); Windows ends it with a carriage-return plus a line-feed (CRLF, \r\n). An editor shows the same lines on either platform, but the Windows file is one byte longer per line, so anything reading raw bytes — a length check, a checksum, a hash, a signature, a byte diff — sees two different files. You document a data file's hash to prove integrity, a colleague on another platform recomputes it, and the value differs because their editor or git checkout used the other line ending. On the same three lines, LF is 22 bytes and hashes to e0af2be21679 while CRLF is 25 bytes and hashes to 45fc3c65c440; normalizing CRLF to LF makes both 22 bytes with the same hash.
eli5: Two people copy out the same short poem by hand. It reads exactly the same, but one of them puts a tiny invisible dot at the end of every line. If you weigh the two pages, they weigh differently because of the dots — even though the words are identical. Computers "weigh" files by hashing their bytes, and Windows adds an invisible extra character at each line end, so the two files hash differently. Wipe out the extra character first and they match.
---

## Why this module

A hash is supposed to certify content, but it certifies bytes, and the bytes of "the same text" quietly differ across platforms because the character that ends a line is not the same everywhere.

Every line in a text file ends with an invisible marker. On Unix and macOS that marker is a single byte, the line feed, written `\n`. On Windows it is two bytes, a carriage return followed by a line feed, written `\r\n`. Open either file in an editor and you see identical lines — the `\r` renders as nothing — so to a human the two files are the same. But they are not the same bytes: the Windows file carries one extra `\r` per line. Anything that operates on bytes rather than rendered text therefore treats them as different files: a byte-length comparison, a checksum, a cryptographic hash, a digital signature, a byte-for-byte diff. The failure is maximally confusing because the thing you can see (the text) is identical while the thing the tool checks (the bytes) is not, and nothing in the editor reveals the discrepancy.

**Text that looks identical can be different bytes because Unix ends a line with one byte (LF) and Windows with two (CRLF), so any byte-sensitive check — length, hash, signature, diff — differs across platforms.**

This turns a documented hash into a reproducibility trap. You compute the SHA-256 of your data file, publish it so others can verify the file was not tampered with, and a collaborator on a different operating system — or with a different git line-ending setting — recomputes it and gets a different digest. The data is unchanged; the line endings are not. The fix is to normalize line endings before doing anything byte-sensitive: convert CRLF to LF (consistently, one way), so the hash is a hash of the content and not of the content-plus-platform-convention. This module hashes the same lines with both endings and shows the digests diverge, then converge after normalizing.

## Concepts

**A line ending** is the byte or bytes that terminate a line. LF (`\n`, one byte) on Unix and macOS; CRLF (`\r\n`, two bytes) on Windows.

**The text is identical, the bytes are not.** Editors render both the same way, so the difference is invisible in every view except a byte-level one.

```python filename=modules/teaching-and-portability/code/newline-inter-01/newline.py:42-44 COMPLETE
def encode(lines, ending):
    """Join the lines with the given line ending and encode to bytes."""
    return (ending.join(lines) + ending).encode("utf-8")
```

**Byte-sensitive operations diverge.** A hash, a signature, a checksum, and a byte diff all see the extra `\r` bytes, so they report the two files as different.

**Normalizing** replaces every CRLF with a single LF (or the reverse, consistently), so the bytes match whatever platform produced the file.

```python filename=modules/teaching-and-portability/code/newline-inter-01/newline.py:47-54 COMPLETE
def normalize(data_bytes):
    """Normalize line endings to LF by replacing every CRLF with a single LF."""
    return data_bytes.replace(b"\r\n", b"\n")


def digest(data_bytes):
    """A short SHA-256 hex digest of the bytes."""
    return hashlib.sha256(data_bytes).hexdigest()[:12]
```

**A reproducible hash is a hash of normalized content, not raw platform bytes — like seeding an RNG or pinning a version, fixing the line ending removes a hidden dependency that would otherwise fork the result across machines.**

<svg role="img" aria-label="A line rendered in an editor looks the same, but the byte view shows CRLF has an extra carriage-return byte the human never sees" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">what you see vs what the bytes are</text>
  <text x="8" y="34" fill="var(--muted)" font-size="8">editor</text>
  <rect x="55" y="24" width="120" height="16" fill="var(--panel)" stroke="var(--grid)"/><text x="60" y="36" fill="var(--ink)" font-size="8" font-family="monospace">1,alice</text>
  <text x="180" y="36" fill="var(--muted)" font-size="7">looks identical either way</text>
  <text x="8" y="66" fill="var(--muted)" font-size="8">bytes</text>
  <text x="55" y="66" fill="var(--s1)" font-size="8" font-family="monospace">1,alice\n</text><text x="120" y="66" fill="var(--muted)" font-size="7">(LF, 8 bytes)</text>
  <text x="55" y="82" fill="var(--s2)" font-size="8" font-family="monospace">1,alice\r\n</text><text x="128" y="82" fill="var(--muted)" font-size="7">(CRLF, 9 bytes)</text>
  <text x="8" y="96" fill="var(--muted)" font-size="8">the \r is invisible in the editor but real in the bytes the hash reads</text>
</svg>
^ The rendered line is the same in an editor, but the byte view exposes the extra `\r` in the CRLF version — the difference the hash sees and the human does not.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/newline-inter-01/newline.py

The fixture is three logical lines of a small CSV.

```json filename=modules/teaching-and-portability/code/newline-inter-01/newline.json:1-4 COMPLETE
{
  "_meta": "The logical lines of a small text file (a CSV here). The same lines can be written two ways: with Unix line endings (LF, a single \\n after each line) or Windows line endings (CRLF, a carriage-return + line-feed \\r\\n). The visible text is identical, but the BYTES are not -- CRLF adds one extra \\r byte per line -- so a byte-length check, a hash, a diff, or a signature over the file differs between a file written on Windows and one written on Unix, even though a human sees the same content. A documented hash therefore fails to reproduce across platforms unless line endings are normalized first. This fixture builds both byte strings from the same lines and shows the divergence and the fix (normalize CRLF to LF before hashing).",
  "lines": ["id,name", "1,alice", "2,bob"]
}
```

Run `--bytes` to write the same lines both ways and hash each.

```text filename=--bytes
BYTES — same 3 lines, two line endings
----------------------------------------------------------
  LF   (Unix):     22 bytes   hash e0af2be21679
  CRLF (Windows):  25 bytes   hash 45fc3c65c440
----------------------------------------------------------
  identical text, 3 extra bytes (one \r per line), a different hash.
```

The three lines — `id,name`, `1,alice`, `2,bob` — are the same content either way. Written with LF they are 22 bytes and hash to `e0af2be21679`. Written with CRLF they are 25 bytes — three extra `\r`, one per line — and hash to a completely different `45fc3c65c440`. A hash is designed to change drastically on any byte difference, so the invisible `\r` bytes produce a digest with no resemblance to the LF one. If you published `e0af2be21679` as the file's checksum and a Windows colleague computed `45fc3c65c440`, it would look exactly like a corrupted or tampered file, when nothing about the data changed at all.

<svg role="img" aria-label="The same three lines are 22 bytes and one hash with LF, 25 bytes and a different hash with CRLF" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">same text: id,name / 1,alice / 2,bob</text>
  <text x="8" y="36" fill="var(--s1)" font-size="8">LF</text>
  <rect x="40" y="26" width="88" height="16" fill="var(--s1)"/><text x="46" y="38" fill="var(--panel)" font-size="8">22 bytes</text>
  <text x="135" y="38" fill="var(--muted)" font-size="8" font-family="monospace">e0af2be21679</text>
  <text x="8" y="66" fill="var(--s2)" font-size="8">CRLF</text>
  <rect x="40" y="56" width="100" height="16" fill="var(--s2)"/><text x="46" y="68" fill="var(--panel)" font-size="8">25 bytes</text>
  <text x="147" y="68" fill="var(--muted)" font-size="8" font-family="monospace">45fc3c65c440</text>
  <rect x="128" y="56" width="12" height="16" fill="var(--ink)"/><text x="118" y="90" fill="var(--muted)" font-size="7">the extra \r bytes (3)</text>
  <text x="8" y="104" fill="var(--muted)" font-size="8">identical content, three invisible extra bytes, a totally different hash</text>
</svg>
^ The CRLF bar is three bytes longer — the invisible carriage returns — and its hash bears no resemblance to the LF one, though the visible text is the same.

## Build

The fix is one normalization step. Run `--normalize`.

```text filename=--normalize
NORMALIZE — both files converted to LF before hashing
----------------------------------------------------------
  normalized LF:    22 bytes   hash e0af2be21679
  normalized CRLF:  22 bytes   hash e0af2be21679
  equal after normalizing: True
----------------------------------------------------------
  normalize to one line ending and the hash is of the content, not the platform.
```

Replacing every CRLF with a single LF turns the 25-byte Windows file back into the 22-byte canonical form, and now both hash to the identical `e0af2be21679`. The hash has become a hash of the *content* — the sequence of characters that make up the lines — rather than a hash of the content plus whichever platform's line-ending convention happened to write the file. That is the property a documented, reproducible checksum needs: it must not depend on anything invisible and platform-specific. This is exactly what git's `text` attribute and `core.autocrlf` normalize on commit, what "open in text mode with `newline=`" does in Python, and what a build that hashes source files should do before hashing — pick one line ending and impose it.

<svg role="img" aria-label="After normalizing to LF, both files are 22 bytes and share the hash e0af2be21679" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">after normalizing CRLF → LF</text>
  <text x="8" y="36" fill="var(--muted)" font-size="8">was LF</text>
  <rect x="60" y="26" width="88" height="16" fill="var(--s1)"/><text x="155" y="38" fill="var(--muted)" font-size="8" font-family="monospace">e0af2be21679</text>
  <text x="8" y="62" fill="var(--muted)" font-size="8">was CRLF</text>
  <rect x="60" y="52" width="88" height="16" fill="var(--s1)"/><text x="155" y="64" fill="var(--muted)" font-size="8" font-family="monospace">e0af2be21679</text>
  <text x="60" y="90" fill="var(--muted)" font-size="8">both 22 bytes, one shared hash — the platform convention is gone</text>
</svg>
^ Normalizing collapses the two files to the same 22 bytes and the same digest, so the hash now certifies the content and reproduces on any platform.

## Definition of done

The self-test pins it: the raw bytes and hashes differ, CRLF is longer by one byte per line, and normalizing to LF makes both the bytes and the hashes equal.

```python filename=modules/teaching-and-portability/code/newline-inter-01/newline.py:89-102 COMPLETE
    bytes_differ = lf != crlf
    print("  the raw bytes differ between LF and CRLF = %s (%d vs %d bytes)" % (bytes_differ, len(lf), len(crlf)))

    crlf_longer_by_line_count = len(crlf) - len(lf) == len(lines)
    print("  CRLF is longer by exactly one byte per line = %s (+%d for %d lines)" % (crlf_longer_by_line_count, len(crlf) - len(lf), len(lines)))

    hashes_differ = digest(lf) != digest(crlf)
    print("  the hashes differ for identical text = %s (%s vs %s)" % (hashes_differ, digest(lf), digest(crlf)))

    normalized_equal = normalize(lf) == normalize(crlf)
    print("  normalizing to LF makes the bytes equal = %s" % normalized_equal)

    normalized_hashes_equal = digest(normalize(lf)) == digest(normalize(crlf))
    print("  the normalized hashes match = %s (%s)" % (normalized_hashes_equal, digest(normalize(crlf))))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the raw bytes and hashes differ; normalizing to LF makes them identical
----------------------------------------------------------------------------------------------------
  the raw bytes differ between LF and CRLF = True (22 vs 25 bytes)
  CRLF is longer by exactly one byte per line = True (+3 for 3 lines)
  the hashes differ for identical text = True (e0af2be21679 vs 45fc3c65c440)
  normalizing to LF makes the bytes equal = True
  the normalized hashes match = True (e0af2be21679)
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  bytes_differ=True  crlf_longer_by_line_count=True  hashes_differ=True  normalized_equal=True  normalized_hashes_equal=True
```

**Done means the divergence and the fix are both proven: identical text is 22 bytes/e0af2be21679 with LF and 25 bytes/45fc3c65c440 with CRLF — a different hash purely from three invisible bytes — and normalizing to LF returns both to 22 bytes and the shared e0af2be21679.**

## Boss fight

Normalizing CRLF to LF fixed the hash. Predict when normalizing is the wrong thing to do, and what other invisible bytes cause the same class of bug. It is tempting to normalize line endings everywhere, always.

Normalizing is right for text you compare or hash for content, but wrong for bytes that must survive intact. Some files are text with meaningful line endings you must not rewrite — a file whose format specifies CRLF (many network protocols, some Windows-native formats), or a binary file that happens to contain `\r\n` byte sequences you would corrupt by "normalizing." This is exactly the bug git's autocrlf can cause: set to convert line endings on a file it wrongly classifies as text, it mangles a binary asset. So the rule is not "always convert," it is "know whether a file is text-with-normalizable-endings or bytes-to-preserve, and treat each accordingly" — mark binaries as binary (`.gitattributes` with `-text`), and only normalize the files whose line endings are a convention rather than content.

The deeper point is that line endings are one of a family of invisible bytes that fork "identical-looking" text. A trailing space, a tab-versus-spaces difference, a byte-order mark (BOM) some editors prepend to UTF-8 files, a non-breaking space pasted from a web page, a Unicode character with two different normalization forms (é as one code point versus e-plus-combining-accent) — each renders the same or nearly the same while changing the bytes and thus the hash. The discipline is the same as for line endings and for the whole reproducibility family: before you hash, compare, or diff text, canonicalize everything invisible that the tool is sensitive to but a human is not — line endings, encoding and BOM, and Unicode normalization form — so the digest certifies the content you can see, not the accidents of how it was typed and saved.

```python filename=modules/teaching-and-portability/code/newline-inter-01/newline.py:60-64 COMPLETE
    lines = data["lines"]
    lf, crlf = encode(lines, "\n"), encode(lines, "\r\n")
    print("BYTES — same %d lines, two line endings" % len(lines))
    print("-" * 58)
    print("  LF   (Unix):     %d bytes   hash %s" % (len(lf), digest(lf)))
```

**The same text on Unix and Windows differs by an invisible byte per line (LF vs CRLF), so its hash, signature, and byte diff differ across platforms — normalize line endings before any byte-sensitive operation so the digest certifies content, but only for files whose endings are convention (not binaries), and canonicalize the rest of the invisible family too: encoding/BOM and Unicode normalization form.**

## External resources

The Git documentation on `core.autocrlf` and the `.gitattributes` `text`/`eol` attributes — how git normalizes line endings on commit and checkout, and how to exclude binary files from that normalization.

The Python documentation on universal newlines and opening files with an explicit `newline=` argument — the language-level control over how line endings are read and written, and why text mode translates them.

The companion "specify encoding='utf-8' when you read and write" and "seed the random generator" modules — encoding and line endings are two invisible byte-level dependencies that break reproducibility the same way, and both are part of controlling everything a documented output silently depends on.
