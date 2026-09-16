"""Blend, resize, and composite colors in LINEAR light, not in the gamma-encoded values stored in the image -- otherwise the result comes out too dark.

The 8-bit number stored for a pixel is not proportional to physical light. It is gamma-encoded: roughly the intensity raised to the power 1/2.2, a perceptual curve that spends more of the 256 code values on darks, where the eye is more sensitive, than on brights. This is why images look right on a display that applies the inverse curve. But it means the stored value and the light it represents are related non-linearly, and that breaks any operation that mixes light.

Physical light adds linearly: put two lamps in a room and the intensities sum. So blending two colors, resizing an image (which averages neighboring pixels), alpha compositing, and anti-aliasing are all operations on LINEAR intensity. Do them on the gamma-encoded values instead -- just average the stored numbers -- and you are averaging in the wrong space. The arithmetic mean of two encoded values is not the encoded value of the mean intensity, because the encoding is a curve, not a line. The result is systematically too dark, because the gamma curve is concave: encoded midpoints sit below the true midpoint.

The symptom is unmistakable once you know it. A 50/50 blend of black (0) and white (255) in gamma space gives mid-gray 128 -- exactly halfway up the code values, which feels right but is wrong. The physically-correct blend decodes both to linear (0.0 and 1.0), averages to 0.5, and re-encodes: 255 * 0.5^(1/2.2) = 186, a much lighter gray. That 58-level gap is the darkening that plagues naive image resizing, alpha blending, and gradient rendering across a great deal of software.

The fix is three steps: decode each value to linear (linear = (v/255)^gamma), do the math on linear values, then encode back (encoded = 255 * result^(1/gamma)). The decode/encode round-trip is exact, so the only change is that the mixing happens in the space where light actually adds.

The rule: perform any operation that mixes light -- blending, resizing, compositing, anti-aliasing -- on linear intensities, decoding from and re-encoding to gamma space around it, because pixel values are gamma-encoded and averaging them directly mixes in the wrong (non-linear) space, producing a systematically too-dark result.

On this fixture, blending black and white 50/50 gives 128 naively but 186 correctly, and blending 64 and 192 gives 128 naively but 146 correctly. This computes both.

  --decode    each encoded value and its linear intensity (the sRGB->linear step)
  --blend     the naive gamma-space average vs the correct linear-space blend, per pair
  --check     the naive blend is too dark; the linear-space blend is lighter and correct

gamma and the value pairs are the fixture; every linear intensity, naive average, and linear-space blend is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "gammablend.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def decode(v, gamma):
    """Gamma-encoded 8-bit value -> linear intensity in [0, 1]."""
    return (v / 255.0) ** gamma


def encode(lin, gamma):
    """Linear intensity in [0, 1] -> gamma-encoded 8-bit value."""
    return round(255.0 * (lin ** (1.0 / gamma)))


def naive_blend(a, b):
    """Average the encoded values directly -- the wrong space."""
    return round((a + b) / 2.0)


def linear_blend(a, b, gamma):
    """Decode to linear, average, re-encode -- the right space."""
    return encode((decode(a, gamma) + decode(b, gamma)) / 2.0, gamma)


# ----------------------------------------------------------------- printing

def decode_view(data):
    gamma = data["gamma"]
    seen = []
    for p in data["pairs"]:
        for v in (p["a"], p["b"]):
            if v not in seen:
                seen.append(v)
    print("DECODE — gamma-encoded 8-bit value -> linear intensity (gamma=%.1f)" % gamma)
    print("-" * 56)
    for v in sorted(seen):
        print("  value %3d  ->  linear %.4f" % (v, decode(v, gamma)))
    print("-" * 56)
    print("  the curve is concave: encoded midpoints sit below linear midpoints")


def blend_view(data):
    gamma = data["gamma"]
    print("BLEND — naive gamma-space average vs correct linear-space blend")
    print("-" * 64)
    print("  pair        naive   correct   diff (correct - naive)")
    for p in data["pairs"]:
        a, b = p["a"], p["b"]
        nv, cv = naive_blend(a, b), linear_blend(a, b, gamma)
        print("  (%3d,%3d)   %3d     %3d       %+d" % (a, b, nv, cv, cv - nv))
    print("-" * 64)
    print("  naive blends come out too dark; the linear-space blend is lighter and correct")


def check(data):
    print("SELF-TEST — the naive (gamma-space) blend is too dark; the linear-space blend is lighter and correct")
    print("-" * 104)
    gamma = data["gamma"]
    pairs = data["pairs"]

    bw = next(p for p in pairs if p["a"] == 0 and p["b"] == 255)
    bw_naive, bw_correct = naive_blend(bw["a"], bw["b"]), linear_blend(bw["a"], bw["b"], gamma)

    roundtrip_exact = all(encode(decode(v, gamma), gamma) == v for v in (0, 64, 128, 192, 255))
    print("  decode then encode is identity (round-trip is lossless) = %s" % roundtrip_exact)

    black_white_naive_is_midgray = bw_naive == 128
    print("  naive black+white blend is mid-gray 128 = %s (%d)" % (black_white_naive_is_midgray, bw_naive))

    black_white_correct_is_lighter = bw_correct == 186
    print("  correct black+white blend is 186, much lighter = %s (%d)" % (black_white_correct_is_lighter, bw_correct))

    naive_too_dark = all(naive_blend(p["a"], p["b"]) < linear_blend(p["a"], p["b"], gamma) for p in pairs)
    print("  every naive blend is darker than the correct one = %s" % naive_too_dark)

    naive_wrong = all(naive_blend(p["a"], p["b"]) != linear_blend(p["a"], p["b"], gamma) for p in pairs)
    print("  the naive and correct blends disagree on every pair = %s" % naive_wrong)

    ok = (roundtrip_exact and black_white_naive_is_midgray and black_white_correct_is_lighter
          and naive_too_dark and naive_wrong)
    print("-" * 104)
    print("SELF-TEST %s  roundtrip_exact=%s  black_white_naive_is_midgray=%s  black_white_correct_is_lighter=%s  naive_too_dark=%s  naive_wrong=%s"
          % ("PASS" if ok else "FAIL", roundtrip_exact, black_white_naive_is_midgray, black_white_correct_is_lighter, naive_too_dark, naive_wrong))
    return ok


def main():
    p = argparse.ArgumentParser(description="Gamma-correct blending: perform any operation that mixes light (blending, resizing, compositing) on linear intensities, decoding from and re-encoding to gamma space around it, because pixel values are gamma-encoded and averaging them directly mixes in the wrong space, producing a systematically too-dark result.")
    p.add_argument("--decode", action="store_true")
    p.add_argument("--blend", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("gamma=%.1f  pairs=%s  file=%s  (the gamma and value pairs are a fixture)"
          % (data["gamma"], [(p["a"], p["b"]) for p in data["pairs"]], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.decode:
        decode_view(data)
    elif args.blend:
        blend_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
