#!/usr/bin/env python3
"""Downsample an image row -- and low-pass filter first, or fine texture aliases.

Halving an image's resolution means turning two pixels into one. The obvious way is
to keep every other pixel and throw the rest away. That is decimation, and on any
detail finer than the new pixel grid it is wrong: the detail does not vanish, it
ALIASES -- folds down into a false low-frequency artifact that was never in the
scene. A one-pixel checkerboard texture, sampled every other pixel, always lands on
the same phase, so instead of averaging to gray it becomes a fake uniform brightness
shift. The scene's real content (a smooth gradient) comes back corrupted.

The fix is a low-pass filter before you decimate: average each group of pixels so the
fine texture cancels and only the coarse structure survives. This is why every
correct image resize (and every audio downsample) filters first. Here a box filter
-- average each pair -- recovers the gradient exactly while decimation carries a
constant aliasing error. This measures both against the ideal downsample.

  --downsample   the row halved by naive decimation vs box-filter-then-decimate
  --error        each method's error against the ideal (gradient-only) downsample
  --check        the filtered result matches the ideal; naive carries an alias error

Stdlib only. Deterministic.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "signal.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the downsamplers

def decimate(row, factor):
    """Naive: keep every `factor`-th pixel, discard the rest. No filtering -> aliasing."""
    return [row[i] for i in range(0, len(row), factor)]


def box_downsample(row, factor):
    """Correct: average each group of `factor` pixels (low-pass), then that IS the pixel."""
    out = []
    for i in range(0, len(row), factor):
        group = row[i:i + factor]
        out.append(sum(group) / len(group))
    return out


def ideal_downsample(gradient, factor):
    """The right answer: the scene (gradient only, no texture) averaged per output pixel."""
    return box_downsample(gradient, factor)


# ------------------------------------------------------------- error

def max_abs_error(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def alias_energy(result, ideal):
    """Total squared deviation of a downsample from the ideal -- the aliased content."""
    return sum((x - y) ** 2 for x, y in zip(result, ideal))


# ----------------------------------------------------------------- printing

def downsample_view(data):
    row, factor, grad = data["row"], data["factor"], data["gradient"]
    print("DOWNSAMPLE — halve the row: naive decimation vs box filter (factor=%d)" % factor)
    print("-" * 66)
    print("  input row (%d px): %s" % (len(row), row))
    print("  ideal (scene avg): %s" % ideal_downsample(grad, factor))
    print("  naive decimate:    %s" % decimate(row, factor))
    print("  box filtered:      %s" % [round(x, 1) for x in box_downsample(row, factor)])
    print("-" * 66)
    print("  the checker texture aliases to a constant +offset under naive decimation.")


def error_view(data):
    row, factor, grad = data["row"], data["factor"], data["gradient"]
    ideal = ideal_downsample(grad, factor)
    naive = decimate(row, factor)
    box = box_downsample(row, factor)
    print("ERROR — each method against the ideal (gradient-only) downsample")
    print("-" * 66)
    print("  naive decimate: max abs error = %.1f   alias energy = %.1f"
          % (max_abs_error(naive, ideal), alias_energy(naive, ideal)))
    print("  box filtered:   max abs error = %.1f   alias energy = %.1f"
          % (max_abs_error(box, ideal), alias_energy(box, ideal)))
    print("-" * 66)
    print("  box filtering cancels the texture; decimation folds it into the output.")


def check(data):
    print("SELF-TEST — box filtering matches the ideal; naive decimation aliases")
    print("-" * 66)
    row, factor, grad = data["row"], data["factor"], data["gradient"]
    ideal = ideal_downsample(grad, factor)

    box = box_downsample(row, factor)
    box_exact = max_abs_error(box, ideal) < 1e-9
    print("  box filter recovers the ideal exactly = %s (max err %.4f)"
          % (box_exact, max_abs_error(box, ideal)))

    naive = decimate(row, factor)
    naive_aliases = max_abs_error(naive, ideal) > 3.0
    print("  naive decimation carries a large alias error = %s (max err %.1f)"
          % (naive_aliases, max_abs_error(naive, ideal)))

    # The aliased error is systematic, not random: same sign/size at every output pixel.
    errs = [naive[i] - ideal[i] for i in range(len(ideal))]
    systematic = max(errs) - min(errs) < 1e-9
    print("  the alias error is a systematic offset (a false brightness shift) = %s (%.1f everywhere)"
          % (systematic, errs[0]))

    box_removes_energy = alias_energy(box, ideal) < alias_energy(naive, ideal)
    print("  box filtering removes the aliased energy = %s (%.1f < %.1f)"
          % (box_removes_energy, alias_energy(box, ideal), alias_energy(naive, ideal)))

    ok = box_exact and naive_aliases and systematic and box_removes_energy
    print("-" * 66)
    print("SELF-TEST %s  box_exact=%s  naive_aliases=%s  systematic=%s  box_removes_energy=%s"
          % ("PASS" if ok else "FAIL", box_exact, naive_aliases, systematic, box_removes_energy))
    return ok


def main():
    p = argparse.ArgumentParser(description="Image downsampling, aliasing, and the low-pass fix.")
    p.add_argument("--downsample", action="store_true")
    p.add_argument("--error", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("row=%d px  factor=%d  file=%s  (signal is a fixture)"
          % (len(data["row"]), data["factor"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.downsample:
        downsample_view(data)
    elif args.error:
        error_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
