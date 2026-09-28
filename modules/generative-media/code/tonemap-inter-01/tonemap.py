"""Tone-map on the pixel's luminance and scale the color, never channel by channel -- a compression curve applied to each of R, G, B independently squeezes the bright channel harder than the dim one, so it desaturates the color and washes a saturated highlight toward white.

A high-dynamic-range image holds linear light values that run past 1.0 -- a lamp, a sky, a specular glint -- and a display can only show 0..1, so a tone-mapping operator compresses the range with a curve that is steep near zero and flattens as it rises. The Reinhard operator x -> x/(1+x) is the canonical example: it barely touches small values and pulls large ones down toward 1.

The obvious way to apply it is to run every channel through the curve. That compresses the brightness, which is what you wanted, but it also silently changes the color. The curve is nonlinear and concave, so it shrinks a big input proportionally more than a small one: a channel at 2.0 is pushed down harder, relative to itself, than a channel at 0.5. The gap between the channels closes, and closing the gap between R, G, and B is the definition of desaturation. A vivid orange highlight comes back pale and milky.

The fix keeps the color and the brightness on separate tracks. Compute the pixel's luminance -- the weighted brightness the eye sees -- run only that single number through the tone curve, and scale the original RGB by the ratio mapped_luminance / luminance. The scale is one common factor across all three channels, so their ratios are untouched: the hue and saturation are exactly preserved, while the brightness is compressed by precisely the factor the curve dictated for the luminance.

On the fixture the HDR pixel is [2.0, 1.2, 0.5], a saturated warm highlight. Per-channel Reinhard returns a washed-out color whose saturation has collapsed; luminance tone mapping returns the same hue and saturation at the compressed brightness. This computes both.

  --perchannel   Reinhard applied to each channel: the desaturated, washed-out result
  --onluminance  Reinhard applied to luminance, then scale RGB: brightness compressed, color preserved
  --check        per-channel tone mapping desaturates while luminance tone mapping preserves the ratios and hits the intended brightness

pixel and the luminance weights are the fixture; the tone-mapped colors, their luminances, and saturations are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "tonemap.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def luminance(rgb, weights):
    """Perceived brightness: the Rec.709 weighted sum of the linear channels."""
    return sum(c * w for c, w in zip(rgb, weights))


def reinhard(x):
    """The tone curve: compress an unbounded value into 0..1, gently near 0 and hard up high."""
    return x / (1.0 + x)


def tone_map_per_channel(rgb):
    """BUG: run each channel through the curve on its own -- the concave curve closes the channel gaps."""
    return [reinhard(c) for c in rgb]


def tone_map_on_luminance(rgb, weights):
    """FIX: map the luminance, then scale RGB by the ratio -- one common factor leaves the ratios intact."""
    lum = luminance(rgb, weights)
    scale = reinhard(lum) / lum
    return [c * scale for c in rgb]


def saturation(rgb):
    """HSV saturation: how far the color is from gray, (max - min) / max -- a pure ratio, brightness-free."""
    hi = max(rgb)
    if hi == 0:
        return 0.0
    return (hi - min(rgb)) / hi


# ----------------------------------------------------------------- printing

def _fmt(rgb):
    return "[%s]" % ", ".join("%.4f" % c for c in rgb)


def perchannel_view(data):
    rgb, w = data["pixel"], data["luminance_weights"]
    out = tone_map_per_channel(rgb)
    print("PER-CHANNEL — Reinhard applied to each channel separately (the bug)")
    print("-" * 64)
    print("  HDR pixel        = %s   saturation %.4f" % (_fmt(rgb), saturation(rgb)))
    print("  per-channel out  = %s   saturation %.4f" % (_fmt(out), saturation(out)))
    print("  luminance %.4f -> %.4f" % (luminance(rgb, w), luminance(out, w)))
    print("-" * 64)
    print("  the channels were pulled together: the saturation collapsed and the color washed out")


def onluminance_view(data):
    rgb, w = data["pixel"], data["luminance_weights"]
    out = tone_map_on_luminance(rgb, w)
    print("ON-LUMINANCE — Reinhard applied to luminance, then scale RGB (the fix)")
    print("-" * 64)
    print("  HDR pixel        = %s   saturation %.4f" % (_fmt(rgb), saturation(rgb)))
    print("  on-luminance out = %s   saturation %.4f" % (_fmt(out), saturation(out)))
    print("  luminance %.4f -> %.4f  (target reinhard(L) = %.4f)"
          % (luminance(rgb, w), luminance(out, w), reinhard(luminance(rgb, w))))
    print("-" * 64)
    print("  the ratios are untouched: same hue and saturation, at the compressed brightness")


def check(data):
    print("SELF-TEST — per-channel tone mapping desaturates while luminance tone mapping preserves the ratios and hits the intended brightness")
    print("-" * 112)
    rgb, w = data["pixel"], data["luminance_weights"]
    per = tone_map_per_channel(rgb)
    lum = tone_map_on_luminance(rgb, w)
    sat0 = saturation(rgb)

    per_channel_desaturates = saturation(per) < sat0 - 0.05
    print("  per-channel tone mapping lowers saturation = %s (%.4f -> %.4f)" % (per_channel_desaturates, sat0, saturation(per)))

    onlum_preserves_saturation = abs(saturation(lum) - sat0) < 1e-9
    print("  luminance tone mapping preserves saturation = %s (%.4f -> %.4f)" % (onlum_preserves_saturation, sat0, saturation(lum)))

    ratios0 = [c / rgb[0] for c in rgb]
    ratios_lum = [c / lum[0] for c in lum]
    onlum_preserves_ratios = all(abs(a - b) < 1e-9 for a, b in zip(ratios0, ratios_lum))
    print("  luminance tone mapping preserves the R:G:B ratios = %s" % onlum_preserves_ratios)

    ratios_per = [c / per[0] for c in per]
    per_channel_shifts_ratios = any(abs(a - b) > 1e-6 for a, b in zip(ratios0, ratios_per))
    print("  per-channel tone mapping shifts the R:G:B ratios = %s" % per_channel_shifts_ratios)

    onlum_hits_target_brightness = abs(luminance(lum, w) - reinhard(luminance(rgb, w))) < 1e-9
    print("  luminance result's brightness equals the tone curve's target = %s (%.4f == %.4f)"
          % (onlum_hits_target_brightness, luminance(lum, w), reinhard(luminance(rgb, w))))

    ok = (per_channel_desaturates and onlum_preserves_saturation and onlum_preserves_ratios
          and per_channel_shifts_ratios and onlum_hits_target_brightness)
    print("-" * 112)
    print("SELF-TEST %s  per_channel_desaturates=%s  onlum_preserves_saturation=%s  onlum_preserves_ratios=%s  per_channel_shifts_ratios=%s  onlum_hits_target_brightness=%s"
          % ("PASS" if ok else "FAIL", per_channel_desaturates, onlum_preserves_saturation, onlum_preserves_ratios,
             per_channel_shifts_ratios, onlum_hits_target_brightness))
    return ok


def main():
    p = argparse.ArgumentParser(description="Tone mapping: apply the tone-compression curve to the pixel's luminance and scale the color by the ratio, never to each channel independently, because a nonlinear concave curve squeezes a bright channel harder than a dim one, closing the channel gaps and desaturating a saturated highlight toward white.")
    p.add_argument("--perchannel", action="store_true")
    p.add_argument("--onluminance", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("pixel=%s  luminance_weights=%s  file=%s  (these are a fixture)"
          % (data["pixel"], data["luminance_weights"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.perchannel:
        perchannel_view(data)
    elif args.onluminance:
        onluminance_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
