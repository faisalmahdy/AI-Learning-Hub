"""Normalize Unicode (NFC) before you compare or hash -- or the same visible text in two encodings is silently unequal.

The character e-with-an-acute-accent can be written two ways in Unicode. Precomposed, it is a single code point,
U+00E9. Decomposed, it is two code points: a plain e (U+0065) followed by a combining acute accent (U+0301) that stacks
onto it. Both render as the identical glyph -- no human, and no font, shows any difference -- but to the computer they
are different strings: different lengths, different bytes, different hashes. So 'cafe' with a precomposed accent and
'cafe' with a decomposed accent are NOT equal, even though they are visibly the same word. Type the same text on two
keyboards, paste from two apps, or move a filename between operating systems (macOS stores names decomposed, most Linux
stores them precomposed) and a comparison that should match silently fails: a lookup misses, a dedup keeps both copies,
a cache never hits, a signature over the 'same' text verifies as different.

The fix is one call before any comparison, hash, or key: Unicode normalization, which rewrites a string into a canonical
form so that any two strings that are canonically equivalent become byte-for-byte identical. NFC (Normalization Form C)
composes characters back to their precomposed form; run both strings through it and 'cafe'-with-accent equals
'cafe'-with-accent, hashes the same, and has the same length, regardless of how each was originally encoded. The rule is
the same shape as every other portability rule: text you will compare, hash, deduplicate, or use as a key must first be
put in one canonical form, because 'looks the same' is not 'is the same' in Unicode.

On this fixture the precomposed string is 4 code points and the decomposed one is 5, and they are unequal with different
sha256 hashes, though both display as the same accented 'cafe'. After NFC both are 4 code points, equal, with one shared
hash. A dictionary keyed on the precomposed form misses a decomposed lookup until both are normalized. This computes it.

  --compare    the two forms: their code points, lengths, equality, and hashes -- different, though they look identical
  --normalize  after NFC: same code points, equal, same hash, same length; and a key lookup that only works normalized
  --check      the raw forms are unequal with different hash and length; NFC makes them equal, same hash, same length

The two strings are the fixture (as code points); every length and hash is computed. Stdlib only.
"""
import argparse
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "normalize.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def build(data):
    """Reconstruct the two strings from their code points, so the file is unambiguous about which is which."""
    pre = "".join(chr(c) for c in data["precomposed_codepoints"])
    dec = "".join(chr(c) for c in data["decomposed_codepoints"])
    return pre, dec


def digest(s):
    """A sha256 hex digest of the string's UTF-8 bytes -- what a cache key or content hash would use."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


def codepoints(s):
    """The string's code points as U+XXXX names -- what the computer actually stores."""
    return ["U+%04X" % ord(ch) for ch in s]


def nfc(s):
    """Normalization Form C: rewrite the string into its canonical composed form."""
    return unicodedata.normalize("NFC", s)


# ----------------------------------------------------------------- printing

def compare_view(data):
    pre, dec = build(data)
    print("COMPARE — two encodings of the same visible text")
    print("-" * 66)
    print("  precomposed:  %s  len %d  hash %s" % (codepoints(pre), len(pre), digest(pre)))
    print("  decomposed:   %s  len %d  hash %s" % (codepoints(dec), len(dec), digest(dec)))
    print("  equal as strings?  %s" % (pre == dec))
    print("-" * 66)
    print("  they render identically but differ in code points, length, and hash.")


def normalize_view(data):
    pre, dec = build(data)
    npre, ndec = nfc(pre), nfc(dec)
    print("NORMALIZE — NFC collapses both to one canonical form")
    print("-" * 66)
    print("  NFC(precomposed): %s  len %d  hash %s" % (codepoints(npre), len(npre), digest(npre)))
    print("  NFC(decomposed):  %s  len %d  hash %s" % (codepoints(ndec), len(ndec), digest(ndec)))
    print("  equal after NFC?  %s" % (npre == ndec))
    print("")
    index = {pre: "row-42"}
    print("  lookup decomposed in a dict keyed on precomposed:      %s" % index.get(dec, "MISS"))
    print("  lookup after normalizing both to NFC:                  %s" % {nfc(k): v for k, v in index.items()}.get(nfc(dec), "MISS"))
    print("-" * 66)
    print("  normalize before you compare, hash, or key -- then the two forms are one.")


def check(data):
    print("SELF-TEST — the raw forms are unequal with different hash and length; NFC makes them equal, same hash, same length")
    print("-" * 116)
    pre, dec = build(data)

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

    nfc_idempotent = nfc(nfc(dec)) == nfc(dec)
    print("  NFC is idempotent (normalizing twice changes nothing) = %s" % nfc_idempotent)

    ok = look_same_differ and different_length and different_hash and nfc_equal and nfc_same_hash and nfc_idempotent
    print("-" * 116)
    print("SELF-TEST %s  look_same_differ=%s  different_length=%s  different_hash=%s  nfc_equal=%s  nfc_same_hash=%s  nfc_idempotent=%s"
          % ("PASS" if ok else "FAIL", look_same_differ, different_length, different_hash, nfc_equal, nfc_same_hash, nfc_idempotent))
    return ok


def main():
    p = argparse.ArgumentParser(description="Normalize Unicode to a canonical form (NFC) before comparing, hashing, deduplicating, or keying, because the same visible text can be encoded as different code-point sequences that are unequal.")
    p.add_argument("--compare", action="store_true")
    p.add_argument("--normalize", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("label=%r  file=%s  (the two strings are a fixture, given as code points)" % (data["label"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.compare:
        compare_view(data)
    elif args.normalize:
        normalize_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
