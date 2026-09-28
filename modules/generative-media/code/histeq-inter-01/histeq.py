"""Equalize the histogram to gain contrast, or a linear stretch uses the full range and still looks flat.

A low-contrast image has its pixel values bunched into a narrow band -- a foggy photo where everything is
some shade of mid-gray. The obvious fix is to stretch: find the darkest and lightest values and linearly
map them to 0 and full-white, so the image spans the whole range. It does span the whole range afterward --
and it still looks flat, because a linear stretch is affine. It moves the endpoints apart but preserves the
shape of the distribution: the values that were bunched together are still bunched together, just at a
larger scale, so the crowded tones the eye needs to tell apart are still crowded. Using the full range is
not the same as using it well.

Histogram equalization uses the range well by allocating output levels in proportion to how many pixels
sit there. It maps each value through the cumulative histogram (the CDF): a tonal region packed with pixels
gets a steep stretch of the CDF and so a wide slice of the output range, while a sparse region gets a
shallow slice. The dense, important tones are spread apart -- exactly where contrast was needed -- and the
output histogram comes out roughly flat, which is the maximum-contrast, maximum-entropy use of the levels.
Both methods hit 0 and full-white; only equalization redistributes the tones between them.

On this fixture 8 pixels are bunched around one dominant gray level. The linear stretch spans the full 0-7
range but leaves the four dominant pixels crowded near the bottom (mapped to 2). Equalization spans the
same range but spreads those four to the middle (mapped to 5), separating them from the darks -- a larger
contrast (standard deviation 2.472 vs 2.236) and a wider output gap around the busy tone. This computes both.

  --map        the value-to-value mapping each method applies
  --output     the output pixels and histogram of each method, with the contrast and the dense-region gap
  --check      the stretch keeps the dense tones bunched low; equalization spreads them for more contrast

The pixels and level count are the fixture; every mapping is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "image.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def histogram(pixels, levels):
    h = [0] * levels
    for p in pixels:
        h[p] += 1
    return h


def cdf(hist):
    out, run = [], 0
    for c in hist:
        run += c
        out.append(run)
    return out


def linear_stretch(pixels, levels):
    """Affine map [min,max] -> [0, levels-1] -- spans the range but keeps the distribution's shape."""
    lo, hi = min(pixels), max(pixels)
    return {v: round((v - lo) / (hi - lo) * (levels - 1)) for v in set(pixels)}


def equalize(pixels, levels):
    """Map each value through the normalized CDF -- allocates output range by pixel density."""
    c = cdf(histogram(pixels, levels))
    n = len(pixels)
    cmin = min(x for x in c if x > 0)
    return {v: round((c[v] - cmin) / (n - cmin) * (levels - 1)) for v in set(pixels)}


def apply(pixels, mapping):
    return [mapping[p] for p in pixels]


def stdev(pixels):
    m = sum(pixels) / len(pixels)
    return round(math.sqrt(sum((p - m) ** 2 for p in pixels) / len(pixels)), 3)


# ----------------------------------------------------------------- printing

def map_view(data):
    pixels, L = data["pixels"], data["levels"]
    st, eq = linear_stretch(pixels, L), equalize(pixels, L)
    print("MAP — how each method maps the input values (levels 0..%d)" % (L - 1))
    print("-" * 50)
    print("  value   count   stretch   equalize")
    for v in sorted(set(pixels)):
        print("  %-5d   %-5d   %-7d   %d" % (v, pixels.count(v), st[v], eq[v]))
    print("-" * 50)
    print("  the dominant value goes low under stretch, mid under equalize.")


def dense_gap(pixels, mapping):
    """Output gap between the dominant tone and the next-lower value -- contrast around the busy region."""
    dom = max(set(pixels), key=pixels.count)
    below = max((v for v in set(pixels) if v < dom), default=dom)
    return mapping[dom] - mapping[below]


def output_view(data):
    pixels, L = data["pixels"], data["levels"]
    stmap, eqmap = linear_stretch(pixels, L), equalize(pixels, L)
    st, eq = apply(pixels, stmap), apply(pixels, eqmap)
    print("OUTPUT — pixels, histogram, and contrast per method")
    print("-" * 58)
    print("  input:     %s   hist %s   std %.3f" % (pixels, histogram(pixels, L), stdev(pixels)))
    print("  stretch:   %s   hist %s   std %.3f" % (st, histogram(st, L), stdev(st)))
    print("  equalize:  %s   hist %s   std %.3f" % (eq, histogram(eq, L), stdev(eq)))
    print("-" * 58)
    print("  gap around the dominant tone: stretch %d, equalize %d (more contrast where the pixels are)."
          % (dense_gap(pixels, stmap), dense_gap(pixels, eqmap)))


def check(data):
    print("SELF-TEST — the linear stretch keeps the dense tones bunched low; equalization spreads them for contrast")
    print("-" * 104)
    pixels, L = data["pixels"], data["levels"]
    stmap, eqmap = linear_stretch(pixels, L), equalize(pixels, L)
    st, eq = apply(pixels, stmap), apply(pixels, eqmap)

    both_use_full_range = min(st) == 0 and max(st) == L - 1 and min(eq) == 0 and max(eq) == L - 1
    print("  both methods span the full 0..%d range = %s" % (L - 1, both_use_full_range))

    equalize_more_contrast = stdev(eq) > stdev(st)
    print("  equalization spreads the pixels more (higher std) = %s (%.3f > %.3f)"
          % (equalize_more_contrast, stdev(eq), stdev(st)))

    both_beat_input = stdev(st) > stdev(pixels) and stdev(eq) > stdev(pixels)
    print("  both raise contrast above the flat input = %s (input %.3f)" % (both_beat_input, stdev(pixels)))

    dominant = max(set(pixels), key=pixels.count)
    equalize_lifts_dominant = eqmap[dominant] > stmap[dominant]
    print("  the stretch leaves the dominant tone crowded low, equalize lifts it = %s (%d vs %d)"
          % (equalize_lifts_dominant, stmap[dominant], eqmap[dominant]))

    equalize_widens_dense_gap = dense_gap(pixels, eqmap) > dense_gap(pixels, stmap)
    print("  equalize gives the densest region the wider output gap = %s (%d vs %d)"
          % (equalize_widens_dense_gap, dense_gap(pixels, eqmap), dense_gap(pixels, stmap)))

    ok = both_use_full_range and equalize_more_contrast and both_beat_input and equalize_lifts_dominant and equalize_widens_dense_gap
    print("-" * 104)
    print("SELF-TEST %s  both_use_full_range=%s  equalize_more_contrast=%s  both_beat_input=%s  equalize_lifts_dominant=%s  equalize_widens_dense_gap=%s"
          % ("PASS" if ok else "FAIL", both_use_full_range, equalize_more_contrast, both_beat_input, equalize_lifts_dominant, equalize_widens_dense_gap))
    return ok


def main():
    p = argparse.ArgumentParser(description="Equalize the histogram to gain contrast a linear stretch cannot.")
    p.add_argument("--map", action="store_true")
    p.add_argument("--output", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("pixels=%d  levels=%d  file=%s  (the image and level count are a fixture)"
          % (len(data["pixels"]), data["levels"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.map:
        map_view(data)
    elif args.output:
        output_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
