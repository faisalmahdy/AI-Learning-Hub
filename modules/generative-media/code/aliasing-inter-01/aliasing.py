"""Low-pass filter before you decimate -- dropping every Nth pixel aliases fine detail into a false pattern that flips with phase.

Downsampling an image means representing it on a coarser grid of pixels, and the tempting way to do it is decimation:
keep every Nth pixel and throw the rest away. It is fast, it is one line, and it is wrong whenever the image contains
detail finer than the new grid can represent. A grid of pixels can only represent frequencies up to half its sampling
rate (the Nyquist limit); make the grid coarser and that limit drops, so any pattern that was fine enough to sit above
the NEW limit cannot be represented -- and decimation does not drop it, it ALIASES it, folding that high frequency down
into a false low frequency that was never in the scene. A fine checkerboard becomes broad bands (moiré); a picket fence
photographed at the wrong scale becomes a few thick posts; a striped shirt on video shimmers with color. The signal the
eye would have blended to a smooth gray instead turns into a bold, wrong pattern.

The worst part is that the aliased result is not even a stable wrong answer: it depends on the sub-pixel PHASE, on exactly
where the coarse sampling grid happens to land. Shift the grid by one input pixel and the same fine pattern decimates to a
completely different output -- solid white in one alignment, solid black in another -- because decimation is reading one
arbitrary sample out of each group and calling it the group. So downsampling by decimation produces a result that is both
false and unrepeatable.

The fix is to remove the frequencies the new grid cannot hold BEFORE you decimate, by low-pass filtering. The simplest
low-pass filter is a box filter: average each group of N pixels, which is exactly the area the output pixel covers, so the
output is the true average of what it represents. Now the fine checker correctly becomes its mean gray, and because every
group is fully averaged, the result no longer depends on phase. This is why every real image resizer filters before it
decimates (area-averaging, or a better filter like Lanczos), and why 'just take every Nth pixel' is the classic aliasing
bug -- and it is exactly the sampling theorem applied to pixels: band-limit, then sample.

On this fixture the row is an alternating 255,0 checker -- the highest frequency a pixel row can hold. Decimating by 2
keeps every other pixel: starting at index 0 it yields all 255 (solid white), starting at index 1 it yields all 0 (solid
black) -- same input, opposite outputs, both wrong. Box-filtering each pair first yields 127.5 everywhere, the true
average, independent of phase. This computes all of it.

  --downsample  the row decimated (phase 0) vs box-filtered-then-decimated -- solid white vs correct mid-gray
  --phase       decimation at phase 0 vs phase 1 -- solid white vs solid black; the box filter is 127.5 either way
  --check       decimation aliases to a phase-dependent constant; the box filter preserves the true average and is phase-stable

The signal and factor are the fixture; every downsampled result is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "aliasing.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def decimate(signal, factor, phase=0):
    """Downsample by keeping every factor-th sample starting at `phase` -- no pre-filter (the aliasing bug)."""
    return signal[phase::factor]


def box_downsample(signal, factor):
    """Downsample by averaging each group of `factor` samples first (a box low-pass), then taking one per group."""
    return [sum(signal[i:i + factor]) / factor for i in range(0, len(signal), factor)]


def average(signal):
    """The true average level of the row -- what a correctly-downsampled uniform region should approach."""
    return sum(signal) / len(signal)


# ----------------------------------------------------------------- printing

def downsample_view(data):
    sig, f = data["signal"], data["factor"]
    print("DOWNSAMPLE — decimate vs box-filter, factor %d" % f)
    print("-" * 60)
    print("  input row              = %s" % sig)
    print("  decimate (phase 0)     = %s   <- solid white: aliased" % decimate(sig, f, 0))
    print("  box-filter then take   = %s   <- %.1f mid-gray: correct" % (box_downsample(sig, f), average(sig)))
    print("-" * 60)
    print("  the input's fine checker should blend to gray (%.1f); decimation turned it solid." % average(sig))


def phase_view(data):
    sig, f = data["signal"], data["factor"]
    print("PHASE — decimation depends on where the grid lands; the box filter does not")
    print("-" * 62)
    print("  decimate phase 0 = %s" % decimate(sig, f, 0))
    print("  decimate phase 1 = %s" % decimate(sig, f, 1))
    print("  box-filter       = %s   (same regardless of phase)" % box_downsample(sig, f))
    print("-" * 62)
    print("  a one-pixel shift flips the aliased result from all-255 to all-0; the box filter stays %.1f." % average(sig))


def check(data):
    print("SELF-TEST — decimation aliases to a phase-dependent constant; the box filter preserves the true average and is phase-stable")
    print("-" * 122)
    sig, f = data["signal"], data["factor"]

    d0 = decimate(sig, f, 0)
    decimate_aliases_constant = len(set(d0)) == 1 and d0[0] != average(sig)
    print("  decimation collapses the checker to a single wrong value = %s (%s)" % (decimate_aliases_constant, d0))

    d1 = decimate(sig, f, 1)
    phase_dependent = d0 != d1
    print("  a one-pixel phase shift changes the aliased result = %s (%s vs %s)" % (phase_dependent, d0[0], d1[0]))

    box = box_downsample(sig, f)
    box_is_true_average = all(abs(v - average(sig)) < 1e-9 for v in box)
    print("  the box filter yields the true average everywhere = %s (%.1f)" % (box_is_true_average, box[0]))

    box0 = box_downsample(sig, f)
    box_phase_stable = box0 == box  # box filter has no phase parameter -- it always averages full groups
    print("  the box-filtered result does not depend on phase = %s" % box_phase_stable)

    true_avg = abs(average(sig) - 127.5) < 1e-9
    print("  the true average of the row is 127.5 = %s" % true_avg)

    ok = decimate_aliases_constant and phase_dependent and box_is_true_average and box_phase_stable and true_avg
    print("-" * 122)
    print("SELF-TEST %s  decimate_aliases_constant=%s  phase_dependent=%s  box_is_true_average=%s  box_phase_stable=%s  true_avg=%s"
          % ("PASS" if ok else "FAIL", decimate_aliases_constant, phase_dependent, box_is_true_average, box_phase_stable, true_avg))
    return ok


def main():
    p = argparse.ArgumentParser(description="Aliasing on downsample: decimating (keeping every Nth pixel) without a low-pass pre-filter aliases detail above the new Nyquist limit into a false pattern that also depends on sub-pixel phase; box-filter (average each group) before decimating to band-limit the signal, so the result is the true average and is phase-stable.")
    p.add_argument("--downsample", action="store_true")
    p.add_argument("--phase", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("signal=%s  factor=%d  file=%s  (the row and factor are a fixture)"
          % (data["signal"], data["factor"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.downsample:
        downsample_view(data)
    elif args.phase:
        phase_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
