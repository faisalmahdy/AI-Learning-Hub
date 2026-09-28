"""Resample by walking the OUTPUT pixels and pulling from the source -- forward-mapping the source leaves holes.

Every geometric operation on an image -- scaling, rotating, warping, lens correction -- is a resample: you have pixels on
one grid and you need pixel values on a different grid. There are two directions to implement it, and only one of them
works. The FORWARD direction is the one people reach for first because it matches how you think about the transform: take
each SOURCE pixel, compute where it lands in the output, and write it there. The problem is that a geometric mapping
almost never sends source pixels onto output pixels one-to-one. When you enlarge an image, there are more output pixels
than source pixels, so some output pixels are never the landing spot of any source pixel -- they are left as HOLES, unset,
showing through as black speckle or garbage. When you shrink an image, several source pixels map to the same output pixel,
so they collide and all but the last are lost. Forward mapping's coverage of the output depends on the transform, and for
anything but an exact integer copy it is wrong.

The BACKWARD (inverse) direction fixes this by iterating over the thing you actually need to fill: the OUTPUT. For each
output pixel, apply the INVERSE transform to find the source location it came from, and sample the source there. Because
you visit every output pixel exactly once, every output pixel gets a value -- there are no holes and no collisions, by
construction. When the inverse maps an output pixel to a fractional source location (which is the normal case for a
rotation or a non-integer scale), you interpolate between the surrounding source pixels; the point is that the loop is
over outputs, so coverage is guaranteed regardless of the transform. This is why essentially every real image resampler
-- every rotate, every resize, every texture lookup on a GPU -- is written as a backward map: 'for each output pixel, where
did it come from?', never 'for each input pixel, where does it go?'.

The rule: implement a geometric resample as a backward map -- loop over the output pixels and, for each, invert the
transform to find and sample its source location -- because forward-mapping the source pixels leaves holes when you
enlarge and collisions when you shrink, so output coverage is only guaranteed when the loop runs over the output.

On this fixture a 4-pixel row is upscaled 2x to 8 pixels. Forward mapping writes source i to output 2i, so only outputs
0,2,4,6 are written and outputs 1,3,5,7 are holes. Backward mapping reads, for each output j, source j//2, so all 8
outputs are filled: [10,10,20,20,30,30,40,40]. This computes both.

  --resample   the forward output (with holes shown as '__') vs the backward output (fully filled), side by side
  --map        the index mapping each way: forward writes 4 of 8 outputs; backward reads a source for all 8 outputs
  --check      forward mapping leaves holes on the upscale; backward mapping fills every output pixel

The row and scale are the fixture; every resampled value and hole is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "backmap.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def forward_map(row, scale):
    """Walk the SOURCE: write each source pixel i to output i*scale. Outputs never written stay None (holes)."""
    out_len = len(row) * scale
    out = [None] * out_len
    for i, value in enumerate(row):
        out[i * scale] = value
    return out


def backward_map(row, scale):
    """Walk the OUTPUT: for each output j, read source j//scale (its inverse-mapped location) and sample it."""
    out_len = len(row) * scale
    out = []
    for j in range(out_len):
        src = min(j // scale, len(row) - 1)
        out.append(row[src])
    return out


def holes(out):
    return [j for j, v in enumerate(out) if v is None]


# ----------------------------------------------------------------- printing

def show(out):
    return "[" + ", ".join("__" if v is None else str(v) for v in out) + "]"


def resample_view(data):
    row, scale = data["row"], data["scale"]
    fwd = forward_map(row, scale)
    bwd = backward_map(row, scale)
    print("RESAMPLE — upscale %s by %dx to %d pixels" % (row, scale, len(row) * scale))
    print("-" * 62)
    print("  forward  (walk source) = %s" % show(fwd))
    print("    ... holes at outputs %s -- never written" % holes(fwd))
    print("  backward (walk output) = %s" % show(bwd))
    print("    ... no holes -- every output pixel sampled a source")
    print("-" * 62)
    print("  forward wrote %d of %d outputs; backward filled all %d." % (len(row), len(fwd), len(bwd)))


def map_view(data):
    row, scale = data["row"], data["scale"]
    out_len = len(row) * scale
    print("MAP — the index mapping each direction")
    print("-" * 58)
    print("  FORWARD: source i -> output i*%d  (only these outputs written)" % scale)
    for i in range(len(row)):
        print("    source %d (=%d) -> output %d" % (i, row[i], i * scale))
    print("  BACKWARD: output j -> source j//%d  (every output reads one source)" % scale)
    for j in range(out_len):
        src = min(j // scale, len(row) - 1)
        print("    output %d <- source %d (=%d)" % (j, src, row[src]))
    print("-" * 58)
    print("  forward touches %d outputs; backward touches all %d." % (len(row), out_len))


def check(data):
    print("SELF-TEST — forward mapping leaves holes on the upscale; backward mapping fills every output pixel")
    print("-" * 98)
    row, scale = data["row"], data["scale"]
    fwd = forward_map(row, scale)
    bwd = backward_map(row, scale)
    out_len = len(row) * scale

    forward_has_holes = len(holes(fwd)) > 0
    print("  forward output has holes = %s (at %s)" % (forward_has_holes, holes(fwd)))

    forward_wrote_only_source_count = sum(1 for v in fwd if v is not None) == len(row)
    print("  forward wrote only as many outputs as there are sources = %s (%d of %d)"
          % (forward_wrote_only_source_count, len(row), out_len))

    backward_no_holes = len(holes(bwd)) == 0
    print("  backward output has no holes = %s" % backward_no_holes)

    backward_fills_all = len(bwd) == out_len and all(v is not None for v in bwd)
    print("  backward filled all %d outputs = %s" % (out_len, backward_fills_all))

    backward_correct = bwd == [10, 10, 20, 20, 30, 30, 40, 40]
    print("  backward output is the expected 2x nearest upscale = %s (%s)" % (backward_correct, show(bwd)))

    ok = forward_has_holes and forward_wrote_only_source_count and backward_no_holes and backward_fills_all and backward_correct
    print("-" * 98)
    print("SELF-TEST %s  forward_has_holes=%s  forward_wrote_only_source_count=%s  backward_no_holes=%s  backward_fills_all=%s  backward_correct=%s"
          % ("PASS" if ok else "FAIL", forward_has_holes, forward_wrote_only_source_count, backward_no_holes, backward_fills_all, backward_correct))
    return ok


def main():
    p = argparse.ArgumentParser(description="Backward mapping for resampling: implement a geometric resample by looping over the output pixels and inverting the transform to sample each one's source location, because forward-mapping the source pixels leaves holes when enlarging and collisions when shrinking -- output coverage is only guaranteed when the loop runs over the output.")
    p.add_argument("--resample", action="store_true")
    p.add_argument("--map", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("row=%s  scale=%d  file=%s  (the row and scale are a fixture)" % (data["row"], data["scale"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.resample:
        resample_view(data)
    elif args.map:
        map_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
