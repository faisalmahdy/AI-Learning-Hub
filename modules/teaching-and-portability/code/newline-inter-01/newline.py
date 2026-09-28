r"""Normalize line endings before you hash, or the same text written on two platforms has two different hashes.

Text that looks identical can be different bytes, and the usual culprit is the invisible character at the end of
each line. Unix ends a line with a single line-feed byte (LF, \n); Windows ends it with a carriage-return plus a
line-feed (CRLF, \r\n). Open a file in an editor on either platform and you see the same lines -- the \r is
invisible -- but the file on Windows is one byte longer per line. So anything that looks at the raw bytes rather
than the rendered text sees two different files: a byte-length check, a checksum, a hash, a digital signature, a
byte-for-byte diff. You compute a hash of your data file, document it to prove integrity, and a colleague on
another platform recomputes it and gets a different value -- not because the data changed, but because their
editor or their git checkout used the other line ending. The documented hash does not reproduce.

The fix is to normalize the line endings before you do anything byte-sensitive: convert CRLF to LF (or the
reverse, consistently) so the bytes match whatever platform produced the file. Then the hash is a hash of the
CONTENT, not of the content-plus-platform-convention, and it reproduces everywhere. The same discipline underlies
git's autocrlf setting, the .gitattributes 'text' attribute, and opening files in text mode with an explicit
newline policy: pick one line ending, normalize to it, and stop letting an invisible byte fork your data.

On this fixture the same three lines written with LF are 22 bytes and hash to e0af2be21679; written with CRLF
they are 25 bytes (three extra \r) and hash to 45fc3c65c440 -- a different hash for identical text. Normalizing
CRLF to LF makes both 22 bytes with the same hash. This computes both.

  --bytes      the LF and CRLF byte lengths and hashes for the same lines
  --normalize  the two files normalized to LF, showing equal bytes and one shared hash
  --check      the raw bytes and hashes differ; normalizing to LF makes them identical

The logical lines are the fixture; every byte string and hash is computed. Stdlib only.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "newline.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def encode(lines, ending):
    """Join the lines with the given line ending and encode to bytes."""
    return (ending.join(lines) + ending).encode("utf-8")


def normalize(data_bytes):
    """Normalize line endings to LF by replacing every CRLF with a single LF."""
    return data_bytes.replace(b"\r\n", b"\n")


def digest(data_bytes):
    """A short SHA-256 hex digest of the bytes."""
    return hashlib.sha256(data_bytes).hexdigest()[:12]


# ----------------------------------------------------------------- printing

def bytes_view(data):
    lines = data["lines"]
    lf, crlf = encode(lines, "\n"), encode(lines, "\r\n")
    print("BYTES — same %d lines, two line endings" % len(lines))
    print("-" * 58)
    print("  LF   (Unix):     %d bytes   hash %s" % (len(lf), digest(lf)))
    print("  CRLF (Windows):  %d bytes   hash %s" % (len(crlf), digest(crlf)))
    print("-" * 58)
    print("  identical text, %d extra bytes (one \\r per line), a different hash." % (len(crlf) - len(lf)))


def normalize_view(data):
    lines = data["lines"]
    lf, crlf = encode(lines, "\n"), encode(lines, "\r\n")
    nlf, ncrlf = normalize(lf), normalize(crlf)
    print("NORMALIZE — both files converted to LF before hashing")
    print("-" * 58)
    print("  normalized LF:    %d bytes   hash %s" % (len(nlf), digest(nlf)))
    print("  normalized CRLF:  %d bytes   hash %s" % (len(ncrlf), digest(ncrlf)))
    print("  equal after normalizing: %s" % (nlf == ncrlf))
    print("-" * 58)
    print("  normalize to one line ending and the hash is of the content, not the platform.")


def check(data):
    print("SELF-TEST — the raw bytes and hashes differ; normalizing to LF makes them identical")
    print("-" * 100)
    lines = data["lines"]
    lf, crlf = encode(lines, "\n"), encode(lines, "\r\n")

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

    ok = bytes_differ and crlf_longer_by_line_count and hashes_differ and normalized_equal and normalized_hashes_equal
    print("-" * 100)
    print("SELF-TEST %s  bytes_differ=%s  crlf_longer_by_line_count=%s  hashes_differ=%s  normalized_equal=%s  normalized_hashes_equal=%s"
          % ("PASS" if ok else "FAIL", bytes_differ, crlf_longer_by_line_count, hashes_differ, normalized_equal, normalized_hashes_equal))
    return ok


def main():
    p = argparse.ArgumentParser(description="Line-ending differences (CRLF vs LF) change the bytes and the hash of identical text; normalize before hashing.")
    p.add_argument("--bytes", action="store_true")
    p.add_argument("--normalize", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("lines=%d  file=%s  (the lines are a fixture)" % (len(data["lines"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.bytes:
        bytes_view(data)
    elif args.normalize:
        normalize_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
