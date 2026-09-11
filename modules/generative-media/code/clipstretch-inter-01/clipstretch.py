"""Clip the extremes before you stretch contrast -- one bright outlier makes a min-max stretch do almost nothing.

Contrast stretching brightens a dull image by remapping its values to fill the full available range: find the darkest and
lightest pixels and rescale everything so the darkest becomes 0 and the lightest becomes 255. When the image genuinely uses
a narrow band -- say everything sits between 100 and 140 -- this is exactly right: the band expands to fill 0..255 and the
faint differences become visible. The method is fragile in one specific way: it defines the range by the single MINIMUM and
single MAXIMUM pixel, so a lone outlier destroys it. One specular highlight (a bright glint off metal or water), one hot or
dead pixel, one dust speck, sets the max to 255 or the min to 0, and now the stretch maps that outlier to the endpoint and
leaves the real content -- which occupied 100..140 -- almost exactly where it was, compressed into a thin slice of the
range. The stretch technically ran; it just spent its entire dynamic range on two stray pixels and gave the actual image
nothing.

Percentile clipping fixes this by defining the range ROBUSTLY. Instead of the absolute min and max, use a low and high
PERCENTILE -- clip, say, the darkest 10% and lightest 10% of pixels -- and stretch that clipped range to fill 0..255,
saturating anything beyond it (the outliers) to pure black or white. Because a couple of outlier pixels are a tiny fraction
of the image, they fall outside the 10th-to-90th-percentile band, so they no longer define the range; the robust range is
the band the real content actually occupies, and stretching THAT gives the content full contrast. The cost is that the
handful of clipped pixels lose their exact value (they clamp to 0 or 255), which is almost always a good trade -- a blown-out
highlight and a black speck carry no detail worth preserving, and sacrificing them to reveal the whole image is what you
want. This is the same robust-statistics idea as trimming outliers before taking a mean: the extremes are not
representative, so do not let them set the scale.

The rule: stretch contrast to a percentile-clipped range (e.g. the 10th to 90th percentile), not the absolute min and max,
because min-max stretching lets a single outlier pixel -- a specular highlight, a dead pixel -- define the range and leave
the real content compressed into a sliver, while clipping the extremes first stretches the band the content actually
occupies to full contrast.

On this fixture the content sits in 100..140 but the row also has a 0 (dead pixel) and a 255 (specular highlight). Naive
min-max stretching maps 0->0 and 255->255 and leaves the content in a 40-wide band. Clipping the 10% extremes gives the
robust range 100..140, which stretches to the full 0..255. This computes both.

  --stretch    the row stretched by naive min-max vs percentile-clipped, and the range each method used
  --contrast   the spread of the real content (the 100-140 band) after each stretch -- 40 (naive) vs 255 (clipped)
  --check      the outliers make min-max stretch leave the content flat; percentile clipping gives it full contrast

row and clip_percentile are the fixture; every stretched value, range, and content spread is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "clipstretch.json"

CONTENT_LO, CONTENT_HI = 100, 140  # the band the real (non-outlier) content occupies


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def percentile(values, p):
    """Nearest-rank percentile: sort, take the value at rank ceil(p/100 * n)."""
    s = sorted(values)
    rank = max(1, math.ceil(p / 100 * len(s)))
    return s[rank - 1]


def stretch(value, lo, hi):
    """Map [lo, hi] to [0, 255], clamping anything outside to the endpoints."""
    if hi == lo:
        return 0.0
    scaled = (value - lo) / (hi - lo) * 255
    return max(0.0, min(255.0, scaled))


def naive_range(row):
    return min(row), max(row)


def clipped_range(row, clip_percentile):
    return percentile(row, clip_percentile), percentile(row, 100 - clip_percentile)


def content_spread(row, lo, hi):
    """The spread (max - min) of the real-content pixels after stretching -- how much contrast the content got."""
    stretched = [stretch(v, lo, hi) for v in row if CONTENT_LO <= v <= CONTENT_HI]
    return max(stretched) - min(stretched)


# ----------------------------------------------------------------- printing

def stretch_view(data):
    row, cp = data["row"], data["clip_percentile"]
    nlo, nhi = naive_range(row)
    clo, chi = clipped_range(row, cp)
    print("STRETCH — the row remapped by naive min-max vs %d%%-clipped percentile" % cp)
    print("-" * 74)
    print("  input           = %s" % row)
    print("  naive range     = [%d, %d]  (the outliers!)" % (nlo, nhi))
    print("  naive stretched = %s" % [round(stretch(v, nlo, nhi)) for v in row])
    print("  clipped range   = [%d, %d]  (the robust content band)" % (clo, chi))
    print("  clip  stretched = %s" % [round(stretch(v, clo, chi)) for v in row])
    print("-" * 74)
    print("  naive spent its range on 0 and 255; clipping used the 100-140 band the content occupies.")


def contrast_view(data):
    row, cp = data["row"], data["clip_percentile"]
    nlo, nhi = naive_range(row)
    clo, chi = clipped_range(row, cp)
    print("CONTRAST — spread of the real content (values in [%d,%d]) after each stretch" % (CONTENT_LO, CONTENT_HI))
    print("-" * 64)
    ns = content_spread(row, nlo, nhi)
    cs = content_spread(row, clo, chi)
    print("  naive min-max:   content spans %.0f of 255  (%.0f%% of the range)" % (ns, ns / 255 * 100))
    print("  percentile clip: content spans %.0f of 255  (%.0f%% of the range)" % (cs, cs / 255 * 100))
    print("-" * 64)
    print("  clipping gives the content %.1fx the contrast of the naive stretch." % (cs / ns))


def check(data):
    print("SELF-TEST — the outliers make min-max stretch leave the content flat; percentile clipping gives it full contrast")
    print("-" * 116)
    row, cp = data["row"], data["clip_percentile"]
    nlo, nhi = naive_range(row)
    clo, chi = clipped_range(row, cp)
    ns = content_spread(row, nlo, nhi)
    cs = content_spread(row, clo, chi)

    outliers_present = min(row) < CONTENT_LO and max(row) > CONTENT_HI
    print("  the row has outliers outside the content band = %s (min %d, max %d vs band %d-%d)"
          % (outliers_present, min(row), max(row), CONTENT_LO, CONTENT_HI))

    naive_range_is_outliers = (nlo, nhi) == (min(row), max(row)) and (nlo < CONTENT_LO and nhi > CONTENT_HI)
    print("  naive range is set by the outliers = %s ([%d, %d])" % (naive_range_is_outliers, nlo, nhi))

    naive_low_contrast = ns < 100
    print("  naive stretch leaves the content low-contrast = %s (spread %.0f of 255)" % (naive_low_contrast, ns))

    clip_full_contrast = cs == 255
    print("  percentile clip gives the content full contrast = %s (spread %.0f of 255)" % (clip_full_contrast, cs))

    clip_beats_naive = cs > ns
    print("  clipping beats naive on content contrast = %s (%.0f vs %.0f)" % (clip_beats_naive, cs, ns))

    ok = outliers_present and naive_range_is_outliers and naive_low_contrast and clip_full_contrast and clip_beats_naive
    print("-" * 116)
    print("SELF-TEST %s  outliers_present=%s  naive_range_is_outliers=%s  naive_low_contrast=%s  clip_full_contrast=%s  clip_beats_naive=%s"
          % ("PASS" if ok else "FAIL", outliers_present, naive_range_is_outliers, naive_low_contrast, clip_full_contrast, clip_beats_naive))
    return ok


def main():
    p = argparse.ArgumentParser(description="Percentile-clipped contrast stretch: stretch contrast to a percentile-clipped range (e.g. the 10th to 90th percentile), not the absolute min and max, because min-max stretching lets a single outlier pixel (a specular highlight, a dead pixel) define the range and leave the real content compressed into a sliver, while clipping the extremes first stretches the band the content actually occupies to full contrast.")
    p.add_argument("--stretch", action="store_true")
    p.add_argument("--contrast", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("row=%s  clip_percentile=%d  file=%s  (the row and clip percentile are a fixture)"
          % (data["row"], data["clip_percentile"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.stretch:
        stretch_view(data)
    elif args.contrast:
        contrast_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
