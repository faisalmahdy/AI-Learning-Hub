#!/usr/bin/env python3
"""Premultiply alpha before blending -- or a transparent pixel's color bleeds a dark fringe.

An RGBA pixel stores a color and an alpha (opacity). A fully transparent pixel's color is
undefined -- you cannot see it -- so tools store it as black (zero). That stored black is
harmless as long as you never do arithmetic on the color of a transparent pixel. Blending
does exactly that arithmetic: averaging two pixels to downsample an edge mixes the visible
color of the opaque pixel with the invisible black of the transparent one, and the result
is a color darker than it should be -- a dark fringe around every soft edge.

The fix is premultiplied alpha: multiply each pixel's color by its own alpha BEFORE
blending, so a transparent pixel contributes zero color weight (its black cannot bleed),
average, then un-premultiply by dividing the blended color by the blended alpha. The edge
comes out full red instead of dark red. This measures both on one edge pixel.

  --blend       the averaged edge pixel: straight (non-premultiplied) vs premultiplied
  --check       premultiplied recovers full red; straight darkens it; both agree on alpha

Stdlib only. Deterministic. Colors and alpha in [0,1].
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "rgba.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))["row"]


# ------------------------------------------------------------- alpha helpers

def premultiply(px):
    """Scale color by alpha: a transparent pixel's color becomes zero-weighted."""
    r, g, b, a = px
    return [r * a, g * a, b * a, a]


def unpremultiply(px):
    """Divide color back out by alpha; a zero-alpha pixel stays transparent (color undefined)."""
    r, g, b, a = px
    if a == 0:
        return [0.0, 0.0, 0.0, 0.0]
    return [r / a, g / a, b / a, a]


def average(pixels):
    """Channel-wise mean of a list of [r,g,b,a] pixels."""
    n = len(pixels)
    return [sum(px[c] for px in pixels) / n for c in range(4)]


# ------------------------------------------------------------- the two blends

def blend_straight(pixels):
    """The bug: average the stored (non-premultiplied) RGBA directly."""
    return average(pixels)


def blend_premultiplied(pixels):
    """Premultiply, average in premultiplied space, then un-premultiply."""
    pm = [premultiply(px) for px in pixels]
    return unpremultiply(average(pm))


# ----------------------------------------------------------------- printing

def fmt(px):
    return "[%.2f, %.2f, %.2f  a=%.2f]" % (px[0], px[1], px[2], px[3])


def blend_view(row):
    s = blend_straight(row)
    p = blend_premultiplied(row)
    print("BLEND — average an opaque-red pixel with a transparent one (the edge)")
    print("-" * 66)
    print("  inputs:        %s  +  %s" % (fmt(row[0]), fmt(row[1])))
    print("  straight avg:  %s   <- red channel darkened to %.2f" % (fmt(s), s[0]))
    print("  premultiplied: %s   <- red channel stays %.2f" % (fmt(p), p[0]))
    print("-" * 66)
    print("  straight blended the transparent pixel's black into the visible color.")


def check(row):
    print("SELF-TEST — premultiplied keeps the edge full red; straight darkens it")
    print("-" * 66)

    s = blend_straight(row)
    p = blend_premultiplied(row)
    opaque_red = row[0][0]  # 1.0

    premul_correct = abs(p[0] - opaque_red) < 1e-9
    print("  premultiplied edge red == opaque source red = %s (%.2f == %.2f)" % (premul_correct, p[0], opaque_red))

    straight_darkens = s[0] < opaque_red - 1e-9
    print("  straight edge red is darker than the source = %s (%.2f < %.2f)" % (straight_darkens, s[0], opaque_red))

    same_alpha = abs(s[3] - p[3]) < 1e-9
    print("  both methods agree on the blended alpha = %s (%.2f)" % (same_alpha, p[3]))

    fringe = p[0] - s[0]
    real_fringe = fringe > 0.25
    print("  the dark-fringe error is substantial = %s (red off by %.2f)" % (real_fringe, fringe))

    det = blend_premultiplied(row) == blend_premultiplied(row)
    ok = premul_correct and straight_darkens and same_alpha and real_fringe and det
    print("-" * 66)
    print("SELF-TEST %s  premul_correct=%s  straight_darkens=%s  same_alpha=%s  real_fringe=%s"
          % ("PASS" if ok else "FAIL", premul_correct, straight_darkens, same_alpha, real_fringe))
    return ok


def main():
    p = argparse.ArgumentParser(description="Premultiplied alpha and the dark-fringe bug.")
    p.add_argument("--blend", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    row = load()
    print("pixels=%d  file=%s  (RGBA values are a fixture)" % (len(row), DATA.name))
    print("")

    if args.check:
        return 0 if check(row) else 1
    if args.blend:
        blend_view(row)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
