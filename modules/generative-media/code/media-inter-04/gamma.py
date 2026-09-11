#!/usr/bin/env python3
"""Blend pixels in linear light -- or averaging sRGB bytes darkens the image.

Every pixel in an ordinary image file is sRGB-encoded: the stored byte is not
proportional to the light the pixel emits, it is a perceptually-spaced code, denser in
the darks where the eye is more sensitive. That encoding is why 8 bits looks smooth.
But it means the stored numbers are NOT light, and you cannot do arithmetic on light by
doing arithmetic on the codes. Blending two pixels -- which is what resizing, alpha
compositing, and antialiasing all do -- is arithmetic on light. Average the sRGB bytes
directly and you get the wrong answer, always too dark.

The black+white case makes it undeniable. The true 50/50 blend of black (0) and white
(255) is a bright mid-gray at code 188, because half the LIGHT of white is still a lot
of perceived brightness. Averaging the bytes gives 128 -- 60 codes too dark, a visibly
muddy gray. The fix is three steps: decode each byte to linear light, average in linear
light, re-encode to sRGB. This measures the gap and the fix.

  --blend       each pair blended the wrong way (average bytes) vs the right way (linear)
  --checker     a black/white checkerboard downsampled: the muddy 128 vs the true 188
  --check       linear blend of 0 and 255 is ~188; byte-average is 128; the gap is large

Stdlib only. Deterministic.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "pixels.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))["pairs"]


# ------------------------------------------------------- the sRGB transfer functions

def srgb_to_linear(code):
    """Decode an 8-bit sRGB value to linear light in [0, 1]."""
    c = code / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(light):
    """Encode linear light in [0, 1] back to an 8-bit sRGB value."""
    v = 12.92 * light if light <= 0.0031308 else 1.055 * (light ** (1 / 2.4)) - 0.055
    return v * 255.0


# ------------------------------------------------------------- the two blends

def blend_wrong(a, b):
    """The bug: average the sRGB bytes directly, as if they were light."""
    return (a + b) / 2.0


def blend_correct(a, b):
    """Decode to linear light, average THERE, re-encode to sRGB."""
    light = (srgb_to_linear(a) + srgb_to_linear(b)) / 2.0
    return linear_to_srgb(light)


# ----------------------------------------------------------------- printing

def blend_view(pairs):
    print("BLEND — 50/50 of each pair: average the bytes (wrong) vs blend in light (right)")
    print("-" * 66)
    print("  a    b     wrong(byte avg)   correct(linear)   too dark by")
    for a, b in pairs:
        w, c = blend_wrong(a, b), blend_correct(a, b)
        print("  %-4d %-4d  %-17.1f %-17.1f %.1f" % (a, b, w, c, c - w))
    print("-" * 66)
    print("  the byte average is always darker than the true blend -- most at black+white.")


def checker_view(pairs):
    # A black/white checkerboard averaged to one pixel: what should its gray be?
    a, b = 0, 255
    print("CHECKER — shrink a black/white checkerboard to one gray pixel")
    print("-" * 66)
    print("  averaging the stored bytes:   (0+255)/2      = %.1f  (muddy, too dark)" % blend_wrong(a, b))
    print("  averaging the LIGHT:          linear then re = %.1f  (true perceived gray)" % blend_correct(a, b))
    print("-" * 66)
    print("  a resizer that skips the linear step makes checkered/thin content go dark.")


def check(pairs):
    print("SELF-TEST — the true blend of black and white is ~188, not 128")
    print("-" * 66)

    correct_bw = blend_correct(0, 255)
    is_bright = correct_bw > 180
    print("  linear blend of 0 and 255 is a bright gray = %s (%.1f)" % (is_bright, correct_bw))

    wrong_bw = blend_wrong(0, 255)
    byte_avg_dark = abs(wrong_bw - 127.5) < 1e-9
    print("  byte-average blend of 0 and 255 is 127.5 = %s (%.1f)" % (byte_avg_dark, wrong_bw))

    big_gap = correct_bw - wrong_bw > 50
    print("  the gap between them is large = %s (%.1f codes darker)" % (big_gap, correct_bw - wrong_bw))

    # The transfer functions must round-trip: decode then encode returns the input.
    roundtrip = all(abs(linear_to_srgb(srgb_to_linear(v)) - v) < 1e-6 for v in (0, 64, 128, 200, 255))
    print("  sRGB decode/encode round-trips exactly = %s" % roundtrip)

    # The wrong blend is never brighter than the correct one -- it is a systematic darkening.
    systematic = all(blend_wrong(a, b) <= blend_correct(a, b) + 1e-9 for a, b in pairs)
    print("  byte-average is never brighter than the linear blend = %s" % systematic)

    ok = is_bright and byte_avg_dark and big_gap and roundtrip and systematic
    print("-" * 66)
    print("SELF-TEST %s  is_bright=%s  byte_avg_dark=%s  big_gap=%s  roundtrip=%s  systematic=%s"
          % ("PASS" if ok else "FAIL", is_bright, byte_avg_dark, big_gap, roundtrip, systematic))
    return ok


def main():
    p = argparse.ArgumentParser(description="Gamma-correct blending: sRGB vs linear light.")
    p.add_argument("--blend", action="store_true")
    p.add_argument("--checker", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    pairs = load()
    print("pairs=%d  file=%s  (sRGB byte pairs are a fixture)" % (len(pairs), DATA.name))
    print("")

    if args.check:
        return 0 if check(pairs) else 1
    if args.blend:
        blend_view(pairs)
    elif args.checker:
        checker_view(pairs)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
