#!/usr/bin/env python3
"""Dither when you quantize: error diffusion hides the banding a naive threshold creates.

Quantizing an image to few levels -- a 2-color palette, a 1-bit display, a low-bit export --
has to map every pixel to the nearest available level. Do it by a naive threshold and a
smooth gradient collapses into hard bands: a run of black, then a run of white, with a
visible edge where the ramp should be continuous. The gradient's local brightness is lost,
rounded away pixel by pixel with no memory.

Error diffusion keeps that memory. When a pixel rounds to a level, the ROUNDING ERROR (how
far it had to move) is carried forward and added to the next pixel, so a region that is 40%
bright gets roughly 40% white pixels sprinkled through it instead of a solid block. The two
available levels are the same; what changes is that the local average now tracks the true
gradient, so the eye sees a smooth ramp made of dots rather than a band. This measures the
banding a threshold creates and the local-average fidelity error diffusion restores.

  --quantize    the gradient under naive threshold vs error diffusion (Floyd-Steinberg, 1D)
  --error       banding (longest run) and local-average error for each method
  --check       both preserve total brightness; error diffusion kills the band and the local error

Stdlib only. Deterministic.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "gradient.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- quantizers

def nearest_level(value, levels):
    return min(levels, key=lambda L: abs(L - value))


def quantize_naive(pixels, levels):
    """Round each pixel to the nearest level, independently. No memory -> banding."""
    return [nearest_level(v, levels) for v in pixels]


def quantize_dither(pixels, levels):
    """Error diffusion: carry each pixel's rounding error forward to the next."""
    out, err = [], 0.0
    for v in pixels:
        target = v + err              # the pixel plus accumulated error
        q = nearest_level(target, levels)
        err = target - q              # what we could not represent, carried forward
        out.append(q)
    return out


# ------------------------------------------------------------- diagnostics

def longest_run(xs):
    """The longest run of identical values -- the signature of a band."""
    best = run = 1
    for i in range(1, len(xs)):
        run = run + 1 if xs[i] == xs[i - 1] else 1
        best = max(best, run)
    return best


def max_window_error(original, quantized, w=4):
    """Largest difference between the local averages of the original and the quantized."""
    worst = 0.0
    for i in range(len(original) - w + 1):
        mo = sum(original[i:i + w]) / w
        mq = sum(quantized[i:i + w]) / w
        worst = max(worst, abs(mo - mq))
    return worst


# ----------------------------------------------------------------- printing

def quantize_view(data):
    px, lv = data["pixels"], data["levels"]
    print("QUANTIZE — a smooth ramp to two levels %s" % lv)
    print("-" * 66)
    print("  input:   %s" % px)
    print("  naive:   %s" % quantize_naive(px, lv))
    print("  dither:  %s" % quantize_dither(px, lv))
    print("-" * 66)
    print("  naive splits into one black block and one white block; dither sprinkles them.")


def error_view(data):
    px, lv = data["pixels"], data["levels"]
    naive = quantize_naive(px, lv)
    dith = quantize_dither(px, lv)
    print("ERROR — banding (longest identical run) and local-average error")
    print("-" * 66)
    print("  method   longest_run   max_window_error   total_brightness")
    print("  naive    %-13d %-18.1f %d" % (longest_run(naive), max_window_error(px, naive), sum(naive)))
    print("  dither   %-13d %-18.1f %d" % (longest_run(dith), max_window_error(px, dith), sum(dith)))
    print("  input total brightness = %d" % sum(px))
    print("-" * 66)
    print("  same two levels, same total brightness; dither has no long run and half the local error.")


def check(data):
    print("SELF-TEST — both preserve brightness; error diffusion kills the band and the local error")
    print("-" * 66)
    px, lv = data["pixels"], data["levels"]
    naive = quantize_naive(px, lv)
    dith = quantize_dither(px, lv)

    binary = all(v in lv for v in dith) and all(v in lv for v in naive)
    print("  both outputs use only the available levels = %s" % binary)

    brightness_preserved = sum(dith) == sum(px)
    print("  error diffusion preserves total brightness = %s (%d == %d)" % (brightness_preserved, sum(dith), sum(px)))

    naive_bands = longest_run(naive) >= 8
    print("  naive quantization creates a band (long identical run) = %s (run %d)" % (naive_bands, longest_run(naive)))

    dither_no_band = longest_run(dith) < longest_run(naive)
    print("  error diffusion breaks the band = %s (run %d < %d)" % (dither_no_band, longest_run(dith), longest_run(naive)))

    lower_local_error = max_window_error(px, dith) < max_window_error(px, naive)
    print("  error diffusion has lower local-average error = %s (%.1f < %.1f)"
          % (lower_local_error, max_window_error(px, dith), max_window_error(px, naive)))

    ok = binary and brightness_preserved and naive_bands and dither_no_band and lower_local_error
    print("-" * 66)
    print("SELF-TEST %s  binary=%s  brightness=%s  naive_bands=%s  dither_no_band=%s  lower_local_error=%s"
          % ("PASS" if ok else "FAIL", binary, brightness_preserved, naive_bands, dither_no_band, lower_local_error))
    return ok


def main():
    p = argparse.ArgumentParser(description="Dithering by error diffusion vs naive threshold quantization.")
    p.add_argument("--quantize", action="store_true")
    p.add_argument("--error", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("pixels=%d  levels=%s  file=%s  (gradient is a fixture)" % (len(data["pixels"]), data["levels"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.quantize:
        quantize_view(data)
    elif args.error:
        error_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
