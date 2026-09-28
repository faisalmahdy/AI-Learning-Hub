"""Scale the initial weights by 1/sqrt(fan_in), or the signal explodes or vanishes through depth.

A linear layer multiplies its input by a matrix of random initial weights. For iid weights the output's
standard deviation is the input's std times sqrt(fan_in) * w_std -- so that factor is a per-layer GAIN
applied to the signal's magnitude. Stack L layers and the magnitude is multiplied by that gain L times: it
grows as gain**L. If the gain is even slightly above 1, gain**L explodes with depth; if slightly below 1, it
decays to nothing. A deep network initialized with an off-scale w_std produces activations that are either
astronomically large (and overflow, or saturate every nonlinearity) or effectively zero (and no gradient
flows) before training takes a single step. The network is broken at birth, and no learning rate fixes it.

The fix is to choose w_std so the per-layer gain is exactly 1: set w_std = 1/sqrt(fan_in), so
sqrt(fan_in) * w_std = 1 and the signal's magnitude is preserved layer after layer. This is the core of the
LeCun/Xavier/He initialization family (He adds a sqrt(2) for the ReLU's halving). The point is that the
right scale is not a small tweak -- it is the difference between a signal that survives depth and one that
does not, and the effect compounds exponentially, so it is invisible at one layer and catastrophic at fifty.

On this fixture fan_in is 100 (so sqrt is 10) and the network is 10 layers deep. w_std=0.1 gives a gain of
exactly 1.0 and the magnitude stays 1.0. w_std=0.3 gives a gain of 3.0 and the signal reaches 3**10 ~ 59049.
w_std=0.03 gives a gain of 0.3 and it decays to 0.3**10 ~ 6e-6. This computes all three.

  --propagate  the signal magnitude at each layer for each initialization
  --gain       the per-layer gain and the final magnitude gain**depth for each
  --check      the scaled init preserves the signal; too-big explodes and too-small vanishes with depth

The fan_in, depth, and init scales are the fixture; every magnitude is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "init.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def gain(fan_in, w_std):
    """The factor a single linear layer multiplies the signal's std by."""
    return math.sqrt(fan_in) * w_std


def propagate(input_std, fan_in, w_std, depth):
    """The signal magnitude after each layer: multiply by the gain, depth times."""
    g = gain(fan_in, w_std)
    mags, m = [input_std], input_std
    for _ in range(depth):
        m *= g
        mags.append(m)
    return mags


def scaled_std(fan_in):
    """The initialization that makes the per-layer gain exactly 1."""
    return 1.0 / math.sqrt(fan_in)


# ----------------------------------------------------------------- printing

def propagate_view(data):
    fan_in, depth, x0 = data["fan_in"], data["depth"], data["input_std"]
    print("PROPAGATE — signal magnitude by layer (fan_in %d, depth %d, input %.1f)" % (fan_in, depth, x0))
    print("-" * 72)
    print("  layer:      " + "".join("%9d" % i for i in range(0, depth + 1, 2)))
    for name, w_std in data["inits"].items():
        mags = propagate(x0, fan_in, w_std, depth)
        row = "".join("%9.2e" % mags[i] for i in range(0, depth + 1, 2))
        print("  %-10s %s" % (name, row))
    print("-" * 72)
    print("  only the scaled init holds steady; the others run away or die out.")


def gain_view(data):
    fan_in, depth, x0 = data["fan_in"], data["depth"], data["input_std"]
    print("GAIN — per-layer gain and final magnitude after %d layers" % depth)
    print("-" * 64)
    for name, w_std in data["inits"].items():
        g = gain(fan_in, w_std)
        final = propagate(x0, fan_in, w_std, depth)[-1]
        print("  %-10s w_std %.3f   gain %.2f   final %.3e" % (name, w_std, g, final))
    print("-" * 64)
    print("  gain**depth is the whole story: 1 stays, >1 explodes, <1 vanishes.")


def check(data):
    print("SELF-TEST — the scaled init preserves the signal; too-big explodes and too-small vanishes with depth")
    print("-" * 104)
    fan_in, depth, x0 = data["fan_in"], data["depth"], data["input_std"]
    inits = data["inits"]

    gain_is_sqrt_fanin_times_wstd = abs(gain(fan_in, inits["scaled"]) - math.sqrt(fan_in) * inits["scaled"]) < 1e-12
    print("  the per-layer gain is sqrt(fan_in)*w_std = %s" % gain_is_sqrt_fanin_times_wstd)

    scaled_wstd_is_one_over_sqrt = abs(inits["scaled"] - scaled_std(fan_in)) < 1e-12
    print("  the scaled w_std equals 1/sqrt(fan_in) = %s (%.3f vs %.3f)" % (scaled_wstd_is_one_over_sqrt, inits["scaled"], scaled_std(fan_in)))

    scaled_final = propagate(x0, fan_in, inits["scaled"], depth)[-1]
    scaled_preserves = abs(scaled_final - x0) < 1e-9
    print("  the scaled init preserves the magnitude through depth = %s (%.3f -> %.3f)" % (scaled_preserves, x0, scaled_final))

    big_final = propagate(x0, fan_in, inits["too_big"], depth)[-1]
    big_explodes = big_final > x0 * 100
    print("  the too-big init explodes with depth = %s (final %.3e)" % (big_explodes, big_final))

    small_final = propagate(x0, fan_in, inits["too_small"], depth)[-1]
    small_vanishes = small_final < x0 / 100
    print("  the too-small init vanishes with depth = %s (final %.3e)" % (small_vanishes, small_final))

    ok = gain_is_sqrt_fanin_times_wstd and scaled_wstd_is_one_over_sqrt and scaled_preserves and big_explodes and small_vanishes
    print("-" * 104)
    print("SELF-TEST %s  gain_is_sqrt_fanin_times_wstd=%s  scaled_wstd_is_one_over_sqrt=%s  scaled_preserves=%s  big_explodes=%s  small_vanishes=%s"
          % ("PASS" if ok else "FAIL", gain_is_sqrt_fanin_times_wstd, scaled_wstd_is_one_over_sqrt, scaled_preserves, big_explodes, small_vanishes))
    return ok


def main():
    p = argparse.ArgumentParser(description="Scale initial weights by 1/sqrt(fan_in) so the signal survives depth.")
    p.add_argument("--propagate", action="store_true")
    p.add_argument("--gain", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("fan_in=%d  depth=%d  input_std=%.1f  file=%s  (the fan_in, depth, and inits are a fixture)"
          % (data["fan_in"], data["depth"], data["input_std"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.propagate:
        propagate_view(data)
    elif args.gain:
        gain_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
