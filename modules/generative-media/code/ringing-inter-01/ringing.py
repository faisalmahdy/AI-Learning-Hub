"""Expect cubic (bicubic/Catmull-Rom) interpolation to overshoot its samples at a sharp edge -- it rings and produces out-of-range values -- where linear interpolation, a convex combination, never does.

Upscaling an image invents new samples between the known pixels, and the choice of interpolation is a choice about a tradeoff. Linear interpolation (bilinear in 2-D) takes a weighted average of the two nearest samples with non-negative weights that sum to one -- a convex combination -- so every interpolated value lies between the samples that produced it. That makes it safe (it can never leave the surrounding pixels' range) and soft: averaging blurs, so bilinear upscaling looks smooth but loses crispness.

Cubic interpolation (bicubic, Catmull-Rom, Lanczos) fits a higher-order curve through more neighbors to recover sharpness, and the sharpness comes from a kernel with negative lobes -- weights that go below zero. Those negative weights are what makes it no longer a convex combination, and they let the fitted curve overshoot: at a high-contrast edge the interpolated values swing below the darker sample and above the brighter one. That over/undershoot is a ring -- a bright halo just past a dark-to-light edge and a dark halo just before it -- and it can push pixel values outside the valid range, below 0 or above 255, which then must be clamped.

The overshoot is not a bug in the implementation; it is the inherent, unavoidable cost of the sharper kernel. Clamping removes the out-of-range values so the image is displayable, but it does not remove the ring -- the halo band is still there, just flattened at the extremes. So the real choice is a tradeoff: linear is soft but monotone (no ringing, no clamping needed), cubic is sharp but rings and needs clamping. Neither is universally right; the point is to know which artifact you are choosing.

The rule: cubic interpolation overshoots the range of its samples at a sharp edge (ringing, and values outside [0, 255] that need clamping) because its kernel has negative lobes and is not a convex combination -- while linear interpolation, a convex combination, stays within the samples' range; the sharpness of cubic and the ringing are the same property.

On this fixture a 0-to-255 step edge is interpolated. Cubic interpolation reaches about 272.9 (above 255) and about -17.9 (below 0) -- a ring roughly 7% of the range past each side -- while linear interpolation stays within [0, 255]. This computes both.

  --interp   the cubic vs linear interpolated value at each fractional position, flagging out-of-range
  --range    the min and max each method produces, against the sample range
  --check    cubic interpolation overshoots the sample range (rings, needs clamping); linear stays within it

samples is the fixture; the interpolated values, ranges, and overshoot are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "ringing.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def catmull_rom(p0, p1, p2, p3, t):
    """Cubic interpolation between p1 and p2 (t in [0,1]) using neighbors p0, p3."""
    return 0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                  + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t)


def linear(p1, p2, t):
    """Linear interpolation between p1 and p2 -- a convex combination."""
    return p1 * (1 - t) + p2 * t


def interpolate(samples):
    """Interpolate at t = 0.25, 0.5, 0.75 in every interior interval; return (position, cubic, linear)."""
    out = []
    for i in range(1, len(samples) - 2):
        for k in (1, 2, 3):
            t = k / 4
            out.append((i + t,
                        catmull_rom(samples[i - 1], samples[i], samples[i + 1], samples[i + 2], t),
                        linear(samples[i], samples[i + 1], t)))
    return out


# ----------------------------------------------------------------- printing

def interp_view(data):
    samples = data["samples"]
    lo, hi = min(samples), max(samples)
    print("INTERP — cubic vs linear interpolated values (sample range [%d, %d])" % (lo, hi))
    print("-" * 60)
    print("  position   cubic      linear     cubic out of range?")
    for pos, c, l in interpolate(samples):
        oor = "  <- OUT OF RANGE" if c < lo or c > hi else ""
        print("  %-8.2f   %-8.2f   %-8.2f   %s" % (pos, c, l, "yes" + oor if (c < lo or c > hi) else "no"))
    print("-" * 60)
    print("  the cubic values near the edge swing past 255 and below 0; linear never leaves [0, 255]")


def range_view(data):
    samples = data["samples"]
    lo, hi = min(samples), max(samples)
    pts = interpolate(samples)
    cmin, cmax = min(c for _, c, _ in pts), max(c for _, c, _ in pts)
    lmin, lmax = min(l for _, _, l in pts), max(l for _, _, l in pts)
    print("RANGE — interpolated value range vs the sample range [%d, %d]" % (lo, hi))
    print("-" * 58)
    print("  cubic  interp range = [%.2f, %.2f]   overshoot %.2f past each side" % (cmin, cmax, cmax - hi))
    print("  linear interp range = [%.2f, %.2f]" % (lmin, lmax))
    print("-" * 58)
    print("  cubic exceeds the sample range on both sides (the ring); linear is contained")


def check(data):
    print("SELF-TEST — cubic interpolation overshoots the sample range (rings, needs clamping); linear stays within it")
    print("-" * 116)
    samples = data["samples"]
    lo, hi = min(samples), max(samples)
    pts = interpolate(samples)
    cmin, cmax = min(c for _, c, _ in pts), max(c for _, c, _ in pts)
    lmin, lmax = min(l for _, _, l in pts), max(l for _, _, l in pts)

    samples_in_range = all(lo <= s <= hi for s in samples)
    print("  every input sample is within [%d, %d] = %s" % (lo, hi, samples_in_range))

    cubic_overshoots_high = cmax > hi
    print("  cubic interpolation exceeds the max sample = %s (%.2f > %d)" % (cubic_overshoots_high, cmax, hi))

    cubic_undershoots_low = cmin < lo
    print("  cubic interpolation drops below the min sample = %s (%.2f < %d)" % (cubic_undershoots_low, cmin, lo))

    linear_stays_in_range = lo <= lmin and lmax <= hi
    print("  linear interpolation stays within the sample range = %s ([%.2f, %.2f])" % (linear_stays_in_range, lmin, lmax))

    overshoot_inherent = cubic_overshoots_high and samples_in_range
    print("  the overshoot appears even though all samples are in range (it is inherent) = %s" % overshoot_inherent)

    ok = (samples_in_range and cubic_overshoots_high and cubic_undershoots_low
          and linear_stays_in_range and overshoot_inherent)
    print("-" * 116)
    print("SELF-TEST %s  samples_in_range=%s  cubic_overshoots_high=%s  cubic_undershoots_low=%s  linear_stays_in_range=%s  overshoot_inherent=%s"
          % ("PASS" if ok else "FAIL", samples_in_range, cubic_overshoots_high, cubic_undershoots_low, linear_stays_in_range, overshoot_inherent))
    return ok


def main():
    p = argparse.ArgumentParser(description="Interpolation ringing: cubic interpolation overshoots the range of its samples at a sharp edge (ringing, and values outside [0,255] that need clamping) because its kernel has negative lobes and is not a convex combination -- while linear interpolation, a convex combination, stays within the samples' range; the sharpness of cubic and the ringing are the same property.")
    p.add_argument("--interp", action="store_true")
    p.add_argument("--range", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("samples=%s  file=%s  (the step edge is a fixture)" % (data["samples"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.interp:
        interp_view(data)
    elif args.range:
        range_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
