"""Weight neighbors by intensity too, or a blur that removes noise also destroys the edge.

Smoothing removes noise by averaging each pixel with its neighbors. A Gaussian blur weights those neighbors
by DISTANCE only -- closer neighbors count more -- so it happily averages across an edge, mixing a dark pixel
with the bright pixels just past the edge. That is fine in a flat region, where the neighbors are similar, but
at an edge it is destruction: the sharp step from 10 to 30 gets smeared into a gentle ramp, and the picture
goes soft. You cannot turn the blur up to kill more noise without blurring the edges more; distance-only
weighting cannot tell "noise" from "edge."

The bilateral filter adds a second weight: RANGE. A neighbor counts only in proportion to how similar its
brightness is to the center pixel. Neighbors on the same side of an edge are similar, so they contribute and
the noise averages out. Neighbors across the edge are very different, so their weight drops to near zero and
they are excluded -- the average never reaches across the edge, and the edge stays crisp. The filter smooths
within regions but not between them, which is exactly edge-preserving smoothing. (This toy uses a hard range
cutoff; a real bilateral filter uses a smooth Gaussian range weight, but the mechanism is identical.)

On this fixture the signal steps from ~10 to ~30 with a little noise on each side. A Gaussian blur softens the
edge from a step of 20 down to 9 while smoothing the noise. The bilateral filter smooths the same noise but
keeps the edge at a step of ~18.7, because the across-edge neighbors are dropped. This computes both.

  --filter    the signal, the Gaussian blur, and the bilateral filter, value by value
  --edge      the step height across the edge under each filter, and the flat-region smoothing
  --check     the Gaussian blurs the edge; the bilateral smooths the flat region but preserves the edge

The signal, kernel, and range threshold are the fixture; every output is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "signal.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def neighbors(sig, i):
    """The left, center, right values, replicating at the borders."""
    left = sig[i - 1] if i > 0 else sig[i]
    right = sig[i + 1] if i < len(sig) - 1 else sig[i]
    return left, sig[i], right


def gaussian(sig, kernel, i):
    """Distance-only weights: the [1,2,1] kernel, applied regardless of intensity."""
    l, c, r = neighbors(sig, i)
    wl, wc, wr = kernel
    return (wl * l + wc * c + wr * r) / (wl + wc + wr)


def bilateral(sig, kernel, thresh, i):
    """Distance AND range weights: drop a neighbor whose intensity differs from the center by more than thresh."""
    l, c, r = neighbors(sig, i)
    wl = kernel[0] if abs(l - c) <= thresh else 0
    wc = kernel[1]
    wr = kernel[2] if abs(r - c) <= thresh else 0
    return (wl * l + wc * c + wr * r) / (wl + wc + wr)


def apply(sig, fn):
    return [round(fn(i), 2) for i in range(len(sig))]


# ----------------------------------------------------------------- printing

def fmt(seq):
    return " ".join("%6.2f" % v for v in seq)


def filter_view(data):
    sig, k, thr = data["signal"], data["spatial_kernel"], data["range_threshold"]
    g = apply(sig, lambda i: gaussian(sig, k, i))
    b = apply(sig, lambda i: bilateral(sig, k, thr, i))
    print("FILTER — Gaussian blur vs bilateral filter (kernel %s, range %d)" % (k, thr))
    print("-" * 58)
    print("  signal:     %s" % fmt(sig))
    print("  gaussian:   %s" % fmt(g))
    print("  bilateral:  %s" % fmt(b))
    print("-" * 58)
    print("  at the edge (index 2,3) the gaussian caves in; the bilateral holds.")


def edge_view(data):
    sig, k, thr = data["signal"], data["spatial_kernel"], data["range_threshold"]
    g = apply(sig, lambda i: gaussian(sig, k, i))
    b = apply(sig, lambda i: bilateral(sig, k, thr, i))
    print("EDGE — step height across the edge, and flat-region smoothing")
    print("-" * 58)
    print("  edge step (index3 - index2): signal %.2f  gaussian %.2f  bilateral %.2f"
          % (sig[3] - sig[2], g[3] - g[2], b[3] - b[2]))
    print("  flat-noise pixel index1: signal %.2f -> gaussian %.2f, bilateral %.2f"
          % (sig[1], g[1], b[1]))
    print("-" * 58)
    print("  both smooth the flat noise; only the bilateral keeps the edge step.")


def check(data):
    print("SELF-TEST — the Gaussian blurs the edge; the bilateral smooths the flat region but preserves the edge")
    print("-" * 104)
    sig, k, thr = data["signal"], data["spatial_kernel"], data["range_threshold"]
    g = apply(sig, lambda i: gaussian(sig, k, i))
    b = apply(sig, lambda i: bilateral(sig, k, thr, i))
    orig_step = sig[3] - sig[2]
    g_step, b_step = g[3] - g[2], b[3] - b[2]

    gaussian_blurs_edge = g_step < orig_step * 0.6
    print("  the gaussian collapses the edge step = %s (%.2f -> %.2f)" % (gaussian_blurs_edge, orig_step, g_step))

    bilateral_preserves_edge = b_step > orig_step * 0.9
    print("  the bilateral keeps the edge step = %s (%.2f, %.0f%% of original)" % (bilateral_preserves_edge, b_step, 100 * b_step / orig_step))

    bilateral_beats_gaussian_edge = b_step > g_step
    print("  the bilateral edge is sharper than the gaussian = %s (%.2f > %.2f)" % (bilateral_beats_gaussian_edge, b_step, g_step))

    both_smooth_flat = abs(g[1] - 10) < abs(sig[1] - 10) and abs(b[1] - 10) < abs(sig[1] - 10)
    print("  both smooth the flat-region noise pixel = %s (%.2f -> g %.2f, b %.2f)" % (both_smooth_flat, sig[1], g[1], b[1]))

    range_gate_drops_across_edge = abs(sig[3] - sig[2]) > thr
    print("  the across-edge neighbor exceeds the range threshold (dropped) = %s (|30-10|=%d > %d)" % (range_gate_drops_across_edge, abs(sig[3] - sig[2]), thr))

    ok = gaussian_blurs_edge and bilateral_preserves_edge and bilateral_beats_gaussian_edge and both_smooth_flat and range_gate_drops_across_edge
    print("-" * 104)
    print("SELF-TEST %s  gaussian_blurs_edge=%s  bilateral_preserves_edge=%s  bilateral_beats_gaussian_edge=%s  both_smooth_flat=%s  range_gate_drops_across_edge=%s"
          % ("PASS" if ok else "FAIL", gaussian_blurs_edge, bilateral_preserves_edge, bilateral_beats_gaussian_edge, both_smooth_flat, range_gate_drops_across_edge))
    return ok


def main():
    p = argparse.ArgumentParser(description="Weight neighbors by intensity as well as distance (bilateral) to smooth without blurring edges.")
    p.add_argument("--filter", action="store_true")
    p.add_argument("--edge", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("length=%d  kernel=%s  range_threshold=%d  file=%s  (the signal is a fixture)"
          % (len(data["signal"]), data["spatial_kernel"], data["range_threshold"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.filter:
        filter_view(data)
    elif args.edge:
        edge_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
