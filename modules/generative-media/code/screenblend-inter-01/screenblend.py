"""Combine light layers with the screen operator, not plain addition -- adding two light layers clips at pure white wherever they are already bright, collapsing every different overlap to the same blown-out value, while screen brightens like light, stays inside the 0..1 range, and never clips.

Compositing a glow, a lens flare, two lamps, or an additive particle effect means combining two layers of light. The physically honest way is addition: light energy sums, so a + b. The trouble is that a display channel maxes out at 1.0, so any sum above 1.0 is clamped, and a lot of overlaps sum above 1.0. Every one of them becomes the same flat 1.0 -- the bright regions blow out to white and lose their variation and their hue. Two genuinely different bright overlaps become indistinguishable.

The screen operator is 1 - (1 - a)(1 - b). It has three properties addition lacks where you want them. It brightens: the result is at least as bright as the brighter input, so light still accumulates. It stays in range: it approaches 1 as the inputs approach 1 but never exceeds it, so bright-on-bright is a distinct near-white, not a clamped flat white. And it is commutative -- screen(a, b) equals screen(b, a) -- so the order of the layers does not matter, which is right for light sources that have no natural front-to-back order (unlike the alpha 'over' operator, which occludes and is order-dependent).

On this fixture a warm layer [0.7, 0.4, 0.2] and a cool layer [0.6, 0.5, 0.9] overlap. Added, the red channel is 1.3 and the blue is 1.1, both clamped to 1.0, so the overlap is a blown-out near-white. Screened, the same overlap is [0.88, 0.70, 0.92] -- brighter than either layer, every channel below 1.0, the color preserved. A separate demo shows two different additive sums (0.7+0.6 and 0.9+0.8) that both clamp to 1.0 and become the same value, while screen keeps them 0.88 and 0.98. This computes all of it.

  --additive  add the layers and clamp: the bright overlap blows out to white and different overlaps collapse to the same 1.0
  --screen    screen the layers: brighter but in range, color preserved, order-independent
  --check     additive clips while screen never does, screen still brightens and is commutative, and additive collapses distinct overlaps that screen keeps apart

the two layers and two collision pairs are the fixture; every additive sum, clamp, and screen value, and all the checks, are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "screenblend.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def add_raw(a, b):
    """Plain additive blend, before the display clamps it: light energy sums."""
    return [x + y for x, y in zip(a, b)]


def clamp(v):
    """What the display actually stores: every channel pinned into 0..1."""
    return [min(1.0, max(0.0, x)) for x in v]


def screen(a, b):
    """The screen operator, 1 - (1-a)(1-b): brightens toward 1 without ever exceeding it."""
    return [1.0 - (1.0 - x) * (1.0 - y) for x, y in zip(a, b)]


# ----------------------------------------------------------------- printing

def _fmt(v):
    return "[" + ", ".join("%.2f" % x for x in v) + "]"


def additive_view(data):
    a, b = data["layer_a"], data["layer_b"]
    raw = add_raw(a, b)
    print("ADDITIVE — add the two light layers, then clamp to the display range")
    print("-" * 64)
    print("  layer A     = %s" % _fmt(a))
    print("  layer B     = %s" % _fmt(b))
    print("  a + b (raw) = %s" % _fmt(raw))
    print("  clamped     = %s   <- channels over 1.0 are pinned to white" % _fmt(clamp(raw)))
    print("-" * 64)
    print("  the bright overlap blows out; the amount of light above 1.0 is thrown away")


def screen_view(data):
    a, b = data["layer_a"], data["layer_b"]
    s = screen(a, b)
    print("SCREEN — 1 - (1-a)(1-b): brighten without leaving the range")
    print("-" * 64)
    print("  layer A = %s" % _fmt(a))
    print("  layer B = %s" % _fmt(b))
    print("  screen  = %s   <- brighter than either, every channel below 1.0" % _fmt(s))
    print("  screen(b, a) = %s   (order does not matter)" % _fmt(screen(b, a)))
    print("-" * 64)
    print("  light accumulates and stays in range, so the overlap keeps its color")


def check(data):
    print("SELF-TEST — additive clips while screen never does, screen still brightens and is commutative, and additive collapses distinct overlaps that screen keeps apart")
    print("-" * 112)
    a, b = data["layer_a"], data["layer_b"]
    raw, s = add_raw(a, b), screen(a, b)

    additive_clips = any(x > 1.0 for x in raw)
    print("  additive sum exceeds 1.0 and must be clamped = %s (raw %s)" % (additive_clips, _fmt(raw)))

    screen_in_range = all(0.0 <= x <= 1.0 for x in s)
    print("  screen result stays within 0..1 (never clips) = %s (%s)" % (screen_in_range, _fmt(s)))

    screen_brightens = all(s[i] >= max(a[i], b[i]) - 1e-9 for i in range(len(s)))
    print("  screen is at least as bright as the brighter layer (light accumulates) = %s" % screen_brightens)

    screen_commutative = all(abs(x - y) < 1e-9 for x, y in zip(screen(a, b), screen(b, a)))
    print("  screen is commutative, so layer order does not matter = %s" % screen_commutative)

    p1, p2 = data["collide_pair_1"], data["collide_pair_2"]
    add1, add2 = clamp([sum(p1)])[0], clamp([sum(p2)])[0]
    scr1, scr2 = screen([p1[0]], [p1[1]])[0], screen([p2[0]], [p2[1]])[0]
    additive_collapses = (add1 == add2) and (abs(scr1 - scr2) > 1e-9)
    print("  two distinct overlaps collapse to the same clamped value but stay distinct under screen = %s (add %.2f==%.2f, screen %.2f vs %.2f)"
          % (additive_collapses, add1, add2, scr1, scr2))

    ok = (additive_clips and screen_in_range and screen_brightens and screen_commutative and additive_collapses)
    print("-" * 112)
    print("SELF-TEST %s  additive_clips=%s  screen_in_range=%s  screen_brightens=%s  screen_commutative=%s  additive_collapses=%s"
          % ("PASS" if ok else "FAIL", additive_clips, screen_in_range, screen_brightens, screen_commutative, additive_collapses))
    return ok


def main():
    p = argparse.ArgumentParser(description="Screen blend for light: combine light layers (glow, flare, lamps, additive particles) with the screen operator 1-(1-a)(1-b) rather than plain addition, because addition clips at 1.0 wherever the layers are already bright -- blowing bright overlaps out to a flat white and collapsing distinct overlaps to the same value -- while screen brightens like light, is commutative so layer order does not matter, and asymptotes toward 1 without ever exceeding it.")
    p.add_argument("--additive", action="store_true")
    p.add_argument("--screen", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("layer_a=%s  layer_b=%s  file=%s" % (data["layer_a"], data["layer_b"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.additive:
        additive_view(data)
    elif args.screen:
        screen_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
