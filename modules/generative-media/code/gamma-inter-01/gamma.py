"""Gamma-encode before quantizing, or linear codes waste the brights and band the shadows.

The eye is not a light meter. It is far more sensitive to a change in dark tones than the same change in
bright tones -- doubling the light in a dim room is obvious, doubling it in daylight is barely noticeable.
Perceived lightness is roughly intensity raised to 1/gamma (gamma about 2.2). So when you have only a
limited number of codes to represent brightness -- 256 in an 8-bit image, or 8 in this toy -- how you
space them across intensity decides whether the picture looks smooth or banded.

Space the codes evenly in physical intensity (LINEAR coding) and you get it backwards: the brights, where
the eye can barely tell codes apart, get finely spaced codes that are wasted, while the darks, where the
eye is acute, get coarsely spaced codes with large perceptual gaps between them -- visible banding in the
shadows. Space the codes evenly in perceived lightness (GAMMA coding: store intensity^(1/gamma)) and every
step looks the same size, so the codes go where the eye needs them and there is no banding. This is why
image formats store gamma-encoded values, not linear ones.

On this fixture 8 codes cover the brightness range. Linear coding's darkest step is a 0.413 jump in
perceived lightness -- a glaring band -- while its brightest step is a wasted 0.068. Gamma coding's steps
are a uniform 0.143 everywhere. Same 8 codes; gamma spends them where perception is. This computes both.

  --codes      the intensity of each code, linear vs gamma spacing
  --steps      the perceived-lightness step between adjacent codes for each coding
  --check      linear coding bands the darks (a large step); gamma coding steps are uniform

The gamma and code count are the fixture; every perceptual step is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "coding.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def lightness(intensity, gamma):
    """Perceived lightness of a physical intensity -- the eye's non-linear response."""
    return intensity ** (1 / gamma)


def linear_codes(n):
    """Codes spaced evenly in physical intensity."""
    return [i / (n - 1) for i in range(n)]


def gamma_codes(n, gamma):
    """Codes spaced evenly in perceived lightness -- their intensities are lightness^gamma."""
    return [(i / (n - 1)) ** gamma for i in range(n)]


def perceptual_steps(intensities, gamma):
    """The jump in perceived lightness between adjacent codes -- big jumps are visible banding."""
    L = [lightness(x, gamma) for x in intensities]
    return [L[i] - L[i - 1] for i in range(1, len(L))]


# ----------------------------------------------------------------- printing

def codes_view(data):
    n, g = data["n_codes"], data["gamma"]
    print("CODES — intensity of each of the %d codes (gamma %.1f)" % (n, g))
    print("-" * 54)
    print("  linear:  %s" % [round(x, 3) for x in linear_codes(n)])
    print("  gamma:   %s" % [round(x, 3) for x in gamma_codes(n, g)])
    print("-" * 54)
    print("  gamma coding packs codes into the darks, where the eye is sensitive.")


def steps_view(data):
    n, g = data["n_codes"], data["gamma"]
    lin = perceptual_steps(linear_codes(n), g)
    gam = perceptual_steps(gamma_codes(n, g), g)
    print("STEPS — perceived-lightness jump between adjacent codes")
    print("-" * 58)
    print("  linear:  %s   max %.3f" % ([round(x, 4) for x in lin], max(lin)))
    print("  gamma:   %s   max %.3f" % ([round(x, 4) for x in gam], max(gam)))
    print("-" * 58)
    print("  linear's biggest jump is the darkest step (banding); gamma's are equal.")


def check(data):
    print("SELF-TEST — linear coding bands the darks with a large step; gamma coding's steps are uniform")
    print("-" * 88)
    n, g = data["n_codes"], data["gamma"]
    lin = perceptual_steps(linear_codes(n), g)
    gam = perceptual_steps(gamma_codes(n, g), g)

    linear_bands = max(lin) > 2 * max(gam)
    print("  linear's worst perceptual step is far larger than gamma's = %s (%.3f vs %.3f)" % (linear_bands, max(lin), max(gam)))

    worst_is_darkest = lin.index(max(lin)) == 0
    print("  linear's worst step is the darkest one = %s (step %d of %d)" % (worst_is_darkest, lin.index(max(lin)) + 1, len(lin)))

    gamma_uniform = max(gam) - min(gam) < 1e-9
    print("  gamma's perceptual steps are all equal = %s (%.3f)" % (gamma_uniform, gam[0]))

    same_codes = len(linear_codes(n)) == len(gamma_codes(n, g)) == n
    print("  both codings use the same %d codes = %s" % (n, same_codes))

    ok = linear_bands and worst_is_darkest and gamma_uniform and same_codes
    print("-" * 88)
    print("SELF-TEST %s  linear_bands=%s  worst_is_darkest=%s  gamma_uniform=%s  same_codes=%s"
          % ("PASS" if ok else "FAIL", linear_bands, worst_is_darkest, gamma_uniform, same_codes))
    return ok


def main():
    p = argparse.ArgumentParser(description="Gamma-encode before quantizing so codes go where the eye is sensitive.")
    p.add_argument("--codes", action="store_true")
    p.add_argument("--steps", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("n_codes=%d  gamma=%.1f  file=%s  (the gamma and code count are a fixture)"
          % (data["n_codes"], data["gamma"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.codes:
        codes_view(data)
    elif args.steps:
        steps_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
