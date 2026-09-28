"""Upsample with bilinear interpolation, not nearest-neighbor -- nearest only copies pixels and comes out blocky.

Enlarging an image invents new pixels between the old ones, and how you invent them decides whether the
result is smooth or blocky. NEAREST-NEIGHBOR upsampling copies each new pixel from the closest original
sample, so a run of new pixels all take the same value and the output is a staircase of flat plateaus with
sharp jumps between them -- the chunky, pixelated look of an image scaled up in a naive viewer. It never
produces a value that was not already in the input; it can only repeat and jump.

BILINEAR upsampling fills each gap by blending the two nearest samples in proportion to distance, so the
output ramps smoothly from one original value to the next. It produces the intermediate values nearest
cannot, turning the staircase into a slope. The cost is a slight blur; the gain is that a smooth region
stays smooth instead of breaking into blocks.

On this fixture a 4-sample signal is upscaled 4x. Nearest-neighbor produces a staircase whose largest
adjacent jump is 60 -- the full gap between two coarse samples, landing all at once -- and it emits only the
4 original values. Bilinear spreads that same gap over the 4 new pixels, so its largest adjacent jump is 15
(60 divided by the factor) and it emits 12 distinct values. This computes both and measures their
smoothness.

  --coarse     the low-resolution signal and the upscale factor
  --upsample   the nearest-neighbor vs bilinear output at high resolution
  --check      nearest jumps by the full coarse gap and copies only original values; bilinear smooths both

The coarse signal and factor are the fixture; every upsampled value is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "signal.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def out_len(coarse, factor):
    """Endpoint-aligned output length: the ends line up and the interior is filled."""
    return (len(coarse) - 1) * factor + 1


# ------------------------------------------------------------- the two upsamplers

def nearest(coarse, factor):
    """Copy each output position from the closest input sample -- a staircase of flat runs."""
    return [coarse[round(i / factor)] for i in range(out_len(coarse, factor))]


def bilinear(coarse, factor):
    """Blend the two nearest samples by distance -- a smooth ramp through intermediate values."""
    out = []
    for i in range(out_len(coarse, factor)):
        x = i / factor
        lo = int(x)
        hi = min(lo + 1, len(coarse) - 1)
        t = x - lo
        out.append(round(coarse[lo] * (1 - t) + coarse[hi] * t, 2))
    return out


def max_jump(signal):
    """The largest step between adjacent output samples -- big means blocky, small means smooth."""
    return round(max(abs(signal[i] - signal[i - 1]) for i in range(1, len(signal))), 2)


def max_coarse_gap(coarse):
    return max(abs(coarse[i] - coarse[i - 1]) for i in range(1, len(coarse)))


# ----------------------------------------------------------------- printing

def coarse_view(data):
    coarse, f = data["coarse"], data["factor"]
    print("COARSE — %d samples upscaled %dx to %d" % (len(coarse), f, out_len(coarse, f)))
    print("-" * 46)
    print("  input:  %s" % coarse)
    print("  largest gap between adjacent samples: %d" % max_coarse_gap(coarse))
    print("-" * 46)
    print("  upsampling must invent %d new samples between the originals." % (out_len(coarse, f) - len(coarse)))


def upsample_view(data):
    coarse, f = data["coarse"], data["factor"]
    nn = nearest(coarse, f)
    bl = bilinear(coarse, f)
    print("UPSAMPLE — nearest-neighbor vs bilinear at %dx" % f)
    print("-" * 62)
    print("  nearest:   %s" % nn)
    print("    max jump %g   distinct values %d" % (max_jump(nn), len(set(nn))))
    print("  bilinear:  %s" % bl)
    print("    max jump %g   distinct values %d" % (max_jump(bl), len(set(bl))))
    print("-" * 62)
    print("  nearest lands the whole gap in one step; bilinear spreads it over the new samples.")


def check(data):
    print("SELF-TEST — nearest jumps by the full coarse gap and copies only original values; bilinear smooths")
    print("-" * 92)
    coarse, f = data["coarse"], data["factor"]
    nn = nearest(coarse, f)
    bl = bilinear(coarse, f)
    gap = max_coarse_gap(coarse)

    nearest_jumps_full_gap = max_jump(nn) == gap
    print("  nearest's biggest jump is the full coarse gap = %s (%g = %d)" % (nearest_jumps_full_gap, max_jump(nn), gap))

    bilinear_smooths = max_jump(bl) == round(gap / f, 2)
    print("  bilinear cuts the biggest jump to gap/factor = %s (%g = %d/%d)" % (bilinear_smooths, max_jump(bl), gap, f))

    nearest_copies_only = set(nn) == set(coarse)
    print("  nearest emits only the original values = %s (%d distinct)" % (nearest_copies_only, len(set(nn))))

    bilinear_invents = len(set(bl)) > len(set(coarse))
    print("  bilinear emits intermediate values = %s (%d distinct vs %d)" % (bilinear_invents, len(set(bl)), len(set(coarse))))

    ok = nearest_jumps_full_gap and bilinear_smooths and nearest_copies_only and bilinear_invents
    print("-" * 92)
    print("SELF-TEST %s  nearest_jumps_full_gap=%s  bilinear_smooths=%s  nearest_copies_only=%s  bilinear_invents=%s"
          % ("PASS" if ok else "FAIL", nearest_jumps_full_gap, bilinear_smooths, nearest_copies_only, bilinear_invents))
    return ok


def main():
    p = argparse.ArgumentParser(description="Upsample with bilinear interpolation, not nearest-neighbor.")
    p.add_argument("--coarse", action="store_true")
    p.add_argument("--upsample", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("coarse=%d  factor=%d  out_len=%d  file=%s  (the signal is a fixture)"
          % (len(data["coarse"]), data["factor"], out_len(data["coarse"], data["factor"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.coarse:
        coarse_view(data)
    elif args.upsample:
        upsample_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
