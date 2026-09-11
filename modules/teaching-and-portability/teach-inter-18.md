---
id: teach-inter-18
title: Specify encoding='utf-8' when you read and write — or the platform default corrupts non-ASCII text
topic: teaching-and-portability
level: intermediate
status: ready
time: 19 min
summary: Open a text file without naming an encoding and Python uses the platform default — UTF-8 on modern Linux and macOS, but historically cp1252 on Windows. That is invisible while writer and reader share a default, and a silent bug the moment they differ. A lesson authored on Linux as UTF-8 and opened on an older Windows box is decoded with cp1252, turning "café €5" into "cafÃ© â‚¬5" — mojibake, with no error. Read the same bytes as ASCII and it errors loudly on the first non-ASCII byte. Either way the learner's run does not match your documented output, and nothing says whose fault it is. The fix is one keyword argument on every read and write — encoding='utf-8' — which makes the codec part of the program instead of the environment. On the text "café €5" written as UTF-8, reading as UTF-8 reproduces it, cp1252 yields mojibake, and ASCII raises.
eli5: Letters are saved as numbers, and you need the same codebook to turn the numbers back into letters. If you save with one codebook and your friend opens with another, plain letters look fine but the special ones (é, €) turn into gibberish — or the program chokes. Telling both sides "use the UTF-8 codebook" makes the message come back exactly as written, on any computer.
---

## Why this module

A program that reads or writes text without naming an encoding is not encoding-free — it silently borrows the encoding from whatever machine it runs on, and machines disagree.

Open a text file with no encoding specified and the default is chosen by the platform: UTF-8 on modern Linux and macOS, cp1252 (Windows-1252) on much of the Windows world. As long as the person who wrote the file and the person who reads it share that default, everything looks fine. The bug is latent, waiting for the two to differ. You author a lesson on Linux, saved as UTF-8; a learner opens it on an older Windows setup that decodes as cp1252. The plain letters survive, but "café €5" comes back as "cafÃ© â‚¬5" — mojibake — and no exception fires, because those bytes are all valid cp1252. The learner sees garbage where your documentation promised clean text and cannot tell whether they broke something or the file is wrong.

**Omitting the encoding does not skip the choice — it delegates the choice to the environment, so the same bytes decode differently on two machines.**

The fix is a single keyword argument on every read and write: encoding='utf-8'. Pin it on both ends and the codec is part of the program, not the platform, so the text round-trips identically everywhere. This module writes one string as UTF-8 and reads it back three ways to show which survive.

## Concepts

**Text is stored as bytes**, and an **encoding** is the codebook mapping characters to bytes and back. Encode with one codebook, decode with another, and you get the wrong characters — or an error.

**UTF-8** is a variable-width encoding covering all of Unicode: ASCII characters are one byte, but an accented letter like é is two bytes and a symbol like € is three. **cp1252** is a single-byte legacy encoding — every byte is one character. **ASCII** is single-byte and only defines 0–127.

The **platform default** is the encoding Python uses when you do not name one. It varies by operating system, which is the entire problem: `open("f.txt")` is a different program on Linux and Windows.

Two failure modes follow. Decoding UTF-8 bytes as **cp1252** never errors — every byte is a valid cp1252 character — so a multi-byte UTF-8 character becomes two or three wrong single-byte characters: silent mojibake. Decoding them as **ASCII** errors on the first byte above 127: a loud crash. The silent one is worse, because it corrupts data that looks like it was read fine.

**A missing encoding is a portability bug that hides until a reader's platform default differs from the writer's — then it corrupts silently or crashes loudly.**

The choice is made either way — the only question is whether your code makes it or the operating system does.

<svg role="img" aria-label="Two paths for the encoding decision: left, code names utf-8 and both machines agree; right, the OS picks and Linux and Windows disagree" viewBox="0 0 300 120" width="300" height="120">
  <text x="30" y="16" fill="var(--s2)" font-size="8">code names it</text>
  <rect x="20" y="22" width="110" height="18" fill="none" stroke="var(--s2)" stroke-width="1"/>
  <text x="30" y="35" fill="var(--ink)" font-size="8">encoding='utf-8'</text>
  <text x="35" y="60" fill="var(--muted)" font-size="7">Linux → utf-8</text>
  <text x="30" y="74" fill="var(--muted)" font-size="7">Windows → utf-8</text>
  <text x="40" y="92" fill="var(--s2)" font-size="8">same everywhere</text>
  <line x1="150" y1="10" x2="150" y2="110" stroke="var(--line)" stroke-width="1"/>
  <text x="185" y="16" fill="var(--s1)" font-size="8">OS picks it</text>
  <rect x="175" y="22" width="110" height="18" fill="none" stroke="var(--s1)" stroke-width="1" stroke-dasharray="2 2"/>
  <text x="185" y="35" fill="var(--ink)" font-size="8">open(path)</text>
  <text x="190" y="60" fill="var(--muted)" font-size="7">Linux → utf-8</text>
  <text x="185" y="74" fill="var(--muted)" font-size="7">Windows → cp1252</text>
  <text x="195" y="92" fill="var(--s1)" font-size="8">mismatch → mojibake</text>
</svg>
^ Naming the encoding makes every machine agree; leaving it to the platform lets Linux and Windows pick different codebooks, which is the mismatch that corrupts.

UTF-8 is the encoding to pin because it represents all of Unicode and is the de facto interchange standard; the discipline is to name it explicitly on both the write and the read.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/teach-inter-18/encoding.py

The fixture is one non-ASCII string, the encoding it was written with, and the encodings a reader might use.

```json filename=modules/teaching-and-portability/code/teach-inter-18/text.json:1-6 COMPLETE
{
  "_meta": "A snippet of lesson text containing non-ASCII characters (an accented letter and a currency symbol). write_encoding is the codec the author saved it with (UTF-8, the modern default on Linux/macOS). read_encodings are codecs a learner's machine might use to read it back -- including cp1252, a common Windows default, and ascii. The question: does the text survive the trip when the reader's encoding differs from the writer's?",
  "text": "café €5",
  "write_encoding": "utf-8",
  "read_encodings": ["utf-8", "cp1252", "ascii"]
}
```

Encode turns the string into bytes under the write codec; decode turns bytes back into a string under a reader's codec, catching the error when it fails.

```python filename=modules/teaching-and-portability/code/teach-inter-18/encoding.py:40-50 COMPLETE
def encode(text, enc):
    """The bytes written to disk under the write encoding."""
    return text.encode(enc)


def decode(raw, enc):
    """Decode bytes under a reader's encoding; return the string, or the error if it fails."""
    try:
        return raw.decode(enc), None
    except UnicodeDecodeError as e:
        return None, "UnicodeDecodeError: %s" % e.reason
```

Run `--roundtrip` and read the same bytes three ways.

```text filename=--roundtrip
ROUNDTRIP — write 'café €5' as utf-8, read back under each encoding
------------------------------------------------------------------
  read utf-8   -> 'café €5'    match
  read cp1252  -> 'cafÃ© â‚¬5' MOJIBAKE
  read ascii   -> ERROR (UnicodeDecodeError: ordinal not in range(128))
```

Only the reader whose encoding matches the writer's gets the text back. cp1252 returns "cafÃ© â‚¬5" with no error at all — the corruption is silent. ASCII refuses outright. The exact same ten bytes produce three different outcomes depending on nothing but the reader's default.

<svg role="img" aria-label="One set of UTF-8 bytes decoded three ways: utf-8 gives the original, cp1252 gives mojibake, ascii errors" viewBox="0 0 300 130" width="300" height="130">
  <rect x="110" y="12" width="80" height="18" fill="var(--panel)" stroke="var(--line)" stroke-width="1"/>
  <text x="118" y="25" fill="var(--ink)" font-size="8">UTF-8 bytes</text>
  <line x1="150" y1="30" x2="60" y2="55" stroke="var(--grid)" stroke-width="1"/>
  <line x1="150" y1="30" x2="150" y2="55" stroke="var(--grid)" stroke-width="1"/>
  <line x1="150" y1="30" x2="245" y2="55" stroke="var(--grid)" stroke-width="1"/>
  <text x="25" y="70" fill="var(--s2)" font-size="8">utf-8</text>
  <text x="10" y="84" fill="var(--muted)" font-size="8">café €5</text>
  <text x="20" y="98" fill="var(--s2)" font-size="7">match</text>
  <text x="128" y="70" fill="var(--s1)" font-size="8">cp1252</text>
  <text x="118" y="84" fill="var(--muted)" font-size="8">cafÃ© â‚¬5</text>
  <text x="120" y="98" fill="var(--s1)" font-size="7">mojibake</text>
  <text x="225" y="70" fill="var(--s1)" font-size="8">ascii</text>
  <text x="222" y="84" fill="var(--muted)" font-size="8">ERROR</text>
  <text x="216" y="98" fill="var(--s1)" font-size="7">crash</text>
</svg>
^ The identical bytes fan out to three fates by reader encoding alone — the correct text, silent mojibake, or a crash — which is why the encoding cannot be left to the platform.

## Build

The bytes view dumps the raw UTF-8 bytes and the character-to-byte expansion behind the mojibake.

```python filename=modules/teaching-and-portability/code/teach-inter-18/encoding.py:70-76 COMPLETE
def bytes_view(data):
    text, wenc = data["text"], data["write_encoding"]
    raw = encode(text, wenc)
    print("BYTES — the %s bytes of %r" % (wenc, text))
    print("-" * 66)
    print("  hex: %s" % " ".join("%02x" % b for b in raw))
    print("  %d characters -> %d bytes (the accent and euro take 2-3 bytes each)" % (len(text), len(raw)))
```

Why does cp1252 mangle it into more characters than the original? Run `--bytes`.

```text filename=--bytes
BYTES — the utf-8 bytes of 'café €5'
------------------------------------------------------------------
  hex: 63 61 66 c3 a9 20 e2 82 ac 35
  7 characters -> 10 bytes (the accent and euro take 2-3 bytes each)
------------------------------------------------------------------
  a single-byte codec reads each of those bytes as its own character.
```

The seven-character string is ten bytes: é is the two bytes c3 a9, and € is the three bytes e2 82 ac. UTF-8 knows to group them back into one character each. cp1252, a single-byte codec, reads c3 as Ã, a9 as ©, e2 as â, and so on — five wrong characters where there should be two. The mojibake is not random; it is the multi-byte characters read one byte at a time.

<svg role="img" aria-label="The UTF-8 bytes c3 a9 form one character é, but cp1252 reads them as two characters Ã and ©" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="20" fill="var(--muted)" font-size="8">bytes: c3 a9</text>
  <rect x="90" y="10" width="30" height="16" fill="var(--s2)"/>
  <rect x="122" y="10" width="30" height="16" fill="var(--s2)"/>
  <text x="95" y="22" fill="var(--panel)" font-size="8">c3</text>
  <text x="127" y="22" fill="var(--panel)" font-size="8">a9</text>
  <text x="160" y="22" fill="var(--muted)" font-size="14">→</text>
  <text x="185" y="45" fill="var(--s2)" font-size="9">UTF-8: one char</text>
  <line x1="105" y1="28" x2="230" y2="38" stroke="var(--s2)" stroke-width="1"/>
  <line x1="137" y1="28" x2="230" y2="38" stroke="var(--s2)" stroke-width="1"/>
  <text x="232" y="41" fill="var(--ink)" font-size="12">é</text>
  <text x="185" y="80" fill="var(--s1)" font-size="9">cp1252: two chars</text>
  <line x1="105" y1="28" x2="215" y2="74" stroke="var(--s1)" stroke-width="1"/>
  <text x="218" y="78" fill="var(--ink)" font-size="12">Ã</text>
  <line x1="137" y1="28" x2="245" y2="74" stroke="var(--s1)" stroke-width="1"/>
  <text x="248" y="78" fill="var(--ink)" font-size="12">©</text>
</svg>
^ UTF-8 groups the two bytes c3 a9 into the single character é; a single-byte codec reads them as two separate characters, Ã and ©, which is exactly the mojibake.

## Definition of done

The self-test pins both failure modes and the fix: UTF-8 round-trips, cp1252 corrupts silently, ASCII raises, the text is genuinely non-ASCII, and pinning UTF-8 on both ends round-trips regardless of platform.

```python filename=modules/teaching-and-portability/code/teach-inter-18/encoding.py:87-101 COMPLETE
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
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — only the matching encoding round-trips; the platform-default mismatch corrupts or crashes
--------------------------------------------------------------------------------------------------------
  reading as utf-8 reproduces the text = True
  reading as cp1252 corrupts silently (no error) = True ('cafÃ© â‚¬5')
  reading as ascii raises = True (UnicodeDecodeError: ordinal not in range(128))
  the text contains non-ASCII characters = True
  pinning utf-8 on both ends round-trips regardless of platform = True
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  utf8_roundtrips=True  cp1252_silently_corrupts=True  ascii_raises=True  nonascii_present=True  explicit_encoding_portable=True
```

**Done means the corruption is demonstrated, not warned about: the same UTF-8 bytes decode to the original under utf-8, to "cafÃ© â‚¬5" under cp1252 with no error, and to a UnicodeDecodeError under ascii.**

## Boss fight

The mojibake was caught here because we compared to the original. Predict how a learner would notice this bug in the wild, with no original to compare against. It is tempting to think mojibake is obvious.

It often is not, and that is what makes the silent case dangerous. If the corrupted text scrolls past in a log, or sits in a data column the learner does not eyeball, "cafÃ©" looks like a plausible weird name rather than a decode error — and because no exception fired, nothing flagged it. The corruption can propagate into a database, a downstream file, a computed result, all without a single error. This is why the silent cp1252 case is worse than the loud ASCII crash: a crash stops you at the scene; silent mojibake ships. The defense is to pin the encoding so the bytes are never open to misinterpretation in the first place.

The mirror-image mistake is pinning the wrong encoding "to be safe" — hardcoding cp1252 or latin-1 because a file once came in that way. That just moves the platform default into your code and re-creates the mismatch for the next UTF-8 file. Pin UTF-8, which covers all of Unicode, and convert at the boundary if a genuinely legacy-encoded input arrives. And name it on writes too: a file written with the platform default is the very file that corrupts for the next reader.

```python filename=modules/teaching-and-portability/code/teach-inter-18/encoding.py:45-50 COMPLETE
def decode(raw, enc):
    """Decode bytes under a reader's encoding; return the string, or the error if it fails."""
    try:
        return raw.decode(enc), None
    except UnicodeDecodeError as e:
        return None, "UnicodeDecodeError: %s" % e.reason
```

**Pass encoding='utf-8' on every read and write so the codec travels with the code, not the machine — the silent mojibake from a platform-default mismatch is the portability bug that ships without an error.**

## External resources

The Python `open()` documentation and PEP 597 — why the encoding argument matters, the locale-dependent default, and the `EncodingWarning` added to catch omitted encodings.

Joel Spolsky, "The Absolute Minimum Every Software Developer Absolutely, Positively Must Know About Unicode and Character Sets" — the classic explainer on why "plain text" without an encoding is meaningless.

The UTF-8 Everywhere manifesto — the case for pinning UTF-8 as the single interchange encoding, the discipline this module applies.
