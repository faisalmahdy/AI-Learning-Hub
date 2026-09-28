"""Blur with two 1-D passes, not one 2-D kernel -- a separable filter gives the identical result at a fraction of the cost.

A Gaussian blur, a box blur, and many other common filters are applied by convolution: slide a k-by-k kernel over the image and, at each pixel, multiply the kernel weights by the covered pixels and sum. Done directly this is k*k multiply-adds per output pixel, and for a real blur -- an 11-by-11 or 21-by-21 kernel -- that is a hundred to several hundred operations at every pixel, which is a lot for a full-resolution image. The obvious implementation is also the expensive one.

The saving comes from a structural fact about these kernels: they are SEPARABLE. A separable 2-D kernel is exactly the outer product of a 1-D kernel with itself -- the Gaussian is the classic example, because a 2-D Gaussian factors into a product of two 1-D Gaussians, one along each axis. When a kernel separates like this, convolving with the full 2-D kernel is mathematically identical to convolving each ROW with the 1-D kernel and then convolving each COLUMN of that intermediate result with the same 1-D kernel. Two passes of a k-length filter instead of one pass of a k-by-k filter.

The cost drops from k*k to 2*k multiply-adds per pixel, and the outputs are not approximately equal -- they are identical, because the two-pass computation is just the 2-D convolution's sum re-associated, not an approximation of it. For k=3 that is 9 operations versus 6, a modest win; for k=11 it is 121 versus 22, and for k=21 it is 441 versus 42. The larger the blur, the bigger the factor, which is why every production image and graphics library implements Gaussian blur as separable passes. The one precondition is separability: the trick applies exactly when the 2-D kernel equals the outer product of a 1-D kernel (Gaussian, box, and many smoothing and derivative kernels qualify); a genuinely non-separable kernel cannot be split this way.

The rule: apply a separable blur as two 1-D convolutions -- once across rows, once down columns -- rather than one 2-D convolution with the full kernel, because a separable kernel is the outer product of a 1-D kernel with itself, so the two-pass computation gives the byte-identical result at 2*k multiply-adds per pixel instead of k*k, a saving that grows with kernel size.

On this fixture the 1-D kernel is [0.25, 0.5, 0.25]; its outer product is the 3x3 blur kernel. The 2-D convolution and the two 1-D passes produce identical interior outputs (max difference 0), at 9 versus 6 operations per pixel here and 121 versus 22 for an 11-tap blur. This computes both.

  --kernels   the 1-D kernel, the 2-D outer-product kernel it generates, and that the 2-D kernel is separable
  --blur      the 2-D-convolved interior and the two-pass interior side by side, and their maximum difference
  --check     the kernel is separable; the two-pass blur matches the 2-D blur exactly at fewer operations per pixel

image and kernel_1d are the fixture; the 2-D kernel, both outputs, their difference, and the op counts are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "separable.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def outer(k1d):
    """The 2-D kernel a 1-D kernel generates: the outer product of the kernel with itself."""
    return [[a * b for b in k1d] for a in k1d]


def conv2d_interior(img, k2d):
    """Full 2-D convolution at interior pixels (valid region), k*k multiply-adds each."""
    h, w = len(img), len(img[0])
    r = len(k2d) // 2
    out = []
    for y in range(r, h - r):
        row = []
        for x in range(r, w - r):
            s = 0.0
            for i in range(len(k2d)):
                for j in range(len(k2d)):
                    s += img[y + i - r][x + j - r] * k2d[i][j]
            row.append(s)
        out.append(row)
    return out


def separable_interior(img, k1d):
    """Two 1-D passes: rows then columns, 2*k multiply-adds each, over the same interior region."""
    h, w = len(img), len(img[0])
    r = len(k1d) // 2
    horiz = [[None] * w for _ in range(h)]
    for y in range(h):
        for x in range(r, w - r):
            horiz[y][x] = sum(img[y][x + j - r] * k1d[j] for j in range(len(k1d)))
    out = []
    for y in range(r, h - r):
        row = []
        for x in range(r, w - r):
            row.append(sum(horiz[y + i - r][x] * k1d[i] for i in range(len(k1d))))
        out.append(row)
    return out


def max_diff(a, b):
    return max(abs(a[y][x] - b[y][x]) for y in range(len(a)) for x in range(len(a[0])))


def is_separable(k2d, k1d):
    """Whether the 2-D kernel equals the outer product of the 1-D kernel."""
    op = outer(k1d)
    return all(abs(k2d[i][j] - op[i][j]) < 1e-12 for i in range(len(k2d)) for j in range(len(k2d)))


def fmt(grid):
    return " / ".join("[" + " ".join("%g" % v for v in row) + "]" for row in grid)


# ----------------------------------------------------------------- printing

def kernels_view(data):
    k1d = data["kernel_1d"]
    k2d = outer(k1d)
    print("KERNELS — the 1-D kernel and the 2-D kernel it generates")
    print("-" * 56)
    print("  1-D kernel = %s  (sum %g)" % (k1d, sum(k1d)))
    print("  2-D kernel = outer product:")
    for row in k2d:
        print("    [" + " ".join("%.4f" % v for v in row) + "]")
    print("-" * 56)
    print("  2-D kernel sum = %g (normalized) ; separable = %s" % (sum(sum(r) for r in k2d), is_separable(k2d, k1d)))


def blur_view(data):
    img, k1d = data["image"], data["kernel_1d"]
    k2d = outer(k1d)
    a = conv2d_interior(img, k2d)
    b = separable_interior(img, k1d)
    print("BLUR — 2-D convolution vs two 1-D passes (interior region)")
    print("-" * 56)
    print("  2-D convolved interior:")
    for row in a:
        print("    [" + " ".join("%.3f" % v for v in row) + "]")
    print("  two-pass interior:")
    for row in b:
        print("    [" + " ".join("%.3f" % v for v in row) + "]")
    print("-" * 56)
    print("  maximum difference = %g (identical)" % max_diff(a, b))


def check(data):
    print("SELF-TEST — the kernel is separable; the two-pass blur matches the 2-D blur exactly at fewer operations per pixel")
    print("-" * 116)
    img, k1d = data["image"], data["kernel_1d"]
    k2d = outer(k1d)
    a = conv2d_interior(img, k2d)
    b = separable_interior(img, k1d)
    k = len(k1d)

    kernel_separable = is_separable(k2d, k1d)
    print("  the 2-D kernel is the outer product of the 1-D kernel (separable) = %s" % kernel_separable)

    kernel_normalized = abs(sum(k1d) - 1.0) < 1e-12 and abs(sum(sum(r) for r in k2d) - 1.0) < 1e-12
    print("  both kernels sum to 1 (blur preserves brightness) = %s (1-D %g, 2-D %g)" % (kernel_normalized, sum(k1d), sum(sum(r) for r in k2d)))

    results_identical = max_diff(a, b) < 1e-12
    print("  the two-pass output is identical to the 2-D output = %s (max diff %g)" % (results_identical, max_diff(a, b)))

    two_d_ops = k * k
    sep_ops = 2 * k
    separable_fewer_ops = sep_ops < two_d_ops
    print("  the separable passes use fewer multiply-adds per pixel = %s (%d vs %d for k=%d)" % (separable_fewer_ops, sep_ops, two_d_ops, k))

    big_two_d, big_sep = 11 * 11, 2 * 11
    saving_grows_with_k = (big_two_d / big_sep) > (two_d_ops / sep_ops)
    print("  the saving grows with kernel size = %s (k=11: %d vs %d, ratio %.1fx > k=%d ratio %.1fx)"
          % (saving_grows_with_k, big_two_d, big_sep, big_two_d / big_sep, k, two_d_ops / sep_ops))

    center_is_blurred = a[len(a) // 2][len(a[0]) // 2] < img[len(img) // 2][len(img[0]) // 2]
    print("  the bright center is actually blurred (peak lowered) = %s (%.1f < %d)" % (center_is_blurred, a[len(a) // 2][len(a[0]) // 2], img[len(img) // 2][len(img[0]) // 2]))

    ok = kernel_separable and kernel_normalized and results_identical and separable_fewer_ops and saving_grows_with_k and center_is_blurred
    print("-" * 116)
    print("SELF-TEST %s  kernel_separable=%s  kernel_normalized=%s  results_identical=%s  separable_fewer_ops=%s  saving_grows_with_k=%s  center_is_blurred=%s"
          % ("PASS" if ok else "FAIL", kernel_separable, kernel_normalized, results_identical, separable_fewer_ops, saving_grows_with_k, center_is_blurred))
    return ok


def main():
    p = argparse.ArgumentParser(description="Separable convolution: apply a separable blur as two 1-D convolutions -- once across rows, once down columns -- rather than one 2-D convolution with the full kernel, because a separable kernel is the outer product of a 1-D kernel with itself, so the two-pass computation gives the byte-identical result at 2*k multiply-adds per pixel instead of k*k, a saving that grows with kernel size.")
    p.add_argument("--kernels", action="store_true")
    p.add_argument("--blur", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("image=%dx%d  kernel_1d=%s  file=%s  (the image and 1-D kernel are a fixture)"
          % (len(data["image"]), len(data["image"][0]), data["kernel_1d"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.kernels:
        kernels_view(data)
    elif args.blur:
        blur_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
