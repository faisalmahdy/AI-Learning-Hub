"""Interpolate hue along the shorter arc around the color wheel, not by linearly interpolating the two angle numbers -- hue is circular, so a straight lerp of the raw angles takes the long way around when the two hues straddle the 0/360 seam and sweeps through the opposite color.

Hue is an angle in [0, 360): the value 0 and the value 360 are the same red, so the number line of hues is really a circle that wraps at that seam. Between any two hues there are two arcs -- a short one and a long one summing to 360 -- and a gradient from one color to another should follow the shorter arc, the way the two colors are actually near each other on the wheel.

Linear interpolation of the raw angles, start + t*(end - start), does not know about the wrap. It just walks the number line from one value to the other. When the two hues are on the same side of the seam that is fine, but when they straddle it -- say 350 and 20, which are only 30 degrees apart going through red -- the raw difference end - start is 20 - 350 = -330, so the lerp walks 330 degrees the long way around: down through magenta, blue, cyan, green, and only then to 20. Its midpoint lands near 185, a cyan, which is close to the complementary color of both endpoints -- the exact opposite of what a red-to-red gradient should show.

The fix is to interpolate the signed shortest angular difference. Compute delta = end - start, and if it is greater than 180 wrap it down by 360, or if it is less than -180 wrap it up by 360, so the step is at most 180 degrees in magnitude -- the shorter arc. Interpolate start + t*delta along that arc, then wrap each result back into [0, 360). Now the gradient sweeps the 30-degree short way and stays in the reds.

On this fixture the endpoints are 350 and 20, 30 degrees apart the short way. The naive lerp sweeps 330 degrees through cyan (midpoint about 185); the shortest-arc lerp sweeps 30 degrees and stays red (midpoint about 5). This computes both.

  --interp   the gradient hues at each step, naive lerp vs shortest-arc lerp
  --arc      the two arc lengths and midpoints the two methods take
  --check    the naive lerp takes the long way and its midpoint lands near the opposite color; the shortest-arc lerp stays on the short arc between the endpoints

start_hue, end_hue, and steps are the fixture; the two sweeps, arc lengths, and midpoints are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "huelerp.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def wrap360(h):
    """Bring a hue angle back into [0, 360)."""
    return h % 360


def shortest_delta(start, end):
    """Signed shortest angular step from start to end, in (-180, 180]."""
    delta = end - start
    while delta > 180:
        delta -= 360
    while delta < -180:
        delta += 360
    return delta


def naive_lerp(start, end, t):
    """Linear interpolation of the raw angle numbers -- ignores the wrap."""
    return wrap360(start + t * (end - start))


def arc_lerp(start, end, t):
    """Interpolation along the shorter arc -- steps by the signed shortest delta, then wraps."""
    return wrap360(start + t * shortest_delta(start, end))


def circular_distance(a, b):
    """Shortest distance between two hues on the wheel, in [0, 180]."""
    d = abs(wrap360(a) - wrap360(b))
    return min(d, 360 - d)


def steps_t(steps):
    """Fractions from 0 to 1 inclusive."""
    return [i / (steps - 1) for i in range(steps)]


# ----------------------------------------------------------------- printing

def interp_view(data):
    start, end, steps = data["start_hue"], data["end_hue"], data["steps"]
    print("INTERP — gradient from hue %d to hue %d in %d steps" % (start, end, steps))
    print("-" * 52)
    print("  t       naive lerp     shortest-arc")
    for t in steps_t(steps):
        print("  %-6.2f  %-13.1f  %.1f" % (t, naive_lerp(start, end, t), arc_lerp(start, end, t)))
    print("-" * 52)
    print("  naive swings to the far side of the wheel; shortest-arc stays in the reds")


def arc_view(data):
    start, end, steps = data["start_hue"], data["end_hue"], data["steps"]
    naive_arc = abs(end - start)
    short_arc = abs(shortest_delta(start, end))
    print("ARC — the two paths from hue %d to hue %d" % (start, end))
    print("-" * 52)
    print("  naive lerp arc length     = %.0f degrees (the long way)" % naive_arc)
    print("  shortest-arc length       = %.0f degrees (the short way)" % short_arc)
    print("  naive midpoint (t=0.5)    = %.1f" % naive_lerp(start, end, 0.5))
    print("  shortest-arc midpoint     = %.1f" % arc_lerp(start, end, 0.5))
    print("-" * 52)
    print("  the two arcs sum to 360; the shorter one is the gradient you meant")


def check(data):
    print("SELF-TEST — the naive lerp takes the long way and its midpoint lands near the opposite color; the shortest-arc lerp stays on the short arc")
    print("-" * 112)
    start, end = data["start_hue"], data["end_hue"]

    naive_arc = abs(end - start)
    short_arc = abs(shortest_delta(start, end))

    naive_goes_long_way = naive_arc > 180
    print("  naive lerp walks more than half the wheel = %s (%.0f degrees)" % (naive_goes_long_way, naive_arc))

    short_arc_is_short = short_arc <= 180 and short_arc < naive_arc
    print("  shortest-arc stays on the short side = %s (%.0f degrees)" % (short_arc_is_short, short_arc))

    naive_mid = naive_lerp(start, end, 0.5)
    naive_midpoint_far = min(circular_distance(naive_mid, start), circular_distance(naive_mid, end)) > 90
    print("  naive midpoint is far from both endpoints = %s (mid %.1f, nearest endpoint %.0f away)"
          % (naive_midpoint_far, naive_mid, min(circular_distance(naive_mid, start), circular_distance(naive_mid, end))))

    short_mid = arc_lerp(start, end, 0.5)
    short_midpoint_between = (circular_distance(short_mid, start) <= short_arc
                             and circular_distance(short_mid, end) <= short_arc)
    print("  shortest-arc midpoint sits between the endpoints = %s (mid %.1f, %.0f from each)"
          % (short_midpoint_between, short_mid, circular_distance(short_mid, start)))

    paths_disagree = circular_distance(naive_mid, short_mid) > 90
    print("  the two midpoints are on opposite sides of the wheel = %s (%.0f apart)"
          % (paths_disagree, circular_distance(naive_mid, short_mid)))

    ok = (naive_goes_long_way and short_arc_is_short and naive_midpoint_far
          and short_midpoint_between and paths_disagree)
    print("-" * 112)
    print("SELF-TEST %s  naive_goes_long_way=%s  short_arc_is_short=%s  naive_midpoint_far=%s  short_midpoint_between=%s  paths_disagree=%s"
          % ("PASS" if ok else "FAIL", naive_goes_long_way, short_arc_is_short, naive_midpoint_far,
             short_midpoint_between, paths_disagree))
    return ok


def main():
    p = argparse.ArgumentParser(description="Hue interpolation: interpolate hue along the shorter arc around the color wheel, not by linearly interpolating the two angle numbers, because hue is circular -- a straight lerp of the raw angles takes the long way around when the two hues straddle the 0/360 seam and sweeps through the opposite color.")
    p.add_argument("--interp", action="store_true")
    p.add_argument("--arc", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("start_hue=%d  end_hue=%d  steps=%d  file=%s  (these are a fixture)"
          % (data["start_hue"], data["end_hue"], data["steps"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.interp:
        interp_view(data)
    elif args.arc:
        arc_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
