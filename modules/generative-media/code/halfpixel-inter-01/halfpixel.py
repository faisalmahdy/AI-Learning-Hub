"""Map output pixels to source coordinates by their CENTERS -- src = (dst + 0.5)*scale - 0.5 -- not by src = dst*scale, or the resampled image shifts half a pixel and loses its symmetry.

Resizing an image walks the output pixels and, for each, computes a source coordinate to sample from, then interpolates the source there. The whole correctness of the resize lives in that one coordinate formula, and it hinges on a fact that is easy to forget: a pixel is not a point. It is a little square, and the value it stores is the sample at its CENTER. So output pixel j does not sit at position j; its center covers the source interval it maps to, and that center lands at (j + 0.5)*scale in source space. Converting to the source's own pixel-center grid gives src = (j + 0.5)*scale - 0.5.

The naive formula src = j*scale drops both half-pixel terms and treats pixels as points at their top-left corners. It is off by half a pixel, and the error is not a harmless constant. It shifts the entire resampled image toward one side, and the shift is asymmetric: the output no longer looks the same measured from the left as from the right. Fine detail moves, edges creep, and a resize-then-resize round trip no longer lands where it started. In deep learning this is the infamous align_corners flag, and getting it wrong silently misaligns feature maps between training and inference; in graphics it is the half-texel offset that makes tiled textures seam and upscaled sprites shimmer.

The clean diagnostic is symmetry. Correct center-based resampling is symmetric about the image center, so it COMMUTES with flipping the image -- resample then flip gives the same result as flip then resample. The naive convention is not symmetric, so those two orders disagree: it has quietly built a left/right bias into the resize. That failure of the flip test is the fingerprint of the half-pixel bug.

The rule: map each output pixel to its source coordinate by the pixel-center convention, src = (dst + 0.5)*scale - 0.5, not src = dst*scale, because a pixel's sample point is its center -- so the naive corner-based mapping shifts the resampled image half a pixel and breaks the left/right symmetry that a correct resize preserves.

On this fixture a 4-sample signal is downsampled to 2. The center convention samples the interval centers and returns [15, 35], symmetric under flipping; the naive convention samples the left edges and returns [10, 30], shifted, and fails the flip test. This computes both.

  --coords    the source coordinate each output pixel samples, under each convention
  --resample  the resampled signal under each convention, and the flip-symmetry test
  --check     the naive convention shifts the samples and breaks flip symmetry; the center convention stays centered and symmetric

src and dst_n are the fixture; the sampled coordinates, resampled signals, and symmetry test are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "halfpixel.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def src_coord(j, scale, mode):
    """Where output pixel j samples the source: center convention or naive corner."""
    if mode == "center":
        return (j + 0.5) * scale - 0.5
    return j * scale


def sample(src, x):
    """Linear interpolation at coordinate x, clamped at the edges."""
    if x <= 0:
        return float(src[0])
    if x >= len(src) - 1:
        return float(src[-1])
    i = int(x)
    f = x - i
    return src[i] * (1 - f) + src[i + 1] * f


def resample(src, dst_n, mode):
    scale = len(src) / dst_n
    return [sample(src, src_coord(j, scale, mode)) for j in range(dst_n)]


# ----------------------------------------------------------------- printing

def coords_view(data):
    src, dst_n = data["src"], data["dst_n"]
    scale = len(src) / dst_n
    print("COORDS — source coordinate each output pixel samples (scale=%.1f)" % scale)
    print("-" * 56)
    print("  out pixel   center: (j+0.5)*s-0.5   naive: j*s")
    for j in range(dst_n):
        print("  %-9d   %-20.2f   %.2f" % (j, src_coord(j, scale, "center"), src_coord(j, scale, "naive")))
    print("-" * 56)
    print("  the center coords are symmetric about the middle; the naive coords hug the left")


def resample_view(data):
    src, dst_n = data["src"], data["dst_n"]
    print("RESAMPLE — the downsampled signal, and the flip-symmetry test")
    print("-" * 60)
    for mode in ("center", "naive"):
        r = resample(src, dst_n, mode)
        rf = resample(list(reversed(src)), dst_n, mode)
        sym = rf == list(reversed(r))
        print("  %-7s  resample=%s  flip(resample)=%s  flip-symmetric=%s" % (mode, r, list(reversed(r)), sym))
    print("-" * 60)
    print("  center resampling commutes with flipping; naive does not (it has a left/right bias)")


def check(data):
    print("SELF-TEST — the naive convention shifts the samples and breaks flip symmetry; the center convention stays centered and symmetric")
    print("-" * 132)
    src, dst_n = data["src"], data["dst_n"]
    scale = len(src) / dst_n
    center_coords = [src_coord(j, scale, "center") for j in range(dst_n)]
    naive_coords = [src_coord(j, scale, "naive") for j in range(dst_n)]

    coords_differ = center_coords != naive_coords
    print("  the two conventions sample different source coordinates = %s (%s vs %s)" % (coords_differ, center_coords, naive_coords))

    naive_samples_left_edge = naive_coords[0] == 0.0 and center_coords[0] > 0.0
    print("  the naive convention samples the very edge; the center convention samples inward = %s (%.2f vs %.2f)"
          % (naive_samples_left_edge, naive_coords[0], center_coords[0]))

    # symmetry of the source-coordinate pattern about the middle of the source
    mid = (len(src) - 1) / 2.0
    center_symmetric = all(abs((center_coords[j] - mid) + (center_coords[dst_n - 1 - j] - mid)) < 1e-9 for j in range(dst_n))
    print("  the center coords are symmetric about the source middle = %s" % center_symmetric)

    r = resample(src, dst_n, "center")
    rf = resample(list(reversed(src)), dst_n, "center")
    center_flip_ok = rf == list(reversed(r))
    print("  center resampling commutes with flipping = %s (%s)" % (center_flip_ok, r))

    rn = resample(src, dst_n, "naive")
    rnf = resample(list(reversed(src)), dst_n, "naive")
    naive_flip_broken = rnf != list(reversed(rn))
    print("  naive resampling does NOT commute with flipping = %s (%s vs flip %s)" % (naive_flip_broken, rn, list(reversed(rnf))))

    ok = (coords_differ and naive_samples_left_edge and center_symmetric and center_flip_ok and naive_flip_broken)
    print("-" * 132)
    print("SELF-TEST %s  coords_differ=%s  naive_samples_left_edge=%s  center_symmetric=%s  center_flip_ok=%s  naive_flip_broken=%s"
          % ("PASS" if ok else "FAIL", coords_differ, naive_samples_left_edge, center_symmetric, center_flip_ok, naive_flip_broken))
    return ok


def main():
    p = argparse.ArgumentParser(description="Half-pixel resampling: map each output pixel to its source coordinate by the pixel-center convention, src = (dst + 0.5)*scale - 0.5, not src = dst*scale, because a pixel's sample point is its center -- so the naive corner-based mapping shifts the resampled image half a pixel and breaks the left/right symmetry that a correct resize preserves.")
    p.add_argument("--coords", action="store_true")
    p.add_argument("--resample", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("src=%s  dst_n=%d  file=%s  (the signal is a fixture)" % (data["src"], data["dst_n"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.coords:
        coords_view(data)
    elif args.resample:
        resample_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
