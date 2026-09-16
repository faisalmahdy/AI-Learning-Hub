"""Premultiply color by alpha before averaging -- a transparent pixel's invisible color leaks into edges otherwise.

An RGBA pixel stores a color and an alpha (coverage/opacity). The color of a fully transparent pixel -- alpha 0 -- is
invisible, so it is also undefined: nothing on screen depends on it, and authoring tools leave whatever bytes happened to
be there, often a default or a leftover from a previous edit. That is harmless as long as the pixel stays transparent.
But the moment you AVERAGE pixels -- and downscaling, blurring, mipmapping, and antialiasing all average pixels -- the
question of what a transparent pixel's color is suddenly matters, because a naive average of the RGB channels weights
that invisible color equally with the visible ones. A red opaque pixel averaged with a transparent pixel that happens to
carry blue comes out purple, and when that purple is later composited onto a page it shows as a colored fringe around
every edge where opaque meets transparent. The bug is famous: dark or discolored halos around cut-out images, and it
comes entirely from averaging color that should have carried zero weight.

The fix is premultiplied alpha. Before averaging, multiply each pixel's color by its alpha, so a transparent pixel's
color becomes zero and contributes nothing no matter what garbage it stored. Average the premultiplied colors and the
alphas, and you have the correct premultiplied result directly; to get a straight color back (un-premultiplied), divide
by the averaged alpha. Equivalently, keep everything premultiplied through the whole pipeline -- compositing is even
simpler in premultiplied form (out = fg + bg*(1-alpha)). The rule mirrors the gamma rule: an averaging operation is only
correct on the right representation, and for alpha that representation is premultiplied, because it weights each pixel's
color by how much of it is actually there.

On this fixture an opaque red pixel (255,0,0, alpha 1) is averaged with a transparent blue pixel (0,0,255, alpha 0).
Averaging the straight channels gives (127.5, 0, 127.5) -- purple -- with alpha 0.5: the invisible blue leaked in.
Premultiplying first zeroes the transparent pixel's color, so the average is (127.5, 0, 0) at alpha 0.5, which
un-premultiplies to pure red (255,0,0) at alpha 0.5 -- the transparent pixel contributed nothing. Composited over white,
the straight result is a purplish (191,128,191) while the premultiplied result is a clean pink (255,128,128). This
computes both.

  --blend      average the two pixels straight vs premultiplied -- straight leaks blue (purple), premultiplied stays red
  --composite  composite each averaged result over the white background -- the straight one carries a purple fringe
  --check      straight averaging leaks the transparent pixel's blue; premultiplying zeroes it and preserves the true red

The pixel colors, alphas, and background are the fixture; every average and composite is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "premult.json"

CH = 3


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def avg(a, b):
    """Per-channel average of two colors."""
    return [(a[i] + b[i]) / 2 for i in range(CH)]


def blend_straight(p1, p2):
    """WRONG: average the RGB channels and the alpha separately, ignoring coverage."""
    rgb = avg(p1["rgb"], p2["rgb"])
    alpha = (p1["alpha"] + p2["alpha"]) / 2
    return rgb, alpha


def premultiply(pixel):
    """Multiply color by alpha, so a transparent pixel's color becomes zero."""
    return [c * pixel["alpha"] for c in pixel["rgb"]]


def blend_premultiplied(p1, p2):
    """RIGHT: premultiply, average, then un-premultiply (divide by the averaged alpha)."""
    pm = avg(premultiply(p1), premultiply(p2))
    alpha = (p1["alpha"] + p2["alpha"]) / 2
    rgb = [c / alpha for c in pm] if alpha else [0.0] * CH
    return rgb, alpha


def composite_over(rgb, alpha, bg):
    """Composite a straight (rgb, alpha) color over an opaque background."""
    return [round(rgb[i] * alpha + bg[i] * (1 - alpha), 1) for i in range(CH)]


# ----------------------------------------------------------------- printing

def blend_view(data):
    p1, p2 = data["pixels"]
    s_rgb, s_a = blend_straight(p1, p2)
    m_rgb, m_a = blend_premultiplied(p1, p2)
    print("BLEND — average an opaque red with a transparent blue pixel")
    print("-" * 62)
    print("  input  %-16s rgb=%s alpha=%.1f" % (p1["name"], p1["rgb"], p1["alpha"]))
    print("  input  %-16s rgb=%s alpha=%.1f" % (p2["name"], p2["rgb"], p2["alpha"]))
    print("-" * 62)
    print("  straight avg       rgb=%s alpha=%.1f  <- purple: blue leaked from the invisible pixel" % ([round(x, 1) for x in s_rgb], s_a))
    print("  premultiplied avg  rgb=%s alpha=%.1f  <- pure red: transparent pixel contributed nothing" % ([round(x, 1) for x in m_rgb], m_a))


def composite_view(data):
    p1, p2 = data["pixels"]
    bg = data["background"]
    s_rgb, s_a = blend_straight(p1, p2)
    m_rgb, m_a = blend_premultiplied(p1, p2)
    print("COMPOSITE — put each averaged result over the white background %s" % bg)
    print("-" * 60)
    print("  straight result over white       = %s  (purplish fringe)" % composite_over(s_rgb, s_a, bg))
    print("  premultiplied result over white  = %s  (clean pink)" % composite_over(m_rgb, m_a, bg))
    print("-" * 60)
    print("  the straight composite is tinted toward blue/purple by a pixel that was fully transparent.")


def check(data):
    print("SELF-TEST — straight averaging leaks the transparent pixel's blue; premultiplying zeroes it and preserves the true red")
    print("-" * 116)
    p1, p2 = data["pixels"]
    s_rgb, s_a = blend_straight(p1, p2)
    m_rgb, m_a = blend_premultiplied(p1, p2)

    straight_leaks_blue = s_rgb[2] > 0
    print("  straight average leaks blue from the transparent pixel = %s (blue=%.1f)" % (straight_leaks_blue, s_rgb[2]))

    premult_no_blue = m_rgb[2] == 0
    print("  premultiplied average has no blue leak = %s (blue=%.1f)" % (premult_no_blue, m_rgb[2]))

    premult_is_pure_red = m_rgb[0] == 255 and m_rgb[1] == 0 and m_rgb[2] == 0
    print("  premultiplied result is pure red = %s (%s)" % (premult_is_pure_red, [round(x, 1) for x in m_rgb]))

    same_alpha = s_a == m_a == 0.5
    print("  both methods give the same alpha = %s (%.1f)" % (same_alpha, m_a))

    transparent_contributes_zero = premultiply(p2) == [0.0, 0.0, 0.0]
    print("  the transparent pixel premultiplies to zero color = %s (%s)" % (transparent_contributes_zero, premultiply(p2)))

    ok = straight_leaks_blue and premult_no_blue and premult_is_pure_red and same_alpha and transparent_contributes_zero
    print("-" * 116)
    print("SELF-TEST %s  straight_leaks_blue=%s  premult_no_blue=%s  premult_is_pure_red=%s  same_alpha=%s  transparent_contributes_zero=%s"
          % ("PASS" if ok else "FAIL", straight_leaks_blue, premult_no_blue, premult_is_pure_red, same_alpha, transparent_contributes_zero))
    return ok


def main():
    p = argparse.ArgumentParser(description="Premultiplied alpha: averaging RGBA pixels (downscale, blur, mipmap, antialias) on straight color lets a transparent pixel's invisible color leak into edges as a fringe; premultiply color by alpha before averaging so a transparent pixel contributes zero color, then un-premultiply.")
    p.add_argument("--blend", action="store_true")
    p.add_argument("--composite", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("pixels=%s  background=%s  file=%s  (the colors and alphas are a fixture)"
          % ([(px["name"], px["rgb"], px["alpha"]) for px in data["pixels"]], data["background"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.blend:
        blend_view(data)
    elif args.composite:
        composite_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
