"""Blend in linear light, not on the stored codes -- averaging gamma-encoded pixels makes the result too dark.

The number stored for a pixel is not proportional to the light it represents. Images are gamma-encoded: the stored code
is roughly perceptually uniform, spread so that codes land where the eye can tell colors apart, which means most of the
codes are packed into the darks. The consequence is that a stored 128 is not half the light of a stored 255 -- decode it
and 128/255 = 0.502 raised to the gamma of 2.2 is only 0.22, so 'half the code' is about a fifth of the light. The
encoding is a curve, not a straight line, and that curve is exactly why you cannot do arithmetic on the stored codes as
if they were light.

Averaging is arithmetic on light. Blending two pixels, resizing an image (every output pixel is a weighted average of
inputs), alpha-compositing, blurring -- all of these add and average pixel values, and they are only correct on LINEAR
values, values proportional to actual light. Do them on the gamma-encoded codes and the result is systematically too
dark, because the encoding curve is convex: the average of two codes decodes to less light than the average of the two
lights. The fix is three steps: decode each code to linear (raise the normalized code to gamma), do the averaging in
linear light, then re-encode the result (raise to 1/gamma). Skip the decode/encode and you get the classic bug -- images
that darken when downscaled, blends that turn muddy, antialiased edges that look dirty -- all from averaging in the wrong
space.

On this fixture blending black (0) and white (255) should give the light halfway between them. In linear light that is
0.5, which re-encodes to 186 -- a bright mid-gray. Averaging the codes directly gives (0+255)/2 = 128, which is far
darker, because 128 is only 22% of full light, not 50%. A dark+light pair (51, 204) blends to 152 correctly but 128
naively, again too dark. Only when the two inputs are equal do the two methods agree, because then there is no curve to
distort. This computes all of it.

  --blend      each pair blended naively (average the codes) vs correctly (average the light), with the code difference
  --intensity  what a few stored codes actually are in linear light -- 128 is 22% light, not 50% -- and why the average darkens
  --check      naive code-averaging is darker than linear-light blending except when the inputs are equal; black+white is 128 vs 186

The pairs and gamma are the fixture; every decoded value and blend is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "gamma.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def decode(code, gamma):
    """Gamma-encoded 8-bit code -> linear light in [0,1]: (code/255) ** gamma."""
    return (code / 255.0) ** gamma


def encode(light, gamma):
    """Linear light in [0,1] -> gamma-encoded 8-bit code: round((light ** (1/gamma)) * 255)."""
    return round((light ** (1.0 / gamma)) * 255)


def blend_naive(a, b):
    """WRONG: average the stored codes directly, as if they were light."""
    return round((a + b) / 2)


def blend_linear(a, b, gamma):
    """RIGHT: decode both to linear light, average the light, re-encode."""
    return encode((decode(a, gamma) + decode(b, gamma)) / 2, gamma)


# ----------------------------------------------------------------- printing

def blend_view(data):
    g = data["gamma"]
    print("BLEND — average the codes (naive) vs average the light (correct), gamma=%.1f" % g)
    print("-" * 62)
    print("  pair          a    b    naive   correct   naive is")
    for p in data["pairs"]:
        n, c = blend_naive(p["a"], p["b"]), blend_linear(p["a"], p["b"], g)
        rel = "same" if n == c else ("%d darker" % (c - n))
        print("  %-12s  %-4d %-4d %-7d %-9d %s" % (p["name"], p["a"], p["b"], n, c, rel))
    print("-" * 62)
    print("  averaging the codes lands below the correct light-average -- the image darkens.")


def intensity_view(data):
    g = data["gamma"]
    print("INTENSITY — what stored codes really are in linear light (gamma=%.1f)" % g)
    print("-" * 56)
    print("  code    fraction of code   fraction of LIGHT")
    for code in (64, 128, 192, 255):
        print("  %-6d  %-17.3f  %.3f" % (code, code / 255.0, decode(code, g)))
    print("-" * 56)
    print("  code 128 is 0.502 of the way up in code but only %.3f of full light --" % decode(128, g))
    print("  so averaging codes weights the darks far more than the light warrants.")


def check(data):
    print("SELF-TEST — naive code-averaging is darker than linear-light blending except when the inputs are equal; black+white is 128 vs 186")
    print("-" * 130)
    g = data["pairs"]
    gamma = data["gamma"]
    bw = next(p for p in g if p["name"] == "black+white")

    naive_bw = blend_naive(bw["a"], bw["b"])
    naive_bw_is_128 = naive_bw == 128
    print("  naive blend of black+white is 128 = %s" % naive_bw_is_128)

    correct_bw = blend_linear(bw["a"], bw["b"], gamma)
    correct_bw_is_186 = correct_bw == 186
    print("  correct (linear) blend of black+white is 186 = %s" % correct_bw_is_186)

    naive_darker = all(blend_naive(p["a"], p["b"]) <= blend_linear(p["a"], p["b"], gamma) for p in g)
    print("  naive blend is never brighter than the correct blend = %s" % naive_darker)

    unequal_strictly_darker = all(blend_naive(p["a"], p["b"]) < blend_linear(p["a"], p["b"], gamma) for p in g if p["a"] != p["b"])
    print("  for unequal pairs the naive blend is strictly darker = %s" % unequal_strictly_darker)

    equal = next(p for p in g if p["a"] == p["b"])
    equal_agrees = blend_naive(equal["a"], equal["b"]) == blend_linear(equal["a"], equal["b"], gamma)
    print("  when the two inputs are equal, both methods agree = %s (%d)" % (equal_agrees, blend_naive(equal["a"], equal["b"])))

    ok = naive_bw_is_128 and correct_bw_is_186 and naive_darker and unequal_strictly_darker and equal_agrees
    print("-" * 130)
    print("SELF-TEST %s  naive_bw_is_128=%s  correct_bw_is_186=%s  naive_darker=%s  unequal_strictly_darker=%s  equal_agrees=%s"
          % ("PASS" if ok else "FAIL", naive_bw_is_128, correct_bw_is_186, naive_darker, unequal_strictly_darker, equal_agrees))
    return ok


def main():
    p = argparse.ArgumentParser(description="Blend in linear light: stored pixel codes are gamma-encoded and not proportional to light, so averaging them (blending, resizing, compositing, blurring) is too dark; decode to linear, average, re-encode.")
    p.add_argument("--blend", action="store_true")
    p.add_argument("--intensity", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("gamma=%.1f  pairs=%s  file=%s  (the pairs and gamma are a fixture)"
          % (data["gamma"], [(p["name"], p["a"], p["b"]) for p in data["pairs"]], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.blend:
        blend_view(data)
    elif args.intensity:
        intensity_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
