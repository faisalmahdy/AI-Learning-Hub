"""Clamp pixel arithmetic to 0..255 (saturate), never let it wrap -- naive uint8 addition wraps an overflowing highlight to near-black, so brightening the image punches dark holes in its lightest areas.

An 8-bit channel holds a value from 0 to 255, and brightening adds an offset to every pixel. The trouble is what happens at the top of the range. A pixel already near 255 plus a positive offset exceeds what a uint8 can hold, and the default behavior of fixed-width integer math -- the arithmetic a uint8 image array uses in many libraries -- is to wrap: the value rolls over modulo 256, so 255 + 1 is 0 and 250 + 30 is 24.

For an image this is not a rounding nuisance, it is a visible catastrophe, and it strikes exactly the wrong pixels. The pixels that overflow are the brightest ones -- highlights, light sources, white surfaces -- and wrapping sends them to near-black. So the operation meant to lighten the picture turns its brightest regions into dark specks: a bright sky gains black pinholes, a white shirt grows soot. The darkest artifact appears in the lightest area, which is the signature of a wrap bug.

The intended behavior is saturating arithmetic: treat the range ends as walls, not as a loop. A sum above 255 clamps to 255, a difference below 0 clamps to 0. Now brightening can only push a pixel toward white and never past it, and darkening can only push toward black and never past it -- the result is monotone, which matches what "brighter" means. Saturation is why photo software brightens cleanly; wraparound is what you get if you forget it.

The rule: clamp pixel arithmetic to the channel's range (0..255 for 8-bit) so it saturates, because fixed-width integer math wraps an overflow around to the opposite end -- turning brightened highlights into near-black holes -- while saturating keeps brightening monotone toward white.

On this fixture brightening a row of pixels by 30 overflows the 250 and 255 values. Wrapped, they become 24 and 29 -- darker than they started, in the brightest spots; clamped, they become 255, staying bright. This computes both.

  --apply    each pixel's raw sum, its wrapped uint8 value, and its saturated (clamped) value
  --break    the pixels that overflow, showing wrap turns the brightest into the darkest
  --check    wrap sends overflowing highlights to near-black; saturating clamps them to white and stays monotone

pixels and offset are the fixture; the raw sums, wrapped values, and clamped values are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "clamp.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def wrap8(value):
    """Fixed-width uint8 arithmetic: the result rolls over modulo 256."""
    return value % 256


def clamp8(value):
    """Saturating arithmetic: values above 255 or below 0 stick at the range ends."""
    return max(0, min(255, value))


# ----------------------------------------------------------------- printing

def apply_view(data):
    pixels, off = data["pixels"], data["offset"]
    print("APPLY — brighten each pixel by %d: raw sum, wrapped uint8, saturated" % off)
    print("-" * 56)
    print("  pixel   raw    wrapped   clamped")
    for p in pixels:
        raw = p + off
        print("  %-5d   %-5d  %-7d   %d" % (p, raw, wrap8(raw), clamp8(raw)))
    print("-" * 56)
    print("  overflowing pixels wrap to near-black but clamp to white")


def break_view(data):
    pixels, off = data["pixels"], data["offset"]
    print("BREAK — the pixels that overflow 255 when brightened by %d" % off)
    print("-" * 56)
    over = [p for p in pixels if p + off > 255]
    print("  overflowing pixels: %s" % over)
    for p in over:
        raw = p + off
        print("    %d + %d = %d -> wrapped %d (darker than %d!) vs clamped %d"
              % (p, off, raw, wrap8(raw), p, clamp8(raw)))
    print("-" * 56)
    print("  the brightest inputs become the darkest outputs under wrap")


def check(data):
    print("SELF-TEST — wrap sends overflowing highlights to near-black; saturating clamps them to white and stays monotone")
    print("-" * 116)
    pixels, off = data["pixels"], data["offset"]

    wrapped = [wrap8(p + off) for p in pixels]
    clamped = [clamp8(p + off) for p in pixels]
    over = [p for p in pixels if p + off > 255]

    some_overflow = len(over) > 0
    print("  some pixels overflow 255 when brightened = %s (%s)" % (some_overflow, over))

    wrap_darkens_a_highlight = any(wrap8(p + off) < p for p in pixels)
    print("  wrap: a brightened pixel comes out DARKER than it started = %s" % wrap_darkens_a_highlight)

    wrap_not_monotone = any(wrap8(p + off) < p for p in over)
    print("  wrap: brightening is not monotone (an overflow drops) = %s" % wrap_not_monotone)

    clamp_never_darkens = all(c >= p for c, p in zip(clamped, pixels))
    print("  clamp: no brightened pixel is darker than its input = %s" % clamp_never_darkens)

    clamp_caps_at_255 = all(c <= 255 for c in clamped) and all(clamp8(p + off) == 255 for p in over)
    print("  clamp: overflowing pixels saturate to 255 (white) = %s" % clamp_caps_at_255)

    ok = (some_overflow and wrap_darkens_a_highlight and wrap_not_monotone
          and clamp_never_darkens and clamp_caps_at_255)
    print("-" * 116)
    print("SELF-TEST %s  some_overflow=%s  wrap_darkens_a_highlight=%s  wrap_not_monotone=%s  clamp_never_darkens=%s  clamp_caps_at_255=%s"
          % ("PASS" if ok else "FAIL", some_overflow, wrap_darkens_a_highlight,
             wrap_not_monotone, clamp_never_darkens, clamp_caps_at_255))
    return ok


def main():
    p = argparse.ArgumentParser(description="Saturating pixel arithmetic: clamp pixel arithmetic to the channel's range (0..255 for 8-bit) so it saturates, because fixed-width integer math wraps an overflow around to the opposite end -- turning brightened highlights into near-black holes -- while saturating keeps brightening monotone toward white.")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--break", dest="brk", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("pixels=%s  offset=%d  file=%s  (the pixels and offset are a fixture)"
          % (data["pixels"], data["offset"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.apply:
        apply_view(data)
    elif args.brk:
        break_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
