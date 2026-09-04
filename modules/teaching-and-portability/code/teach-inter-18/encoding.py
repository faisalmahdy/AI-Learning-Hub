"""Specify encoding='utf-8' when you read and write, or the platform default corrupts non-ASCII text.

When you open a text file without naming an encoding, Python (and most tools) use the PLATFORM DEFAULT: UTF-8
on modern Linux and macOS, but historically cp1252 (Windows-1252) on Windows. That is invisible as long as the
writer and the reader run the same default. The moment they differ -- you author a lesson on Linux and a learner
opens it on an older Windows box -- the bytes are decoded with the wrong codec. A file saved as UTF-8 and read
as cp1252 does not error on common characters; it silently turns 'café €5' into 'cafÃ© â‚¬5' -- mojibake. Read
the same bytes as ASCII and it does error, loudly, on the first non-ASCII byte. Either way the learner's run does
not match your documented output, and nothing in the text says whose fault it is.

The fix is one keyword argument on every read and write: encoding='utf-8'. Pin the codec on both ends and the
bytes round-trip identically regardless of the machine's default, because the encoding is now part of the
program, not part of the environment. UTF-8 is the right default to pin: it covers all of Unicode and is the de
facto standard for interchange. The mistake is not 'using the wrong encoding' -- it is letting the ENVIRONMENT
pick the encoding, so the same code behaves differently on two machines.

On this fixture the text 'café €5' is written as UTF-8. Reading it back as UTF-8 reproduces it exactly; reading
it as cp1252 yields mojibake ('cafÃ© â‚¬5') with no error; reading it as ASCII raises UnicodeDecodeError. This
computes all three.

  --roundtrip   the text decoded under each reader encoding, and whether it matches the original
  --bytes       the raw UTF-8 bytes, showing the multi-byte characters the wrong codec misreads
  --check       only the matching encoding round-trips; the platform-default mismatch corrupts or crashes

The text and encodings are the fixture; every decode is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "text.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def encode(text, enc):
    """The bytes written to disk under the write encoding."""
    return text.encode(enc)


def decode(raw, enc):
    """Decode bytes under a reader's encoding; return the string, or the error if it fails."""
    try:
        return raw.decode(enc), None
    except UnicodeDecodeError as e:
        return None, "UnicodeDecodeError: %s" % e.reason


# ----------------------------------------------------------------- printing

def roundtrip_view(data):
    text, wenc = data["text"], data["write_encoding"]
    raw = encode(text, wenc)
    print("ROUNDTRIP — write %r as %s, read back under each encoding" % (text, wenc))
    print("-" * 66)
    for renc in data["read_encodings"]:
        got, err = decode(raw, renc)
        if err:
            print("  read %-7s -> ERROR (%s)" % (renc, err))
        else:
            print("  read %-7s -> %-12r %s" % (renc, got, "match" if got == text else "MOJIBAKE"))
    print("-" * 66)
    print("  only the encoding that matches the write survives the trip.")


def bytes_view(data):
    text, wenc = data["text"], data["write_encoding"]
    raw = encode(text, wenc)
    print("BYTES — the %s bytes of %r" % (wenc, text))
    print("-" * 66)
    print("  hex: %s" % " ".join("%02x" % b for b in raw))
    print("  %d characters -> %d bytes (the accent and euro take 2-3 bytes each)" % (len(text), len(raw)))
    print("-" * 66)
    print("  a single-byte codec reads each of those bytes as its own character.")


def check(data):
    print("SELF-TEST — only the matching encoding round-trips; the platform-default mismatch corrupts or crashes")
    print("-" * 104)
    text, wenc = data["text"], data["write_encoding"]
    raw = encode(text, wenc)

    utf8_roundtrips = decode(raw, "utf-8")[0] == text
    print("  reading as utf-8 reproduces the text = %s" % utf8_roundtrips)

    cp1252_mojibake, cp_err = decode(raw, "cp1252")
    cp1252_silently_corrupts = cp_err is None and cp1252_mojibake != text
    print("  reading as cp1252 corrupts silently (no error) = %s (%r)" % (cp1252_silently_corrupts, cp1252_mojibake))

    ascii_val, ascii_err = decode(raw, "ascii")
    ascii_raises = ascii_err is not None
    print("  reading as ascii raises = %s (%s)" % (ascii_raises, ascii_err))

    nonascii_present = any(ord(ch) > 127 for ch in text)
    print("  the text contains non-ASCII characters = %s" % nonascii_present)

    explicit_encoding_portable = decode(encode(text, "utf-8"), "utf-8")[0] == text
    print("  pinning utf-8 on both ends round-trips regardless of platform = %s" % explicit_encoding_portable)

    ok = utf8_roundtrips and cp1252_silently_corrupts and ascii_raises and nonascii_present and explicit_encoding_portable
    print("-" * 104)
    print("SELF-TEST %s  utf8_roundtrips=%s  cp1252_silently_corrupts=%s  ascii_raises=%s  nonascii_present=%s  explicit_encoding_portable=%s"
          % ("PASS" if ok else "FAIL", utf8_roundtrips, cp1252_silently_corrupts, ascii_raises, nonascii_present, explicit_encoding_portable))
    return ok


def main():
    p = argparse.ArgumentParser(description="Pin encoding='utf-8' on reads and writes so text survives a platform-default mismatch.")
    p.add_argument("--roundtrip", action="store_true")
    p.add_argument("--bytes", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("text=%r  write_encoding=%s  file=%s  (the text and encodings are a fixture)"
          % (data["text"], data["write_encoding"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.roundtrip:
        roundtrip_view(data)
    elif args.bytes:
        bytes_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
