"""Pick the palette from the image's colors, not a fixed grid -- adaptive quantization halves the error.

Reducing an image to a small palette -- 4, 16, 256 colors -- forces a choice: which colors go in
the palette? The lazy answer is a fixed grid: space the palette evenly across the whole range,
0, 85, 170, 255 for four gray levels. But an image's colors are not spread evenly; they cluster.
A photo of a dark room at dusk lives near black and near a warm highlight, with almost nothing in
between, so a uniform palette wastes half its entries on the empty middle and quantizes the
crowded regions coarsely -- large error where all the pixels are.

An adaptive palette puts its entries where the colors actually are. Median cut is the classic
method: sort the colors, recursively split the set at its median into as many boxes as you have
palette slots, and take each box's mean as a palette entry -- so dense regions get many finely
spaced entries and empty regions get none. On this fixture the pixels cluster near 30 and near
220; a uniform 4-level palette scores a mean quantization error of 32.1 with two wasted levels
stranded at 85 and 170, while the adaptive palette places all four levels among the clusters and
cuts the error to 1.3. Same four levels, same pixels -- the palette just went where the data was.
This computes both palettes and their errors.

  --pixels     the pixel value distribution and where its colors cluster
  --palettes   the uniform grid palette vs the adaptive (median-cut) palette, and each one's error
  --check      the adaptive palette places entries at the clusters and roughly halves the error

The pixel values and palette size are the fixture; both palettes and errors are computed. Stdlib.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "pixels.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mean(xs):
    return sum(xs) / len(xs)


# ------------------------------------------------------------- the two palettes

def uniform_palette(k):
    """A fixed grid: k levels spaced evenly across 0..255, ignoring where the colors are."""
    if k == 1:
        return [128]
    return [round(i * 255 / (k - 1)) for i in range(k)]


def median_cut_palette(pixels, k):
    """Adaptive: recursively split the pixel set at its median into k boxes; each box's mean is a level."""
    boxes = [sorted(pixels)]
    while len(boxes) < k:
        # split the box with the widest spread
        box = max(boxes, key=lambda b: (b[-1] - b[0], b))
        boxes.remove(box)
        mid = len(box) // 2
        boxes.append(box[:mid])
        boxes.append(box[mid:])
        boxes.sort()
    return [round(mean(b)) for b in boxes if b]


# ------------------------------------------------------------- quantization error

def quantize_error(pixels, palette):
    """Mean absolute distance from each pixel to its nearest palette level."""
    return round(mean([min(abs(p - c) for c in palette) for p in pixels]), 4)


def nearest(value, palette):
    return min(palette, key=lambda c: abs(c - value))


# ----------------------------------------------------------------- printing

def pixels_view(data):
    pixels = data["pixels"]
    print("PIXELS — %d values; a histogram showing where the colors cluster" % len(pixels))
    print("-" * 54)
    for lo in range(0, 256, 32):
        n = sum(1 for p in pixels if lo <= p < lo + 32)
        print("  %3d-%-3d  %-20s %d" % (lo, lo + 31, "#" * n, n))
    print("-" * 54)
    print("  the mass sits near 30 and near 220; the middle is nearly empty.")


def palettes_view(data):
    pixels, k = data["pixels"], data["k"]
    uni = uniform_palette(k)
    ada = median_cut_palette(pixels, k)
    print("PALETTES — uniform grid vs adaptive (median cut), %d levels" % k)
    print("-" * 54)
    print("  uniform:  %-24s error %.2f" % (uni, quantize_error(pixels, uni)))
    print("  adaptive: %-24s error %.2f" % (ada, quantize_error(pixels, ada)))
    print("-" * 54)
    print("  the uniform palette strands a level in the empty middle; adaptive spends them all on data.")


def check(data):
    print("SELF-TEST — the adaptive palette places entries at the clusters and roughly halves the error")
    print("-" * 70)
    pixels, k = data["pixels"], data["k"]

    uni = uniform_palette(k)
    ada = median_cut_palette(pixels, k)
    e_uni, e_ada = quantize_error(pixels, uni), quantize_error(pixels, ada)

    adaptive_better = e_ada < e_uni
    print("  the adaptive palette has lower quantization error = %s (%.2f vs %.2f)" % (adaptive_better, e_ada, e_uni))

    roughly_halves = e_ada < e_uni / 1.8
    print("  it roughly halves the error or better = %s (%.2fx)" % (roughly_halves, e_uni / e_ada))

    # the uniform palette wastes a level in the empty middle; no pixel is near it
    empty_levels = [c for c in uni if min(abs(p - c) for p in pixels) > 40]
    uniform_wastes = len(empty_levels) > 0
    print("  the uniform palette strands a level far from every pixel = %s (%s)" % (uniform_wastes, empty_levels))

    # every adaptive level is near some cluster of pixels (no wasted entries)
    adaptive_uses_all = all(min(abs(p - c) for p in pixels) <= 40 for c in ada)
    print("  every adaptive level sits near real pixels (none wasted) = %s (%s)" % (adaptive_uses_all, ada))

    ok = adaptive_better and roughly_halves and uniform_wastes and adaptive_uses_all
    print("-" * 70)
    print("SELF-TEST %s  adaptive_better=%s  roughly_halves=%s  uniform_wastes=%s  adaptive_uses_all=%s"
          % ("PASS" if ok else "FAIL", adaptive_better, roughly_halves, uniform_wastes, adaptive_uses_all))
    return ok


def main():
    p = argparse.ArgumentParser(description="Pick the palette from the image's colors, not a fixed grid.")
    p.add_argument("--pixels", action="store_true")
    p.add_argument("--palettes", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("pixels=%d  k=%d  file=%s  (the pixel values are a fixture)"
          % (len(data["pixels"]), data["k"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.pixels:
        pixels_view(data)
    elif args.palettes:
        palettes_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
