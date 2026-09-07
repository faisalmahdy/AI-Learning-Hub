"""Scale each channel so the scene's average is gray (gray-world) -- but only when the scene's average really is gray.

A photograph taken under colored light carries a color cast: shoot a white wall under a bluish LED and the image's blue
channel is lifted relative to red and green, so everything looks faintly blue. The eye discounts the light's color
automatically (a white shirt looks white indoors and outdoors); a camera does not, so it must correct the cast in
software -- white balance. The simplest correction is the gray-world assumption: over a whole scene, the average of all
the colors is roughly a neutral gray, because the many colored objects average out. If that holds, then any imbalance
between the channel averages is the light's cast, not the scene's content, and you remove it by scaling each channel so
its average matches the others. Scale the blue channel down and the red and green up until all three averages are equal,
and the cast is gone.

The scale factors are exactly target/channel_mean, where the target is the average the channels should share. Applied to
a genuinely neutral scene under a colored light, this works: it cancels the light and leaves the true, gray-averaged
colors. But the whole method rests on the assumption, and the assumption is a claim about the scene, not a law. When a
scene is genuinely dominated by one color -- a field of grass, a photo of the ocean, a red-brick wall -- its average is
NOT gray, and gray-world will 'correct' the real color out of the image, scaling the dominant channel down until the
grass turns gray. The algorithm cannot tell a green cast from green grass; it assumes any imbalance is a cast, and on a
one-color scene that assumption is false.

On this fixture the cast scene has channel means R=100, G=110, B=160 -- blue lifted by the light. Gray-world scales them
to a common 123.3, equalizing the channels and removing the cast. The color scene is real grass, means R=60, G=150,
B=50; gray-world equalizes those to 86.7 too, neutralizing the green that was supposed to be there. This computes both.

  --balance     the cast scene's channel means and scale factors, and the equalized means after gray-world
  --assumption  gray-world applied to the genuinely-green scene, which flattens the real color away
  --check       gray-world equalizes the channel means (removing a cast) but also flattens a real color-dominated scene

The two scenes' channel means are the fixture; every scale and result is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "whitebalance.json"

CHANNELS = ["R", "G", "B"]


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def target(means):
    """The gray-world target the channels should share: the mean of the three channel means."""
    return sum(means[c] for c in CHANNELS) / len(CHANNELS)


def gray_world_scales(means):
    """The per-channel scale factors that make every channel mean equal the target: target / channel_mean."""
    t = target(means)
    return {c: t / means[c] for c in CHANNELS}


def apply_scales(means, scales):
    """Apply the scale factors to the channel means."""
    return {c: means[c] * scales[c] for c in CHANNELS}


def is_neutral(means, tol=1e-6):
    """Are all three channel means equal (a neutral, cast-free scene)?"""
    return max(means[c] for c in CHANNELS) - min(means[c] for c in CHANNELS) < tol


# ----------------------------------------------------------------- printing

def balance_view(data):
    m = data["cast_scene"]
    scales = gray_world_scales(m)
    out = apply_scales(m, scales)
    print("BALANCE — gray-world on a neutral scene under a bluish light")
    print("-" * 58)
    print("  channel   mean     scale (target/mean)   after")
    for c in CHANNELS:
        print("  %-8s  %-7.1f  %-19.3f   %.1f" % (c, m[c], scales[c], out[c]))
    print("-" * 58)
    print("  target = %.1f; blue is scaled down, red and green up, cast removed (all equal)." % target(m))


def assumption_view(data):
    m = data["color_scene"]
    scales = gray_world_scales(m)
    out = apply_scales(m, scales)
    print("ASSUMPTION — gray-world on genuinely green grass (average is NOT gray)")
    print("-" * 60)
    print("  channel   mean     after gray-world")
    for c in CHANNELS:
        print("  %-8s  %-7.1f  %.1f" % (c, m[c], out[c]))
    print("-" * 60)
    print("  the real green (G=%.0f) is flattened to the same %.1f as red and blue -- the color is gone." % (m["G"], target(m)))


def check(data):
    print("SELF-TEST — gray-world equalizes the channel means (removing a cast) but also flattens a real color-dominated scene")
    print("-" * 114)
    cast, color = data["cast_scene"], data["color_scene"]

    cast_has_imbalance = not is_neutral(cast)
    print("  the cast scene has unequal channel means (a cast) = %s (%s)" % (cast_has_imbalance, {c: cast[c] for c in CHANNELS}))

    cast_scales = gray_world_scales(cast)
    cast_out = apply_scales(cast, cast_scales)
    cast_neutralized = is_neutral(cast_out)
    print("  gray-world equalizes the cast scene's channels = %s (%s)" % (cast_neutralized, {c: round(cast_out[c], 1) for c in CHANNELS}))

    scales_are_ratio = all(abs(cast_scales[c] - target(cast) / cast[c]) < 1e-12 for c in CHANNELS)
    print("  the scale factors are target/channel_mean = %s" % scales_are_ratio)

    color_out = apply_scales(color, gray_world_scales(color))
    color_flattened = is_neutral(color_out) and not is_neutral(color)
    print("  applied to real green grass, gray-world flattens the color = %s (G %.0f -> %.1f)" % (color_flattened, color["G"], color_out["G"]))

    green_was_dominant = color["G"] == max(color[c] for c in CHANNELS)
    print("  the grass scene was genuinely green-dominant (not a cast) = %s" % green_was_dominant)

    ok = cast_has_imbalance and cast_neutralized and scales_are_ratio and color_flattened and green_was_dominant
    print("-" * 114)
    print("SELF-TEST %s  cast_has_imbalance=%s  cast_neutralized=%s  scales_are_ratio=%s  color_flattened=%s  green_was_dominant=%s"
          % ("PASS" if ok else "FAIL", cast_has_imbalance, cast_neutralized, scales_are_ratio, color_flattened, green_was_dominant))
    return ok


def main():
    p = argparse.ArgumentParser(description="Gray-world white balance: scale each channel by target/channel_mean so the scene's average is gray, removing a color cast -- valid only when the scene's average really is gray, else it flattens a real color.")
    p.add_argument("--balance", action="store_true")
    p.add_argument("--assumption", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("cast_scene=%s  color_scene=%s  file=%s  (the scenes are a fixture)"
          % (data["cast_scene"], data["color_scene"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.balance:
        balance_view(data)
    elif args.assumption:
        assumption_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
