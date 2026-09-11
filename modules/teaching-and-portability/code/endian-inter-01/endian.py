"""Fix the byte order explicitly -- a native-endian write reads back as a different number on a machine of the other endianness.

A multi-byte integer has to be laid out as a sequence of bytes to be written to a file, sent over a network, or hashed,
and there are two conventions for which byte comes first. BIG-ENDIAN stores the most-significant byte first, so the 32-bit
number 1 becomes the bytes 00 00 00 01 -- the way we write numbers, biggest place value on the left. LITTLE-ENDIAN stores
the least-significant byte first, so 1 becomes 01 00 00 00. Neither is more correct; they are just two orderings, and
different CPUs pick different ones: x86 and most ARM are little-endian, while some architectures and the Internet's
'network byte order' are big-endian. Inside one machine this never matters, because the machine reads back what it wrote in
its own order.

It becomes a portability bug the moment the bytes cross a machine boundary and one program serialized with the machine's
NATIVE order. If the writer used native order and it happened to be little-endian, it wrote 01 00 00 00 for the value 1;
a reader on a big-endian machine, also using native order, reads those four bytes most-significant-first and gets
0x01000000 = 16777216. Same bytes, wildly different number, and no error -- the read succeeds, it just returns garbage,
because the two machines disagreed silently about what the bytes meant. This is the classic 'works on my machine' for binary
formats: everything is fine as long as writer and reader share an endianness, and it breaks the instant they do not, which
is exactly what happens when a file or packet written on one architecture is read on another.

The fix is to never use native byte order for data that leaves the machine: choose an explicit endianness -- pick one, big
or little (big-endian is the conventional 'network byte order' for interchange) -- and specify it on BOTH the write and the
read, so the bytes mean the same thing regardless of the CPU. In Python that is int.to_bytes(width, 'big') / int.from_bytes(
bytes, 'big') or struct with a '<' or '>' prefix (never '=' or no prefix, which are native); the point is that the byte
order is part of the format's contract, stated explicitly, not inherited from whatever CPU ran the code.

The rule: serialize multi-byte integers with an explicitly chosen byte order (big or little) on both the write and the read,
never the machine's native order, because native endianness makes the bytes depend on the CPU, so a value written on a
little-endian machine reads back as a different number on a big-endian one (and vice versa) with no error.

On this fixture the value 1 stored in 4 bytes is 00 00 00 01 big-endian and 01 00 00 00 little-endian. Written big-endian and
read big-endian it is 1 (correct); written big-endian and read little-endian it is 16777216 (wrong). This computes both.

  --bytes      the value's big-endian and little-endian byte layouts, and how they differ
  --roundtrip  write big-endian, then read with a matching order (1) vs the wrong order (16777216) -- the endianness mismatch
  --check      the two encodings differ, a mismatched read returns the wrong number, and a matched explicit order round-trips

value and width_bytes are the fixture; the encodings and cross-reads are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "endian.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def encode(value, width, order):
    """Serialize the integer to `width` bytes in the given byte order ('big' or 'little')."""
    return value.to_bytes(width, order)


def decode(raw, order):
    """Read bytes back as an integer using the given byte order."""
    return int.from_bytes(raw, order)


def hex_bytes(raw):
    return " ".join("%02X" % b for b in raw)


# ----------------------------------------------------------------- printing

def bytes_view(data):
    v, w = data["value"], data["width_bytes"]
    be = encode(v, w, "big")
    le = encode(v, w, "little")
    print("BYTES — the value %d in %d bytes, two byte orders" % (v, w))
    print("-" * 56)
    print("  big-endian    (MSB first) = %s" % hex_bytes(be))
    print("  little-endian (LSB first) = %s" % hex_bytes(le))
    print("-" * 56)
    print("  same number, reversed byte order -- inside one machine, both read back as %d." % v)


def roundtrip_view(data):
    v, w = data["value"], data["width_bytes"]
    be = encode(v, w, "big")
    print("ROUNDTRIP — write big-endian, then read it two ways")
    print("-" * 60)
    print("  wrote (big-endian): %s" % hex_bytes(be))
    print("  read as big-endian    -> %d   (matched: correct)" % decode(be, "big"))
    print("  read as little-endian -> %d   (mismatched: wrong)" % decode(be, "little"))
    print("-" * 60)
    print("  a reader on the other-endian machine (native order) reads %d, not %d." % (decode(be, "little"), v))


def check(data):
    print("SELF-TEST — the two encodings differ, a mismatched read returns the wrong number, and a matched explicit order round-trips")
    print("-" * 124)
    v, w = data["value"], data["width_bytes"]
    be = encode(v, w, "big")
    le = encode(v, w, "little")

    encodings_differ = be != le
    print("  big-endian and little-endian bytes differ = %s (%s vs %s)" % (encodings_differ, hex_bytes(be), hex_bytes(le)))

    matched_read_correct = decode(be, "big") == v
    print("  big-endian bytes read as big-endian = %s (%d)" % (matched_read_correct, decode(be, "big")))

    mismatched_read_wrong = decode(be, "little") != v
    print("  big-endian bytes read as little-endian is wrong = %s (%d, not %d)" % (mismatched_read_wrong, decode(be, "little"), v))

    mismatch_is_16777216 = decode(be, "little") == 16777216
    print("  reading 00 00 00 01 as little-endian gives 16777216 = %s" % mismatch_is_16777216)

    explicit_order_roundtrips = decode(encode(v, w, "big"), "big") == v and decode(encode(v, w, "little"), "little") == v
    print("  an explicitly-chosen order round-trips either way = %s" % explicit_order_roundtrips)

    ok = encodings_differ and matched_read_correct and mismatched_read_wrong and mismatch_is_16777216 and explicit_order_roundtrips
    print("-" * 124)
    print("SELF-TEST %s  encodings_differ=%s  matched_read_correct=%s  mismatched_read_wrong=%s  mismatch_is_16777216=%s  explicit_order_roundtrips=%s"
          % ("PASS" if ok else "FAIL", encodings_differ, matched_read_correct, mismatched_read_wrong, mismatch_is_16777216, explicit_order_roundtrips))
    return ok


def main():
    p = argparse.ArgumentParser(description="Endianness: serialize multi-byte integers with an explicitly chosen byte order (big or little) on both the write and the read, never the machine's native order, because native endianness makes the bytes depend on the CPU, so a value written on a little-endian machine reads back as a different number on a big-endian one (and vice versa) with no error.")
    p.add_argument("--bytes", action="store_true")
    p.add_argument("--roundtrip", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("value=%d  width_bytes=%d  file=%s  (the value and width are a fixture)"
          % (data["value"], data["width_bytes"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.bytes:
        bytes_view(data)
    elif args.roundtrip:
        roundtrip_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
