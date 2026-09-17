"""Adjust saturation by scaling each channel around the pixel's luma, not by scaling the raw RGB values -- scaling the raw values changes brightness and clips, while scaling around luma changes saturation and leaves perceived brightness untouched.

Saturation is how far a color sits from gray, and the gray a color should collapse toward is its own luma -- its perceived brightness, a weighted sum of the channels (green counts most, blue least). Changing saturation means moving the channels toward or away from that gray point while leaving the brightness where it was. The operation that does this is new = luma + factor * (channel - luma): at factor 0 the pixel becomes its gray luma, at factor 1 it is unchanged, above 1 it is pushed further from gray. Crucially, for any factor the luma is preserved, because the same luma is added back to every channel and the weighted sum returns to the original.

The naive approach is to multiply each channel by the factor. It looks like it should boost saturation -- the numbers get bigger -- but it does the wrong thing on two counts. First, it scales the color's brightness along with its chroma: multiplying every channel by 1.5 makes the pixel 1.5 times brighter, so a 'more saturated' image comes out glaringly brighter, not just more colorful. Second, channels that exceed 255 are clipped, and clipping different channels by different amounts twists the hue, so the color shifts as well as brightening.

The difference is exactly the luma. The luma-preserving formula keeps the weighted brightness fixed at the original value no matter the factor; the channel-scaling formula multiplies the luma by the factor, so brightness rides along with saturation and the two can no longer be controlled separately. A saturation slider built on channel scaling is really a brightness-and-saturation slider with a hue glitch at the top end.

The rule: change saturation with new_channel = luma + factor * (channel - luma), scaling each channel around the pixel's luma, because that adjusts how far the color is from gray while preserving its perceived brightness -- whereas multiplying the raw channels scales brightness too and clips, shifting brightness and hue instead of just saturation.

On this fixture a pixel is pushed to 1.5x saturation. The luma-preserving formula keeps the luma at its original value and stays in range; multiplying the channels raises the luma and clips a channel past 255. This computes both.

  --adjust    the correct luma-preserving adjustment vs naive channel scaling, channel by channel
  --luma      the pixel's luma before and after each method -- preserved by one, changed by the other
  --check     scaling around luma preserves brightness and stays in range; scaling raw channels shifts luma and clips

pixel, factor, and the luma weights are the fixture; the luma and the two adjusted pixels are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "satadjust.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def luma(pixel, weights):
    """Perceived brightness: the weighted sum of the channels (Rec. 601)."""
    return sum(w * c for w, c in zip(weights, pixel))


def saturate_around_luma(pixel, factor, weights):
    """Correct: move each channel away from the pixel's luma by the factor -- luma is preserved."""
    y = luma(pixel, weights)
    return [y + factor * (c - y) for c in pixel]


def saturate_naive(pixel, factor):
    """Naive: multiply each raw channel by the factor -- scales brightness too, and may exceed 255."""
    return [c * factor for c in pixel]


def clip(pixel):
    return [max(0.0, min(255.0, c)) for c in pixel]


# ----------------------------------------------------------------- printing

def adjust_view(data):
    px, f, w = data["pixel"], data["factor"], data["luma_weights"]
    correct = saturate_around_luma(px, f, w)
    naive = saturate_naive(px, f)
    print("ADJUST — pixel %s at saturation factor %.1f" % (px, f))
    print("-" * 60)
    print("  channel   original   around-luma   naive x%.1f" % f)
    for i, name in enumerate("RGB"):
        print("  %s         %-8d   %-11.1f   %.1f" % (name, px[i], correct[i], naive[i]))
    print("-" * 60)
    print("  around-luma stays in range; naive pushes R past 255 (will clip)")


def luma_view(data):
    px, f, w = data["pixel"], data["factor"], data["luma_weights"]
    y0 = luma(px, w)
    yc = luma(saturate_around_luma(px, f, w), w)
    yn = luma(clip(saturate_naive(px, f)), w)
    print("LUMA — perceived brightness before and after each method")
    print("-" * 54)
    print("  original luma            = %.2f" % y0)
    print("  around-luma luma         = %.2f  (change %.2f)" % (yc, yc - y0))
    print("  naive (clipped) luma     = %.2f  (change %+.2f)" % (yn, yn - y0))
    print("-" * 54)
    print("  scaling around luma preserves brightness; naive scaling changes it")


def check(data):
    print("SELF-TEST — scaling around luma preserves brightness and stays in range; scaling raw channels shifts luma and clips")
    print("-" * 120)
    px, f, w = data["pixel"], data["factor"], data["luma_weights"]
    y0 = luma(px, w)
    correct = saturate_around_luma(px, f, w)
    naive = saturate_naive(px, f)

    correct_preserves_luma = abs(luma(correct, w) - y0) < 1e-9
    print("  around-luma preserves the original luma = %s (%.2f)" % (correct_preserves_luma, luma(correct, w)))

    correct_in_range = all(0.0 <= c <= 255.0 for c in correct)
    print("  around-luma channels stay within 0..255 = %s" % correct_in_range)

    naive_clips = any(c > 255.0 for c in naive)
    print("  naive channel scaling pushes a channel past 255 = %s (%s)" % (naive_clips, [round(c, 1) for c in naive]))

    naive_changes_luma = abs(luma(clip(naive), w) - y0) > 1.0
    print("  naive (after clipping) changes the luma = %s (%.2f vs %.2f)" % (naive_changes_luma, luma(clip(naive), w), y0))

    correct_raises_saturation = (max(correct) - min(correct)) > (max(px) - min(px))
    print("  around-luma actually increases saturation (channel spread) = %s" % correct_raises_saturation)

    ok = (correct_preserves_luma and correct_in_range and naive_clips
          and naive_changes_luma and correct_raises_saturation)
    print("-" * 120)
    print("SELF-TEST %s  correct_preserves_luma=%s  correct_in_range=%s  naive_clips=%s  naive_changes_luma=%s  correct_raises_saturation=%s"
          % ("PASS" if ok else "FAIL", correct_preserves_luma, correct_in_range, naive_clips,
             naive_changes_luma, correct_raises_saturation))
    return ok


def main():
    p = argparse.ArgumentParser(description="Saturation adjustment: change saturation with new_channel = luma + factor * (channel - luma), scaling each channel around the pixel's luma, because that adjusts how far the color is from gray while preserving its perceived brightness -- whereas multiplying the raw channels scales brightness too and clips, shifting brightness and hue instead of just saturation.")
    p.add_argument("--adjust", action="store_true")
    p.add_argument("--luma", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("pixel=%s  factor=%.1f  luma_weights=%s  file=%s  (these are a fixture)"
          % (data["pixel"], data["factor"], data["luma_weights"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.adjust:
        adjust_view(data)
    elif args.luma:
        luma_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
