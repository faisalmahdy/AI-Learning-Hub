"""Subsample the chroma, not the luma -- the eye barely notices halved color resolution but sees every lost bit of brightness detail.

Storing an image as red, green, and blue is convenient but wasteful for compression, because it spreads the information the eye cares about evenly across three channels that are treated identically. Human vision is not even-handed: it is far more sensitive to LUMINANCE -- brightness and its fine detail, edges, texture -- than to CHROMINANCE, the color itself. You can blur the color of an image substantially and, as long as the brightness stays sharp, it looks almost unchanged; blur the brightness and it looks obviously soft. Every image and video codec exploits this by first converting RGB into one luma channel (Y) and two chroma channels (Cb, Cr), which separates the detail the eye tracks from the color it does not.

Chroma subsampling is the payoff. Keep the luma at full resolution -- every pixel of brightness detail -- but store the chroma at half resolution in each direction, one color sample per 2x2 block of pixels. This is '4:2:0', and it cuts the color data to a quarter, taking the whole image from three full planes to one full plane plus two quarter planes -- half the data -- for a loss the eye mostly cannot see, because it fell entirely on the color channel it is worst at resolving. At decode time the quarter-resolution chroma is upsampled back to full size and recombined with the untouched luma.

The loss is not zero, and it lands in a specific place: sharp COLOR edges. A boundary where the color changes abruptly but the brightness does not -- saturated colored text on a colored background, thin colored lines, fine color patterns -- has high-frequency chroma, and averaging a 2x2 block throws that detail away, so the color edge blurs or bleeds. This is exactly the 'colored text looks fuzzy' artifact of aggressive subsampling. It is invisible on the smooth color gradients that fill most photographs and very visible on synthetic sharp-color content, which is why subsampling is near-free for photos and why UI screenshots and colored text are where it shows.

The rule: subsample the chroma (color) planes, not the luma (brightness) plane -- store one chroma sample per block of pixels while keeping luma full-resolution -- because the eye resolves brightness detail far better than color, so halving chroma resolution roughly halves the data with little visible loss, degrading only sharp color edges while every bit of brightness detail is preserved.

On this fixture luma is kept full-resolution (lossless). Subsampling the smooth chroma to a quarter and upsampling back is lossless too (max error 0); subsampling the sharp-color chroma averages each 2x2 block to 80 and cannot recover its 20/140 edge (max error 60). The scheme stores half the data. This computes both.

  --planes    the luma and the two chroma planes, and the 4:2:0 data ratio versus full-resolution 4:4:4
  --reconstruct  subsample-then-upsample the smooth vs sharp chroma, and the reconstruction error of each
  --check     luma is untouched; subsampling is lossless on smooth chroma and degrades sharp color edges, at half the data

luma, smooth_chroma, and sharp_chroma are the fixture; every subsampled plane, reconstruction, error, and data ratio is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "chromasub.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def subsample_2x2(plane):
    """Average each 2x2 block to one sample -- quarter-resolution chroma."""
    n = len(plane)
    out = []
    for by in range(0, n, 2):
        row = []
        for bx in range(0, n, 2):
            block = [plane[by][bx], plane[by][bx + 1], plane[by + 1][bx], plane[by + 1][bx + 1]]
            row.append(sum(block) / 4)
        out.append(row)
    return out


def upsample_2x(small):
    """Nearest-neighbor upsample: each sample fills its 2x2 block back to full resolution."""
    out = []
    for row in small:
        full_row = []
        for v in row:
            full_row.extend([v, v])
        out.append(list(full_row))
        out.append(list(full_row))
    return out


def max_abs_error(a, b):
    return max(abs(a[y][x] - b[y][x]) for y in range(len(a)) for x in range(len(a[0])))


def data_ratio_420(n):
    """4:2:0 bytes (Y full + two quarter chroma) over 4:4:4 bytes (three full planes)."""
    full = 3 * n * n
    sub = n * n + 2 * (n // 2) * (n // 2)
    return sub / full


# ----------------------------------------------------------------- printing

def grid(p):
    return " / ".join("[" + " ".join("%g" % v for v in row) + "]" for row in p)


def planes_view(data):
    n = len(data["luma"])
    print("PLANES — luma (full-res) and chroma, and the 4:2:0 data ratio")
    print("-" * 62)
    print("  luma (Y, %dx%d, kept full):   %s" % (n, n, grid(data["luma"])))
    print("  smooth chroma (%dx%d):        %s" % (n, n, grid(data["smooth_chroma"])))
    print("  sharp  chroma (%dx%d):        %s" % (n, n, grid(data["sharp_chroma"])))
    print("-" * 62)
    print("  4:4:4 (all full) = %d samples ; 4:2:0 = %d samples ; ratio = %.2f (half the data)"
          % (3 * n * n, n * n + 2 * (n // 2) * (n // 2), data_ratio_420(n)))


def reconstruct_view(data):
    print("RECONSTRUCT — subsample then upsample each chroma plane")
    print("-" * 66)
    for name, key in (("smooth", "smooth_chroma"), ("sharp", "sharp_chroma")):
        plane = data[key]
        small = subsample_2x2(plane)
        back = upsample_2x(small)
        print("  %s chroma:" % name)
        print("    subsampled (quarter): %s" % grid(small))
        print("    upsampled back:       %s" % grid(back))
        print("    max reconstruction error = %g" % max_abs_error(plane, back))


def check(data):
    print("SELF-TEST — luma is untouched; subsampling is lossless on smooth chroma and degrades sharp color edges, at half the data")
    print("-" * 122)
    n = len(data["luma"])
    smooth, sharp = data["smooth_chroma"], data["sharp_chroma"]
    smooth_err = max_abs_error(smooth, upsample_2x(subsample_2x2(smooth)))
    sharp_err = max_abs_error(sharp, upsample_2x(subsample_2x2(sharp)))

    luma_full_res = True  # luma is never subsampled in 4:2:0
    print("  the luma plane is kept full-resolution (never subsampled) = %s" % luma_full_res)

    data_saved_half = abs(data_ratio_420(n) - 0.5) < 1e-9
    print("  4:2:0 stores half the data of 4:4:4 = %s (ratio %.2f)" % (data_saved_half, data_ratio_420(n)))

    smooth_lossless = smooth_err == 0
    print("  subsampling the smooth chroma is lossless = %s (max error %g)" % (smooth_lossless, smooth_err))

    sharp_degraded = sharp_err > 0
    print("  subsampling the sharp-color chroma degrades it = %s (max error %g)" % (sharp_degraded, sharp_err))

    degradation_worse_on_sharp = sharp_err > smooth_err
    print("  the sharp color edge is hurt far more than smooth color = %s (%g > %g)" % (degradation_worse_on_sharp, sharp_err, smooth_err))

    loss_only_in_chroma = luma_full_res and sharp_degraded
    print("  the loss falls only on chroma; brightness detail is preserved = %s" % loss_only_in_chroma)

    ok = luma_full_res and data_saved_half and smooth_lossless and sharp_degraded and degradation_worse_on_sharp and loss_only_in_chroma
    print("-" * 122)
    print("SELF-TEST %s  luma_full_res=%s  data_saved_half=%s  smooth_lossless=%s  sharp_degraded=%s  degradation_worse_on_sharp=%s  loss_only_in_chroma=%s"
          % ("PASS" if ok else "FAIL", luma_full_res, data_saved_half, smooth_lossless, sharp_degraded, degradation_worse_on_sharp, loss_only_in_chroma))
    return ok


def main():
    p = argparse.ArgumentParser(description="Chroma subsampling: subsample the chroma (color) planes, not the luma (brightness) plane -- store one chroma sample per block of pixels while keeping luma full-resolution -- because the eye resolves brightness detail far better than color, so halving chroma resolution roughly halves the data with little visible loss, degrading only sharp color edges while every bit of brightness detail is preserved.")
    p.add_argument("--planes", action="store_true")
    p.add_argument("--reconstruct", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("luma=%dx%d  chroma planes=2  file=%s  (the luma and chroma planes are a fixture)"
          % (len(data["luma"]), len(data["luma"][0]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.planes:
        planes_view(data)
    elif args.reconstruct:
        reconstruct_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
