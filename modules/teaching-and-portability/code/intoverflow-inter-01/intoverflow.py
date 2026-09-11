"""Mask fixed-width integer arithmetic to the width -- Python's ints never overflow, so a ported 32-bit hash won't match.

Many algorithms -- hashes, checksums, PRNGs, cyclic redundancy checks -- are specified in terms of FIXED-WIDTH integers
that wrap around on overflow. A 32-bit unsigned integer holds values 0 through 2**32 - 1, and when a computation exceeds
that, the high bits are simply discarded: the result is the true value modulo 2**32. In C, Java, and JavaScript this
wraparound is automatic and invisible -- it is just what the machine's integer arithmetic does -- so an algorithm's
reference implementation relies on it without ever mentioning it. The classic DJB2 string hash is exactly this: start at
5381, and for each byte compute hash = hash * 33 + byte, on a 32-bit unsigned integer, so every step silently wraps.

Now port that to Python. Python integers are arbitrary-precision: they never overflow, never wrap, they just grow. A
direct, faithful-looking translation -- hash = hash * 33 + byte with no wrap -- therefore computes a completely different
number, because after a few bytes the true value has raced past 2**32 and Python keeps every digit while the reference
kept only the low 32 bits. The two implementations agree for the first few bytes and then diverge without any error,
warning, or exception. The failure is the worst kind: silent and cross-language. A file's hash computed in C will not
match the same file's hash computed in the ported Python, so a deduplication check, a cache key, a content-addressed
lookup, or an integrity comparison that spans the two languages quietly starts missing matches, and nothing points at the
missing '& 0xFFFFFFFF'.

The fix is to mask each step to the width: hash = (hash * 33 + byte) & 0xFFFFFFFF, which discards everything above the low
32 bits and so reproduces the hardware wraparound exactly. And there is a clean identity behind it: because addition and
multiplication commute with taking a remainder, masking at every step gives the same answer as computing the full
arbitrary-precision value and taking it modulo 2**32 once at the end -- fixed-width wraparound simply IS arithmetic mod
2**width. Knowing that, the rule is easy to apply and easy to check.

The rule: when you port an algorithm that assumes fixed-width integer overflow to a language with arbitrary-precision
integers (Python), you must mask every operation to the width (& (2**width - 1)), because Python's ints never wrap on
their own, and an unmasked translation silently computes a different value that will not match the reference on any input
long enough to overflow.

On this fixture the string 'portable' is hashed with DJB2 (seed 5381, multiplier 33). The unmasked Python hash grows to a
large multi-digit integer far above 2**32; the masked hash stays within 32 bits and equals the unmasked value taken mod
2**32 -- the value a C/Java/JS implementation would produce. This computes both.

  --hash     the unmasked (wrong, unbounded) hash vs the masked (portable, 32-bit) hash of the string, side by side
  --trace    byte by byte: where the unmasked value races past 2**32 while the masked value wraps and stays in range
  --check    the unmasked hash exceeds 32 bits and differs from the reference; the masked hash fits and equals value mod 2**32

The text, seed, multiplier, and width are the fixture; every hash value is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "intoverflow.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def djb2_unmasked(data, seed, mult):
    """Faithful-looking Python port with NO wrap -- the integer grows without bound (the bug)."""
    h = seed
    for byte in data:
        h = h * mult + byte
    return h


def djb2_masked(data, seed, mult, mask):
    """Portable version: mask each step to the width, reproducing fixed-width wraparound."""
    h = seed
    for byte in data:
        h = (h * mult + byte) & mask
    return h


# ----------------------------------------------------------------- printing

def hash_view(data):
    text, seed, mult, bits = data["text"], data["seed"], data["multiplier"], data["width_bits"]
    mask = (1 << bits) - 1
    raw = text.encode("utf-8")
    unmasked = djb2_unmasked(raw, seed, mult)
    masked = djb2_masked(raw, seed, mult, mask)
    print("HASH — DJB2 of %r (seed %d, multiplier %d, %d-bit)" % (text, seed, mult, bits))
    print("-" * 68)
    print("  unmasked (Python, no wrap) = %d" % unmasked)
    print("    ... that is %d bits wide -- far above the %d-bit range 0..%d" % (unmasked.bit_length(), bits, mask))
    print("  masked   (portable 32-bit) = %d" % masked)
    print("    ... within 0..%d, the value a C/Java/JS implementation returns" % mask)
    print("-" * 68)
    print("  same algorithm, different answers: the missing '& 0x%X' is the whole bug." % mask)


def trace_view(data):
    text, seed, mult, bits = data["text"], data["seed"], data["multiplier"], data["width_bits"]
    mask = (1 << bits) - 1
    raw = text.encode("utf-8")
    print("TRACE — byte by byte, where the unmasked value escapes the 32-bit range")
    print("-" * 74)
    print("  byte        unmasked h                masked h      over 2**%d?" % bits)
    hu = seed
    hm = seed
    for byte in raw:
        hu = hu * mult + byte
        hm = (hm * mult + byte) & mask
        over = "yes" if hu > mask else "no"
        print("  %-4r  %-24d  %-12d  %s" % (chr(byte), hu, hm, over))
    print("-" * 74)
    print("  once unmasked passes 2**%d, the two columns diverge and never agree again." % bits)


def check(data):
    print("SELF-TEST — the unmasked hash overflows and differs from the reference; the masked hash fits and equals value mod 2**width")
    print("-" * 124)
    text, seed, mult, bits = data["text"], data["seed"], data["multiplier"], data["width_bits"]
    mask = (1 << bits) - 1
    modulus = 1 << bits
    raw = text.encode("utf-8")
    unmasked = djb2_unmasked(raw, seed, mult)
    masked = djb2_masked(raw, seed, mult, mask)

    unmasked_overflows = unmasked > mask
    print("  unmasked hash exceeds the %d-bit range = %s (%d bits wide)" % (bits, unmasked_overflows, unmasked.bit_length()))

    masked_fits = 0 <= masked <= mask
    print("  masked hash fits in %d bits = %s (%d)" % (bits, masked_fits, masked))

    they_differ = masked != unmasked
    print("  the two implementations give different values = %s (%d vs %d)" % (they_differ, masked, unmasked))

    masking_equals_mod = masked == unmasked % modulus
    print("  masking each step == taking the full value mod 2**%d = %s (%d)" % (bits, masking_equals_mod, unmasked % modulus))

    reference = unmasked % modulus
    masked_matches_reference = masked == reference
    print("  masked hash matches the C/Java/JS reference value = %s (%d)" % (masked_matches_reference, reference))

    ok = unmasked_overflows and masked_fits and they_differ and masking_equals_mod and masked_matches_reference
    print("-" * 124)
    print("SELF-TEST %s  unmasked_overflows=%s  masked_fits=%s  they_differ=%s  masking_equals_mod=%s  masked_matches_reference=%s"
          % ("PASS" if ok else "FAIL", unmasked_overflows, masked_fits, they_differ, masking_equals_mod, masked_matches_reference))
    return ok


def main():
    p = argparse.ArgumentParser(description="Fixed-width integer overflow: when you port an algorithm that assumes fixed-width integer wraparound (a hash, checksum, or PRNG) to a language with arbitrary-precision integers like Python, you must mask every operation to the width (& (2**width - 1)), because Python's ints never overflow and an unmasked translation silently computes a different value than the reference on any input long enough to overflow -- masking each step equals taking the full value modulo 2**width.")
    p.add_argument("--hash", action="store_true")
    p.add_argument("--trace", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("text=%r  seed=%d  multiplier=%d  width_bits=%d  file=%s  (the text and parameters are a fixture)"
          % (data["text"], data["seed"], data["multiplier"], data["width_bits"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.hash:
        hash_view(data)
    elif args.trace:
        trace_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
