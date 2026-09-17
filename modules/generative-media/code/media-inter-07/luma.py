#!/usr/bin/env python3
"""Brightness is weighted by the eye, not (R+G+B)/3 -- green is bright, blue is nearly dark.

Turning a color into a single brightness -- for grayscale, for a luminance key, for a contrast
check -- tempts the obvious formula: average the three channels, (R+G+B)/3. It is wrong,
because the eye is not equally sensitive to the three primaries. Green light looks far brighter
than blue light of the same intensity, and red sits in between; the standard Rec. 709 weights
capture this as 0.2126 R + 0.7152 G + 0.0722 B. Green carries almost three-quarters of perceived
brightness, blue barely a fourteenth.

The average gets this catastrophically wrong on saturated color. Pure red, pure green, and pure
blue all average to 255/3 = 85, so the naive formula calls them equally bright -- it cannot tell
a primary from a primary by brightness at all, and a grayscale built on it turns a vivid red /
green / blue image into three identical grays. Perceptual luma spreads them across their true
range: green 182, red 54, blue 18. This computes both on a set of color patches, shows the
average collapsing the primaries to one value while luma orders them the way the eye does, and
checks the weights sum to one.

  --patches   each color's naive average vs perceptual luma, and the ordering each gives
  --gray      a small colored image converted to grayscale both ways -- the contrast the average loses
  --check     the average collapses the primaries to one brightness; luma orders green>red>blue

The colors are the fixture; every brightness is computed from the Rec. 709 weights. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "colors.json"

# Rec. 709 luma coefficients -- the eye's sensitivity to red, green, blue
WR, WG, WB = 0.2126, 0.7152, 0.0722


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the two brightness formulas

def naive_brightness(rgb):
    """The bug: the unweighted average, (R+G+B)/3. Treats the three primaries as equal."""
    r, g, b = rgb
    return (r + g + b) / 3.0


def luma(rgb):
    """Rec. 709 perceptual luma: green counts most, blue least."""
    r, g, b = rgb
    return WR * r + WG * g + WB * b


# ------------------------------------------------------------- helpers

def order_by(patches, f):
    """Patch names sorted brightest-first by a brightness function; ties broken by name."""
    return [p["name"] for p in sorted(patches, key=lambda p: (-f(p["rgb"]), p["name"]))]


def spread(patches, f):
    """The brightness range a formula assigns across a set of patches (max - min)."""
    vals = [f(p["rgb"]) for p in patches]
    return max(vals) - min(vals)


# ----------------------------------------------------------------- printing

def patches_view(data):
    print("PATCHES — naive average vs perceptual luma (Rec. 709)")
    print("-" * 60)
    print("  name       rgb              naive   luma")
    for p in data["patches"]:
        print("  %-10s %-16s %-7.1f %.1f" % (p["name"], str(p["rgb"]), naive_brightness(p["rgb"]), luma(p["rgb"])))
    print("-" * 60)
    prim = [p for p in data["patches"] if p["name"] in ("red", "green", "blue")]
    print("  brightest-first by naive: %s" % order_by(prim, naive_brightness))
    print("  brightest-first by luma:  %s" % order_by(prim, luma))


def gray_view(data):
    img = data["image"]
    print("GRAY — a colored strip to grayscale, naive vs luma")
    print("-" * 60)
    print("  pixel rgb            naive  luma")
    for px in img:
        print("  %-16s %-6.0f %.0f" % (str(px), naive_brightness(px), luma(px)))
    naive_vals = [naive_brightness(px) for px in img]
    luma_vals = [luma(px) for px in img]
    print("-" * 60)
    print("  naive contrast (max-min): %.0f    luma contrast: %.0f"
          % (max(naive_vals) - min(naive_vals), max(luma_vals) - min(luma_vals)))
    print("  the average flattens the colored regions; luma keeps them distinct.")


def check(data):
    print("SELF-TEST — the average collapses the primaries; luma orders green > red > blue")
    print("-" * 60)
    patches = {p["name"]: p["rgb"] for p in data["patches"]}
    r, g, b = patches["red"], patches["green"], patches["blue"]

    naive_collapses = naive_brightness(r) == naive_brightness(g) == naive_brightness(b)
    print("  naive calls red, green, blue equally bright = %s (all %.1f)"
          % (naive_collapses, naive_brightness(r)))

    luma_orders = luma(g) > luma(r) > luma(b)
    print("  luma orders green > red > blue = %s (%.1f > %.1f > %.1f)"
          % (luma_orders, luma(g), luma(r), luma(b)))

    weights_sum = abs((WR + WG + WB) - 1.0) < 1e-9
    print("  the luma weights sum to 1 = %s (%.4f)" % (weights_sum, WR + WG + WB))

    prim = [p for p in data["patches"] if p["name"] in ("red", "green", "blue")]
    naive_spread = spread(prim, naive_brightness)
    luma_spread = spread(prim, luma)
    luma_keeps_contrast = naive_spread == 0 and luma_spread > 100
    print("  naive spread across primaries is 0, luma spread is wide = %s (%.1f vs %.1f)"
          % (luma_keeps_contrast, naive_spread, luma_spread))

    ok = naive_collapses and luma_orders and weights_sum and luma_keeps_contrast
    print("-" * 60)
    print("SELF-TEST %s  naive_collapses=%s  luma_orders=%s  weights_sum=%s  luma_keeps_contrast=%s"
          % ("PASS" if ok else "FAIL", naive_collapses, luma_orders, weights_sum, luma_keeps_contrast))
    return ok


def main():
    p = argparse.ArgumentParser(description="Perceptual luma vs the naive RGB average.")
    p.add_argument("--patches", action="store_true")
    p.add_argument("--gray", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("patches=%d  weights=(%.4f, %.4f, %.4f)  file=%s  (the colors are a fixture)"
          % (len(data["patches"]), WR, WG, WB, DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.patches:
        patches_view(data)
    elif args.gray:
        gray_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
