"""Convert color to grayscale with luma weights, not a channel average -- the eye weights green far more than blue, and averaging erases that.

Turning a color image to grayscale looks like it should be the average of the red, green, and blue channels: add them up, divide by three. That treats the three channels as equally important to brightness, and they are not. Human vision is most sensitive to green, less to red, and least to blue -- by large factors -- so equal intensities of the three primaries do not look equally bright at all. Pure green looks bright, pure red middling, pure blue distinctly dark. A grayscale conversion is supposed to capture how bright each pixel LOOKS, and a plain channel average captures how much total signal is present regardless of how the eye weights it, which is a different and wrong thing.

The failure is sharpest on saturated colors. Because the average weights every channel the same, all three fully-saturated primaries -- pure red, pure green, pure blue -- collapse to the identical gray value (a third of full), even though they span a huge range of perceived brightness. In that grayscale a bright green region and a dark blue region become the same shade, indistinguishable, and any contrast the color carried between them is gone. The conversion ran and produced a plausible gray image; it just flattened exactly the brightness differences a viewer would have seen.

The fix is to weight the channels by their contribution to perceived brightness -- LUMA. The standard coefficients (Rec. 601: 0.299 for red, 0.587 for green, 0.114 for blue, summing to 1) come from measurements of human sensitivity, and they reproduce how bright each color looks: green, at 0.587, dominates; blue, at 0.114, barely registers. Applying them, the primaries map to well-separated grays (~76, ~150, ~29) that match perception, and the grayscale preserves the brightness structure of the original instead of destroying it. The weights are a property of the eye, not a tunable, which is why they are baked into image standards.

The rule: convert color to grayscale with a perceptual luma weighting (about 0.299 R + 0.587 G + 0.114 B), not a plain channel average, because the eye weights green far above red and blue -- so an average maps colors of very different perceived brightness (all three saturated primaries) to the same gray, flattening contrast the luma weighting preserves.

On these three primaries the naive average maps red, green, and blue all to 85 -- identical -- while luma weighting maps them to 76.2, 149.7, and 29.1, spanning the real range of perceived brightness. This computes both.

  --gray      each primary's naive average vs luma gray value
  --collapse  how the naive average collapses the primaries to one value while luma keeps them separated
  --check     the average maps all three primaries to the same gray; luma weighting separates them by perceived brightness

colors and luma_weights are the fixture; every gray value is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "lumagray.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def naive_gray(rgb):
    """Plain channel average -- treats all channels as equally bright."""
    return sum(rgb) / 3


def luma_gray(rgb, weights):
    """Perceptual luma -- weights each channel by the eye's sensitivity."""
    return sum(w * c for w, c in zip(weights, rgb))


# ----------------------------------------------------------------- printing

def gray_view(data):
    colors, w = data["colors"], data["luma_weights"]
    print("GRAY — naive average vs luma gray for each primary (weights %s)" % w)
    print("-" * 56)
    print("  color   rgb              naive   luma")
    for name, rgb in colors.items():
        print("  %-6s  %-15s  %-6.1f  %.1f" % (name, rgb, naive_gray(rgb), luma_gray(rgb, w)))
    print("-" * 56)
    print("  naive weights channels equally; luma weights green most, blue least")


def collapse_view(data):
    colors, w = data["colors"], data["luma_weights"]
    naive = {name: naive_gray(rgb) for name, rgb in colors.items()}
    luma = {name: luma_gray(rgb, w) for name, rgb in colors.items()}
    print("COLLAPSE — naive maps the primaries together; luma keeps them apart")
    print("-" * 60)
    print("  naive grays: %s -> spread %.1f" % ({n: round(v, 1) for n, v in naive.items()}, max(naive.values()) - min(naive.values())))
    print("  luma  grays: %s -> spread %.1f" % ({n: round(v, 1) for n, v in luma.items()}, max(luma.values()) - min(luma.values())))
    print("-" * 60)
    print("  the naive average flattens all contrast to spread 0; luma keeps a spread of %.1f gray levels"
          % (max(luma.values()) - min(luma.values())))


def check(data):
    print("SELF-TEST — the average maps all three primaries to the same gray; luma weighting separates them by perceived brightness")
    print("-" * 120)
    colors, w = data["colors"], data["luma_weights"]
    naive = [naive_gray(rgb) for rgb in colors.values()]
    luma = {name: luma_gray(rgb, w) for name, rgb in colors.items()}

    weights_sum_one = abs(sum(w) - 1.0) < 1e-9
    print("  the luma weights sum to 1 = %s (%.3f)" % (weights_sum_one, sum(w)))

    green_weight_largest = w[1] == max(w)
    print("  green has the largest luma weight = %s (%.3f)" % (green_weight_largest, w[1]))

    naive_all_equal = max(naive) - min(naive) < 1e-9
    print("  the naive average maps all three primaries to the SAME gray = %s (%.1f)" % (naive_all_equal, naive[0]))

    luma_all_different = len({round(v, 1) for v in luma.values()}) == 3
    print("  luma weighting gives all three DIFFERENT grays = %s (%s)" % (luma_all_different, {n: round(v, 1) for n, v in luma.items()}))

    green_brightest = luma["green"] > luma["red"] > luma["blue"]
    print("  luma ranks green > red > blue (matching perception) = %s (%.1f > %.1f > %.1f)" % (green_brightest, luma["green"], luma["red"], luma["blue"]))

    luma_preserves_contrast = (max(luma.values()) - min(luma.values())) > (max(naive) - min(naive))
    print("  luma preserves brightness contrast the average flattens = %s (spread %.1f vs %.1f)"
          % (luma_preserves_contrast, max(luma.values()) - min(luma.values()), max(naive) - min(naive)))

    ok = (weights_sum_one and green_weight_largest and naive_all_equal and luma_all_different
          and green_brightest and luma_preserves_contrast)
    print("-" * 120)
    print("SELF-TEST %s  weights_sum_one=%s  green_weight_largest=%s  naive_all_equal=%s  luma_all_different=%s  green_brightest=%s  luma_preserves_contrast=%s"
          % ("PASS" if ok else "FAIL", weights_sum_one, green_weight_largest, naive_all_equal, luma_all_different, green_brightest, luma_preserves_contrast))
    return ok


def main():
    p = argparse.ArgumentParser(description="Luminance grayscale: convert color to grayscale with a perceptual luma weighting (about 0.299 R + 0.587 G + 0.114 B), not a plain channel average, because the eye weights green far above red and blue -- so an average maps colors of very different perceived brightness (all three saturated primaries) to the same gray, flattening contrast the luma weighting preserves.")
    p.add_argument("--gray", action="store_true")
    p.add_argument("--collapse", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("colors=%s  luma_weights=%s  file=%s  (the primaries and weights are a fixture)"
          % (list(data["colors"]), data["luma_weights"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.gray:
        gray_view(data)
    elif args.collapse:
        collapse_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
