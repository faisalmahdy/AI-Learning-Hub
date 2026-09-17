"""Restricting the range of x attenuates the correlation -- a real relationship looks weak when you only study a slice.

Correlation measures how much y moves with x relative to how much each varies. That makes it sensitive to
the RANGE of x you look at. Over the full range, a genuine linear relationship shows a strong correlation.
But study only a narrow slice of x -- only admitted students, only top performers, only high earners -- and
the variation in x collapses toward the noise, so the same relationship measures far weaker, sometimes near
zero. The relationship did not change; you just looked through a keyhole that hid most of the variation.

This is range restriction, and it is a standard way real correlations are underestimated. The classic case:
'SAT scores barely predict college grades' -- measured only among admitted students, whose SAT range is
narrow by construction, so the correlation is attenuated relative to the full applicant pool. Any time a
correlation is computed on a pre-selected, range-restricted subgroup, it understates the true association.

On this fixture ten points have a strong linear relationship: the full-range correlation is 0.92. Restrict
to x in [5,8] -- four points from the middle -- and the correlation drops to 0.31, weak enough to dismiss.
Same points, same relationship; only the range of x examined changed. This computes both.

  --points     the full point set and the restricted slice
  --correlate  the correlation over the full range vs the restricted range
  --check      the full-range correlation is strong; restricting the range attenuates it to weak

The points and the restriction range are the fixture; every correlation is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "points.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def pearson(points):
    """Correlation of (x, y): covariance over the product of the spreads."""
    n = len(points)
    mx = sum(p[0] for p in points) / n
    my = sum(p[1] for p in points) / n
    cov = sum((x - mx) * (y - my) for x, y in points)
    vx = sum((x - mx) ** 2 for x, y in points)
    vy = sum((y - my) ** 2 for x, y in points)
    if vx == 0 or vy == 0:
        return 0.0
    return round(cov / math.sqrt(vx * vy), 4)


def restrict(points, lo, hi):
    """Keep only the points whose x falls in [lo, hi] -- the narrow slice you actually studied."""
    return [p for p in points if lo <= p[0] <= hi]


# ----------------------------------------------------------------- printing

def points_view(data):
    pts = data["points"]
    lo, hi = data["restrict_lo"], data["restrict_hi"]
    print("POINTS — %d points; the restricted view keeps x in [%d,%d]" % (len(pts), lo, hi))
    print("-" * 46)
    for x, y in pts:
        mark = "  <- kept" if lo <= x <= hi else ""
        print("  x=%2d  y=%2d%s" % (x, y, mark))
    print("-" * 46)
    print("  the restricted view sees only %d of %d points." % (len(restrict(pts, lo, hi)), len(pts)))


def correlate_view(data):
    pts = data["points"]
    lo, hi = data["restrict_lo"], data["restrict_hi"]
    full = pearson(pts)
    rest = pearson(restrict(pts, lo, hi))
    print("CORRELATE — full range vs restricted range")
    print("-" * 48)
    print("  full range (x 1-10):   r = %+.4f  (strong)" % full)
    print("  restricted (x %d-%d):    r = %+.4f  (weak)" % (lo, hi, rest))
    print("-" * 48)
    print("  same relationship; restricting the range of x attenuated it.")


def check(data):
    print("SELF-TEST — the full-range correlation is strong; restricting the range attenuates it to weak")
    print("-" * 88)
    pts = data["points"]
    lo, hi = data["restrict_lo"], data["restrict_hi"]
    full = pearson(pts)
    rest = pearson(restrict(pts, lo, hi))

    full_strong = full > 0.8
    print("  the full-range correlation is strong = %s (r = %+.4f)" % (full_strong, full))

    restricted_weak = rest < 0.4
    print("  the restricted-range correlation is weak = %s (r = %+.4f)" % (restricted_weak, rest))

    restriction_attenuates = rest < full
    print("  restricting the range attenuates the correlation = %s (%+.4f -> %+.4f)" % (restriction_attenuates, full, rest))

    same_points = set(map(tuple, restrict(pts, lo, hi))).issubset(set(map(tuple, pts)))
    print("  the restricted set is a subset of the same points = %s (nothing changed but the range)" % same_points)

    ok = full_strong and restricted_weak and restriction_attenuates and same_points
    print("-" * 88)
    print("SELF-TEST %s  full_strong=%s  restricted_weak=%s  restriction_attenuates=%s  same_points=%s"
          % ("PASS" if ok else "FAIL", full_strong, restricted_weak, restriction_attenuates, same_points))
    return ok


def main():
    p = argparse.ArgumentParser(description="Restricting the range of x attenuates the correlation.")
    p.add_argument("--points", action="store_true")
    p.add_argument("--correlate", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("points=%d  restrict=[%d,%d]  file=%s  (the points are a fixture)"
          % (len(data["points"]), data["restrict_lo"], data["restrict_hi"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.points:
        points_view(data)
    elif args.correlate:
        correlate_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
