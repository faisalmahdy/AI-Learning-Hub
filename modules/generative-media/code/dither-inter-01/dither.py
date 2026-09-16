"""Diffuse the quantization error to neighbors -- rounding each pixel alone flattens a region and loses its brightness.

Reducing an image to a few levels -- printing to a black-and-white device, shrinking to a tiny palette -- means mapping
each pixel to the nearest available level. Done pixel by pixel in isolation, that rounding throws away everything between
the levels: a smooth mid-gray region, with no value close to black or white, rounds every pixel the same way and becomes
a solid block of one level. The detail is gone, and worse, the average brightness is wrong -- a region that was 50% gray
can become 100% white, because every pixel individually rounded up. Naive quantization is locally 'correct' (each pixel
went to its nearest level) and globally a disaster (the region's tone is destroyed).

Error-diffusion dithering fixes this by not letting the rounding error vanish. When a pixel is quantized, the difference
between its true value and the level it was forced to -- the quantization error -- is CARRIED FORWARD and added to the
neighboring pixels not yet processed. So if a 128 pixel is forced up to 255 (an error of -127, meaning we output 127 too
much light), that -127 is pushed onto the next pixel, which now sees 128 - 127 = 1 and rounds to 0 (black), compensating.
Over a region the pushed-forward errors cancel, so the LOCAL AVERAGE of the output matches the input even though every
individual pixel is pure black or white. The mid-gray does not become a flat block; it becomes a fine black-and-white
pattern that averages to mid-gray, which is exactly how newspapers print photographs with only black ink. (Real
2-D dithering, Floyd-Steinberg, spreads the error to several neighbors with fixed weights; this is the 1-D core of it.)

The trade-off is that dithering replaces smooth tone with texture (visible dot patterns) and can add noise, but it
preserves the information -- brightness and gradients survive as patterns -- where naive thresholding discards it. It is
the same 'conserve the quantity' idea as many numerical methods: don't drop the residual, carry it.

On this fixture the row is a uniform mid-gray 128. Naive quantization sends every pixel to 255 -- solid white, average
255, when the input averaged 128. Error diffusion produces the alternating pattern [255, 0, 255, 0, 255, 0], average
127.5 -- essentially the true 128. This computes both.

  --quantize   the row quantized naively vs by error diffusion, with the output averages -- 255 (wrong) vs 127.5 (right)
  --trace      the error-diffusion step by step: each pixel's carried-in error, its output level, and the error pushed forward
  --check      naive quantization flattens the region and wrong-brightness; error diffusion preserves the average as a pattern

The row and levels are the fixture; every quantized output and average is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "dither.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def nearest_level(value, levels):
    """Round a value to the nearest available output level."""
    return min(levels, key=lambda L: abs(value - L))


def naive_quantize(row, levels):
    """Round each pixel to its nearest level independently -- no memory of the error."""
    return [nearest_level(v, levels) for v in row]


def diffuse_quantize(row, levels):
    """Error diffusion: quantize each pixel, then push its quantization error onto the next pixel."""
    work = [float(v) for v in row]
    out = []
    for i in range(len(work)):
        q = nearest_level(work[i], levels)
        error = work[i] - q
        out.append(q)
        if i + 1 < len(work):
            work[i + 1] += error
    return out


def average(xs):
    return sum(xs) / len(xs)


# ----------------------------------------------------------------- printing

def quantize_view(data):
    row, levels = data["row"], data["levels"]
    n = naive_quantize(row, levels)
    d = diffuse_quantize(row, levels)
    print("QUANTIZE — a mid-gray %s row to levels %s" % (row, levels))
    print("-" * 60)
    print("  input            = %s   avg %.1f" % (row, average(row)))
    print("  naive quantize   = %s   avg %.1f   <- solid, wrong brightness" % (n, average(n)))
    print("  error diffusion  = %s   avg %.1f   <- pattern, right brightness" % (d, average(d)))
    print("-" * 60)
    print("  naive is off by %.1f; diffusion is off by %.1f." % (abs(average(n) - average(row)), abs(average(d) - average(row))))


def trace_view(data):
    row, levels = data["row"], data["levels"]
    work = [float(v) for v in row]
    print("TRACE — error diffusion carries each pixel's error forward")
    print("-" * 62)
    print("  pixel  sees (value+carried)   output   error pushed forward")
    for i in range(len(work)):
        q = nearest_level(work[i], levels)
        error = work[i] - q
        print("  %-5d  %-19.1f  %-6d   %+.1f" % (i, work[i], q, error))
        if i + 1 < len(work):
            work[i + 1] += error
    print("-" * 62)
    print("  the error alternates sign, so outputs alternate 255/0 and the average stays ~128.")


def check(data):
    print("SELF-TEST — naive quantization flattens the region and gets the brightness wrong; error diffusion preserves it as a pattern")
    print("-" * 120)
    row, levels = data["row"], data["levels"]
    inp_avg = average(row)
    n = naive_quantize(row, levels)
    d = diffuse_quantize(row, levels)

    naive_flattens = len(set(n)) == 1
    print("  naive output is a single flat level = %s (%s)" % (naive_flattens, n))

    naive_brightness_wrong = abs(average(n) - inp_avg) > 50
    print("  naive average brightness is far from the input = %s (%.1f vs %.1f)" % (naive_brightness_wrong, average(n), inp_avg))

    diffusion_preserves = abs(average(d) - inp_avg) < 1
    print("  diffusion average brightness matches the input = %s (%.1f vs %.1f)" % (diffusion_preserves, average(d), inp_avg))

    diffusion_has_pattern = len(set(d)) > 1
    print("  diffusion output is a pattern, not a flat block = %s (%s)" % (diffusion_has_pattern, d))

    diffusion_beats_naive = abs(average(d) - inp_avg) < abs(average(n) - inp_avg)
    print("  diffusion is closer to the true brightness than naive = %s (%.1f < %.1f error)"
          % (diffusion_beats_naive, abs(average(d) - inp_avg), abs(average(n) - inp_avg)))

    ok = naive_flattens and naive_brightness_wrong and diffusion_preserves and diffusion_has_pattern and diffusion_beats_naive
    print("-" * 120)
    print("SELF-TEST %s  naive_flattens=%s  naive_brightness_wrong=%s  diffusion_preserves=%s  diffusion_has_pattern=%s  diffusion_beats_naive=%s"
          % ("PASS" if ok else "FAIL", naive_flattens, naive_brightness_wrong, diffusion_preserves, diffusion_has_pattern, diffusion_beats_naive))
    return ok


def main():
    p = argparse.ArgumentParser(description="Error-diffusion dithering: quantizing each pixel to the nearest of a few levels independently flattens a region and loses its average brightness; carrying each pixel's quantization error forward to its neighbors (dithering) preserves the local average, rendering a tone as a black/white pattern instead of a solid block.")
    p.add_argument("--quantize", action="store_true")
    p.add_argument("--trace", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("row=%s  levels=%s  file=%s  (the row and levels are a fixture)"
          % (data["row"], data["levels"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.quantize:
        quantize_view(data)
    elif args.trace:
        trace_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
