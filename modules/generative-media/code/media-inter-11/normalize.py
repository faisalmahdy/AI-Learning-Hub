"""Divide a convolution kernel by its weight-sum, or the image changes brightness -- a blur that sums to 16 makes it 16x brighter.

A convolution replaces each pixel with a weighted sum of its neighbourhood, using a small grid of
weights -- the kernel. What the kernel does to the image's overall brightness is decided entirely by
one number: the sum of its weights. A kernel whose weights sum to 1 preserves the mean brightness; one
that sums to S scales every pixel, and the mean, by S; one that sums to 0 produces a zero-mean result.
So a blur kernel like [[1,2,1],[2,4,2],[1,2,1]], whose weights sum to 16, must be divided by 16 before
you apply it -- normalized -- or the image comes out sixteen times brighter and clips to white.

This is the most common convolution bug: writing the kernel weights and forgetting to divide by their
sum. It does not show up as an error, it shows up as a washed-out or darkened image, and it is invisible
if you only ever look at edge or sharpen kernels, which happen to sum to 1 already. The sharpen
[[0,-1,0],[-1,5,-1],[0,-1,0]] sums to 1 and needs no normalization; the edge detector sums to 0 and is
supposed to zero the mean; only the blur needs the divide -- and it is the one people forget.

On this fixture (a 4x4 image, mean brightness 116.875) the blur applied raw multiplies the mean to
1870.0 -- 16x too bright. Divided by its sum of 16, the mean stays 116.875. The sharpen (sum 1) preserves
it untouched, and the edge kernel (sum 0) drives the mean to exactly 0.0. Convolution uses wrap-around
edges so the brightness law mean_out = kernel_sum x mean_in is exact. This computes all of it.

  --kernels    the three kernels and their weight-sums (16, 1, 0)
  --brightness the mean brightness after each kernel, raw vs divided by its sum
  --check      the raw blur scales brightness by its sum; dividing by the sum preserves it

The image and kernels are the fixture; every sum, convolution, and mean is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "image.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def kernel_sum(k):
    return sum(sum(row) for row in k)


def mean(img):
    flat = [v for row in img for v in row]
    return round(sum(flat) / len(flat), 4)


# ------------------------------------------------------------- convolution (wrap-around edges)

def convolve(img, k, divisor):
    """Convolve with wrap-around edges, dividing the result by `divisor`. Wrap makes the brightness law exact."""
    h, w = len(img), len(img[0])
    out = []
    for r in range(h):
        row = []
        for c in range(w):
            acc = 0
            for i in range(3):
                for j in range(3):
                    rr, cc = (r + i - 1) % h, (c + j - 1) % w  # wrap around the edges
                    acc += k[i][j] * img[rr][cc]
            row.append(acc / divisor)
        out.append(row)
    return out


# ----------------------------------------------------------------- printing

def kernels_view(data):
    print("KERNELS — the 3x3 weights and their sums")
    print("-" * 44)
    for name, k in data["kernels"].items():
        print("  %-8s sum = %2d   %s" % (name, kernel_sum(k), k))
    print("-" * 44)
    print("  the weight-sum sets the brightness: 1 preserves, S scales, 0 zeroes.")


def brightness_view(data):
    img = data["image"]
    m0 = mean(img)
    print("BRIGHTNESS — mean after each kernel, applied raw vs divided by its sum (input mean %.3f)" % m0)
    print("-" * 72)
    for name, k in data["kernels"].items():
        s = kernel_sum(k)
        raw = mean(convolve(img, k, 1))
        norm = mean(convolve(img, k, s)) if s != 0 else None
        norm_str = "%.3f" % norm if norm is not None else "(sum 0 -- cannot divide)"
        print("  %-8s sum %2d   raw mean %9.3f   divided-by-sum mean %s" % (name, s, raw, norm_str))
    print("-" * 72)
    print("  raw blur is 16x too bright; divided by 16 it matches the input; sharpen already preserves.")


def check(data):
    print("SELF-TEST — the raw blur scales brightness by its sum; dividing by the sum preserves it")
    print("-" * 84)
    img = data["image"]
    m0 = mean(img)
    ks = data["kernels"]

    blur_s = kernel_sum(ks["blur"])
    raw_blur = mean(convolve(img, ks["blur"], 1))
    raw_scales_by_sum = abs(raw_blur - blur_s * m0) < 1e-6
    print("  the raw blur scales the mean by its weight-sum = %s (%.3f = %d x %.3f)"
          % (raw_scales_by_sum, raw_blur, blur_s, m0))

    norm_blur = mean(convolve(img, ks["blur"], blur_s))
    dividing_preserves = abs(norm_blur - m0) < 1e-6
    print("  dividing the blur by its sum preserves the mean = %s (%.3f = %.3f)" % (dividing_preserves, norm_blur, m0))

    sharpen_s = kernel_sum(ks["sharpen"])
    sharpen_preserves = sharpen_s == 1 and abs(mean(convolve(img, ks["sharpen"], 1)) - m0) < 1e-6
    print("  the sharpen sums to 1 and preserves the mean untouched = %s (sum %d)" % (sharpen_preserves, sharpen_s))

    edge_s = kernel_sum(ks["edge"])
    edge_zeroes = edge_s == 0 and abs(mean(convolve(img, ks["edge"], 1))) < 1e-6
    print("  the edge kernel sums to 0 and zeroes the mean = %s (sum %d, mean %.3f)"
          % (edge_zeroes, edge_s, mean(convolve(img, ks["edge"], 1))))

    ok = raw_scales_by_sum and dividing_preserves and sharpen_preserves and edge_zeroes
    print("-" * 84)
    print("SELF-TEST %s  raw_scales_by_sum=%s  dividing_preserves=%s  sharpen_preserves=%s  edge_zeroes=%s"
          % ("PASS" if ok else "FAIL", raw_scales_by_sum, dividing_preserves, sharpen_preserves, edge_zeroes))
    return ok


def main():
    p = argparse.ArgumentParser(description="Divide a convolution kernel by its weight-sum to preserve brightness.")
    p.add_argument("--kernels", action="store_true")
    p.add_argument("--brightness", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("image=%dx%d  kernels=%s  file=%s  (the image and kernels are a fixture)"
          % (len(data["image"]), len(data["image"][0]), list(data["kernels"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.kernels:
        kernels_view(data)
    elif args.brightness:
        brightness_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
