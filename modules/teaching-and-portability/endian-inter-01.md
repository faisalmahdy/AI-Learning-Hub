---
id: endian-inter-01
title: Fix the byte order explicitly — a native-endian write reads back as a different number on a machine of the other endianness
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: A multi-byte integer has to be laid out as a sequence of bytes to be written to a file, sent over a network, or hashed, and there are two conventions for which byte comes first. Big-endian stores the most-significant byte first, so the 32-bit number 1 becomes 00 00 00 01. Little-endian stores the least-significant byte first, so 1 becomes 01 00 00 00. Neither is more correct; different CPUs pick different ones (x86 and most ARM are little-endian, while some architectures and the Internet's "network byte order" are big-endian). Inside one machine this never matters, because the machine reads back what it wrote in its own order. It becomes a portability bug the moment the bytes cross a machine boundary and one program serialized with the machine's native order: if the writer's native order was little-endian it wrote 01 00 00 00 for the value 1, and a reader on a big-endian machine using native order reads those bytes most-significant-first and gets 0x01000000 = 16777216 — same bytes, wildly different number, and no error, because the machines disagreed silently about what the bytes meant. This is the classic "works on my machine" for binary formats. The fix is to never use native byte order for data that leaves the machine: choose an explicit endianness (big-endian is the conventional network byte order for interchange) and specify it on both the write and the read. On a fixture where the value 1 in 4 bytes is 00 00 00 01 big-endian and 01 00 00 00 little-endian, writing big-endian and reading big-endian yields 1 (correct), while writing big-endian and reading little-endian yields 16777216 (wrong).
eli5: Imagine writing the number "one thousand two hundred thirty-four" but you and a friend disagree about which end to start from: you write the digits big-side-first as 1234, and your friend reads numbers little-side-first, so when they see your 1234 they read it as 4321 — a totally different number. Computers store big numbers as a few bytes, and there are two "reading directions" (big-end-first or little-end-first). As long as you write and read in the same direction, everything's fine. But send your bytes to a computer that reads the other way, and it gets a scrambled number — no complaint, just the wrong answer. The fix is to agree on a direction ahead of time and both stick to it, instead of each using your own habit.
---

## Why this module

Binary serialization has a silent disagreement built into it: two machines can store the same integer as the same bytes in opposite orders, and each is certain its order is the obvious one. As long as a program writes and reads on the same machine, the disagreement never surfaces — the machine is consistent with itself. The trap springs the instant the bytes travel to a machine that reads the other way, because nothing about the bytes announces their order; the receiver applies its own convention and gets a different number, with no error to signal that anything went wrong. The bug is invisible precisely because both machines are behaving "correctly" by their own lights.

Big-endian stores the most-significant byte first, so the 32-bit number 1 becomes 00 00 00 01; little-endian stores the least-significant byte first, so 1 becomes 01 00 00 00. Different CPUs pick different orders. If a writer used its native order and it was little-endian, it wrote 01 00 00 00 for the value 1, and a reader on a big-endian machine using native order reads those four bytes most-significant-first and gets 0x01000000 = 16777216 — same bytes, wildly different number, and no error.

The fix is to never use native byte order for data that leaves the machine: choose an explicit endianness (big-endian is the conventional "network byte order") and specify it on both the write and the read, so the bytes mean the same thing regardless of the CPU. This module encodes and cross-reads a value both ways.

**Serialize multi-byte integers with an explicitly chosen byte order (big or little) on both the write and the read, never the machine's native order, because native endianness makes the bytes depend on the CPU — so a value written on a little-endian machine reads back as a different number on a big-endian one (and vice versa) with no error.**

## Concepts

**Encoding chooses a byte order, and decoding must use the same one** — Python's `to_bytes`/`from_bytes` take the order as an explicit argument.

```python filename=modules/teaching-and-portability/code/endian-inter-01/endian.py:51-58 COMPLETE
def encode(value, width, order):
    """Serialize the integer to `width` bytes in the given byte order ('big' or 'little')."""
    return value.to_bytes(width, order)


def decode(raw, order):
    """Read bytes back as an integer using the given byte order."""
    return int.from_bytes(raw, order)
```

**We render the raw bytes as hex** to see the layout the two orders produce.

```python filename=modules/teaching-and-portability/code/endian-inter-01/endian.py:61-62 COMPLETE
def hex_bytes(raw):
    return " ".join("%02X" % b for b in raw)
```

<svg role="img" aria-label="The 32-bit value 1 laid out two ways: big-endian bytes 00 00 00 01 with the 01 last, little-endian bytes 01 00 00 00 with the 01 first" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the value 1 in 4 bytes — the '01' sits at opposite ends</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">big-endian</text>
  <g font-size="8" fill="var(--panel)">
    <rect x="90" y="24" width="40" height="16" fill="var(--muted)"/><text x="98" y="36">00</text>
    <rect x="132" y="24" width="40" height="16" fill="var(--muted)"/><text x="140" y="36">00</text>
    <rect x="174" y="24" width="40" height="16" fill="var(--muted)"/><text x="182" y="36">00</text>
    <rect x="216" y="24" width="40" height="16" fill="var(--s1)"/><text x="224" y="36">01</text>
  </g>
  <text x="90" y="52" fill="var(--muted)" font-size="6">MSB first — the 01 is last</text>
  <text x="10" y="76" fill="var(--muted)" font-size="7">little-endian</text>
  <g font-size="8" fill="var(--panel)">
    <rect x="90" y="66" width="40" height="16" fill="var(--s1)"/><text x="98" y="78">01</text>
    <rect x="132" y="66" width="40" height="16" fill="var(--muted)"/><text x="140" y="78">00</text>
    <rect x="174" y="66" width="40" height="16" fill="var(--muted)"/><text x="182" y="78">00</text>
    <rect x="216" y="66" width="40" height="16" fill="var(--muted)"/><text x="224" y="78">00</text>
  </g>
  <text x="90" y="94" fill="var(--muted)" font-size="6">LSB first — the 01 is first</text>
</svg>
^ The value 1 has one non-zero byte (01) and three zero bytes; big-endian places the 01 last (most-significant first) and little-endian places it first (least-significant first) — the same number, the same four bytes, in opposite order.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/endian-inter-01/endian.py

The fixture is the value and its storage width.

```json filename=modules/teaching-and-portability/code/endian-inter-01/endian.json:3-4 COMPLETE
  "value": 1,
  "width_bytes": 4
```

Run `--bytes`.

```text filename=--bytes
BYTES — the value 1 in 4 bytes, two byte orders
--------------------------------------------------------
  big-endian    (MSB first) = 00 00 00 01
  little-endian (LSB first) = 01 00 00 00
--------------------------------------------------------
  same number, reversed byte order -- inside one machine, both read back as 1.
```

The value 1 stored in four bytes is 00 00 00 01 big-endian and 01 00 00 00 little-endian — the single 01 byte moves from the last position to the first. Both are correct encodings of the number 1; they are just two conventions for which end the most-significant byte goes. The key phrase is the last line: *inside one machine, both read back as 1*. A little-endian machine that writes 01 00 00 00 and reads it back little-endian gets 1; a big-endian machine that writes 00 00 00 01 and reads it back big-endian also gets 1. Each machine is perfectly self-consistent, which is exactly why the bug is invisible during development — you test on one machine, write and read agree, everything works. The disagreement only exists between machines of different endianness, and only when the byte order is left to each machine's native default instead of being fixed by the format.

## Build

Cross the boundary: write with one order and read with the other, as two machines of different endianness would.

```text filename=--roundtrip
ROUNDTRIP — write big-endian, then read it two ways
------------------------------------------------------------
  wrote (big-endian): 00 00 00 01
  read as big-endian    -> 1   (matched: correct)
  read as little-endian -> 16777216   (mismatched: wrong)
------------------------------------------------------------
  a reader on the other-endian machine (native order) reads 16777216, not 1.
```

<svg role="img" aria-label="A little-endian machine writes the value 1 as 01 00 00 00 and sends the bytes to a big-endian machine, which reads them as 16777216" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">native order on each side: same bytes, different number</text>
  <rect x="14" y="28" width="80" height="30" fill="none" stroke="var(--s1)"/><text x="20" y="42" fill="var(--s1)" font-size="7">little-endian</text><text x="20" y="53" fill="var(--muted)" font-size="6">writes 1</text>
  <rect x="110" y="34" width="80" height="18" fill="var(--panel)" stroke="var(--ink)"/><text x="116" y="46" fill="var(--ink)" font-size="7">01 00 00 00</text>
  <path d="M94 43 L108 43" fill="none" stroke="var(--muted)"/><path d="M190 43 L204 43" fill="none" stroke="var(--muted)"/>
  <rect x="206" y="28" width="80" height="30" fill="none" stroke="var(--s2)"/><text x="212" y="42" fill="var(--s2)" font-size="7">big-endian</text><text x="212" y="53" fill="var(--s2)" font-size="6">reads 16777216</text>
  <text x="14" y="80" fill="var(--muted)" font-size="6">the bytes arrived perfectly; the two CPUs just disagree on their order</text>
</svg>
^ A little-endian machine writes the value 1 in its native order (01 00 00 00) and sends the bytes intact to a big-endian machine, which reads them in *its* native order and reconstructs 16,777,216 — the transmission was flawless; only the byte-order convention differed.

The writer serialized the value 1 as big-endian: 00 00 00 01. A reader that also uses big-endian reads those bytes most-significant-first and reconstructs 1 — correct. A reader that uses little-endian reads the *same four bytes* least-significant-first, treating 00 as the low byte and 01 as the high byte, and reconstructs 0x01000000 = 16777216 — off by a factor of sixteen million. Nothing failed: `int.from_bytes` happily accepted the bytes and returned a valid integer; it was simply the wrong integer, because the reader applied a different convention than the writer. This is the whole hazard in one number: 1 became 16777216 not through corruption or a bug in the arithmetic, but because two programs disagreed about the order of bytes that were transmitted perfectly. If the writer had used its *native* order (leaving it to whatever CPU compiled the code) and the reader did the same on a different-endian CPU, this is exactly the silent mismatch that would occur — and it would have passed every test that ran writer and reader on the same architecture.

```python filename=modules/teaching-and-portability/code/endian-inter-01/endian.py:98-105 COMPLETE
    encodings_differ = be != le
    print("  big-endian and little-endian bytes differ = %s (%s vs %s)" % (encodings_differ, hex_bytes(be), hex_bytes(le)))

    matched_read_correct = decode(be, "big") == v
    print("  big-endian bytes read as big-endian = %s (%d)" % (matched_read_correct, decode(be, "big")))

    mismatched_read_wrong = decode(be, "little") != v
    print("  big-endian bytes read as little-endian is wrong = %s (%d, not %d)" % (mismatched_read_wrong, decode(be, "little"), v))
```

## Definition of done

The self-test pins the differing encodings, the correct matched read, the wrong mismatched read (and its exact value), and the explicit round-trip.

```python filename=modules/teaching-and-portability/code/endian-inter-01/endian.py:107-110 COMPLETE
    mismatch_is_16777216 = decode(be, "little") == 16777216
    print("  reading 00 00 00 01 as little-endian gives 16777216 = %s" % mismatch_is_16777216)

    explicit_order_roundtrips = decode(encode(v, w, "big"), "big") == v and decode(encode(v, w, "little"), "little") == v
    print("  an explicitly-chosen order round-trips either way = %s" % explicit_order_roundtrips)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the two encodings differ, a mismatched read returns the wrong number, and a matched explicit order round-trips
----------------------------------------------------------------------------------------------------------------------------
  big-endian and little-endian bytes differ = True (00 00 00 01 vs 01 00 00 00)
  big-endian bytes read as big-endian = True (1)
  big-endian bytes read as little-endian is wrong = True (16777216, not 1)
  reading 00 00 00 01 as little-endian gives 16777216 = True
  an explicitly-chosen order round-trips either way = True
```

<svg role="img" aria-label="The same big-endian bytes 00 00 00 01 read two ways: matched big-endian gives 1, mismatched little-endian gives 16777216" viewBox="0 0 300 92" width="300" height="92">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the same bytes 00 00 00 01, read two ways</text>
  <rect x="100" y="24" width="100" height="16" fill="none" stroke="var(--ink)"/><text x="112" y="36" fill="var(--ink)" font-size="8">00 00 00 01</text>
  <path d="M100 40 L70 58" fill="none" stroke="var(--s1)"/><path d="M200 40 L230 58" fill="none" stroke="var(--s2)"/>
  <text x="30" y="72" fill="var(--s1)" font-size="7">big-endian → 1 ✓</text>
  <text x="200" y="72" fill="var(--s2)" font-size="7">little-endian → 16777216 ✗</text>
  <text x="10" y="88" fill="var(--muted)" font-size="6">identical bytes, two conventions, two answers — no error either way</text>
</svg>
^ The identical bytes 00 00 00 01 decode to 1 when read big-endian (matching the write) and to 16,777,216 when read little-endian (mismatched) — one set of bytes, two conventions, two very different numbers, with no error to flag the mismatch.

**Done means the endianness hazard is proven on real bytes: the value 1 in 4 bytes is 00 00 00 01 big-endian and 01 00 00 00 little-endian, and the same big-endian bytes decode to 1 when read big-endian and to 16777216 when read little-endian, while an explicitly-chosen order round-trips either way — so multi-byte integers must be serialized with an explicit byte order on both write and read, never native.**

## Boss fight

Predict two ways endianness is broader and subtler than "pick big or little," because it touches more than integers and the fix has a matching discipline on the read side.

The first trap is that endianness applies to every multi-byte value in a binary format, not just one integer, and the format must specify the order for all of them consistently — mixing conventions within a format, or forgetting a field, corrupts silently just like the single-integer case. A struct with an int, a float, and a length prefix has an endianness for each multi-byte field, and floating-point numbers (IEEE 754) have a byte order too, so a naive `struct.pack` with the native `=`/no-prefix format string makes the *whole record* machine-dependent; the fix is a `<` or `>` prefix that fixes the order for every field. This is why real binary formats state their endianness in the spec (PNG and network protocols are big-endian; many file formats and most modern CPUs are little-endian), and why formats that must be self-describing sometimes include a BYTE-ORDER MARK — a known magic value at the start (like the 0xFEFF in Unicode, or TIFF's "II"/"MM" tag) that lets the reader detect which endianness the writer used and adapt. The broad rule is: the byte order is part of the wire/file format contract, declared once and applied to every multi-byte value, or it is a bug waiting on every field.

The second trap is that the safest modern move is often to sidestep hand-rolled binary serialization entirely, because getting endianness (and width, and alignment, and signedness) right on every field by hand is error-prone. Text-based interchange formats — JSON, CSV, XML — have no endianness at all, because numbers are written as decimal digit strings that mean the same thing everywhere (this is one reason they dominate for cross-system data despite being larger and slower). When binary efficiency is needed, schema-based serialization libraries (Protocol Buffers, FlatBuffers, Avro, MessagePack) define the byte order (typically little-endian, or varint encodings) as part of the format and handle it for you, so you describe the data's shape and never touch a byte-order flag. So the layered guidance is: for interchange, prefer a format that removes the question (text, or a schema library that fixes the order); when you must write raw bytes, always specify explicit endianness on write and read and treat native order as a bug outside a single machine; and remember that the same "state the convention explicitly, don't inherit the platform default" discipline is what fixes encodings, line endings, and locales — endianness is the binary member of that family.

**Endianness is a whole-format property, not one field: every multi-byte value (integers AND IEEE-754 floats) needs a fixed order, so a native `struct` format string makes the entire record machine-dependent — declare the order once in the format's contract (a `<`/`>` prefix, a spec-stated endianness, or a byte-order mark for self-describing formats) and apply it to every field. And the safest move is often to avoid hand-rolled binary: text formats (JSON/CSV) have no endianness because numbers are decimal strings, and schema libraries (Protobuf, Avro, MessagePack) fix the byte order for you — reserve raw binary for when you need it, and there always specify endianness explicitly, treating native order as the same inherit-the-platform-default bug that breaks encodings, line endings, and locales.**

## External resources

References on byte order and binary serialization (the endianness entry in any systems text, Python's `int.to_bytes`/`int.from_bytes` and `struct` documentation, and network byte order / `htonl`) — the two conventions, how to specify them explicitly, and why native order is non-portable.

Documentation for schema-based and text serialization (Protocol Buffers, FlatBuffers, Avro, MessagePack, JSON) — how these formats fix or eliminate the byte-order question so cross-machine data does not depend on the writer's CPU.

The companion integer-overflow, encoding, and line-ending modules in this topic — endianness is the binary-serialization member of the same family, where a platform default (byte order, integer width, text encoding, newline) silently changes how bytes are interpreted across machines, and the fix is always to state the convention explicitly rather than inherit it.
