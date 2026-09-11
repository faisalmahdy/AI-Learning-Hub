"""Interpolate each missing color from its measured neighbors -- replicating the nearest one invents false colors.

A camera's image sensor does not measure red, green, and blue at every pixel. Over each photosite sits a single colored
filter, so each site measures only ONE channel; the sensor's raw output is a MOSAIC of single-color samples, laid out in a
fixed pattern (the Bayer array: rows of R,G,R,G alternating with G,B,G,B, so half the pixels are green and a quarter each
red and blue). The full-color image -- three channels at every pixel -- does not exist yet; it must be RECONSTRUCTED by
estimating, at each pixel, the two channels that pixel did not measure, from the neighboring pixels that did. This
reconstruction is called demosaicing, and it is done for every photo a Bayer-sensor camera takes.

The naive reconstruction is to fill each missing channel from the NEAREST pixel that measured it -- copy the closest red
into a pixel that only measured green, and so on. This is fast and it is wrong at exactly the places that matter. Copying
the nearest same-color sample ignores the sample on the other side, so across a gradient or an edge it produces a value
that is too high or too low, and because the three channels are reconstructed independently with this crude copy, their
errors do not match -- a pixel that should be neutral gray gets, say, too much red and too little green, which the eye sees
as a colored fringe or a zippering pattern along edges. The artifacts are COLOR errors invented by the reconstruction, not
present in the scene.

The better reconstruction interpolates: estimate a missing channel as the average of the measured samples of that channel
on BOTH sides. Because a smoothly varying channel is close to linear over a couple of pixels, averaging the two neighbors
lands on the true value, so the interpolated channel tracks the real gradient instead of stair-stepping, and the three
channels stay consistent, which is what kills the false color. (Real demosaicing goes further -- edge-directed and
gradient-corrected methods interpolate ALONG edges rather than across them, and use the correlation between channels -- but
the core is: interpolate the missing samples, do not replicate the nearest one.)

The rule: reconstruct a missing color channel by interpolating the measured samples of that channel on both sides, not by
copying the single nearest one, because independent nearest-neighbor replication invents color fringes across edges and
gradients while two-sided interpolation tracks the true value and keeps the channels consistent.

On this fixture the sensor row alternates R and G filters; both true channels vary linearly. At the interior missing
pixels, bilinear interpolation of a channel from its two measured neighbors recovers the ground truth exactly (zero error),
while nearest-neighbor replication is off by up to 20 levels. This computes both.

  --recon     the reconstructed R and G at every pixel, nearest-replication vs bilinear, beside the ground truth
  --error     the per-pixel reconstruction error of each method against the truth, and the interior totals (naive > 0, bilinear = 0)
  --check     nearest replication misses the interior missing channels; bilinear interpolation recovers them exactly

pattern, mosaic, truth_R, and truth_G are the fixture; every reconstructed channel and error is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "demosaic.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def neighbors(pattern, mosaic, i, channel):
    """The nearest measured sample of `channel` on the left and on the right of position i (value, distance)."""
    left = right = None
    for j in range(i - 1, -1, -1):
        if pattern[j] == channel:
            left = (mosaic[j], i - j)
            break
    for j in range(i + 1, len(pattern)):
        if pattern[j] == channel:
            right = (mosaic[j], j - i)
            break
    return left, right


def estimate_nearest(pattern, mosaic, i, channel):
    """Replicate the single nearest measured sample of the channel (tie -> left)."""
    left, right = neighbors(pattern, mosaic, i, channel)
    if left and right:
        return left[0] if left[1] <= right[1] else right[0]
    return (left or right)[0]


def estimate_bilinear(pattern, mosaic, i, channel):
    """Average the measured samples of the channel on both sides (one side only at an edge)."""
    left, right = neighbors(pattern, mosaic, i, channel)
    if left and right:
        return (left[0] + right[0]) / 2
    return (left or right)[0]


def reconstruct(data, estimator):
    """Full (R, G) per pixel: the measured channel is kept; the missing one is estimated."""
    pattern, mosaic = data["pattern"], data["mosaic"]
    out = []
    for i, ch in enumerate(pattern):
        r = mosaic[i] if ch == "R" else estimator(pattern, mosaic, i, "R")
        g = mosaic[i] if ch == "G" else estimator(pattern, mosaic, i, "G")
        out.append((r, g))
    return out


def interior_error(data, estimator):
    """Total absolute error of the ESTIMATED (missing) channels vs truth, excluding edge pixels 0 and last."""
    pattern = data["pattern"]
    recon = reconstruct(data, estimator)
    total = 0
    for i in range(1, len(pattern) - 1):
        r, g = recon[i]
        if pattern[i] != "R":
            total += abs(r - data["truth_R"][i])
        if pattern[i] != "G":
            total += abs(g - data["truth_G"][i])
    return total


# ----------------------------------------------------------------- printing

def recon_view(data):
    near = reconstruct(data, estimate_nearest)
    bil = reconstruct(data, estimate_bilinear)
    print("RECON — reconstructed (R,G) per pixel; the measured channel is exact, the other is estimated")
    print("-" * 78)
    print("  pos  filter  nearest (R,G)   bilinear (R,G)   truth (R,G)")
    for i, ch in enumerate(data["pattern"]):
        print("  %-3d  %-6s  %-15s %-16s (%d, %d)"
              % (i, ch, "(%g, %g)" % near[i], "(%g, %g)" % bil[i], data["truth_R"][i], data["truth_G"][i]))
    print("-" * 78)
    print("  at interior pixels bilinear matches the truth; nearest replication does not.")


def error_view(data):
    pattern = data["pattern"]
    near = reconstruct(data, estimate_nearest)
    bil = reconstruct(data, estimate_bilinear)
    print("ERROR — reconstruction error of the estimated channel vs the ground truth")
    print("-" * 68)
    print("  pos  filter  missing  nearest->err       bilinear->err")
    for i, ch in enumerate(pattern):
        miss = "G" if ch == "R" else "R"
        truth = data["truth_G"][i] if miss == "G" else data["truth_R"][i]
        nv = near[i][1] if miss == "G" else near[i][0]
        bv = bil[i][1] if miss == "G" else bil[i][0]
        edge = "  (edge)" if i == 0 or i == len(pattern) - 1 else ""
        print("  %-3d  %-6s  %-7s  %g->%-2g            %g->%g%s" % (i, ch, miss, nv, abs(nv - truth), bv, abs(bv - truth), edge))
    print("-" * 68)
    print("  interior total error -- nearest: %g   bilinear: %g"
          % (interior_error(data, estimate_nearest), interior_error(data, estimate_bilinear)))


def check(data):
    print("SELF-TEST — nearest replication misses the interior missing channels; bilinear interpolation recovers them exactly")
    print("-" * 114)
    near = reconstruct(data, estimate_nearest)
    bil = reconstruct(data, estimate_bilinear)
    near_err = interior_error(data, estimate_nearest)
    bil_err = interior_error(data, estimate_bilinear)

    bilinear_exact_interior = bil_err == 0
    print("  bilinear interior reconstruction error = %g -> exact = %s" % (bil_err, bilinear_exact_interior))

    nearest_wrong_interior = near_err > 0
    print("  nearest interior reconstruction error = %g -> wrong = %s" % (near_err, nearest_wrong_interior))

    bilinear_beats_nearest = bil_err < near_err
    print("  bilinear beats nearest on interior error = %s (%g < %g)" % (bilinear_beats_nearest, bil_err, near_err))

    # pixel 2 (R filter, missing G): truth G=120; bilinear avg(110,130)=120; nearest picks 110
    pixel2_bilinear_true = bil[2][1] == data["truth_G"][2]
    print("  pixel 2 missing G: bilinear = %g = truth %d = %s (nearest = %g)"
          % (bil[2][1], data["truth_G"][2], pixel2_bilinear_true, near[2][1]))

    nearest_invents_error = near[2][1] != data["truth_G"][2]
    print("  pixel 2 missing G: nearest replication is wrong = %s (%g vs truth %d)"
          % (nearest_invents_error, near[2][1], data["truth_G"][2]))

    ok = bilinear_exact_interior and nearest_wrong_interior and bilinear_beats_nearest and pixel2_bilinear_true and nearest_invents_error
    print("-" * 114)
    print("SELF-TEST %s  bilinear_exact_interior=%s  nearest_wrong_interior=%s  bilinear_beats_nearest=%s  pixel2_bilinear_true=%s  nearest_invents_error=%s"
          % ("PASS" if ok else "FAIL", bilinear_exact_interior, nearest_wrong_interior, bilinear_beats_nearest, pixel2_bilinear_true, nearest_invents_error))
    return ok


def main():
    p = argparse.ArgumentParser(description="Bayer demosaicing: reconstruct a missing color channel by interpolating the measured samples of that channel on both sides, not by copying the single nearest one, because independent nearest-neighbor replication invents color fringes across edges and gradients while two-sided interpolation tracks the true value and keeps the channels consistent.")
    p.add_argument("--recon", action="store_true")
    p.add_argument("--error", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("pattern=%s  mosaic=%s  file=%s  (the mosaic and ground truth are a fixture)"
          % (data["pattern"], data["mosaic"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.recon:
        recon_view(data)
    elif args.error:
        error_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
