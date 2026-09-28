"""Rotate a hue with circular (modulo 360) arithmetic, not by clamping -- hue is an angle on a color wheel where 360 equals 0, so a rotation past 360 must wrap around into the reds; clamping sticks it at the boundary and collapses distinct hues into one.

Hue is the angular coordinate of color: 0 degrees is red, it sweeps through green at 120 and blue at 240, and at 360 it comes all the way back to red. That periodicity is the whole point -- hue lives on a circle, not a line, and every operation on it is an operation on a circle. Rotating a palette warmer or cooler means turning every hue by some number of degrees around that wheel.

Turning around a wheel is modular addition: add the rotation and take the result modulo 360. A hue of 340 (a red-magenta) rotated by 40 degrees lands at 20 (a warm red-orange), because it crossed the 360/0 seam and continued into the low angles. That crossing is normal and correct; the wheel has no edge.

The naive mistake is to forget the wheel and treat hue as an ordinary bounded number that must be clamped to its range. Then 340 + 40 = 380 is not wrapped to 20 but clamped to the ceiling, 360, which reads as red-magenta again -- a color the rotation was supposed to move away from. The rotation silently stops working for any hue near the top of the range, exactly the reds and magentas, which is a very visible band of colors.

Clamping does a second, worse thing: it is many-to-one at the boundary. Every hue that would rotate past 360 clamps to the same ceiling value, so 340 and 350, which should rotate to two different colors (20 and 30), both collapse to one. Distinct colors in the input become identical in the output -- information destroyed, not just shifted. Wrapping preserves the distinction because the circle has room past the seam.

The rule: rotate hue with circular arithmetic -- (hue + rotation) modulo 360 -- never by clamping the sum to the range, because hue is an angle where 360 equals 0, so clamping produces the wrong color for any hue that should cross the seam and collapses distinct crossing hues into a single boundary value.

On this fixture four hues are rotated by 40 degrees. The two low hues behave the same either way, but 340 and 350 cross the seam: wrapping sends them to 20 and 30, while clamping pins both to 360, the wrong color and a collision. This computes both.

  --rotate    each hue's rotated result under wraparound vs clamping, and whether it crosses the seam
  --collide   the distinct hues that clamping collapses to the same value but wrapping keeps distinct
  --check     hues that cross 360 wrap to the correct low angles; clamping gives the wrong color and collides

hues, rotation, and hue_max are the fixture; the wrapped and clamped results and the collisions are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "huewrap.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def wrap(hue, rotation, hue_max):
    """Circular rotation: add and take modulo, so the hue wraps around the wheel."""
    return (hue + rotation) % hue_max


def clamp(hue, rotation, hue_max):
    """Naive rotation: add and clamp to the range, treating the wheel as if it had an edge."""
    return min(hue + rotation, hue_max)


def crosses_seam(hue, rotation, hue_max):
    """Does this hue's rotation push it past the 360/0 seam?"""
    return hue + rotation >= hue_max


# ----------------------------------------------------------------- printing

def rotate_view(data):
    hues, rot, hm = data["hues"], data["rotation"], data["hue_max"]
    print("ROTATE — each hue turned by %d degrees" % rot)
    print("-" * 56)
    print("  hue    wrapped   clamped   crosses seam?")
    for h in hues:
        print("  %-5d  %-7d   %-7d   %s" % (h, wrap(h, rot, hm), clamp(h, rot, hm), crosses_seam(h, rot, hm)))
    print("-" * 56)
    print("  low hues agree; hues crossing the seam diverge sharply")


def collide_view(data):
    hues, rot, hm = data["hues"], data["rotation"], data["hue_max"]
    crossing = [h for h in hues if crosses_seam(h, rot, hm)]
    print("COLLIDE — hues that cross the seam, clamped vs wrapped")
    print("-" * 56)
    for h in crossing:
        print("  hue %d -> wrapped %d, clamped %d" % (h, wrap(h, rot, hm), clamp(h, rot, hm)))
    clamped_vals = [clamp(h, rot, hm) for h in crossing]
    wrapped_vals = [wrap(h, rot, hm) for h in crossing]
    print("  clamped values: %s  (distinct: %d)" % (clamped_vals, len(set(clamped_vals))))
    print("  wrapped values: %s  (distinct: %d)" % (wrapped_vals, len(set(wrapped_vals))))
    print("-" * 56)
    print("  clamping collapses distinct crossing hues; wrapping keeps them distinct")


def check(data):
    print("SELF-TEST — hues that cross 360 wrap to the correct low angles; clamping gives the wrong color and collides")
    print("-" * 116)
    hues, rot, hm = data["hues"], data["rotation"], data["hue_max"]
    crossing = [h for h in hues if crosses_seam(h, rot, hm)]

    some_cross = len(crossing) > 0
    print("  some hues cross the 360/0 seam when rotated = %s (%s)" % (some_cross, crossing))

    wrap_in_range = all(0 <= wrap(h, rot, hm) < hm for h in hues)
    print("  every wrapped hue stays in [0, %d) = %s" % (hm, wrap_in_range))

    wrap_differs_from_clamp = any(wrap(h, rot, hm) != clamp(h, rot, hm) for h in crossing)
    print("  wrap and clamp disagree on the crossing hues = %s" % wrap_differs_from_clamp)

    clamped_vals = [clamp(h, rot, hm) for h in crossing]
    clamp_collides = len(set(clamped_vals)) < len(crossing)
    print("  clamping collapses distinct crossing hues to one value = %s (%s)" % (clamp_collides, clamped_vals))

    wrapped_vals = [wrap(h, rot, hm) for h in crossing]
    wrap_keeps_distinct = len(set(wrapped_vals)) == len(crossing)
    print("  wrapping keeps the crossing hues distinct = %s (%s)" % (wrap_keeps_distinct, wrapped_vals))

    ok = (some_cross and wrap_in_range and wrap_differs_from_clamp and clamp_collides and wrap_keeps_distinct)
    print("-" * 116)
    print("SELF-TEST %s  some_cross=%s  wrap_in_range=%s  wrap_differs_from_clamp=%s  clamp_collides=%s  wrap_keeps_distinct=%s"
          % ("PASS" if ok else "FAIL", some_cross, wrap_in_range, wrap_differs_from_clamp, clamp_collides, wrap_keeps_distinct))
    return ok


def main():
    p = argparse.ArgumentParser(description="Hue rotation: rotate hue with circular arithmetic -- (hue + rotation) modulo 360 -- never by clamping the sum to the range, because hue is an angle where 360 equals 0, so clamping produces the wrong color for any hue that should cross the seam and collapses distinct crossing hues into a single boundary value.")
    p.add_argument("--rotate", action="store_true")
    p.add_argument("--collide", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("hues=%s  rotation=%d  hue_max=%d  file=%s  (these are a fixture)"
          % (data["hues"], data["rotation"], data["hue_max"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.rotate:
        rotate_view(data)
    elif args.collide:
        collide_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
