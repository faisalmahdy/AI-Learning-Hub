"""A 2D Gaussian blur factors into two 1D passes -- identical output, a fraction of the multiplies.

Blurring an image convolves it with a 2D kernel. Done directly, a 5x5 Gaussian touches 25 pixels for
every output pixel: 25 multiply-adds each, times millions of pixels, times every frame. But the 2D
Gaussian is separable -- its 5x5 kernel is exactly the outer product of a 1D kernel with itself -- and
a separable kernel can be applied as two 1D passes: blur along the rows with the 1D kernel, then blur
the result along the columns with the same 1D kernel. That costs 5 + 5 = 10 multiply-adds per pixel
instead of 25, and the saving grows with kernel size: an NxN kernel drops from N-squared taps to 2N.

The catch that makes it a real lesson: the two passes must both happen, in either order, to equal the
2D blur. Blur the rows and stop and you have smeared the image horizontally only -- a motion blur, not
a Gaussian -- and it does not match the 2D result at all. Separability is a factoring of the FULL 2D
convolution, not a shortcut that skips half of it.

This builds the 5x5 kernel as the outer product of [1,4,6,4,1] with itself, blurs the fixture image
both ways with integer arithmetic (so the comparison is exact, not merely close), and counts the
multiply-adds each method uses. The two-pass output matches the full 2D output pixel for pixel; the
one-pass (rows only) output does not.

  --kernel     the 1D kernel and the 5x5 outer-product kernel it generates
  --blur       the full-2D blur vs the separable two-pass blur, and the rows-only near-miss
  --check      two passes equal the full 2D blur exactly and cost less; one pass does not match

The image and 1D kernel are the fixture; the 2D kernel, both blurs, and the op counts are computed. Stdlib.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "image.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def outer(k):
    """The 2D kernel as the outer product of the 1D kernel with itself -- this is what 'separable' means."""
    return [[a * b for b in k] for a in k]


def clamp_get(img, r, c):
    """Zero-padded fetch: out-of-bounds pixels read as 0, applied identically by both methods."""
    if 0 <= r < len(img) and 0 <= c < len(img[0]):
        return img[r][c]
    return 0


# ------------------------------------------------------------- the two blurs (integer until the final divide)

def blur_2d(img, k):
    """Full 2D convolution with the k-by-k kernel: k*k taps per pixel. Returns (image, taps_per_pixel)."""
    k2 = outer(k)
    n = len(k)
    off = n // 2
    total_norm = sum(k) ** 2
    out = []
    for r in range(len(img)):
        row = []
        for c in range(len(img[0])):
            acc = 0
            for i in range(n):
                for j in range(n):
                    acc += k2[i][j] * clamp_get(img, r + i - off, c + j - off)
            row.append(round(acc / total_norm))
        out.append(row)
    return out, n * n


def blur_separable(img, k):
    """Two 1D passes: rows then columns. 2*k taps per pixel, identical result. Returns (image, taps)."""
    n = len(k)
    off = n // 2
    norm = sum(k)
    # pass 1: convolve each row with the 1D kernel (keep integer, divide by norm)
    tmp = []
    for r in range(len(img)):
        row = []
        for c in range(len(img[0])):
            acc = sum(k[j] * clamp_get(img, r, c + j - off) for j in range(n))
            row.append(acc / norm)
        tmp.append(row)
    # pass 2: convolve each column of the intermediate with the same 1D kernel
    out = []
    for r in range(len(img)):
        row = []
        for c in range(len(img[0])):
            acc = sum(k[i] * (tmp[r + i - off][c] if 0 <= r + i - off < len(img) else 0) for i in range(n))
            row.append(round(acc / norm))
        out.append(row)
    return out, 2 * n


def blur_rows_only(img, k):
    """The BUG: one pass along the rows only -- a horizontal smear, not a 2D Gaussian."""
    n = len(k)
    off = n // 2
    norm = sum(k)
    out = []
    for r in range(len(img)):
        row = []
        for c in range(len(img[0])):
            acc = sum(k[j] * clamp_get(img, r, c + j - off) for j in range(n))
            row.append(round(acc / norm))
        out.append(row)
    return out, n


# ----------------------------------------------------------------- printing

def show(img):
    for row in img:
        print("    " + " ".join("%3d" % v for v in row))


def kernel_view(data):
    k = data["kernel1d"]
    print("KERNEL — the 1D kernel and the 5x5 it generates by outer product")
    print("-" * 46)
    print("  1D: %s  (normalize by %d)" % (k, sum(k)))
    print("  5x5 outer product (normalize by %d):" % (sum(k) ** 2))
    for row in outer(k):
        print("    " + " ".join("%2d" % v for v in row))


def blur_view(data):
    img, k = data["image"], data["kernel1d"]
    b2, t2 = blur_2d(img, k)
    bs, ts = blur_separable(img, k)
    br, tr = blur_rows_only(img, k)
    print("BLUR — full 2D vs separable two-pass vs rows-only, with taps per pixel")
    print("-" * 52)
    print("  full 2D blur (%d taps/pixel):" % t2)
    show(b2)
    print("  separable two-pass (%d taps/pixel):" % ts)
    show(bs)
    print("  rows-only, the bug (%d taps/pixel):" % tr)
    show(br)
    print("-" * 52)
    print("  two-pass matches full 2D; rows-only is a horizontal smear that does not.")


def check(data):
    print("SELF-TEST — two 1D passes equal the full 2D blur exactly and cost less; one pass does not match")
    print("-" * 90)
    img, k = data["image"], data["kernel1d"]

    b2, taps_2d = blur_2d(img, k)
    bs, taps_sep = blur_separable(img, k)
    br, taps_row = blur_rows_only(img, k)

    separable_matches = bs == b2
    print("  separable two-pass equals the full 2D blur pixel for pixel = %s" % separable_matches)

    separable_cheaper = taps_sep < taps_2d
    print("  the separable pass costs fewer taps per pixel = %s (%d vs %d)" % (separable_cheaper, taps_sep, taps_2d))

    savings_is_ratio = taps_2d / taps_sep == len(k) / 2
    print("  the saving is the k/2 factor separability predicts = %s (%.1fx, k=%d)"
          % (savings_is_ratio, taps_2d / taps_sep, len(k)))

    one_pass_wrong = br != b2
    print("  rows-only does NOT match the 2D blur = %s (skipping a pass is not separability)" % one_pass_wrong)

    ok = separable_matches and separable_cheaper and savings_is_ratio and one_pass_wrong
    print("-" * 90)
    print("SELF-TEST %s  separable_matches=%s  separable_cheaper=%s  savings_is_ratio=%s  one_pass_wrong=%s"
          % ("PASS" if ok else "FAIL", separable_matches, separable_cheaper, savings_is_ratio, one_pass_wrong))
    return ok


def main():
    p = argparse.ArgumentParser(description="A 2D Gaussian blur factors into two 1D passes.")
    p.add_argument("--kernel", action="store_true")
    p.add_argument("--blur", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    img = data["image"]
    print("image=%dx%d  kernel=%s  file=%s  (the image and 1D kernel are a fixture)"
          % (len(img), len(img[0]), data["kernel1d"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.kernel:
        kernel_view(data)
    elif args.blur:
        blur_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
