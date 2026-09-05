"""Choose a border policy for the convolution, or zero-padding darkens every edge of the image.

Any convolution -- a blur, a sharpen, an edge detector -- centers a kernel on each pixel and combines it
with its neighbors. At the image border the kernel hangs off the edge, over pixels that do not exist, and
the code has to decide what value those out-of-bounds pixels have. The lazy default is zero: treat
everything past the edge as black. That is wrong for a blur, because a border pixel now averages real
pixels with black, so it comes out darker than it should. On a bright, flat image every edge pixel is
dragged toward zero -- a dark rim, a vignette, that was never in the picture. The kernel is correct; the
made-up border pixels corrupted it.

The fix is a border policy that invents plausible out-of-bounds values instead of black. Edge-extend
(clamp) repeats the nearest real pixel, so a border pixel is averaged with copies of itself and stays put.
Reflect mirrors the image across the edge, which is smooth across the boundary and also avoids the
darkening. Both keep a flat region flat at the edge; only zero-padding introduces the dark rim, because
only zero-padding pretends the world outside the image is black.

On this fixture a flat row of value 100 is blurred with a 3-wide box. Zero-padding drops the two edge
pixels to 67 -- a visible darkening -- while the interior stays 100. Edge-extend and reflect keep every
pixel at 100, edges included. This computes all three.

  --blur       the blurred row under each border policy
  --error      the per-pixel error against the true flat value, per policy
  --check      zero-padding darkens the border; edge-extend and reflect leave it flat

The row and kernel are the fixture; every output is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "row.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def at_zero(row, i):
    """Out-of-bounds -> 0 (black). Averaging with black darkens the border."""
    return row[i] if 0 <= i < len(row) else 0


def at_clamp(row, i):
    """Out-of-bounds -> nearest edge pixel (edge-extend)."""
    return row[min(max(i, 0), len(row) - 1)]


def at_reflect(row, i):
    """Out-of-bounds -> mirror across the edge."""
    n = len(row)
    if i < 0:
        i = -i
    elif i >= n:
        i = 2 * (n - 1) - i
    return row[min(max(i, 0), n - 1)]


BORDERS = {"zero": at_zero, "clamp": at_clamp, "reflect": at_reflect}


def box_blur(row, half, border):
    at = BORDERS[border]
    out = []
    for i in range(len(row)):
        window = [at(row, j) for j in range(i - half, i + half + 1)]
        out.append(round(sum(window) / len(window), 1))
    return out


def abs_error(a, b):
    return [round(abs(x - y), 1) for x, y in zip(a, b)]


# ----------------------------------------------------------------- printing

def blur_view(data):
    row, half = data["row"], data["kernel"] // 2
    print("BLUR — a flat row of %d blurred (width %d) under each border policy" % (row[0], data["kernel"]))
    print("-" * 58)
    print("  input:   %s" % row)
    for name in BORDERS:
        print("  %-8s %s" % (name + ":", box_blur(row, half, name)))
    print("-" * 58)
    print("  zero darkens the ends; clamp and reflect keep them flat.")


def error_view(data):
    row, half = data["row"], data["kernel"] // 2
    print("ERROR — absolute error against the true flat value %d" % row[0])
    print("-" * 58)
    for name in BORDERS:
        err = abs_error(box_blur(row, half, name), row)
        print("  %-8s %s   total %.1f" % (name + ":", err, sum(err)))
    print("-" * 58)
    print("  only zero-padding has any error, and it is all at the edges.")


def check(data):
    print("SELF-TEST — zero-padding darkens the border; edge-extend and reflect leave it flat")
    print("-" * 90)
    row, half = data["row"], data["kernel"] // 2
    flat = row[0]
    zero = box_blur(row, half, "zero")
    clamp = box_blur(row, half, "clamp")
    reflect = box_blur(row, half, "reflect")

    zeropad_darkens_border = zero[0] < flat and zero[-1] < flat
    print("  zero-padding makes the edge pixels darker than the interior = %s (%.1f, %.1f vs %d)"
          % (zeropad_darkens_border, zero[0], zero[-1], flat))

    clamp_preserves_border = clamp[0] == flat and clamp[-1] == flat
    print("  edge-extend keeps the edge pixels at the true value = %s (%.1f)" % (clamp_preserves_border, clamp[0]))

    reflect_preserves_border = reflect[0] == flat and reflect[-1] == flat
    print("  reflect keeps the edge pixels at the true value = %s (%.1f)" % (reflect_preserves_border, reflect[0]))

    interior_matches = zero[half:-half] == clamp[half:-half] == reflect[half:-half]
    print("  all policies agree in the interior (the effect is border-only) = %s" % interior_matches)

    only_zero_has_error = sum(abs_error(zero, row)) > 0 and sum(abs_error(clamp, row)) == 0 and sum(abs_error(reflect, row)) == 0
    print("  only zero-padding has any error = %s (zero %.1f, clamp 0, reflect 0)" % (only_zero_has_error, sum(abs_error(zero, row))))

    ok = zeropad_darkens_border and clamp_preserves_border and reflect_preserves_border and interior_matches and only_zero_has_error
    print("-" * 90)
    print("SELF-TEST %s  zeropad_darkens_border=%s  clamp_preserves_border=%s  reflect_preserves_border=%s  interior_matches=%s  only_zero_has_error=%s"
          % ("PASS" if ok else "FAIL", zeropad_darkens_border, clamp_preserves_border, reflect_preserves_border, interior_matches, only_zero_has_error))
    return ok


def main():
    p = argparse.ArgumentParser(description="Choose a border policy for the convolution so the edges do not darken.")
    p.add_argument("--blur", action="store_true")
    p.add_argument("--error", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("pixels=%d  kernel=%d  file=%s  (the row and kernel are a fixture)"
          % (len(data["row"]), data["kernel"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.blur:
        blur_view(data)
    elif args.error:
        error_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
